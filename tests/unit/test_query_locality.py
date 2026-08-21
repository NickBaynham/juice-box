"""Unit test enforcing the workstream's exit criterion: the repository
layer under `persistence/` is the only module issuing queries.

Parses with `ast` rather than scanning source text for the substrings
`"select("` and `"session.execute"`. A text scan has both failure modes
this check exists to avoid:

- False positives: a docstring or comment that merely mentions
  `select(` or `session.execute` (this very module's docstring, for
  instance) would trip a substring scan despite issuing no query.
- False negatives: a text scan only catches the literal spelling it was
  given. `sqlalchemy.select(...)`, a `select` imported under an alias, or
  a query issued through a session attribute not literally named
  `session` (`self.session.execute(...)`, `db_session.execute(...)`) all
  read differently in source but are exactly the violation this test
  must catch across W2 through W4, where the convention may be reused on
  a class rather than a bare parameter.

Structural matching on the call expression -- the final attribute of a
`select(...)` or `x.select(...)` call, and the base name of an
`x.execute(...)` call -- catches those variations and ignores comments
and strings entirely, which is what parsing rather than scanning buys.
"""

import ast
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[2] / "src" / "juicebox"
PERSISTENCE_ROOT = SRC_ROOT / "persistence"


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
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if _final_identifier(func) == "select":
            found.append((node.lineno, "select("))
        elif (
            isinstance(func, ast.Attribute)
            and func.attr == "execute"
            and (base := _final_identifier(func.value)) is not None
            and base.lower().endswith("session")
        ):
            found.append((node.lineno, "session.execute"))
    return found


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
