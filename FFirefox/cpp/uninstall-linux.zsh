#!/usr/bin/env zsh
set -euo pipefail
systemctl --user disable --now ff-focus-watcher.service || true
rm -f "$HOME/.config/systemd/user/FF-FocusWatcher.service"
systemctl --user daemon-reload || true

sudo rm -f /usr/local/bin/FFLinkRouter || true
sudo rm -f /usr/local/bin/ff-focus-watcher.py || true
rm -f "$HOME/.local/share/applications/ff-link-router.desktop" || true

echo "Uninstalled watcher + router. (Logs and JSON remain under ~/.local/share/FF)"
