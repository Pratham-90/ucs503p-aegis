# Aegis — handoff for the next chat session

> **To the assistant reading this:** the user (Pratham) is continuing work from an earlier
> session. Read this file first. Then (1) walk the user **step by step, one step at a time,
> waiting for them to confirm each step**, through the "What the user must do" list below,
> and (2) implement the **dark/light mode switch** described in the last section.
> Everything stated here was true on 2026-10-09; verify with `git log` / the files before relying on it.

## Project in one paragraph

Aegis is an encrypted "dead man's switch" legacy vault for UCS503P (Software Engineering Lab,
TIET, 2026–27 ODD). Team: Pratham Arora, Krishna Pandey, Nipun Behl (COE). Lab instructor:
Dr. Paramveer Sidhu. An Owner stores an encrypted message/file; N trustees each get one Shamir
share; if the Owner stops checking in and the grace period ends, any K of N trustees can open it.
The server is **zero-knowledge**: the browser does all crypto (AES-256-GCM, hand-written Shamir
over GF(2^521−1), RSA-OAEP-2048 per trustee); the server stores only ciphertext + encrypted shares.

- Repo: `E:\Projects\Aegis\ucs503p-aegis` → https://github.com/Pratham-90/ucs503p-aegis
- Work branch: **`prototype`** — open **PR #1** to `main`: https://github.com/Pratham-90/ucs503p-aegis/pull/1
- Docs site (mkdocs, from `main`): https://pratham-90.github.io/ucs503p-aegis/
- The brief this work follows: `C:\Users\Pratham\Downloads\AEGIS_PROTOTYPE_BRIEF.md`

## What is already done (on branch `prototype`)

| Area | Where | Status |
| --- | --- | --- |
| Authoritative Python crypto + property tests + shared test vectors | `code/crypto/`, `scripts/gen_test_vectors.py` | done |
| TypeScript client crypto (reproduces all 13 Python vectors) | `frontend/src/crypto/` | done |
| Scheduler: pure `evaluate()` + transactional `tick()` + exactly-once outbox | `code/scheduler/`, `code/notifications/` | done |
| SQLAlchemy models (SQLite local, Postgres/Neon deployed) | `code/vault/` | done |
| FastAPI app (auth, vaults, check-in links, trustee, cron, demo console) | `code/api/` | done |
| React 18 + TS + Vite + Tailwind v4 UI (all 9 demo steps) | `frontend/src/pages/` | done |
| Playwright end-to-end demo test + 22 screenshots | `frontend/e2e/`, `report-assets/screenshots/` | done, passing |
| Vercel config (Vite static + Python function on one origin) | `vercel.json`, `api/index.py`, `.vercelignore`, `uv.lock` | done, **not deployed** |
| CI (ruff, pytest + 80% coverage gate, eslint, vitest, build, Playwright) and 5-min tick cron | `.github/workflows/ci.yml`, `tick.yml` | done |
| Measurements → `metrics/prototype-metrics.json` + `metrics/README.md` | `scripts/collect_metrics.py` | done (local) |
| Mermaid diagrams → PNG | `docs/diagrams/`, `scripts/export_diagrams.sh`, `report-assets/diagrams/` | done |
| Report content (Word, 31 pages, 18 figures) + bibliography | `report/Aegis_Prototype_Report_Content.docx`, `report/references.bib`, `scripts/make_report_docx.py` | done (has `[TODO]`s) |
| Journal entry | `journals/pra-kri-nip/w8-prototype-build.md` | done ("who did what" = TODO) |
| README with run/deploy instructions | `README.md` | done (live URL = TODO) |

Key measured results (local): 125/125 Python + 22/22 TS tests; coverage crypto 100%, scheduler 98.8%;
Hypothesis 1600 cases, 0 failing; reliability over 1000 schedules → **0 early / 0 duplicate / 0 missed**
releases; zero-knowledge inspection → **0 findings**; check-in p95 23.7 ms locally.
**Honest gaps:** NFR-REL-2 / NFR-PERF-2 (≤ 60 s) are **not met with the 5-minute cron alone**
(809 s / 829 s); deployed latency and Lighthouse are **not measured yet** (need the live site).

Notable decisions/changes the user should know about:
- `pyproject.toml` got a minimal fix: the template's project name was not a valid package name and
  broke Vercel's `uv lock`; renamed to `ucs503p-aegis`, runtime deps added, `[tool.uv] package = false`.
- `.gitignore` gained `node_modules/`, `*.db`, `.vercel/`, `demo-keys/`.
- Commits carry `Co-Authored-By: Claude …`; the journal states the code was written with an AI assistant.

## Run it locally (for the user)

Prereqs: Python 3.12 venv already at `.venv`, Node 24, `frontend/node_modules` installed.

```bash
# terminal 1 — API on :8000 (SQLite, DEMO_MODE on, emails go to the in-app Outbox)
.venv/Scripts/python scripts/run_local_server.py --db preview.db --port 8000
# terminal 2 — UI on http://localhost:5173  (use "localhost", not 127.0.0.1)
cd frontend && npx vite --port 5173
```

- Demo owner (seeded, local only): `demo-owner@example.com` / `preview-demo-pass`
- Demo Console token (local): `local-demo-token`
- Re-seed: `DEMO_OWNER_PASSWORD=preview-demo-pass .venv/Scripts/python scripts/seed_demo.py --base-url http://127.0.0.1:8000`
  (if the owner already has a vault, first click "Reset demo data" in the Demo Console). Trustee key files → `demo-keys/`.
- Tests: `.venv/Scripts/python -m pytest` · `cd frontend && npm test && npx eslint . && npm run build` · `cd frontend && npx playwright test`

## What the user must do (walk them through these, one at a time)

1. **Review PR #1** (https://github.com/Pratham-90/ucs503p-aegis/pull/1): check that the CI run is green
   (`gh pr checks 1`); if a job fails, read its log and fix it on `prototype`.
2. **Create the Vercel project:** vercel.com → Add New → Project → import `Pratham-90/ucs503p-aegis`.
   Leave Framework/Root as detected (they come from `vercel.json`). Deploy the `prototype` branch first
   as a Preview, or merge PR #1 and deploy `main` as Production.
3. **Add Neon Postgres:** Vercel project → Storage / Marketplace → Neon → connect to the project.
   It injects `DATABASE_URL` (tables are created automatically on first request).
4. **Set environment variables** (Vercel → Settings → Environment Variables, Production + Preview),
   see `.env.example`: `JWT_SECRET`, `CRON_SECRET`, `DEMO_ADMIN_TOKEN` (each a long random string:
   `python -c "import secrets; print(secrets.token_urlsafe(48))"`), `APP_BASE_URL` (the deployment URL,
   no trailing slash), `DEMO_MODE=true`, `EMAIL_MODE=log`. Optional: `EMAIL_MODE=resend` + `RESEND_API_KEY`
   + `EMAIL_FROM` (without a verified domain Resend only mails the account owner). Redeploy after setting.
   The user must enter secrets themselves — the assistant must not type secret values into web forms.
5. **Smoke-test:** open `<URL>/api/health` (expect `"status":"ok","database":"postgresql"`), then the site.
   If the function fails, check Vercel → Deployments → Functions logs. (Running the Python function
   under `vercel dev` does not work on Windows — its emulator needs AF_UNIX sockets — so the first real
   deployment is the true test of `api/index.py`.)
6. **GitHub secrets for the 5-minute tick:** repo → Settings → Secrets and variables → Actions → add
   `APP_BASE_URL` and `CRON_SECRET` (same values as Vercel). Scheduled workflows only run from `main`,
   so this starts working after PR #1 is merged. Test via Actions → scheduler-tick → Run workflow.
7. **Seed the live demo:** `DEMO_OWNER_PASSWORD=<choose> .venv/Scripts/python scripts/seed_demo.py --base-url https://<URL>`.
8. **Measure the live site and regenerate the report:**
   `.venv/Scripts/python scripts/load_checkin.py --base-url https://<URL> --label deployed`, then
   `.venv/Scripts/python scripts/collect_metrics.py --reuse`, then `.venv/Scripts/python scripts/make_report_docx.py`.
   Lighthouse is still TODO: no `scripts/lighthouse.mjs` exists yet (write one, or run Lighthouse in
   Chrome DevTools on `/` and `/dashboard` and save scores to `metrics/raw/lighthouse_landing.json` /
   `lighthouse_dashboard.json` with keys `scores`, `command`, `environment`, `measured_at`).
9. **Fill the `[TODO]`s:** live URL in `README.md` and the report (`LIVE_URL` in `scripts/make_report_docx.py`);
   roll numbers of Krishna and Nipun, group, user-testing results and final remarks in the report;
   "who did what" in `journals/pra-kri-nip/w8-prototype-build.md`. Then regenerate the .docx and
   copy its content into the team's Overleaf template.
10. **Merge PR #1** once CI is green and the live demo has been smoke-tested on a laptop and a phone.

## Next feature to implement: dark / light mode switch

Add a theme switch to the website (`frontend/`):

- A toggle button in the header (`frontend/src/components/Layout.tsx`, next to the nav) cycling
  **Light / Dark / System**, with an accessible label and a sun/moon icon.
- Persist the choice in `localStorage` (key e.g. `aegis.theme`); default to **System**, following
  `prefers-color-scheme` and reacting to OS changes while on System.
- Apply it by toggling a `dark` class on `<html>`; set it **before React renders** (small inline script
  in `frontend/index.html`) to avoid a flash of the wrong theme.
- Tailwind is **v4** (`@import "tailwindcss"` in `frontend/src/index.css`, no config file): enable
  class-based dark mode with `@custom-variant dark (&:where(.dark, .dark *));` and add `dark:` classes.
  Update `html { color-scheme }` accordingly.
- Cover every surface: body background (`index.html` uses `bg-slate-50 text-slate-900`), header/footer,
  `Card`, `Alert`, inputs (`inputClass`), buttons, `Mono` blocks, countdown tiles, tables in the Demo
  Console, the landing hero, and the wizard step pills (`components/ui.tsx`, all files in `src/pages/`).
  Keep the state-badge meaning (Active green, Warning amber, Grace orange, Released red) readable in both
  themes, with accessible contrast.
- Verify: `npx tsc -b && npx eslint . && npm test && npm run build`, and run `npx playwright test`
  (the E2E must still pass). The report screenshots in `report-assets/screenshots/` were taken in light
  mode; leave them as they are unless the user asks to regenerate them.
- Commit on `prototype` as `feat(frontend): dark/light/system theme switch` and push (updates PR #1).
