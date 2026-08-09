# `crypto` — key management & payload confidentiality

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

## Public surface (planned)

| Function | Responsibility |
| --- | --- |
| `split_secret(secret, n, k)` | Produce `n` shares with threshold `k`. |
| `reconstruct_secret(shares)` | Recover the secret from any `k` shares. |
| `encrypt_payload(plaintext, key)` | Seal a payload under a symmetric key. |
| `decrypt_payload(ciphertext, key)` | Open a payload once the key is recovered. |

## Status

Week 1: **scaffold only** — no implementation yet. A standalone feasibility
spike proving split/reconstruct lives at `code/spikes/shamir_spike.py` (clearly
marked throwaway). Hardening into production code (constant-time field
arithmetic, cryptographically secure randomness, authenticated encryption,
share integrity/authenticity) is scheduled for **Week 4**.
