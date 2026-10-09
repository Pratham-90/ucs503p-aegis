"""Payload sealing and share wrapping, as performed client-side (FR-2, FR-2a, FR-8)."""

import json

import pytest
from cryptography.exceptions import InvalidTag

from crypto import Share, int_to_key, key_to_int, reconstruct_secret, share_from_bytes, share_to_bytes, split_secret
from crypto.envelope import (
    IV_BYTES,
    aes_gcm_decrypt,
    aes_gcm_encrypt,
    pack_payload,
    rsa_generate_jwk_pair,
    rsa_oaep_decrypt,
    rsa_oaep_encrypt,
    vault_aad,
)

KEY = bytes(range(32))


def test_aes_gcm_round_trip_and_layout():
    iv, ct = aes_gcm_encrypt(KEY, b"hello", vault_aad("v1"))
    assert len(iv) == IV_BYTES and len(ct) == len(b"hello") + 16  # ciphertext || 16-byte tag
    assert aes_gcm_decrypt(KEY, iv, ct, vault_aad("v1")) == b"hello"


def test_aes_gcm_detects_tampering_wrong_key_and_wrong_vault():
    iv, ct = aes_gcm_encrypt(KEY, b"secret", vault_aad("v1"))
    with pytest.raises(InvalidTag):
        aes_gcm_decrypt(KEY, iv, bytes([ct[0] ^ 1]) + ct[1:], vault_aad("v1"))
    with pytest.raises(InvalidTag):
        aes_gcm_decrypt(bytes(32), iv, ct, vault_aad("v1"))
    with pytest.raises(InvalidTag):
        aes_gcm_decrypt(KEY, iv, ct, vault_aad("v2"))  # ciphertext bound to its vault


def test_pack_payload_keeps_file_names_inside_the_ciphertext():
    payload = json.loads(pack_payload("hi", {"name": "will.pdf", "type": "application/pdf", "data": "AA"}))
    assert payload == {"v": 1, "message": "hi", "file": {"name": "will.pdf", "type": "application/pdf", "data": "AA"}}


@pytest.fixture(scope="module")
def trustee_keys():
    return [rsa_generate_jwk_pair() for _ in range(3)]


def test_rsa_oaep_wraps_a_share_for_one_trustee_only(trustee_keys):
    (pub_a, priv_a), (_pub_b, priv_b), _ = trustee_keys
    wrapped = rsa_oaep_encrypt(pub_a, share_to_bytes(Share(1, 123)))
    assert share_from_bytes(rsa_oaep_decrypt(priv_a, wrapped)) == Share(1, 123)
    with pytest.raises(ValueError):
        rsa_oaep_decrypt(priv_b, wrapped)
    assert pub_a["alg"] == "RSA-OAEP-256" and "d" not in pub_a


def test_full_client_flow_k_of_n(trustee_keys):
    """Encrypt -> split -> wrap per trustee -> unwrap -> reconstruct -> decrypt."""
    iv, ct = aes_gcm_encrypt(KEY, pack_payload("the vault"), vault_aad("vault-1"))
    shares = split_secret(key_to_int(KEY), n=3, k=2)
    blobs = [rsa_oaep_encrypt(pub, share_to_bytes(s)) for (pub, _), s in zip(trustee_keys, shares, strict=True)]
    recovered = [share_from_bytes(rsa_oaep_decrypt(priv, b)) for (_, priv), b in zip(trustee_keys, blobs, strict=True)]
    key = int_to_key(reconstruct_secret(recovered[1:]))  # any two trustees
    assert json.loads(aes_gcm_decrypt(key, iv, ct, vault_aad("vault-1")))["message"] == "the vault"
