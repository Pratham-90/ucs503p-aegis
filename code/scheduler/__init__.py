"""Aegis :: scheduler — the check-in clock.

Responsibilities:
    * ``state.evaluate(clock, now)``: a *pure* function that decides the vault's
      lifecycle state (Active -> Warning -> Grace -> Released) and the actions
      owed on the way. It is the only place release is decided (NFR-REL-1).
    * ``tick.tick(db, now)``: applies those decisions to the database in one
      transaction, with an idempotent outbox, so a release is recorded exactly
      once (NFR-REL-3) and deadlines survive restarts (NFR-REL-2).

Deployment note: Vercel functions do not keep a process alive, so there is no
APScheduler loop. Ticks are triggered by a GitHub Actions cron, a "Run tick now"
button, lazy due-checks on status reads, and a daily Vercel cron backstop.
"""

__all__: list[str] = []
