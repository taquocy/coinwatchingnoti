#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE_TEMPLATE="$PROJECT_DIR/deploy/coingecko-notifier.service"
SERVICE_NAME="coingecko-notifier.service"
TARGET_SERVICE="/etc/systemd/system/$SERVICE_NAME"
RUN_USER="${RUN_USER:-$(whoami)}"
RUN_GROUP="${RUN_GROUP:-$(id -gn)}"
PYTHON_PATH="${PYTHON_PATH:-$PROJECT_DIR/.venv/bin/python}"

if [[ ! -x "$PYTHON_PATH" ]]; then
  echo "Python executable not found at $PYTHON_PATH"
  echo "Run ./scripts/bootstrap_pi.sh first or set PYTHON_PATH=/path/to/python"
  exit 1
fi

TMP_FILE="$(mktemp)"
trap 'rm -f "$TMP_FILE"' EXIT

sed \
  -e "s|__PROJECT_DIR__|$PROJECT_DIR|g" \
  -e "s|__RUN_USER__|$RUN_USER|g" \
  -e "s|__RUN_GROUP__|$RUN_GROUP|g" \
  -e "s|__PYTHON_PATH__|$PYTHON_PATH|g" \
  "$SERVICE_TEMPLATE" > "$TMP_FILE"

sudo cp "$TMP_FILE" "$TARGET_SERVICE"
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl restart "$SERVICE_NAME"

echo "Installed and started $SERVICE_NAME"
echo "Check status with: sudo systemctl status $SERVICE_NAME"
echo "Check logs with: journalctl -u $SERVICE_NAME -f"
