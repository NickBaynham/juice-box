# Project

## Identity

Name: Juice Box
One-line description: Containerized orchestration platform that launches, controls, observes, and coordinates autonomous AI agents working against persistent objectives in isolated containers.

Specification: docs/specs/juice-box-spec.md

## Stack

Language and version: Python 3.12+
Package manager: pdm
Frameworks: FastAPI, Pydantic, SQLAlchemy, Alembic, asyncio, Pytest
Local services (docker compose): PostgreSQL, agent runtime containers (Docker)

## Constraints

- Work in small increments; each increment is tested before moving on.
- pdm for Python; Make targets for setup, lint, test, build, run.
- No emojis in code, docs, or output.
- API first: anything available in a UI must be available through the API.
- Provider agnostic: no hard dependency on a single LLM provider, agent framework, or cloud platform.
- Agents run under least privilege; secrets are referenced by name, never embedded in specs.
