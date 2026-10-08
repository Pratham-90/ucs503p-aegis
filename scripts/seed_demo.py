"""Seed a ready-made demo vault so presenters can jump straight to step 6 (brief section 1).

Runs the *client-side* steps (keypairs, AES-GCM, Shamir split, RSA-OAEP wrapping)
with the Python crypto and talks to the API over HTTP, exactly like the browser,
so it works against a local server or the deployed URL without database access.

    python scripts/seed_demo.py --base-url https://<deployment>.vercel.app

Requires DEMO_MODE=true on the target (minute-scale schedule). Writes, into the
git-ignored demo-keys/ directory: each trustee's private key file (same format
the browser downloads), their portal links, and the owner's credentials.
The owner password comes from DEMO_OWNER_PASSWORD, or is generated.
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "code"))

import httpx  # noqa: E402

from api.testing import ScriptedBrowser  # noqa: E402

OWNER = "demo-owner@example.com"
TRUSTEES = ["demo-alice@example.com", "demo-bob@example.com", "demo-carol@example.com"]
MESSAGE = (
    "Aegis demo vault.\n\nIf you are reading this, two of my three trustees combined their shares after I "
    "stopped checking in. The (fictional) bank details are in the blue folder; the solicitor is J. Rao."
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--interval", type=int, default=120, help="check-in interval in seconds")
    parser.add_argument("--grace", type=int, default=60, help="grace period in seconds")
    parser.add_argument("--out", default=str(ROOT / "demo-keys"))
    args = parser.parse_args()

    password = os.environ.get("DEMO_OWNER_PASSWORD") or secrets.token_urlsafe(12)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    base = args.base_url.rstrip("/")
    with httpx.Client(base_url=base, timeout=60) as client:
        health = client.get("/api/health").json()
        if not health.get("demo_mode"):
            raise SystemExit("The target is not in DEMO_MODE; refusing to seed a minute-scale demo vault.")
        try:
            vault = ScriptedBrowser(client).create_vault(
                owner_email=OWNER, password=password, trustee_emails=TRUSTEES, k=2,
                interval_s=args.interval, grace_s=args.grace, message=MESSAGE,
                file={"name": "demo-instructions.txt", "type": "text/plain",
                      "data": "VGhpcyBmaWxlIHdhcyBpbiB0aGUgdmF1bHQu"})  # "This file was in the vault."
        except httpx.HTTPStatusError as exc:
            detail = exc.response.json().get("error", {})
            hint = "If the demo owner already has a vault, use 'Reset demo data' in the Demo Console."
            raise SystemExit(f"Seeding failed: {detail.get('code')}: {detail.get('message')}\n{hint}") from exc

    lines = [f"Aegis demo seed — {datetime.now(UTC).isoformat(timespec='seconds')}", f"Target: {base}", "",
             f"Owner login: {OWNER} / {password}", f"Vault id: {vault.vault_id}  (K = 2 of N = 3)", ""]
    for position, (email, token, private_jwk) in enumerate(
            zip(TRUSTEES, vault.trustee_tokens, vault.trustee_private_jwks, strict=True), start=1):
        key_file = {"format": "aegis-trustee-key/v1", "vault_id": vault.vault_id, "position": position,
                    "email": email, "created_at": datetime.now(UTC).isoformat(), "private_jwk": private_jwk}
        path = out / f"aegis-trustee-{email}.json"
        path.write_text(json.dumps(key_file, indent=2))
        lines.append(f"Trustee #{position} {email}\n  portal: {base}/trustee?t={token}\n  key file: {path.name}")
    (out / "README.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"\nWrote key files and README.txt to {out} (git-ignored).")


if __name__ == "__main__":
    main()
