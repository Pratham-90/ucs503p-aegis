// Lighthouse scores for the deployed site (brief section 8; metrics/README.md).
//
//     node scripts/lighthouse.mjs --base-url https://<deployment>.vercel.app
//
// Runs Lighthouse (pinned version, default mobile profile with simulated throttling, headless
// Chrome) on the landing page and /dashboard, and writes metrics/raw/lighthouse_<page>.json in
// the shape scripts/collect_metrics.py reads: {scores, command, environment, measured_at, notes}.
// Logged out, /dashboard redirects to /login inside the SPA, so it measures the same app shell
// plus the redirect; the notes say so.

import { execSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const LIGHTHOUSE = "lighthouse@13.5.0";
const CATEGORIES = ["performance", "accessibility", "best-practices", "seo"];
const PAGES = { landing: "/", dashboard: "/dashboard" };

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const argIndex = process.argv.indexOf("--base-url");
const baseUrl = argIndex > 0 ? process.argv[argIndex + 1]?.replace(/\/$/, "") : undefined;
if (!baseUrl) {
  console.error("usage: node scripts/lighthouse.mjs --base-url https://<deployment>");
  process.exit(2);
}

const tmp = mkdtempSync(path.join(os.tmpdir(), "aegis-lighthouse-"));
try {
  for (const [page, route] of Object.entries(PAGES)) {
    const url = baseUrl + route;
    const out = path.join(tmp, `${page}.json`);
    const args = [
      "--yes", LIGHTHOUSE, url, "--quiet", "--output=json", `--output-path=${out}`,
      `--only-categories=${CATEGORIES.join(",")}`, "--chrome-flags=--headless=new",
    ];
    console.log(`lighthouse ${url}`);
    execSync(["npx", ...args.map((a) => `"${a}"`)].join(" "), { stdio: "inherit" });

    const report = JSON.parse(readFileSync(out, "utf8"));
    const scores = Object.fromEntries(
      CATEGORIES.map((c) => [c, Math.round((report.categories[c]?.score ?? 0) * 100)]),
    );
    const lost = CATEGORIES.flatMap((c) => report.categories[c].auditRefs)
      .filter((ref) => ref.weight > 0 && report.audits[ref.id].score !== null && report.audits[ref.id].score < 1)
      .map((ref) => report.audits[ref.id].title);
    const notes = [
      `Lighthouse ${report.lighthouseVersion}, ${report.configSettings.formFactor} profile, ` +
        `${report.configSettings.throttlingMethod} throttling`,
      `final URL ${report.finalDisplayedUrl}`,
      route === "/dashboard" ? "logged out, so the SPA redirects to /login" : null,
      lost.length ? `audits below full score: ${lost.join("; ")}` : null,
    ].filter(Boolean).join("; ");
    const result = {
      scores,
      command: `node scripts/lighthouse.mjs --base-url ${baseUrl}`,
      environment: `deployed: ${baseUrl} (Vercel), headless Chrome ${report.environment.hostUserAgent.match(/Chrome\/([\d.]+)/)?.[1] ?? ""}`.trim(),
      measured_at: new Date(report.fetchTime).toISOString().replace(/\.\d+Z$/, "+00:00"),
      notes,
    };
    writeFileSync(path.join(root, "metrics", "raw", `lighthouse_${page}.json`), JSON.stringify(result, null, 2) + "\n");
    console.log(`${page}: ${JSON.stringify(scores)}`);
  }
} finally {
  rmSync(tmp, { recursive: true, force: true });
}
