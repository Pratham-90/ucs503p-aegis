"""Aegis :: notifications — outbound messaging.

Responsibilities:
    * Queue check-in prompts, grace reminders, trustee invites and release
      notices into a transactional outbox (``outbox.queue_email``); the UNIQUE
      ``dedupe_key`` makes each decision exactly-once (NFR-REL-3).
    * Deliver queued mail through an ``EmailSender`` strategy: ``LogSender``
      (EMAIL_MODE=log, in-app Outbox only) or ``ResendSender`` (EMAIL_MODE=resend).

Emails never contain secret material: release notices carry a link, and the
trustee fetches their *encrypted* blob (FR-7). Email only, no SMS (NG-1).
"""

__all__: list[str] = []
