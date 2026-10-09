"""Repository functions: the only code that maps vault rows to scheduler clocks.

Keeping persistence here (Repository pattern) is what lets the same logic run on
SQLite and Postgres unchanged (NFR-PORT-1).
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from scheduler.state import Clock, VaultState, check_in

from .models import CheckIn, Trustee, Vault


def new_token() -> str:
    """A URL-safe random token (256 bits). Only its hash is ever stored."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def clock_of(vault: Vault) -> Clock:
    return Clock(VaultState(vault.state), vault.deadline_at, vault.interval_s, vault.grace_s, vault.warning_s)


def lock_vault(session: Session, vault_id: str) -> Vault | None:
    """Load a vault row for update (row lock on Postgres; SQLite holds BEGIN IMMEDIATE)."""
    return session.execute(select(Vault).where(Vault.id == vault_id).with_for_update()).scalar_one_or_none()


def trustee_by_token(session: Session, token: str) -> Trustee | None:
    """Resolve a trustee from their invite token or their release (magic-link) token."""
    h = hash_token(token)
    return session.execute(
        select(Trustee).where(or_(Trustee.invite_token_hash == h, Trustee.access_token_hash == h))
    ).scalar_one_or_none()


def apply_check_in(session: Session, vault: Vault, now: datetime, source: str) -> None:
    """Record a confirmed check-in (FR-6). Raises SchedulerError if it is too late or not armed.

    Callers must first run the due-check (``scheduler.tick.process_vault``) in the
    same transaction, so a vault already due for release is released, not saved.
    """
    updated = check_in(clock_of(vault), now)
    vault.state = updated.state.value
    vault.deadline_at = updated.deadline_at
    vault.last_checkin_at = now
    session.add(CheckIn(vault_id=vault.id, at=now, source=source))


def arm_vault(session: Session, vault: Vault, now: datetime) -> None:
    """Start the check-in clock once the encrypted payload is stored."""
    vault.state = VaultState.ACTIVE.value
    vault.armed_at = now
    vault.last_checkin_at = now
    vault.deadline_at = now + timedelta(seconds=vault.interval_s)
    session.add(CheckIn(vault_id=vault.id, at=now, source="arm"))
