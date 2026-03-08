.PHONY: test lint format

test:
	python -m pytest tests/ -v

lint:
	ruff check -v .
	ruff format --diff .

format:
	ruff format .
