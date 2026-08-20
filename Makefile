.DEFAULT_GOAL := help

.PHONY: help install lint test test-integration build run migrate

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "%-18s %s\n", $$1, $$2}'

install: ## Install dependencies
	pdm install

lint: ## Run the linter
	pdm run ruff check .

test: ## Start the database and run unit tests
	docker compose up -d --wait db
	pdm run pytest -m "not integration"

test-integration: ## Start the database and run integration tests
	docker compose up -d --wait db
	pdm run pytest -m integration

build: ## Build the distribution
	pdm build

run: ## Build and start the Compose stack
	docker compose up -d --build

migrate: ## Apply pending Alembic migrations to the Compose database
	docker compose up -d --wait db
	docker compose run --rm api pdm run alembic upgrade head
