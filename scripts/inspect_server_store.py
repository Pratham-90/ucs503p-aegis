"""Zero-knowledge inspection (NFR-SEC-1, NFR-SEC-5; brief section 8).

Creates vaults whose secrets are known, then scans *everything the server
holds* for them: every column of every row of every table, and every request
body the server received. A finding is any occurrence of the plaintext message,
the attached file contents, the AES key, or any plaintext share, in any of:
raw bytes, UTF-8, standard/URL-safe base64, hex, or nested JSON.

Two sources:
  scripted  the client steps replayed with the authoritative Python crypto
            through the real API (TestClient); request bodies are recorded.
  e2e       the database left by the Playwright run of the real browser UI
            (e2e.db), with the secrets the test observed
            (frontend/test-results/e2e-known-secrets.json). The AES key is
            reconstructed from two of those shares, so it can be searched for too.

Usage:  python scripts/inspect_server_store.py [--out metrics/raw/zero_knowledge.json]
"""

from __future__ import annotations

import argparse
import base64
import binascii
import json
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "code"))

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import inspect, text  # noqa: E402

from api.app import create_app  # noqa: E402
from api.config import Settings  # noqa: E402
from api.testing import ScriptedBrowser  # noqa: E402
from crypto import int_to_key, reconstruct_secret, share_from_bytes, share_from_text, share_to_text  # noqa: E402
from crypto.encoding import FIELD_BYTES, share_to_bytes  # noqa: E402
from vault.db import Database  # noqa: E402

B64 = re.compile(r"[A-Za-z0-9+/=_-]{16,}")
HEX = re.compile(r"(?:[0-9a-fA-F]{2}){16,}")


def decodings(value) -> list[bytes]:
    """Every plausible byte decoding of a stored value."""
    if value is None:
        return []
    if isinstance(value, (bytes, bytearray, memoryview)):
        return [bytes(value)]
    s = str(value)
    out = [s.encode("utf-8", "ignore")]
    for token in B64.findall(s):
        token = token.rstrip("=")
        for shift in range(4):  # base64 embedded after other characters may start at any alignment
            part = token[shift:]
            for decoder in (base64.b64decode, base64.urlsafe_b64decode):
                try:
                    out.append(decoder(part + "=" * (-len(part) % 4)))
                except (binascii.Error, ValueError):
                    pass
    for token in HEX.findall(s):
        try:
            out.append(bytes.fromhex(token))
        except ValueError:
            pass
    try:  # nested JSON values
        parsed = json.loads(s)
        if isinstance(parsed, (dict, list)):
            for leaf in _leaves(parsed):
                out += decodings(leaf)
    except (ValueError, TypeError):
        pass
    return out


def _leaves(obj):
    if isinstance(obj, dict):
        for v in obj.values():
            yield from _leaves(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _leaves(v)
    else:
        yield obj


def needles_for(message: str, file_bytes: bytes | None, key: bytes | None, share_texts: list[str]) -> dict[str, bytes]:
    needles = {"plaintext message": message.encode()}
    if file_bytes:
        needles["attached file contents"] = file_bytes
    if key:
        needles["AES key"] = key
    for i, t in enumerate(share_texts, 1):
        share = share_from_text(t)
        needles[f"share {i} (text)"] = t.encode()
        needles[f"share {i} (bytes)"] = share_to_bytes(share)
        needles[f"share {i} (y)"] = share.y.to_bytes(FIELD_BYTES, "big")
    return needles


def scan_database(url: str, needles: dict[str, bytes]) -> tuple[list[dict], int, int]:
    db = Database(url)
    findings, rows_scanned, values_scanned = [], 0, 0
    with db.engine.connect() as conn:
        for table in inspect(db.engine).get_table_names():
            for row in conn.execute(text(f'SELECT * FROM "{table}"')).mappings():
                rows_scanned += 1
                for column, value in row.items():
                    values_scanned += 1
                    for blob in decodings(value):
                        for name, needle in needles.items():
                            if needle and needle in blob:
                                findings.append({"where": f"{table}.{column}", "found": name})
    db.dispose()
    return findings, rows_scanned, values_scanned


def scan_requests(bodies: list[str], needles: dict[str, bytes]) -> list[dict]:
    findings = []
    for i, body in enumerate(bodies):
        for blob in decodings(body):
            for name, needle in needles.items():
                if needle and needle in blob:
                    findings.append({"where": f"request #{i}", "found": name})
    return findings


def scripted_run() -> dict:
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        url = f"sqlite:///{Path(tmp, 'zk.db').as_posix()}"
        settings = Settings(database_url=url, demo_mode=True, demo_admin_token="zk", app_base_url="http://testserver")
        app = create_app(settings, db=Database(url))
        message = "ZK-MARKER-9b1e: the safe combination is 31-7-22"
        file_body = b"ZK-FILE-MARKER-c44d"
        with TestClient(app) as client:
            browser = ScriptedBrowser(client)
            vault = browser.create_vault(
                owner_email="zk@example.com", password="correct horse", k=2, interval_s=120, grace_s=60,
                trustee_emails=["zk-a@example.com", "zk-b@example.com", "zk-c@example.com"], message=message,
                file={"name": "combo.txt", "type": "text/plain", "data": base64.b64encode(file_body).decode()},
            )
            share_texts = [share_to_text(share_from_bytes(raw)) for raw in vault.shares_bytes]
            # run the whole lifecycle so outbox, tokens and tick logs exist too
            client.post("/api/demo/clock/advance", json={"seconds": 200}, headers={"X-Demo-Token": "zk"})
            client.post("/api/demo/tick", headers={"X-Demo-Token": "zk"})
            needles = needles_for(message, file_body, vault.key, share_texts)
            needles["file contents (base64, as in the envelope)"] = base64.b64encode(file_body)
        app.state.db.dispose()
        db_findings, rows, values = scan_database(url, needles)
        req_findings = scan_requests(browser.sent, needles)
    return {"source": "scripted client (Python crypto) through the real API", "needles": list(needles),
            "rows_scanned": rows, "values_scanned": values, "requests_scanned": len(browser.sent),
            "findings": db_findings + req_findings}


def e2e_run() -> dict | None:
    secrets_file = ROOT / "frontend" / "test-results" / "e2e-known-secrets.json"
    db_file = ROOT / "e2e.db"
    if not (secrets_file.exists() and db_file.exists()):
        return None
    known = json.loads(secrets_file.read_text())
    shares = [share_from_text(t) for t in known["shares"]]
    key = int_to_key(reconstruct_secret(shares))  # derived from two shares, never seen by the server
    needles = needles_for(known["marker"], known["file_marker"].encode(), key, known["shares"])
    findings, rows, values = scan_database(f"sqlite:///{db_file.as_posix()}", needles)
    return {"source": "database left by the Playwright run of the real browser UI (e2e.db)",
            "needles": list(needles), "rows_scanned": rows, "values_scanned": values, "findings": findings}


def self_test() -> dict:
    """Positive control: the scanner must find a planted secret in every encoding it claims to cover."""
    secret = b"PLANTED-SECRET-0123456789-abcdef"
    planted = {
        "raw bytes": secret,
        "utf-8 text": "prefix " + secret.decode() + " suffix",
        "base64": "x" + base64.b64encode(secret).decode(),
        "base64url": base64.urlsafe_b64encode(secret).decode().rstrip("="),
        "hex": secret.hex(),
        "nested json": json.dumps({"a": [{"b": base64.b64encode(secret).decode()}]}),
    }
    detected = {name: any(secret in blob for blob in decodings(value)) for name, value in planted.items()}
    detected["utf-8 text"] = any(secret.decode("latin-1").encode() in b for b in decodings(planted["utf-8 text"]))
    if not all(detected.values()):
        raise SystemExit(f"scanner self-test FAILED: {detected}")
    return detected


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", default=str(ROOT / "metrics" / "raw" / "zero_knowledge.json"))
    args = parser.parse_args()
    control = self_test()
    print(f"scanner self-test passed for: {', '.join(control)}")
    results = {"scripted": scripted_run(), "e2e": e2e_run()}
    total = sum(len(r["findings"]) for r in results.values() if r)
    results["total_findings"] = total
    results["scanner_self_test"] = control
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(results, indent=2) + "\n")
    for name in ("scripted", "e2e"):
        r = results[name]
        if r is not None:
            print(f"{name}: {r['rows_scanned']} rows / {r['values_scanned']} values scanned for "
                  f"{len(r['needles'])} secrets -> {len(r['findings'])} findings")
        else:
            print("e2e: skipped (run the Playwright test first)")
    print(f"total findings: {total}")


if __name__ == "__main__":
    main()
