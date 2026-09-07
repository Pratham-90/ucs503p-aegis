# `api` — HTTP application layer

The FastAPI app that ties Aegis together. It owns transport and validation, and
delegates every business rule to the domain packages (`crypto`, `scheduler`,
`vault`, `notifications`).

## Endpoint groups (planned)

| Group | Maps to |
| --- | --- |
| Auth | Registration / login (FR-1) |
| Vault | Create vault; accept **client-encrypted** ciphertext + `N` encrypted blobs (FR-2, FR-2a); configure timing (FR-3) |
| Trustees | Designate trustees, enrol their **public keys**, set threshold `K` (FR-4) |
| Check-in | One-action confirmation endpoint (FR-6) |
| Recovery | On release, **serve** the ciphertext + each trustee's blob (FR-7); reconstruction + decryption happen **client-side** (FR-8) — the server does no decryption |

## Responsibilities

- Define Pydantic request/response schemas and validate all input.
- Authenticate and authorize requests.
- Orchestrate calls into the domain packages; hold no persistence or crypto
  logic itself. Under the zero-knowledge model the API **never** receives a
  plaintext payload, key, or share, and performs no payload cryptography
  (`NFR-SEC-5`).

## Status

Week 1: **scaffold only**. Framework: FastAPI. Frontend (React + Tailwind) is a
separate concern documented in the architecture diagram.
