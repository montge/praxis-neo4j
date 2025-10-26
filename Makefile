.PHONY: help install test test-unit test-integration test-e2e test-all coverage lint format clean docker-up docker-down

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install dependencies
	pip install -r requirements.txt

install-dev: ## Install development dependencies
	pip install -e ".[dev]"

test: test-unit ## Run all tests (default: unit tests only)

test-unit: ## Run unit tests only
	pytest tests/unit/ -v --cov=src --cov-report=term --cov-report=html

test-integration: ## Run integration tests (requires Neo4j running)
	pytest tests/integration/ -v --cov=src --cov-report=term

test-e2e: ## Run end-to-end tests (requires Neo4j running)
	pytest tests/e2e/ -v --cov=src --cov-report=term

test-all: ## Run all tests including integration and e2e
	pytest tests/ -v --cov=src --cov-report=term --cov-report=html

coverage: ## Generate coverage report
	pytest tests/ --cov=src --cov-report=html --cov-report=term
	@echo "Coverage report generated in htmlcov/index.html"

lint: ## Run code quality checks
	black --check src/ tests/
	flake8 src/ tests/ --max-line-length=100 --extend-ignore=E203,W503
	mypy src/ --ignore-missing-imports

format: ## Format code with black
	black src/ tests/

clean: ## Clean up generated files
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf coverage.xml
	rm -rf tests/test_backups/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

docker-up: ## Start Neo4j with Docker
	./scripts/start.sh

docker-down: ## Stop Neo4j Docker container
	./scripts/stop.sh

docker-logs: ## Show Neo4j Docker logs
	docker compose logs neo4j --tail 50

docker-shell: ## Open shell in Neo4j container
	docker exec -it $$(docker compose ps -q neo4j) /bin/bash
