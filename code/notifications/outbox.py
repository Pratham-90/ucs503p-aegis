"""Transactional outbox and delivery (FR-5, FR-7, NFR-REL-3).

Deciding to send an email = inserting an ``OutboxEmail`` row in the *same*
transaction as the state change. ``dedupe_key`` is UNIQUE, so the decision is
recorded exactly once even if two ticks race. Delivery happens after commit and
is at-least-once towards the provider (a crash between "sent" and "marked sent"
could resend); the in-app Outbox is the demo's source of truth.

``EmailSender`` is a Strategy: ``LogSender`` only marks rows (EMAIL_MODE=log);
``ResendSender`` also calls the Resend HTTP API (EMAIL_MODE=resend).
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from vault.models import OutboxEmail


def queue_email(session: Session, *, to: str, subject: str, body: str, kind: str,
                dedupe_key: str, vault_id: str | None = None) -> OutboxEmail | None:
    """Insert an outbox row unless one with ``dedupe_key`` exists. Returns the row or None."""
    if session.execute(select(OutboxEmail.id).where(OutboxEmail.dedupe_key == dedupe_key)).first():
        return None
    row = OutboxEmail(to=to, subject=subject, body=body, kind=kind, dedupe_key=dedupe_key, vault_id=vault_id)
    try:
        with session.begin_nested():
            session.add(row)
            session.flush()
    except IntegrityError:  # a concurrent transaction recorded it first
        return None
    return row


class EmailSender(Protocol):
    mode: str

    def send(self, email: OutboxEmail) -> None: ...


class LogSender:
    """Records the email in the outbox only — the demo reads it from /demo."""

    mode = "log"

    def send(self, email: OutboxEmail) -> None:
        email.status = "logged"
        email.sent_at = datetime.now(UTC)


class ResendSender:
    mode = "resend"

    def __init__(self, api_key: str, sender: str) -> None:
        self.api_key = api_key
        self.sender = sender

    def send(self, email: OutboxEmail) -> None:
        import httpx

        try:
            response = httpx.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"from": self.sender, "to": [email.to], "subject": email.subject, "text": email.body},
                timeout=10,
            )
            response.raise_for_status()
            email.status = "sent"
            email.sent_at = datetime.now(UTC)
        except Exception:  # keep the demo going; the in-app outbox still shows it
            email.status = "failed"


def sender_from_env() -> EmailSender:
    if os.environ.get("EMAIL_MODE", "log") == "resend" and os.environ.get("RESEND_API_KEY"):
        return ResendSender(os.environ["RESEND_API_KEY"], os.environ.get("EMAIL_FROM", "Aegis <onboarding@resend.dev>"))
    return LogSender()


def deliver_pending(session: Session, sender: EmailSender, limit: int = 50) -> int:
    rows = session.execute(
        select(OutboxEmail).where(OutboxEmail.status == "queued").order_by(OutboxEmail.created_at).limit(limit)
    ).scalars().all()
    for row in rows:
        sender.send(row)
    return len(rows)
