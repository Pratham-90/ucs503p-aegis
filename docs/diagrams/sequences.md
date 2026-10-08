# Sequence diagrams

How the prototype carries out the two flows that matter, end to end. Everything
inside a browser box happens on the client; only ciphertext and encrypted blobs
ever reach the server (`NFR-SEC-5`).

## Create and seal a vault (FR-1 … FR-4, FR-2a)

```mermaid
sequenceDiagram
    autonumber
    actor Owner as Owner browser
    participant API as FastAPI (Vercel function)
    participant DB as Postgres
    actor Trustee as Trustee browser
    Owner->>API: POST /api/vaults (trustee emails, K, interval, grace)
    API->>API: validate FR-4 (reject K below 2, warn at K = N)
    API->>DB: vault in Setup + trustees (invite token hashes only)
    API->>DB: outbox: invite emails
    API-->>Owner: invite links
    Owner-->>Trustee: invite link (email / shared)
    Trustee->>Trustee: generate RSA-OAEP-2048 keypair (Web Crypto)
    Trustee->>API: POST /api/trustee/enrol/{token} (public JWK only)
    Trustee->>Trustee: download private key file (never uploaded)
    Owner->>API: GET /api/vaults/mine (poll until every trustee enrolled)
    Note over Owner: random 256-bit key, AES-256-GCM(payload),<br/>Shamir split (K of N), RSA-OAEP wrap each share
    Owner->>API: POST /api/vaults/{id}/payload (ciphertext, IV, N blobs)
    API->>DB: store ciphertext + blobs, state = Active, deadline = now + interval
    API-->>Owner: server view (ciphertext only)
```

## Release and recover (FR-5 … FR-8)

```mermaid
sequenceDiagram
    autonumber
    participant Cron as Tick trigger (GitHub Actions / button / status read)
    participant API as FastAPI (Vercel function)
    participant DB as Postgres
    actor Owner as Owner
    actor T1 as Trustee 1 browser
    actor T2 as Trustee 2 browser
    Cron->>API: POST /api/cron/tick (X-Cron-Secret)
    API->>DB: SELECT due vaults FOR UPDATE SKIP LOCKED
    API->>API: evaluate(clock, now): Active to Warning
    API->>DB: outbox: check-in prompt (single-use token, dedupe key)
    API-->>Owner: email: check in
    Note over Owner: no response
    Cron->>API: tick (later)
    API->>API: evaluate: Grace, then Released only when now >= deadline + grace
    API->>DB: state = Released, outbox: one release email per trustee (dedupe)
    API-->>T1: email: vault released (magic link)
    API-->>T2: email: vault released (magic link)
    T1->>API: GET /api/trustee/blob/{token}
    T1->>T1: RSA-OAEP decrypt with private key file = share 1
    T2->>API: GET /api/trustee/blob/{token}
    T2->>T2: RSA-OAEP decrypt = share 2
    Note over T1,T2: Recovery Room (one browser): paste K shares
    T1->>API: GET /api/trustee/payload/{token} (ciphertext only)
    T1->>T1: Lagrange at 0 = key, AES-256-GCM decrypt = message + file
```

← Back to [Diagrams](index.md) · [architecture](architecture.md) · [data model](data-model.md)
