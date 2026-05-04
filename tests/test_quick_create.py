from __future__ import annotations

import sys
from types import ModuleType

import pytest

import actionrail.runtime as runtime
from actionrail.actions import Action, ActionRegistry
from actionrail.authoring import DraftRail, DraftSlot, build_draft_spec, save_user_preset
from actionrail.quick_create import (
    ANCHOR_CHOICES,
    QuickCreateDraftInput,
    QuickCreateSlotInput,
    action_choices,
    build_quick_create_draft,
    clear_quick_create_previews,
    icon_choices,
    load_quick_create_preset,
    make_default_input,
    preview_quick_create_draft,
    save_quick_create_preset,
    template_by_id,
    template_choices,
)
from actionrail.quick_create_ui import (
    _slider_label,
    _valid_draft_status_text,
    _widget_value_from_slider,
)
from actionrail.spec import RailLayout, StackItem, StackSpec


@pytest.fixture(autouse=True)
def clear_runtime_overlays() -> None:
    runtime.hide_all()
    yield
    runtime.hide_all()


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


def test_quick_create_slider_value_preserves_unscaled_integers() -> None:
    assert _widget_value_from_slider(7, 1) == 7
    assert isinstance(_widget_value_from_slider(7, 1), int)
    assert _widget_value_from_slider(125, 100) == 1.25


def test_quick_create_valid_status_uses_runtime_schema() -> None:
    valid_draft = build_quick_create_draft(make_default_input())

    assert _valid_draft_status_text(valid_draft) == "Valid draft: quick-vertical-stack (4 slots)"

    invalid_draft = build_quick_create_draft(
        QuickCreateDraftInput(
            preset_id="bad",
            template_id="vertical_stack",
            slots=(QuickCreateSlotInput(id="slot", label=""),),
            anchor="viewport.left.center",
            orientation="vertical",
        )
    )
    with pytest.raises(ValueError, match="requires non-empty string 'label'"):
        _valid_draft_status_text(invalid_draft)


def test_quick_create_preview_uses_runtime_and_cleans_previous_preview(monkeypatch) -> None:
    events: list[tuple[str, str]] = []

    class FakeHost:
        def __init__(self, spec, *, panel=None, registry=None) -> None:
            self.spec = spec
            self.panel = panel
            self.registry = registry
            self.widget = None
            self._filter_targets = ()
            self._predicate_refresh_timer = None

        def show(self) -> None:
            events.append(("show", f"{self.spec.id}:{self.panel}"))

        def close(self) -> None:
            events.append(("close", self.spec.id))

    fake_overlay = ModuleType("actionrail.overlay")
    fake_overlay.ViewportOverlayHost = FakeHost
    fake_overlay._qt_widget_is_valid = lambda widget: True
    monkeypatch.setitem(sys.modules, "actionrail.overlay", fake_overlay)

    draft = build_quick_create_draft(make_default_input("horizontal_strip"))
    first = preview_quick_create_draft(draft, panel="modelPanel4")
    second = preview_quick_create_draft(draft, panel="modelPanel5")
    cleared = clear_quick_create_previews()

    assert isinstance(first, FakeHost)
    assert isinstance(second, FakeHost)
    assert cleared == 1
    assert runtime.active_overlay_ids() == ()
    assert events == [
        ("show", "quick-horizontal-strip:modelPanel4"),
        ("close", "quick-horizontal-strip"),
        ("show", "quick-horizontal-strip:modelPanel5"),
        ("close", "quick-horizontal-strip"),
    ]


def test_quick_create_preview_records_diagnostics_for_broken_draft() -> None:
    draft = DraftRail(
        id="broken_preview",
        slots=(DraftSlot(id="missing", label="Missing", action="missing.action"),),
    )

    with pytest.raises(ValueError, match="diagnostic errors"):
        preview_quick_create_draft(draft)

    import actionrail

    report = actionrail.last_report()
    assert report is not None
    assert report.errors[0].code == "missing_action"
    assert clear_quick_create_previews("broken_preview") == 0


def test_quick_create_preview_rejects_locked_builtin_ids() -> None:
    draft = DraftRail(
        id="transform_stack",
        slots=(DraftSlot(id="move", label="M", action="maya.tool.move"),),
    )

    with pytest.raises(ValueError, match="locked built-in"):
        preview_quick_create_draft(draft)


def test_save_quick_create_preset_can_save_without_showing(tmp_path) -> None:
    draft = build_quick_create_draft(make_default_input())

    result = save_quick_create_preset(draft, preset_dir=tmp_path, show=False)

    assert result.preset_id == "quick-vertical-stack"
    assert result.path == tmp_path / "quick-vertical-stack.json"
    assert result.host is None
    assert result.path.is_file()


def test_save_quick_create_preset_requires_explicit_overwrite(tmp_path) -> None:
    draft = build_quick_create_draft(make_default_input())

    save_quick_create_preset(draft, preset_dir=tmp_path, show=False)
    with pytest.raises(FileExistsError, match="overwrite=True"):
        save_quick_create_preset(draft, preset_dir=tmp_path, show=False)

    result = save_quick_create_preset(
        draft,
        preset_dir=tmp_path,
        overwrite=True,
        show=False,
    )

    assert result.path == tmp_path / "quick-vertical-stack.json"


def test_load_quick_create_preset_returns_editable_values(tmp_path) -> None:
    values = QuickCreateDraftInput(
        preset_id="artist_tools",
        template_id="horizontal_strip",
        slots=(
            QuickCreateSlotInput(
                id="move",
                label="Move",
                action="maya.tool.move",
                key_label="W",
                icon="maya.move",
            ),
        ),
        anchor="viewport.bottom.center",
        orientation="horizontal",
        columns=4,
        offset=(2, -8),
        opacity=0.75,
    )
    draft = build_quick_create_draft(values)
    save_quick_create_preset(draft, preset_dir=tmp_path, show=False)

    loaded = load_quick_create_preset("artist_tools", preset_dir=tmp_path)

    assert loaded.preset_id == "artist_tools"
    assert loaded.template_id == "horizontal_strip"
    assert loaded.anchor == "viewport.bottom.center"
    assert loaded.orientation == "horizontal"
    assert loaded.columns == 4
    assert loaded.offset == (2, -8)
    assert loaded.opacity == 0.75
    assert loaded.slots == values.slots


def test_load_quick_create_preset_infers_vertical_and_edge_templates(tmp_path) -> None:
    save_user_preset(
        StackSpec(
            id="loose_vertical",
            layout=RailLayout(anchor="viewport.left.center"),
            items=(StackItem(type="button", id="loose", label="Loose"),),
        ),
        preset_dir=tmp_path,
    )
    edge_values = QuickCreateDraftInput(
        preset_id="edge_user",
        template_id="edge_tab_rail",
        slots=(QuickCreateSlotInput(id="primary", label="Tool"),),
        anchor="viewport.left.center",
        orientation="vertical",
        opacity=0.92,
    )
    save_quick_create_preset(
        build_quick_create_draft(edge_values),
        preset_dir=tmp_path,
        show=False,
    )

    loose_loaded = load_quick_create_preset("loose_vertical", preset_dir=tmp_path)
    edge_loaded = load_quick_create_preset("edge_user", preset_dir=tmp_path)

    assert loose_loaded.template_id == "vertical_stack"
    assert loose_loaded.slots[0].id == "loose"
    assert edge_loaded.template_id == "edge_tab_rail"


def test_load_quick_create_preset_rejects_builtins() -> None:
    with pytest.raises(ValueError, match="saved user presets"):
        load_quick_create_preset("transform_stack")


def test_save_quick_create_preset_clears_preview_and_shows_saved_user_preset(
    tmp_path,
    monkeypatch,
) -> None:
    events: list[tuple[str, str]] = []

    class FakeHost:
        def __init__(self, spec, *, panel=None, registry=None) -> None:
            self.spec = spec
            self.panel = panel
            self.registry = registry
            self.widget = None
            self._filter_targets = ()
            self._predicate_refresh_timer = None

        def show(self) -> None:
            events.append(("show", f"{self.spec.id}:{self.panel}"))

        def close(self) -> None:
            events.append(("close", self.spec.id))

    fake_overlay = ModuleType("actionrail.overlay")
    fake_overlay.ViewportOverlayHost = FakeHost
    fake_overlay._qt_widget_is_valid = lambda widget: True
    monkeypatch.setitem(sys.modules, "actionrail.overlay", fake_overlay)

    draft = build_quick_create_draft(make_default_input("horizontal_strip"))
    preview_quick_create_draft(draft, panel="modelPanel4")
    result = save_quick_create_preset(draft, preset_dir=tmp_path, panel="modelPanel5")

    assert isinstance(result.host, FakeHost)
    assert result.path == tmp_path / "quick-horizontal-strip.json"
    assert runtime.active_overlay_ids() == ("quick-horizontal-strip",)
    assert events == [
        ("show", "quick-horizontal-strip:modelPanel4"),
        ("close", "quick-horizontal-strip"),
        ("show", "quick-horizontal-strip:modelPanel5"),
    ]


def test_save_quick_create_preset_preserves_unrelated_overlays(tmp_path, monkeypatch) -> None:
    events: list[tuple[str, str]] = []

    class FakeHost:
        def __init__(self, spec, *, panel=None, registry=None) -> None:
            self.spec = spec
            self.panel = panel
            self.registry = registry
            self.widget = None
            self._filter_targets = ()
            self._predicate_refresh_timer = None

        def show(self) -> None:
            events.append(("show", f"{self.spec.id}:{self.panel}"))

        def close(self) -> None:
            events.append(("close", self.spec.id))

    fake_overlay = ModuleType("actionrail.overlay")
    fake_overlay.ViewportOverlayHost = FakeHost
    fake_overlay._qt_widget_is_valid = lambda widget: True
    monkeypatch.setitem(sys.modules, "actionrail.overlay", fake_overlay)

    draft = build_quick_create_draft(make_default_input("horizontal_strip"))
    preview_quick_create_draft(draft, panel="modelPanel4")
    runtime.show_spec(
        StackSpec(
            id="reference",
            layout=RailLayout(anchor="viewport.left.center"),
            items=(StackItem(type="button", id="reference.slot", label="R"),),
        ),
        panel="modelPanel6",
    )
    save_quick_create_preset(draft, preset_dir=tmp_path, panel="modelPanel5")

    assert runtime.active_overlay_ids() == ("reference", "quick-horizontal-strip")
    assert events == [
        ("show", "quick-horizontal-strip:modelPanel4"),
        ("show", "reference:modelPanel6"),
        ("close", "quick-horizontal-strip"),
        ("show", "quick-horizontal-strip:modelPanel5"),
    ]
