"""Operational endpoints: cron tick, Demo Console, health."""

from __future__ import annotations

import json
import os
from dataclasses import asdict
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from notifications.outbox import EmailSender, deliver_pending
from scheduler.tick import tick
from vault.db import Database
from vault.models import AppSetting, OutboxEmail, Owner, TickLog, Vault

from ..config import Settings
from ..deps import (
    CLOCK_OFFSET_KEY,
    clock_offset,
    get_db,
    get_session,
    get_settings,
    require_cron,
    require_demo_admin,
    server_now,
)
from ..errors import APIError
from ..schemas import ClockAdvance
from ..views import iso, server_view

router = APIRouter()


def run_tick(db: Database, settings: Settings, sender: EmailSender, trigger: str) -> dict:
    with db.session() as s:
        now = server_now(s, settings)
    result = tick(db, now, trigger=trigger, base_url=settings.app_base_url)
    with db.session() as s:
        delivered = deliver_pending(s, sender)
    return {**asdict(result), "now": now.isoformat(), "emails_delivered": delivered}


# --- cron ----------------------------------------------------------------------------

@router.post("/cron/tick", tags=["scheduler"], dependencies=[Depends(require_cron)])
def cron_tick(request: Request, db: Database = Depends(get_db), settings: Settings = Depends(get_settings)):
    """GitHub Actions every 5 minutes (header X-Cron-Secret)."""
    return run_tick(db, settings, request.app.state.sender, "github-actions")


@router.get("/cron/tick", tags=["scheduler"], dependencies=[Depends(require_cron)])
def vercel_cron_tick(request: Request, db: Database = Depends(get_db), settings: Settings = Depends(get_settings)):
    """Vercel Cron backstop (GET with ``Authorization: Bearer $CRON_SECRET``)."""
    return run_tick(db, settings, request.app.state.sender, "vercel-cron")


# --- Demo Console --------------------------------------------------------------------

demo = APIRouter(prefix="/demo", tags=["demo"], dependencies=[Depends(require_demo_admin)])


@demo.post("/tick")
def demo_tick(request: Request, db: Database = Depends(get_db), settings: Settings = Depends(get_settings)):
    return run_tick(db, settings, request.app.state.sender, "demo-button")


@demo.get("/outbox")
def demo_outbox(limit: int = Query(100, le=500), session: Session = Depends(get_session)):
    rows = session.execute(select(OutboxEmail).order_by(OutboxEmail.created_at.desc()).limit(limit)).scalars()
    return {"emails": [{"id": e.id, "to": e.to, "subject": e.subject, "body": e.body, "kind": e.kind,
                        "status": e.status, "vault_id": e.vault_id, "created_at": iso(e.created_at),
                        "sent_at": iso(e.sent_at)} for e in rows]}


@demo.get("/ticks")
def demo_ticks(limit: int = Query(50, le=500), session: Session = Depends(get_session)):
    rows = session.execute(select(TickLog).order_by(TickLog.started_at.desc()).limit(limit)).scalars()
    return {"ticks": [{"id": t.id, "trigger": t.trigger, "started_at": iso(t.started_at),
                       "finished_at": iso(t.finished_at), "vaults_checked": t.vaults_checked,
                       "transitions": json.loads(t.transitions_json)} for t in rows]}


@demo.get("/vaults")
def demo_vaults(session: Session = Depends(get_session)):
    rows = session.execute(select(Vault, Owner.email).join(Owner).order_by(Vault.created_at.desc())).all()
    return {"vaults": [{"id": v.id, "owner_email": email, "state": v.state, "k": v.k, "n": v.n,
                        "deadline_at": iso(v.deadline_at)} for v, email in rows]}


@demo.get("/server-view/{vault_id}")
def demo_server_view(vault_id: str, session: Session = Depends(get_session)):
    vault = session.get(Vault, vault_id)
    if vault is None:
        raise APIError(404, "vault_not_found", "No such vault.")
    return server_view(vault)


@demo.get("/clock")
def demo_clock(session: Session = Depends(get_session), settings: Settings = Depends(get_settings)):
    return {"offset_s": clock_offset(session, settings), "server_now": iso(server_now(session, settings)),
            "real_now": iso(datetime.now(UTC)), "demo_mode": settings.demo_mode}


def _require_demo_mode(settings: Settings) -> None:
    if not settings.demo_mode:
        raise APIError(403, "demo_mode_off", "Only available when DEMO_MODE=true.")


@demo.post("/clock/advance")
def demo_clock_advance(body: ClockAdvance, session: Session = Depends(get_session),
                       settings: Settings = Depends(get_settings)):
    """Fast-forward the server clock (DEMO_MODE only). It moves *time*, not the release rule."""
    _require_demo_mode(settings)
    row = session.get(AppSetting, CLOCK_OFFSET_KEY) or AppSetting(key=CLOCK_OFFSET_KEY, value="0")
    row.value = str(float(row.value) + body.seconds)
    session.add(row)
    session.flush()
    return {"offset_s": float(row.value), "server_now": iso(server_now(session, settings))}


@demo.post("/clock/reset")
def demo_clock_reset(session: Session = Depends(get_session), settings: Settings = Depends(get_settings)):
    _require_demo_mode(settings)
    row = session.get(AppSetting, CLOCK_OFFSET_KEY)
    if row:
        session.delete(row)
    return {"offset_s": 0.0}


@demo.post("/reset")
def demo_reset(request: Request, db: Database = Depends(get_db), settings: Settings = Depends(get_settings)):
    _require_demo_mode(settings)
    db.drop_all()
    db.create_all()
    return {"reset": True}


# --- health --------------------------------------------------------------------------

@router.get("/health", tags=["ops"])
def health(session: Session = Depends(get_session), settings: Settings = Depends(get_settings)):
    session.execute(text("SELECT 1"))
    return {"status": "ok", "database": session.get_bind().dialect.name, "email_mode": settings.email_mode,
            "demo_mode": settings.demo_mode, "git_sha": os.environ.get("VERCEL_GIT_COMMIT_SHA", "local")[:12],
            "server_now": iso(server_now(session, settings))}
