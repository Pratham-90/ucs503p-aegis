# `crypto` — secret-sharing algorithms & reference implementation

The cryptographic core of Aegis. Two concerns live here:

1. **Shamir's Secret Sharing (SSS).** The algorithmic heart of the project.
   A symmetric key is split into `N` shares over a finite field GF(p) (or
   GF(2^8)) such that:
   - any `K` shares reconstruct the key exactly (Lagrange interpolation), and
   - any `K-1` shares reveal *nothing* about the key (each subset of size
     `< K` is consistent with every possible secret).
2. **Payload encryption.** The vault payload is sealed with a symmetric cipher
   (authenticated encryption planned, e.g. AES-GCM) under the key that SSS
   protects. Ciphertext is what the `vault` layer persists — never plaintext.

## Two implementations, one specification (Week 2 trust model)

Under the [zero-knowledge trust model](../../docs/srs/index.md#23-trust-model),
the **deployed** cryptography runs client-side — key generation, payload
encryption, the Shamir split, per-trustee share encryption, and `K`-of-`N`
reconstruction all happen in the Owner's and trustees' browsers (`FR-2`,
`FR-2a`, `FR-8`); the server never holds the key, a plaintext share, or the
payload (`NFR-SEC-5`).

To keep that client crypto correct, Aegis uses **two implementations bound by
shared, versioned test vectors** — standard practice for cryptographic
libraries (known-answer tests across implementations):

1. **Python (`code/crypto`) — the authoritative specification and test oracle.**
   This is the algorithmic core of the project. It is fully **unit- and
   property-tested** (Python + Hypothesis) and carries the coverage obligation of
   `NFR-MAINT-1` (≥80% on this package). It defines what "correct" means.
2. **Test vectors — a committed, versioned artifact.** The Python package emits a
   file of known inputs and outputs (secrets, polynomial coefficients where
   applicable, shares, and reconstructions). It is checked into the repo and is a
   **Week-4 deliverable**.
3. **JavaScript — the deployment target.** The browser implementation consumes
   the *same* vectors in its own test suite and must reproduce them exactly.

The Python code is therefore not a throwaway reference: it is the specification
the deployed JavaScript is validated against.

## Public surface

| Function | Responsibility |
| --- | --- |
| `split_secret(secret, n, k)` | Authoritative `n` shares with threshold `k`. |
| `reconstruct_secret(shares)` | Authoritative recovery from any `k` shares. |
| `emit_test_vectors(...)` | Write the versioned known-answer vectors the JS must match. |
| `encrypt_payload` / `decrypt_payload` | Specify payload sealing; executed client-side, ciphertext stored server-side. |

## Status

Week 1: scaffold + a throwaway feasibility spike (`code/spikes/shamir_spike.py`).
Week 2: structure clarified — Python is the authoritative spec + test oracle, the
deployed crypto is JS, and the two are bound by shared test vectors.
Week 4: harden the Python core (constant-time field arithmetic, CSPRNG,
authenticated encryption, share integrity/authenticity), ship the property-test
suite, and emit the versioned test-vector artifact the JS validates against.
