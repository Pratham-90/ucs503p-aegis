"""Plain-text email templates. None of them ever contains secret material:
release emails carry a *link*; the encrypted blob is fetched by the trustee."""

from __future__ import annotations

from datetime import datetime


def _when(dt: datetime | None) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S UTC") if dt else "unknown"


def trustee_invite(owner_email: str, link: str) -> tuple[str, str]:
    return (
        "You have been asked to be a trustee on Aegis",
        f"{owner_email} has named you as a trustee of their Aegis legacy vault.\n\n"
        f"Open this link to enrol. Your browser will generate a keypair; the private key stays on your device "
        f"and you will be asked to download it as a file. Keep that file safe.\n\n{link}\n\n"
        "You will not see anything inside the vault unless it is released and enough trustees cooperate.",
    )


def checkin_prompt(link: str, release_at: datetime | None) -> tuple[str, str]:
    return (
        "Aegis: please check in",
        "Your Aegis check-in is due. One click confirms you are fine and resets the timer (FR-6):\n\n"
        f"{link}\n\nIf no check-in is confirmed, the vault will be released to your trustees at {_when(release_at)}.",
    )


def grace_reminder(link: str, release_at: datetime | None) -> tuple[str, str]:
    return (
        "Aegis: final reminder — vault in grace period",
        "You have missed your check-in and the vault is in its grace period.\n\n"
        f"Check in now: {link}\n\nRelease to your trustees is scheduled for {_when(release_at)}.",
    )


def release_notice(link: str, k: int) -> tuple[str, str]:
    return (
        "Aegis: a vault you guard has been released",
        "A vault you are a trustee of has been released because its owner stopped checking in.\n\n"
        f"Open your trustee portal, load your private key file and decrypt your share:\n\n{link}\n\n"
        f"The vault opens only when {k} trustees combine their shares in the Recovery Room.",
    )
