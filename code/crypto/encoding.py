"""Byte and text encodings shared with the TypeScript client (FR-2a, FR-8).

Formats (version 1):

* key        : 32 bytes (AES-256), as an integer big-endian for Shamir.
* share bytes: ``0x01 || x (1 byte) || y (66 bytes, big-endian)`` = 68 bytes.
  This is the plaintext that is RSA-OAEP-wrapped for a trustee (fits in the
  190-byte limit of RSA-2048/OAEP-SHA-256).
* share text : ``aegis-share:v1:<x>:<y as base64url, no padding>`` — what a
  trustee copies into the Recovery Room.
"""

from __future__ import annotations

import base64

from .shamir import FIELD_BYTES, ShamirError, Share

KEY_BYTES = 32
SHARE_VERSION = 1
SHARE_BYTES = 2 + FIELD_BYTES
SHARE_TEXT_PREFIX = "aegis-share:v1:"


def b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def b64url_decode(text: str) -> bytes:
    if any(c not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_" for c in text):
        raise ValueError("not base64url")
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def key_to_int(key: bytes) -> int:
    if len(key) != KEY_BYTES:
        raise ShamirError(f"key must be {KEY_BYTES} bytes")
    return int.from_bytes(key, "big")


def int_to_key(value: int) -> bytes:
    """Inverse of :func:`key_to_int`.

    A reconstruction from too few (or wrong) shares yields an essentially random
    field element, which almost never fits in 256 bits; that is reported here.
    """
    if not 0 <= value < 2 ** (8 * KEY_BYTES):
        raise ShamirError("reconstructed value is not a valid 256-bit key (too few or wrong shares)")
    return value.to_bytes(KEY_BYTES, "big")


def share_to_bytes(share: Share) -> bytes:
    return bytes([SHARE_VERSION, share.x]) + share.y.to_bytes(FIELD_BYTES, "big")


def share_from_bytes(data: bytes) -> Share:
    if len(data) != SHARE_BYTES or data[0] != SHARE_VERSION:
        raise ShamirError("malformed share bytes")
    return Share(data[1], int.from_bytes(data[2:], "big"))


def share_to_text(share: Share) -> str:
    return f"{SHARE_TEXT_PREFIX}{share.x}:{b64url_encode(share.y.to_bytes(FIELD_BYTES, 'big'))}"


def share_from_text(text: str) -> Share:
    text = text.strip()
    if not text.startswith(SHARE_TEXT_PREFIX):
        raise ShamirError("share text must start with 'aegis-share:v1:'")
    parts = text[len(SHARE_TEXT_PREFIX):].split(":")
    if len(parts) != 2 or not parts[0].isdigit():
        raise ShamirError("share text must look like aegis-share:v1:<x>:<y>")
    try:
        y_bytes = b64url_decode(parts[1])
    except ValueError as exc:
        raise ShamirError("share y is not valid base64url") from exc
    if len(y_bytes) != FIELD_BYTES:
        raise ShamirError(f"share y must decode to {FIELD_BYTES} bytes")
    return Share(int(parts[0]), int.from_bytes(y_bytes, "big"))
