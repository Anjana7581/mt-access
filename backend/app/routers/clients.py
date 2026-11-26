"""Admin-only client management."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..deps import require_admin
from ..models import ActivityLog, ClientApplication, RemoteSession, User
from ..schemas import (ActivityOut, ClientCreate, ClientCreateOut, ClientOut, ClientUpdate,
                       PasswordReset, PasswordResetOut)
from ..security import generate_password, hash_password
from ..services import audit
from ..services import sessions as sess

router = APIRouter(prefix="/api/clients", tags=["clients"], dependencies=[Depends(require_admin)])


def _get_client(db: Session, client_id: int) -> User:
    user = db.scalar(
        select(User).where(User.id == client_id, User.role == "client")
        .options(selectinload(User.assignment).selectinload(ClientApplication.application))
    )
    if not user:
        raise HTTPException(404, "Client not found")
    return user


@router.post("", response_model=ClientCreateOut, status_code=201)
def create_client(body: ClientCreate, request: Request, db: Session = Depends(get_db),
                  admin: User = Depends(require_admin)):
    email = body.email.lower()
    if db.scalar(select(User.id).where(User.email == email)):
        raise HTTPException(409, "Email already in use")
    if body.client_code and db.scalar(select(User.id).where(User.client_code == body.client_code)):
        raise HTTPException(409, "client_code already in use")

    password = body.password or generate_password()
    user = User(name=body.name.strip(), email=email, client_code=body.client_code,
                password_hash=hash_password(password), role="client", status="active")
    db.add(user)
    try:
        db.flush()
        if not user.client_code:
            user.client_code = f"CLIENT{user.id:03d}"
        audit.log(db, admin.id, "client_created", f"client_id={user.id} code={user.client_code}", request)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Email or client_code already in use")

    out = ClientCreateOut.model_validate(user)
    out.initial_password = None if body.password else password
    return out


@router.get("", response_model=list[ClientOut])
def list_clients(q: Optional[str] = None, status_: Optional[str] = Query(None, alias="status"),
                 skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200),
                 db: Session = Depends(get_db)):
    stmt = (select(User).where(User.role == "client")
            .options(selectinload(User.assignment).selectinload(ClientApplication.application))
            .order_by(User.id).offset(skip).limit(limit))
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(User.name.like(like), User.email.like(like), User.client_code.like(like)))
    if status_:
        stmt = stmt.where(User.status == status_)
    return db.scalars(stmt).all()


@router.get("/{client_id}", response_model=ClientOut)
def get_client(client_id: int, db: Session = Depends(get_db)):
    return _get_client(db, client_id)


@router.put("/{client_id}", response_model=ClientOut)
def update_client(client_id: int, body: ClientUpdate, request: Request,
                  db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    user = _get_client(db, client_id)
    changes = body.model_dump(exclude_unset=True)
    if "email" in changes and changes["email"]:
        email = changes["email"].lower()
        if email != user.email and db.scalar(select(User.id).where(User.email == email)):
            raise HTTPException(409, "Email already in use")
        user.email = email
    if changes.get("name"):
        user.name = changes["name"].strip()
    if changes.get("status") and changes["status"] != user.status:
        user.status = changes["status"]
        if user.status == "inactive":
            user.token_version += 1       # kick out immediately. Phase 4 also disconnects live sessions.
            sess.request_stop_for_client(db, user.id, "Client deactivated")
        audit.log(db, admin.id, f"client_{user.status}d" if user.status == "inactive" else "client_activated",
                  f"client_id={user.id}", request)
    audit.log(db, admin.id, "client_updated", f"client_id={user.id} fields={sorted(changes)}", request)
    db.commit()
    return user


@router.delete("/{client_id}", status_code=204)
def delete_client(client_id: int, request: Request, db: Session = Depends(get_db),
                  admin: User = Depends(require_admin)):
    user = _get_client(db, client_id)
    if db.scalar(select(func.count()).select_from(RemoteSession).where(RemoteSession.client_id == user.id)):
        raise HTTPException(409, "Client has session history; deactivate instead of deleting")
    audit.log(db, admin.id, "client_deleted", f"client_id={user.id} code={user.client_code}", request)
    db.delete(user)
    db.commit()


@router.post("/{client_id}/reset-password", response_model=PasswordResetOut)
def reset_password(client_id: int, body: PasswordReset, request: Request,
                   db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    user = _get_client(db, client_id)
    new_pw = body.new_password or generate_password()
    user.password_hash = hash_password(new_pw)
    user.token_version += 1
    user.failed_login_attempts = 0
    user.locked_until = None
    audit.log(db, admin.id, "password_reset", f"client_id={user.id}", request)
    db.commit()
    return PasswordResetOut(generated_password=None if body.new_password else new_pw)


@router.get("/{client_id}/activity", response_model=list[ActivityOut])
def client_activity(client_id: int, limit: int = Query(100, ge=1, le=500), db: Session = Depends(get_db)):
    user = _get_client(db, client_id)
    needle = f"client_id={user.id}"
    cond = or_(ActivityLog.user_id == user.id,
               ActivityLog.details == needle,
               ActivityLog.details.startswith(needle + " ", autoescape=True))
    return db.scalars(select(ActivityLog).where(cond).order_by(ActivityLog.id.desc()).limit(limit)).all()
