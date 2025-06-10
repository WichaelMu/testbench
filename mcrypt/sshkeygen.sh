#!/usr/bin/zsh

set -e

KEY_DIR="$HOME/.ssh/generated_keys"

mkdir -p "$KEY_DIR"

exec_generate_key_pair() {
  local REPO_STRING=$1

  if [[ -z "$REPO_STRING" ]]; then
    >&2 echo "[ERROR] Repository string is required!"
    return 1
  fi

  local KEY_NAME="$(echo "$REPO_STRING" | sed 's/[^a-zA-Z0-9_-]/-/g')"
  local KEY_PATH="$KEY_DIR/$KEY_NAME"

  ssh-keygen -t ed25519 -C "$REPO_STRING" -f "$KEY_PATH" -N "" && \
    echo "[INFO] SSH key generated: $KEY_PATH" && \
    echo ""
}

exec_generator_main() {

  if [[ $# -eq 0 ]]; then
    echo "[USAGE] Provide a list of repository strings as arguments."
    echo "Example: $0 \"git@github.com:uts-itd/repo1.git\" \"git@github.com:uts-itd/repo2.git\""
    echo ""
    echo "./sshkeygen.sh \$(paste -s -d '\" ' sshreposfile)"
    return 1
  fi

  for REPO in "$@"; do
    echo "[INFO] Processing: $REPO"
    exec_generate_key_pair "$REPO"
  done

}

exec_generator_main "$@"
