# `api` — HTTP application layer

The FastAPI app that ties Aegis together. It owns transport and validation, and
delegates every business rule to the domain packages (`crypto`, `scheduler`,
`vault`, `notifications`).

## Endpoint groups (planned)

| Group | Maps to |
| --- | --- |
| Auth | Registration / login (FR-1) |
| Vault | Create vault, upload payload (FR-2), configure timing (FR-3) |
| Trustees | Designate trustees, set threshold `K` (FR-4) |
| Check-in | One-action confirmation endpoint (FR-6) |
| Recovery | Trustee share submission, K-of-N reconstruct + decrypt (FR-8) |

## Responsibilities

- Define Pydantic request/response schemas and validate all input.
- Authenticate and authorize requests.
- Orchestrate calls into the domain packages; hold no persistence or crypto
  logic itself.

## Status

Week 1: **scaffold only**. Framework: FastAPI. Frontend (React + Tailwind) is a
separate concern documented in the architecture diagram.
