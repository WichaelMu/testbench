#!/usr/bin/env zsh
set -euo pipefail

print "== Uninstalling FF-FocusWatcher (Linux) =="

SERVICE_NAME="FF-FocusWatcher.service"
DEST_BIN="${HOME}/.local/bin/ff-focus-watcher.py"
DEST_SERVICE="${HOME}/.config/systemd/user/${SERVICE_NAME}"

# Stop / disable service (ignore errors if not present)
systemctl --user stop "${SERVICE_NAME}" 2>/dev/null || true
systemctl --user disable "${SERVICE_NAME}" 2>/dev/null || true
systemctl --user daemon-reload || true

# Remove installed files
[[ -f "${DEST_BIN}" ]] && rm -f "${DEST_BIN}"
[[ -f "${DEST_SERVICE}" ]] && rm -f "${DEST_SERVICE}"

# Optional: remove watcher state/logs; comment these out if you want to keep them
for f in \
    "${HOME}/.local/share/FF/focus.json" \
    "${HOME}/.local/share/FF/focus_stack.json" \
    "${HOME}/.local/share/FF/FF-FocusWatcher.log"
do
    [[ -f "${f}" ]] && rm -f "${f}"
done

print "FF-FocusWatcher uninstalled."
