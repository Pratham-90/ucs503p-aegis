# `notifications` — outbound messaging

Everything Aegis sends to a human goes through here. Isolating delivery behind
one package lets the `scheduler` depend on an abstract notifier rather than SMTP
details.

## Messages (planned)

| Message | Trigger | Recipient |
| --- | --- | --- |
| Check-in prompt | Interval elapses (vault enters `Warning`) | Owner |
| Warning reminder | During the warning / grace window | Owner |
| Blob delivery | Grace expires; vault `Released` | Each Trustee |

## Responsibilities

- Render message templates and deliver them reliably over SMTP.
- Carry the one-action check-in confirmation link in the prompt (FR-6).
- Deliver each trustee their own **encrypted share blob** (encrypted to that
  trustee at upload, per `FR-2a`) with instructions to decrypt it locally and
  combine `K` shares client-side (`FR-7`, `FR-8`). The plaintext share is never
  in the message or on the server.

## Non-goals (v1)

No **SMS** and no **mobile push** — email only. See the SRS non-goals list.

## Status

Week 1: **scaffold only**. Transport: SMTP.
