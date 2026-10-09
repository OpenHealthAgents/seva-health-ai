#!/usr/bin/env bash
# ==============================================================================
# SevaHealth AI - Challenge Demo Shell Runner (`./scripts/demo.sh`)
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

if command -v python3 &>/dev/null; then
    python3 "${SCRIPT_DIR}/demo.py" "$@"
elif command -v python &>/dev/null; then
    python "${SCRIPT_DIR}/demo.py" "$@"
else
    echo "Error: Python is required to run the SevaHealth demo." >&2
    exit 1
fi
