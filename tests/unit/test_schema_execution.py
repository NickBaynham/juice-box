import pytest
from pydantic import ValidationError

from juicebox.schemas.agent import ApprovalOperation, Execution, Repository


def test_accepts_a_repository():
    repository = Repository.model_validate(
        {"url": "https://github.com/example/application",
         "branch": "juicebox/test-commander"}
    )
    assert repository.branch == "juicebox/test-commander"


def test_rejects_a_non_https_repository_url():
    with pytest.raises(ValidationError) as caught:
        Repository.model_validate({"url": "git@github.com:example/application.git"})
    assert caught.value.errors()[0]["loc"] == ("url",)


def test_accepts_known_approval_operations():
    execution = Execution.model_validate(
        {"max_iterations": 100, "require_approval_for": ["merge", "force-push"]}
    )
    assert ApprovalOperation.MERGE in execution.require_approval_for


def test_rejects_an_unknown_approval_operation():
    with pytest.raises(ValidationError) as caught:
        Execution.model_validate(
            {"max_iterations": 100, "require_approval_for": ["rm -rf /"]}
        )
    assert caught.value.errors()[0]["loc"] == ("require_approval_for", 0)


def test_rejects_a_non_positive_iteration_limit():
    with pytest.raises(ValidationError) as caught:
        Execution.model_validate({"max_iterations": 0})
    assert caught.value.errors()[0]["loc"] == ("max_iterations",)


def test_rejects_a_repository_url_carrying_credentials():
    """Specification section 17: secrets are referenced by name, never
    embedded. A credential in the URL would reach persisted JSONB and the
    clone command W6 runs.
    """
    with pytest.raises(ValidationError) as caught:
        Repository.model_validate(
            {"url": "https://user:token@github.com/example/application"}
        )
    assert caught.value.errors()[0]["loc"] == ("url",)
