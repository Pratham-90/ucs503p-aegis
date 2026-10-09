"""Shared fixtures: an in-memory database and a factory for armed vaults."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from vault.db import Database
from vault.models import Owner, ShareBlob, Trustee, Vault
from vault.repository import arm_vault, hash_token

T0 = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
BASE = "https://aegis.example"


@pytest.fixture
def db():
    database = Database("sqlite://")
    database.create_all()
    yield database
    database.dispose()


def make_vault(db: Database, *, email="owner@example.com", k=2, n=3, interval=120, grace=60,
               warning=None, armed_at=T0) -> str:
    """Create an owner + vault with N enrolled trustees and encrypted blobs, armed at ``armed_at``."""
    with db.session() as s:
        owner = Owner(email=email, password_hash="x")
        vault = Vault(owner=owner, k=k, n=n, interval_s=interval, grace_s=grace, warning_s=warning,
                      payload_ciphertext=b"\x00" * 32, payload_iv=b"\x01" * 12, payload_meta_json="{}")
        s.add(vault)
        s.flush()
        for i in range(1, n + 1):
            t = Trustee(vault=vault, position=i, email=f"t{i}-{email}",
                        invite_token_hash=hash_token(f"inv-{email}-{i}"), public_key_jwk="{}", enrolled_at=armed_at)
            s.add(t)
            s.flush()
            s.add(ShareBlob(vault_id=vault.id, trustee_id=t.id, x_index=i, encrypted_share=b"\x02" * 256))
        arm_vault(s, vault, armed_at)
        return vault.id


def seconds(n: float) -> timedelta:
    return timedelta(seconds=n)
