# `vault` — domain models & repositories

The persistence and domain layer. Everything the system remembers lives behind
this package's repositories, so the other layers never touch SQLAlchemy
directly.

## Entities (planned)

| Entity | Notes |
| --- | --- |
| `Owner` | Registered user who owns a vault. One vault per Owner in v1. |
| `Vault` | The container. Holds lifecycle state + timing configuration. |
| `Payload` | **Client-encrypted** ciphertext + non-secret metadata (filename, size, MIME). The server never sees the plaintext. |
| `Trustee` | A designated recipient; holds an **enrolled public key** (private key stays on their device). |
| `ShareBlob` | One Shamir share **encrypted under a trustee's public key**, stored server-side and delivered on release. The server never sees the plaintext share. |
| `CheckIn` | A recorded, confirmed check-in event with a timestamp. |

## Responsibilities

- Model the domain and its invariants (e.g. `2 <= K <= N` (FR-4), one active
  vault per Owner).
- Expose repositories (`OwnerRepository`, `VaultRepository`, …) as the only
  persistence entry points.
- Guarantee that everything persisted is **ciphertext or an encrypted blob** —
  the payload as client-side ciphertext, each share as a trustee-encrypted
  `ShareBlob`, and never the plaintext key or a plaintext share
  (`NFR-SEC-1`, `NFR-SEC-5`).

## Status

Week 1: **scaffold only**. Storage: SQLAlchemy — SQLite for development,
Postgres for later stages.
