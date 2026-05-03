from __future__ import annotations

import pytest

from actionrail.actions import create_default_registry, validate_action_ids
from actionrail.spec import (
    TRANSFORM_STACK_ID,
    StackItem,
    _default_item_id,
    action_ids,
    get_example_spec,
    load_builtin_preset,
    load_preset,
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
    assert spec.items[3].tone == "neutral"
    assert spec.items[5].tone == "teal"
    assert spec.items[0].tooltip == "Move tool"
    assert spec.items[1].action == ""
    assert spec.items[1].tooltip == "Unassigned slot"
    assert spec.items[5].key_label == "S"
    assert spec.items[0].active_when == "maya.tool == move"
    assert spec.items[1].active_when == ""
    assert spec.items[2].active_when == "maya.tool == rotate"
    assert spec.items[3].active_when == "maya.tool == scale"


def test_transform_stack_actions_are_registered() -> None:
    spec = get_example_spec()

    assert action_ids(spec) == (
        "maya.tool.move",
        "maya.tool.rotate",
        "maya.tool.scale",
        "maya.anim.set_key",
    )
    validate_action_ids(action_ids(spec), create_default_registry())


def test_unknown_example_id_raises() -> None:
    with pytest.raises(KeyError, match="missing"):
        get_example_spec("missing")


def test_parse_stack_spec_validates_basic_shape() -> None:
    with pytest.raises(ValueError, match="items"):
        parse_stack_spec({"id": "broken", "anchor": "viewport.left.center", "items": []})


def test_load_preset_reports_invalid_json(tmp_path) -> None:
    preset_path = tmp_path / "broken.json"
    preset_path.write_text("{not json", encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid ActionRail preset JSON"):
        load_preset(preset_path)


def test_parse_stack_spec_rejects_non_object_payload() -> None:
    with pytest.raises(ValueError, match="must be an object"):
        parse_stack_spec(["not", "an", "object"])


def test_horizontal_rail_loads_from_json() -> None:
    spec = load_builtin_preset("horizontal_tools")

    assert spec.id == "horizontal_tools"
    assert spec.anchor == "viewport.bottom.center"
    assert spec.layout.orientation == "horizontal"
    assert spec.layout.columns == 5
    assert spec.layout.offset == (0, -24)
    assert spec.layout.opacity == 0.92
    assert [item.key_label for item in spec.items if item.key_label] == ["W", "E", "R", "S"]
    assert [item.active_when for item in spec.items if item.type == "toolButton"] == [
        "maya.tool == move",
        "maya.tool == rotate",
        "maya.tool == scale",
    ]
    assert action_ids(spec) == (
        "maya.tool.move",
        "maya.tool.rotate",
        "maya.tool.scale",
        "maya.anim.set_key",
    )


def test_maya_tools_rail_uses_maya_resource_icon_ids() -> None:
    spec = load_builtin_preset("maya_tools")

    assert spec.id == "maya_tools"
    assert spec.layout.orientation == "horizontal"
    assert [item.icon for item in spec.items if item.icon] == [
        "maya.move",
        "maya.rotate",
        "maya.scale",
        "maya.set_key",
    ]


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


def test_parse_stack_spec_accepts_null_layout() -> None:
    spec = parse_stack_spec(
        {
            "id": "null_layout",
            "anchor": "viewport.left.center",
            "layout": None,
            "items": [{"type": "button", "label": "K"}],
        }
    )

    assert spec.layout.anchor == "viewport.left.center"


def test_parse_stack_spec_rejects_non_object_layout() -> None:
    with pytest.raises(ValueError, match="layout must be an object"):
        parse_stack_spec(
            {
                "id": "broken",
                "layout": "bad",
                "items": [{"type": "button", "label": "K"}],
            }
        )


def test_parse_stack_spec_rejects_missing_anchor() -> None:
    with pytest.raises(ValueError, match="requires non-empty string 'anchor'"):
        parse_stack_spec(
            {
                "id": "broken",
                "items": [{"type": "button", "label": "K"}],
            }
        )


def test_parse_stack_spec_supports_optional_icon_id() -> None:
    spec = parse_stack_spec(
        {
            "id": "with_icon",
            "anchor": "viewport.left.center",
            "items": [
                {
                    "type": "button",
                    "label": "K",
                    "action": "maya.anim.set_key",
                    "icon": "lucide.key",
                }
            ],
        }
    )

    assert spec.items[0].icon == "lucide.key"


def test_parse_stack_spec_allows_unassigned_placeholder_slot() -> None:
    spec = parse_stack_spec(
        {
            "id": "placeholder",
            "anchor": "viewport.left.center",
            "items": [{"type": "button", "label": "T", "tooltip": "Unassigned slot"}],
        }
    )

    assert spec.items[0].action == ""
    assert action_ids(spec) == ()


def test_stack_item_preserves_legacy_positional_tone_argument() -> None:
    item = StackItem("button", "id", "K", "maya.anim.set_key", "teal")

    assert item.tone == "teal"
    assert item.icon == ""


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


def test_parse_stack_spec_rejects_bool_spacer_size() -> None:
    with pytest.raises(ValueError, match="spacer"):
        parse_stack_spec(
            {
                "id": "broken",
                "anchor": "viewport.left.center",
                "items": [{"type": "spacer", "size": True}],
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


def test_parse_stack_spec_rejects_bool_layout_counts() -> None:
    with pytest.raises(ValueError, match="rows"):
        parse_stack_spec(
            {
                "id": "broken",
                "layout": {"anchor": "viewport.left.center", "rows": True},
                "items": [{"type": "button", "label": "K", "action": "maya.anim.set_key"}],
            }
        )


def test_parse_stack_spec_rejects_bad_layout_locked_flag() -> None:
    with pytest.raises(ValueError, match="locked"):
        parse_stack_spec(
            {
                "id": "broken",
                "layout": {"anchor": "viewport.left.center", "locked": "yes"},
                "items": [{"type": "button", "label": "K"}],
            }
        )


def test_parse_stack_spec_rejects_bad_layout_string_and_number_fields() -> None:
    with pytest.raises(ValueError, match="orientation"):
        parse_stack_spec(
            {
                "id": "broken",
                "layout": {"anchor": "viewport.left.center", "orientation": False},
                "items": [{"type": "button", "label": "K"}],
            }
        )

    with pytest.raises(ValueError, match="scale"):
        parse_stack_spec(
            {
                "id": "broken",
                "layout": {"anchor": "viewport.left.center", "scale": 0},
                "items": [{"type": "button", "label": "K"}],
            }
        )

    with pytest.raises(ValueError, match="offset"):
        parse_stack_spec(
            {
                "id": "broken",
                "layout": {"anchor": "viewport.left.center", "offset": [0, True]},
                "items": [{"type": "button", "label": "K"}],
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


def test_parse_stack_spec_accepts_boolean_predicates() -> None:
    spec = parse_stack_spec(
        {
            "id": "predicates",
            "anchor": "viewport.left.center",
            "items": [
                {
                    "type": "button",
                    "label": "K",
                    "visible_when": True,
                    "enabled_when": False,
                }
            ],
        }
    )

    assert spec.items[0].visible_when == "true"
    assert spec.items[0].enabled_when == "false"


def test_parse_stack_spec_rejects_non_object_item_and_bad_item_strings() -> None:
    with pytest.raises(ValueError, match="item 0 must be an object"):
        parse_stack_spec(
            {
                "id": "broken",
                "anchor": "viewport.left.center",
                "items": ["bad"],
            }
        )

    with pytest.raises(ValueError, match="label"):
        parse_stack_spec(
            {
                "id": "broken",
                "anchor": "viewport.left.center",
                "items": [{"type": "button"}],
            }
        )

    with pytest.raises(ValueError, match="id"):
        parse_stack_spec(
            {
                "id": "broken",
                "anchor": "viewport.left.center",
                "items": [{"type": "button", "id": 123, "label": "K"}],
            }
        )


def test_default_item_id_falls_back_to_generic_suffix() -> None:
    assert _default_item_id("preset", 2, {}) == "preset.2.item"


def test_parse_stack_spec_rejects_duplicate_item_ids() -> None:
    with pytest.raises(ValueError, match="duplicate id 'duplicate.slot'"):
        parse_stack_spec(
            {
                "id": "broken",
                "anchor": "viewport.left.center",
                "items": [
                    {
                        "type": "button",
                        "id": "duplicate.slot",
                        "label": "A",
                        "action": "maya.tool.move",
                    },
                    {
                        "type": "button",
                        "id": "duplicate.slot",
                        "label": "B",
                        "action": "maya.tool.rotate",
                    },
                ],
            }
        )
