#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../../../.." && pwd)"
UNIT_DIR="$HOME/.config/systemd/user"
UNIT_NAME="aisha-mission-control.service"
UNIT_PATH="$UNIT_DIR/$UNIT_NAME"

mkdir -p "$UNIT_DIR"
cat > "$UNIT_PATH" <<UNIT
[Unit]
Description=Aisha Mission Control
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=$REPO_ROOT
Environment=MISSION_CONTROL_HOST=127.0.0.1
Environment=MISSION_CONTROL_PORT=8020
Environment=MISSION_CONTROL_DATABASE=%h/.local/share/aisha/mission-control.sqlite3
ExecStart=%h/Documents/Aisha/homelab-bootstrap/services/mission-control/scripts/run-mission-control.sh
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
UNIT

systemctl --user daemon-reload
systemctl --user enable "$UNIT_NAME"

echo "Installed $UNIT_NAME for user $USER"
echo "WorkingDirectory: $REPO_ROOT"
echo "Start it with: systemctl --user start $UNIT_NAME"
