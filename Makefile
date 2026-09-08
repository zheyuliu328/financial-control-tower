.PHONY: install install-dev build test test-cov lint format demo quickstart verify run-real

install:
	python -m pip install .
install-dev:
	python -m pip install '.[dev]'
build:
	python -m build
test:
	python -m pytest
test-cov:
	python -m pytest --cov=financial_control_tower --cov-report=term
lint:
	python -m ruff check src scripts tests main.py quick_demo.py fraud_rule_metrics.py
	python -m ruff format --check src scripts tests main.py quick_demo.py fraud_rule_metrics.py
format:
	python -m ruff format src scripts tests main.py quick_demo.py fraud_rule_metrics.py
demo:
	python main.py --sample
quickstart: demo
verify:
	bash scripts/verify.sh
run-real:
	python scripts/run_real.py "$(CSV)" --output "$(OUTPUT)"
