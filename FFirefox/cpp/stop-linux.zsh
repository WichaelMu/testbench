#!/usr/bin/env zsh
set -euo pipefail
systemctl --user stop FF-FocusWatcher.service || true
echo "Stopped FF-FocusWatcher.service"
