"""Maps a validation failure to the JSON body a 422 response carries."""

from typing import Any

import yaml
from pydantic import ValidationError


def validation_error_detail(error: ValidationError | yaml.YAMLError) -> list[dict[str, Any]]:
    """Return one detail entry per underlying failure, with `loc` as a list.

    A `ValidationError` contributes one entry per `error.errors()`, each
    carrying its field path, message, and type; `loc` becomes a list
    because a tuple is not JSON, and an empty `loc` stays `[]` rather than
    being dropped. A `yaml.YAMLError` has no field path, so it becomes a
    single entry with `loc == []` and `type == "yaml_error"`.
    """
    if isinstance(error, ValidationError):
        return [
            {"loc": list(item["loc"]), "msg": item["msg"], "type": item["type"]}
            for item in error.errors()
        ]
    return [{"loc": [], "msg": str(error), "type": "yaml_error"}]
