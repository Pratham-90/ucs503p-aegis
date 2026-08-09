# High-level architecture

How the pieces fit. The React frontend talks to a FastAPI backend, which
delegates to four domain packages; persistence, scheduling, and email are the
external-facing edges.

```mermaid
flowchart TB
    subgraph client["Client"]
        ui["React + Tailwind<br/>web UI"]
    end

    subgraph backend["Backend — FastAPI (code/api)"]
        api["API layer<br/>auth · schemas · routing"]
        crypto["crypto<br/>Shamir SSS + payload encryption"]
        scheduler["scheduler<br/>check-in clock"]
        vault["vault<br/>models & repositories"]
        notif["notifications<br/>SMTP messaging"]
    end

    db[("SQLAlchemy<br/>SQLite dev / Postgres later")]
    jobs[("APScheduler<br/>persistent job store")]
    smtp(["SMTP server"])
    owner[["👤 Owner"]]
    trustee[["👤 Trustee"]]

    ui -- "HTTPS / REST" --> api
    api --> crypto
    api --> vault
    api --> scheduler
    api --> notif

    scheduler --> jobs
    scheduler --> crypto
    scheduler --> notif
    vault --> db

    notif --> smtp
    smtp -. "check-in prompt (FR-5)" .-> owner
    smtp -. "key share on release (FR-7)" .-> trustee
    owner -. "one-action check-in (FR-6)" .-> ui
    trustee -. "submit K shares (FR-8)" .-> ui

    classDef ext fill:#e7f0ff,stroke:#3b6db5,color:#000;
    classDef store fill:#f0f0f0,stroke:#888,color:#000;
    class smtp,owner,trustee ext;
    class db,jobs store;
```

## Component responsibilities

| Component | Responsibility | Package |
| --- | --- | --- |
| Web UI | Owner/trustee interactions, responsive web only (NG-2) | *(frontend)* |
| API layer | Transport, auth, validation, orchestration | `code/api` |
| crypto | Shamir split/reconstruct + payload encryption | `code/crypto` |
| scheduler | Deadlines, lifecycle transitions, release gate | `code/scheduler` |
| vault | Domain models & repositories | `code/vault` |
| notifications | Check-in prompts and share delivery over SMTP | `code/notifications` |

## Trust and data-flow notes

- The payload crosses the API only as ciphertext once sealed; the database
  stores ciphertext + metadata only (`NFR-SEC-1`).
- The plaintext key exists transiently in `crypto` during split (setup) and
  reconstruction (post-release) — never persisted.
- `scheduler` owns every path toward release and is backed by a persistent job
  store so deadlines survive restarts (`NFR-REL-2`).

← Back to the [SRS](../srs/index.md) · see also the
[use-case diagram](use-case.md) and [vault lifecycle](vault-lifecycle.md).
