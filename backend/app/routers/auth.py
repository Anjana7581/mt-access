"""Login / logout / current user."""
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..deps import get_current_user
from ..models import User, utcnow
from ..schemas import ChangePasswordIn, LoginIn, TokenOut, UserOut
from ..security import DUMMY_HASH, create_access_token, hash_password, verify_password
from ..services import audit

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, request: Request, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email.strip().lower()))
    now = utcnow()

    if user and user.locked_until and user.locked_until > now:
        audit.log(db, user.id, "login_blocked_locked", request=request)
        db.commit()
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Account temporarily locked. Try again later.")

    password_ok = verify_password(body.password, user.password_hash if user else DUMMY_HASH)

    if not user or not password_ok or user.status != "active":
        if user and not password_ok:
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= settings.max_failed_logins:
                user.locked_until = now + timedelta(minutes=settings.lockout_minutes)
                user.failed_login_attempts = 0
        audit.log(db, user.id if user else None, "login_failed", request=request)
        db.commit()
        # Same message for every failure: don't reveal which accounts exist or are inactive.
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")

    user.failed_login_attempts = 0
    user.locked_until = None
    audit.log(db, user.id, "login", request=request)
    db.commit()
    return TokenOut(access_token=create_access_token(user))


@router.post("/logout", status_code=204)
def logout(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Bumps token_version, which invalidates this user's tokens everywhere."""
    user.token_version += 1
    audit.log(db, user.id, "logout", request=request)
    db.commit()


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.post("/change-password", response_model=TokenOut)
def change_password(body: ChangePasswordIn, request: Request, user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    now = utcnow()
    if user.locked_until and user.locked_until > now:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Account temporarily locked. Try again later.")
    if not verify_password(body.current_password, user.password_hash):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= settings.max_failed_logins:
            user.locked_until = now + timedelta(minutes=settings.lockout_minutes)
            user.failed_login_attempts = 0
        audit.log(db, user.id, "password_change_failed", request=request)
        db.commit()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Current password is incorrect")
    if verify_password(body.new_password, user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "New password must be different from the current one")
    user.password_hash = hash_password(body.new_password)
    user.token_version += 1          # signs out every other device
    user.failed_login_attempts = 0
    user.locked_until = None
    audit.log(db, user.id, "password_changed", request=request)
    db.commit()
    return TokenOut(access_token=create_access_token(user))   # caller stays logged in