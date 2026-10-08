"""FastAPI application factory. Every route lives under ``/api`` (same origin as the SPA)."""

from __future__ import annotations

import asyncio

from fastapi import FastAPI

from notifications.outbox import EmailSender, sender_from_env
from vault.db import Database

from . import errors
from .config import Settings
from .routes import auth, checkin, ops, trustee, vaults

TAGS = [
    {"name": "auth", "description": "Owner registration and login (FR-1, NFR-SEC-3)."},
    {"name": "vaults", "description": "Create a vault, upload ciphertext, check in (FR-2..FR-6)."},
    {"name": "check-in", "description": "One-click check-in links (FR-6, NFR-USE-1)."},
    {"name": "trustee", "description": "Enrolment, portal, encrypted blob after release (FR-4, FR-7, FR-8)."},
    {"name": "scheduler", "description": "Cron-triggered ticks (FR-5, FR-7, NFR-REL-*)."},
    {"name": "demo", "description": "Demo Console (requires X-Demo-Token)."},
    {"name": "ops", "description": "Health."},
]


def create_app(settings: Settings | None = None, db: Database | None = None,
               sender: EmailSender | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    if settings.cookie_secure and settings.jwt_secret == Settings.jwt_secret:
        raise RuntimeError("JWT_SECRET must be set for an HTTPS deployment.")
    app = FastAPI(title="Aegis API", version="0.1.0-prototype", openapi_tags=TAGS,
                  docs_url="/api/docs", openapi_url="/api/openapi.json", redoc_url=None)
    app.state.settings = settings
    app.state.db = db or Database(settings.database_url)
    app.state.schema_ready = False
    app.state.sender = sender or sender_from_env()
    errors.install(app)

    # FastAPI runs a sync dependency's setup, the endpoint and the dependency's teardown
    # (where the transaction commits) as separate hops into a 40-thread pool. If every
    # thread is blocked waiting for a database lock, the lock holder cannot get a thread
    # to commit and all requests stall until the lock timeout (found by the load test).
    # Capping in-flight requests well below the pool size always leaves threads free.
    gate = asyncio.Semaphore(settings.max_concurrent_requests)

    @app.middleware("http")
    async def _limit_concurrency(request, call_next):
        async with gate:
            return await call_next(request)

    for router in (auth.router, vaults.router, checkin.router, trustee.router, ops.router, ops.demo):
        app.include_router(router, prefix="/api")
    return app
