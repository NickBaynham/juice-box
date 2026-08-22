import pytest
from pydantic import ValidationError

from juicebox.schemas.loading import load_objective

MINIMAL = """
objective:
  id: improve-api-tests
  goal: Improve automated API test coverage.
  success_criteria:
    - critical API flows are tested
"""


def test_loads_a_minimal_objective():
    objective = load_objective(MINIMAL)
    assert objective.id == "improve-api-tests"
    assert objective.completion_action.commit is False


def test_rejects_an_objective_with_no_success_criteria():
    document = MINIMAL.replace(
        "  success_criteria:\n    - critical API flows are tested\n", ""
    )
    with pytest.raises(ValidationError) as caught:
        load_objective(document)
    assert caught.value.errors()[0]["loc"] == ("objective", "success_criteria")


def test_rejects_empty_success_criteria():
    document = MINIMAL.replace(
        "  success_criteria:\n    - critical API flows are tested\n",
        "  success_criteria: []\n",
    )
    with pytest.raises(ValidationError) as caught:
        load_objective(document)
    error = caught.value.errors()[0]
    assert error["loc"] == ("objective", "success_criteria")
    assert error["type"] == "too_short"


def test_rejects_an_id_that_is_not_a_slug():
    document = MINIMAL.replace("improve-api-tests", "Improve API Tests")
    with pytest.raises(ValidationError) as caught:
        load_objective(document)
    assert caught.value.errors()[0]["loc"] == ("objective", "id")


def test_pull_request_requires_push():
    document = MINIMAL + "  completion_action:\n    push: false\n    pull_request: true\n"
    with pytest.raises(ValidationError) as caught:
        load_objective(document)
    assert caught.value.errors()[0]["loc"] == ("objective", "completion_action")


def test_rejects_a_document_with_no_objective_key():
    with pytest.raises(ValidationError) as caught:
        load_objective("goal: do the thing\n")
    assert caught.value.errors()[0]["loc"] == ("objective",)


def test_rejects_a_whitespace_only_goal():
    """`system_prompt` strips and rejects blank; `goal` must match it."""
    document = MINIMAL.replace(
        "goal: Improve automated API test coverage.", 'goal: "   "'
    )
    with pytest.raises(ValidationError) as caught:
        load_objective(document)
    assert caught.value.errors()[0]["loc"] == ("objective", "goal")
