"""Hypothesis property tests for Shamir's Secret Sharing.

* any K (or more) shares reconstruct the secret            -- FR-8
* any K-1 shares are consistent with *every* candidate secret -- NFR-SEC-2
* K < 2 is rejected                                         -- FR-4
* share encodings round-trip                                -- FR-2a
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from crypto import (
    PRIME,
    ShamirError,
    Share,
    reconstruct_secret,
    share_from_bytes,
    share_from_text,
    share_to_bytes,
    share_to_text,
    split_secret,
)
from crypto.shamir import polynomial_from_points, split_with_coefficients

EXAMPLES = 200
field = st.integers(min_value=0, max_value=PRIME - 1)


@st.composite
def split_case(draw):
    k = draw(st.integers(min_value=2, max_value=7))
    n = draw(st.integers(min_value=k, max_value=9))
    secret = draw(field)
    coefficients = [secret] + draw(st.lists(field, min_size=k - 1, max_size=k - 1))
    return k, n, secret, split_with_coefficients(coefficients, n)


@settings(max_examples=EXAMPLES)
@given(case=split_case(), data=st.data())
def test_any_k_or_more_shares_reconstruct(case, data):
    k, n, secret, shares = case
    size = data.draw(st.integers(min_value=k, max_value=n), label="subset size")
    subset = data.draw(st.permutations(shares), label="order")[:size]
    assert reconstruct_secret(subset) == secret


@settings(max_examples=EXAMPLES)
@given(case=split_case(), candidate=field, data=st.data())
def test_k_minus_one_shares_are_consistent_with_every_candidate_secret(case, candidate, data):
    """For the K-1 shares an attacker holds and ANY candidate secret, there is a
    valid coefficient vector that the real split turns into exactly those shares.
    So the attacker's view is equally consistent with every secret (NFR-SEC-2)."""
    k, n, _secret, shares = case
    seen = data.draw(st.permutations(shares), label="order")[: k - 1]
    coefficients = polynomial_from_points(seen, zero_value=candidate)
    assert len(coefficients) == k  # degree <= K-1: a legitimate split polynomial
    assert coefficients[0] == candidate
    regenerated = {s.x: s.y for s in split_with_coefficients(coefficients, n)}
    assert all(regenerated[s.x] == s.y for s in seen)


@settings(max_examples=EXAMPLES)
@given(k=st.integers(min_value=-10, max_value=1), n=st.integers(min_value=-10, max_value=20),
       secret=field)
def test_threshold_below_two_is_always_rejected(k, n, secret):
    try:
        split_secret(secret, n, k)
    except ShamirError:
        return
    raise AssertionError("split accepted K < 2")


@settings(max_examples=EXAMPLES)
@given(x=st.integers(min_value=1, max_value=255), y=field)
def test_share_encodings_round_trip(x, y):
    share = Share(x, y)
    assert share_from_bytes(share_to_bytes(share)) == share
    assert share_from_text(share_to_text(share)) == share
