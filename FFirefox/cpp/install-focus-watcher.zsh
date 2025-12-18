#!/usr/bin/env zsh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
EXT_ID="ff-focus-watcher@absolution"
SRC_DIR="${SCRIPT_DIR}/gnome-extension/${EXT_ID}"
DEST_DIR="${HOME}/.local/share/gnome-shell/extensions/${EXT_ID}"

echo "== Installing GNOME Shell extension FF-FocusWatcher (Wayland) =="
echo "Source: ${SRC_DIR}"
echo "Dest:   ${DEST_DIR}"

mkdir -p "${DEST_DIR}"

cp "${SRC_DIR}/metadata.json" "${SRC_DIR}/extension.js" "${DEST_DIR}/"

echo "Installed extension files to:"
echo "  ${DEST_DIR}"

if command -v gnome-extensions >/dev/null 2>&1; then
    echo "Enabling extension (if GNOME Shell is running)..."
    gnome-extensions enable "${EXT_ID}" 2>/dev/null || \
        echo "  Could not enable via CLI; use the GNOME Extensions app to enable it."
else
    echo "gnome-extensions CLI not found."
    echo "Use the GNOME Extensions app to enable '${EXT_ID}'."
fi

echo ""
echo "You must restart GNOME Shell for changes to fully apply:"
echo "  - Log out and log back in, OR"
echo "  - Press Alt+F2, type:  r   and press Enter (on Xorg sessions)."
