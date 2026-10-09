"""Aegis :: crypto — authoritative Shamir's Secret Sharing and its encodings.

This package is the *specification and test oracle* for the client crypto
(see README.md). The deployed cryptography runs in the browser (FR-2, FR-2a,
FR-8, NFR-SEC-5); the TypeScript implementation must reproduce the shared
vectors in ``test_vectors.json``, which ``scripts/gen_test_vectors.py`` emits
from this package.

Modules:
    shamir    -- GF(2**521 - 1) split / reconstruct (FR-2a, FR-4, FR-8, NFR-SEC-2)
    encoding  -- key / share byte and text formats shared with the client
    envelope  -- AES-256-GCM sealing and RSA-OAEP wrapping (seed + vectors only)
"""

from .encoding import (
    int_to_key,
    key_to_int,
    share_from_bytes,
    share_from_text,
    share_to_bytes,
    share_to_text,
)
from .shamir import (
    MIN_THRESHOLD,
    PRIME,
    ShamirError,
    Share,
    reconstruct_secret,
    split_secret,
    validate_threshold,
)

__all__: list[str] = [
    "MIN_THRESHOLD",
    "PRIME",
    "Share",
    "ShamirError",
    "int_to_key",
    "key_to_int",
    "reconstruct_secret",
    "share_from_bytes",
    "share_from_text",
    "share_to_bytes",
    "share_to_text",
    "split_secret",
    "validate_threshold",
]
