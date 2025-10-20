.PHONY: help install test validate format lint clean docker-up docker-down

# Default target
help:
	@echo "PromptFi Colloseum - Available Commands"
	@echo "========================================"
	@echo ""
	@echo "Setup & Installation:"
	@echo "  make install     - Install all dependencies with UV"
	@echo "  make validate    - Validate project setup"
	@echo ""
	@echo "Development:"
	@echo "  make test        - Run test suite with pytest"
	@echo "  make format      - Format code with black"
	@echo "  make lint        - Lint code with ruff"
	@echo "  make clean       - Clean up generated files"
	@echo ""
	@echo "Infrastructure:"
	@echo "  make docker-up   - Start docker containers (ClickHouse, Postgres, Redis, Grafana)"
	@echo "  make docker-down - Stop docker containers"
	@echo ""

install:
	@echo "📦 Installing dependencies with UV..."
	uv sync

validate:
	@echo "✅ Validating project setup..."
	uv run python scripts/validate_setup.py

test:
	@echo "🧪 Running test suite..."
	uv run pytest tests/ -v

format:
	@echo "🎨 Formatting code with black..."
	uv run black core/ data_plane/ tests/ scripts/ --line-length 100

lint:
	@echo "🔍 Linting code with ruff..."
	uv run ruff check core/ data_plane/ tests/ scripts/

clean:
	@echo "🧹 Cleaning up generated files..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true

docker-up:
	@echo "🐳 Starting docker containers..."
	docker-compose up -d
	@echo "Waiting for services to be ready..."
	@sleep 5
	@echo "✅ Infrastructure ready:"
	@echo "  - ClickHouse:  http://localhost:8123"
	@echo "  - PostgreSQL:  localhost:5432"
	@echo "  - Redis:       localhost:6379"
	@echo "  - Grafana:     http://localhost:3000"

docker-down:
	@echo "🛑 Stopping docker containers..."
	docker-compose down
