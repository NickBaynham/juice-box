"""Proves every example document under `examples/` validates."""

from pathlib import Path

from juicebox.schemas.loading import load_agent_definition, load_objective

EXAMPLES = Path(__file__).resolve().parents[2] / "examples"


def test_every_agent_example_validates():
    paths = sorted(EXAMPLES.glob("*.agent.yaml"))
    assert paths, "no agent examples found"
    for path in paths:
        load_agent_definition(path.read_text())


def test_every_objective_example_validates():
    paths = sorted(EXAMPLES.glob("*.objective.yaml"))
    assert paths, "no objective examples found"
    for path in paths:
        load_objective(path.read_text())


def test_every_example_file_is_covered_by_a_glob():
    """A file named neither *.agent.yaml nor *.objective.yaml is checked by
    nothing, and the exit criterion claims every example validates."""
    covered = set(EXAMPLES.glob("*.agent.yaml")) | set(EXAMPLES.glob("*.objective.yaml"))
    assert set(EXAMPLES.glob("*.yaml")) == covered
