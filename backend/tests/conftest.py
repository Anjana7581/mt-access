import os

os.environ.update(DATABASE_URL="sqlite://", SECRET_KEY="test-secret-key-test-secret-key-0123456789",
                  BCRYPT_ROUNDS="4", ALLOWED_APP_ROOTS=r"C:\Trading", ENVIRONMENT="test")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import User
from app.security import hash_password

ADMIN = ("admin@example.com", "AdminPass123")


@pytest.fixture()
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    with Session() as db:
        db.add(User(name="Admin", email=ADMIN[0], password_hash=hash_password(ADMIN[1]), role="admin"))
        db.commit()
    yield TestClient(app)
    app.dependency_overrides.clear()


def login(c, email, password):
    r = c.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture()
def admin(client):
    return login(client, *ADMIN)
