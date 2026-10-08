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

## Prototype status

Implemented (all under `/api`, OpenAPI docs at `/api/docs`): `auth/register|login|logout`, `me`,
`vaults` (create, `mine`, `{id}/payload`, `{id}/checkin`, `{id}/server-view`, reissue invite),
`checkin/{token}` (GET previews, POST confirms — so link scanners cannot check in), `trustee/*`
(invite, enrol, vaults, blob, payload), `cron/tick` (POST with `X-Cron-Secret`, GET with Bearer for
Vercel Cron), `demo/*` (behind `X-Demo-Token`), `health`. Errors share one JSON shape.
Every route that reads a vault's status first runs a due-check, so state is current even
between ticks. Deployed through `api/index.py` (see `code/README.md`).
