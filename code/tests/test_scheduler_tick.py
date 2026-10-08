"""The transactional tick: persistence, exactly-once release, restarts, races (NFR-REL-1/2/3)."""

import threading

import pytest
from conftest import BASE, T0, make_vault, seconds
from sqlalchemy import func, select

from notifications.outbox import queue_email
from scheduler.state import SchedulerError
from scheduler.tick import due_check, process_vault, tick
from vault.db import Database
from vault.models import CheckInToken, OutboxEmail, ShareBlob, TickLog, Trustee, Vault
from vault.repository import apply_check_in, lock_vault


def state(db, vault_id):
    with db.session() as s:
        return s.get(Vault, vault_id).state


def outbox(db, kind=None):
    with db.session() as s:
        q = select(OutboxEmail)
        if kind:
            q = q.where(OutboxEmail.kind == kind)
        return s.execute(q).scalars().all()


def test_nothing_happens_before_the_deadline(db):
    vid = make_vault(db)
    result = tick(db, T0 + seconds(119), trigger="test", base_url=BASE)
    assert result.transitions == [] and state(db, vid) == "active" and outbox(db) == []


def test_warning_sends_one_prompt_with_a_hashed_single_use_token(db):
    make_vault(db)
    result = tick(db, T0 + seconds(120), trigger="test", base_url=BASE)
    assert [t.to_state for t in result.transitions] == ["warning"]
    [prompt] = outbox(db, "checkin_prompt")
    assert prompt.to == "owner@example.com" and "/checkin/" in prompt.body
    with db.session() as s:
        token = s.execute(select(CheckInToken)).scalar_one()
        raw = prompt.body.split("/checkin/")[1].split()[0]
        assert raw not in token.token_hash and len(token.token_hash) == 64  # only the hash is stored


def test_release_happens_exactly_at_deadline_plus_grace_and_only_once(db):
    vid = make_vault(db)
    assert tick(db, T0 + seconds(179.999), trigger="test", base_url=BASE).transitions[-1].to_state == "grace"
    assert state(db, vid) == "grace"
    result = tick(db, T0 + seconds(180), trigger="test", base_url=BASE)
    assert result.transitions[-1].to_state == "released"
    for _ in range(3):  # duplicate / retried ticks
        assert tick(db, T0 + seconds(180), trigger="retry", base_url=BASE).transitions == []
    releases = outbox(db, "release")
    assert len(releases) == 3 and len({r.to for r in releases}) == 3
    with db.session() as s:
        assert all(b.delivered_at is not None for b in s.execute(select(ShareBlob)).scalars())
        assert all(t.access_token_hash for t in s.execute(select(Trustee)).scalars())
        assert s.get(Vault, vid).released_at == T0 + seconds(180)


def test_catch_up_after_an_outage_emits_owed_emails_in_order(db):
    make_vault(db)
    result = tick(db, T0 + seconds(10_000), trigger="test", base_url=BASE)
    assert result.transitions[0].actions == ["send_checkin_prompt", "send_grace_reminder", "release"]
    assert [e.kind for e in sorted(outbox(db), key=lambda e: e.created_at)][:2] == ["checkin_prompt", "grace_reminder"]


def test_stale_snapshot_race_cannot_duplicate_a_release(db):
    """A second tick that read the vault before the first committed would try to queue the
    same release emails; the UNIQUE dedupe_key rejects them."""
    vid = make_vault(db)
    tick(db, T0 + seconds(180), trigger="first", base_url=BASE)
    with db.session() as s:
        vault = s.get(Vault, vid)
        for t in vault.trustees:
            assert queue_email(s, to=t.email, subject="x", body="x", kind="release",
                               dedupe_key=f"release:{vid}:{t.id}", vault_id=vid) is None
    assert len(outbox(db, "release")) == 3


def test_concurrent_ticks_on_a_shared_database_release_once(tmp_path):
    database = Database(f"sqlite:///{tmp_path / 'race.db'}")
    database.create_all()
    vid = make_vault(database)
    barrier = threading.Barrier(4)
    errors = []

    def run():
        barrier.wait()
        try:
            tick(database, T0 + seconds(200), trigger="race", base_url=BASE)
        except Exception as exc:  # pragma: no cover - surfaced below
            errors.append(exc)

    threads = [threading.Thread(target=run) for _ in range(4)]
    for th in threads:
        th.start()
    for th in threads:
        th.join()
    assert errors == []
    assert state(database, vid) == "released"
    assert len(outbox(database, "release")) == 3
    database.dispose()


def test_deadlines_survive_a_restart(tmp_path):
    url = f"sqlite:///{tmp_path / 'restart.db'}"
    first = Database(url)
    first.create_all()
    vid = make_vault(first)
    tick(first, T0 + seconds(130), trigger="before-crash", base_url=BASE)
    first.dispose()  # the process dies
    second = Database(url)  # a new process
    assert state(second, vid) == "warning"
    tick(second, T0 + seconds(180), trigger="after-restart", base_url=BASE)
    assert state(second, vid) == "released"
    with second.session() as s:
        assert s.execute(select(func.count()).select_from(TickLog)).scalar() == 2
    second.dispose()


def test_check_in_from_grace_resets_and_late_check_in_is_refused(db):
    vid = make_vault(db)
    tick(db, T0 + seconds(160), trigger="test", base_url=BASE)
    with db.session() as s:
        vault = lock_vault(s, vid)
        assert due_check(s, vid, T0 + seconds(170), BASE) is None
        apply_check_in(s, vault, T0 + seconds(170), "dashboard")
    assert state(db, vid) == "active"
    assert tick(db, T0 + seconds(170 + 179), trigger="test", base_url=BASE).transitions[-1].to_state == "grace"
    with db.session() as s:
        vault = lock_vault(s, vid)
        transition = due_check(s, vid, T0 + seconds(170 + 180), BASE)  # due-check first
        assert transition.to_state == "released"
        with pytest.raises(SchedulerError):
            apply_check_in(s, vault, T0 + seconds(170 + 180), "dashboard")


def test_process_vault_ignores_setup_vaults(db):
    vid = make_vault(db)
    with db.session() as s:
        vault = s.get(Vault, vid)
        vault.state = "setup"
        assert process_vault(s, vault, T0 + seconds(10_000), BASE) is None
