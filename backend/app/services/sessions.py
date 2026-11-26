
"""Session lifecycle helpers.

The application process is independent of the client's remote-access connection.
Only an explicit administrative action requests application termination.

Lifecycle:
pending -> launching -> running -> stop_requested -> stopped
pending/launching/running may become failed only when failure is confirmed.
A launching session is never expired only because the Agent heartbeat was interrupted.
"""

import secrets
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..models import ActivityLog, Agent, RemoteSession, utcnow


ACTIVE = (
    "pending",
    "launching",
    "running",
    "stop_requested",
)


def new_session_id() -> str:
    return secrets.token_hex(16)


def active_session(db: Session, client_id: int) -> RemoteSession | None:
    return db.scalar(
        select(RemoteSession)
        .where(
            RemoteSession.client_id == client_id,
            RemoteSession.status.in_(ACTIVE),
        )
        .order_by(RemoteSession.id.desc())
    )


def has_active_session_for_application(
    db: Session,
    application_id: int,
) -> bool:
    return (
        db.scalar(
            select(RemoteSession.id)
            .where(
                RemoteSession.application_id == application_id,
                RemoteSession.status.in_(ACTIVE),
            )
            .limit(1)
        )
        is not None
    )


def agent_online(db: Session) -> bool:
    cutoff = utcnow() - timedelta(
        seconds=settings.agent_online_seconds
    )

    return (
        db.scalar(
            select(Agent.id)
            .where(Agent.last_seen >= cutoff)
            .limit(1)
        )
        is not None
    )


def expire_stale(db: Session) -> None:
    """Never expire pending/launching sessions by time alone.

    A temporary Agent/network outage must not turn a real or recoverable
    application process into a failed database session.

    Pending launches are delivered when the Agent reconnects.
    Launching sessions are reconciled against actual Windows processes
    by the Agent recovery protocol.
    """
    return


def request_stop(session: RemoteSession, reason: str) -> None:
    """Request application termination. Caller must commit.

    A pending launch can be cancelled because the Agent has not claimed it.
    Once launching/running, keep stop_requested until the Agent confirms
    that the process has actually stopped.
    """
    if session.status == "pending":
        session.status = "stopped"
        session.ended_at = utcnow()
        session.message = reason

    elif session.status in ("launching", "running"):
        session.status = "stop_requested"
        session.message = reason


def request_stop_for_client(
    db: Session,
    client_id: int,
    reason: str,
) -> None:
    """Request termination for all active sessions belonging to a client."""
    sessions = db.scalars(
        select(RemoteSession).where(
            RemoteSession.client_id == client_id,
            RemoteSession.status.in_(ACTIVE),
        )
    ).all()

    for session in sessions:
        request_stop(session, reason)


def request_stop_for_application(
    db: Session,
    application_id: int,
    reason: str,
) -> None:
    """Request termination for all active sessions of an application."""
    sessions = db.scalars(
        select(RemoteSession).where(
            RemoteSession.application_id == application_id,
            RemoteSession.status.in_(ACTIVE),
        )
    ).all()

    for session in sessions:
        request_stop(session, reason)
