"""One-click check-in from the emailed link (FR-6, NFR-USE-1; threat T-5).

GET only *previews* the token (no side effects), so a mail scanner that pre-fetches
links cannot check in on the owner's behalf. The frontend page /checkin/:token
POSTs automatically on load, so opening the link is still the single action.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from scheduler.state import SchedulerError
from scheduler.tick import due_check
from vault.models import CheckInToken, Vault
from vault.repository import apply_check_in, hash_token, lock_vault

from ..config import Settings
from ..deps import get_session, get_settings, server_now
from ..errors import APIError

router = APIRouter(tags=["check-in"])


def _token(session: Session, token: str) -> CheckInToken:
    row = session.execute(select(CheckInToken).where(CheckInToken.token_hash == hash_token(token))).scalar_one_or_none()
    if row is None:
        raise APIError(404, "token_not_found", "This check-in link is not valid.")
    return row


@router.get("/checkin/{token}")
def preview(token: str, session: Session = Depends(get_session), settings: Settings = Depends(get_settings)):
    row = _token(session, token)
    now = server_now(session, settings)
    vault = session.get(Vault, row.vault_id)
    status = "used" if row.used_at else "expired" if now >= row.expires_at else "valid"
    return {"status": status, "vault_state": vault.state, "expires_at": row.expires_at.isoformat()}


@router.post("/checkin/{token}")
def confirm(token: str, session: Session = Depends(get_session), settings: Settings = Depends(get_settings)):
    row = _token(session, token)
    now = server_now(session, settings)
    if row.used_at:
        raise APIError(409, "token_used", "This check-in link has already been used.")
    if now >= row.expires_at:
        raise APIError(410, "token_expired", "This check-in link has expired.")
    vault = lock_vault(session, row.vault_id)
    due_check(session, vault.id, now, settings.app_base_url)
    try:
        apply_check_in(session, vault, now, "email-link")
    except SchedulerError as exc:
        raise APIError(409, "checkin_rejected", str(exc), state=vault.state) from exc
    row.used_at = now  # single use
    return {"status": "checked_in", "state": vault.state, "deadline_at": vault.deadline_at.isoformat()}
