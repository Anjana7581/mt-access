"""FastAPI entrypoint. Run: uvicorn app.main:app --reload"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import Base, engine
from .routers import (
    agent,
    applications,
    assignments,
    auth,
    clients,
    rdp_credentials,
    sessions,
)
from .seed import seed_admin


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.environment == "production" and (settings.secret_key == "change-me" or len(settings.secret_key) < 32):
        raise RuntimeError("Set a strong SECRET_KEY before running in production")
    Base.metadata.create_all(engine)   # prototype only; switch to Alembic migrations before production
    seed_admin()
    yield


app = FastAPI(title="MetaTrader Remote Access Management", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
                   allow_methods=["*"], allow_headers=["*"])

for r in (
    auth.router,
    clients.router,
    applications.router,
    assignments.router,
    sessions.router,
    sessions.agents_router,
    agent.router,
    rdp_credentials.router,
    rdp_credentials.client_router,
):
    app.include_router(r)


@app.get("/api/health")
def health():
    return {"status": "ok"}
