# ADR-0001: PostgreSQL is the persistence store from the first increment

## Status

Accepted — 2026-08-14. Resolves the conflict between spec section 22
(PostgreSQL listed as initial implementation) and section 26
(PostgreSQL listed as a Phase 2 addition).

## Context

Section 22 names PostgreSQL, SQLAlchemy, and Alembic as the initial stack.
Section 26 lists "PostgreSQL persistence" as a Phase 2 addition, implying
the MVP persists somewhere else. Both cannot hold.

The alternative reading is that the MVP uses SQLite or the filesystem and
migrates later. That migration is not free: Juice Box state is
JSON-shaped (task graphs, execution records, message history, tool
results), and SQLite's async story, JSON operators, and concurrent-writer
behavior differ enough from Postgres that the models, queries, and
migrations would be rewritten rather than ported. The project constraint
in CLAUDE.md also requires databases to run on Docker locally, which
removes the usual reason to prefer SQLite (no local service to run).

## Decision

PostgreSQL is the persistence store from the first increment that needs
persistence. Access is SQLAlchemy 2.x async ORM over asyncpg, with schema
managed by Alembic from the first migration. Postgres runs via
`docker compose` locally; no SQLite fallback and no in-memory production
path is provided.

Tests run against a real Postgres instance from `docker compose`, not
against a substitute engine.

Section 26 is amended: "PostgreSQL persistence" is removed from Phase 2.
What remains in Phase 2 is checkpoint and resume semantics, which
ADR-0002 governs.

## Consequences

- `make test` requires Docker to be running. The Makefile test target
  brings the database up before invoking pytest.
- No dual-dialect abstraction is needed; JSONB, `TIMESTAMPTZ`, and
  Postgres-specific indexes may be used directly.
- Contributors must run Docker locally. This is already a project
  constraint, so it adds no new requirement.
- CI must provide a Postgres service container.
