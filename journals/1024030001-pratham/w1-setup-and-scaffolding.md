# Week 1 : Project Setup, Requirements, and Scaffolding

**Date:** 2026-08-10 · **Semester:** 2026-27 ODD · **Project:** Aegis (solo)

## Goal for the week

Stand up the repository and produce the Week-1 requirements/scaffolding
deliverables — no application behaviour yet.

## What was set up

- Cloned the institute template, removed its git history, and re-initialised a
  fresh repository on branch `main`.
- Created a **private** GitHub repository `ucs503p-aegis` under my account and
  wired it as `origin`.
- Read the whole template first (Makefile, `mkdocs.yml`, `pyproject.toml`, the
  CI workflow, and the sample content) before writing anything.
- **Module scaffold** under `code/`: five responsibility-scoped packages —
  `crypto`, `scheduler`, `vault`, `notifications`, `api` — each with an
  `__init__` docstring and a `README` stub, plus a passing smoke test
  (`code/tests/test_smoke.py`, 5 passed).
- **SRS** in `project-proposal/main.tex` (template LaTeX style) and a Markdown
  mirror at `docs/srs/index.md`.
- **Diagrams** in `docs/diagrams/` (use-case, vault lifecycle, architecture) as
  Mermaid, referenced from the SRS.
- **Shamir feasibility spike** at `code/spikes/shamir_spike.py` (throwaway).
- **12-week plan** at `docs/plan/twelve-week-plan.md`.

## Decisions made

- **SRS delivered twice:** authoritative LaTeX `main.tex` plus a navigable
  Markdown mirror in `docs/` (the mirror is what CI builds and what the
  diagrams link to). Requirement IDs are identical in both.
- **Python packages live directly under `code/`** (not `code/src/`), matching
  the template's `pytest` config (`pythonpath = ["code"]`) so the test suite
  imports them with no `pyproject` changes.
- **Removed the template's C++ sample** so `code/` is a clean Python tree.
- **Extended `mkdocs.yml`** with a single `mermaid` superfences fence so the
  diagrams render on the deployed site (no new dependency — `mkdocs-material`
  bundles mermaid.js).
- **v1 non-goals fixed:** email only (no SMS), web only (no mobile app), one
  vault per Owner.

## Issue resolved (ticket)

**Symptom:** `python -m pytest` failed immediately with
`pyproject.toml: Invalid statement (at line 1, column 1)`.

**Cause:** the template's `pyproject.toml` was saved with a **UTF-8 BOM**
(`EF BB BF`). Python 3.11+'s `tomllib` — which `pytest` uses to read
`[tool.pytest.ini_options]` — rejects a leading BOM, so pytest could not start.

**Fix:** stripped the 3 BOM bytes (content otherwise byte-identical). `tomllib`
then parses the file and the smoke suite runs green. This was the only edit made
to `pyproject.toml`.

## What's open

- **PDF not built:** no LaTeX toolchain is installed locally or in CI, so
  `main.pdf` is not regenerated. Need to compile `main.tex` via Overleaf or a
  local TeX install before the proposal is submitted.
- **CI only deploys docs:** the template's workflow builds/deploys mkdocs but
  does **not** run `pytest`/`ruff`. Open question for Week 2: add a separate
  test+lint CI workflow so the suite gates changes.
- **No application code yet:** all five packages are empty scaffolds. Domain
  models + persistence are the Week-2 target.
- **Crypto hardening deferred to Week 4:** the spike proves feasibility only;
  constant-time arithmetic, share integrity/VSS, and authenticated payload
  encryption are still to do (see `code/spikes/README.md`).
