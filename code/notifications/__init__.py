"""Aegis :: notifications — outbound messaging.

Responsibilities:
    * Send scheduled check-in prompts to the Owner.
    * Send warning reminders during the warning/grace windows.
    * On release, deliver each trustee their key share with instructions for
      reconstruction.

Transport: SMTP email in v1. Non-goals for v1 explicitly exclude SMS and push
notifications (see the SRS non-goals). Templates and delivery are isolated here
so the scheduler and api layers depend only on an abstract notifier.

Week 1 status: scaffold only.
"""

__all__: list[str] = []
