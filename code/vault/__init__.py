"""Aegis :: vault — domain models and repositories.

Responsibilities:
    * Define the persistent domain entities: Owner, Vault, Payload (ciphertext
      + metadata), Trustee, Share, CheckIn event, and the vault's lifecycle
      state.
    * Provide repository interfaces that mediate all persistence, keeping
      SQLAlchemy details out of the crypto/scheduler/api layers.

Storage: SQLAlchemy over SQLite in development, Postgres later. The payload is
stored as ciphertext only; the plaintext key is never persisted here.

Week 1 status: scaffold only.
"""

__all__: list[str] = []
