#!/usr/bin/env zsh
set -euo pipefail

# --- Harden build env (common cause of '-O' without a value) ---
unset CFLAGS || true
unset CXXFLAGS || true
unset CPPFLAGS || true
unset LDFLAGS || true
unalias g++ 2>/dev/null || true

GXX="/usr/bin/g++"
if [[ ! -x "$GXX" ]]; then
  GXX="$(command -v g++)"
fi
if [[ -z "${GXX:-}" ]]; then
  echo "ERROR: g++ not found." >&2
  exit 1
fi

UserName="${USER}"
Uid="$(id -u)"
Dest="/usr/local/bin"
SrcDir="$(pwd)"

echo "== Building for user: ${UserName} (uid=${Uid})  Dest: ${Dest}"
echo "   Sources: ${SrcDir}"

mkdir -p build

# --- Flags as arrays to avoid zsh splitting/option confusion ---
typeset -a CXXFLAGS_COMMON
CXXFLAGS_COMMON=(-O2 -DNDEBUG -std=c++20 -DFF_LINUX -I"${SrcDir}/Headers")

echo
echo "== Compiling =="
echo "  CXXFLAGS_COMMON: ${CXXFLAGS_COMMON[*]}"
echo

set -x
"$GXX" "${CXXFLAGS_COMMON[@]}" -c FFCommon.cpp      -o build/FFCommon.o
"$GXX" "${CXXFLAGS_COMMON[@]}" -c FFLinkRouter.cpp   -o build/FFLinkRouter.o
"$GXX" -O2 -s -o build/FFLinkRouter build/FFCommon.o build/FFLinkRouter.o
set +x

echo
echo "== Installing router =="
sudo install -D -m 0755 build/FFLinkRouter "${Dest}/FFLinkRouter"

# --- Python watcher (you said you already have this file beside the script) ---
WatcherSrc="${SrcDir}/ff-focus-watcher.py"
if [[ ! -f "${WatcherSrc}" ]]; then
  echo "ERROR: ${WatcherSrc} not found. Place the file next to this script." >&2
  exit 2
fi

DataRoot="${XDG_DATA_HOME:-$HOME/.local/share}/FF"
mkdir -p "${DataRoot}"
sudo install -D -m 0755 "${WatcherSrc}" "${Dest}/ff-focus-watcher.py"

echo
echo "== Wiring systemd user service for watcher =="
UnitDir="$HOME/.config/systemd/user"
mkdir -p "${UnitDir}"

ServiceFile="${UnitDir}/ff-focus-watcher.service"
cat > "${ServiceFile}" <<'UNIT'
[Unit]
Description=FF Focus Watcher (Wayland/X11 -> focus.json)
After=graphical-session.target
Wants=graphical-session.target

[Service]
Type=simple
ExecStart=/usr/local/bin/ff-focus-watcher.py
Restart=always
RestartSec=2
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=default.target
UNIT

systemctl --user daemon-reload
systemctl --user enable --now ff-focus-watcher.service

echo
echo "== Optional: set FFLinkRouter as default handler =="
DesktopFile="$HOME/.local/share/applications/ff-link-router.desktop"
mkdir -p "$(dirname "${DesktopFile}")"
cat > "${DesktopFile}" <<EOF
[Desktop Entry]
Name=FF Link Router
Exec=/usr/local/bin/FFLinkRouter %u
Terminal=false
Type=Application
MimeType=x-scheme-handler/http;x-scheme-handler/https;text/html;
EOF

update-desktop-database ~/.local/share/applications >/dev/null 2>&1 || true
xdg-settings set default-web-browser ff-link-router.desktop || true

echo
echo "Installed router: ${Dest}/FFLinkRouter"
echo "Installed watcher: ${Dest}/ff-focus-watcher.py"
echo "Data root: ${DataRoot}"
