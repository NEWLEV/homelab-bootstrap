#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../../../.." && pwd)"
UNIT_DIR="$HOME/.config/systemd/user"
CONFIG_DIR="$HOME/.config/aisha"
ENV_FILE="$CONFIG_DIR/integration-dispatcher.env"

install -d -m 700 "$UNIT_DIR" "$CONFIG_DIR"
sed "s|%h/Documents/Aisha|$REPO_ROOT|" \
  "$REPO_ROOT/homelab-bootstrap/services/integrations/systemd/aisha-integration-dispatcher.service" \
  > "$UNIT_DIR/aisha-integration-dispatcher.service"
cp "$REPO_ROOT/homelab-bootstrap/services/integrations/systemd/aisha-integration-dispatcher.timer" \
  "$UNIT_DIR/aisha-integration-dispatcher.timer"

if [[ ! -f "$ENV_FILE" ]]; then
  umask 077
  cat > "$ENV_FILE" <<'ENV'
# Set only the n8n webhook endpoints you have imported and activated.
MISSION_CONTROL_URL=http://127.0.0.1:8020
MISSION_CONTROL_PUBLIC_URL=http://aisha:8000/platform/mission-control
# SLACK_ALERT_WEBHOOK_URL=http://127.0.0.1:5678/webhook/mission-control/slack
# DISCORD_ALERT_WEBHOOK_URL=http://127.0.0.1:5678/webhook/mission-control/discord
# TELEGRAM_ALERT_WEBHOOK_URL=http://127.0.0.1:5678/webhook/mission-control/telegram
ENV
fi

systemctl --user daemon-reload
systemctl --user enable aisha-integration-dispatcher.timer
echo "Installed dispatcher timer. Add only activated webhook endpoints to $ENV_FILE, then run:"
echo "  systemctl --user start aisha-integration-dispatcher.timer"
