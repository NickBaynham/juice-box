import pytest
import yaml
from pydantic import ValidationError

from juicebox.api.errors import validation_error_detail
from juicebox.schemas.loading import load_agent_definition


def test_detail_carries_the_field_path():
    with pytest.raises(ValidationError) as caught:
        load_agent_definition("apiVersion: juicebox.ai/v2\nkind: Agent\n")
    detail = validation_error_detail(caught.value)
    assert detail[0]["loc"] == ["apiVersion"]
    assert "type" in detail[0] and "msg" in detail[0]


def test_detail_survives_an_empty_loc():
    """A document that is not a mapping reports loc == (); the body must
    still be JSON-serialisable and must not assume a field name."""
    with pytest.raises(ValidationError) as caught:
        load_agent_definition("- a\n- b\n")
    detail = validation_error_detail(caught.value)
    assert detail[0]["loc"] == []


def test_yaml_error_detail_is_a_single_entry():
    with pytest.raises(yaml.YAMLError) as caught:
        load_agent_definition("apiVersion: [unclosed\n")
    detail = validation_error_detail(caught.value)
    assert len(detail) == 1
    assert detail[0]["loc"] == []
