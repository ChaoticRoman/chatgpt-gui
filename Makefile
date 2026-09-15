.PHONY: all lint format test xtest importcheck typecheck ruffversion

# Keep in sync with RUFF_VERSION in .github/workflows/lint.yml
RUFF_VERSION := 0.16.6

all: lint xtest

ruffversion:
	@ruff --version | grep -qxF "ruff $(RUFF_VERSION)" || { \
		echo "ruff $(RUFF_VERSION) required, found: $$(ruff --version)"; \
		echo "install it with: pip install 'ruff==$(RUFF_VERSION)'"; \
		exit 1; }

lint: ruffversion
	ruff check .
	ruff format --diff .
	$(MAKE) importcheck
	$(MAKE) typecheck

format: ruffversion
	ruff format .

importcheck:
	python -c "import libopenai.auth, libopenai.constants, libopenai.core, libopenai.files, libopenai.pricing, libopenai.validation, libopenai.vectors, cli, dale, gui, pricing"

typecheck:
	pyright

test:
	python -m pytest tests/ -v

xtest:
	python -m pytest tests/ -v -n 16
