"""Payload sealing and share wrapping, mirroring the browser's Web Crypto calls.

In production these operations run **client-side** (FR-2, FR-2a, NFR-SEC-5);
the server never calls them. They exist in Python so that the seed script can
build a realistic demo vault and so that the test-vector generator can emit
known-answer cases (AES-256-GCM, RSA-OAEP-SHA-256) for the TypeScript client.

``cryptography`` is imported lazily: the API runtime does not depend on it.
"""

from __future__ import annotations

import json
import os
from typing import Any

from .encoding import b64url_decode, b64url_encode

IV_BYTES = 12
PAYLOAD_VERSION = 1


def vault_aad(vault_id: str) -> bytes:
    """Associated data that binds a ciphertext to its vault (prevents swapping)."""
    return f"aegis-vault:v1:{vault_id}".encode()


def aes_gcm_encrypt(key: bytes, plaintext: bytes, aad: bytes, iv: bytes | None = None) -> tuple[bytes, bytes]:
    """Return ``(iv, ciphertext || tag)`` — the same layout Web Crypto produces."""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    iv = iv if iv is not None else os.urandom(IV_BYTES)
    return iv, AESGCM(key).encrypt(iv, plaintext, aad)


def aes_gcm_decrypt(key: bytes, iv: bytes, ciphertext: bytes, aad: bytes) -> bytes:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    return AESGCM(key).decrypt(iv, ciphertext, aad)


def pack_payload(message: str, file: dict[str, Any] | None = None) -> bytes:
    """The plaintext envelope the client encrypts. File names live *inside* it,
    so the server stores no filename metadata (narrows threat T-3)."""
    return json.dumps(
        {"v": PAYLOAD_VERSION, "message": message, "file": file}, separators=(",", ":")
    ).encode()


# --- RSA-OAEP (trustee keypairs) -------------------------------------------------

def _int_b64(value: int) -> str:
    return b64url_encode(value.to_bytes((value.bit_length() + 7) // 8, "big"))


def _b64_int(text: str) -> int:
    return int.from_bytes(b64url_decode(text), "big")


def rsa_generate_jwk_pair(bits: int = 2048) -> tuple[dict[str, Any], dict[str, Any]]:
    """Generate an RSA-OAEP-256 keypair as (public JWK, private JWK)."""
    from cryptography.hazmat.primitives.asymmetric import rsa

    key = rsa.generate_private_key(public_exponent=65537, key_size=bits)
    priv = key.private_numbers()
    pub = priv.public_numbers
    public_jwk = {"kty": "RSA", "alg": "RSA-OAEP-256", "ext": True, "key_ops": ["encrypt"],
                  "n": _int_b64(pub.n), "e": _int_b64(pub.e)}
    private_jwk = {**public_jwk, "key_ops": ["decrypt"], "d": _int_b64(priv.d),
                   "p": _int_b64(priv.p), "q": _int_b64(priv.q), "dp": _int_b64(priv.dmp1),
                   "dq": _int_b64(priv.dmq1), "qi": _int_b64(priv.iqmp)}
    return public_jwk, private_jwk


def _oaep():
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding

    return padding.OAEP(mgf=padding.MGF1(hashes.SHA256()), algorithm=hashes.SHA256(), label=None)


def rsa_oaep_encrypt(public_jwk: dict[str, Any], data: bytes) -> bytes:
    from cryptography.hazmat.primitives.asymmetric import rsa

    key = rsa.RSAPublicNumbers(_b64_int(public_jwk["e"]), _b64_int(public_jwk["n"])).public_key()
    return key.encrypt(data, _oaep())


def rsa_oaep_decrypt(private_jwk: dict[str, Any], data: bytes) -> bytes:
    from cryptography.hazmat.primitives.asymmetric import rsa

    pub = rsa.RSAPublicNumbers(_b64_int(private_jwk["e"]), _b64_int(private_jwk["n"]))
    key = rsa.RSAPrivateNumbers(
        p=_b64_int(private_jwk["p"]), q=_b64_int(private_jwk["q"]), d=_b64_int(private_jwk["d"]),
        dmp1=_b64_int(private_jwk["dp"]), dmq1=_b64_int(private_jwk["dq"]),
        iqmp=_b64_int(private_jwk["qi"]), public_numbers=pub,
    ).private_key()
    return key.decrypt(data, _oaep())
