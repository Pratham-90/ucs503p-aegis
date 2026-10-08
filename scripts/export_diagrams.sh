#!/usr/bin/env bash
# Export every Mermaid block in docs/diagrams/*.md to report-assets/diagrams/<page>-<n>.png.
# Uses the official Mermaid renderer inside Playwright's Chromium (mermaid-cli's Puppeteer
# launcher fails on Windows with "spawn UNKNOWN"; Playwright's browser works everywhere here).
#   bash scripts/export_diagrams.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/frontend"
node scripts/export-diagrams.mjs
