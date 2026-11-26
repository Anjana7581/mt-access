
"""Endpoints used only by the Windows Agent."""

import secrets
from datetime import timedelta

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models import ActivityLog, Agent, Application, RemoteSession, utcnow
from ..schemas import AgentHeartbeat, AgentReport
from ..services import audit
from ..services import sessions as svc


def require_agent(x_agent_secret: str = Header(default="")):
    if len(settings.agent_secret) < 24:
        raise HTTPException(
            503,
            "AGENT_SECRET is not configured on the server (minimum 24 characters)",
        )

    if not secrets.compare_digest(
        x_agent_secret.encode(),
        settings.agent_secret.encode(),
    ):
        raise HTTPException(401, "Invalid agent credentials")


router = APIRouter(
    prefix="/api/agent",
    tags=["agent"],
    dependencies=[Depends(require_agent)],
)


def system_log(db: Session, activity: str, details: str):
    db.add(
        ActivityLog(
            user_id=None,
            activity=activity[:80],
            details=details[:5000],
        )
    )


@router.post("/heartbeat")
def heartbeat(body: AgentHeartbeat, db: Session = Depends(get_db)):
    """Register the Agent or update its online status."""
    agent = db.scalar(select(Agent).where(Agent.name == body.name))
    now = utcnow()
    cutoff = now - timedelta(seconds=settings.agent_online_seconds)

    if not agent:
        agent = Agent(
            name=body.name,
            version=body.version,
            last_seen=now,
        )
        db.add(agent)
        system_log(
            db,
            "agent_online",
            f"agent={body.name}; Agent registered and online",
        )
    else:
        if agent.last_seen < cutoff:
            system_log(
                db,
                "agent_reconnected",
                f"agent={body.name}; Agent reconnected to backend",
            )

        agent.version = body.version
        agent.last_seen = now

    db.commit()

    return {
        "ok": True,
        "agent": body.name,
        "server_time": now.isoformat(),
    }


def _app_fields(app: Application) -> dict:
    return {
        "application_id": app.id,
        "application_type": app.application_type,
        "executable_path": app.executable_path,
        "working_directory": app.working_directory,
    }


@router.get("/work")
def work(db: Session = Depends(get_db)):
    """Return launch/stop commands and process-reconciliation records.

    A session in launching is sent as recovering, not expired. This lets
    the Agent find an MT process that started just before a lost report
    or Agent restart.
    """
    svc.expire_stale(db)

    rows = db.execute(
        select(RemoteSession, Application)
        .join(Application, Application.id == RemoteSession.application_id)
        .where(RemoteSession.status.in_(svc.ACTIVE))
        .order_by(RemoteSession.id)
    ).all()

    commands = []
    running = []
    recovering = []
    expected = []

    for session, app in rows:
        if session.status == "pending":
            if app.status != "active":
                session.status = "failed"
                session.ended_at = utcnow()
                session.message = "Application is inactive"

                system_log(
                    db,
                    "application_launch_rejected",
                    f"session={session.session_id}; application_id={app.id}; Application is inactive",
                )
                continue

            session.status = "launching"

            commands.append({
                "action": "launch",
                "session_id": session.session_id,
                **_app_fields(app),
            })

            expected.append(session.session_id)

        elif session.status == "launching":
            recovering.append({
                "session_id": session.session_id,
                "pid": session.pid,
                "started_at": (
                    session.started_at.isoformat()
                    if session.started_at else None
                ),
                "launch_timeout_seconds": settings.launch_timeout_seconds,
                **_app_fields(app),
            })

            expected.append(session.session_id)

        elif session.status == "stop_requested":
            commands.append({
                "action": "stop",
                "session_id": session.session_id,
                "pid": session.pid,
                **_app_fields(app),
            })

            expected.append(session.session_id)

        elif session.status == "running":
            running.append({
                "session_id": session.session_id,
                "pid": session.pid,
                **_app_fields(app),
            })

            expected.append(session.session_id)

    db.commit()

    return {
        "commands": commands,
        "running": running,
        "recovering": recovering,
        "expected": expected,
    }


@router.post("/events")
def agent_event(body: dict, db: Session = Depends(get_db)):
    """Store Agent, network, and application events in the admin activity log."""
    name = str(body.get("name", "")).strip()
    event = str(body.get("event", "")).strip()
    details = str(body.get("details", "")).strip()

    if not name or not event:
        raise HTTPException(422, "Agent name and event are required")

    if len(name) > 80 or len(event) > 80:
        raise HTTPException(422, "Agent name or event is too long")

    agent = db.scalar(select(Agent).where(Agent.name == name))

    if not agent:
        raise HTTPException(404, "Agent is not registered")

    system_log(db, event, f"agent={name}; {details}")
    db.commit()

    return {"ok": True}


@router.post("/sessions/{session_id}/report")
def report(
    session_id: str,
    body: AgentReport,
    request: Request,
    db: Session = Depends(get_db),
):
    """Receive process status from the Agent without overriding admin stop requests."""
    session = db.scalar(
        select(RemoteSession).where(RemoteSession.session_id == session_id)
    )

    if not session:
        raise HTTPException(404, "Unknown session")

    # A delayed report must never reopen a terminal session.
    if session.status not in svc.ACTIVE:
        return {"status": session.status}

    if body.status == "running":
        if body.pid is None:
            raise HTTPException(
                422,
                "A running process report must include its PID",
            )

        session.pid = body.pid

        # Admin termination wins over a late launch-success report.
        if session.status != "stop_requested":
            session.status = "running"

    elif body.status == "stopped":
        session.status = "stopped"
        session.ended_at = utcnow()

        if body.pid is not None:
            session.pid = body.pid

    elif body.status == "failed":
        # A failed stop attempt must not cancel an administrator's request.
        if session.status == "stop_requested":
            system_log(
                db,
                "application_termination_attempt_failed",
                f"session={session.session_id}; pid={session.pid}; {body.message or 'Agent reported failure'}",
            )
            db.commit()
            return {"status": session.status}

        session.status = "failed"
        session.ended_at = utcnow()

        if body.pid is not None:
            session.pid = body.pid

    if body.message and session.status != "stop_requested":
        session.message = body.message

    audit.log(
        db,
        session.client_id,
        f"session_{session.status}",
        (
            f"session={session.session_id} "
            f"pid={session.pid} "
            f"{body.message or ''}"
        ).strip(),
        request,
    )

    if body.status == "failed":
        system_log(
            db,
            "application_error",
            f"session={session.session_id}; client_id={session.client_id}; error={body.message or 'Unknown error'}",
        )

    elif body.status == "stopped":
        system_log(
            db,
            "application_stopped",
            f"session={session.session_id}; client_id={session.client_id}; message={body.message or 'Application stopped'}",
        )

    db.commit()

    return {"status": session.status}
