#!/usr/bin/env bash
set -euo pipefail

SERVICE_ROOT="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
UNIT_DIR="$HOME/.config/systemd/user"
UNIT_NAME="aisha-dashboard.service"
UNIT_PATH="$UNIT_DIR/$UNIT_NAME"

mkdir -p "$UNIT_DIR"
cat > "$UNIT_PATH" <<UNIT
[Unit]
Description=Aisha Dashboard
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=$SERVICE_ROOT
ExecStart=%h/.venvs/aisha/bin/python -m app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
UNIT

systemctl --user daemon-reload
systemctl --user enable "$UNIT_NAME"

echo "Installed $UNIT_NAME for user $USER"
echo "WorkingDirectory: $SERVICE_ROOT"
echo "Start it with: systemctl --user start $UNIT_NAME"
