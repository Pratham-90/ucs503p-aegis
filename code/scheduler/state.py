"""The vault lifecycle as a pure function of (vault clock, now).

``evaluate`` is the *only* place that decides a vault may be released, and it
takes no I/O, so it can be tested exhaustively (NFR-REL-1). ``tick`` (tick.py)
applies its decisions to the database transactionally.

Timeline for a vault whose current deadline is D (D = last check-in + interval):

    Active ── now >= D ──────────────► Warning   (send check-in prompt, FR-5)
    Warning ─ now >= D + warning_s ──► Grace     (send grace reminder)
    Grace ─── now >= D + grace_s ────► Released  (deliver encrypted blobs, FR-7)

``warning_s`` defaults to half the grace period. The SRS fixes only the
interval and the grace period (FR-3); it leaves the Warning/Grace boundary open
(the gap noted in Week 1), so the prototype places it inside the grace window.
That keeps the release instant exactly ``D + grace_s`` as NFR-REL-1 requires.

A confirmed check-in from Active, Warning or Grace returns the vault to Active
with ``D = now + interval`` (FR-6). Released is terminal. ``Setup`` is the
pre-armed state before the encrypted payload is uploaded; the clock does not run.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from enum import StrEnum


class VaultState(StrEnum):
    SETUP = "setup"
    ACTIVE = "active"
    WARNING = "warning"
    GRACE = "grace"
    RELEASED = "released"


class Action(StrEnum):
    SEND_CHECKIN_PROMPT = "send_checkin_prompt"
    SEND_GRACE_REMINDER = "send_grace_reminder"
    RELEASE = "release"


class SchedulerError(ValueError):
    pass


_RANK = {VaultState.ACTIVE: 0, VaultState.WARNING: 1, VaultState.GRACE: 2, VaultState.RELEASED: 3}
_ENTRY_ACTION = {
    VaultState.WARNING: Action.SEND_CHECKIN_PROMPT,
    VaultState.GRACE: Action.SEND_GRACE_REMINDER,
    VaultState.RELEASED: Action.RELEASE,
}
_ORDER = (VaultState.ACTIVE, VaultState.WARNING, VaultState.GRACE, VaultState.RELEASED)


@dataclass(frozen=True)
class Clock:
    """The scheduling-relevant part of a vault."""

    state: VaultState
    deadline_at: datetime | None
    interval_s: int
    grace_s: int
    warning_s: int | None = None

    def __post_init__(self) -> None:
        if self.interval_s <= 0:
            raise SchedulerError("interval must be positive (FR-3)")
        if self.grace_s < 0:
            raise SchedulerError("grace period must not be negative (FR-3)")
        if self.warning_s is not None and not 0 <= self.warning_s <= self.grace_s:
            raise SchedulerError("warning window must lie within the grace period")
        if self.deadline_at is not None and self.deadline_at.tzinfo is None:
            raise SchedulerError("deadline must be timezone-aware (UTC)")

    @property
    def effective_warning_s(self) -> int:
        return self.grace_s // 2 if self.warning_s is None else self.warning_s

    @property
    def grace_starts_at(self) -> datetime | None:
        if self.deadline_at is None:
            return None
        return self.deadline_at + timedelta(seconds=self.effective_warning_s)

    @property
    def release_at(self) -> datetime | None:
        """The earliest instant at which the vault may be released (NFR-REL-1)."""
        if self.deadline_at is None:
            return None
        return self.deadline_at + timedelta(seconds=self.grace_s)

    def next_due_at(self) -> datetime | None:
        """When the next transition becomes due (used to find vaults worth ticking)."""
        if self.state is VaultState.ACTIVE:
            return self.deadline_at
        if self.state is VaultState.WARNING:
            return self.grace_starts_at
        if self.state is VaultState.GRACE:
            return self.release_at
        return None


@dataclass(frozen=True)
class Decision:
    new_state: VaultState
    actions: tuple[Action, ...] = ()

    @property
    def changed(self) -> bool:
        return bool(self.actions)


def _target_state(clock: Clock, now: datetime) -> VaultState:
    if now >= clock.release_at:
        return VaultState.RELEASED
    if now >= clock.grace_starts_at:
        return VaultState.GRACE
    if now >= clock.deadline_at:
        return VaultState.WARNING
    return VaultState.ACTIVE


def evaluate(clock: Clock, now: datetime) -> Decision:
    """Decide the vault's state at ``now`` and the actions owed on the way there.

    * Only ever moves forward; a backward clock jump never un-warns a vault.
    * Catches up through every missed transition in order (e.g. after an outage),
      but the Released transition still requires ``now >= deadline + grace``.
    """
    if now.tzinfo is None:
        raise SchedulerError("now must be timezone-aware (UTC)")
    if clock.state in (VaultState.SETUP, VaultState.RELEASED) or clock.deadline_at is None:
        return Decision(clock.state)
    target = _target_state(clock, now)
    if _RANK[target] <= _RANK[clock.state]:
        return Decision(clock.state)
    passed = _ORDER[_RANK[clock.state] + 1 : _RANK[target] + 1]
    return Decision(target, tuple(_ENTRY_ACTION[s] for s in passed))


def check_in(clock: Clock, now: datetime) -> Clock:
    """Apply a confirmed check-in (FR-6): back to Active, deadline = now + interval."""
    if now.tzinfo is None:
        raise SchedulerError("now must be timezone-aware (UTC)")
    if clock.state is VaultState.RELEASED:
        raise SchedulerError("vault already released; check-ins are no longer accepted")
    if clock.state is VaultState.SETUP:
        raise SchedulerError("vault is not armed yet")
    if clock.release_at is not None and now >= clock.release_at:
        # FR-7: only a check-in confirmed *before* deadline + grace counts. Rejecting
        # late ones makes the outcome independent of whether a tick ran first.
        raise SchedulerError("check-in window closed: the vault is due for release")
    return replace(clock, state=VaultState.ACTIVE, deadline_at=now + timedelta(seconds=clock.interval_s))
