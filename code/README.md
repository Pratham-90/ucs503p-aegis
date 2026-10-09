# `code/` — Aegis application source (Python)

One package per responsibility. `pyproject.toml` puts this directory on the
import path for pytest (`[tool.pytest.ini_options] pythonpath = ["code"]`), so
each package is imported by its top-level name (`import crypto`, `import scheduler`, …).

```
code/
├── crypto/          authoritative Shamir + encodings; test_vectors.json (FR-2a, FR-4, FR-8, NFR-SEC-2)
├── scheduler/       pure evaluate() and transactional tick() (FR-5, FR-7, NFR-REL-1/2/3)
├── vault/           SQLAlchemy models, engine/session, repositories (NFR-PORT-1)
├── notifications/   outbox with exactly-once dedupe keys, EmailSender (log / Resend)
├── api/             FastAPI app: auth, vaults, check-in links, trustee, cron, demo
├── spikes/          the Week-1 throwaway Shamir spike (kept for history)
└── tests/           pytest suites
```

## How the deployed function imports these packages

Decision (brief section 3): **keep the packages in `code/` and put `code/` on
`sys.path` in the Vercel entry file**, rather than restructuring into an
installable `aegis` package. `api/index.py` (the Vercel function) does:

1. insert `code/` at the front of `sys.path`;
2. drop any already-imported module named `api` — the entry file sits in a
   top-level directory that is *also* called `api` (Vercel requires that name),
   so without this the import could resolve to the wrong package;
3. `importlib.import_module("api.main").app`.

`scripts/run_local_server.py` does the same for uvicorn. This kept every test,
import and the pytest configuration unchanged.

## Tests

```bash
python -m pytest                                   # 125 tests
python -m pytest --cov=code/crypto --cov=code/scheduler   # NFR-MAINT-1 (>= 80%)
```

Use path-style `--cov=code/<pkg>`: `--cov=api` would match the root `api/` entry.
