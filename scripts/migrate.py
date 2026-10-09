#!/usr/bin/env python3
"""SevaHealth AI - Production Database Migration Strategy & Runner.

Applies sequential, versioned SQL migrations located in infrastructure/postgres/migrations/
Tracks applied migrations in the `schema_migrations` ledger table with SHA-256 integrity hashes.
"""

import os
import sys
import argparse
import hashlib
from pathlib import Path
from datetime import datetime, timezone
import structlog
import sqlalchemy
from sqlalchemy import text

from packages.config.settings import settings

logger = structlog.get_logger(__name__)

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "infrastructure" / "postgres" / "migrations"


def compute_sha256(content: str) -> str:
    """Computes SHA-256 hash of migration script content."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def get_db_engine(db_url: str = None):
    """Initializes SQLAlchemy database engine."""
    url = db_url or settings.DATABASE_URL
    return sqlalchemy.create_engine(url, pool_pre_ping=True)


def ensure_migrations_table(engine):
    """Creates schema_migrations tracking table if it does not exist."""
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS schema_migrations (
        version VARCHAR(255) PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        checksum VARCHAR(64) NOT NULL,
        applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """
    with engine.begin() as conn:
        conn.execute(text(create_table_sql))


def get_applied_migrations(engine):
    """Retrieves map of applied migration versions and their checksums."""
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version, name, checksum, applied_at FROM schema_migrations ORDER BY version ASC"))
        return {row[0]: {"name": row[1], "checksum": row[2], "applied_at": row[3]} for row in result}


def run_migrations(db_url: str = None, dry_run: bool = False, verbose: bool = True):
    """Discovers and applies pending migrations sequentially."""
    engine = get_db_engine(db_url)
    ensure_migrations_table(engine)
    applied = get_applied_migrations(engine)

    if not MIGRATIONS_DIR.exists():
        logger.error("migrations_dir_not_found", path=str(MIGRATIONS_DIR))
        return False

    migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    if not migration_files:
        logger.info("no_migration_files_found", path=str(MIGRATIONS_DIR))
        return True

    pending = []
    for file_path in migration_files:
        version = file_path.stem.split("_")[0]
        content = file_path.read_text(encoding="utf-8")
        checksum = compute_sha256(content)

        if version in applied:
            recorded = applied[version]
            if recorded["checksum"] != checksum:
                logger.warning(
                    "migration_checksum_mismatch",
                    version=version,
                    file=file_path.name,
                    expected=recorded["checksum"],
                    actual=checksum,
                )
        else:
            pending.append((version, file_path.name, checksum, content))

    if verbose:
        print(f"=== SevaHealth Database Migration Runner ===")
        print(f"Database URL: {engine.url.render_as_string(hide_password=True)}")
        print(f"Total Migrations: {len(migration_files)} | Applied: {len(applied)} | Pending: {len(pending)}\n")

    if not pending:
        if verbose:
            print("Database schema is fully up to date! No pending migrations.")
        return True

    if dry_run:
        print("Dry Run Mode: The following migrations would be applied:")
        for ver, name, csum, _ in pending:
            print(f"  [PENDING] {name} (Version: {ver}, SHA-256: {csum[:12]}...)")
        return True

    # Apply pending migrations transactionally
    for ver, name, csum, content in pending:
        if verbose:
            print(f"Applying migration: {name} ...", end=" ", flush=True)

        try:
            with engine.begin() as conn:
                # Execute migration statements
                # Split by semicolon or execute as script block
                conn.execute(text(content))
                # Record in schema_migrations
                conn.execute(
                    text("INSERT INTO schema_migrations (version, name, checksum, applied_at) VALUES (:ver, :name, :csum, CURRENT_TIMESTAMP)"),
                    {"ver": ver, "name": name, "csum": csum},
                )
            if verbose:
                print("SUCCESS")
        except Exception as e:
            if verbose:
                print("FAILED!")
            logger.error("migration_failed", file=name, error=str(e))
            raise e

    if verbose:
        print(f"\nSuccessfully applied {len(pending)} migration(s).")
    return True


def show_status(db_url: str = None):
    """Displays migration status table."""
    engine = get_db_engine(db_url)
    ensure_migrations_table(engine)
    applied = get_applied_migrations(engine)
    migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))

    print("\n--- SevaHealth Schema Migration Status ---")
    print(f"{'Version':<10} {'Status':<12} {'Migration Name':<35} {'Applied At':<25}")
    print("-" * 82)

    for file_path in migration_files:
        version = file_path.stem.split("_")[0]
        name = file_path.name
        if version in applied:
            status = "APPLIED"
            applied_at = str(applied[version]["applied_at"])[:19]
        else:
            status = "PENDING"
            applied_at = "-"
        print(f"{version:<10} {status:<12} {name:<35} {applied_at:<25}")
    print("-" * 82 + "\n")


def main():
    parser = argparse.ArgumentParser(description="SevaHealth AI Database Migration Runner")
    parser.add_argument("--db-url", type=str, default=None, help="Database connection URL")
    parser.add_argument("--check", action="store_true", help="Dry run check for pending migrations")
    parser.add_argument("--status", action="store_true", help="Display migration status report")
    args = parser.parse_args()

    if args.status:
        show_status(args.db_url)
        sys.exit(0)

    success = run_migrations(db_url=args.db_url, dry_run=args.check, verbose=True)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
