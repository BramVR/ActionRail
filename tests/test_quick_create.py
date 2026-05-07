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
    edit_quick_create_layout,
    edit_quick_create_slots,
    icon_choices,
    load_quick_create_preset,
    make_default_input,
    preview_quick_create_draft,
    save_quick_create_preset,
    template_by_id,
    template_choices,
)
from actionrail.quick_create_ui import (
    _buttons_per_row_from_values,
    _generated_slot_input,
    _layout_rows_for_button_count,
    _set_combo_text,
    _slider_label,
    _slot_input_from_row,
    _valid_draft_status_text,
    _widget_value_from_slider,
)
from actionrail.spec import RailLayout, StackItem, StackSpec


class PublishCmds:
    def __init__(self) -> None:
        self.runtime_commands: dict[str, dict[str, object]] = {}
        self.name_commands: dict[str, dict[str, object]] = {}

    def runTimeCommand(self, name: str = "", **kwargs: object) -> object:  # noqa: N802
        if kwargs.get("userCommandArray"):
            return tuple(self.runtime_commands)
        if kwargs.get("exists"):
            return name in self.runtime_commands
        if kwargs.get("query") and kwargs.get("command"):
            return self.runtime_commands[name].get("command")
        if kwargs.get("delete"):
            self.runtime_commands.pop(name, None)
            return None
        payload = dict(kwargs)
        payload.pop("edit", None)
        self.runtime_commands[name] = payload
        return name

    def nameCommand(self, name: str, **kwargs: object) -> str:  # noqa: N802
        self.name_commands[name] = dict(kwargs)
        return name

    def hotkey(self, *args: object, **kwargs: object) -> object:
        if kwargs.get("query"):
            return None
        return None


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
    assert values.collapse_enabled is False
    assert values.collapse_edge == "bottom"


def test_template_choices_include_blank_and_viewport_starters() -> None:
    assert [template.id for template in template_choices()] == [
        "vertical_stack",
        "horizontal_strip",
        "edge_tab_rail",
        "blank_bar",
        "viewport_display_strip",
    ]


def test_blank_bar_template_starts_with_unassigned_slots() -> None:
    values = make_default_input("blank_bar")
    spec = build_draft_spec(build_quick_create_draft(values))

    assert values.preset_id == "quick-blank-bar"
    assert values.anchor == "viewport.bottom.center"
    assert values.orientation == "horizontal"
    assert values.columns == 6
    assert [slot.label for slot in values.slots] == ["1", "2", "3", "4", "5", "6"]
    assert all(not slot.action and not slot.icon for slot in values.slots)
    assert all(not item.action and not item.icon for item in spec.items)


def test_viewport_display_template_uses_grid_action_book_entry() -> None:
    values = make_default_input("viewport_display_strip")
    spec = build_draft_spec(build_quick_create_draft(values))

    assert values.preset_id == "quick-viewport-display-strip"
    assert values.anchor == "viewport.top.center"
    assert values.orientation == "horizontal"
    assert values.columns == 4
    assert values.slots[0].action == "maya.display.toggle_grid"
    assert values.slots[0].icon == "maya.grid"
    assert spec.items[0].id == "quick-viewport-display-strip.toggle_grid"
    assert spec.items[0].tooltip == "maya.display.toggle_grid"


def test_vertical_template_uses_anchor_edge_for_disabled_collapse_defaults() -> None:
    values = make_default_input("vertical_stack")

    assert values.collapse_enabled is False
    assert values.collapse_edge == "left"


def test_edge_tab_template_includes_phase_2_6_collapse_schema() -> None:
    values = make_default_input("edge_tab_rail")
    draft = build_quick_create_draft(values)

    assert draft.layout.anchor == "viewport.left.center"
    assert draft.layout.orientation == "vertical"
    assert draft.layout.opacity == 0.92
    assert draft.collapse.enabled is True
    assert draft.collapse.edge == "left"
    assert draft.collapse.handle_icon == "chevron-right"
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
    assert spec.items[0].active_when == ""


def test_build_quick_create_draft_infers_persistent_tool_active_state() -> None:
    values = QuickCreateDraftInput(
        preset_id="tool_states",
        template_id="vertical_stack",
        slots=(
            QuickCreateSlotInput(id="move", label="M", action="maya.tool.move"),
            QuickCreateSlotInput(id="rotate", label="R", action="maya.tool.rotate"),
            QuickCreateSlotInput(id="scale", label="S", action="maya.tool.scale"),
            QuickCreateSlotInput(id="key", label="K", action="maya.anim.set_key"),
            QuickCreateSlotInput(
                id="custom",
                label="C",
                action="maya.tool.move",
                active_when="false",
            ),
        ),
        anchor="viewport.left.center",
        orientation="vertical",
    )

    spec = build_draft_spec(build_quick_create_draft(values))

    assert [item.active_when for item in spec.items] == [
        "maya.tool == move",
        "maya.tool == rotate",
        "maya.tool == scale",
        "",
        "false",
    ]


def test_build_quick_create_draft_normalizes_layout_capacity() -> None:
    horizontal = make_default_input("horizontal_strip")
    horizontal = QuickCreateDraftInput(
        preset_id=horizontal.preset_id,
        template_id=horizontal.template_id,
        slots=horizontal.slots,
        anchor=horizontal.anchor,
        orientation=horizontal.orientation,
        rows=1,
        columns=1,
    )
    vertical = make_default_input("vertical_stack")
    vertical = QuickCreateDraftInput(
        preset_id=vertical.preset_id,
        template_id=vertical.template_id,
        slots=vertical.slots,
        anchor=vertical.anchor,
        orientation=vertical.orientation,
        rows=1,
        columns=1,
    )

    horizontal_spec = build_draft_spec(build_quick_create_draft(horizontal))
    vertical_spec = build_draft_spec(build_quick_create_draft(vertical))

    assert horizontal_spec.layout.columns == 4
    assert vertical_spec.layout.rows == 4


def test_build_quick_create_draft_preserves_authored_wrapped_capacity() -> None:
    values = QuickCreateDraftInput(
        preset_id="wrapped",
        template_id="horizontal_strip",
        slots=tuple(
            QuickCreateSlotInput(id=f"slot_{index}", label=str(index))
            for index in range(10)
        ),
        anchor="viewport.bottom.center",
        orientation="horizontal",
        rows=2,
        columns=5,
    )

    spec = build_draft_spec(build_quick_create_draft(values))

    assert spec.layout.rows == 2
    assert spec.layout.columns == 5
    assert len(spec.items) == 10


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


def test_quick_create_button_count_helpers_generate_blank_extra_slots() -> None:
    generated = _generated_slot_input(10)

    assert generated.id == "slot_10"
    assert generated.label == "10"
    assert generated.action == ""
    assert generated.icon == ""
    assert _layout_rows_for_button_count(10, 4) == 3
    assert _layout_rows_for_button_count(10, 5) == 2


def test_quick_create_buttons_per_row_uses_columns_as_row_capacity() -> None:
    horizontal = make_default_input("horizontal_strip")
    vertical = make_default_input("vertical_stack")

    assert _buttons_per_row_from_values(horizontal) == 4
    assert _buttons_per_row_from_values(vertical) == 1


def test_quick_create_combo_preserves_unknown_editable_text() -> None:
    class FakeCombo:
        def __init__(self) -> None:
            self.text = ""
            self.index = -1

        def findText(self, text: str) -> int:
            return -1 if text == "custom.unknown" else 0

        def setCurrentIndex(self, index: int) -> None:
            self.index = index

        def isEditable(self) -> bool:
            return True

        def setEditText(self, text: str) -> None:
            self.text = text

    combo = FakeCombo()

    _set_combo_text(combo, "custom.unknown")

    assert combo.text == "custom.unknown"
    assert combo.index == -1


def test_quick_create_row_preserves_hidden_slot_metadata() -> None:
    class FakeText:
        def __init__(self, text: str) -> None:
            self._text = text

        def text(self) -> str:
            return self._text

    class FakeCombo:
        def __init__(self, text: str) -> None:
            self._text = text

        def currentText(self) -> str:
            return self._text

    source = QuickCreateSlotInput(
        id="meta",
        label="Meta",
        action="old.action",
        key_label="K",
        icon="old.icon",
        type="toolButton",
        tone="teal",
        tooltip="Custom tip",
        visible_when="selection.count > 0",
        enabled_when='plugin.exists("foo")',
        active_when="maya.tool == move",
        size=7,
    )

    slot = _slot_input_from_row(
        {
            "id": FakeText("meta"),
            "label": FakeText("Edited"),
            "action": FakeCombo("custom.action"),
            "key_label": FakeText("E"),
            "icon": FakeCombo("custom.icon"),
            "source": source,
        }
    )

    assert slot.label == "Edited"
    assert slot.action == "custom.action"
    assert slot.icon == "custom.icon"
    assert slot.tone == "teal"
    assert slot.tooltip == "Custom tip"
    assert slot.visible_when == "selection.count > 0"
    assert slot.enabled_when == 'plugin.exists("foo")'
    assert slot.active_when == "maya.tool == move"
    assert slot.type == "toolButton"


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


def test_quick_create_valid_status_surfaces_publish_diagnostics() -> None:
    warning_draft = DraftRail(
        id="warning_draft",
        slots=(
            DraftSlot(
                id="move",
                label="Move",
                action="maya.tool.move",
                icon="missing.icon",
            ),
        ),
    )

    assert (
        _valid_draft_status_text(warning_draft)
        == "Valid draft: warning_draft (1 slots); warnings: 1: missing_icon [warning_draft.move]"
    )

    error_draft = DraftRail(
        id="error_draft",
        slots=(DraftSlot(id="missing", label="Missing", action="missing.action"),),
    )
    with pytest.raises(ValueError, match=r"Draft has errors: 1: missing_action"):
        _valid_draft_status_text(error_draft)


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


def test_quick_create_edit_layout_previews_and_selects_edit_mode(monkeypatch) -> None:
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

    import actionrail.edit_mode as edit_mode

    monkeypatch.setattr(
        edit_mode,
        "enter_edit_mode",
        lambda *, panel=None, settings=None: events.append(("enter_edit", str(panel))),
    )
    monkeypatch.setattr(
        edit_mode,
        "select_edit_mode_rail",
        lambda preset_id: type(
            "State",
            (),
            {"enabled": True, "selected_preset_id": preset_id},
        )(),
    )

    draft = build_quick_create_draft(make_default_input("horizontal_strip"))
    state = edit_quick_create_layout(draft, panel="modelPanel4")

    assert state.selected_preset_id == "quick-horizontal-strip"
    assert runtime.active_overlay_ids() == ("quick-horizontal-strip",)
    assert events == [
        ("show", "quick-horizontal-strip:modelPanel4"),
        ("enter_edit", "modelPanel4"),
    ]


def test_quick_create_edit_slots_previews_exits_edit_mode_and_unlocks(monkeypatch) -> None:
    events: list[tuple[str, str]] = []

    class FakeHost:
        def __init__(self, spec, *, panel=None, registry=None) -> None:
            self.spec = spec
            self.panel = panel
            self.registry = registry
            self.widget = None
            self._filter_targets = ()
            self._predicate_refresh_timer = None
            self.unlocked = False

        def show(self) -> None:
            events.append(("show", f"{self.spec.id}:{self.panel}"))

        def close(self) -> None:
            events.append(("close", self.spec.id))

        def set_slot_edit_unlocked(self, unlocked: bool) -> bool:
            self.unlocked = unlocked
            events.append(("unlock", f"{self.spec.id}:{unlocked}"))
            return True

    fake_overlay = ModuleType("actionrail.overlay")
    fake_overlay.ViewportOverlayHost = FakeHost
    fake_overlay._qt_widget_is_valid = lambda widget: True
    monkeypatch.setitem(sys.modules, "actionrail.overlay", fake_overlay)

    import actionrail.edit_mode as edit_mode

    monkeypatch.setattr(
        edit_mode,
        "exit_edit_mode",
        lambda: events.append(("exit_edit", "")),
    )

    draft = build_quick_create_draft(make_default_input("horizontal_strip"))
    host = edit_quick_create_slots(draft, panel="modelPanel4")

    assert host.spec.id == "quick-horizontal-strip"
    assert host.unlocked is True
    assert runtime.active_overlay_ids() == ("quick-horizontal-strip",)
    assert events == [
        ("show", "quick-horizontal-strip:modelPanel4"),
        ("exit_edit", ""),
        ("unlock", "quick-horizontal-strip:True"),
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
    assert result.diagnostics is not None
    assert result.path.is_file()


def test_save_quick_create_preset_rejects_diagnostic_errors(tmp_path) -> None:
    draft = DraftRail(
        id="broken_save",
        slots=(DraftSlot(id="missing", label="Missing", action="missing.action"),),
    )

    with pytest.raises(ValueError, match=r"missing_action \[broken_save.missing\]"):
        save_quick_create_preset(draft, preset_dir=tmp_path, show=False)

    import actionrail

    report = actionrail.last_report()
    assert report is not None
    assert [issue.code for issue in report.errors] == ["missing_action"]
    assert not (tmp_path / "broken_save.json").exists()


def test_save_quick_create_preset_can_publish_slot_runtime_commands(tmp_path) -> None:
    cmds = PublishCmds()
    draft = build_quick_create_draft(make_default_input())

    result = save_quick_create_preset(
        draft,
        preset_dir=tmp_path,
        show=False,
        publish=True,
        cmds_module=cmds,
    )

    assert [command.runtime_command for command in result.published] == [
        "ActionRail_slot_quick_vertical_stack_move",
        "ActionRail_slot_quick_vertical_stack_rotate",
        "ActionRail_slot_quick_vertical_stack_scale",
        "ActionRail_slot_quick_vertical_stack_set_key",
    ]
    assert "ActionRail_slot_quick_vertical_stack_move" in cmds.runtime_commands
    command_text = str(
        cmds.runtime_commands["ActionRail_slot_quick_vertical_stack_move"]["command"]
    )
    assert f"user_preset_dir={str(tmp_path)!r}" in command_text


def test_save_quick_create_preset_reports_removed_stale_slot_commands(tmp_path) -> None:
    cmds = PublishCmds()
    cmds.runtime_commands["ActionRail_slot_quick_vertical_stack_old"] = {
        "command": (
            "import actionrail; "
            "actionrail.run_slot('quick-vertical-stack', 'quick-vertical-stack.old')"
        )
    }
    draft = build_quick_create_draft(make_default_input())

    result = save_quick_create_preset(
        draft,
        preset_dir=tmp_path,
        show=False,
        publish=True,
        cmds_module=cmds,
    )

    assert [command.runtime_command for command in result.unpublished] == [
        "ActionRail_slot_quick_vertical_stack_old"
    ]
    assert "ActionRail_slot_quick_vertical_stack_old" not in cmds.runtime_commands


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
    assert loaded.slots == (
        QuickCreateSlotInput(
            id="move",
            label="Move",
            action="maya.tool.move",
            key_label="W",
            icon="maya.move",
            tooltip="maya.tool.move",
            active_when="maya.tool == move",
        ),
    )


def test_load_quick_create_preset_preserves_rich_items(tmp_path) -> None:
    save_user_preset(
        StackSpec(
            id="rich_tools",
            layout=RailLayout(anchor="viewport.left.center", rows=3),
            items=(
                StackItem(
                    type="button",
                    id="rich_tools.meta",
                    label="Meta",
                    action="custom.missing",
                    tone="teal",
                    tooltip="Custom tip",
                    visible_when="selection.count > 0",
                    enabled_when='plugin.exists("foo")',
                    active_when="maya.tool == move",
                    icon="custom.unknown",
                ),
                StackItem(type="spacer", id="rich_tools.gap", size=8),
                StackItem(
                    type="button",
                    id="rich_tools.rotate",
                    label="Rotate",
                    action="maya.tool.rotate",
                ),
            ),
        ),
        preset_dir=tmp_path,
    )

    loaded = load_quick_create_preset("rich_tools", preset_dir=tmp_path)
    rebuilt = build_draft_spec(build_quick_create_draft(loaded))

    assert [item.type for item in rebuilt.items] == ["button", "spacer", "button"]
    assert rebuilt.items[0].tone == "teal"
    assert rebuilt.items[0].tooltip == "Custom tip"
    assert rebuilt.items[0].visible_when == "selection.count > 0"
    assert rebuilt.items[0].enabled_when == 'plugin.exists("foo")'
    assert rebuilt.items[0].active_when == "maya.tool == move"
    assert rebuilt.items[0].icon == "custom.unknown"
    assert rebuilt.items[1].id == "rich_tools.gap"
    assert rebuilt.items[1].size == 8


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
        collapse_enabled=True,
        collapse_edge="left",
        collapse_handle_icon="chevron-right",
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
    assert edge_loaded.collapse_enabled is True
    assert edge_loaded.collapse_handle_icon == "chevron-right"


def test_load_quick_create_preset_infers_blank_and_viewport_templates(tmp_path) -> None:
    save_quick_create_preset(
        build_quick_create_draft(make_default_input("blank_bar")),
        preset_dir=tmp_path,
        show=False,
    )
    save_quick_create_preset(
        build_quick_create_draft(make_default_input("viewport_display_strip")),
        preset_dir=tmp_path,
        show=False,
    )

    blank_loaded = load_quick_create_preset("quick-blank-bar", preset_dir=tmp_path)
    viewport_loaded = load_quick_create_preset(
        "quick-viewport-display-strip",
        preset_dir=tmp_path,
    )

    assert blank_loaded.template_id == "blank_bar"
    assert all(not slot.action for slot in blank_loaded.slots)
    assert viewport_loaded.template_id == "viewport_display_strip"
    assert viewport_loaded.slots[0].action == "maya.display.toggle_grid"


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
