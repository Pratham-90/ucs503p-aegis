"""Reliability simulation for NFR-REL-1/2/3 (brief section 8).

Drives the *real* scheduler code (``scheduler.tick.tick``, ``due_check`` and
``vault.repository.apply_check_in`` on a file-backed SQLite database) with a
fake clock, across >= 1000 vault schedules, and checks every outcome against an
independent oracle kept by the simulator itself.

Faults injected per world: random check-ins (on time, late-in-grace, too late),
irregular tick gaps with clock jitter (including small *backward* jumps),
duplicate ticks at the same instant, genuinely concurrent ticks (two threads),
and simulated process restarts (engine disposed and re-created from the file).

Measured:
  * early releases     released_at < last accepted check-in + interval + grace   (must be 0)
  * duplicate releases more than one release email per (vault, trustee)            (must be 0)
  * missed releases    an abandoned vault never released by the end of the run     (must be 0)
  * max lateness       released_at - due release time                              (NFR-REL-2: <= 60 s)
  * prompt delay       Warning prompt time - deadline                              (NFR-PERF-2: <= 60 s)

Two tick cadences are run: "requirement" (gaps 5-55 s, the cadence NFR-REL-2
assumes) and "deployment" (every 300 s plus GitHub-Actions-style delays of up to
10 min, i.e. the cron trigger alone, without lazy due-checks).

Usage:  python scripts/reliability_sim.py [--schedules 1000] [--seed 2026] [--out metrics/raw/reliability.json]
"""

from __future__ import annotations

import argparse
import heapq
import json
import random
import sys
import tempfile
import threading
import time
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "code"))

from sqlalchemy import select  # noqa: E402

from scheduler.state import SchedulerError  # noqa: E402
from scheduler.tick import due_check, tick  # noqa: E402
from vault.db import Database  # noqa: E402
from vault.models import OutboxEmail, Owner, ShareBlob, Trustee, Vault  # noqa: E402
from vault.repository import apply_check_in, arm_vault, hash_token, lock_vault  # noqa: E402

T0 = datetime(2026, 10, 1, 0, 0, tzinfo=UTC)
BASE = "https://sim.invalid"
VAULTS_PER_WORLD = 40
N_TRUSTEES = 3


def at(seconds: float) -> datetime:
    return T0 + timedelta(seconds=seconds)


class World:
    """One database with VAULTS_PER_WORLD independent vault schedules."""

    def __init__(self, rng: random.Random, path: Path, cadence: str) -> None:
        self.rng, self.path, self.cadence = rng, path, cadence
        self.db = Database(f"sqlite:///{path.as_posix()}")
        self.db.create_all()
        self.vaults: dict[str, dict] = {}
        self.stats = defaultdict(int)
        self.prompt_delays: list[float] = []

    # --- setup ------------------------------------------------------------------------
    def create_vaults(self, index: int) -> None:
        with self.db.session() as s:
            for i in range(VAULTS_PER_WORLD):
                interval = self.rng.randint(60, 1800)
                grace = self.rng.choice([0, self.rng.randint(1, 900), self.rng.randint(1, 900)])
                warning = self.rng.choice([None, self.rng.randint(0, grace)])
                owner = Owner(email=f"o{index}-{i}@sim.invalid", password_hash="x")
                vault = Vault(owner=owner, k=2, n=N_TRUSTEES, interval_s=interval, grace_s=grace, warning_s=warning,
                              payload_ciphertext=b"c" * 32, payload_iv=b"i" * 12, payload_meta_json="{}")
                s.add(vault)
                s.flush()
                for p in range(1, N_TRUSTEES + 1):
                    t = Trustee(vault=vault, position=p, email=f"t{p}-{index}-{i}@sim.invalid",
                                invite_token_hash=hash_token(f"{index}-{i}-{p}"), public_key_jwk="{}", enrolled_at=T0)
                    s.add(t)
                    s.flush()
                    s.add(ShareBlob(vault_id=vault.id, trustee_id=t.id, x_index=p, encrypted_share=b"b" * 256))
                arm_at = self.rng.uniform(0, 600)
                arm_vault(s, vault, at(arm_at))
                self.vaults[vault.id] = {"interval": interval, "grace": grace, "accepted": [arm_at],
                                         "cycles_left": self.rng.randint(0, 5), "stopped": False}

    # --- the owner's behaviour ----------------------------------------------------------
    def next_checkin(self, vid: str) -> float | None:
        v = self.vaults[vid]
        if v["cycles_left"] <= 0:
            v["stopped"] = True
            return None
        v["cycles_left"] -= 1
        last, interval, grace = v["accepted"][-1], v["interval"], v["grace"]
        roll = self.rng.random()
        if roll < 0.6:   # on time
            return last + interval * self.rng.uniform(0.1, 0.99)
        if roll < 0.9:   # late, inside the warning/grace window
            return last + interval + grace * self.rng.uniform(0.0, 0.98)
        return last + interval + grace + self.rng.uniform(0.0, 120.0)  # too late: must be refused

    def owner_check_in(self, vid: str, t: float) -> bool:
        now = at(t + self.rng.uniform(-2, 2))  # the owner's request also sees a jittered server clock
        with self.db.session() as s:
            vault = lock_vault(s, vid)
            due_check(s, vid, now, BASE)
            try:
                apply_check_in(s, vault, now, "sim")
            except SchedulerError:
                self.stats["checkins_refused"] += 1
                return False
        self.vaults[vid]["accepted"].append((now - T0).total_seconds())
        self.stats["checkins_accepted"] += 1
        return True

    # --- ticking ------------------------------------------------------------------------
    def gap(self) -> float:
        if self.cadence == "requirement":
            return self.rng.uniform(5, 55)
        return 300 + self.rng.choice([0, 0, 0, self.rng.uniform(0, 600)])  # GitHub Actions cron delay

    def do_tick(self, t: float) -> None:
        now = at(t + self.rng.uniform(-3, 3))  # clock jitter, including backward jumps
        roll = self.rng.random()
        if roll < 0.05:  # two ticks racing on separate connections
            threads = [threading.Thread(target=tick, args=(self.db, now), kwargs={"trigger": "race", "base_url": BASE})
                       for _ in range(2)]
            for th in threads:
                th.start()
            for th in threads:
                th.join()
            self.stats["concurrent_tick_pairs"] += 1
        else:
            tick(self.db, now, trigger="sim", base_url=BASE)
            if roll < 0.15:  # retry / duplicate trigger at the same instant
                tick(self.db, now, trigger="duplicate", base_url=BASE)
                self.stats["duplicate_ticks"] += 1
        self.stats["ticks"] += 1
        if self.rng.random() < 0.02:  # the process dies; a new one loads state from the database
            self.db.dispose()
            self.db = Database(f"sqlite:///{self.path.as_posix()}")
            self.stats["restarts"] += 1

    def run(self) -> None:
        events: list[tuple[float, int, str]] = []
        for vid in self.vaults:
            nxt = self.next_checkin(vid)
            if nxt is not None:
                heapq.heappush(events, (nxt, 0, vid))
        horizon = 600 + 6 * (1800 + 900) + 1800 + 900 + 1200
        t = 0.0
        while t < horizon:
            t += self.gap()
            while events and events[0][0] <= t:
                ct, _, vid = heapq.heappop(events)
                if self.owner_check_in(vid, ct):
                    nxt = self.next_checkin(vid)
                    if nxt is not None:
                        heapq.heappush(events, (nxt, 0, vid))
                else:
                    self.vaults[vid]["stopped"] = True
            self.do_tick(t)
        tick(self.db, at(horizon + 10_000), trigger="final", base_url=BASE)  # flush anything owed

    # --- the oracle ---------------------------------------------------------------------
    def verify(self) -> dict:
        early, missed, lateness = [], [], []
        with self.db.session() as s:
            releases = defaultdict(int)
            for e in s.execute(select(OutboxEmail)).scalars():
                if e.kind == "release":
                    releases[(e.vault_id, e.to)] += 1
            for vid, v in self.vaults.items():
                vault = s.get(Vault, vid)
                if vault.released_at is None:
                    missed.append(vid)
                    continue
                released = (vault.released_at - T0).total_seconds()
                last = max(a for a in v["accepted"] if a <= released + 1e-6)
                due = last + v["interval"] + v["grace"]
                if released < due - 1e-6:
                    early.append({"vault": vid, "released": released, "due": due})
                lateness.append(released - due)
                # prompt delay: the prompt for the final deadline
                deadline = last + v["interval"]
                query = select(OutboxEmail).where(OutboxEmail.vault_id == vid, OutboxEmail.kind == "checkin_prompt")
                prompts = s.execute(query).scalars().all()
                after = [(p.created_at - T0).total_seconds() for p in prompts
                         if (p.created_at - T0).total_seconds() >= deadline - 3.0001]
                if after:
                    self.prompt_delays.append(min(after) - deadline)
            duplicates = sum(1 for count in releases.values() if count > 1)
            wrong_count = sum(1 for vid in self.vaults if s.get(Vault, vid).released_at is not None
                              and sum(releases[(vid, t.email)] for t in s.get(Vault, vid).trustees) != N_TRUSTEES)
        self.db.dispose()
        return {"early": early, "missed": missed, "duplicates": duplicates, "wrong_release_count": wrong_count,
                "lateness": lateness}


def simulate(schedules: int, seed: int, cadence: str) -> dict:
    rng = random.Random(seed)
    worlds = max(1, -(-schedules // VAULTS_PER_WORLD))
    totals = defaultdict(int)
    early, missed, lateness, prompt_delays = [], [], [], []
    duplicates = wrong = 0
    started = time.perf_counter()
    with tempfile.TemporaryDirectory() as tmp:
        for w in range(worlds):
            world = World(random.Random(rng.random()), Path(tmp) / f"world-{w}.db", cadence)
            world.create_vaults(w)
            world.run()
            result = world.verify()
            early += result["early"]
            missed += result["missed"]
            duplicates += result["duplicates"]
            wrong += result["wrong_release_count"]
            lateness += result["lateness"]
            prompt_delays += world.prompt_delays
            for k, v in world.stats.items():
                totals[k] += v
    lateness.sort()
    prompt_delays.sort()
    pct = lambda xs, q: round(xs[min(len(xs) - 1, int(q * len(xs)))], 3) if xs else None  # noqa: E731
    return {
        "cadence": cadence,
        "schedules": worlds * VAULTS_PER_WORLD,
        "seed": seed,
        "early_releases": len(early),
        "early_release_examples": early[:5],
        "duplicate_releases": duplicates,
        "releases_with_wrong_email_count": wrong,
        "missed_releases": len(missed),
        "max_lateness_s": round(max(lateness), 3) if lateness else None,
        "p95_lateness_s": pct(lateness, 0.95),
        "max_prompt_delay_s": round(max(prompt_delays), 3) if prompt_delays else None,
        "p95_prompt_delay_s": pct(prompt_delays, 0.95),
        "fault_injection": dict(totals),
        "runtime_s": round(time.perf_counter() - started, 1),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--schedules", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--out", default=str(ROOT / "metrics" / "raw" / "reliability.json"))
    args = parser.parse_args()
    out = {"requirement_cadence": simulate(args.schedules, args.seed, "requirement"),
           "deployment_cadence": simulate(args.schedules, args.seed + 1, "deployment")}
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=2) + "\n")
    for name, r in out.items():
        print(f"{name}: {r['schedules']} schedules, early={r['early_releases']}, duplicates={r['duplicate_releases']}, "
              f"missed={r['missed_releases']}, max lateness={r['max_lateness_s']} s, "
              f"max prompt delay={r['max_prompt_delay_s']} s ({r['runtime_s']} s)")


if __name__ == "__main__":
    main()
