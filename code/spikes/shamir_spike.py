#!/usr/bin/env python3
# =====================================================================
#  THROWAWAY FEASIBILITY SPIKE  --  NOT PRODUCTION CODE
# ---------------------------------------------------------------------
#  Week 1, UCS503P / Aegis.  This script exists only to prove that a
#  hand-written Shamir's Secret Sharing scheme over a finite field can
#  split a symmetric key into N shares (threshold K) and reconstruct it
#  from any K shares, while K-1 shares reveal nothing.
#
#  It deliberately cuts corners (see code/spikes/README.md, "Hardening
#  for Week 4"). Do NOT import this into the application. The production
#  implementation will live in code/crypto/.
# =====================================================================

from __future__ import annotations

import secrets
from typing import List, Tuple

Share = Tuple[int, int]

# 13th Mersenne prime (2**521 - 1). Comfortably larger than a 256-bit
# key, so a symmetric key can be encoded as a single field element.
PRIME: int = 2**521 - 1


def _eval_poly(coeffs: List[int], x: int, prime: int) -> int:
    """Evaluate a polynomial (Horner's method) at x, modulo prime.

    coeffs[0] is the constant term (the secret); coeffs[i] multiplies x**i.
    """
    acc = 0
    for c in reversed(coeffs):
        acc = (acc * x + c) % prime
    return acc


def split_secret(secret: int, n: int, k: int, prime: int = PRIME) -> List[Share]:
    """Split ``secret`` into ``n`` shares such that any ``k`` reconstruct it."""
    if not 1 <= k <= n:
        raise ValueError("require 1 <= k <= n")
    if not 0 <= secret < prime:
        raise ValueError("secret must be a field element in [0, prime)")
    # Random degree-(k-1) polynomial with f(0) = secret.
    coeffs = [secret] + [secrets.randbelow(prime) for _ in range(k - 1)]
    # Evaluate at x = 1..n (never at x = 0, which would leak the secret).
    return [(x, _eval_poly(coeffs, x, prime)) for x in range(1, n + 1)]


def reconstruct_secret(shares: List[Share], prime: int = PRIME) -> int:
    """Recover f(0) from shares via Lagrange interpolation, modulo prime."""
    xs = [x for x, _ in shares]
    if len(set(xs)) != len(xs):
        raise ValueError("shares must have distinct x-coordinates")
    total = 0
    for i, (xi, yi) in enumerate(shares):
        num, den = 1, 1
        for j, (xj, _) in enumerate(shares):
            if i == j:
                continue
            num = (num * (-xj)) % prime      # product of (0 - xj)
            den = (den * (xi - xj)) % prime  # product of (xi - xj)
        lagrange_i = num * pow(den, -1, prime)  # modular inverse (Py 3.8+)
        total = (total + yi * lagrange_i) % prime
    return total % prime


# --- byte <-> field-element helpers (a key is bytes; the field is ints) ---

def int_from_bytes(b: bytes) -> int:
    return int.from_bytes(b, "big")


def int_to_bytes(i: int, length: int) -> bytes:
    return i.to_bytes(length, "big")


def _demo() -> None:
    print("=" * 60)
    print("Shamir's Secret Sharing -- feasibility spike")
    print("Field: GF(2**521 - 1)")
    print("=" * 60)

    # A 256-bit symmetric key, the kind Aegis will protect.
    key_bytes = secrets.token_bytes(32)
    secret = int_from_bytes(key_bytes)
    n, k = 5, 3
    print(f"\nKey (hex): {key_bytes.hex()}")
    print(f"Splitting into N={n} shares, threshold K={k}\n")

    shares = split_secret(secret, n, k)
    for x, y in shares:
        print(f"  share {x}: {hex(y)[:34]}...")

    # 1) Any K shares reconstruct the exact secret.
    subset_a = [shares[0], shares[2], shares[4]]  # x = 1,3,5
    subset_b = [shares[1], shares[2], shares[3]]  # x = 2,3,4
    rec_a = reconstruct_secret(subset_a)
    rec_b = reconstruct_secret(subset_b)
    print("\n[1] Reconstruct from two different K-subsets:")
    print(f"    subset {{1,3,5}} -> match: {rec_a == secret}")
    print(f"    subset {{2,3,4}} -> match: {rec_b == secret}")
    assert rec_a == secret and rec_b == secret
    assert int_to_bytes(rec_a, 32) == key_bytes

    # 2) K-1 shares do NOT determine the secret.
    #    Interpolating any 2 (= K-1) points yields some field element that
    #    is almost never the real secret; every candidate secret is equally
    #    consistent with those 2 points (information-theoretic security).
    rec_kminus1 = reconstruct_secret(shares[:2])
    print("\n[2] K-1 = 2 shares reveal nothing:")
    print(f"    value from 2 shares equals real secret? {rec_kminus1 == secret}")
    assert rec_kminus1 != secret

    print("\nRESULT: split/reconstruct verified; K-1 shares insufficient. [OK]")


if __name__ == "__main__":
    _demo()
