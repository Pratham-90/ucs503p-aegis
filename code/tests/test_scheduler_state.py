"""Exhaustive tests of the pure lifecycle function (FR-5, FR-6, FR-7, NFR-REL-1, NFR-REL-3)."""

from datetime import UTC, datetime, timedelta

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from scheduler.state import Action, Clock, SchedulerError, VaultState, check_in, evaluate

T0 = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
S = timedelta(seconds=1)
A, W, G, R = VaultState.ACTIVE, VaultState.WARNING, VaultState.GRACE, VaultState.RELEASED


def clock(state=A, interval=120, grace=60, warning=None, deadline=T0):
    return Clock(state, deadline, interval, grace, warning)


# --- the timeline --------------------------------------------------------------------

@pytest.mark.parametrize(
    "offset,expected,actions",
    [
        (-1, A, ()),
        (0, W, (Action.SEND_CHECKIN_PROMPT,)),
        (29, W, (Action.SEND_CHECKIN_PROMPT,)),
        (30, G, (Action.SEND_CHECKIN_PROMPT, Action.SEND_GRACE_REMINDER)),
        (59, G, (Action.SEND_CHECKIN_PROMPT, Action.SEND_GRACE_REMINDER)),
        (60, R, (Action.SEND_CHECKIN_PROMPT, Action.SEND_GRACE_REMINDER, Action.RELEASE)),
        (10_000, R, (Action.SEND_CHECKIN_PROMPT, Action.SEND_GRACE_REMINDER, Action.RELEASE)),
    ],
)
def test_from_active(offset, expected, actions):
    decision = evaluate(clock(), T0 + offset * S)
    assert decision.new_state is expected and decision.actions == actions


def test_never_released_one_microsecond_early():  # NFR-REL-1
    almost = T0 + timedelta(seconds=60) - timedelta(microseconds=1)
    for state in (A, W, G):
        assert evaluate(clock(state=state), almost).new_state is not R


def test_released_exactly_at_deadline_plus_grace():
    assert evaluate(clock(state=G), T0 + 60 * S) == evaluate(clock(state=G), T0 + 60 * S)
    assert evaluate(clock(state=G), T0 + 60 * S).actions == (Action.RELEASE,)


def test_each_action_is_owed_once():  # NFR-REL-3 at the decision level
    assert evaluate(clock(state=W), T0 + 10 * S).actions == ()
    assert evaluate(clock(state=G), T0 + 45 * S).actions == ()
    assert evaluate(clock(state=W), T0 + 40 * S).actions == (Action.SEND_GRACE_REMINDER,)


def test_backward_clock_jump_never_regresses_a_state():
    for state in (W, G):
        assert evaluate(clock(state=state), T0 - 3600 * S).new_state is state


def test_released_and_setup_are_inert():
    assert evaluate(clock(state=R), T0 + 10**6 * S) .actions == ()
    assert evaluate(clock(state=VaultState.SETUP, deadline=None), T0).new_state is VaultState.SETUP


def test_custom_and_zero_warning_windows():
    assert evaluate(clock(warning=0), T0).new_state is G
    assert evaluate(clock(warning=60), T0 + 59 * S).new_state is W


def test_zero_grace_releases_at_the_deadline():  # FR-3 allows an explicit zero grace
    c = clock(grace=0)
    assert evaluate(c, T0 - S).new_state is A
    assert evaluate(c, T0).new_state is R


def test_next_due_at_follows_the_state():
    assert clock(state=A).next_due_at() == T0
    assert clock(state=W).next_due_at() == T0 + 30 * S
    assert clock(state=G).next_due_at() == T0 + 60 * S
    assert clock(state=R).next_due_at() is None


# --- check-in (FR-6) -------------------------------------------------------------------

@pytest.mark.parametrize("state", [A, W, G])
def test_check_in_returns_to_active_and_resets_deadline(state):
    now = T0 + 20 * S
    c = check_in(clock(state=state), now)
    assert c.state is A and c.deadline_at == now + 120 * S


def test_check_in_after_deadline_plus_grace_is_too_late():
    with pytest.raises(SchedulerError, match="window closed"):
        check_in(clock(state=G), T0 + 60 * S)


@pytest.mark.parametrize("state", [R, VaultState.SETUP])
def test_check_in_rejected_when_released_or_unarmed(state):
    with pytest.raises(SchedulerError):
        check_in(clock(state=state), T0)


# --- validation ------------------------------------------------------------------------

@pytest.mark.parametrize(
    "kwargs",
    [dict(interval=0), dict(grace=-1), dict(grace=10, warning=11), dict(deadline=datetime(2026, 1, 1))],
)
def test_invalid_clocks_are_rejected(kwargs):
    with pytest.raises(SchedulerError):
        clock(**kwargs)


def test_naive_times_are_rejected():
    with pytest.raises(SchedulerError):
        evaluate(clock(), datetime(2026, 1, 1))
    with pytest.raises(SchedulerError):
        check_in(clock(), datetime(2026, 1, 1))


# --- properties ------------------------------------------------------------------------

offsets = st.integers(min_value=-10**6, max_value=10**6)


@settings(max_examples=500)
@given(interval=st.integers(1, 10**6), grace=st.integers(0, 10**6), data=st.data(),
       state=st.sampled_from([A, W, G]), offset=offsets)
def test_property_never_early(interval, grace, data, state, offset):
    """NFR-REL-1: whatever the configuration and the time, Released implies now >= D + grace."""
    warning = data.draw(st.one_of(st.none(), st.integers(0, grace)))
    c = Clock(state, T0, interval, grace, warning)
    now = T0 + offset * S
    if evaluate(c, now).new_state is R:
        assert now >= T0 + grace * S


@settings(max_examples=300)
@given(steps=st.lists(offsets, min_size=1, max_size=40))
def test_property_release_owed_at_most_once_and_states_monotone(steps):
    """Over any (even non-monotone) sequence of evaluation times, the RELEASE action is
    owed at most once and the state never moves backwards (NFR-REL-3)."""
    c = clock()
    rank = [A, W, G, R]
    releases = 0
    for offset in steps:
        decision = evaluate(c, T0 + offset * S)
        assert rank.index(decision.new_state) >= rank.index(c.state)
        releases += decision.actions.count(Action.RELEASE)
        c = Clock(decision.new_state, c.deadline_at, c.interval_s, c.grace_s, c.warning_s)
    assert releases <= 1
