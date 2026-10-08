"""Run the Aegis API locally with uvicorn (local development and the Playwright E2E).

    python scripts/run_local_server.py [--db aegis.db] [--fresh] [--port 8000]

Defaults are for a laptop only: SQLite, DEMO_MODE on, EMAIL_MODE=log. Any of the
environment variables in .env.example can override them.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="aegis.db", help="SQLite file name, relative to the repo root")
    parser.add_argument("--fresh", action="store_true", help="delete the database first")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    db_path = ROOT / args.db
    if args.fresh and db_path.exists():
        db_path.unlink()
    os.environ.setdefault("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    os.environ.setdefault("DEMO_MODE", "true")
    os.environ.setdefault("EMAIL_MODE", "log")
    os.environ.setdefault("APP_BASE_URL", "http://127.0.0.1:5173")
    os.environ.setdefault("DEMO_ADMIN_TOKEN", "local-demo-token")
    os.environ.setdefault("CRON_SECRET", "local-cron-secret")

    sys.path.insert(0, str(ROOT / "code"))
    import uvicorn

    uvicorn.run("api.main:app", host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
