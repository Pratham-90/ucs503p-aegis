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

## Where this runs — the trust model changed (Week 2)

Under the [zero-knowledge trust model](../../docs/srs/index.md#23-trust-model),
**the live cryptography runs client-side (in the browser), not on the server.**
Key generation, payload encryption, the Shamir split, per-trustee share
encryption, and `K`-of-`N` reconstruction all happen on the Owner's and
trustees' devices (`FR-2`, `FR-2a`, `FR-8`). The server never holds the key, a
plaintext share, or the payload (`NFR-SEC-5`).

This Python package therefore is **not** the production crypto path. It serves
as:

- a **reference implementation** of the SSS math (the same algorithm the client
  must implement), and
- a **shared test-vector generator** — known (secret, shares) tuples used to
  cross-validate the client (JS/WASM) implementation so the two agree bit-for-bit.

## Reference surface (planned)

| Function | Responsibility |
| --- | --- |
| `split_secret(secret, n, k)` | Reference `n` shares with threshold `k`. |
| `reconstruct_secret(shares)` | Reference recovery from any `k` shares. |
| `test_vectors(...)` | Emit fixed (secret, shares) tuples for client cross-checks. |

Payload `encrypt`/`decrypt` are specified here but executed client-side; the
server stores only their ciphertext output.

## Status

Week 1: scaffold + a throwaway feasibility spike (`code/spikes/shamir_spike.py`).
Week 2: responsibility clarified — crypto is client-side; this package is the
reference + test vectors. Hardening (constant-time field arithmetic, CSPRNG,
authenticated encryption, share integrity/authenticity) is scheduled for
**Week 4**, and must hold for the *client* implementation.
