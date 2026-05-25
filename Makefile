.PHONY: install dev test lint format clean docker-up docker-down seed sync

## ── Setup ─────────────────────────────────────────────────────
install:
	uv sync

dev:
	uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

## ── Database ──────────────────────────────────────────────────
docker-up:
	docker compose up -d postgres

docker-down:
	docker compose down

seed:
	uv run python scripts/seed_data.py

## ── Testing ───────────────────────────────────────────────────
test:
	uv run pytest tests/ -v

## ── Code Quality ──────────────────────────────────────────────
lint:
	uv run ruff check app/ tests/

format:
	uv run ruff format app/ tests/

## ── Cleanup ───────────────────────────────────────────────────
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov uv.lock
