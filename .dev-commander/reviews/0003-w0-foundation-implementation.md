# Review 0003: W0 foundation implementation

Scope: commits `4256168..37b43b0`, twelve commits, 29 files, 1477
insertions. The whole of workstream W0 as delivered by plan 0001.

Verdict: approve. Two blockers and two majors were found during review
and repaired before this record was written; the repairs are commits
`1d123d9`, `dd86556`, and `37b43b0`. The remaining findings are minors
carried into W1.

## Method

Each of the eight increments was reviewed against this rubric as it
landed, and the workstream was then reviewed as a whole. Reviews were
verification-based rather than reading-based: the container image was
rebuilt, the Compose stack was started and curled, `docs/development.md`
was executed verbatim in a clean clone, and the unit suite was
mutation-tested. Findings below cite what was run, not what was read.

## Correctness

No blocker or major findings outstanding.

**Repaired, was a blocker.** `.github/workflows/ci.yml:7` checked out at
the default `fetch-depth: 1`, but gitleaks-action scans `BASE^..HEAD` on
a push. Any push carrying two or more commits failed with `fatal:
ambiguous argument ... unknown revision`, proven by run 32100718124.
Run 32099590862 passed only because that push carried a single commit,
which makes the action fall back to `--log-opts=-1`. The secret-scan
gate had therefore never scanned more than one commit. Repaired in
`1d123d9` by setting `fetch-depth: 0`; verified on run 32101919046, a
genuine two-commit push, which scanned `dd86556^..37b43b0` and passed.

**Repaired, was a major.** `src/juicebox/config/settings.py` declared no
`extra` policy, so pydantic-settings raised `ValidationError` on any key
in `.env` it did not declare. `docs/development.md` documents `.env` as
a configuration mechanism and W8 will place `ANTHROPIC_API_KEY` there,
so following the documentation crashed the application at startup.
Repaired in `dd86556` with `extra="ignore"` and a covering test.

**Repaired, was a major.** `tests/unit/test_settings.py::test_defaults`
and `tests/unit/test_entrypoint.py` read whatever `JUICEBOX_` variables
and `.env` file the developer had. Proven: `JUICEBOX_API_PORT=9999 make
test` failed. W1 gives every developer a `JUICEBOX_DATABASE_URL`, which
would have turned the suite red for reasons unrelated to the code under
test. Repaired in `dd86556` with an autouse fixture in
`tests/unit/conftest.py`.

Every other claim in the plan's increments is backed by a passing test.
Exit criteria verified directly: `make install lint test build` all
green, `GET /health` returns 200 both from the bare process and from the
Compose stack, and both integration tests pass.

## Simplicity

No findings. `src/juicebox/__main__.py` is 20 lines and one function;
`app.py` is a factory and nothing more; `health.py` is a single route.
No speculative interfaces, no defensive branches, no exception handlers
beyond the one legitimate retry suppression in the container test's
polling loop.

## DRY

No findings at this size. One observation for later:
`__version__` is asserted as a literal `"0.1.0"` in three tests and
declared in both `pyproject.toml` and `src/juicebox/__init__.py`, so a
version bump is five edits. Worth `dynamic = ["version"]` when the first
bump happens, not before.

## Size

No findings. Every module is under 30 lines.

## Clarity

No findings. No emojis anywhere in code, output, or documentation,
verified by grep. Docstrings are one line each; naming carries the
meaning rather than comments.

## Tests

No findings. The unit suite was mutation-tested with seven mutations
covering the health payload, the route path, the `factory=True`
argument, the port default, and router registration. Every mutation was
caught. The container test was confirmed to exercise the freshly built
image rather than a cached one, and the database test was confirmed to
fail when pointed at a dead port rather than passing on a swallowed
exception. Failing-first evidence was recorded for every increment that
had a test; increments 7 and 8 have none by design, and the plan says so.

## Minor findings carried into W1

1. `Dockerfile:8-9` copies `src` before `pdm install`, so any source
   edit invalidates the dependency layer. Trivial today, grows as W1
   adds sqlalchemy, alembic, and asyncpg. The corrected plan text now
   specifies the two-stage `--no-self` form; adopt it in W1.
2. `tests/integration/test_container_image.py` runs `docker run` outside
   the `try`/`finally`, so an interrupted run leaves a container that
   poisons later local runs. CI is unaffected.
3. `docker-compose.yml` publishes both services on all interfaces.
   Binding `127.0.0.1` costs nothing and matters before W6 and W9 add an
   agent container runtime.
4. The API container runs as root. W9's plan mounts the Docker socket
   into this service, and root plus that socket is host root. Add a
   non-root `USER` while the Dockerfile is still four lines.
5. The CI workflow has no `permissions:` block and installs `pdm` and
   `pip-audit` unpinned, the only unreproducible surface in CI.
6. `log_level` has no consumer. Wire it in W4 or note that it is
   reserved.
7. The dependency scan audits the dev group alongside runtime
   dependencies, so a CVE in pytest would block a build that ships no
   pytest. Defensible, but split it if it ever blocks.
8. `gitleaks-action@v2` remains on Node 20 and has no v3. The
   deprecation annotation persists on every run.

## Documents needing amendment

- ADR-0001 states CI must provide a PostgreSQL service container. CI
  instead runs `make test`, which brings PostgreSQL up through Compose
  on the runner. The implementation is better, since it is one code path
  locally and in CI, but the ADR now describes something that does not
  exist.
- Design 0002 workstream criterion 2 requires `pdm run pytest
  tests/acceptance`, which exits 4 because that directory does not exist
  until W12. It contradicts criterion 3, which correctly traces no
  requirement to W0. Condition the acceptance run on a traced scenario
  existing.
- Design 0002 increment criterion 7 requires exactly one commit per
  increment. As written it penalises a self-review correction found
  after committing, which is what happened in increment 8, and rewards
  either hiding the correction or rewriting published history.
