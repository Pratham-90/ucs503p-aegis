// Render every Mermaid block in docs/diagrams/*.md to report-assets/diagrams/<page>-<n>.png
// with the official Mermaid renderer inside Playwright's Chromium (2x scale, white background).
// Run via:  bash scripts/export_diagrams.sh   (or: node frontend/scripts/export-diagrams.mjs)
import { chromium } from "@playwright/test";
import { mkdirSync, readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, "../..");
const docs = path.join(root, "docs", "diagrams");
const out = path.join(root, "report-assets", "diagrams");
mkdirSync(out, { recursive: true });

const blocks = [];
for (const file of readdirSync(docs).filter((f) => f.endsWith(".md")).sort()) {
  const text = readFileSync(path.join(docs, file), "utf8").replace(/\r\n/g, "\n");
  [...text.matchAll(/```mermaid\n([\s\S]*?)```/g)].forEach((m, i) =>
    blocks.push({ name: `${file.replace(/\.md$/, "")}-${i + 1}`, source: m[1] }),
  );
}

const mermaidJs = readFileSync(path.join(here, "..", "node_modules", "mermaid", "dist", "mermaid.min.js"), "utf8");
const browser = await chromium.launch();
const page = await browser.newPage({ deviceScaleFactor: 2, viewport: { width: 1600, height: 1200 } });
await page.setContent('<html><body style="margin:0;padding:16px;background:#fff"><div id="c"></div></body></html>');
await page.addScriptTag({ content: mermaidJs });
await page.evaluate(() => window.mermaid.initialize({ startOnLoad: false, theme: "default", securityLevel: "strict" }));

for (const { name, source } of blocks) {
  await page.evaluate(async ({ source, id }) => {
    const { svg } = await window.mermaid.render(id, source);
    document.getElementById("c").innerHTML = svg;
  }, { source, id: `d${name.replace(/\W/g, "")}` });
  await page.locator("#c svg").screenshot({ path: path.join(out, `${name}.png`) });
  console.log(`rendered ${name}.png`);
}
await browser.close();
