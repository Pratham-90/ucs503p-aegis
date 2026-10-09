"""The committed test vectors must agree with the authoritative Python crypto.

The TypeScript client runs the same vectors (frontend/src/crypto/vectors.test.ts),
so between them these two suites pin both implementations to one answer.
"""

import json
from pathlib import Path

import pytest

from crypto import Share, reconstruct_secret, share_from_bytes, share_from_text, share_to_bytes, share_to_text
from crypto.envelope import aes_gcm_decrypt, aes_gcm_encrypt, rsa_oaep_decrypt
from crypto.shamir import PRIME, split_with_coefficients

VECTORS = json.loads((Path(__file__).resolve().parents[1] / "crypto" / "test_vectors.json").read_text())


def test_header():
    assert VECTORS["version"] == 1
    assert int(VECTORS["field"]["prime_hex"], 16) == PRIME


@pytest.mark.parametrize("case", VECTORS["shamir"], ids=lambda c: c["name"])
def test_shamir_vectors(case):
    coefficients = [int(c, 16) for c in case["coefficients_hex"]]
    shares = split_with_coefficients(coefficients, case["n"])
    for share, expected in zip(shares, case["shares"], strict=True):
        assert share == Share(expected["x"], int(expected["y_hex"], 16))
        assert share_to_bytes(share).hex() == expected["bytes_hex"]
        assert share_to_text(share) == expected["text"]
        assert share_from_text(expected["text"]) == share
        assert share_from_bytes(bytes.fromhex(expected["bytes_hex"])) == share
    by_x = {s.x: s for s in shares}
    for r in case["reconstructions"]:
        assert reconstruct_secret([by_x[x] for x in r["xs"]]) == int(r["secret_hex"], 16) == int(case["secret_hex"], 16)
    for r in case["insufficient"]:
        value = reconstruct_secret([by_x[x] for x in r["xs"]])
        assert value == int(r["value_hex"], 16) and r["equals_secret"] is False


@pytest.mark.parametrize("case", VECTORS["aes_gcm"], ids=lambda c: c["name"])
def test_aes_gcm_vectors(case):
    key, iv, aad = (bytes.fromhex(case[k]) for k in ("key_hex", "iv_hex", "aad_hex"))
    pt, ct = bytes.fromhex(case["plaintext_hex"]), bytes.fromhex(case["ciphertext_hex"])
    assert aes_gcm_encrypt(key, pt, aad, iv)[1] == ct
    assert aes_gcm_decrypt(key, iv, ct, aad) == pt


def test_rsa_oaep_vectors():
    group = VECTORS["rsa_oaep"][0]
    for case in group["cases"]:
        plaintext = rsa_oaep_decrypt(group["private_jwk"], bytes.fromhex(case["ciphertext_hex"]))
        assert plaintext.hex() == case["plaintext_hex"]
