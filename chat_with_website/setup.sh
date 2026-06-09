#!/usr/bin/env bash
# Create virtual environment and install dependencies.
# Usage: source setup.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [[ ! -d .venv ]]; then
    python3 -m venv .venv
    echo "Created virtual environment at .venv"
fi

# shellcheck disable=SC1091
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "Setup complete. Virtual environment is active."
echo "Run: python main.py --help"
