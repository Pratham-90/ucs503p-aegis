# Software Requirements Specification (SRS)

**Project:** Aegis — an encrypted "dead man's switch" legacy vault
**Author:** Pratham Arora (Roll No. `1024030001`, COE) — `parora_be24@thapar.edu`
**Course:** UCS503P — Software Engineering (Laboratory), TIET, 2026–27 ODD

!!! note "Companion to the LaTeX proposal"
    This page mirrors the formal SRS in
    [`project-proposal/main.tex`](https://github.com/Pratham-90/ucs503p-aegis/blob/main/project-proposal/main.tex).
    The LaTeX document is the submission artifact; this Markdown version is the
    web-navigable copy that the diagrams link back to. Requirement IDs are
    identical in both.

## 1. Purpose

This SRS defines the functional and non-functional requirements of **Aegis** for
version 1 (v1). It is the authoritative reference for the design,
implementation, and evaluation of the system across the UCS503P timeline.
Readers are the lab instructor/evaluator (acceptance authority) and the author
(sole developer). Every functional requirement carries a traceable ID
(`FR-n`) and every non-functional requirement a category ID (`NFR-cat-n`) so
that design, code, and tests can cite what they satisfy.

## 2. Scope

### 2.1 In scope (v1)

A web application — Python/FastAPI backend, React frontend — providing:

- Owner registration and authentication.
- Creation of a single vault per Owner and upload of an encrypted payload.
- Configuration of a check-in interval and a grace period.
- Designation of `N` trustees and a threshold `K` (`1 ≤ K ≤ N`).
- A scheduler that prompts for check-ins and, on missed check-in past the grace
  period, distributes key shares.
- A one-action check-in confirmation.
- Trustee submission of `K` shares to reconstruct the key and decrypt the
  payload.

The algorithmic core is a hand-written implementation of **Shamir's Secret
Sharing** over a finite field, plus symmetric encryption of the payload.

### 2.2 Non-goals (explicit exclusions for v1)

| ID | Non-goal |
| --- | --- |
| **NG-1** | **No SMS.** Notifications are email (SMTP) only. |
| **NG-2** | **No mobile app.** Responsive web only; no native client. |
| **NG-3** | **Single vault per user.** One vault per Owner in v1. |

## 3. Glossary

| Term | Definition |
| --- | --- |
| **Vault** | Encrypted container owned by one Owner: one payload + release config + lifecycle state. |
| **Payload** | The Owner's secret data (files/messages), stored only as ciphertext. |
| **Share** | One piece of the split decryption key produced by SSS; held by a single trustee. |
| **Threshold (`K`)** | Minimum shares needed to reconstruct the key; any `K` of `N` suffice, any `K−1` reveal nothing. |
| **Grace period** | Extra time granted after a missed check-in before release. |
| **Check-in** | Explicit, confirmed action by which the Owner signals presence, resetting the release timer. |
| **Owner** | Registered user who creates the vault, uploads the payload, and is prompted to check in. |
| **Trustee** | Person designated to receive a key share and help reconstruct after release. |
| **Scheduler** | Time-triggered system actor that tracks deadlines and drives the lifecycle. |

## 4. System actors and models

Three actors: **Owner** and **Trustee** (human), and the **Scheduler** — a
time-triggered *system* actor that initiates prompts and release with no human
action. The accompanying models (Mermaid diagrams):

- [Use-case diagram](../diagrams/use-case.md) — Owner, Trustee, Scheduler.
- [Vault lifecycle state diagram](../diagrams/vault-lifecycle.md) — Active →
  Warning → Grace → Released.
- [High-level architecture](../diagrams/architecture.md).

## 5. Functional Requirements

| ID | Requirement |
| --- | --- |
| **FR-1** | **Registration & authentication.** Register an Owner (email + password) and authenticate returning Owners before any vault operation. Passwords never stored in plaintext (see `NFR-SEC-3`). |
| **FR-2** | **Vault creation & payload upload.** An authenticated Owner creates their single vault and uploads a payload (files/message); it is encrypted and persisted only as ciphertext (see `NFR-SEC-1`). |
| **FR-3** | **Timing configuration.** The Owner sets the check-in interval and the grace period (positive durations; grace may be zero only if explicitly chosen). |
| **FR-4** | **Trustee designation & threshold.** The Owner designates `N ≥ 1` trustees and sets `K` with `1 ≤ K ≤ N`; on confirmation the key is split into `N` Shamir shares with threshold `K`. |
| **FR-5** | **Scheduled check-in prompts.** At each interval boundary the Scheduler moves the vault to *Warning* and emails a check-in prompt (see `NFR-PERF-2`). |
| **FR-6** | **One-action check-in confirmation.** The Owner confirms a check-in with a single action (one click on a tokenised link), resetting the timer and returning the vault to *Active*. |
| **FR-7** | **Share distribution on expiry.** Only if no valid check-in is confirmed before the deadline **and** the grace period have both elapsed does the Scheduler move the vault to *Released* and email one share to each trustee (see `NFR-REL-1`). |
| **FR-8** | **K-of-N reconstruction & decryption.** After release, the system accepts trustee-submitted shares; on any `K` valid shares it reconstructs the key and decrypts the payload. Fewer than `K` cannot decrypt. |

## 6. Non-Functional Requirements

### 6.1 Reliability — the catastrophic failure mode

| ID | Requirement & measurable criterion |
| --- | --- |
| **NFR-REL-1** | **No early release.** The system must **never** release a vault or distribute any share before `deadline + grace` has elapsed with no confirmed check-in. *Measure:* across ≥1000 simulated schedules (restarts, timer resets, retries, clock adjustments) the number of early releases is exactly **zero**. The project's single most important requirement. |
| **NFR-REL-2** | **Durable deadlines.** Pending deadlines survive a restart. *Measure:* after a forced restart, every deadline is re-armed and fires ≤60 s after due time; none lost, none early. |
| **NFR-REL-3** | **Exactly-once release.** Each vault releases at most once; each trustee receives at most one share, even under retries/concurrency. |

### 6.2 Security — payload confidentiality

| ID | Requirement & measurable criterion |
| --- | --- |
| **NFR-SEC-1** | **Payload never in plaintext.** Only ciphertext + non-secret metadata (filename, size, MIME) is persisted. *Measure:* automated inspection of DB and file store finds no plaintext payload; the plaintext key lives only transiently in memory. |
| **NFR-SEC-2** | **Threshold secrecy.** Any `≤ K−1` shares reveal no information about the key. *Measure:* property tests show every `K−1` subset is consistent with all possible secrets (intrinsic to SSS). |
| **NFR-SEC-3** | **Credential protection.** Passwords stored only as salted hashes via a memory-hard function (Argon2/bcrypt). |
| **NFR-SEC-4** | **Transport security.** All client–server traffic over HTTPS/TLS in deployed environments. |

### 6.3 Performance, usability, maintainability

| ID | Requirement & measurable criterion |
| --- | --- |
| **NFR-PERF-1** | Check-in confirmation processed within **500 ms (p95)** under nominal load. |
| **NFR-PERF-2** | A due check-in prompt dispatched within **60 s** of its scheduled time. |
| **NFR-USE-1** | Check-in requires **exactly one** deliberate action, no re-auth beyond the tokenised link (supports `FR-6`). |
| **NFR-MAINT-1** | Codebase passes `ruff` with no errors; unit-test coverage **≥80%** on `crypto` and `scheduler`. |
| **NFR-PORT-1** | Runs on SQLite (dev) and PostgreSQL (later) with no code change, via SQLAlchemy. |

## 7. Assumptions and Constraints

### Assumptions

- The Owner and every trustee have a working, monitored email address.
- Trustees are cooperative and willing to combine shares after release.
- The server's scheduling clock is the authoritative time source.
- SMTP delivery is reasonably reliable; transient failures are retried.

### Constraints

- **Platform:** Python 3 + FastAPI, SQLAlchemy, APScheduler, SMTP, React + Tailwind.
- **Algorithmic:** Shamir's Secret Sharing is hand-written (finite-field
  polynomial evaluation + Lagrange interpolation), not a third-party library;
  no HSM in v1.
- **Product:** non-goals NG-1…NG-3 hold.
- **Process:** solo development over a 12-week UCS503P timeline with weekly,
  CI-backed increments.

## 8. Requirement traceability

The IDs above are cited in the module docs (`code/*/README.md`) and will be
cited by tests as they are written — giving a requirement → module → test
trace. The lifecycle behind `FR-5`–`FR-7` and `NFR-REL-1` is specified by the
[vault lifecycle state diagram](../diagrams/vault-lifecycle.md).
