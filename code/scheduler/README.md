# `scheduler` — the check-in clock

Owns time. Turns the Owner's **check-in interval** and **grace period** (FR-3)
into deadlines and moves each vault through its lifecycle.

## Design (as built in the prototype)

| Piece | What it does | Requirement |
| --- | --- | --- |
| `state.evaluate(clock, now)` | **Pure function**: the vault's state at `now` and the actions owed. The *only* place release is decided. Moves forward only; catches up through missed transitions in order. | NFR-REL-1 |
| `state.check_in(clock, now)` | Back to Active with `deadline = now + interval`; refused at or after `deadline + grace`. | FR-6 |
| `tick.tick(db, now)` | Loads due vaults `FOR UPDATE SKIP LOCKED` (Postgres) / under `BEGIN IMMEDIATE` (SQLite), applies `evaluate`, writes the state change and outbox rows **in one transaction**, logs the tick. | NFR-REL-2, NFR-REL-3 |
| `tick.due_check(...)` | The same, for one vault, run when a status endpoint is read. | FR-5 |

```
Setup ──payload uploaded──► Active ──now ≥ D──► Warning ──now ≥ D + warning_s──► Grace ──now ≥ D + grace──► Released
                              ▲           (prompt)              (reminder)              (encrypted blobs)
                              └──────────── confirmed check-in (from Active / Warning / Grace) ──┘
```

`D` is the deadline (last check-in + interval). `warning_s` defaults to half the
grace period; the SRS leaves this boundary open, and placing it inside the grace
window keeps the release instant exactly `D + grace`.

## Why there is no APScheduler

The Week-1 plan named APScheduler, but Vercel functions do not keep a process
alive. Deadlines therefore live in the database (which also gives NFR-REL-2 for
free) and ticks are triggered from outside: GitHub Actions every 5 minutes,
the Demo Console "Run tick now" button, lazy due-checks on status reads, and a
daily Vercel Cron backstop.

## Exactly-once and never-early, tested

- `code/tests/test_scheduler_state.py` — exhaustive cases plus Hypothesis
  properties (release implies `now ≥ D + grace`; release owed at most once over
  non-monotone time).
- `code/tests/test_scheduler_tick.py` — duplicate ticks, a stale-snapshot race,
  four concurrent threads, restarts.
- `scripts/reliability_sim.py` — ≥ 1000 schedules with fault injection; results
  in `metrics/`. Timeliness (≤ 60 s) depends on the tick cadence: met at the
  requirement cadence, **not** met by the 5-minute cron alone.
