"""Unit tests for the authoritative crypto package (FR-2a, FR-4, FR-8, NFR-SEC-2)."""

import random

import pytest

from crypto import (
    PRIME,
    ShamirError,
    Share,
    int_to_key,
    key_to_int,
    reconstruct_secret,
    share_from_bytes,
    share_from_text,
    share_to_bytes,
    share_to_text,
    split_secret,
    validate_threshold,
)
from crypto.encoding import SHARE_BYTES, b64url_decode, b64url_encode
from crypto.shamir import eval_poly, interpolate_at, polynomial_from_points, split_with_coefficients

KEY = bytes(range(32))


# --- split / reconstruct ----------------------------------------------------------

def test_known_polynomial_gives_known_shares():
    shares = split_with_coefficients([1234, 166, 94], n=5)
    assert [s.y for s in shares] == [eval_poly([1234, 166, 94], x) for x in range(1, 6)]
    assert shares[0] == Share(1, 1234 + 166 + 94)


@pytest.mark.parametrize("subset", [(0, 1), (0, 4), (2, 3), (1, 2, 4), (0, 1, 2, 3, 4)])
def test_any_k_or_more_shares_reconstruct(subset):
    secret = key_to_int(KEY)
    shares = split_secret(secret, n=5, k=2, rand_below=random.Random(7).randrange)
    assert reconstruct_secret([shares[i] for i in subset]) == secret


def test_k_minus_one_shares_do_not_reconstruct():
    secret = key_to_int(KEY)
    shares = split_secret(secret, n=5, k=3, rand_below=random.Random(1).randrange)
    assert reconstruct_secret(shares[:2]) != secret


def test_seeded_rng_is_reproducible_and_default_rng_is_not():
    a = split_secret(42, 4, 3, rand_below=random.Random(99).randrange)
    b = split_secret(42, 4, 3, rand_below=random.Random(99).randrange)
    assert a == b
    assert split_secret(42, 4, 3) != split_secret(42, 4, 3)  # CSPRNG coefficients differ


def test_order_of_shares_does_not_matter():
    shares = split_secret(5, 4, 3, rand_below=random.Random(3).randrange)
    assert reconstruct_secret(shares[3:0:-1]) == 5


# --- FR-4 validation --------------------------------------------------------------

@pytest.mark.parametrize("k,n", [(1, 3), (0, 3), (-1, 3), (1, 1)])
def test_threshold_below_two_is_rejected(k, n):
    with pytest.raises(ShamirError, match="at least 2"):
        validate_threshold(k, n)
    with pytest.raises(ShamirError):
        split_secret(1, n, k)


@pytest.mark.parametrize("k,n", [(3, 2), (2, 256), (True, 3), (2, 3.0)])
def test_impossible_or_ill_typed_configurations_are_rejected(k, n):
    with pytest.raises(ShamirError):
        validate_threshold(k, n)


def test_k_equal_n_is_allowed_by_the_crypto():
    # FR-4 *warns* at K = N (a UI concern); it is not a crypto error.
    shares = split_secret(9, 3, 3)
    assert reconstruct_secret(shares) == 9


@pytest.mark.parametrize("secret", [-1, PRIME, PRIME + 5])
def test_secret_must_be_a_field_element(secret):
    with pytest.raises(ShamirError):
        split_secret(secret, 3, 2)


def test_coefficients_must_be_field_elements():
    with pytest.raises(ShamirError, match="a1"):
        split_with_coefficients([1, PRIME], 3)


@pytest.mark.parametrize("x,y", [(0, 1), (256, 1), (1, -1), (1, PRIME), (True, 1), (1, 2.5)])
def test_malformed_shares_are_rejected(x, y):
    with pytest.raises(ShamirError):
        Share(x, y)


def test_reconstruct_rejects_duplicates_single_shares_and_junk():
    with pytest.raises(ShamirError, match="distinct"):
        reconstruct_secret([Share(1, 5), Share(1, 6)])
    with pytest.raises(ShamirError, match="at least 2"):
        reconstruct_secret([Share(1, 5)])
    with pytest.raises(ShamirError, match="Share objects"):
        reconstruct_secret([(1, 5), (2, 6)])
    with pytest.raises(ShamirError, match="at least one"):
        interpolate_at([], 0)


def test_polynomial_from_points_round_trips_through_split():
    shares = split_with_coefficients([10, 20, 30], 5)
    coeffs = polynomial_from_points(shares[:2], zero_value=10)
    assert coeffs == [10, 20, 30]


# --- encodings --------------------------------------------------------------------

def test_key_int_round_trip_and_range_check():
    assert int_to_key(key_to_int(KEY)) == KEY
    with pytest.raises(ShamirError):
        key_to_int(b"short")
    with pytest.raises(ShamirError, match="too few or wrong shares"):
        int_to_key(2**256)


def test_share_bytes_and_text_round_trip():
    share = Share(7, PRIME - 1)
    raw = share_to_bytes(share)
    assert len(raw) == SHARE_BYTES == 68 and raw[0] == 1
    assert share_from_bytes(raw) == share
    text = share_to_text(share)
    assert text.startswith("aegis-share:v1:7:")
    assert share_from_text(f"  {text}\n") == share


@pytest.mark.parametrize(
    "text",
    [
        "aegis-share:v2:1:AAAA",
        "aegis-share:v1:1",
        "aegis-share:v1:x:AAAA",
        "aegis-share:v1:1:AA AA",
        "aegis-share:v1:1:AAAA",  # wrong length
        "aegis-share:v1:0:" + b64url_encode(bytes(66)),  # x = 0
    ],
)
def test_malformed_share_text_is_rejected(text):
    with pytest.raises(ShamirError):
        share_from_text(text)


def test_malformed_share_bytes_are_rejected():
    with pytest.raises(ShamirError):
        share_from_bytes(b"\x01" * 10)
    with pytest.raises(ShamirError):
        share_from_bytes(b"\x02" + b"\x01" + bytes(66))


def test_b64url_rejects_non_alphabet():
    assert b64url_decode(b64url_encode(b"\xff\xfe")) == b"\xff\xfe"
    with pytest.raises(ValueError):
        b64url_decode("ab+/")
