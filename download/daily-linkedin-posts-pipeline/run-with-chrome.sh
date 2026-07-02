#!/usr/bin/env bash
# run-with-chrome.sh — Run any Node/Puppeteer script with Playwright's Chromium
# Usage: ./run-with-chrome.sh node render.js [args...]
#        ./run-with-chrome.sh node cap_infographic_today.cjs

# Point Puppeteer at Playwright's Chromium (linux)
export PUPPETEER_EXECUTABLE_PATH="/home/z/.cache/ms-playwright/chromium-1200/chrome-linux64/chrome"

# Load .env if present
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/.env" ]; then
  set -a
  source "$SCRIPT_DIR/.env"
  set +a
fi

exec "$@"