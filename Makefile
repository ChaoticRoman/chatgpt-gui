.PHONY: all lint format test xtest

all: lint xtest

lint:
	ruff check .
	ruff format --diff .

format:
	ruff format .

test:
	python -m pytest tests/ -v

xtest:
	python -m pytest tests/ -v -n 16
