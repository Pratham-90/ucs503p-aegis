# Week 8 : Prototype Build

**Date:** 2026-10-08 · **Branch:** `prototype` · **Team:** Pratham Arora, Krishna Pandey, Nipun Behl

## Goal for the week

Build a working prototype of Aegis that runs the 5-minute demo script from the
team's prototype brief (`AEGIS_PROTOTYPE_BRIEF.md`), deployable on Vercel, with
real measurements for the prototype report.

## How the work was done

The implementation on the `prototype` branch was produced with an AI coding
assistant (Claude Code) working from the team's brief; every such commit carries
a `Co-Authored-By` trailer. The team's own contributions this week are recorded
below.

**Who did what:** TODO (team to fill in: review, testing on devices, demo
rehearsal, report writing, deployment).

## What was built

- **Authoritative Python crypto** (`code/crypto`): GF(2^521 − 1) Shamir with
  validation, share encodings, AES-GCM and RSA-OAEP helpers; Hypothesis property
  tests; `test_vectors.json` shared with the client.
- **TypeScript client crypto** (`frontend/src/crypto`): BigInt Shamir, Web Crypto
  AES-256-GCM and RSA-OAEP-2048; reproduces all 13 Python vectors.
- **Scheduler**: a pure `evaluate(clock, now)` and a transactional `tick()` with an
  idempotent outbox (exactly-once release). No APScheduler: ticks are triggered
  by GitHub Actions, a Demo Console button, lazy due-checks and a daily Vercel Cron.
- **FastAPI backend** (`code/api`) and **React frontend**: register/login,
  vault wizard with FR-4 validation, trustee enrolment with browser-generated
  keys, one-click check-in, trustee portal, client-side Recovery Room, Demo Console.
- **Tests and measurements**: 125 Python tests, 22 TypeScript tests, a Playwright
  run of the whole demo script (22 screenshots), a 1000-schedule reliability
  simulator, a zero-knowledge inspection, a check-in load test, crypto timings —
  all collected into `metrics/prototype-metrics.json`.
- **Deployment config** for Vercel (`vercel.json`, `api/index.py`) and CI
  (`.github/workflows/ci.yml`, `tick.yml`).

## Decisions

- **Classic Vercel layout** (static Vite build + file-based Python function, one
  origin) instead of Vercel "Services", which is still beta.
- **Warning/Grace boundary** placed inside the grace window (default half), since
  the SRS fixes only interval and grace; the release instant stays `deadline + grace`.
- **Late check-ins are refused** once `deadline + grace` has passed, so the
  outcome does not depend on whether a tick happened to run first.
- **The secret is typed only after every trustee has enrolled**, so plaintext is
  never kept in the browser while waiting.
- **Emailed check-in links**: GET only previews; the page POSTs to confirm, so
  email link scanners cannot check in on the owner's behalf.

## Problems found and fixed

1. **Template `pyproject.toml` had an invalid project name**
   (`tiet-ucs503.github.io/...`). Vercel's Python builder runs `uv lock` and failed
   on it. Renamed to `ucs503p-aegis`, added the runtime dependencies and
   `[tool.uv] package = false`; pytest configuration unchanged.
2. **Requests stalled under concurrency** (found by the load test): FastAPI runs a
   sync dependency's setup, the endpoint and the commit-on-teardown as separate
   thread-pool hops; with every thread waiting on a SQLite lock, the lock holder
   could not get a thread to commit. Fixed by capping in-flight requests (async
   semaphore) below the thread-pool size.
3. **The zero-knowledge scanner missed misaligned base64** — caught by its own
   positive-control self-test; it now tries all four alignments.
4. **`crypto.getRandomValues` rejects requests over 64 KiB** — `randomBytes` now
   fills in chunks (found by the 1 MiB timing run).
5. **`vercel dev` cannot run Python functions on Windows** (its emulator uses
   `AF_UNIX` sockets). The layout was validated as far as possible locally
   (static build, rewrites, dependency install, imports); the final check is the
   first real deployment.

## Results (from `metrics/README.md`)

- Reliability, 1000 schedules: **0 early, 0 duplicate, 0 missed releases**, with
  restarts, racing ticks and clock jitter injected.
- Release lateness and prompt delay ≤ 60 s at the requirement cadence, but about
  13–14 minutes with the 5-minute cron alone: NFR-REL-2 / NFR-PERF-2 are **not met**
  by the cron trigger by itself.
- Zero-knowledge inspection: **0 findings**.
- Check-in p95 23.7 ms locally (sequential); deployed latency not yet measured.

## What's open

- **Deploy to Vercel** (needs the team's Vercel account, Neon, env vars and the
  GitHub secrets for the tick workflow), then measure the deployed latency and
  Lighthouse scores.
- Fill in "who did what" above and the `[TODO]` fields in the report file.
- Future work recorded in the report: multiple vaults, account recovery, large
  files, 2FA, a production email domain, rate limiting, constant-time crypto,
  verifiable secret sharing, Alembic migrations.
