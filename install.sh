#!/usr/bin/env bash
set -euo pipefail

APP_NAME="linux-tab-text-expander"
APP_BIN="$HOME/.local/bin/$APP_NAME"
CONFIG_DIR="$HOME/.config/$APP_NAME"
CONFIG_FILE="$CONFIG_DIR/replacements.json"
SERVICE_DIR="$HOME/.config/systemd/user"
SERVICE_FILE="$SERVICE_DIR/$APP_NAME.service"

if [ "${XDG_SESSION_TYPE:-}" != "x11" ]; then
  echo "This text expander currently requires an X11 desktop session."
  echo "Current XDG_SESSION_TYPE=${XDG_SESSION_TYPE:-unset}. Log in with Ubuntu on Xorg / X11, then run this again."
  exit 1
fi

run_as_root() {
  if command -v sudo >/dev/null 2>&1 && sudo -n true >/dev/null 2>&1; then
    sudo "$@"
  elif command -v pkexec >/dev/null 2>&1; then
    pkexec "$@"
  elif command -v sudo >/dev/null 2>&1; then
    sudo "$@"
  else
    echo "Need sudo or pkexec to install system packages." >&2
    exit 1
  fi
}

if command -v apt-get >/dev/null 2>&1; then
  run_as_root env DEBIAN_FRONTEND=noninteractive apt-get update
  run_as_root env DEBIAN_FRONTEND=noninteractive apt-get install -y \
    python3 \
    python3-pip \
    python3-tk \
    xdotool \
    x11-utils
fi

python3 - <<'PY' || {
import pynput
import Xlib
PY
  python3 -m pip install --user pynput python-xlib || \
    python3 -m pip install --user --break-system-packages pynput python-xlib
}

mkdir -p "$HOME/.local/bin" "$CONFIG_DIR" "$SERVICE_DIR"
install -m 0755 linux-tab-text-expander.py "$APP_BIN"

if [ -f "$CONFIG_FILE" ]; then
  cp "$CONFIG_FILE" "$CONFIG_FILE.bak.$(date +%Y%m%d%H%M%S)"
fi
install -m 0644 replacements.json "$CONFIG_FILE"

cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=Linux Tab text expander
After=graphical-session.target

[Service]
Type=simple
Environment=TEXT_EXPANDER_CONFIG=%h/.config/$APP_NAME/replacements.json
ExecStart=%h/.local/bin/$APP_NAME
Restart=on-failure
RestartSec=2

[Install]
WantedBy=default.target
EOF

systemctl --user import-environment DISPLAY XAUTHORITY XDG_SESSION_TYPE
systemctl --user daemon-reload
systemctl --user enable --now "$APP_NAME.service"

echo "Installed $APP_NAME."
echo "Try typing 'jr' or ';ship', then press Tab while the hint is visible."
