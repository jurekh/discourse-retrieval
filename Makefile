.PHONY: build lint test clean

build:
	uv sync --group dev

lint:
	uv run ruff check .
	uv run ruff format --check .

test:
	uv run pytest

clean:
	rm -rf .venv dist *.egg-info .coverage .pytest_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
