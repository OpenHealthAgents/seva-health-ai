#!/usr/bin/env bash
# ==============================================================================
# SevaHealth AI - Database Migration Shell Script Wrapper
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=== SevaHealth AI: Running Database Migrations ==="

if command -v python3 &>/dev/null; then
    python3 "${SCRIPT_DIR}/migrate.py" "$@"
elif command -v python &>/dev/null; then
    python "${SCRIPT_DIR}/migrate.py" "$@"
else
    echo "Error: Python is required to execute migration runner." >&2
    exit 1
fi
