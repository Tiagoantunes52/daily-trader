.PHONY: help install dev lint format typecheck test test-cov clean build run frontend-install frontend-dev frontend-build frontend-test all-tests

# Default target
help:
	@echo "Available commands:"
	@echo "  install          Install dependencies"
	@echo "  dev              Install dev dependencies"
	@echo "  lint             Run linting checks"
	@echo "  format           Format code"
	@echo "  typecheck        Run type checking"
	@echo "  test             Run tests in parallel"
	@echo "  test-cov         Run tests with coverage in parallel"
	@echo "  test-serial      Run tests serially (no parallelization)"
	@echo "  test-slow        Show the 20 slowest tests"
	@echo "  test-timeout     Run tests serially with timeout, stop on first failure"
	@echo "  clean            Clean cache and build files"
	@echo "  build            Build the project"
	@echo "  run              Run the application"
	@echo "  frontend-install Install frontend dependencies"
	@echo "  frontend-lint    Run frontend linting checks"
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
	uv run ty check src/

test:
	uv run pytest tests/ -v -n auto

test-cov:
	uv run pytest tests/ -v -n auto --cov=src

test-serial:
	uv run pytest tests/ -v

test-slow:
	uv run pytest tests/ -v -n auto --durations=20

test-timeout:
	uv run pytest tests/ -v --timeout=30 --timeout-method=thread -x

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

frontend-lint:
	cd frontend && npm run lint

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