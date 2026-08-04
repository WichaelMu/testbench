#!/usr/bin/zsh

DEFINE_ARG=""
DEFINES=()
OUT_FILE=""
SOURCE_FILES=()
NO_AOT_FLAG=0
# Mono 6.14's TermInfoReader rejects the current xterm-256color entry because
# its compiled terminfo file is larger than 4 KiB.  Limit only Mono's child
# processes to a widely available, small terminal definition.
MONO_TERM="${CSCOMPILE_TERM:-xterm-color}"

usage() {
  echo "Usage: $0 [--define DEFINE1,DEFINE2,...] [--no-aot] --out OUTFILE --source FILE1.cs [FILE2.cs ...]"
  echo "  --define   Comma-separated list of C# preprocessor defines. Optional."
  echo "  --no-aot   Skip Mono AOT step after build. Optional."
  echo "  --out      Output file path. Required."
  echo "  --source   Space-separated list of C# source files. Required; must be last argument."
  exit 1
}

# Argument Parsing
while [[ $# -gt 0 ]]; do
  case "$1" in
    --define)
      if [[ -n "$2" && "$2" != --* ]]; then
        IFS=',' read -rA DEFINES <<< "$2"
        shift 2
      else
        echo "Error: --define requires an argument."
        usage
      fi
      ;;

    --out)
      if [[ -n "$2" && "$2" != --* ]]; then
        OUT_FILE="$2"
        shift 2
      else
        echo "Error: --out requires an output path."
        usage
      fi
      ;;

    --no-aot)
      NO_AOT_FLAG=1
      shift
      ;;

    --source)
      shift
      if [[ $# -eq 0 ]]; then
        echo "Error: --source requires at least one filename."
        usage
      fi
      while [[ $# -gt 0 ]]; do
        SOURCE_FILES+=("$1")
        shift
      done
      ;;

    -h|--help|?)
      usage
      ;;

    *)
      echo "Unknown argument: $1"
      usage
      ;;

  esac
done

# Validate required args
if [[ -z "$OUT_FILE" ]]; then
  echo "Error: --out is required."
  usage
fi

if [[ ${#SOURCE_FILES[@]} -eq 0 ]]; then
  echo "Error: --source is required with at least one file."
  usage
fi

# Check for mcs
if ! command -v mcs >/dev/null 2>&1; then
  echo "Error: 'mcs' compiler not found or not executable in \$PATH."
  exit 1
fi

# Check source files exist
for SRC in "${SOURCE_FILES[@]}"; do
  if [[ ! -f "$SRC" ]]; then
    echo "Error: Source file '$SRC' does not exist in $(pwd)."
    exit 1
  fi
done

# Build define argument for mcs
if [[ ${#DEFINES[@]} -gt 0 ]]; then
  DEFINE_ARG="-define:$(IFS=','; echo "${DEFINES[*]}")"
fi

echo "Compiling ${SOURCE_FILES[*]} to $OUT_FILE..."
set -x
TERM="$MONO_TERM" mcs -out:"$OUT_FILE" -optimize+ $DEFINE_ARG "${SOURCE_FILES[@]}"
EXIT_CODE=$?
set +x

if [[ $EXIT_CODE -ne 0 ]]; then
  echo "Build failed."
  exit $EXIT_CODE
fi

echo "Build succeeded: $OUT_FILE"

# Decide whether to AOT (env NO_AOT=1 OR flag --no-aot disables it)
if [[ "${NO_AOT:-$NO_AOT_FLAG}" = "1" ]]; then
  echo "Skipping AOT (requested via --no-aot or NO_AOT=1)."
  exit 0
fi

# --- Mono AOT (Ahead-Of-Time) compile ---
if command -v mono >/dev/null 2>&1; then
	echo "AOT-compiling with: mono --aot=full \"$OUT_FILE\" ..."
	if TERM="$MONO_TERM" mono --aot=full "$OUT_FILE"; then
    if [[ -f "${OUT_FILE}.so" ]]; then
      strip -s "${OUT_FILE}.so" 2>/dev/null || true
    fi
    echo "AOT done."
  else
    echo "Warning: mono --aot failed; continuing with IL image."
  fi
else
  echo "Warning: 'mono' not found; skipping AOT."
fi
