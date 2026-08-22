"""Objective envelope: specification section 9."""

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from juicebox.schemas.agent import NAME_PATTERN


class CompletionAction(BaseModel):
    """The `completion_action:` block: what W10 does once W9 detects success.

    `pull_request` requires `push`, and `push` requires `commit` — W10
    pushes a branch it committed to, and a pull request needs a pushed
    branch. The impossible combination is better refused here than
    discovered at the end of a run.
    """

    model_config = ConfigDict(extra="forbid")

    commit: bool = False
    push: bool = False
    pull_request: bool = False

    @model_validator(mode="after")
    def _check_dependencies(self) -> "CompletionAction":
        if self.push and not self.commit:
            raise ValueError("push requires commit")
        if self.pull_request and not self.push:
            raise ValueError("pull_request requires push")
        return self


class Objective(BaseModel):
    """The `objective:` block an agent works toward.

    `success_criteria` is required and non-empty because W9 detects
    completion against it; an objective without any can never finish.
    `tasks` stays optional because section 10 has the agent decompose the
    goal itself. `context` values are strings only; increment 7 documents
    the restriction so a reader does not write `version: 1.2` and get a
    type error.
    """

    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=NAME_PATTERN)
    goal: str = Field(min_length=1)
    context: dict[str, str] = {}
    tasks: list[str] = []
    constraints: list[str] = []
    success_criteria: list[str] = Field(min_length=1)
    completion_action: CompletionAction = CompletionAction()

    @field_validator("success_criteria", mode="before")
    @classmethod
    def _empty_key_means_empty_list(cls, value: list[str] | None) -> list[str]:
        """Treat `success_criteria:` written with no items as `[]`.

        YAML parses a key followed by nothing as `None`, not an empty
        list, which would otherwise fail as a type error rather than the
        `min_length=1` check below.
        """
        return [] if value is None else value


class ObjectiveDocument(BaseModel):
    """The document envelope: unwraps the top-level `objective:` key.

    Validating through a model, rather than subscripting the parsed
    mapping, ensures every error `loc` inside an objective begins
    `("objective", ...)`, and that a missing key, a top-level list, or an
    empty document all raise `pydantic.ValidationError` instead of
    `KeyError` or `TypeError`.
    """

    model_config = ConfigDict(extra="forbid")

    objective: Objective
