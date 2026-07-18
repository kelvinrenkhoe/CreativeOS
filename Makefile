.PHONY: install test lint format format-check quality

install:
	python -m pip install -e ".[dev]"

test:
	pytest -q

lint:
	ruff check .

format:
	ruff format .
	ruff check . --fix

format-check:
	ruff format --check .

quality: lint format-check test
