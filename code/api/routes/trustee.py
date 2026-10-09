"""Trustee endpoints: enrolment (FR-4), portal, blob and ciphertext after release (FR-7, FR-8)."""

from __future__ import annotations

import base64
import json

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from crypto.encoding import b64url_decode
from scheduler.state import VaultState
from scheduler.tick import due_check
from vault.models import Trustee, Vault
from vault.repository import trustee_by_token

from ..config import Settings
from ..deps import get_session, get_settings, server_now
from ..errors import APIError
from ..schemas import EnrolIn
from ..views import iso

router = APIRouter(tags=["trustee"])
PRIVATE_JWK_FIELDS = {"d", "p", "q", "dp", "dq", "qi", "oth", "k"}


def _trustee(session: Session, token: str) -> Trustee:
    trustee = trustee_by_token(session, token)
    if trustee is None:
        raise APIError(404, "trustee_not_found", "This trustee link is not valid.")
    return trustee


def validate_public_jwk(jwk: dict) -> dict:
    """Accept only an RSA-2048 *public* key; refuse anything carrying private material."""
    if PRIVATE_JWK_FIELDS & set(jwk):
        raise APIError(422, "private_key_uploaded", "That is a private key. Only the public key may be uploaded.")
    if jwk.get("kty") != "RSA" or not isinstance(jwk.get("n"), str) or not isinstance(jwk.get("e"), str):
        raise APIError(422, "bad_public_key", "Expected an RSA public key in JWK form.")
    try:
        modulus = b64url_decode(jwk["n"])
    except ValueError as exc:
        raise APIError(422, "bad_public_key", "The key modulus is not base64url.") from exc
    if len(modulus) != 256:
        raise APIError(422, "bad_public_key", "Trustee keys must be RSA-2048.")
    if jwk.get("alg") not in (None, "RSA-OAEP-256"):
        raise APIError(422, "bad_public_key", "Trustee keys must be RSA-OAEP-256.")
    return {"kty": "RSA", "alg": "RSA-OAEP-256", "n": jwk["n"], "e": jwk["e"], "ext": True, "key_ops": ["encrypt"]}


@router.get("/trustee/invite/{token}")
def invite(token: str, session: Session = Depends(get_session)):
    trustee = _trustee(session, token)
    vault = trustee.vault
    return {"vault_id": vault.id, "trustee_email": trustee.email, "owner_email": vault.owner.email,
            "position": trustee.position,
            "enrolled": trustee.public_key_jwk is not None, "k": vault.k, "n": vault.n, "vault_state": vault.state,
            "can_enrol": vault.state == VaultState.SETUP.value}


@router.post("/trustee/enrol/{token}")
def enrol(token: str, body: EnrolIn, session: Session = Depends(get_session),
          settings: Settings = Depends(get_settings)):
    trustee = _trustee(session, token)
    if trustee.vault.state != VaultState.SETUP.value:
        raise APIError(409, "enrolment_closed", "The vault is already sealed; enrolment is closed.")
    trustee.public_key_jwk = json.dumps(validate_public_jwk(body.public_key_jwk))
    trustee.enrolled_at = server_now(session, settings)
    return {"enrolled": True, "position": trustee.position, "email": trustee.email}


@router.get("/trustee/vaults")
def my_vaults(t: str = Query(..., description="trustee invite or release token"),
              session: Session = Depends(get_session), settings: Settings = Depends(get_settings)):
    trustee = _trustee(session, t)
    now = server_now(session, settings)
    due_check(session, trustee.vault_id, now, settings.app_base_url)  # lazy tick trigger
    vault = session.get(Vault, trustee.vault_id)
    released = vault.state == VaultState.RELEASED.value
    return {"vaults": [{
        "vault_id": vault.id, "owner_email": vault.owner.email, "state": vault.state, "k": vault.k, "n": vault.n,
        "your_position": trustee.position, "your_email": trustee.email, "released_at": iso(vault.released_at),
        "blob_available": released, "server_now": iso(now),
    }]}


def _released_vault(session: Session, trustee: Trustee, settings: Settings) -> Vault:
    now = server_now(session, settings)
    due_check(session, trustee.vault_id, now, settings.app_base_url)
    vault = session.get(Vault, trustee.vault_id)
    if vault.state != VaultState.RELEASED.value:
        raise APIError(403, "not_released", "Nothing is available until the vault is released (NFR-REL-1).",
                       state=vault.state)
    return vault


@router.get("/trustee/blob/{token}")
def my_blob(token: str, session: Session = Depends(get_session), settings: Settings = Depends(get_settings)):
    trustee = _trustee(session, token)
    vault = _released_vault(session, trustee, settings)
    blob = next(b for b in vault.blobs if b.trustee_id == trustee.id)
    return {"vault_id": vault.id, "x_index": blob.x_index, "k": vault.k, "n": vault.n,
            "encrypted_share_b64": base64.b64encode(blob.encrypted_share).decode()}


@router.get("/trustee/payload/{token}")
def released_payload(token: str, session: Session = Depends(get_session), settings: Settings = Depends(get_settings)):
    """The vault ciphertext for the Recovery Room. Useless without K decrypted shares."""
    trustee = _trustee(session, token)
    vault = _released_vault(session, trustee, settings)
    return {"vault_id": vault.id, "k": vault.k, "n": vault.n, "iv_b64": base64.b64encode(vault.payload_iv).decode(),
            "ciphertext_b64": base64.b64encode(vault.payload_ciphertext).decode(),
            "meta": json.loads(vault.payload_meta_json or "{}")}

