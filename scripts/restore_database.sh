#!/usr/bin/env bash
# ==============================================================================
# SevaHealth AI - Database Disaster Recovery Shell Script
# ==============================================================================

set -euo pipefail

if [ "$#" -lt 1 ]; then
    echo "Usage: $0 <path_to_backup.sql.gz> [--force]"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_FILE="$1"
shift

if command -v python3 &>/dev/null; then
    python3 "${SCRIPT_DIR}/restore_database.py" "${BACKUP_FILE}" "$@"
elif command -v python &>/dev/null; then
    python "${SCRIPT_DIR}/restore_database.py" "${BACKUP_FILE}" "$@"
else
    echo "Error: Python is required to execute restore utility." >&2
    exit 1
fi
