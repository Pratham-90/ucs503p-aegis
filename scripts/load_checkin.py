"""Check-in latency (NFR-PERF-1: p95 <= 500 ms; brief section 8).

Creates a throwaway owner + armed vault through the real API (client steps done
with the Python crypto), then measures POST /api/vaults/{id}/checkin:
the first request (cold start) separately, 200 sequential, and 50 concurrent.

    python scripts/load_checkin.py --base-url https://<deployment>.vercel.app --label deployed
    python scripts/load_checkin.py --base-url http://127.0.0.1:8000 --label local

The vault needs DEMO_MODE=true on the target (2-minute interval).
"""

from __future__ import annotations

import argparse
import json
import secrets
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "code"))

import httpx  # noqa: E402

from api.testing import ScriptedBrowser  # noqa: E402


def percentile(samples: list[float], q: float) -> float:
    ordered = sorted(samples)
    return round(ordered[min(len(ordered) - 1, int(q * len(ordered)))], 1)


def summary(samples: list[float]) -> dict:
    return {"n": len(samples), "p50_ms": percentile(samples, 0.50), "p95_ms": percentile(samples, 0.95),
            "p99_ms": percentile(samples, 0.99), "mean_ms": round(statistics.fmean(samples), 1),
            "max_ms": round(max(samples), 1)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--label", required=True, help="e.g. local or deployed")
    parser.add_argument("--sequential", type=int, default=200)
    parser.add_argument("--concurrent", type=int, default=50)
    parser.add_argument("--out", default=None)
    args = parser.parse_args()
    out_path = Path(args.out or ROOT / "metrics" / "raw" / f"checkin_latency_{args.label}.json")

    tag = secrets.token_hex(4)
    with httpx.Client(base_url=args.base_url.rstrip("/"), timeout=60) as client:
        vault = ScriptedBrowser(client).create_vault(
            owner_email=f"load-{tag}@example.com", password="load-test-password",
            trustee_emails=[f"load-{tag}-{i}@example.com" for i in range(3)], k=2, interval_s=120, grace_s=60,
            message=f"load test {tag}")
        url = f"/api/vaults/{vault.vault_id}/checkin"

        def one() -> float:
            t0 = time.perf_counter()
            r = client.post(url)
            r.raise_for_status()
            return (time.perf_counter() - t0) * 1000

        cold = one()
        sequential = [one() for _ in range(args.sequential)]
        with ThreadPoolExecutor(max_workers=args.concurrent) as pool:
            concurrent = list(pool.map(lambda _: one(), range(args.concurrent)))

    measured_at = datetime.now(UTC).isoformat(timespec="seconds")
    result = {"label": args.label, "base_url": args.base_url, "measured_at": measured_at,
              "first_request_ms": round(cold, 1), "sequential": summary(sequential),
              "concurrent": summary(concurrent), "all_warm": summary(sequential + concurrent)}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: result[k] for k in ("label", "first_request_ms", "sequential", "concurrent")}, indent=2))


if __name__ == "__main__":
    main()
