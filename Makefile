.PHONY: help install build test lint format clean docker-build docker-run demo

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
	pip install -r requirements.txt

install-dev: ## Install with dev dependencies
	pip install -e ".[dev]"

build: ## Build package
	python -m build

test: ## Run tests
	pytest

test-cov: ## Run tests with coverage
	pytest --cov=financial_control_tower --cov-report=html

lint: ## Run linters
	ruff check .

format: ## Format code
	black .
	ruff check --fix .

clean: ## Clean build artifacts
	rm -rf build/ dist/ *.egg-info/ .pytest_cache/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

docker-build: ## Build Docker image
	docker build -t financial-control-tower:latest .

docker-run: ## Run Docker container
	docker run -p 8501:8501 financial-control-tower:latest

demo: ## Run demo with sample data
	bash run.sh

validate: ## Run validation checks
	python -c "import src.audit.financial_control_tower as fct; print('✓ FCT module loaded')"

quickstart: ## Quick start: install and demo
	$(MAKE) install
	$(MAKE) demo
