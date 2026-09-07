# 12-Week Plan

The roadmap for Aegis across the UCS503P timeline (2026–27 ODD). Each week
produces a reviewable increment and cites the requirements it advances (see the
[SRS](../srs/index.md)). Weeks are indicative and may shift as work lands; this
page is updated as the project progresses.

| Week | Focus | Key deliverables | Requirements |
| :--: | --- | --- | --- |
| **1** ✅ | Requirements & scaffolding | Repo + module scaffold, SRS, diagrams, Shamir spike, this plan | `FR-1…8`, `NFR-*` (specified) |
| **2** | Domain model & persistence | `vault` package: SQLAlchemy models (Owner, Vault, Payload, Trustee, Share, CheckIn) + repositories on SQLite; unit tests | `FR-2`, `NFR-PORT-1` |
| **3** | Auth & vault API | FastAPI app; registration/login; create vault + upload payload; timing config | `FR-1`, `FR-2`, `FR-3`, `NFR-SEC-3` |
| **4** | Crypto core + test vectors | Hardened **Python** `crypto` (authoritative spec + test oracle): Shamir split/reconstruct + authenticated payload encryption, **property tests (Hypothesis)**, and a committed **versioned test-vector artifact** the JS client crypto is validated against | `FR-2a`, `FR-4`, `FR-8`, `NFR-SEC-1`, `NFR-SEC-2`, `NFR-MAINT-1` |
| **5** | Scheduler core | APScheduler; Active→Warning→Grace→Released state machine; **persistent, never-early** deadlines; reliability suite | `FR-5`, `NFR-REL-1`, `NFR-REL-2`, `NFR-REL-3` |
| **6** | Notifications & check-in | SMTP prompts/reminders; one-action tokenised check-in confirmation | `FR-5`, `FR-6`, `NFR-PERF-2`, `NFR-USE-1` |
| **7** | Release path end-to-end | Share distribution on expiry; trustee share submission; K-of-N reconstruct + decrypt | `FR-7`, `FR-8` |
| **8** | Prototype integration & report | End-to-end prototype demo; ≥1000-schedule reliability run; **prototype-stage report** | `NFR-REL-1`, integration |
| **9** | Frontend | React + Tailwind UI for Owner (setup, check-in) and Trustee (submit share) | `FR-1…8` (UI), `NG-2` |
| **10** | Security & NFR hardening | Password hashing, HTTPS/TLS, performance targets, `ruff` clean + coverage | `NFR-SEC-3`, `NFR-SEC-4`, `NFR-PERF-1`, `NFR-MAINT-1` |
| **11** | E2E testing & deployment | Postgres deployment, CI/CD, end-to-end tests, bug-fixing, docs polish | `NFR-PORT-1`, all |
| **12** | Final report & demo | **Final report**, final demo, submission wrap-up | all |

## Milestones

- **M1 — Requirements frozen (Week 1).** SRS + diagrams reviewed. ✅
- **M2 — Core secured (Week 4).** Payload encrypted; key split/reconstruct
  works and is tested (`NFR-SEC-1`, `NFR-SEC-2`).
- **M3 — Release gate proven (Week 5).** No-early-release verified by the
  reliability suite (`NFR-REL-1`) — the project's make-or-break guarantee.
- **M4 — Prototype (Week 8).** End-to-end owner→miss→release→trustee flow demoed;
  prototype-stage report submitted.
- **M5 — Final (Week 12).** Hardened, deployed, documented; final report and
  demo.

## Risk notes

- The scheduler's *never release early* guarantee (`NFR-REL-1`) is the highest
  risk and is deliberately front-loaded (Week 5, proven Week 8) with a
  dedicated reliability suite rather than left to the end.
- The hand-written crypto (`FR-4`, `FR-8`) is the second risk; the Week-1 spike
  already de-risked feasibility, leaving Week 4 to focus on hardening.
