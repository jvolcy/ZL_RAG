#!/usr/bin/env bash
# Launch the Website Knowledge Assistant.
# Usage: ./start.sh [arguments passed to main.py]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [[ ! -d .venv ]]; then
    echo "Virtual environment not found. Run: source setup.sh" >&2
    exit 1
fi

# shellcheck disable=SC1091
source .venv/bin/activate
exec python main.py "$@"
