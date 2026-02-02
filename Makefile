.PHONY: help install dev lint format typecheck test test-cov clean build run frontend-install frontend-dev frontend-build frontend-test all-tests

# Default target
help:
	@echo "Available commands:"
	@echo "  install          Install dependencies"
	@echo "  dev              Install dev dependencies"
	@echo "  lint             Run linting checks"
	@echo "  format           Format code"
	@echo "  typecheck        Run type checking"
	@echo "  test             Run tests"
	@echo "  test-cov         Run tests with coverage"
	@echo "  clean            Clean cache and build files"
	@echo "  build            Build the project"
	@echo "  run              Run the application"
	@echo "  frontend-install Install frontend dependencies"
	@echo "  frontend-dev     Start frontend dev server"
	@echo "  frontend-build   Build frontend for production"
	@echo "  frontend-test    Run frontend tests"
	@echo "  all-tests        Run both backend and frontend tests"

# Backend commands
install:
	uv sync

dev:
	uv sync --dev

lint:
	uv run ruff check src/ tests/

format:
	uv run ruff format src/ tests/

typecheck:
	uv run mypy src/ --ignore-missing-imports

test:
	uv run pytest tests/ -v

test-cov:
	uv run pytest tests/ -v --cov=src

clean:
	rm -rf .ruff_cache/
	rm -rf src/__pycache__/
	rm -rf tests/__pycache__/
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf dist/
	rm -rf build/
	rm -rf *.egg-info/

build:
	uv build

run:
	uv run python main.py

# Frontend commands
frontend-install:
	cd frontend && npm install

frontend-dev:
	cd frontend && npm run dev

frontend-build:
	cd frontend && npm run build

frontend-test:
	cd frontend && npm test

# Combined commands
all-tests: test frontend-test

# Development workflow
check: lint typecheck test
	@echo "All checks passed!"

fix: format
	uv run ruff check src/ tests/ --fix
	@echo "Code formatted and auto-fixable issues resolved!"