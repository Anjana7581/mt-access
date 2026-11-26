
"""Remote application sessions.

Client disconnect ends access only.
Admin termination stops the server-side application.
"""

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..config import settings
from ..database import get_db
from ..deps import require_admin, require_client
from ..models import (
    ActivityLog,
    Agent,
    Application,
    ClientApplication,
    RemoteSession,
    User,
    utcnow,
)
from ..schemas import (
    AgentOut,
    SessionAdminOut,
    SessionOut,
)
from ..services import audit
from ..services import sessions as svc


router = APIRouter(
    prefix="/api/sessions",
    tags=["sessions"],
)

agents_router = APIRouter(
    prefix="/api/agents",
    tags=["sessions"],
    dependencies=[Depends(require_admin)],
)


def _view(
    session: RemoteSession,
    app: Application | None,
) -> SessionOut:
    return SessionOut(
        status=session.status,
        session_id=session.session_id,
        application_name=(
            app.application_name if app else None
        ),
        application_type=(
            app.application_type if app else None
        ),
        started_at=session.started_at,
        ended_at=session.ended_at,
        message=session.message,
    )


# ---------------- client ----------------

@router.post(
    "/launch",
    response_model=SessionOut,
    status_code=202,
)
def launch(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_client),
):
    # Prevent simultaneous duplicate launch requests.
    db.scalar(
        select(User.id)
        .where(User.id == user.id)
        .with_for_update()
    )

    svc.expire_stale(db)

    existing = svc.active_session(db, user.id)

    if existing:
        return _view(
            existing,
            db.get(Application, existing.application_id),
        )

    assignment = db.scalar(
        select(ClientApplication)
        .where(ClientApplication.client_id == user.id)
        .options(selectinload(ClientApplication.application))
    )

    if not assignment:
        raise HTTPException(
            409,
            "No application is assigned to your account",
        )

    if assignment.application.status != "active":
        raise HTTPException(
            409,
            "Your application is currently unavailable",
        )

    if not svc.agent_online(db):
        raise HTTPException(
            503,
            "The remote host is offline. Please try again shortly.",
        )

    session = RemoteSession(
        client_id=user.id,
        application_id=assignment.application_id,
        session_id=svc.new_session_id(),
        status="pending",
    )

    db.add(session)

    audit.log(
        db,
        user.id,
        "session_launch_requested",
        f"application_id={assignment.application_id}",
        request,
    )

    db.commit()
    db.refresh(session)

    return _view(session, assignment.application)


@router.get(
    "/status",
    response_model=SessionOut,
)
def my_status(
    db: Session = Depends(get_db),
    user: User = Depends(require_client),
):
    svc.expire_stale(db)

    session = db.scalar(
        select(RemoteSession)
        .where(RemoteSession.client_id == user.id)
        .order_by(RemoteSession.id.desc())
    )

    if not session:
        return SessionOut(status="none")

    return _view(
        session,
        db.get(Application, session.application_id),
    )


@router.post(
    "/disconnect",
    response_model=SessionOut,
)
def disconnect(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_client),
):
    """Disconnect client access without stopping the MT application."""

    session = svc.active_session(db, user.id)

    if not session:
        raise HTTPException(
            404,
            "No active application session",
        )

    audit.log(
        db,
        user.id,
        "client_access_disconnected",
        (
            f"session={session.session_id}; "
            "Application process remains running on the server"
        ),
        request,
    )

    # IMPORTANT:
    # Do not call svc.request_stop().
    # Do not change the application session status.
    # Do not send a stop command to the Windows Agent.

    db.commit()

    return _view(
        session,
        db.get(Application, session.application_id),
    )


# ---------------- admin ----------------

@router.get(
    "",
    response_model=list[SessionAdminOut],
)
def list_sessions(
    active_only: bool = True,
    limit: int = 100,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    svc.expire_stale(db)

    query = (
        select(RemoteSession, Application, User)
        .join(
            Application,
            Application.id == RemoteSession.application_id,
        )
        .join(
            User,
            User.id == RemoteSession.client_id,
        )
        .order_by(RemoteSession.id.desc())
        .limit(min(max(limit, 1), 500))
    )

    if active_only:
        query = query.where(
            RemoteSession.status.in_(svc.ACTIVE)
        )

    output = []

    for session, app, user in db.execute(query):
        view = _view(session, app)

        output.append(
            SessionAdminOut(
                **view.model_dump(),
                id=session.id,
                client_id=user.id,
                client_code=user.client_code,
                pid=session.pid,
            )
        )

    return output


@router.post(
    "/{session_id}/terminate",
    response_model=SessionOut,
)
def terminate(
    session_id: str,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    session = db.scalar(
        select(RemoteSession).where(
            RemoteSession.session_id == session_id
        )
    )

    if not session:
        raise HTTPException(
            404,
            "Session not found",
        )

    if session.status not in svc.ACTIVE:
        raise HTTPException(
            409,
            f"Session is already {session.status}",
        )

    # Admin authority: request application termination regardless
    # of whether the client currently has access.
    svc.request_stop(
        session,
        "Terminated by administrator",
    )

    audit.log(
        db,
        admin.id,
        "session_terminated",
        (
            f"session={session.session_id}; "
            f"client_id={session.client_id}; "
            "Administrator termination requested"
        ),
        request,
    )

    db.add(
        ActivityLog(
            user_id=admin.id,
            activity="admin_application_termination",
            details=(
                f"session={session.session_id}; "
                f"client_id={session.client_id}; "
                "Admin requested application termination. "
                "Any active client access will be interrupted."
            ),
        )
    )

    db.commit()

    return _view(
        session,
        db.get(Application, session.application_id),
    )


# ---------------- agent status ----------------

@agents_router.get(
    "",
    response_model=list[AgentOut],
)
def list_agents(
    db: Session = Depends(get_db),
):
    now = utcnow()
    cutoff = now - timedelta(
        seconds=settings.agent_online_seconds
    )

    agents = db.scalars(
        select(Agent).order_by(Agent.id)
    ).all()

    output = []

    for agent in agents:
        online = agent.last_seen >= cutoff

        if not online:
            # Create one offline log for this outage.
            existing_log = db.scalar(
                select(ActivityLog.id)
                .where(
                    ActivityLog.activity == "agent_offline",
                    ActivityLog.details.like(
                        f"agent={agent.name};%"
                    ),
                    ActivityLog.created_at >= agent.last_seen,
                )
                .limit(1)
            )

            if not existing_log:
                db.add(
                    ActivityLog(
                        user_id=None,
                        activity="agent_offline",
                        details=(
                            f"agent={agent.name}; "
                            f"last_seen={agent.last_seen.isoformat()}; "
                            "No recent heartbeat received. "
                            "Running MT applications are not "
                            "automatically terminated."
                        ),
                    )
                )

        output.append(
            AgentOut(
                id=agent.id,
                name=agent.name,
                version=agent.version,
                last_seen=agent.last_seen,
                online=online,
            )
        )

    db.commit()

    return output
