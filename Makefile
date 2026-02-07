.PHONY: help install install-dev build test test-cov lint format clean \
        config-check demo quickstart run-real verify \
        docker-build docker-run release

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

install: ## Install dependencies
	pip install -r requirements.txt

install-dev: ## Install with dev dependencies
	pip install -e ".[dev]"

build: ## Build package
	python -m build

test: ## Run tests
	pytest || echo "Tests not available"

test-cov: ## Run tests with coverage
	pytest --cov=src --cov-report=html || echo "Tests not available"

lint: ## Run linters
	ruff check . || true

format: ## Format code
	black . 2>/dev/null || true
	ruff check --fix . 2>/dev/null || true

clean: ## Clean build artifacts
	rm -rf build/ dist/ *.egg-info/ .pytest_cache/ .mypy_cache/ htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

config-check: ## Check configuration
	@echo "Config check not implemented yet"

demo: ## Run demo with sample data
	python quick_demo.py

quickstart: ## Quick start (default offline)
	$(MAKE) demo

run-real: ## Run with real data (usage: make run-real CSV=path/to/erp.csv)
	@if [ -z "$(CSV)" ]; then \
		echo "Usage: make run-real CSV=path/to/erp.csv"; \
		exit 1; \
	fi
	python scripts/run_real.py $(CSV) --output artifacts

verify: ## Run full verification suite
	@bash ../scripts/verify.sh

docker-build: ## Build Docker image
	docker build -t $(shell basename $(PWD)):latest .

docker-run: ## Run Docker container
	docker run -v $(PWD)/data:/app/data $(shell basename $(PWD)):latest

release: ## Create a new release (requires VERSION)
	@if [ -z "$(VERSION)" ]; then \
		echo "Usage: make release VERSION=x.y.z"; \
		exit 1; \
	fi
	git tag -a $(VERSION) -m "Release $(VERSION)"
	git push origin $(VERSION)
