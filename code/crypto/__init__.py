"""Aegis :: crypto — key-management and payload confidentiality core.

Responsibilities:
    * Shamir's Secret Sharing over a finite field: split a symmetric key
      into ``N`` shares such that any ``K`` reconstruct it and any ``K-1``
      reveal nothing (information-theoretic threshold secrecy).
    * Symmetric encryption/decryption of the vault payload with that key.

This package is the security boundary of the system: the plaintext key
exists only transiently in memory during split and reconstruction, and the
payload is never persisted in plaintext (see NFR-SEC-1 in the SRS).

Week 1 status: scaffold only. A throwaway feasibility spike for the Shamir
math lives at ``code/spikes/shamir_spike.py``; the production, hardened
implementation is scheduled for Week 4.
"""

__all__: list[str] = []
