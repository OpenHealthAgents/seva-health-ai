#!/usr/bin/env bash
# ==============================================================================
# SevaHealth AI - Automated Database Backup Shell Script
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="${SCRIPT_DIR}/../backups"
TIMESTAMP="$(date -u +%Y%m%d_%H%M%S)"
BACKUP_NAME="sevahealth_backup_${TIMESTAMP}"
CONTAINER="sevahealth-postgres"
POSTGRES_USER="${POSTGRES_USER:-seva}"
POSTGRES_DB="${POSTGRES_DB:-sevahealth_db}"

mkdir -p "${BACKUP_DIR}"

echo "=== SevaHealth Database Backup Shell Runner ==="
echo "Dumping database '${POSTGRES_DB}' from container '${CONTAINER}'..."

if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER}$"; then
    docker exec -t "${CONTAINER}" pg_dump -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" --clean --if-exists | gzip > "${BACKUP_DIR}/${BACKUP_NAME}.sql.gz"
    
    cd "${BACKUP_DIR}"
    sha256sum "${BACKUP_NAME}.sql.gz" > "${BACKUP_NAME}.sha256"
    
    echo "Backup completed: ${BACKUP_DIR}/${BACKUP_NAME}.sql.gz"
    echo "Checksum: $(cat ${BACKUP_NAME}.sha256)"
else
    echo "Notice: Container ${CONTAINER} is not running. Calling python fallback backup..."
    python3 "${SCRIPT_DIR}/backup_database.py" "$@"
fi
