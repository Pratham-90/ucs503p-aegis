"""Apply ``evaluate`` to the database: one transaction per tick (NFR-REL-1/2/3).

* Deadlines live in the database, so a restart loses nothing (NFR-REL-2): any
  process that calls ``tick`` resumes exactly where the last one stopped.
* Due vaults are loaded ``FOR UPDATE SKIP LOCKED`` on Postgres (SQLite takes the
  write lock up front with BEGIN IMMEDIATE), the release guard is evaluated on
  that locked row, and the state change + outbox rows commit together.
* ``OutboxEmail.dedupe_key`` is UNIQUE, e.g. ``release:<vault>:<trustee>``, so a
  release is recorded exactly once even under duplicate or racing ticks (NFR-REL-3).
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from notifications import templates
from notifications.outbox import queue_email
from vault.db import Database
from vault.models import CheckInToken, TickLog, Vault
from vault.repository import clock_of, hash_token, new_token

from .state import Action, VaultState, evaluate

ARMED_STATES = (VaultState.ACTIVE.value, VaultState.WARNING.value, VaultState.GRACE.value)


@dataclass
class Transition:
    vault_id: str
    from_state: str
    to_state: str
    actions: list[str]
    at: str


@dataclass
class TickResult:
    tick_id: str
    trigger: str
    vaults_checked: int
    transitions: list[Transition] = field(default_factory=list)
    duration_ms: float = 0.0


def _checkin_link(session: Session, vault: Vault, base_url: str, expires_at: datetime | None) -> str:
    token = new_token()
    session.add(CheckInToken(vault_id=vault.id, token_hash=hash_token(token), expires_at=expires_at))
    return f"{base_url}/checkin/{token}"


def process_vault(session: Session, vault: Vault, now: datetime, base_url: str) -> Transition | None:
    """Evaluate one (already locked) vault and apply the decision. Returns the transition, if any."""
    clock = clock_of(vault)
    decision = evaluate(clock, now)
    if not decision.changed:
        return None
    previous = vault.state
    vault.state = decision.new_state.value
    deadline_key = int(clock.deadline_at.timestamp())
    owner_email = vault.owner.email
    for action in decision.actions:
        if action is Action.SEND_CHECKIN_PROMPT:
            link = _checkin_link(session, vault, base_url, clock.release_at)
            subject, body = templates.checkin_prompt(link, clock.release_at)
            queue_email(session, to=owner_email, subject=subject, body=body, kind="checkin_prompt",
                        dedupe_key=f"prompt:{vault.id}:{deadline_key}", vault_id=vault.id, created_at=now)
        elif action is Action.SEND_GRACE_REMINDER:
            link = _checkin_link(session, vault, base_url, clock.release_at)
            subject, body = templates.grace_reminder(link, clock.release_at)
            queue_email(session, to=owner_email, subject=subject, body=body, kind="grace_reminder",
                        dedupe_key=f"grace:{vault.id}:{deadline_key}", vault_id=vault.id, created_at=now)
        elif action is Action.RELEASE:
            vault.released_at = now
            for blob in vault.blobs:
                blob.delivered_at = now
            for trustee in vault.trustees:
                token = new_token()
                trustee.access_token_hash = hash_token(token)
                subject, body = templates.release_notice(f"{base_url}/trustee?t={token}", vault.k)
                queue_email(session, to=trustee.email, subject=subject, body=body, kind="release",
                            dedupe_key=f"release:{vault.id}:{trustee.id}", vault_id=vault.id,
                            created_at=now)
    return Transition(vault.id, previous, vault.state, [a.value for a in decision.actions], now.isoformat())


def due_check(session: Session, vault_id: str, now: datetime, base_url: str) -> Transition | None:
    """Lazy due-check used when a status endpoint is read (tick trigger (c) in the brief)."""
    vault = session.execute(select(Vault).where(Vault.id == vault_id).with_for_update()).scalar_one_or_none()
    if vault is None or vault.state not in ARMED_STATES:
        return None
    return process_vault(session, vault, now, base_url)


def tick(db: Database, now: datetime, *, trigger: str, base_url: str) -> TickResult:
    """Process every vault whose next transition may be due. Idempotent: running it twice
    at the same instant changes nothing the second time."""
    started = time.perf_counter()
    with db.session() as session:
        query = (
            select(Vault)
            .where(Vault.state.in_(ARMED_STATES), Vault.deadline_at <= now)  # every threshold is >= deadline
            .order_by(Vault.deadline_at)
        )
        query = query.with_for_update(skip_locked=True) if db.is_postgres else query
        vaults = session.execute(query).scalars().all()
        transitions = [t for v in vaults if (t := process_vault(session, v, now, base_url)) is not None]
        duration = (time.perf_counter() - started) * 1000
        log = TickLog(trigger=trigger, started_at=now, finished_at=now + timedelta(milliseconds=duration),
                      vaults_checked=len(vaults), transitions_json=json.dumps([asdict(t) for t in transitions]))
        session.add(log)
        session.flush()
        return TickResult(log.id, trigger, len(vaults), transitions, round(duration, 3))
