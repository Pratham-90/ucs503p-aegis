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
- Creation of a single vault per Owner; the payload is encrypted **in the
  Owner's browser** and uploaded as ciphertext only.
- Configuration of a check-in interval and a grace period.
- Designation of `N` trustees (each enrolling a public key) and a threshold `K`
  (`1 ≤ K ≤ N`).
- A scheduler that prompts for check-ins and, on missed check-in past the grace
  period, distributes each trustee's **encrypted share blob**.
- A one-action check-in confirmation.
- **Client-side reconstruction:** any `K` trustees decrypt their blobs and
  combine shares in the browser to recover the key and decrypt the payload.

The algorithmic core is a hand-written implementation of **Shamir's Secret
Sharing** over a finite field, plus symmetric encryption of the payload — all
performed **client-side** (see the [Trust model](#23-trust-model)).

### 2.2 Non-goals (explicit exclusions for v1)

| ID | Non-goal |
| --- | --- |
| **NG-1** | **No SMS.** Notifications are email (SMTP) only. |
| **NG-2** | **No mobile app.** Responsive web only; no native client. |
| **NG-3** | **Single vault per user.** One vault per Owner in v1. |

### 2.3 Trust model

Aegis adopts a **zero-knowledge server** design: the server is trusted for
**scheduling and availability**, and **never for confidentiality**. All payload
cryptography — key generation, encryption, Shamir splitting, and reconstruction
— runs on clients (the Owner's and trustees' browsers). The server persists only
the ciphertext payload, the `N` trustee-encrypted share blobs, and non-secret
metadata (`FR-2`, `FR-2a`, `NFR-SEC-5`).

The boundary and its honest consequences:

- **The server alone can never read a payload.** A confidentiality breach
  requires the server **and** at least `K` trustees.
- **The server controls release timing.** It could release blobs early or refuse
  to release. Early release still yields plaintext only if `≥ K` trustees then
  collude; denial of release is an *availability* failure, not a confidentiality
  one (see threat [`T-7`](../threat-model.md)).
- **Client code is server-delivered.** The zero-knowledge property holds against
  a *passive/storage* compromise of the server, **not** against a malicious
  server that serves backdoored client code (which could exfiltrate the key at
  encryption time). This residual risk is **not mitigated in v1** (see threat
  [`T-4`](../threat-model.md)).

The full per-threat analysis is in the [threat model](../threat-model.md).

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
| **FR-2** | **Vault creation & client-side payload encryption.** An authenticated Owner creates their single vault; the payload (files/message) is encrypted **in the browser** under a locally generated symmetric key, and only the ciphertext + non-secret metadata are uploaded. The server never receives the plaintext payload or the key (see `NFR-SEC-1`, `NFR-SEC-5`). |
| **FR-2a** | **Client-side key splitting & share encryption.** In the browser, the symmetric key is split into `N` Shamir shares (threshold `K`, per `FR-4`); each share is then encrypted under its trustee's enrolled public key. The server receives only the `N` trustee-encrypted share blobs — never a plaintext share or the key (see `NFR-SEC-5`). |
| **FR-3** | **Timing configuration.** The Owner sets the check-in interval and the grace period (positive durations; grace may be zero only if explicitly chosen). |
| **FR-4** | **Trustee designation, enrolment & threshold.** The Owner designates `N ≥ 1` trustees (by email) and sets `K` with `1 ≤ K ≤ N`. Each trustee enrols a **public key** whose private key is generated on, and never leaves, their own device; these public keys are the inputs to the client-side split (`FR-2a`). The key is never split or held server-side. |
| **FR-5** | **Scheduled check-in prompts.** At each interval boundary the Scheduler moves the vault to *Warning* and emails a check-in prompt (see `NFR-PERF-2`). |
| **FR-6** | **One-action check-in confirmation.** The Owner confirms a check-in with a single action (one click on a tokenised link), resetting the timer and returning the vault to *Active*. |
| **FR-7** | **Blob distribution on expiry.** Only if no valid check-in is confirmed before the deadline **and** the grace period have both elapsed does the Scheduler move the vault to *Released* and deliver to each trustee their own encrypted share blob (already encrypted to them at upload, per `FR-2a`) — only then (see `NFR-REL-1`). The server distributes blobs; it never holds a plaintext share. |
| **FR-8** | **Client-side K-of-N reconstruction & decryption.** After release, each trustee decrypts their blob locally with their private key to recover their share; any `K` trustees combine shares **in the browser** to reconstruct the key and decrypt the payload. Fewer than `K` cannot decrypt. The server performs no decryption and never sees a plaintext share, the key, or the payload (see `NFR-SEC-5`). |

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
| **NFR-SEC-1** | **Payload never in plaintext.** Only ciphertext + non-secret metadata (filename, size, MIME) is persisted. *Measure:* automated inspection of DB and file store finds no plaintext payload; the plaintext key lives only transiently in **client** memory (Owner's browser at encryption, a trustee's browser at reconstruction) and never on the server (see `NFR-SEC-5`). |
| **NFR-SEC-2** | **Threshold secrecy.** Any `≤ K−1` shares reveal no information about the key. *Measure:* property tests show every `K−1` subset is consistent with all possible secrets (intrinsic to SSS). |
| **NFR-SEC-3** | **Credential protection.** Passwords stored only as salted hashes via a memory-hard function (Argon2/bcrypt). |
| **NFR-SEC-4** | **Transport security.** All client–server traffic over HTTPS/TLS in deployed environments. |
| **NFR-SEC-5** | **Zero-knowledge server.** The server shall at no point possess sufficient material to decrypt a payload unaided. *Measure:* inspecting everything the server persists or receives (DB rows, uploaded objects, request logs) finds, per vault, only the ciphertext payload, the `N` trustee-public-key-encrypted share blobs, and non-secret metadata — no plaintext payload, no key, no plaintext share. Decryption requires material held only by clients and by `≥ K` trustees, never the server alone. See the [Trust model](#23-trust-model) and [threat model](../threat-model.md). |

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
[vault lifecycle state diagram](../diagrams/vault-lifecycle.md). The trust
boundary and per-threat coverage are analysed in the
[threat model](../threat-model.md), whose mitigations cite these same
identifiers.
