from __future__ import annotations

import pytest

from actionrail.actions import create_default_registry, validate_action_ids
from actionrail.spec import (
    TRANSFORM_STACK_ID,
    action_ids,
    get_example_spec,
    load_builtin_preset,
    parse_stack_spec,
)


def test_transform_stack_spec_matches_phase_zero_reference() -> None:
    spec = get_example_spec()

    assert spec.id == TRANSFORM_STACK_ID
    assert spec.anchor == "viewport.left.center"
    assert spec.layout.orientation == "vertical"
    assert spec.layout.rows == 5
    assert spec.layout.columns == 1
    assert spec.layout.locked is True
    assert [item.label for item in spec.items if item.label] == ["M", "T", "R", "S", "K"]
    assert [item.id for item in spec.items] == [
        "transform_stack.move",
        "transform_stack.translate",
        "transform_stack.rotate",
        "transform_stack.scale",
        "transform_stack.gap",
        "transform_stack.set_key",
    ]
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
    assert spec.items[0].tooltip == "Move tool"
    assert spec.items[5].key_label == "S"
    assert spec.items[3].active_when == "maya.tool == scale"


def test_transform_stack_actions_are_registered() -> None:
    spec = get_example_spec()

    validate_action_ids(action_ids(spec), create_default_registry())


def test_unknown_example_id_raises() -> None:
    with pytest.raises(KeyError, match="missing"):
        get_example_spec("missing")


def test_parse_stack_spec_validates_basic_shape() -> None:
    with pytest.raises(ValueError, match="items"):
        parse_stack_spec({"id": "broken", "anchor": "viewport.left.center", "items": []})


def test_horizontal_rail_loads_from_json() -> None:
    spec = load_builtin_preset("horizontal_tools")

    assert spec.id == "horizontal_tools"
    assert spec.anchor == "viewport.bottom.center"
    assert spec.layout.orientation == "horizontal"
    assert spec.layout.columns == 5
    assert spec.layout.offset == (0, -24)
    assert spec.layout.opacity == 0.92
    assert [item.key_label for item in spec.items if item.key_label] == ["W", "E", "R", "S"]
    assert action_ids(spec) == (
        "maya.tool.move",
        "maya.tool.rotate",
        "maya.tool.scale",
        "maya.anim.set_key",
    )


def test_legacy_top_level_anchor_remains_supported() -> None:
    spec = parse_stack_spec(
        {
            "id": "legacy",
            "anchor": "viewport.left.center",
            "items": [{"type": "button", "label": "K", "action": "maya.anim.set_key"}],
        }
    )

    assert spec.anchor == "viewport.left.center"
    assert spec.layout.orientation == "vertical"
    assert spec.items[0].id == "legacy.0.maya_anim_set_key"


def test_parse_stack_spec_rejects_unknown_item_type() -> None:
    with pytest.raises(ValueError, match="Unsupported ActionRail item type"):
        parse_stack_spec(
            {
                "id": "broken",
                "anchor": "viewport.left.center",
                "items": [{"type": "slider", "label": "X", "action": "maya.tool.move"}],
            }
        )


def test_parse_stack_spec_rejects_bad_spacer_size() -> None:
    with pytest.raises(ValueError, match="spacer"):
        parse_stack_spec(
            {
                "id": "broken",
                "anchor": "viewport.left.center",
                "items": [{"type": "spacer", "size": -1}],
            }
        )


def test_parse_stack_spec_rejects_bad_layout_orientation() -> None:
    with pytest.raises(ValueError, match="orientation"):
        parse_stack_spec(
            {
                "id": "broken",
                "layout": {"anchor": "viewport.left.center", "orientation": "diagonal"},
                "items": [{"type": "button", "label": "K", "action": "maya.anim.set_key"}],
            }
        )


def test_parse_stack_spec_rejects_bad_predicate_type() -> None:
    with pytest.raises(ValueError, match="visible_when"):
        parse_stack_spec(
            {
                "id": "broken",
                "anchor": "viewport.left.center",
                "items": [
                    {
                        "type": "button",
                        "label": "K",
                        "action": "maya.anim.set_key",
                        "visible_when": {"bad": "shape"},
                    }
                ],
            }
        )
