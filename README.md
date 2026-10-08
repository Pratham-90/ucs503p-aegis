# Aegis — an encrypted "dead man's switch" legacy vault

Aegis lets an **Owner** store an encrypted message or file in a **vault** and
designate **trustees** who can open it *only if the Owner stops responding*.
The Owner checks in on a schedule; if a check-in is missed and the grace period
ends, each trustee receives their encrypted share, and any **K of N** trustees
together reconstruct the key and open the vault. Fewer than K learn nothing.

The server is **zero-knowledge**: the browser encrypts the payload (AES-256-GCM),
splits the key with Shamir's Secret Sharing, and wraps each share to its
trustee's public key (RSA-OAEP) before upload. The server stores only
ciphertext and encrypted shares; it is trusted to keep time, never to read.

> **Course context.** UCS503P — Software Engineering (Laboratory), Thapar
> Institute of Engineering and Technology, 2026–27 ODD. Team: Pratham Arora,
> Krishna Pandey, Nipun Behl (COE). Lab instructor: Dr. Paramveer Sidhu.
> SRS, threat model, diagrams and plan: [`docs/`](docs/) (published at
> <https://pratham-90.github.io/ucs503p-aegis/>).

## Status: working prototype

| | |
| --- | --- |
| **Live URL** | **TODO** — not deployed yet. Set after the first Vercel deployment (see [Deploy](#deploy-to-vercel)). |
| Demo script | All 9 steps work end to end locally; verified by the Playwright test (`frontend/e2e/demo.spec.ts`). |
| Measurements | [`metrics/README.md`](metrics/README.md) — every value from a script that was actually run. |

## Repository layout

```
api/index.py              Vercel entrypoint (exposes code/api's FastAPI app)
code/
  crypto/                 authoritative Shamir (Python) + test_vectors.json
  scheduler/              pure evaluate(), transactional tick()
  vault/                  SQLAlchemy models, DB session, repositories
  notifications/          outbox + EmailSender (log / Resend)
  api/                    FastAPI app, routes, schemas
  tests/                  pytest (unit, property, integration)
frontend/                 React 18 + TypeScript + Vite + Tailwind
  src/crypto/             aes.ts, shamir.ts, rsa.ts, encoding.ts, vault.ts (+ tests)
  e2e/                    Playwright demo script
scripts/                  seed, vectors, reliability, load, inspection, metrics, diagrams
metrics/                  prototype-metrics.json + README (generated)
report-assets/            screenshots/ and diagrams/ (PNG) for the report
report/                   Word file with report content + references.bib
docs/                     mkdocs site (SRS, threat model, diagrams, plan)
```

## Run it locally

Prerequisites: Python 3.12 and Node 22+.

```bash
python -m venv .venv
.venv/Scripts/activate            # macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
(cd frontend && npm ci)
```

Two terminals:

```bash
python scripts/run_local_server.py --fresh      # API on :8000 (SQLite, DEMO_MODE, EMAIL_MODE=log)
```

```bash
cd frontend && npm run dev                       # UI on http://localhost:5173 (proxies /api)
```

The local Demo Console token is `local-demo-token` (set `DEMO_ADMIN_TOKEN` to change
it). Emails appear in the Demo Console's Outbox. To start from a ready-made vault:

```bash
python scripts/seed_demo.py --base-url http://127.0.0.1:8000   # writes key files to demo-keys/
```

## Test and measure

```bash
ruff check . && python -m pytest                           # Python: unit, property, integration
cd frontend && npx eslint . && npm test && npm run build    # TypeScript incl. Python<->TS vectors
cd frontend && npx playwright install chromium && npx playwright test   # end-to-end demo script
python scripts/collect_metrics.py                          # regenerate metrics/ (~5 min)
python scripts/gen_test_vectors.py                         # regenerate the shared vectors
bash scripts/export_diagrams.sh                            # Mermaid -> report-assets/diagrams/*.png
```

## Deploy to Vercel

One Vercel project serves the static frontend and the FastAPI function on the
same origin (`vercel.json`). Steps:

1. Import the GitHub repo into Vercel (framework comes from `vercel.json`; no root-directory change).
2. Add **Neon Postgres** from the Vercel Marketplace; it injects `DATABASE_URL`. Tables are created on first request.
3. Set environment variables (Production and Preview) from [`.env.example`](.env.example):
   `JWT_SECRET`, `CRON_SECRET`, `DEMO_ADMIN_TOKEN` (long random strings), `APP_BASE_URL`
   (the deployment URL), `DEMO_MODE=true`, `EMAIL_MODE=log` (or `resend` + `RESEND_API_KEY` + `EMAIL_FROM`).
4. In GitHub → Settings → Secrets → Actions add `APP_BASE_URL` and `CRON_SECRET` for the
   5-minute tick (`.github/workflows/tick.yml`; scheduled workflows run from `main` only).
5. Seed: `python scripts/seed_demo.py --base-url https://<deployment>`.
6. Measure the live site: `python scripts/load_checkin.py --base-url https://<deployment> --label deployed`,
   then `python scripts/collect_metrics.py --reuse`.

Without a verified email domain Resend only delivers to the account owner's own
address; `EMAIL_MODE=log` keeps every email in the in-app Outbox, which is what
the demo uses.

## Licence

MIT — see [`LICENSE`](LICENSE).
