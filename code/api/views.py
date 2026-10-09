"""Serialisers shared by the owner, trustee and demo endpoints."""

from __future__ import annotations

import base64
import json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from scheduler.state import VaultState
from vault.models import CheckIn, Vault
from vault.repository import clock_of


def iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


def threshold_advice(k: int, n: int) -> tuple[int, list[str]]:
    """FR-4: loss tolerance N - K, and the K = N warning."""
    warnings = []
    if k == n:
        warnings.append(
            "K equals N: the vault becomes unrecoverable if any single trustee loses their key or is unreachable."
        )
    return n - k, warnings


def vault_summary(session: Session, vault: Vault, now: datetime) -> dict:
    clock = clock_of(vault)
    loss_tolerance, warnings = threshold_advice(vault.k, vault.n)
    checkins = session.execute(
        select(CheckIn).where(CheckIn.vault_id == vault.id).order_by(CheckIn.at.desc()).limit(10)
    ).scalars().all()
    armed = vault.state != VaultState.SETUP.value
    return {
        "id": vault.id,
        "state": vault.state,
        "k": vault.k,
        "n": vault.n,
        "loss_tolerance": loss_tolerance,
        "warnings": warnings,
        "interval_s": vault.interval_s,
        "grace_s": vault.grace_s,
        "warning_s": clock.effective_warning_s,
        "deadline_at": iso(vault.deadline_at) if armed else None,
        "grace_starts_at": iso(clock.grace_starts_at) if armed else None,
        "release_at": iso(clock.release_at) if armed else None,
        "last_checkin_at": iso(vault.last_checkin_at),
        "armed_at": iso(vault.armed_at),
        "released_at": iso(vault.released_at),
        "payload_uploaded": vault.payload_ciphertext is not None,
        "all_enrolled": all(t.public_key_jwk for t in vault.trustees),
        "trustees": [
            {"id": t.id, "position": t.position, "email": t.email, "enrolled": t.public_key_jwk is not None,
             "enrolled_at": iso(t.enrolled_at),
             "public_key_jwk": json.loads(t.public_key_jwk) if t.public_key_jwk else None}
            for t in vault.trustees
        ],
        "checkins": [{"at": iso(c.at), "source": c.source} for c in checkins],
        "server_now": iso(now),
    }


def _bytes_view(data: bytes | None, keep: int = 48) -> dict | None:
    if data is None:
        return None
    encoded = base64.b64encode(data).decode()
    return {"length_bytes": len(data), "base64_preview": encoded[:keep] + ("…" if len(encoded) > keep else "")}


def server_view(vault: Vault) -> dict:
    """The raw stored row, as the server holds it (ciphertext truncated for display)."""
    return {
        "table": "vault",
        "row": {
            "id": vault.id, "owner_id": vault.owner_id, "k": vault.k, "n": vault.n,
            "interval_s": vault.interval_s, "grace_s": vault.grace_s, "warning_s": vault.warning_s,
            "state": vault.state, "last_checkin_at": iso(vault.last_checkin_at),
            "deadline_at": iso(vault.deadline_at), "released_at": iso(vault.released_at),
            "payload_ciphertext": _bytes_view(vault.payload_ciphertext),
            "payload_iv": _bytes_view(vault.payload_iv),
            "payload_meta_json": json.loads(vault.payload_meta_json) if vault.payload_meta_json else None,
            "created_at": iso(vault.created_at),
        },
        "share_blobs": [
            {"trustee_id": b.trustee_id, "x_index": b.x_index, "encrypted_share": _bytes_view(b.encrypted_share),
             "delivered_at": iso(b.delivered_at)}
            for b in sorted(vault.blobs, key=lambda b: b.x_index)
        ],
        "trustee_public_keys": [
            {"position": t.position, "email": t.email, "has_public_key": t.public_key_jwk is not None}
            for t in vault.trustees
        ],
        "never_received": ["the plaintext payload", "the AES key", "any plaintext share", "any trustee private key"],
    }
