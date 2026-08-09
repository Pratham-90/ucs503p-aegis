# Aegis — an encrypted "dead man's switch" legacy vault

Aegis lets an **Owner** store encrypted files and messages in a **vault** and
designate **trustees** who can open it *only if the Owner stops responding*.

The Owner checks in at a configured interval. Miss a check-in, and after a grace
period the vault's decryption key — split ahead of time into `N` shares with a
threshold `K` — is distributed to the trustees. Any **K of N** trustees combine
their shares to reconstruct the key and open the vault. Fewer than `K` learn
nothing.

> **Course context.** Solo project for **UCS503P — Software Engineering
> (Laboratory)**, Thapar Institute of Engineering and Technology, 2026–27 ODD
> semester. The formal project proposal (with author identity) lives in
> [`project-proposal/`](project-proposal/); the SRS, diagrams, and the 12-week
> plan live under [`docs/`](docs/).

## Algorithmic core

**Shamir's Secret Sharing.** The payload is sealed with a symmetric key; that
key is split into `N` shares over a finite field such that any `K` reconstruct
it (Lagrange interpolation) and any `K-1` reveal *nothing*. This threshold
property — not any single cipher — is what makes the dead-man's-switch safe: no
one trustee, and no coalition smaller than `K`, can open the vault.

## Planned stack

| Layer | Choice |
| --- | --- |
| Language | Python 3 |
| API | FastAPI |
| Persistence | SQLAlchemy — SQLite (dev), Postgres (later) |
| Secret sharing | Hand-written Shamir module (`code/crypto`) |
| Scheduling | APScheduler |
| Email | SMTP |
| Frontend | React + Tailwind |
| Tests / lint | pytest + ruff |

## Repository layout

```
code/                 application source (one package per responsibility)
  crypto/             Shamir secret sharing + payload encryption
  scheduler/          the check-in clock; drives the vault lifecycle
  vault/              domain models & repositories
  notifications/      outbound SMTP messaging
  api/                FastAPI application layer
  spikes/             throwaway feasibility experiments
  tests/              pytest suite
docs/                 mkdocs documentation (SRS mirror, diagrams, 12-week plan)
project-proposal/     LaTeX project proposal / SRS (main.tex)
journals/             weekly engineering journal
```

## Setup

```bash
# 1. Clone
git clone https://github.com/Pratham-90/ucs503p-aegis.git
cd ucs503p-aegis

# 2. (Recommended) create a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Install test/lint tooling (application deps land as modules are built)
python -m pip install pytest ruff

# 4. Run the test suite
python -m pytest

# 5. Preview the documentation locally (requires the mkdocs stack)
python -m pip install mkdocs mkdocs-material mkdocs-material-extensions \
  mkdocstrings mkdocstrings-python mkdocs-literate-nav mkdocs-section-index \
  mkdocs-git-revision-date-localized-plugin mkdocs-git-authors-plugin \
  pymdown-extensions
mkdocs serve
```

## Status

**Week 1 — requirements & scaffolding.** Module scaffold, SRS, diagrams, a
Shamir feasibility spike, and the 12-week plan. No application behaviour is
implemented yet. See [`journals/`](journals/) for the weekly log and
`docs/plan/twelve-week-plan.md` for the roadmap.

## Licence

MIT — see [`LICENSE`](LICENSE).
