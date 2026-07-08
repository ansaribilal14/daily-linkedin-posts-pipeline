#!/usr/bin/env bash
# pull_and_run.sh — Pull repo + post to all platforms
set -e

REPO="https://github.com/ansaribilal14/daily-linkedin-posts-pipeline"
DIR="daily-linkedin-posts-pipeline"

if [ -d "$DIR" ]; then
  cd "$DIR" && git pull
else
  git clone "$REPO" "$DIR" && cd "$DIR"
fi

[ ! -d "node_modules" ] && npm install puppeteer

echo ""
echo "============================================"
echo "  Founders Wing — Multi-Platform Poster"
echo "  90 posts across IG, FB, Threads, X"
echo "============================================"
echo ""
echo "A browser window opens per platform."
echo "Log in if prompted. Script handles the rest."
echo ""
echo "FLAGS:"
echo "  node post_all_platforms.cjs                          # all platforms, all days"
echo "  node post_all_platforms.cjs --platform threads        # Threads only"
echo "  node post_all_platforms.cjs --platform twitter        # Twitter only"
echo "  node post_all_platforms.cjs --platform instagram      # Instagram only"
echo "  node post_all_platforms.cjs --date 2026-07-08         # specific day"
echo "  node post_all_platforms.cjs --today                  # today only"
echo ""

node post_all_platforms.cjs "$@"