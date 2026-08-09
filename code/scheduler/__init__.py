"""Aegis :: scheduler — the check-in clock.

Responsibilities:
    * Track each vault's check-in interval, warning window, and grace period.
    * Drive the vault lifecycle: Active -> Warning -> Grace -> Released, firing
      the transitions when their time triggers elapse.
    * Ask the ``notifications`` package to prompt the Owner, and — only after
      the grace period expires with no confirmed check-in — trigger share
      distribution to trustees.

Planned mechanism: APScheduler jobs persisted alongside the vault state, so a
restart never loses a pending deadline. This package owns the single most
safety-critical rule in Aegis: it must **never release a vault early**
(see NFR-REL-1 in the SRS).

Week 1 status: scaffold only.
"""

__all__: list[str] = []
