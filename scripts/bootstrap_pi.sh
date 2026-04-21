#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

PYTHON_BIN="${PYTHON_BIN:-python3}"

echo "[1/5] Checking Python..."
"$PYTHON_BIN" --version

echo "[2/5] Creating virtual environment..."
"$PYTHON_BIN" -m venv .venv

echo "[3/5] Installing dependencies..."
".venv/bin/pip" install --upgrade pip
".venv/bin/pip" install -r requirements.txt

echo "[4/5] Preparing environment file..."
if [[ ! -f ".env" ]]; then
  cp .env.example .env
  echo "Created .env from .env.example. Please edit it before sending notifications."
else
  echo ".env already exists. Keeping current file."
fi

echo "[5/5] Bootstrap complete."
echo
echo "Preview current data:"
echo "  ./scripts/run_preview.sh"
echo
echo "Send immediately:"
echo "  ./scripts/run_now.sh"
echo
echo "Start scheduler:"
echo "  ./scripts/start_scheduler.sh"
