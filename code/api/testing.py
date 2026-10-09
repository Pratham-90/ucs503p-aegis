"""A scripted "browser" for integration tests and measurement scripts.

It performs exactly the client-side steps of the demo (FR-2, FR-2a, FR-4, FR-8)
with the authoritative Python crypto, talking to the API over HTTP (a
``TestClient`` or an ``httpx.Client``). Every request body it sends is recorded,
so the zero-knowledge inspection can scan what the server actually received.
"""

from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass, field
from typing import Any

from crypto import int_to_key, key_to_int, reconstruct_secret, share_from_bytes, share_to_bytes, split_secret
from crypto.envelope import (
    aes_gcm_decrypt,
    aes_gcm_encrypt,
    pack_payload,
    rsa_generate_jwk_pair,
    rsa_oaep_decrypt,
    rsa_oaep_encrypt,
    vault_aad,
)


@dataclass
class ScriptedVault:
    vault_id: str
    owner_email: str
    message: str
    key: bytes
    trustee_tokens: list[str]
    trustee_private_jwks: list[dict[str, Any]]
    shares_bytes: list[bytes]
    sent_bodies: list[str] = field(default_factory=list)


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode()


class ScriptedBrowser:
    def __init__(self, client) -> None:
        self.client = client
        self.sent: list[str] = []

    def _post(self, url: str, payload: dict | None = None, **kw):
        if payload is not None:
            self.sent.append(json.dumps(payload))
        response = self.client.post(url, json=payload, **kw)
        return response

    def create_vault(self, *, owner_email: str, password: str, trustee_emails: list[str], k: int,
                     interval_s: int, grace_s: int, message: str, file: dict | None = None) -> ScriptedVault:
        r = self._post("/api/auth/register", {"email": owner_email, "password": password})
        if r.status_code == 409:
            r = self._post("/api/auth/login", {"email": owner_email, "password": password})
        r.raise_for_status()
        r = self._post("/api/vaults", {"trustee_emails": trustee_emails, "k": k, "interval_s": interval_s,
                                       "grace_s": grace_s})
        r.raise_for_status()
        created = r.json()
        vault_id = created["vault_id"]
        tokens, privates, publics = [], [], {}
        for invite in created["invites"]:
            token = invite["link"].rsplit("/", 1)[1]
            public_jwk, private_jwk = rsa_generate_jwk_pair()  # in the real app: in the trustee's browser
            self._post(f"/api/trustee/enrol/{token}", {"public_key_jwk": public_jwk}).raise_for_status()
            tokens.append(token)
            privates.append(private_jwk)
            publics[invite["trustee_id"]] = (invite["position"], public_jwk)

        key = os.urandom(32)  # the browser's AES-256 key; never sent
        plaintext = pack_payload(message, file)
        iv, ciphertext = aes_gcm_encrypt(key, plaintext, vault_aad(vault_id))
        shares = split_secret(key_to_int(key), n=len(trustee_emails), k=k)
        blobs, shares_bytes = [], []
        for trustee_id, (position, public_jwk) in publics.items():
            share = shares[position - 1]
            shares_bytes.append(share_to_bytes(share))
            blobs.append({"trustee_id": trustee_id, "x_index": share.x,
                          "encrypted_share_b64": _b64(rsa_oaep_encrypt(public_jwk, share_to_bytes(share)))})
        r = self._post(f"/api/vaults/{vault_id}/payload", {
            "ciphertext_b64": _b64(ciphertext), "iv_b64": _b64(iv),
            "meta": {"v": 1, "alg": "AES-256-GCM", "size_bytes": len(plaintext), "has_file": file is not None},
            "blobs": blobs})
        r.raise_for_status()
        return ScriptedVault(vault_id, owner_email, message, key, tokens, privates, shares_bytes, self.sent)

    def recover(self, vault: ScriptedVault, trustee_indexes: list[int]) -> dict:
        """Trustees decrypt their own blobs, then the Recovery Room reconstructs and decrypts."""
        shares = []
        for i in trustee_indexes:
            blob = self.client.get(f"/api/trustee/blob/{vault.trustee_tokens[i]}")
            blob.raise_for_status()
            raw = rsa_oaep_decrypt(vault.trustee_private_jwks[i], base64.b64decode(blob.json()["encrypted_share_b64"]))
            shares.append(share_from_bytes(raw))
        payload = self.client.get(f"/api/trustee/payload/{vault.trustee_tokens[trustee_indexes[0]]}")
        payload.raise_for_status()
        body = payload.json()
        key = int_to_key(reconstruct_secret(shares))
        plaintext = aes_gcm_decrypt(key, base64.b64decode(body["iv_b64"]), base64.b64decode(body["ciphertext_b64"]),
                                    vault_aad(vault.vault_id))
        return json.loads(plaintext)
