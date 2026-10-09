"""Pydantic request/response models."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field, field_validator


class Credentials(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=256)


class OwnerOut(BaseModel):
    id: str
    email: str


class VaultCreate(BaseModel):
    """FR-3 (schedule) and FR-4 (trustees, threshold). Server-side checks mirror the UI."""

    trustee_emails: list[EmailStr] = Field(min_length=2)
    k: int
    interval_s: int = Field(gt=0)
    grace_s: int = Field(ge=0)
    warning_s: int | None = Field(default=None, ge=0)

    @field_validator("trustee_emails")
    @classmethod
    def _distinct(cls, emails: list[str]) -> list[str]:
        lowered = [e.lower() for e in emails]
        if len(set(lowered)) != len(lowered):
            raise ValueError("trustee emails must be distinct")
        return lowered


class TrusteeOut(BaseModel):
    id: str
    position: int
    email: str
    enrolled: bool
    enrolled_at: datetime | None


class InviteLink(BaseModel):
    trustee_id: str
    email: str
    link: str


class BlobIn(BaseModel):
    trustee_id: str
    x_index: int
    encrypted_share_b64: str


class PayloadIn(BaseModel):
    """Everything the browser uploads: ciphertext and wrapped shares only (FR-2, FR-2a, NFR-SEC-5)."""

    ciphertext_b64: str
    iv_b64: str
    meta: dict[str, Any] = Field(default_factory=dict)
    blobs: list[BlobIn]


class EnrolIn(BaseModel):
    public_key_jwk: dict[str, Any]


class ClockAdvance(BaseModel):
    seconds: int = Field(gt=0, le=30 * 86_400)
