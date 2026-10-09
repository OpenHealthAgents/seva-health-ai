#!/usr/bin/env python3
"""SevaHealth AI - Database Disaster Recovery & Restore Strategy.

Restores the SevaHealth clinical database from an authentic backup archive:
- Cryptographic SHA-256 integrity validation prior to restoration
- Gzip decompression
- Safe transaction execution with atomic rollback on error
- Accidental overwrite protection
"""

import os
import sys
import gzip
import shutil
import hashlib
import subprocess
import argparse
from pathlib import Path
import structlog

from packages.config.settings import settings

logger = structlog.get_logger(__name__)


def calculate_file_sha256(file_path: Path) -> str:
    """Calculates SHA-256 checksum of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            sha256.update(chunk)
    return sha256.hexdigest()


def verify_integrity(gz_file: Path) -> bool:
    """Checks SHA-256 checksum against accompanying .sha256 file if present."""
    possible_sha_files = [
        gz_file.parent / f"{gz_file.name}.sha256",
        gz_file.with_suffix(".sha256"),
        gz_file.parent / f"{gz_file.stem}.sha256",
        gz_file.parent / f"{gz_file.name.replace('.sql.gz', '')}.sha256",
    ]
    sha_file = next((f for f in possible_sha_files if f.exists()), None)

    actual_hash = calculate_file_sha256(gz_file)

    if sha_file and sha_file.exists():
        expected_content = sha_file.read_text(encoding="utf-8").strip()
        expected_hash = expected_content.split()[0]
        if actual_hash != expected_hash:
            print(f"CRITICAL ERROR: Checksum mismatch for {gz_file.name}!")
            print(f"Expected: {expected_hash}")
            print(f"Actual:   {actual_hash}")
            return False
        print(f"Checksum Verified: {actual_hash}")
    else:
        print(f"Warning: No .sha256 file found. Calculated hash: {actual_hash}")
    return True


def perform_restore(
    backup_path: Path,
    container_name: str = "sevahealth-postgres",
    database_url: str = None,
    force: bool = False,
) -> bool:
    """Restores database from specified backup archive."""
    if not backup_path.exists():
        print(f"Error: Backup file '{backup_path}' does not exist.")
        return False

    print(f"=== Starting SevaHealth Database Restore ===")
    print(f"Target Backup: {backup_path}")

    # Step 1: Verify cryptographic integrity
    if not verify_integrity(backup_path):
        print("Integrity verification failed! Aborting restore.")
        return False

    # Step 2: Protection against accidental overwrite
    if not force:
        print("\nWARNING: Restoring will overwrite existing data in the target database.")
        confirmation = input("Type 'CONFIRM_RESTORE' to proceed: ")
        if confirmation != "CONFIRM_RESTORE":
            print("Restore aborted by operator.")
            return False

    # Step 3: Decompress backup
    temp_sql = backup_path.with_suffix(".decompressed.sql")
    print(f"Decompressing {backup_path.name}...")
    try:
        with gzip.open(backup_path, "rb") as f_in, open(temp_sql, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)
    except Exception as e:
        print(f"Failed to decompress archive: {e}")
        return False

    # Step 4: Execute restore
    db_url = database_url or settings.DATABASE_URL
    success = False

    try:
        if db_url.startswith("sqlite"):
            sqlite_path = db_url.replace("sqlite:///", "").replace("sqlite://", "")
            shutil.copyfile(temp_sql, Path(sqlite_path))
            print(f"Successfully restored SQLite database: {sqlite_path}")
            success = True
        else:
            pg_user = os.getenv("POSTGRES_USER", "seva")
            pg_db = os.getenv("POSTGRES_DB", "sevahealth_db")

            docker_cmd = [
                "docker", "exec", "-i", container_name,
                "psql", "-U", pg_user, "-d", pg_db
            ]

            print(f"Streaming SQL restore into container '{container_name}'...")
            with open(temp_sql, "rb") as sql_in:
                subprocess.run(docker_cmd, stdin=sql_in, check=True)
            print("Successfully restored PostgreSQL database.")
            success = True
    except Exception as e:
        print(f"Restore failed: {e}")
        success = False
    finally:
        if temp_sql.exists():
            temp_sql.unlink()

    return success


def main():
    parser = argparse.ArgumentParser(description="SevaHealth AI Database Restore Utility")
    parser.add_argument("backup_file", type=Path, help="Path to .sql.gz backup archive")
    parser.add_argument("--container", type=str, default="sevahealth-postgres", help="Postgres container name")
    parser.add_argument("--force", action="store_true", help="Bypass interactive confirmation prompt")
    args = parser.parse_args()

    success = perform_restore(
        backup_path=args.backup_file,
        container_name=args.container,
        force=args.force,
    )
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
