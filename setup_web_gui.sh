#!/usr/bin/env bash
# Bootstrap a Python virtual environment and install dependencies for the Lookout Web Activity GUI.

set -euo pipefail

VENV_DIR="${VENV_DIR:-.venv}"  # override using VENV_DIR env var
PYTHON_BIN="${PYTHON_BIN:-python3}"

usage() {
    cat <<USAGE
Usage: $0 [--venv PATH] [--python PYTHON]

Options:
  --venv PATH     Target directory for the virtual environment (default: $VENV_DIR)
  --python CMD    Python interpreter to use (default: $PYTHON_BIN)
  --help          Show this help message

Environment overrides:
  VENV_DIR        Same as --venv
  PYTHON_BIN      Same as --python
USAGE
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --venv)
            shift
            [[ $# -gt 0 ]] || { echo "Missing value for --venv" >&2; exit 1; }
            VENV_DIR="$1"
            ;;
        --python)
            shift
            [[ $# -gt 0 ]] || { echo "Missing value for --python" >&2; exit 1; }
            PYTHON_BIN="$1"
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        *)
            echo "Unknown argument: $1" >&2
            usage >&2
            exit 1
            ;;
    esac
    shift

done

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    echo "ERROR: Could not find python interpreter '$PYTHON_BIN'." >&2
    exit 1
fi

# Create virtual environment if it does not exist yet
if [[ ! -d "$VENV_DIR" ]]; then
    echo "Creating virtual environment in '$VENV_DIR'"
    "$PYTHON_BIN" -m venv "$VENV_DIR"
else
    echo "Reusing existing virtual environment '$VENV_DIR'"
fi

# shellcheck disable=SC1090
source "$VENV_DIR"/bin/activate

pip install --upgrade pip
pip install -r requirements.txt

echo
cat <<SUMMARY
Virtual environment ready.
To activate it run:
  source "$VENV_DIR"/bin/activate

Then start the GUI with:
  python lookout_web_activity_gui.py
SUMMARY
