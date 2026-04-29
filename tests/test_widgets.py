from __future__ import annotations

import actionrail.widgets as widgets
from actionrail.actions import create_default_registry
from actionrail.predicates import PredicateContext
from actionrail.spec import RailLayout, StackItem, StackSpec
from actionrail.state import MayaStateSnapshot
from actionrail.widgets import (
    _button_text,
    _is_item_active,
    _is_item_visible,
    _slot_render_state,
    refresh_predicate_state,
)


class FakeStyle:
    def __init__(self) -> None:
        self.unpolished = 0
        self.polished = 0

    def unpolish(self, _button: object) -> None:
        self.unpolished += 1

    def polish(self, _button: object) -> None:
        self.polished += 1


class FakeButton:
    def __init__(
        self,
        slot_id: str,
        *,
        label: str = "S",
        key_label: str = "",
        tone: str = "neutral",
        active: str = "false",
        enabled: bool = True,
        tooltip: str = "",
    ) -> None:
        self.properties = {
            "actionRailSlotId": slot_id,
            "actionRailLabel": label,
            "actionRailKeyLabel": key_label,
            "actionRailIcon": "",
            "actionRailIconPath": "",
            "actionRailTone": tone,
            "actionRailActive": active,
            "actionRailLocked": "false",
            "actionRailDiagnosticCode": "",
            "actionRailDiagnosticSeverity": "",
            "actionRailDiagnosticBadge": "",
        }
        self.enabled = enabled
        self.style_object = FakeStyle()
        self.updated = 0
        self.text_value = _button_text(label, key_label)
        self.tooltip_value = tooltip

    def property(self, name: str) -> object:
        return self.properties.get(name)

    def setProperty(self, name: str, value: object) -> None:  # noqa: N802
        self.properties[name] = value

    def isEnabled(self) -> bool:  # noqa: N802
        return self.enabled

    def setEnabled(self, enabled: bool) -> None:  # noqa: N802
        self.enabled = enabled

    def text(self) -> str:
        return self.text_value

    def setText(self, text: str) -> None:  # noqa: N802
        self.text_value = text

    def toolTip(self) -> str:  # noqa: N802
        return self.tooltip_value

    def setToolTip(self, tooltip: str) -> None:  # noqa: N802
        self.tooltip_value = tooltip

    def style(self) -> FakeStyle:
        return self.style_object

    def update(self) -> None:
        self.updated += 1


class FakeRoot:
    def __init__(self, buttons: list[FakeButton]) -> None:
        self.buttons = buttons

    def findChildren(self, _widget_type: object) -> list[FakeButton]:  # noqa: N802
        return self.buttons


class FakeQt:
    class QtWidgets:
        QPushButton = FakeButton


class AvailabilityCmds:
    def commandInfo(self, command_name: str, *, exists: bool = False) -> bool:  # noqa: N802
        return command_name == "availableCommand" and exists

    def pluginInfo(self, plugin_name: str, *, query: bool = False, loaded: bool = False) -> bool:  # noqa: N802
        return plugin_name == "loadedPlugin" and query and loaded


def test_literal_false_visibility_skips_item_before_frame_building() -> None:
    assert _is_item_visible(StackItem(type="button", visible_when="")) is True
    assert _is_item_visible(StackItem(type="button", visible_when="true")) is True
    assert _is_item_visible(StackItem(type="button", visible_when="false")) is False


def test_state_visibility_skips_item_before_frame_building() -> None:
    item = StackItem(type="button", visible_when="selection.count > 0")

    assert _is_item_visible(item) is False
    assert (
        _is_item_visible(
            item,
            PredicateContext(state=MayaStateSnapshot(current_tool="", selection_count=1)),
        )
        is True
    )


def test_missing_visible_dependency_keeps_item_visible_for_badge() -> None:
    item = StackItem(
        type="button",
        visible_when="plugin.exists('missingPlugin')",
    )

    assert (
        _is_item_visible(
            item,
            PredicateContext(cmds_module=AvailabilityCmds()),
        )
        is True
    )


def test_missing_visible_dependency_preserves_other_visibility_clauses() -> None:
    item = StackItem(
        type="button",
        visible_when="selection.count > 0 and plugin.exists('missingPlugin')",
    )

    assert (
        _is_item_visible(
            item,
            PredicateContext(
                state=MayaStateSnapshot(current_tool="", selection_count=0),
                cmds_module=AvailabilityCmds(),
            ),
        )
        is False
    )
    assert (
        _is_item_visible(
            item,
            PredicateContext(
                state=MayaStateSnapshot(current_tool="", selection_count=1),
                cmds_module=AvailabilityCmds(),
            ),
        )
        is True
    )


def test_negated_missing_visible_dependency_does_not_get_forced_badge_state() -> None:
    item = StackItem(
        type="button",
        visible_when="not plugin.exists('missingPlugin')",
    )

    assert (
        _is_item_visible(
            item,
            PredicateContext(cmds_module=AvailabilityCmds()),
        )
        is True
    )


def test_empty_active_predicate_is_inactive_by_default() -> None:
    assert _is_item_active(StackItem(type="button", active_when="")) is False
    assert _is_item_active(StackItem(type="button", active_when="true")) is True


def test_button_text_adds_key_label_on_second_line() -> None:
    assert _button_text("K", "") == "K"
    assert _button_text("K", "Ctrl+S") == "K\nCtrl+S"


def test_slot_render_state_uses_action_tooltip_fallback() -> None:
    registry = create_default_registry(object())
    item = StackItem(
        type="button",
        id="tooltip_test.set_key",
        label="K",
        action="maya.anim.set_key",
    )

    state = _slot_render_state(item, registry)

    assert state.tooltip == "Set keyframe"


def test_slot_render_state_marks_missing_action_as_error() -> None:
    registry = create_default_registry(object())
    item = StackItem(
        type="button",
        id="broken.missing",
        label="X",
        action="maya.missing.action",
    )

    state = _slot_render_state(item, registry)

    assert state.enabled is False
    assert state.diagnostic_code == "missing_action"
    assert state.diagnostic_severity == "error"
    assert state.text == "X\n!"
    assert "maya.missing.action" in state.tooltip


def test_slot_render_state_locks_unassigned_slot_without_error() -> None:
    registry = create_default_registry(object())
    item = StackItem(
        type="button",
        id="placeholder.empty",
        label="T",
        tooltip="Unassigned slot",
    )

    state = _slot_render_state(item, registry)

    assert state.locked is True
    assert state.enabled is False
    assert state.active is False
    assert state.diagnostic_code == ""
    assert state.diagnostic_severity == ""
    assert state.text == "T"
    assert state.tooltip == "Unassigned slot"


def test_slot_render_state_marks_missing_icon_as_warning() -> None:
    registry = create_default_registry(object())
    item = StackItem(
        type="button",
        id="broken.icon",
        label="I",
        action="maya.anim.set_key",
        icon="missing.icon",
    )

    state = _slot_render_state(item, registry)

    assert state.enabled is True
    assert state.icon == "missing.icon"
    assert state.icon_path == ""
    assert state.diagnostic_code == "missing_icon"
    assert state.diagnostic_severity == "warning"
    assert state.text == "I\n?"


def test_slot_render_state_marks_missing_command_predicate_as_warning() -> None:
    registry = create_default_registry(AvailabilityCmds())
    item = StackItem(
        type="button",
        id="broken.command",
        label="C",
        action="maya.anim.set_key",
        enabled_when="command.exists('missingCommand')",
    )

    state = _slot_render_state(
        item,
        registry,
        PredicateContext(cmds_module=AvailabilityCmds()),
    )

    assert state.enabled is False
    assert state.diagnostic_code == "missing_command"
    assert state.diagnostic_severity == "warning"
    assert state.text == "C\n?"
    assert "missingCommand" in state.tooltip


def test_slot_render_state_marks_missing_visible_plugin_as_warning() -> None:
    registry = create_default_registry(AvailabilityCmds())
    item = StackItem(
        type="button",
        id="broken.plugin",
        label="P",
        action="maya.anim.set_key",
        visible_when="plugin.exists('missingPlugin')",
    )

    state = _slot_render_state(
        item,
        registry,
        PredicateContext(cmds_module=AvailabilityCmds()),
    )

    assert state.enabled is False
    assert state.diagnostic_code == "missing_plugin"
    assert state.diagnostic_severity == "warning"
    assert state.text == "P\n?"
    assert "missingPlugin" in state.tooltip


def test_slot_render_state_ignores_negated_missing_availability_predicates() -> None:
    registry = create_default_registry(AvailabilityCmds())
    item = StackItem(
        type="button",
        id="fallback.command",
        label="F",
        action="maya.anim.set_key",
        enabled_when="not command.exists('missingCommand')",
    )

    state = _slot_render_state(
        item,
        registry,
        PredicateContext(cmds_module=AvailabilityCmds()),
    )

    assert state.enabled is True
    assert state.diagnostic_code == ""
    assert state.diagnostic_severity == ""
    assert state.text == "F"


def test_refresh_predicate_state_updates_enabled_and_active(
    monkeypatch,
) -> None:
    monkeypatch.setattr(widgets, "load", lambda: FakeQt)
    spec = StackSpec(
        id="refresh_test",
        layout=RailLayout(anchor="viewport.left.center"),
        items=(
            StackItem(
                type="button",
                id="refresh_test.scale",
                label="S",
                action="maya.tool.scale",
                enabled_when="selection.count > 0",
                active_when="maya.tool == scale",
            ),
        ),
    )
    button = FakeButton("refresh_test.scale", active="false", enabled=False)
    root = FakeRoot([button])

    result = refresh_predicate_state(
        root,
        spec,
        registry=object(),
        state_snapshot=MayaStateSnapshot(current_tool="scaleSuperContext", selection_count=1),
    )

    assert result.needs_rebuild is False
    assert result.refreshed == 2
    assert button.isEnabled() is True
    assert button.property("actionRailActive") == "true"
    assert button.style_object.polished == 1
    assert button.updated == 1


def test_refresh_predicate_state_preserves_runtime_key_label(
    monkeypatch,
) -> None:
    monkeypatch.setattr(widgets, "load", lambda: FakeQt)
    spec = StackSpec(
        id="refresh_test",
        layout=RailLayout(anchor="viewport.left.center"),
        items=(
            StackItem(
                type="button",
                id="refresh_test.set_key",
                label="K",
                action="maya.anim.set_key",
                key_label="S",
            ),
        ),
    )
    button = FakeButton("refresh_test.set_key", label="K", key_label="F12")
    root = FakeRoot([button])

    result = refresh_predicate_state(root, spec, registry=object())

    assert result.needs_rebuild is False
    assert result.refreshed == 0
    assert button.property("actionRailKeyLabel") == "F12"
    assert button.text() == "K\nF12"


def test_refresh_predicate_state_updates_diagnostic_badge(
    monkeypatch,
) -> None:
    monkeypatch.setattr(widgets, "load", lambda: FakeQt)
    spec = StackSpec(
        id="refresh_test",
        layout=RailLayout(anchor="viewport.left.center"),
        items=(
            StackItem(
                type="button",
                id="refresh_test.missing",
                label="X",
                action="maya.missing.action",
            ),
        ),
    )
    button = FakeButton("refresh_test.missing")
    root = FakeRoot([button])

    result = refresh_predicate_state(root, spec, registry=create_default_registry(object()))

    assert result.needs_rebuild is False
    assert button.isEnabled() is False
    assert button.property("actionRailDiagnosticCode") == "missing_action"
    assert button.property("actionRailDiagnosticSeverity") == "error"
    assert button.text() == "X\n!"
    assert button.style_object.polished == 1


def test_refresh_predicate_state_requests_rebuild_when_visibility_changes(
    monkeypatch,
) -> None:
    monkeypatch.setattr(widgets, "load", lambda: FakeQt)
    spec = StackSpec(
        id="refresh_test",
        layout=RailLayout(anchor="viewport.left.center"),
        items=(
            StackItem(
                type="button",
                id="refresh_test.visible_after_select",
                label="V",
                action="maya.anim.set_key",
                visible_when="selection.count > 0",
            ),
        ),
    )
    root = FakeRoot([])

    result = refresh_predicate_state(
        root,
        spec,
        registry=object(),
        state_snapshot=MayaStateSnapshot(current_tool="", selection_count=1),
    )

    assert result.needs_rebuild is True
    assert result.visible_slot_ids == ("refresh_test.visible_after_select",)
    assert result.rendered_slot_ids == ()
