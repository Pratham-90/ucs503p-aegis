"""Owner vault endpoints: create (FR-3, FR-4), upload ciphertext (FR-2, FR-2a), check in (FR-6)."""

from __future__ import annotations

import base64
import binascii
import json

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from crypto.shamir import ShamirError, validate_threshold
from notifications import templates
from notifications.outbox import queue_email
from scheduler.state import SchedulerError, VaultState
from scheduler.tick import due_check
from vault.models import Owner, ShareBlob, Trustee, Vault
from vault.repository import apply_check_in, arm_vault, hash_token, lock_vault, new_token

from ..config import Settings
from ..deps import current_owner, get_session, get_settings, server_now
from ..errors import APIError
from ..schemas import PayloadIn, VaultCreate
from ..views import server_view, threshold_advice, vault_summary

router = APIRouter(tags=["vaults"])
RSA_2048_BLOB_BYTES = 256


def _b64(value: str, what: str) -> bytes:
    try:
        return base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise APIError(422, "bad_base64", f"{what} is not valid base64.") from exc


def _owned(session: Session, owner: Owner, vault_id: str) -> Vault:
    vault = lock_vault(session, vault_id)
    if vault is None or vault.owner_id != owner.id:
        raise APIError(404, "vault_not_found", "No such vault.")
    return vault


@router.post("/vaults", status_code=201)
def create_vault(body: VaultCreate, owner: Owner = Depends(current_owner), session: Session = Depends(get_session),
                 settings: Settings = Depends(get_settings)):
    n = len(body.trustee_emails)
    try:
        validate_threshold(body.k, n)  # FR-4: rejects K < 2 and K > N
    except ShamirError as exc:
        raise APIError(422, "invalid_threshold", str(exc)) from exc
    if n > settings.max_trustees:
        raise APIError(422, "too_many_trustees", f"At most {settings.max_trustees} trustees in the prototype.")
    if body.interval_s < settings.min_interval_s:
        raise APIError(422, "interval_too_short",
                       f"The check-in interval must be at least {settings.min_interval_s} s"
                       + ("" if settings.demo_mode else " (1 day) outside DEMO_MODE") + ".")
    if body.warning_s is not None and body.warning_s > body.grace_s:
        raise APIError(422, "invalid_warning", "The warning window must lie within the grace period.")
    if owner.email in body.trustee_emails:
        raise APIError(422, "owner_as_trustee", "The owner cannot be their own trustee.")
    if session.execute(select(Vault.id).where(Vault.owner_id == owner.id)).first():
        raise APIError(409, "vault_exists", "This prototype supports one vault per owner (NG-3).")

    vault = Vault(owner_id=owner.id, k=body.k, n=n, interval_s=body.interval_s, grace_s=body.grace_s,
                  warning_s=body.warning_s, state=VaultState.SETUP.value)
    session.add(vault)
    session.flush()
    invites = []
    for position, email in enumerate(body.trustee_emails, start=1):
        token = new_token()
        trustee = Trustee(vault_id=vault.id, position=position, email=email, invite_token_hash=hash_token(token))
        session.add(trustee)
        session.flush()
        link = f"{settings.app_base_url}/trustee/enrol/{token}"
        subject, text = templates.trustee_invite(owner.email, link)
        queue_email(session, to=email, subject=subject, body=text, kind="invite",
                    dedupe_key=f"invite:{trustee.id}", vault_id=vault.id)
        invites.append({"trustee_id": trustee.id, "position": position, "email": email, "link": link})
    loss_tolerance, warnings = threshold_advice(body.k, n)
    return {"vault_id": vault.id, "invites": invites, "loss_tolerance": loss_tolerance, "warnings": warnings}


@router.get("/vaults/mine")
def my_vault(owner: Owner = Depends(current_owner), session: Session = Depends(get_session),
             settings: Settings = Depends(get_settings)):
    vault_id = session.execute(select(Vault.id).where(Vault.owner_id == owner.id)).scalar_one_or_none()
    if vault_id is None:
        return {"vault": None}
    now = server_now(session, settings)
    due_check(session, vault_id, now, settings.app_base_url)  # lazy tick trigger
    return {"vault": vault_summary(session, session.get(Vault, vault_id), now)}


@router.post("/vaults/{vault_id}/payload")
def upload_payload(vault_id: str, body: PayloadIn, owner: Owner = Depends(current_owner),
                   session: Session = Depends(get_session), settings: Settings = Depends(get_settings)):
    vault = _owned(session, owner, vault_id)
    if vault.state != VaultState.SETUP.value or vault.payload_ciphertext is not None:
        raise APIError(409, "already_uploaded", "The payload can be uploaded only once.")
    trustees = {t.id: t for t in vault.trustees}
    if not all(t.public_key_jwk for t in trustees.values()):
        raise APIError(409, "trustees_not_enrolled", "Every trustee must enrol a public key first.")
    ciphertext = _b64(body.ciphertext_b64, "ciphertext")
    iv = _b64(body.iv_b64, "iv")
    if len(iv) != 12:
        raise APIError(422, "bad_iv", "The AES-GCM IV must be 12 bytes.")
    if not 16 <= len(ciphertext) <= settings.max_ciphertext_bytes:
        raise APIError(413, "payload_too_large", f"Ciphertext must be at most {settings.max_ciphertext_bytes} bytes.")
    if sorted(b.trustee_id for b in body.blobs) != sorted(trustees):
        raise APIError(422, "bad_blobs", "Exactly one encrypted share per trustee is required.")
    meta = {k: v for k, v in body.meta.items() if k in ("v", "alg", "size_bytes", "has_file")}
    for blob in body.blobs:
        trustee = trustees[blob.trustee_id]
        if blob.x_index != trustee.position:
            raise APIError(422, "bad_x_index", "Each share's x-index must match its trustee's position.")
        data = _b64(blob.encrypted_share_b64, "encrypted share")
        if len(data) != RSA_2048_BLOB_BYTES:
            raise APIError(422, "bad_blob", "Each encrypted share must be one RSA-2048 OAEP block (256 bytes).")
        session.add(ShareBlob(vault_id=vault.id, trustee_id=trustee.id, x_index=blob.x_index, encrypted_share=data))
    vault.payload_ciphertext, vault.payload_iv = ciphertext, iv
    vault.payload_meta_json = json.dumps({**meta, "k": vault.k, "n": vault.n})
    now = server_now(session, settings)
    arm_vault(session, vault, now)  # the check-in clock starts now
    session.flush()
    return {"vault": vault_summary(session, vault, now), "server_view": server_view(vault)}


@router.post("/vaults/{vault_id}/checkin")
def check_in_now(vault_id: str, owner: Owner = Depends(current_owner), session: Session = Depends(get_session),
                 settings: Settings = Depends(get_settings)):
    vault = _owned(session, owner, vault_id)
    now = server_now(session, settings)
    due_check(session, vault_id, now, settings.app_base_url)  # a vault that is already due is released, not saved
    try:
        apply_check_in(session, vault, now, "dashboard")
    except SchedulerError as exc:
        raise APIError(409, "checkin_rejected", str(exc), state=vault.state) from exc
    session.flush()
    return {"vault": vault_summary(session, vault, now)}


@router.post("/vaults/{vault_id}/trustees/{trustee_id}/invite")
def reissue_invite(vault_id: str, trustee_id: str, owner: Owner = Depends(current_owner),
                   session: Session = Depends(get_session), settings: Settings = Depends(get_settings)):
    """Rotate an un-enrolled trustee's invite link (only hashes are stored, so links cannot be re-shown)."""
    vault = _owned(session, owner, vault_id)
    trustee = next((t for t in vault.trustees if t.id == trustee_id), None)
    if trustee is None:
        raise APIError(404, "trustee_not_found", "No such trustee.")
    if vault.state != VaultState.SETUP.value or trustee.public_key_jwk:
        raise APIError(409, "already_enrolled", "This trustee has already enrolled.")
    token = new_token()
    trustee.invite_token_hash = hash_token(token)
    return {"trustee_id": trustee.id, "email": trustee.email, "link": f"{settings.app_base_url}/trustee/enrol/{token}"}


@router.get("/vaults/{vault_id}/server-view")
def my_server_view(vault_id: str, owner: Owner = Depends(current_owner), session: Session = Depends(get_session)):
    return server_view(_owned(session, owner, vault_id))
