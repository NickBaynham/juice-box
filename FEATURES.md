# Features

What works today. Planned work is tracked in [TODO.md](TODO.md).

## Build and test

- pdm project exposing the `juicebox` package with a declared version.
- Make targets for setup, lint, test, and build.
- Pytest suite with an `integration` marker that separates tests requiring
  Docker services from the default unit run.
- Ruff linting across the repository.
