#!/usr/bin/env bash
# ============================================
# pull_and_run.sh — Pull, build, and schedule
# 15 days of LinkedIn posts (45 total)
# ============================================
set -e

REPO="https://github.com/ansaribilal14/daily-linkedin-posts-pipeline"
DIR="daily-linkedin-posts-pipeline"

echo ""
echo "============================================"
echo "  Founders Wing — LinkedIn Post Pipeline"
echo "============================================"
echo ""

# ---------- 1. CLONE / PULL ----------
if [ -d "$DIR" ]; then
  echo "[1/5] Pulling latest from GitHub..."
  cd "$DIR"
  git pull
else
  echo "[1/5] Cloning repo..."
  git clone "$REPO" "$DIR"
  cd "$DIR"
fi

# ---------- 2. INSTALL DEPS ----------
echo ""
echo "[2/5] Installing dependencies..."

# Node deps (carousel-routine for rendering)
if [ -f "carousel-routine/package.json" ]; then
  cd carousel-routine
  npm install
  cd ..
fi

# Root puppeteer (for scheduler)
if [ ! -d "node_modules" ]; then
  npm init -y 2>/dev/null
  npm install puppeteer
fi

# Python deps
pip install playwright 2>/dev/null || pip3 install playwright 2>/dev/null
echo "  Done."

# ---------- 3. BUILD CAROUSEL HTML ----------
echo ""
echo "[3/5] Building carousel HTML slides..."
python3 build_all_carousels.py

# ---------- 4. RENDER CAROUSELS TO PNG + PDF ----------
echo ""
echo "[4/5] Rendering carousels to PNG + PDF..."
node build_all_carousels.cjs

echo ""
echo "  Carousel build complete."
echo "  Output: carousel-routine/output/*/carousel-branded/"

# ---------- 5. SCHEDULE ----------
echo ""
echo "[5/5] Starting LinkedIn scheduler..."
echo ""
echo "============================================"
echo "  SCHEDULING 45 POSTS (July 5-19)"
echo "============================================"
echo ""
echo "A Chrome window will open with your LinkedIn session."
echo "Log in if prompted. The script handles the rest."
echo ""
echo "FLAGS:"
echo "  node schedule_all_15days.cjs              # all 45 posts"
echo "  node schedule_all_15days.cjs --date 2026-07-05  # single day"
echo "  node schedule_all_15days.cjs --from 5 --to 9    # day range"
echo "  node schedule_all_15days.cjs --now              # post 1st now"
echo ""
read -p "Press ENTER to start scheduling all 45 posts..."

node schedule_all_15days.cjs