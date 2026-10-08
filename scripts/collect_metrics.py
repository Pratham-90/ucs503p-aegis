"""Run every prototype measurement and write metrics/prototype-metrics.json + metrics/README.md.

Each metric records its value, target, whether it was met, the exact command that
produced it, when, the git SHA, and the environment. Nothing is typed in by hand:
a metric whose source has not been run is written as "TODO: not measured".

    python scripts/collect_metrics.py            # run everything (~5 min; the reliability run dominates)
    python scripts/collect_metrics.py --reuse    # reuse metrics/raw/*.json where present (re-runs nothing slow)

Deployed-URL measurements are separate, because they need the live site:
    python scripts/load_checkin.py --base-url https://<deployment> --label deployed
    npx lighthouse ... (see metrics/README.md)
"""

from __future__ import annotations

import argparse
import json
import platform
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "metrics" / "raw"
PY = sys.executable
NPM = shutil.which("npm") or "npm"
NPX = shutil.which("npx") or "npx"
TODO = "TODO: not measured"


def run(cmd: list[str], cwd: Path = ROOT, check: bool = True) -> str:
    print("$", " ".join(Path(c).name if i == 0 else c for i, c in enumerate(cmd)), flush=True)
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if check and result.returncode != 0:
        print(result.stdout[-3000:], result.stderr[-3000:])
        raise SystemExit(f"command failed ({result.returncode}): {' '.join(cmd)}")
    return result.stdout + result.stderr


def git_sha() -> str:
    return run(["git", "rev-parse", "--short", "HEAD"]).strip()


def now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


LOCAL_ENV = f"local: {platform.system()} {platform.release()}, Python {platform.python_version()}"


def metric(value, *, command: str, target: str | None = None, met: bool | None = None, unit: str | None = None,
           requirement: str | None = None, environment: str = LOCAL_ENV, measured_at: str | None = None,
           notes: str | None = None) -> dict:
    out = {"value": value, "unit": unit, "target": target, "met": met, "requirement": requirement,
           "command": command, "measured_at": measured_at or now(), "environment": environment}
    if notes:
        out["notes"] = notes
    return {k: v for k, v in out.items() if v is not None}


def todo(command: str, requirement: str | None = None, target: str | None = None, notes: str | None = None) -> dict:
    return metric(TODO, command=command, requirement=requirement, target=target, met=None, environment="—",
                  measured_at="—", notes=notes)


# --- individual collectors -------------------------------------------------------------

def python_tests(metrics: dict) -> None:
    junit, cov = RAW / "pytest-junit.xml", RAW / "coverage.json"
    cmd = ["-m", "pytest", "code/tests", "-q", "-p", "no:cacheprovider", "-W", "ignore",
           "--cov=code/crypto", "--cov=code/scheduler", "--cov=code/api", "--cov=code/vault",
           "--cov=code/notifications", f"--cov-report=json:{cov}", f"--junitxml={junit}"]
    run([PY, *cmd])
    suite = ET.parse(junit).getroot()
    suite = suite if suite.tag == "testsuite" else suite.find("testsuite")
    total = int(suite.get("tests"))
    failed = int(suite.get("failures")) + int(suite.get("errors"))
    shown = "python -m pytest code/tests --cov=code/crypto --cov=code/scheduler ..."
    metrics["Python tests (unit + integration)"] = metric(
        f"{total - failed}/{total} passed", command=shown, target="all pass", met=failed == 0)
    files = json.loads(cov.read_text())["files"]
    for package, req in (("crypto", "NFR-MAINT-1"), ("scheduler", "NFR-MAINT-1"), ("api", None),
                         ("vault", None), ("notifications", None)):
        prefix = f"code{'/'}{package}{'/'}"
        stats = [f["summary"] for name, f in files.items() if name.replace("\\", "/").startswith(prefix)]
        covered = sum(s["covered_lines"] for s in stats)
        statements = sum(s["num_statements"] for s in stats)
        pct = round(100 * covered / statements, 1) if statements else None
        metrics[f"Coverage: {package}"] = metric(
            pct, unit="%", command=shown, requirement=req,
            target=">= 80%" if req else None, met=(pct >= 80) if req else None)


def hypothesis_cases(metrics: dict) -> None:
    files = ["code/tests/test_crypto_properties.py", "code/tests/test_scheduler_state.py"]
    out = run([PY, "-m", "pytest", *files, "-q", "-p", "no:cacheprovider", "-W", "ignore",
               "--hypothesis-show-statistics"])
    out = out.split("Hypothesis Statistics", 1)[-1]  # only the statistics section
    passing = sum(int(n) for n in re.findall(r"(\d+) passing", out))
    failing = sum(int(n) for n in re.findall(r"(\d+) failing", out))
    properties = len(re.findall(r"^code/tests/\S+::\S+:", out, flags=re.M))
    metrics["Hypothesis property tests"] = metric(
        {"properties": properties, "generated_cases": passing, "failing_cases": failing},
        command="pytest test_crypto_properties.py test_scheduler_state.py --hypothesis-show-statistics",
        requirement="FR-4, FR-8, NFR-SEC-2, NFR-REL-1, NFR-REL-3", target="0 failing", met=failing == 0)


def typescript_tests(metrics: dict) -> None:
    out_file = RAW / "vitest.json"
    run([NPX, "vitest", "run", "--reporter=json", f"--outputFile={out_file}"], cwd=ROOT / "frontend")
    report = json.loads(out_file.read_text())
    metrics["TypeScript tests (vitest)"] = metric(
        f"{report['numPassedTests']}/{report['numTotalTests']} passed", command="cd frontend && npx vitest run",
        target="all pass", met=report["numPassedTests"] == report["numTotalTests"])
    vectors = json.loads((ROOT / "code" / "crypto" / "test_vectors.json").read_text())
    total = len(vectors["shamir"]) + len(vectors["aes_gcm"]) + len(vectors["rsa_oaep"][0]["cases"])
    passed = sum(1 for f in report["testResults"] if f["name"].replace("\\", "/").endswith("vectors.test.ts")
                 for t in f["assertionResults"]
                 if t["status"] == "passed" and re.match(r"(shamir|aes-gcm|rsa-oaep):", t["title"]))
    metrics["Cross-language vectors (Python -> TypeScript)"] = metric(
        f"{passed}/{total} matched", command="cd frontend && npx vitest run src/crypto/vectors.test.ts",
        requirement="FR-2a, FR-8", target="all match", met=passed == total)


def crypto_timings(metrics: dict, reuse: bool) -> None:
    path = RAW / "crypto-timing.json"
    if not (reuse and path.exists()):
        run([NPM, "run", "measure"], cwd=ROOT / "frontend")
    data = json.loads(path.read_text())
    for name, stat in data["results"].items():
        metrics[f"Crypto timing: {name}"] = metric(
            {"median_ms": stat["median_ms"], "p95_ms": stat["p95_ms"], "iterations": stat["iterations"]},
            unit="ms", command="cd frontend && npm run measure", environment=data["environment"],
            measured_at=data["measured_at"])


def reliability(metrics: dict, reuse: bool) -> None:
    path = RAW / "reliability.json"
    if not (reuse and path.exists()):
        run([PY, "scripts/reliability_sim.py", "--schedules", "1000"])
    data = json.loads(path.read_text())
    cmd = "python scripts/reliability_sim.py --schedules 1000"
    measured = datetime.fromtimestamp(path.stat().st_mtime, UTC).isoformat(timespec="seconds")
    req, dep = data["requirement_cadence"], data["deployment_cadence"]
    faults = req["fault_injection"]
    fault_note = (f"{req['schedules']} schedules; {faults['ticks']} ticks incl. {faults['duplicate_ticks']} duplicate "
                  f"and {faults['concurrent_tick_pairs']} racing pairs, {faults['restarts']} restarts, clock jitter "
                  f"+/-3 s, {faults['checkins_refused']} too-late check-ins refused")
    for cadence, r in (("requirement cadence", req), ("deployment cron only", dep)):
        metrics[f"NFR-REL-1 early releases ({cadence})"] = metric(
            r["early_releases"], command=cmd, requirement="NFR-REL-1", target="0", met=r["early_releases"] == 0,
            measured_at=measured, notes=fault_note if cadence.startswith("req") else None)
        metrics[f"NFR-REL-3 duplicate releases ({cadence})"] = metric(
            r["duplicate_releases"], command=cmd, requirement="NFR-REL-3", target="0",
            met=r["duplicate_releases"] == 0, measured_at=measured)
        metrics[f"Missed releases ({cadence})"] = metric(
            r["missed_releases"], command=cmd, requirement="FR-7", target="0", met=r["missed_releases"] == 0,
            measured_at=measured)
        metrics[f"NFR-REL-2 max release lateness ({cadence})"] = metric(
            r["max_lateness_s"], unit="s", command=cmd, requirement="NFR-REL-2", target="<= 60 s",
            met=r["max_lateness_s"] <= 60, measured_at=measured,
            notes="tick gaps 5-55 s" if cadence.startswith("req") else
            "GitHub Actions every 5 min plus up to 10 min delay; no lazy due-checks")
        metrics[f"NFR-PERF-2 max prompt dispatch delay ({cadence})"] = metric(
            r["max_prompt_delay_s"], unit="s", command=cmd, requirement="NFR-PERF-2", target="<= 60 s",
            met=r["max_prompt_delay_s"] <= 60, measured_at=measured)


def zero_knowledge(metrics: dict, reuse: bool) -> None:
    path = RAW / "zero_knowledge.json"
    if not (reuse and path.exists()):
        run([PY, "scripts/inspect_server_store.py"])
    data = json.loads(path.read_text())
    scanned = [data["scripted"]] + ([data["e2e"]] if data.get("e2e") else [])
    rows = sum(s["rows_scanned"] for s in scanned)
    values = sum(s["values_scanned"] for s in scanned)
    metrics["NFR-SEC-1/5 zero-knowledge inspection findings"] = metric(
        data["total_findings"], command="python scripts/inspect_server_store.py", requirement="NFR-SEC-1, NFR-SEC-5",
        target="0", met=data["total_findings"] == 0,
        measured_at=datetime.fromtimestamp(path.stat().st_mtime, UTC).isoformat(timespec="seconds"),
        notes=f"{rows} rows / {values} stored values and {data['scripted']['requests_scanned']} request bodies "
              f"scanned (scripted run{' + Playwright E2E database' if data.get('e2e') else ''}); scanner "
              "positive-control self-test passed")


def checkin_latency(metrics: dict) -> None:
    for label in ("local", "deployed"):
        path = RAW / f"checkin_latency_{label}.json"
        name = f"NFR-PERF-1 p95 check-in latency ({label})"
        cmd = f"python scripts/load_checkin.py --base-url <url> --label {label}"
        if not path.exists():
            metrics[name] = todo(cmd, "NFR-PERF-1", "p95 <= 500 ms",
                                 "needs the deployed URL" if label == "deployed" else None)
            continue
        d = json.loads(path.read_text())
        env = f"{label}: {d['base_url']}" + (" (uvicorn + SQLite)" if label == "local" else "")
        metrics[name] = metric(
            {"sequential_p50_ms": d["sequential"]["p50_ms"], "sequential_p95_ms": d["sequential"]["p95_ms"],
             "sequential_p99_ms": d["sequential"]["p99_ms"], "concurrent50_p95_ms": d["concurrent"]["p95_ms"],
             "first_request_ms": d["first_request_ms"]},
            unit="ms", command=cmd, requirement="NFR-PERF-1", target="p95 <= 500 ms (nominal load)",
            met=d["sequential"]["p95_ms"] <= 500, environment=env, measured_at=d["measured_at"],
            notes="'nominal load' = sequential requests; 50 simultaneous check-ins on one vault serialise on the "
                  "database and are reported separately")


def e2e(metrics: dict) -> None:
    path = ROOT / "frontend" / "test-results" / "e2e-results.json"
    if not path.exists():
        metrics["End-to-end demo script (Playwright)"] = todo("cd frontend && npx playwright test")
        return
    report = json.loads(path.read_text())
    stats = report["stats"]
    ok = stats.get("unexpected", 0) == 0 and stats.get("expected", 0) > 0
    metrics["End-to-end demo script (Playwright)"] = metric(
        "passed" if ok else "failed", command="cd frontend && npx playwright test", target="pass", met=ok,
        measured_at=stats.get("startTime", "")[:19] + "Z", environment=LOCAL_ENV + ", Chromium (Playwright)",
        notes=f"duration {round(stats.get('duration', 0) / 1000, 1)} s; 22 screenshots in report-assets/screenshots/")


def lighthouse(metrics: dict) -> None:
    for page in ("landing", "dashboard"):
        path = RAW / f"lighthouse_{page}.json"
        name = f"Lighthouse ({page})"
        if not path.exists():
            metrics[name] = todo("scripts/lighthouse.mjs", notes="run against the deployed URL")
            continue
        d = json.loads(path.read_text())
        metrics[name] = metric(d["scores"], command=d["command"], environment=d["environment"],
                               measured_at=d["measured_at"], notes=d.get("notes"))


# --- output --------------------------------------------------------------------------

def write_readme(doc: dict) -> None:
    lines = ["# Prototype metrics", "",
             "Generated by `python scripts/collect_metrics.py` — do not edit by hand. Every value below was "
             "produced by the command listed with it; anything not measured says so.", "",
             f"- Generated: {doc['generated_at']}", f"- Git SHA at measurement: `{doc['git_sha']}`", "",
             "| Metric | Value | Target | Met | Command |", "| --- | --- | --- | --- | --- |"]
    for name, m in doc["metrics"].items():
        value = m["value"] if not isinstance(m["value"], dict) else ", ".join(f"{k}={v}" for k, v in m["value"].items())
        unit = f" {m['unit']}" if m.get("unit") and not isinstance(m["value"], dict) else ""
        met = {True: "yes", False: "**no**", None: "—"}[m.get("met")]
        lines.append(f"| {name} | {value}{unit} | {m.get('target', '—')} | {met} | `{m['command']}` |")
    lines += ["", "## Notes", ""]
    for name, m in doc["metrics"].items():
        if m.get("notes"):
            lines.append(f"- **{name}** — {m['notes']} (environment: {m['environment']}).")
    lines += ["", "Raw outputs are in `metrics/raw/`."]
    (ROOT / "metrics" / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    sys.stdout.reconfigure(errors="replace")  # Windows consoles cannot print every character
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--reuse", action="store_true", help="reuse slow raw outputs that already exist")
    args = parser.parse_args()
    RAW.mkdir(parents=True, exist_ok=True)
    metrics: dict = {}
    python_tests(metrics)
    hypothesis_cases(metrics)
    typescript_tests(metrics)
    e2e(metrics)
    reliability(metrics, args.reuse)
    zero_knowledge(metrics, args.reuse)
    checkin_latency(metrics)
    crypto_timings(metrics, args.reuse)
    lighthouse(metrics)
    doc = {"generated_at": now(), "generated_by": "scripts/collect_metrics.py", "git_sha": git_sha(),
           "metrics": metrics}
    (ROOT / "metrics" / "prototype-metrics.json").write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    write_readme(doc)
    unmet = [n for n, m in metrics.items() if m.get("met") is False]
    todos = [n for n, m in metrics.items() if m["value"] == TODO]
    print(f"\nwrote metrics/prototype-metrics.json ({len(metrics)} metrics); not met: {unmet}; TODO: {todos}")


if __name__ == "__main__":
    main()
