#!/usr/bin/env bash

if [[ "${BASH_SOURCE}" == "${0}" ]]; then
    echo "ERROR: This script must be sourced to affect your environement."
    echo "Execute with" 
    echo ". $0"
    echo or
    echo "source $0"
    exit 1
fi

set -euo pipefail
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
