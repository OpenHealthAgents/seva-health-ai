.PHONY: help install dev test lint seed docker-up docker-down clean

help:
	@echo "SevaHealth AI Development Commands"
	@echo "  make install     - Install Python dependencies"
	@echo "  make dev         - Start FastAPI backend with auto-reload"
	@echo "  make test        - Run test suite"
	@echo "  make lint        - Run linter and type checker"
	@echo "  make seed        - Populate synthetic patient personas & regional data"
	@echo "  make docker-up   - Start full stack in Docker Compose"
	@echo "  make docker-down - Stop Docker Compose stack"
	@echo "  make clean       - Remove cached files and SQLite databases"

install:
	pip install -e ".[dev]"

dev:
	python -m uvicorn services.api.main:app --reload --port 8000 --host 0.0.0.0

test:
	pytest tests -v --tb=short

lint:
	ruff check .
	mypy packages services agents ml

seed:
	python scripts/seed_data.py

docker-up:
	docker compose up --build -d

docker-down:
	docker compose down

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -f sevahealth.db
