# `code/` — Aegis application source

Python packages, one per bounded responsibility. `pyproject.toml` puts this
directory on the import path (`[tool.pytest.ini_options] pythonpath = ["code"]`),
so each package is importable by its top-level name.

```
code/
├── crypto/          Shamir secret sharing + payload encryption (security core)
├── scheduler/       the check-in clock; drives the vault lifecycle
├── vault/           domain models & repositories (SQLAlchemy)
├── notifications/   outbound SMTP messaging
├── api/             FastAPI application layer
├── spikes/          throwaway feasibility experiments (NOT production code)
└── tests/           pytest suite
```

Each package carries its own `README.md` describing its responsibility. Week 1
ships the scaffold and a smoke test only; implementation lands module-by-module
across later weeks (see `docs/plan/twelve-week-plan.md`).

## Running the tests

```bash
python -m pip install pytest
python -m pytest
```

The template's CI (`.github/workflows/mkdocs.yml`) builds and deploys the docs
site; it does not run the test suite. Run pytest locally before committing.
