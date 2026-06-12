#!/bin/bash
# deploy/status.sh - Zeigt an, welche Methode gerade aktiv ist
LINK=$(readlink /etc/systemd/system/pixelwise.service)
echo "Aktive Methode: $(basename "$LINK")"
