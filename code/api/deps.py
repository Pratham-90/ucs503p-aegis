"""FastAPI dependencies: settings, DB session, the (demo-adjustable) clock, auth guards."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

from fastapi import Depends, Header, Request
from sqlalchemy.orm import Session

from vault.db import Database
from vault.models import AppSetting, Owner

from .config import Settings
from .errors import APIError
from .security import COOKIE_NAME, read_session_token, secrets_match

CLOCK_OFFSET_KEY = "demo_clock_offset_s"


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_db(request: Request) -> Database:
    db: Database = request.app.state.db
    if not request.app.state.schema_ready:  # serverless: create tables lazily, once per process
        db.create_all()
        request.app.state.schema_ready = True
    return db


def get_session(db: Database = Depends(get_db)) -> Iterator[Session]:
    with db.session() as session:
        yield session


def clock_offset(session: Session, settings: Settings) -> float:
    if not settings.demo_mode:
        return 0.0
    row = session.get(AppSetting, CLOCK_OFFSET_KEY)
    return float(row.value) if row else 0.0


def server_now(session: Session, settings: Settings) -> datetime:
    """Real UTC time, plus the demo fast-forward offset when DEMO_MODE is on."""
    return datetime.now(UTC) + timedelta(seconds=clock_offset(session, settings))


def current_owner(request: Request, session: Session = Depends(get_session),
                  settings: Settings = Depends(get_settings)) -> Owner:
    token = request.cookies.get(COOKIE_NAME)
    owner_id = read_session_token(token, settings) if token else None
    owner = session.get(Owner, owner_id) if owner_id else None
    if owner is None:
        raise APIError(401, "not_authenticated", "Please log in.")
    return owner


def require_demo_admin(x_demo_token: str | None = Header(default=None),
                       settings: Settings = Depends(get_settings)) -> None:
    if not secrets_match(x_demo_token, settings.demo_admin_token):
        raise APIError(403, "demo_token_required", "A valid X-Demo-Token header is required.")


def require_cron(x_cron_secret: str | None = Header(default=None), authorization: str | None = Header(default=None),
                 settings: Settings = Depends(get_settings)) -> None:
    bearer = authorization[7:] if authorization and authorization.startswith("Bearer ") else None
    if not (secrets_match(x_cron_secret, settings.cron_secret) or secrets_match(bearer, settings.cron_secret)):
        raise APIError(403, "cron_secret_required", "Invalid cron secret.")
