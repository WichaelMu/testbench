#!/usr/bin/zsh

DEFINE_ARG=""
DEFINES=()
OUT_FILE=""
SOURCE_FILES=()

usage() {
  echo "Usage: $0 [--define DEFINE1,DEFINE2,...] --out OUTFILE --source FILE1.cs [FILE2.cs ...]"
  echo "  --define   Comma-separated list of C# preprocessor defines. Optional."
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
mcs -out:"$OUT_FILE" -optimize+ $DEFINE_ARG "${SOURCE_FILES[@]}"
set +x

EXIT_CODE=$?

if [[ $EXIT_CODE -eq 0 ]]; then
  echo "Build succeeded: $OUT_FILE"
else
  echo "Build failed."
  exit $EXIT_CODE
fi

