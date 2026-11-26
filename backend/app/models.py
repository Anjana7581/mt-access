"""Database models (MySQL). sessions/activity_logs are defined now so the schema is
complete; sessions get used from Phase 3/4 onward."""
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    """Naive UTC timestamp (consistent across MySQL and SQLite)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (Index("ix_users_role_status", "role", "status"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    client_code: Mapped[Optional[str]] = mapped_column(String(32), unique=True)  # e.g. CLIENT001
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="client")      # admin | client
    status: Mapped[str] = mapped_column(String(20), default="active")    # active | inactive
    token_version: Mapped[int] = mapped_column(Integer, default=0)       # bump => all JWTs invalid
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    assignment: Mapped[Optional["ClientApplication"]] = relationship(
        back_populates="client", uselist=False, cascade="all, delete-orphan",
        foreign_keys="ClientApplication.client_id",
    )


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(primary_key=True)
    application_name: Mapped[str] = mapped_column(String(120))
    executable_path: Mapped[str] = mapped_column(String(500), unique=True)
    working_directory: Mapped[str] = mapped_column(String(500))
    application_type: Mapped[str] = mapped_column(String(10))            # MT4 | MT5
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    assignment: Mapped[Optional["ClientApplication"]] = relationship(
        back_populates="application", uselist=False
    )


class ClientApplication(Base):
    """One client <-> one installation. Both sides are UNIQUE on purpose: a single
    MetaTrader installation must never be shared by two clients."""
    __tablename__ = "client_applications"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id", ondelete="RESTRICT"), unique=True)
    assigned_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    assigned_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    client: Mapped[User] = relationship(back_populates="assignment", foreign_keys=[client_id])
    application: Mapped[Application] = relationship(back_populates="assignment")


class RemoteSession(Base):
    __tablename__ = "sessions"
    __table_args__ = (Index("ix_sessions_client_status", "client_id", "status"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id", ondelete="RESTRICT"))
    session_id: Mapped[str] = mapped_column(String(64), unique=True)
    status: Mapped[str] = mapped_column(String(20), default="starting")
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    pid: Mapped[Optional[int]] = mapped_column(Integer)
    message: Mapped[Optional[str]] = mapped_column(String(255))

class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    version: Mapped[Optional[str]] = mapped_column(String(20))
    last_seen: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    
class ActivityLog(Base):
    __tablename__ = "activity_logs"
    __table_args__ = (Index("ix_activity_user_created", "user_id", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    activity: Mapped[str] = mapped_column(String(80))
    details: Mapped[Optional[str]] = mapped_column(Text)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)



class RdpCredential(Base):
    """Encrypted Windows RDP credentials for an assigned application."""
    __tablename__ = "rdp_credentials"

    id: Mapped[int] = mapped_column(primary_key=True)

    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    hostname: Mapped[str] = mapped_column(String(253), nullable=False)
    port: Mapped[int] = mapped_column(Integer, default=3389, nullable=False)

    # Both values are Fernet-encrypted before database storage.
    username_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    password_encrypted: Mapped[str] = mapped_column(Text, nullable=False)

    remote_app_alias: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utcnow,
        onupdate=utcnow,
    )
