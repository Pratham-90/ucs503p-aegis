# `vault` — domain models & repositories

The persistence and domain layer. Everything the system remembers lives behind
this package's repositories, so the other layers never touch SQLAlchemy
directly.

## Entities (planned)

| Entity | Notes |
| --- | --- |
| `Owner` | Registered user who owns a vault. One vault per Owner in v1. |
| `Vault` | The container. Holds lifecycle state + timing configuration. |
| `Payload` | Encrypted blob (ciphertext) + metadata (filename, size, MIME). |
| `Trustee` | A designated recipient of a key share. |
| `Share` | One Shamir share, distributed to a trustee on release. |
| `CheckIn` | A recorded, confirmed check-in event with a timestamp. |

## Responsibilities

- Model the domain and its invariants (e.g. `1 <= K <= N`, one active vault
  per Owner).
- Expose repositories (`OwnerRepository`, `VaultRepository`, …) as the only
  persistence entry points.
- Guarantee the payload is stored **as ciphertext only** — the plaintext key
  is never written to the database (NFR-SEC-1).

## Status

Week 1: **scaffold only**. Storage: SQLAlchemy — SQLite for development,
Postgres for later stages.
