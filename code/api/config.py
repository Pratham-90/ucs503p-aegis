"""Runtime configuration from environment variables (see .env.example)."""

from __future__ import annotations

import os
from dataclasses import dataclass


def _bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    return default if value is None else value.strip().lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class Settings:
    database_url: str = "sqlite:///./aegis.db"
    jwt_secret: str = "dev-insecure-jwt-secret-change-me"
    cron_secret: str = ""
    demo_admin_token: str = ""
    email_mode: str = "log"
    app_base_url: str = "http://localhost:5173"
    demo_mode: bool = False  # secure default; the deployed prototype sets DEMO_MODE=true
    session_hours: int = 12
    #: Owner check-in intervals must be >= 1 day unless DEMO_MODE is on (FR-3).
    min_interval_s_production: int = 86_400
    min_interval_s_demo: int = 30
    max_trustees: int = 10
    #: In-flight requests per process; must stay well below the 40-thread pool (see app.py).
    max_concurrent_requests: int = 16
    max_ciphertext_bytes: int = 1_450_000  # a 1 MB file, base64'd inside the JSON envelope, + AES-GCM tag

    @property
    def cookie_secure(self) -> bool:
        return self.app_base_url.startswith("https://")

    @property
    def min_interval_s(self) -> int:
        return self.min_interval_s_demo if self.demo_mode else self.min_interval_s_production

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            database_url=os.environ.get("DATABASE_URL", cls.database_url),
            jwt_secret=os.environ.get("JWT_SECRET", cls.jwt_secret),
            cron_secret=os.environ.get("CRON_SECRET", ""),
            demo_admin_token=os.environ.get("DEMO_ADMIN_TOKEN", ""),
            email_mode=os.environ.get("EMAIL_MODE", "log"),
            app_base_url=os.environ.get("APP_BASE_URL", cls.app_base_url).rstrip("/"),
            demo_mode=_bool("DEMO_MODE", False),
        )
