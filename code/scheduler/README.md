# `scheduler` — the check-in clock

Owns time. This package turns the Owner's configured **check-in interval** and
**grace period** into scheduled deadlines and moves a vault through its
lifecycle when those deadlines pass.

## Lifecycle driven here

```
Active  --(interval elapses, prompt due)-->  Warning
Warning --(Owner confirms check-in)-------->  Active      (deadline reset)
Warning --(grace period elapses)----------->  Grace
Grace   --(grace expires, still no check-in)-> Released    (shares distributed)
```

See the state diagram in `docs/diagrams/vault-lifecycle.md` for the full set of
triggers and guards.

## Responsibilities

- Schedule the next prompt when a vault becomes `Active` or is reset.
- Persist jobs so a process restart re-arms every pending deadline (no missed
  or duplicated releases).
- On grace expiry, invoke `crypto` share generation + `notifications`
  distribution exactly once.

## Critical constraint

The catastrophic failure mode is **releasing a vault early**. Every transition
toward `Released` must be gated on a real, persisted, elapsed deadline — never
on wall-clock drift, a race, or a retry. This is NFR-REL-1 in the SRS and the
primary focus of the scheduler's test suite.

## Status

Week 1: **scaffold only**. Planned engine: APScheduler with a persistent job
store.
