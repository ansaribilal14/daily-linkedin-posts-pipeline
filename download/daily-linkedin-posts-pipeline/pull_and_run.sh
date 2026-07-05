#!/usr/bin/env bash
# pull_and_run.sh — Pull repo + schedule all posts
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
echo "  45 posts ready. Opening LinkedIn..."
echo "============================================"
echo ""

node schedule_all_15days.cjs "$@"