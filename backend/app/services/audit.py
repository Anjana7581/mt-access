"""Writes to activity_logs. Callers commit."""
from typing import Optional

from fastapi import Request
from sqlalchemy.orm import Session

from ..models import ActivityLog


def log(db: Session, user_id: Optional[int], activity: str, details: str | None = None,
        request: Request | None = None) -> None:
    ip = request.client.host if request and request.client else None
    db.add(ActivityLog(user_id=user_id, activity=activity, details=details, ip_address=ip))
