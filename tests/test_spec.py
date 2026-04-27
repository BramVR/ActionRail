from __future__ import annotations

import pytest

from actionrail.actions import create_default_registry, validate_action_ids
from actionrail.spec import TRANSFORM_STACK_ID, action_ids, get_example_spec


def test_transform_stack_spec_matches_phase_zero_reference() -> None:
    spec = get_example_spec()

    assert spec.id == TRANSFORM_STACK_ID
    assert spec.anchor == "viewport.left.center"
    assert [item.label for item in spec.items if item.label] == ["M", "T", "R", "S", "K"]
    assert [item.type for item in spec.items] == [
        "toolButton",
        "toolButton",
        "toolButton",
        "toolButton",
        "spacer",
        "button",
    ]
    assert spec.items[3].tone == "pink"
    assert spec.items[5].tone == "teal"


def test_transform_stack_actions_are_registered() -> None:
    spec = get_example_spec()

    validate_action_ids(action_ids(spec), create_default_registry())


def test_unknown_example_id_raises() -> None:
    with pytest.raises(KeyError, match="missing"):
        get_example_spec("missing")
