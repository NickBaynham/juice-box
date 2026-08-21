"""Unit test enforcing the workstream's exit criterion: the repository
layer under `persistence/` is the only module issuing queries.

Parses with `ast` rather than scanning source text. A text scan has both
failure modes this check exists to avoid:

- False positives: a docstring or comment mentioning `select(` or
  `session.execute` -- this module's own docstring, for instance -- trips
  a substring scan despite issuing no query.
- False negatives: a text scan catches only the spelling it was given.
  `sqlalchemy.select(...)`, `from sqlalchemy import select as sel`, and a
  session reached through an attribute (`self.session.execute(...)`,
  `db_session.scalars(...)`) all read differently in source and are all
  the violation this test must catch across W2 through W4.

`select` is resolved against each module's own imports rather than
matched by name, so an aliased import is caught and an unrelated
`select` -- a `selectors` object, a local helper of the same name -- is
not. Session calls are matched on the query-issuing methods the
repository layer actually uses, reached through any name ending in
`session`.

What it does not catch: a query issued through a name this module cannot
resolve statically, such as one fetched from a registry at runtime, or a
raw connection that never passes through a `session`-named binding.
"""

import ast
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[2] / "src" / "juicebox"
PERSISTENCE_ROOT = SRC_ROOT / "persistence"

# The query-issuing session methods the repository layer uses.
SESSION_QUERY_METHODS = frozenset({"execute", "scalars", "scalar", "get", "stream"})


def _scanned_modules() -> list[Path]:
    """Every `.py` file under `src/juicebox`, excluding `persistence/`."""
    return [
        path
        for path in SRC_ROOT.rglob("*.py")
        if PERSISTENCE_ROOT not in path.parents
    ]


def _final_identifier(expr: ast.expr) -> str | None:
    """The last dotted component of a name or attribute expression."""
    if isinstance(expr, ast.Name):
        return expr.id
    if isinstance(expr, ast.Attribute):
        return expr.attr
    return None


def _violations(tree: ast.AST) -> list[tuple[int, str]]:
    """Return `(line, marker)` for each disallowed call in `tree`.

    A `select(...)` or `sa.select(...)` call is the `select(` marker. An
    `x.execute(...)` call is the `session.execute` marker when `x`'s own
    final identifier is or ends with "session" (case-insensitive), which
    covers a bare `session` parameter as well as a `self.session` or
    `db_session` attribute.
    """
    found = []
    select_names = _sqlalchemy_select_names(tree)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if _resolves_to_select(func, select_names):
            found.append((node.lineno, "select("))
        elif (
            isinstance(func, ast.Attribute)
            and func.attr in SESSION_QUERY_METHODS
            and (base := _final_identifier(func.value)) is not None
            and base.lower().endswith("session")
        ):
            found.append((node.lineno, f"session.{func.attr}"))
    return found


def _sqlalchemy_select_names(tree: ast.AST) -> tuple[set[str], set[str]]:
    """Return the local names bound to sqlalchemy's `select` and to sqlalchemy.

    Resolving against imports is what separates a real query from a call
    that merely shares the name.
    """
    direct: set[str] = set()
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("sqlalchemy"):
            direct |= {alias.asname or alias.name for alias in node.names if alias.name == "select"}
        elif isinstance(node, ast.Import):
            modules |= {
                alias.asname or alias.name.split(".")[0]
                for alias in node.names
                if alias.name.startswith("sqlalchemy")
            }
    return direct, modules


def _resolves_to_select(func: ast.expr, names: tuple[set[str], set[str]]) -> bool:
    """Whether a call target is sqlalchemy's `select`, however it was bound."""
    direct, modules = names
    if isinstance(func, ast.Name):
        return func.id in direct
    if isinstance(func, ast.Attribute) and func.attr == "select":
        return _final_identifier(func.value) in modules
    return False


def test_no_module_outside_persistence_issues_queries():
    """The repository layer is the only module issuing queries.

    This is the executable form of W1's exit criterion. It exists because
    nothing else enforces it, and it is meant to catch W2 through W4
    regressions, not only this workstream's.
    """
    offenders = {}
    for module in _scanned_modules():
        violations = _violations(ast.parse(module.read_text()))
        if violations:
            offenders[module] = violations

    assert not offenders, "\n".join(
        f"{path.relative_to(SRC_ROOT.parent.parent)}:{line} contains {marker!r}"
        for path, lines in offenders.items()
        for line, marker in lines
    )


def test_scanned_modules_excludes_persistence_and_is_non_empty():
    """Tripwire: an empty or over-broad file list would make the test
    above pass or fail for the wrong reason."""
    scanned = _scanned_modules()
    assert scanned, "no modules found under src/juicebox"
    assert all(PERSISTENCE_ROOT not in path.parents for path in scanned)
    assert any(path.name == "app.py" for path in scanned)
