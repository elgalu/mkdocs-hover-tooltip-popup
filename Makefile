SHELL := /bin/bash
.DEFAULT_GOAL := help
.PHONY: help setup all hooks check prek clean env build serve test tests test-unit test-e2e docs \
        version-bump pypi-build pypi-check pypi-publish pypi-publish-test pypi-all

help: ## Show this help message
	@echo "mkdocs-hover-tooltip-popup Makefile"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z0-9_-]+:.*?## / {printf "  %-18s %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""
	@echo "Note: 'make' alone prints this help. Run 'make setup' the first time you clone."

setup: ## First-time contributor setup (.venv, deps, prek hooks, d2 if needed)
	@./scripts/contributor-setup.sh

check: ## Run prek hooks (CI: changed files only; local: --all-files)
	@./scripts/check.sh

prek: ## Run prek on all files unconditionally
	@./scripts/prek.sh

test: ## Run all pytest tests with coverage (extra args via ARGS=...)
	@./scripts/test.sh $(ARGS)

tests: test ## Alias for 'test'

test-unit: ## Run only the fast unit tests (skip headless-browser E2E)
	@./scripts/test.sh -m "not e2e" $(ARGS)

test-e2e: ## Run only the headless-browser E2E tests
	@./scripts/test.sh -m e2e --no-cov $(ARGS)

build: ## Build demo docs (mkdocs build --strict, output: site/)
	@./scripts/build.sh

serve: ## Live-preview docs at http://127.0.0.1:8000
	@./scripts/serve.sh

docs: build ## Alias for 'build'

env: ## Print Python / uv / venv diagnostic info
	@./scripts/env.sh

clean: ## Remove .venv, build artifacts, caches, rendered site/
	@./scripts/clean.sh

version-bump: ## Bump version in pyproject (BUMP=patch|minor|major, default patch)
	@./scripts/version-bump.sh $(BUMP)

pypi-build: ## Build sdist + wheel into dist/ and validate (twine check)
	@./scripts/pypi-build.sh

pypi-check: pypi-build ## Alias for pypi-build (build + validate, no upload)

pypi-publish-test: ## Upload dist/ to TestPyPI (needs UV_PUBLISH_TOKEN_TEST)
	@./scripts/pypi-publish-test.sh

pypi-publish: ## Upload dist/ to PyPI (needs UV_PUBLISH_TOKEN)
	@./scripts/pypi-publish.sh

pypi-all: ## Full release: test -> version-bump (BUMP=) -> build -> publish to PyPI
	@$(MAKE) test
	@$(MAKE) version-bump BUMP=$(BUMP)
	@$(MAKE) pypi-build
	@$(MAKE) pypi-publish

all: check ## Alias for 'check'
hooks: check ## Alias for 'check'
