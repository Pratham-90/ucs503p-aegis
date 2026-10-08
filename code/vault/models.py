"""SQLAlchemy 2.x models (data model from the prototype brief, section 4.1).

Everything persisted for a vault is ciphertext, an encrypted blob, or
non-secret metadata (NFR-SEC-1, NFR-SEC-5). Tokens are stored only as SHA-256
hashes. All timestamps are UTC.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
    TypeDecorator,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(UTC)


def new_id() -> str:
    return str(uuid.uuid4())


class UTCDateTime(TypeDecorator):
    """Timezone-aware UTC datetimes on every backend (SQLite drops tzinfo)."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            if value.tzinfo is None:
                raise ValueError("naive datetime; use UTC-aware datetimes")
            value = value.astimezone(UTC)
        return value

    def process_result_value(self, value, dialect):
        if value is not None and value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value


class Base(DeclarativeBase):
    pass


class Owner(Base):
    __tablename__ = "owner"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))  # argon2id (NFR-SEC-3)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    vaults: Mapped[list[Vault]] = relationship(back_populates="owner")


class Vault(Base):
    __tablename__ = "vault"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    owner_id: Mapped[str] = mapped_column(ForeignKey("owner.id"), unique=True, index=True)  # NG-3: one per owner
    k: Mapped[int] = mapped_column(Integer)
    n: Mapped[int] = mapped_column(Integer)
    interval_s: Mapped[int] = mapped_column(Integer)
    grace_s: Mapped[int] = mapped_column(Integer)
    warning_s: Mapped[int | None] = mapped_column(Integer, nullable=True)
    state: Mapped[str] = mapped_column(String(16), default="setup", index=True)
    last_checkin_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    deadline_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True, index=True)
    released_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    armed_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    payload_ciphertext: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    payload_iv: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    payload_meta_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    owner: Mapped[Owner] = relationship(back_populates="vaults")
    trustees: Mapped[list[Trustee]] = relationship(back_populates="vault", order_by="Trustee.position")
    blobs: Mapped[list[ShareBlob]] = relationship(back_populates="vault")


class Trustee(Base):
    __tablename__ = "trustee"
    __table_args__ = (UniqueConstraint("vault_id", "email"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    vault_id: Mapped[str] = mapped_column(ForeignKey("vault.id"), index=True)
    position: Mapped[int] = mapped_column(Integer)  # 1..N, also the share's x-coordinate
    email: Mapped[str] = mapped_column(String(320))
    invite_token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    # Magic-link token minted at release and sent in the release email (hash only).
    access_token_hash: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    public_key_jwk: Mapped[str | None] = mapped_column(Text, nullable=True)
    enrolled_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    vault: Mapped[Vault] = relationship(back_populates="trustees")


class ShareBlob(Base):
    """One Shamir share, RSA-OAEP-encrypted to its trustee's public key in the browser."""

    __tablename__ = "share_blob"
    __table_args__ = (UniqueConstraint("vault_id", "trustee_id"), UniqueConstraint("vault_id", "x_index"))
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    vault_id: Mapped[str] = mapped_column(ForeignKey("vault.id"), index=True)
    trustee_id: Mapped[str] = mapped_column(ForeignKey("trustee.id"))
    x_index: Mapped[int] = mapped_column(Integer)
    encrypted_share: Mapped[bytes] = mapped_column(LargeBinary)
    delivered_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    vault: Mapped[Vault] = relationship(back_populates="blobs")


class CheckIn(Base):
    __tablename__ = "checkin"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    vault_id: Mapped[str] = mapped_column(ForeignKey("vault.id"), index=True)
    at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    source: Mapped[str] = mapped_column(String(16))  # "dashboard" | "email-link" | "arm"


class CheckInToken(Base):
    """Single-use, expiring, bound to one deadline (threat T-5)."""

    __tablename__ = "checkin_token"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    vault_id: Mapped[str] = mapped_column(ForeignKey("vault.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime)
    used_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)


class OutboxEmail(Base):
    """Every email the system decides to send. ``dedupe_key`` makes delivery exactly-once (NFR-REL-3)."""

    __tablename__ = "outbox_email"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    vault_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    to: Mapped[str] = mapped_column(String(320))
    subject: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(String(32))
    dedupe_key: Mapped[str] = mapped_column(String(200), unique=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    sent_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="queued")  # queued | logged | sent | failed


class TickLog(Base):
    __tablename__ = "tick_log"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    trigger: Mapped[str] = mapped_column(String(32))
    started_at: Mapped[datetime] = mapped_column(UTCDateTime)
    finished_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    vaults_checked: Mapped[int] = mapped_column(Integer, default=0)
    transitions_json: Mapped[str] = mapped_column(Text, default="[]")


class AppSetting(Base):
    """Small key/value store (used for the DEMO_MODE clock offset)."""

    __tablename__ = "app_setting"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text)
