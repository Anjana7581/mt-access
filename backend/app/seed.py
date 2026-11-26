"""Create the first admin. Run: python -m app.seed  (uses INITIAL_ADMIN_EMAIL / INITIAL_ADMIN_PASSWORD)."""
from sqlalchemy import select

from .config import settings
from .database import Base, SessionLocal, engine
from .models import User
from .security import check_password_policy, hash_password


def seed_admin() -> bool:
    if not (settings.initial_admin_email and settings.initial_admin_password):
        return False
    check_password_policy(settings.initial_admin_password)
    with SessionLocal() as db:
        if db.scalar(select(User.id).where(User.role == "admin")):
            return False
        db.add(User(name="Administrator", email=settings.initial_admin_email.lower(),
                    password_hash=hash_password(settings.initial_admin_password), role="admin"))
        db.commit()
        return True


if __name__ == "__main__":
    Base.metadata.create_all(engine)
    print("Admin created" if seed_admin() else "No admin created (already exists or env not set)")
