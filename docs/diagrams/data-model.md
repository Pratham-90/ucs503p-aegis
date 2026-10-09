# Data model

The SQLAlchemy model in `code/vault/models.py` (SQLite locally, Postgres on
Neon in deployment; `NFR-PORT-1`). Payload and shares exist only as ciphertext
and encrypted blobs; tokens are stored only as SHA-256 hashes; timestamps are UTC.

```mermaid
erDiagram
    OWNER ||--o| VAULT : owns
    VAULT ||--|{ TRUSTEE : designates
    VAULT ||--o{ SHARE_BLOB : stores
    TRUSTEE ||--o| SHARE_BLOB : "is sent"
    VAULT ||--o{ CHECKIN : records
    VAULT ||--o{ CHECKIN_TOKEN : issues
    VAULT ||--o{ OUTBOX_EMAIL : queues
    OWNER {
        string id PK
        string email UK
        string password_hash "argon2id"
    }
    VAULT {
        string id PK
        string owner_id FK "unique: one vault per owner (NG-3)"
        int k "2 to N (FR-4)"
        int n
        int interval_s
        int grace_s
        int warning_s "default grace / 2"
        string state "setup, active, warning, grace, released"
        datetime deadline_at
        datetime released_at
        bytes payload_ciphertext "AES-256-GCM"
        bytes payload_iv
        string payload_meta_json "non-secret"
    }
    TRUSTEE {
        string id PK
        string vault_id FK
        int position "= share x"
        string email
        string invite_token_hash UK
        string access_token_hash UK
        string public_key_jwk "RSA-OAEP-2048 public only"
    }
    SHARE_BLOB {
        string id PK
        string vault_id FK
        string trustee_id FK
        int x_index
        bytes encrypted_share "256-byte RSA-OAEP block"
        datetime delivered_at
    }
    CHECKIN {
        string id PK
        string vault_id FK
        datetime at
        string source
    }
    CHECKIN_TOKEN {
        string id PK
        string vault_id FK
        string token_hash UK
        datetime expires_at
        datetime used_at "single use"
    }
    OUTBOX_EMAIL {
        string id PK
        string dedupe_key UK "exactly-once (NFR-REL-3)"
        string kind
        string to
        string status
    }
    TICK_LOG {
        string id PK
        string trigger
        datetime started_at
        int vaults_checked
        string transitions_json
    }
```

← Back to [Diagrams](index.md) · [sequences](sequences.md)
