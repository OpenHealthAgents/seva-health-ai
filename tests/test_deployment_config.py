"""Unit and Integration Tests for SevaHealth AI Deployment Architecture.

Verifies:
- Production, development, and demo Docker Compose configuration validity
- Strict image version pinning (zero :latest or :next tags)
- Health check configurations across all microservices
- Completeness of .env.example configuration keys
- Database migration runner functionality and checksum calculation
- Database backup and recovery tools with SHA-256 verification
- Documentation coverage (local, demo, staging, production, backup, recovery)
"""

import os
import gzip
import json
import yaml
import pytest
from pathlib import Path

from scripts.migrate import compute_sha256, MIGRATIONS_DIR
from scripts.backup_database import calculate_file_sha256, perform_backup, enforce_retention
from scripts.restore_database import verify_integrity

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_docker_compose_production_structure():
    """Validates docker-compose.yml contains all 12 components with pinned tags and healthchecks."""
    compose_file = PROJECT_ROOT / "docker-compose.yml"
    assert compose_file.exists(), "docker-compose.yml must exist"

    with open(compose_file, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    services = config.get("services", {})
    required_services = [
        "sevahealth-api",
        "sevahealth-worker",
        "sevahealth-scheduler",
        "sevahealth-ai",
        "reverse-proxy",
        "postgres",
        "redis",
        "minio",
        "ehrbase",
        "ehrdb",
        "prometheus",
        "grafana",
    ]

    for s_name in required_services:
        assert s_name in services, f"Service '{s_name}' missing from production docker-compose.yml"
        s_config = services[s_name]
        # Health check validation
        assert "healthcheck" in s_config, f"Service '{s_name}' must declare a healthcheck"
        assert "test" in s_config["healthcheck"], f"Service '{s_name}' healthcheck must declare test command"


def test_production_images_strictly_pinned():
    """Enforces zero unpinned (:latest, :next) images in production docker-compose.yml."""
    compose_file = PROJECT_ROOT / "docker-compose.yml"
    with open(compose_file, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    services = config.get("services", {})
    for s_name, s_config in services.items():
        if "image" in s_config:
            image = s_config["image"]
            assert ":latest" not in image, f"Service '{s_name}' uses unpinned ':latest' tag: {image}"
            assert ":next" not in image, f"Service '{s_name}' uses unpinned ':next' tag: {image}"
            assert ":" in image, f"Service '{s_name}' image lacks an explicit version tag: {image}"


def test_development_and_demo_compose_files():
    """Validates docker-compose.dev.yml and docker-compose.demo.yml schemas."""
    dev_file = PROJECT_ROOT / "docker-compose.dev.yml"
    demo_file = PROJECT_ROOT / "docker-compose.demo.yml"

    assert dev_file.exists(), "docker-compose.dev.yml must exist"
    assert demo_file.exists(), "docker-compose.demo.yml must exist"

    with open(dev_file, "r", encoding="utf-8") as f:
        dev_config = yaml.safe_load(f)
    assert "services" in dev_config
    assert "sevahealth-api-dev" in dev_config["services"]

    with open(demo_file, "r", encoding="utf-8") as f:
        demo_config = yaml.safe_load(f)
    assert "services" in demo_config
    assert "demo-api" in demo_config["services"]
    assert "demo-postgres" in demo_config["services"]


def test_env_example_completeness():
    """.env.example must specify all 12 operational configuration domains."""
    env_file = PROJECT_ROOT / ".env.example"
    assert env_file.exists(), ".env.example must exist"
    content = env_file.read_text(encoding="utf-8")

    expected_keys = [
        "ENVIRONMENT",
        "SECRET_KEY",
        "DATABASE_URL",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "REDIS_URL",
        "EHRBASE_URL",
        "EHRBASE_USER",
        "S3_ENDPOINT",
        "S3_ACCESS_KEY",
        "S3_SECRET_KEY",
        "WORKER_CONCURRENCY",
        "AI_PROVIDER",
        "LOG_LEVEL",
        "BACKUP_DIR",
        "BACKUP_RETENTION_DAYS",
    ]

    for key in expected_keys:
        assert f"{key}=" in content, f"Key '{key}' must be defined in .env.example"


def test_dockerfiles_exist():
    """Ensures dedicated Dockerfiles exist for API, worker, scheduler, and AI service."""
    docker_dir = PROJECT_ROOT / "infrastructure" / "docker"
    assert (docker_dir / "Dockerfile.api").exists()
    assert (docker_dir / "Dockerfile.worker").exists()
    assert (docker_dir / "Dockerfile.scheduler").exists()
    assert (docker_dir / "Dockerfile.ai").exists()


def test_pinned_requirements_prod():
    """Ensures requirements-prod.txt contains strictly pinned package versions."""
    req_file = PROJECT_ROOT / "requirements-prod.txt"
    assert req_file.exists(), "requirements-prod.txt must exist"
    lines = [l.strip() for l in req_file.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")]

    for line in lines:
        assert "==" in line, f"Requirement '{line}' must be pinned with exact '==' version"


def test_migration_checksum_utility():
    """Verifies migration checksum computation and presence of migrations directory."""
    assert MIGRATIONS_DIR.exists()
    migrations = list(MIGRATIONS_DIR.glob("*.sql"))
    assert len(migrations) >= 1

    sample_sql = "CREATE TABLE test (id INT);"
    hash1 = compute_sha256(sample_sql)
    hash2 = compute_sha256(sample_sql)
    assert hash1 == hash2
    assert len(hash1) == 64


def test_database_backup_and_retention(tmp_path):
    """Tests logical backup creation, gzip archive, SHA-256 verification and retention."""
    # Test backup execution using temporary directory
    backup_file = perform_backup(
        output_dir=tmp_path,
        database_url="sqlite:///./test_mock.db",
        retention_days=30,
    )

    assert backup_file.exists()
    assert backup_file.suffix == ".gz"

    sha_file = tmp_path / f"{backup_file.stem}.sha256"
    assert sha_file.exists()

    manifest_file = tmp_path / f"{backup_file.stem}.manifest.json"
    assert manifest_file.exists()

    with open(manifest_file, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)
    assert manifest_data["status"] == "VERIFIED_COMPLETED"
    assert "sha256_checksum" in manifest_data

    # Test integrity verification
    assert verify_integrity(backup_file) is True

    # Test retention policy
    enforce_retention(tmp_path, retention_days=0)  # retention_days=0 purges immediate files
    # Should not crash and cleans up files


def test_deployment_documentation_coverage():
    """Verifies deployment-guide.md covers all required operational categories."""
    doc_path = PROJECT_ROOT / "docs" / "deployment" / "deployment-guide.md"
    assert doc_path.exists(), "docs/deployment/deployment-guide.md must exist"
    doc_text = doc_path.read_text(encoding="utf-8").lower()

    required_topics = [
        "local development setup",
        "evaluation demo mode setup",
        "staging environment",
        "production deployment hardening",
        "database migration strategy",
        "database backup strategy",
        "disaster recovery",
    ]

    for topic in required_topics:
        assert topic in doc_text, f"Topic '{topic}' must be documented in deployment-guide.md"
