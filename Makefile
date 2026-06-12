.PHONY: all lint format test xtest importcheck typecheck

all: lint xtest

lint:
	ruff check .
	ruff format --diff .
	$(MAKE) importcheck
	$(MAKE) typecheck

format:
	ruff format .

importcheck:
	python -c "import libopenai.auth, libopenai.constants, libopenai.core, libopenai.files, libopenai.pricing, libopenai.validation, libopenai.vectors, cli, dale, gui"

typecheck:
	pyright

test:
	python -m pytest tests/ -v

xtest:
	python -m pytest tests/ -v -n 16
