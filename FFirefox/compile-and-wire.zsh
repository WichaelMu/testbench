#!/usr/bin/zsh
set -euo pipefail

# --- Target user (works with/without sudo) ---
if [[ $EUID -eq 0 ]]; then
  [[ -n "${SUDO_USER:-}" ]] || { echo "Run as your user (or with sudo), not pure root." >&2; exit 1; }
  TUSER="$SUDO_USER"
else
  TUSER="$USER"
fi
TUID="$(id -u "$TUSER")"
TGID="$(id -g "$TUSER")"
THOME="$(getent passwd "$TUSER" | cut -d: -f6)"
[[ -z "$THOME" ]] && THOME="$HOME"

# --- Paths / names ---
DEST="${BINARIES:-/usr/local/bin}"   # set BINARIES="$HOME/.local/bin" to avoid sudo entirely
UNIT_DIR="$THOME/.config/systemd/user"
SERVICE="FFFocus-Tracker.service"
mkdir -p "$UNIT_DIR"

# --- Ensure binfmt 'cli' (no-extension CIL) ---
ensure_cli_binfmt() {
  local NAME=cli MONO=${MONO_PATH:-/usr/bin/mono} PKG=local-ff
  # ready
  if [[ ! -x "$MONO" ]]; then echo "mono not at $MONO; sudo apt install mono-runtime"; return 1; fi
  sudo modprobe binfmt_misc || true
  sudo mount -t binfmt_misc binfmt_misc /proc/sys/fs/binfmt_misc 2>/dev/null || true
  # clean
  if command -v update-binfmts >/dev/null 2>&1; then
    sudo update-binfmts --disable "$NAME" 2>/dev/null || true
    sudo update-binfmts --remove  "$NAME" 2>/dev/null || true
  fi
  [[ -e /proc/sys/fs/binfmt_misc/$NAME ]] && echo -1 | sudo tee /proc/sys/fs/binfmt_misc/$NAME >/dev/null || true
  # install fresh
  if command -v update-binfmts >/dev/null 2>&1; then
    sudo update-binfmts --install "$NAME" "$MONO" --package "$PKG" --magic 'MZ' --offset 0
  else
    echo ":$NAME:M::MZ::$MONO:" | sudo tee /proc/sys/fs/binfmt_misc/register >/dev/null
  fi
  # persist & reload
  echo ":$NAME:M::MZ::$MONO:" | sudo tee /etc/binfmt.d/99-mono-$NAME.conf >/dev/null
  sudo systemctl restart systemd-binfmt 2>/dev/null || sudo systemctl restart binfmt-support 2>/dev/null || true
}

# call it early:
ensure_cli_binfmt || exit 1

# --- Compiler pick ---
have_csc=false; have_mcs=false
command -v csc >/dev/null 2>&1 && have_csc=true
command -v mcs >/dev/null 2>&1 && have_mcs=true
$have_csc || $have_mcs || { echo "Need a C# compiler (your 'csc' alias or 'mcs')." >&2; exit 1; }

compile_one () {
  local OUT="$1"; shift
  local SRCS=("$@")
  echo "Compiling $OUT ..."
  if $have_csc; then
    csc --define LINUX --out "$OUT" --source "${SRCS[@]}"
  else
    mcs -d:LINUX -optimize+ -out:"$OUT" "${SRCS[@]}"
  fi
  chmod 0755 "$OUT"   # so binfmt can execute it directly
}

compile_one FFFocusTracker FFFocusTracker.cs FFCommon.cs
compile_one FFLinkRouter   FFLinkRouter.cs   FFCommon.cs

# --- Move helper: create dest dir if needed, move (not copy), set mode/owner ---
ensure_dir () {
  local D="$1"
  if [[ -d "$D" ]]; then return 0; fi
  if [[ -w "$(dirname "$D")" ]]; then
    mkdir -p "$D"
  else
    sudo mkdir -p "$D"
  fi
}

move_uo () {  # src dst mode
  local SRC="$1" DST="$2" MODE="${3:-0755}"
  local DDIR; DDIR="$(dirname "$DST")"
  ensure_dir "$DDIR"

  if [[ -w "$DDIR" ]]; then
    mv -f "$SRC" "$DST"
    chmod "$MODE" "$DST" || true
  else
    sudo mv -f "$SRC" "$DST"
    sudo chmod "$MODE" "$DST"
  fi

  # Ensure ownership (TUID:TGID). Needed if root performed the move across filesystems.
  local CUR_UID
  CUR_UID="$(stat -c %u "$DST" 2>/dev/null || echo "")"
  if [[ "$CUR_UID" != "$TUID" ]]; then
    sudo chown "$TUID:$TGID" "$DST" 2>/dev/null || true
  fi

  # Verify source is gone
  if [[ -e "$SRC" ]]; then
    echo "Warning: '$SRC' still exists after move; removing."
    rm -f -- "$SRC" 2>/dev/null || sudo rm -f -- "$SRC" 2>/dev/null || true
  fi
}

# --- Move the freshly built binaries into DEST ---
move_uo FFFocusTracker "$DEST/FFFocusTracker" 0755
move_uo FFLinkRouter   "$DEST/FFLinkRouter"   0755

# --- Sanity: confirm they are real CILs (not a script) ---
if command -v file >/dev/null 2>&1; then
  for f in "$DEST/FFFocusTracker" "$DEST/FFLinkRouter"; do
    file -b "$f" | grep -Eiq 'PE32|Mono/.NET|CLR' || { echo "Error: $f is not a valid CIL/PE image."; exit 2; }
  done
fi

# --- Create/Update user service (runs in user session; no mono prefix, no extension) ---
UNIT_FILE="$UNIT_DIR/$SERVICE"
if [[ ! -f "$UNIT_FILE" ]]; then
  cat >"$UNIT_FILE" <<UNIT
[Unit]
Description=FF Focus Tracker (records last-focused Firefox profile)
After=graphical-session.target
Wants=graphical-session.target

[Service]
Type=simple
Environment=HOME=$THOME
Environment=XDG_DATA_HOME=$THOME/.local/share
WorkingDirectory=$THOME
ExecStart=$DEST/FFFocusTracker
Restart=always
RestartSec=2

[Install]
WantedBy=default.target
UNIT
  chown "$TUID:$TGID" "$UNIT_FILE"
else
  sed -i "s|^ExecStart=.*|ExecStart=$DEST/FFFocusTracker|" "$UNIT_FILE"
  grep -q '^Environment=HOME=' "$UNIT_FILE" || sed -i "/^\[Service\]/a Environment=HOME=$THOME" "$UNIT_FILE"
  grep -q '^Environment=XDG_DATA_HOME=' "$UNIT_FILE" || sed -i "/^\[Service\]/a Environment=XDG_DATA_HOME=$THOME/.local/share" "$UNIT_FILE"
  grep -q '^WorkingDirectory=' "$UNIT_FILE" || sed -i "/^\[Service\]/a WorkingDirectory=$THOME" "$UNIT_FILE"
fi

# --- systemctl --user as the real user (never as root) ---
userctl () {
  local R="/run/user/$TUID"
  local CMD=(systemctl --user "$@")
  if [[ $EUID -eq 0 ]]; then
    sudo -u "$TUSER" XDG_RUNTIME_DIR="$R" DBUS_SESSION_BUS_ADDRESS="unix:path=$R/bus" "${CMD[@]}"
  else
    XDG_RUNTIME_DIR="$R" DBUS_SESSION_BUS_ADDRESS="unix:path=$R/bus" "${CMD[@]}"
  fi
}

# Ensure log dirs exist for the first run
mkdir -p "$THOME/.local/share/FF/logs" "$THOME/.local/share/FF/state"

# Reload + enable + (re)start
userctl daemon-reload || true
userctl enable "$SERVICE" >/dev/null 2>&1 || true
if userctl is-active "$SERVICE" >/dev/null 2>&1; then
  userctl restart "$SERVICE"
else
  userctl start "$SERVICE"
fi

echo "Done. Service: $SERVICE  |  Binaries: $DEST"
echo "Logs: $THOME/.local/share/FF/logs"
