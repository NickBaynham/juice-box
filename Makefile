.DEFAULT_GOAL := help

.PHONY: help install lint test build run

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "%-10s %s\n", $$1, $$2}'

install: ## Install dependencies
	pdm install

lint: ## Run the linter
	pdm run ruff check .

test: ## Run unit tests
	pdm run pytest -m "not integration"

build: ## Build the distribution
	pdm build

run: ## Run the API
	pdm run python -m juicebox
