"""Generate code/crypto/test_vectors.json from the authoritative Python crypto.

The TypeScript client (frontend/src/crypto/*.test.ts) must reproduce every
vector; CI fails if the two implementations disagree (FR-2a, FR-8, NFR-SEC-2).

Shamir and AES-GCM vectors are fully deterministic (seeded). RSA-OAEP padding is
randomised by design, so its ciphertexts change on every regeneration; they are
still valid known-answer cases because the private key is included.

Usage:  python scripts/gen_test_vectors.py
"""

from __future__ import annotations

import json
import random
import sys
from datetime import UTC, datetime
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "code"))

from crypto.encoding import share_to_bytes, share_to_text  # noqa: E402
from crypto.envelope import aes_gcm_encrypt, rsa_generate_jwk_pair, rsa_oaep_encrypt, vault_aad  # noqa: E402
from crypto.shamir import PRIME, Share, reconstruct_secret, split_with_coefficients  # noqa: E402

VERSION = 1
OUT = ROOT / "code" / "crypto" / "test_vectors.json"
RSA_KEY_FILE = ROOT / "code" / "crypto" / "vector_rsa_key.json"  # test-only key, not a secret

SHAMIR_CASES = [  # (name, seed, k, n, secret source)
    ("k2n3-small-secret", 1, 2, 3, "small"),
    ("k2n3-256bit-key", 2, 2, 3, "key"),
    ("k3n5-256bit-key", 3, 3, 5, "key"),
    ("k5n7-256bit-key", 4, 5, 7, "key"),
    ("k3n3-max-secret", 5, 3, 3, "max"),
    ("k2n2-zero-secret", 6, 2, 2, "zero"),
]


def _hex(v: int) -> str:
    return format(v, "x")


def shamir_vector(name: str, seed: int, k: int, n: int, source: str) -> dict:
    rng = random.Random(seed)
    secret = {"small": 1234567, "key": rng.getrandbits(256), "max": PRIME - 1, "zero": 0}[source]
    coefficients = [secret] + [rng.randrange(PRIME) for _ in range(k - 1)]
    shares = split_with_coefficients(coefficients, n)
    reconstructions = []
    for subset in list(combinations(shares, k))[:4] + [tuple(shares)]:
        reconstructions.append({"xs": [s.x for s in subset], "secret_hex": _hex(reconstruct_secret(subset))})
    insufficient = []
    if k > 2:  # K-1 >= 2 shares can be interpolated, but give the wrong value
        subset = shares[: k - 1]
        insufficient.append({"xs": [s.x for s in subset], "value_hex": _hex(reconstruct_secret(subset)),
                             "equals_secret": reconstruct_secret(subset) == secret})
    return {
        "name": name, "seed": seed, "k": k, "n": n, "secret_hex": _hex(secret),
        "coefficients_hex": [_hex(c) for c in coefficients],
        "shares": [{"x": s.x, "y_hex": _hex(s.y), "bytes_hex": share_to_bytes(s).hex(),
                    "text": share_to_text(s)} for s in shares],
        "reconstructions": reconstructions,
        "insufficient": insufficient,
    }


def aes_vectors() -> list[dict]:
    rng = random.Random(1000)
    out = []
    for i, (vault_id, plaintext) in enumerate([
        ("vault-a", b""),
        ("vault-b", b"Aegis known-answer test"),
        ("00000000-0000-4000-8000-000000000001", '{"v":1,"message":"héllo ✓","file":null}'.encode()),
        ("vault-d", bytes(rng.getrandbits(8) for _ in range(1000))),
    ]):
        key = bytes(rng.getrandbits(8) for _ in range(32))
        iv = bytes(rng.getrandbits(8) for _ in range(12))
        aad = vault_aad(vault_id)
        _, ct = aes_gcm_encrypt(key, plaintext, aad, iv)
        out.append({"name": f"aes-gcm-{i}", "key_hex": key.hex(), "iv_hex": iv.hex(), "aad_hex": aad.hex(),
                    "vault_id": vault_id, "plaintext_hex": plaintext.hex(), "ciphertext_hex": ct.hex()})
    return out


def rsa_vectors() -> list[dict]:
    if RSA_KEY_FILE.exists():
        keys = json.loads(RSA_KEY_FILE.read_text())
    else:
        public_jwk, private_jwk = rsa_generate_jwk_pair()
        keys = {"_note": "TEST-ONLY RSA key for cross-language vectors. Not a secret.",
                "public_jwk": public_jwk, "private_jwk": private_jwk}
        RSA_KEY_FILE.write_text(json.dumps(keys, indent=2) + "\n")
    out = []
    for i, share in enumerate([Share(1, 1), Share(255, PRIME - 1), Share(3, 987654321)]):
        plaintext = share_to_bytes(share)
        out.append({"name": f"rsa-oaep-{i}", "plaintext_hex": plaintext.hex(),
                    "ciphertext_hex": rsa_oaep_encrypt(keys["public_jwk"], plaintext).hex()})
    return [{"public_jwk": keys["public_jwk"], "private_jwk": keys["private_jwk"], "cases": out}]


def main() -> None:
    vectors = {
        "version": VERSION,
        "generated_by": "scripts/gen_test_vectors.py",
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "field": {"name": "GF(2^521 - 1)", "prime_hex": _hex(PRIME)},
        "formats": {"share_bytes": "0x01 || x (1 byte) || y (66 bytes, big-endian)",
                    "share_text": "aegis-share:v1:<x>:<y base64url, no padding>",
                    "aes_gcm": "ciphertext_hex = ciphertext || 16-byte tag; aad = 'aegis-vault:v1:<vault_id>'",
                    "rsa": "RSA-OAEP, 2048-bit, SHA-256 / MGF1-SHA-256, no label"},
        "shamir": [shamir_vector(*case) for case in SHAMIR_CASES],
        "aes_gcm": aes_vectors(),
        "rsa_oaep": rsa_vectors(),
    }
    OUT.write_text(json.dumps(vectors, indent=2) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)}: {len(vectors['shamir'])} shamir, "
          f"{len(vectors['aes_gcm'])} aes-gcm, {len(vectors['rsa_oaep'][0]['cases'])} rsa-oaep vectors")


if __name__ == "__main__":
    main()
