"""Shamir's Secret Sharing over GF(p), p = 2**521 - 1 (authoritative implementation).

This module is the specification that the TypeScript client crypto mirrors; the
two are bound by the shared vectors in ``test_vectors.json``.

Requirements: FR-2a (key splitting), FR-4 (K >= 2 is enforced here as well as in
the UI), FR-8 (K-of-N reconstruction), NFR-SEC-2 (any K-1 shares reveal nothing).

Hardened from ``code/spikes/shamir_spike.py``: parameter validation, a typed
``Share``, an injectable random source for deterministic test mode, and helpers
used by the property tests and the test-vector generator.
"""

from __future__ import annotations

import secrets
from collections.abc import Callable, Sequence
from dataclasses import dataclass

#: The 13th Mersenne prime. Large enough to hold a 256-bit key as one element.
PRIME: int = 2**521 - 1
#: Bytes needed to encode any field element (ceil(521 / 8)).
FIELD_BYTES: int = 66
#: x-coordinates are encoded in one byte, so at most 255 shares.
MAX_SHARES: int = 255
#: FR-4: a single trustee must never be able to open a vault.
MIN_THRESHOLD: int = 2

#: ``rand_below(p)`` must return a uniform integer in ``[0, p)``.
RandBelow = Callable[[int], int]


class ShamirError(ValueError):
    """Invalid parameters or malformed shares."""


@dataclass(frozen=True)
class Share:
    """One point ``(x, f(x))`` on the secret polynomial."""

    x: int
    y: int

    def __post_init__(self) -> None:
        if isinstance(self.x, bool) or not isinstance(self.x, int):
            raise ShamirError("share x must be an integer")
        if not 1 <= self.x <= MAX_SHARES:
            raise ShamirError(f"share x must be in 1..{MAX_SHARES}, got {self.x}")
        if isinstance(self.y, bool) or not isinstance(self.y, int):
            raise ShamirError("share y must be an integer")
        if not 0 <= self.y < PRIME:
            raise ShamirError("share y is not an element of the field")


def validate_threshold(k: int, n: int) -> None:
    """Reject configurations that FR-4 forbids (K < 2) or that cannot exist."""
    for name, value in (("K", k), ("N", n)):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ShamirError(f"{name} must be an integer")
    if k < MIN_THRESHOLD:
        raise ShamirError(f"threshold K must be at least {MIN_THRESHOLD} (FR-4), got {k}")
    if n < k:
        raise ShamirError(f"N must be at least K, got K={k}, N={n}")
    if n > MAX_SHARES:
        raise ShamirError(f"N must be at most {MAX_SHARES}, got {n}")


def _check_field_element(value: int, what: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value < PRIME:
        raise ShamirError(f"{what} must be an integer in [0, p)")


def eval_poly(coefficients: Sequence[int], x: int) -> int:
    """Evaluate ``sum(c_i * x**i) mod p`` by Horner's method."""
    acc = 0
    for c in reversed(coefficients):
        acc = (acc * x + c) % PRIME
    return acc


def split_with_coefficients(coefficients: Sequence[int], n: int) -> list[Share]:
    """Deterministic split for a given coefficient vector ``[secret, a1, ..., a(k-1)]``.

    Used by the test-vector generator and the property tests. Application code
    should call :func:`split_secret`, which draws the coefficients at random.
    """
    k = len(coefficients)
    validate_threshold(k, n)
    for i, c in enumerate(coefficients):
        _check_field_element(c, "the secret" if i == 0 else f"coefficient a{i}")
    # x = 0 is never used: f(0) is the secret itself.
    return [Share(x, eval_poly(coefficients, x)) for x in range(1, n + 1)]


def split_secret(
    secret: int, n: int, k: int, *, rand_below: RandBelow | None = None
) -> list[Share]:
    """Split ``secret`` into ``n`` shares, any ``k`` of which reconstruct it.

    ``rand_below`` defaults to :func:`secrets.randbelow` (a CSPRNG). Tests inject
    a seeded generator to make the split reproducible.
    """
    validate_threshold(k, n)
    _check_field_element(secret, "the secret")
    draw = rand_below or secrets.randbelow
    coefficients = [secret] + [draw(PRIME) for _ in range(k - 1)]
    return split_with_coefficients(coefficients, n)


def _validated_points(shares: Sequence[Share]) -> list[Share]:
    points = list(shares)
    for s in points:
        if not isinstance(s, Share):
            raise ShamirError("expected Share objects")
    xs = [s.x for s in points]
    if len(set(xs)) != len(xs):
        raise ShamirError("shares must have distinct x-coordinates")
    return points


def interpolate_at(shares: Sequence[Share], x: int) -> int:
    """Value at ``x`` of the unique polynomial of degree < len(shares) through the shares."""
    points = _validated_points(shares)
    if not points:
        raise ShamirError("at least one share is required")
    total = 0
    for i, si in enumerate(points):
        num, den = 1, 1
        for j, sj in enumerate(points):
            if i != j:
                num = num * (x - sj.x) % PRIME
                den = den * (si.x - sj.x) % PRIME
        total = (total + si.y * num * pow(den, -1, PRIME)) % PRIME
    return total


def reconstruct_secret(shares: Sequence[Share]) -> int:
    """Recover ``f(0)`` by Lagrange interpolation.

    The caller is responsible for supplying at least K shares: with fewer, the
    result is an unrelated field element (that is the threshold property, not a
    bug). Because K >= 2 always (FR-4), a single share is rejected outright.
    """
    points = _validated_points(shares)
    if len(points) < MIN_THRESHOLD:
        raise ShamirError(f"at least {MIN_THRESHOLD} shares are required")
    return interpolate_at(points, 0)


def polynomial_from_points(shares: Sequence[Share], zero_value: int) -> list[int]:
    """Coefficients of the unique degree-<=len(shares) polynomial with ``f(0) = zero_value``
    passing through every share.

    The K-1 secrecy property test uses it: given any K-1 shares and *any*
    candidate secret, it constructs coefficients that the real ``split`` code
    turns into exactly the same K-1 shares.
    """
    _check_field_element(zero_value, "the candidate secret")
    points = [(0, zero_value)] + [(s.x, s.y) for s in _validated_points(shares)]
    size = len(points)
    coefficients = [0] * size
    for i, (xi, yi) in enumerate(points):
        # Expand the Lagrange basis polynomial l_i(x) = prod_{j!=i} (x - xj)/(xi - xj).
        basis = [1]
        den = 1
        for j, (xj, _) in enumerate(points):
            if i == j:
                continue
            nxt = [0] * (len(basis) + 1)
            for d, c in enumerate(basis):
                nxt[d] = (nxt[d] - c * xj) % PRIME
                nxt[d + 1] = (nxt[d + 1] + c) % PRIME
            basis = nxt
            den = den * (xi - xj) % PRIME
        scale = yi * pow(den, -1, PRIME) % PRIME
        for d, c in enumerate(basis):
            coefficients[d] = (coefficients[d] + c * scale) % PRIME
    return coefficients
