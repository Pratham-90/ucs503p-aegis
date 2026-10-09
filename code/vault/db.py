"""Engine and session factory. SQLite locally, Postgres (Neon) in deployment (NFR-PORT-1)."""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool, StaticPool

from .models import Base

DEFAULT_URL = "sqlite:///./aegis.db"


def normalize_url(url: str) -> str:
    """Neon/Vercel hand out ``postgres://`` or ``postgresql://`` URLs; use the psycopg 3 driver."""
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


def make_engine(url: str | None = None) -> Engine:
    url = normalize_url(url or os.environ.get("DATABASE_URL") or DEFAULT_URL)
    if url.startswith("sqlite"):
        kwargs: dict = {"connect_args": {"check_same_thread": False}}
        if url in ("sqlite://", "sqlite:///:memory:"):
            kwargs["poolclass"] = StaticPool
        engine = create_engine(url, **kwargs)

        @event.listens_for(engine, "connect")
        def _sqlite_pragmas(dbapi_conn, _record):  # pragma: no cover - trivial
            dbapi_conn.isolation_level = None  # let SQLAlchemy emit BEGIN itself (below)
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA foreign_keys=ON")
            cur.execute("PRAGMA busy_timeout=10000")
            cur.close()

        @event.listens_for(engine, "begin")
        def _sqlite_begin_immediate(conn):  # pragma: no cover - trivial
            # Take the write lock up front so concurrent ticks serialise instead of
            # both reading a vault before either commits (Postgres uses FOR UPDATE).
            conn.exec_driver_sql("BEGIN IMMEDIATE")

        return engine
    # Serverless functions do not keep a process alive, so do not pool connections.
    return create_engine(url, poolclass=NullPool, pool_pre_ping=True)


class Database:
    def __init__(self, url: str | None = None) -> None:
        self.engine = make_engine(url)
        self.Session = sessionmaker(self.engine, expire_on_commit=False)

    @property
    def is_postgres(self) -> bool:
        return self.engine.dialect.name == "postgresql"

    def create_all(self) -> None:
        Base.metadata.create_all(self.engine)

    def drop_all(self) -> None:
        Base.metadata.drop_all(self.engine)

    @contextmanager
    def session(self) -> Iterator[Session]:
        s = self.Session()
        try:
            yield s
            s.commit()
        except Exception:
            s.rollback()
            raise
        finally:
            s.close()

    def dispose(self) -> None:
        self.engine.dispose()
