#!/usr/bin/zsh
set -euo pipefail

DEST="${BINARIES:-/usr/local/bin}"          # where FFFocusTracker / FFLinkRouter are installed (no extension)
APPDIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
DESKTOP_ID="ff-link-router.desktop"
DESKTOP_PATH="$APPDIR/$DESKTOP_ID"

# 0) Sanity: FFLinkRouter must exist and be a valid CIL (no extension)
if [[ ! -x "$DEST/FFLinkRouter" ]]; then
  echo "Error: $DEST/FFLinkRouter not found or not executable." >&2
  exit 1
fi
if command -v file >/dev/null 2>&1; then
  if ! file -b "$DEST/FFLinkRouter" | grep -Eiq 'PE32|Mono/.NET|CLR'; then
    echo "Error: $DEST/FFLinkRouter is not a valid CIL image (did a wrapper overwrite it?)." >&2
    exit 2
  fi
fi

# 1) Ensure binfmt 'cli' is enabled so a no-extension CIL runs directly
if command -v update-binfmts >/dev/null 2>&1; then
  if ! update-binfmts --display cli 2>/dev/null | grep -q 'status.*enabled'; then
    echo "Enabling binfmt 'cli' (requires sudo)..."
    sudo update-binfmts --enable cli || true
  fi
fi

# 2) Create a proper .desktop entry so GNOME can treat it as a browser target
mkdir -p "$APPDIR"
cat >"$DESKTOP_PATH" <<DESK
[Desktop Entry]
Name=FF Link Router
Comment=Routes http/https to the last-focused Firefox profile
Exec=$DEST/FFLinkRouter %u
TryExec=$DEST/FFLinkRouter
Terminal=false
Type=Application
MimeType=x-scheme-handler/http;x-scheme-handler/https;
NoDisplay=false
Categories=Network;WebBrowser;
DESK

# 3) Register & set as default for http/https
update-desktop-database "$APPDIR" >/dev/null 2>&1 || true

# Use both gio and xdg-mime (some desktops honor one over the other)
gio mime x-scheme-handler/http  "$DESKTOP_ID" || true
gio mime x-scheme-handler/https "$DESKTOP_ID" || true

xdg-mime default "$DESKTOP_ID" x-scheme-handler/http
xdg-mime default "$DESKTOP_ID" x-scheme-handler/https

# Optional: set as "default web browser" at the desktop level (GNOME honors the scheme handlers above anyway)
xdg-settings set default-web-browser "$DESKTOP_ID" || true

echo "Registered $DESKTOP_ID -> $DEST/FFLinkRouter"

# 4) Show current associations
echo "Current handler (gio):"
gio mime x-scheme-handler/http  || true
gio mime x-scheme-handler/https || true

echo "Done."
