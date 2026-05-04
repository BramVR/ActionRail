from __future__ import annotations

import pytest

from actionrail.actions import Action, ActionRegistry
from actionrail.authoring import build_draft_spec
from actionrail.quick_create import (
    ANCHOR_CHOICES,
    QuickCreateDraftInput,
    QuickCreateSlotInput,
    action_choices,
    build_quick_create_draft,
    icon_choices,
    make_default_input,
    template_by_id,
    template_choices,
)
from actionrail.quick_create_ui import _slider_label


def test_template_defaults_build_valid_draft_specs() -> None:
    for template in template_choices():
        values = make_default_input(template.id)
        draft = build_quick_create_draft(values)
        spec = build_draft_spec(draft)

        assert draft.id == values.preset_id
        assert draft.layout == template.layout
        assert len(draft.slots) == len(template.slots)
        assert spec.id == draft.id
        assert spec.items[0].id.startswith(f"{draft.id}.")


def test_horizontal_template_uses_bottom_strip_layout() -> None:
    values = make_default_input("horizontal_strip")

    assert values.preset_id == "quick-horizontal-strip"
    assert values.anchor == "viewport.bottom.center"
    assert values.orientation == "horizontal"
    assert values.columns == 4
    assert values.offset == (0, -36)


def test_edge_tab_template_is_valid_without_phase_2_6_collapse_schema() -> None:
    values = make_default_input("edge_tab_rail")
    draft = build_quick_create_draft(values)

    assert draft.layout.anchor == "viewport.left.center"
    assert draft.layout.orientation == "vertical"
    assert draft.layout.opacity == 0.92
    assert draft.slots[0].id == "primary"


def test_build_quick_create_draft_uses_edited_values() -> None:
    values = QuickCreateDraftInput(
        preset_id="anim.blocking",
        template_id="vertical_stack",
        slots=(
            QuickCreateSlotInput(
                id="set_key",
                label="K",
                action="maya.anim.set_key",
                key_label="S",
                icon="maya.set_key",
            ),
        ),
        anchor=ANCHOR_CHOICES[-1],
        orientation="horizontal",
        rows=2,
        columns=3,
        offset=(10, -12),
        scale=1.25,
        opacity=0.8,
        locked=True,
    )

    draft = build_quick_create_draft(values)
    spec = build_draft_spec(draft)

    assert draft.layout.anchor == "viewport.center"
    assert draft.layout.orientation == "horizontal"
    assert draft.layout.rows == 2
    assert draft.layout.columns == 3
    assert draft.layout.offset == (10, -12)
    assert draft.layout.scale == 1.25
    assert draft.layout.opacity == 0.8
    assert draft.layout.locked is True
    assert spec.items[0].id == "anim.blocking.set_key"
    assert spec.items[0].tooltip == "maya.anim.set_key"
    assert spec.items[0].key_label == "S"
    assert spec.items[0].icon == "maya.set_key"


def test_build_quick_create_draft_uses_label_tooltip_without_action() -> None:
    values = QuickCreateDraftInput(
        preset_id="notes",
        template_id="vertical_stack",
        slots=(QuickCreateSlotInput(id="empty", label="Empty"),),
        anchor="viewport.left.center",
        orientation="vertical",
    )

    draft = build_quick_create_draft(values)

    assert draft.slots[0].tooltip == "Empty"


def test_empty_slots_and_unknown_templates_raise() -> None:
    with pytest.raises(KeyError, match="Unknown ActionRail Quick Create template"):
        template_by_id("missing")

    with pytest.raises(ValueError, match="requires at least one slot"):
        build_quick_create_draft(
            QuickCreateDraftInput(
                preset_id="empty",
                template_id="vertical_stack",
                slots=(),
                anchor="viewport.left.center",
                orientation="vertical",
            )
        )


def test_action_choices_use_registry_labels_and_tooltips() -> None:
    registry = ActionRegistry()
    registry.register(Action("custom.z", "Zeta", lambda: None, "Last"))
    registry.register(Action("custom.a", "Alpha", lambda: None, "First"))

    assert action_choices(registry) == (
        ("custom.a", "Alpha", "First"),
        ("custom.z", "Zeta", "Last"),
    )


def test_icon_choices_expose_picker_descriptors() -> None:
    icons = icon_choices(provider="maya")

    assert any(icon.id == "maya.move" for icon in icons)
    assert all(icon.provider == "maya" for icon in icons)


def test_quick_create_slider_label_formats_scaled_values() -> None:
    assert _slider_label(12, 1) == "12"
    assert _slider_label(125, 100) == "1.25"
