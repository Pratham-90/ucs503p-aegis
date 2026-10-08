# `notifications` — outbound messaging

Everything Aegis sends to a person goes through a **transactional outbox**.

## Messages

| Kind | Trigger | Recipient | Dedupe key |
| --- | --- | --- | --- |
| `invite` | Vault created | each trustee | `invite:<trustee>` |
| `checkin_prompt` | Active → Warning | Owner | `prompt:<vault>:<deadline>` |
| `grace_reminder` | Warning → Grace | Owner | `grace:<vault>:<deadline>` |
| `release` | Grace → Released | each trustee | `release:<vault>:<trustee>` |

Prompts carry a one-click check-in link (single-use, expiring token; FR-6).
Release notices carry a trustee magic link; the encrypted blob is fetched by
the trustee, so **no email ever contains secret material** (FR-7).

## Design

- `outbox.queue_email(...)` inserts a row in the *same* transaction as the state
  change. `dedupe_key` is UNIQUE, so the decision to send is recorded exactly
  once even under racing ticks (NFR-REL-3).
- Delivery happens after commit through an `EmailSender` **strategy**:
  `LogSender` (`EMAIL_MODE=log`: the in-app Outbox in the Demo Console is the
  mailbox) or `ResendSender` (`EMAIL_MODE=resend`: also calls the Resend API).
  Delivery to the provider is at-least-once.

## Known limitations (prototype)

- In log mode the outbox body holds the one-click link, so the raw token is
  stored in that row (tokens are single-use, expiring, and the outbox is
  admin-only). Only token *hashes* are stored elsewhere.
- Without a verified sending domain, Resend only delivers to the account owner's
  address; a production domain is future work.
- Email only — no SMS (NG-1).
