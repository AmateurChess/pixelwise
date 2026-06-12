#!/bin/bash
# deploy/switch-method.sh
set -euo pipefail

METHOD=${1:-}
TARGET_SERVICE="/etc/systemd/system/pixelwise.service"

# Pfad zum Projekt auf dem Server
PROJ_DIR="/opt/pixelwise"

case "$METHOD" in
  baseline)
    SOURCE_SERVICE="$PROJ_DIR/deploy/pixelwise.service"
    ;;
  gunicorn)
    SOURCE_SERVICE="$PROJ_DIR/deploy/pixelwise-gunicorn.service"
    ;;
  hotswap)
    SOURCE_SERVICE="$PROJ_DIR/deploy/pixelwise-hotswap.service"
    ;;
  *)
    echo "Nutzung: bash deploy/switch-method.sh [baseline|gunicorn|hotswap]"
    exit 1
    ;;
esac

echo "Wechsle zu Methode: $METHOD..."
sudo ln -sf "$SOURCE_SERVICE" "$TARGET_SERVICE"
sudo systemctl daemon-reload
sudo systemctl restart pixelwise
echo "Erfolgreich gewechselt."
sudo systemctl status pixelwise --no-pager
