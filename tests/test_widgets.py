from __future__ import annotations

import actionrail.widgets as widgets
from actionrail.actions import create_default_registry
from actionrail.predicates import PredicateContext
from actionrail.qt import QtBinding
from actionrail.spec import RailLayout, StackItem, StackSpec
from actionrail.state import MayaStateSnapshot
from actionrail.widgets import (
    SlotRenderState,
    _apply_button_icon,
    _apply_slot_render_state,
    _button_text,
    _diagnostic_tooltip,
    _icon_diagnostic,
    _is_item_active,
    _is_item_visible,
    _scaled_theme,
    _slot_render_state,
    refresh_predicate_state,
    set_slot_key_label,
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
            "actionRailIconName": "",
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


class FakeSignal:
    def __init__(self) -> None:
        self.callbacks = []

    def connect(self, callback) -> None:
        self.callbacks.append(callback)

    def emit(self) -> None:
        for callback in list(self.callbacks):
            callback(False)


class FakeWidgetBase:
    def __init__(self) -> None:
        self.children = []
        self.properties = {}

    def setObjectName(self, name: str) -> None:  # noqa: N802
        self.object_name = name

    def setAttribute(self, *args) -> None:  # noqa: N802
        self.attribute = args

    def setFocusPolicy(self, policy) -> None:  # noqa: N802
        self.focus_policy = policy

    def setStyleSheet(self, style: str) -> None:  # noqa: N802
        self.style_sheet = style

    def setWindowOpacity(self, opacity: float) -> None:  # noqa: N802
        self.opacity = opacity

    def adjustSize(self) -> None:  # noqa: N802
        self.adjusted = True

    def sizeHint(self):  # noqa: N802
        return (100, 200)

    def setFixedSize(self, *args) -> None:  # noqa: N802
        self.fixed_size = args

    def findChildren(self, widget_type):  # noqa: N802
        found = []

        def walk(widget) -> None:
            if isinstance(widget, widget_type):
                found.append(widget)
            for child in getattr(widget, "children", []):
                walk(child)

        walk(self)
        return found

    def setProperty(self, name: str, value) -> None:  # noqa: N802
        self.properties[name] = value

    def mousePressEvent(self, event) -> None:  # noqa: N802
        event.ignore()

    mouseMoveEvent = mousePressEvent
    mouseReleaseEvent = mousePressEvent
    wheelEvent = mousePressEvent


class FakeFrame(FakeWidgetBase):
    pass


class BuildButton(FakeButton):
    def __init__(self, text: str) -> None:
        super().__init__("", label=text)
        self.clicked = FakeSignal()
        self.icons = []

    def setFixedSize(self, *args) -> None:  # noqa: N802
        self.fixed_size = args

    def setFocusPolicy(self, policy) -> None:  # noqa: N802
        self.focus_policy = policy

    def setCursor(self, cursor) -> None:  # noqa: N802
        self.cursor = cursor

    def setIcon(self, icon) -> None:  # noqa: N802
        self.icons.append(icon)

    def setIconSize(self, size) -> None:  # noqa: N802
        self.icon_size = size


class FakeLayout:
    def __init__(self, parent) -> None:
        self.parent = parent
        self.items = []

    def setContentsMargins(self, *margins) -> None:  # noqa: N802
        self.margins = margins

    def setSpacing(self, spacing: int) -> None:  # noqa: N802
        self.spacing = spacing

    def addWidget(self, widget, *args) -> None:  # noqa: N802
        self.items.append(("widget", widget, args))
        self.parent.children.append(widget)

    def addSpacing(self, spacing: int) -> None:  # noqa: N802
        self.items.append(("spacing", spacing))


class BuildQtCore:
    class Qt:
        WA_TranslucentBackground = 1
        WA_NoSystemBackground = 2
        NoFocus = 3
        AlignLeft = 4
        PointingHandCursor = 5
        ArrowCursor = 6

    class QSize:
        def __init__(self, width: int, height: int) -> None:
            self.width = width
            self.height = height


class BuildQtGui:
    class QIcon:
        def __init__(self, path: str = "") -> None:
            self.path = path


class BuildQtWidgets:
    QWidget = FakeWidgetBase
    QFrame = FakeFrame
    QPushButton = BuildButton
    QVBoxLayout = FakeLayout
    QHBoxLayout = FakeLayout


def build_qt_binding() -> QtBinding:
    return QtBinding("Fake", BuildQtCore, BuildQtGui, BuildQtWidgets, lambda pointer, base: base)


class AvailabilityCmds:
    def commandInfo(self, command_name: str, *, exists: bool = False) -> bool:  # noqa: N802
        return command_name == "availableCommand" and exists

    def pluginInfo(self, plugin_name: str, *, query: bool = False, loaded: bool = False) -> bool:  # noqa: N802
        return plugin_name == "loadedPlugin" and query and loaded


class BuildCmds(AvailabilityCmds):
    def __init__(self) -> None:
        self.calls = []

    def setToolTo(self, context: str) -> None:  # noqa: N802
        self.calls.append(("setToolTo", context))

    def setKeyframe(self) -> None:  # noqa: N802
        self.calls.append(("setKeyframe", ""))


class MissingMayaIconResourceCmds(BuildCmds):
    def resourceManager(self, *, nameFilter: str) -> list[str]:  # noqa: N802
        _ = nameFilter
        return []


def test_literal_false_visibility_skips_item_before_frame_building() -> None:
    assert _is_item_visible(StackItem(type="button", visible_when="")) is True
    assert _is_item_visible(StackItem(type="button", visible_when="true")) is True
    assert _is_item_visible(StackItem(type="button", visible_when="false")) is False


def test_action_rail_root_ignores_mouse_and_wheel_events(monkeypatch) -> None:
    monkeypatch.setattr(widgets, "load", build_qt_binding)
    root = widgets.ActionRailRoot.create()
    ignored = []

    class Event:
        def ignore(self) -> None:
            ignored.append(True)

    event = Event()
    root.mousePressEvent(event)
    root.mouseMoveEvent(event)
    root.mouseReleaseEvent(event)
    root.wheelEvent(event)

    assert ignored == [True, True, True, True]


def test_build_transform_stack_constructs_scaled_horizontal_widget(monkeypatch) -> None:
    monkeypatch.setattr(widgets, "load", build_qt_binding)
    cmds = BuildCmds()
    registry = create_default_registry(cmds)
    spec = StackSpec(
        id="built",
        layout=RailLayout(
            anchor="viewport.bottom.center",
            orientation="horizontal",
            scale=1.5,
            opacity=0.5,
        ),
        items=(
            StackItem(
                type="toolButton",
                id="built.move",
                label="M",
                action="maya.tool.move",
                active_when="maya.tool == move",
            ),
            StackItem(type="spacer", id="built.gap", size=3),
            StackItem(type="button", id="built.empty", label="E"),
            StackItem(
                type="button",
                id="built.hidden",
                label="H",
                visible_when="false",
            ),
        ),
    )

    root = widgets.build_transform_stack(
        spec,
        registry,
        state_snapshot=MayaStateSnapshot(current_tool="moveSuperContext", selection_count=0),
        cmds_module=cmds,
    )
    buttons = root.findChildren(BuildButton)

    assert root.opacity == 0.5
    assert root.fixed_size == ((100, 200),)
    assert [button.property("actionRailSlotId") for button in buttons] == [
        "built.move",
        "built.empty",
    ]
    assert buttons[0].property("actionRailActive") == "true"
    assert buttons[1].property("actionRailLocked") == "true"

    buttons[0].clicked.emit()
    assert cmds.calls == [("setToolTo", "moveSuperContext")]


def test_build_transform_stack_flushes_pending_vertical_tool_cluster(monkeypatch) -> None:
    monkeypatch.setattr(widgets, "load", build_qt_binding)
    spec = StackSpec(
        id="vertical",
        layout=RailLayout(anchor="viewport.left.center", orientation="vertical"),
        items=(
            StackItem(type="toolButton", id="vertical.move", label="M", action="maya.tool.move"),
        ),
    )

    root = widgets.build_transform_stack(spec, create_default_registry(BuildCmds()))

    assert root.children[0].fixed_size[0] == widgets.DEFAULT_THEME.rail_width


def test_set_slot_key_label_updates_matching_buttons(monkeypatch) -> None:
    monkeypatch.setattr(widgets, "load", build_qt_binding)
    button = BuildButton("M")
    button.setProperty("actionRailSlotId", "slot.move")
    button.setProperty("actionRailLabel", "")
    button.setProperty("actionRailDiagnosticBadge", "?")
    button.setText("Move")
    root = FakeRoot([button])

    assert set_slot_key_label(root, "slot.move", "Ctrl+M") == 1
    assert button.text() == "Move\nCtrl+M?"
    assert set_slot_key_label(root, "slot.other", "X") == 0


def test_refresh_predicate_state_skips_missing_button_after_visibility_match(monkeypatch) -> None:
    monkeypatch.setattr(widgets, "load", build_qt_binding)
    spec = StackSpec(
        id="refresh",
        layout=RailLayout(anchor="viewport.left.center"),
        items=(StackItem(type="button", id="refresh.one", label="One"),),
    )
    monkeypatch.setattr(widgets, "_slot_buttons", lambda _root: {"refresh.one": None})

    result = refresh_predicate_state(FakeRoot([]), spec, create_default_registry(BuildCmds()))

    assert result.needs_rebuild is False
    assert result.refreshed == 0


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
    assert _button_text("K", "Ctrl+S", "?") == "K\nCtrl+S?"


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


def test_icon_diagnostic_handles_status_without_issue(monkeypatch) -> None:
    monkeypatch.setattr(
        widgets,
        "icon_status",
        lambda _icon_id: type("Status", (), {"ok": False, "issue": None})(),
    )

    assert _icon_diagnostic("missing.icon").code == "missing_icon"


def test_slot_diagnostic_ignores_availability_without_context() -> None:
    diagnostic = widgets._availability_diagnostic(
        StackItem(type="button", enabled_when="command.exists('missing')"),
        None,
    )

    assert diagnostic.has_issue is False


def test_slot_render_state_resolves_manifest_icon_path() -> None:
    registry = create_default_registry(object())
    item = StackItem(
        type="button",
        id="icon.ok",
        label="M",
        action="maya.tool.move",
        icon="actionrail.move",
    )

    state = _slot_render_state(item, registry)

    assert state.enabled is True
    assert state.icon == "actionrail.move"
    assert state.icon_path.endswith("icons\\actionrail\\move.svg") or state.icon_path.endswith(
        "icons/actionrail/move.svg"
    )
    assert state.diagnostic_code == ""
    assert state.text == "M"


def test_slot_render_state_resolves_maya_icon_name() -> None:
    registry = create_default_registry(object())
    item = StackItem(
        type="button",
        id="icon.maya",
        label="M",
        action="maya.tool.move",
        icon="maya.move",
    )

    state = _slot_render_state(item, registry)

    assert state.enabled is True
    assert state.icon == "maya.move"
    assert state.icon_path == ""
    assert state.icon_name == "move_M.png"
    assert state.diagnostic_code == ""
    assert state.text == "M"


def test_build_transform_stack_validates_maya_icon_resource(monkeypatch) -> None:
    monkeypatch.setattr(widgets, "load", build_qt_binding)
    cmds = MissingMayaIconResourceCmds()
    spec = StackSpec(
        id="missing_maya_icon",
        layout=RailLayout(anchor="viewport.left.center"),
        items=(
            StackItem(
                type="button",
                id="missing_maya_icon.move",
                label="M",
                action="maya.tool.move",
                icon="maya.move",
            ),
        ),
    )

    root = widgets.build_transform_stack(
        spec,
        create_default_registry(cmds),
        cmds_module=cmds,
    )
    button = root.findChildren(BuildButton)[0]

    assert button.property("actionRailDiagnosticCode") == "missing_maya_icon_resource"
    assert button.property("actionRailDiagnosticSeverity") == "warning"
    assert button.property("actionRailIconName") == ""
    assert button.text() == "M\n?"


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


def test_apply_slot_render_state_handles_partial_and_raising_buttons(monkeypatch) -> None:
    monkeypatch.setattr(widgets, "load", build_qt_binding)

    class PartialButton:
        def __init__(self) -> None:
            self.tooltip = ""

        def property(self, _name: str) -> object:
            raise RuntimeError("deleted")

        def setProperty(self, _name: str, _value: object) -> None:  # noqa: N802
            raise RuntimeError("deleted")

        def setToolTip(self, tooltip: str) -> None:  # noqa: N802
            self.tooltip = tooltip

        def text(self) -> str:
            raise RuntimeError("deleted")

        def setText(self, _text: str) -> None:  # noqa: N802
            raise RuntimeError("deleted")

        def isEnabled(self) -> bool:  # noqa: N802
            raise RuntimeError("deleted")

        def setEnabled(self, _enabled: bool) -> None:  # noqa: N802
            raise RuntimeError("deleted")

    refreshed = _apply_slot_render_state(
        PartialButton(),
        SlotRenderState(
            label="L",
            key_label="K",
            icon="",
            icon_path="",
            icon_name="",
            tone="neutral",
            tooltip="Tip",
            enabled=False,
            active=False,
            locked=True,
        ),
    )

    assert refreshed == 0


def test_apply_slot_render_state_ignores_tooltip_access_errors(monkeypatch) -> None:
    monkeypatch.setattr(widgets, "load", build_qt_binding)

    class TooltipButton(BuildButton):
        def toolTip(self) -> str:  # noqa: N802
            raise RuntimeError("deleted")

        def setToolTip(self, _tooltip: str) -> None:  # noqa: N802
            raise RuntimeError("deleted")

    refreshed = _apply_slot_render_state(
        TooltipButton("L"),
        SlotRenderState(
            label="L",
            key_label="",
            icon="",
            icon_path="",
            icon_name="",
            tone="neutral",
            tooltip="Tip",
            enabled=True,
            active=False,
        ),
    )

    assert refreshed >= 0


def test_apply_button_icon_handles_repeated_missing_and_failing_icon_paths(monkeypatch) -> None:
    monkeypatch.setattr(widgets, "load", build_qt_binding)
    button = BuildButton("Icon")
    button.setProperty("actionRailButtonIconSize", 32)

    assert _apply_button_icon(button, "") == 1
    assert _apply_button_icon(button, "") == 0
    assert _apply_button_icon(button, "icons/test.svg") == 1
    assert button.icon_size.width == 32
    assert button.icon_size.height == 32
    assert _apply_button_icon(button, "", "move_M.png") == 1
    assert button.icons[-1].path == ":/move_M.png"
    assert button.property("actionRailAppliedIconSource") == ":/move_M.png"
    assert _apply_button_icon(button, "", ":/rotate_M.png") == 1
    assert button.icons[-1].path == ":/rotate_M.png"

    class FailingIconButton(BuildButton):
        def property(self, _name: str) -> object:
            raise RuntimeError("deleted")

        def setIcon(self, _icon) -> None:  # noqa: N802
            raise RuntimeError("deleted")

    assert _apply_button_icon(FailingIconButton("Icon"), "icons/test.svg") == 0


def test_set_button_property_and_diagnostic_tooltip_helpers() -> None:
    class BrokenPropertyButton:
        def property(self, _name: str) -> object:
            raise RuntimeError("deleted")

        def setProperty(self, _name: str, _value: object) -> None:  # noqa: N802
            raise RuntimeError("deleted")

    assert widgets._set_button_property(BrokenPropertyButton(), "name", "value") == 0
    assert _diagnostic_tooltip("", widgets._SlotDiagnostic(message="Problem")) == "Problem"
    assert _scaled_theme(widgets.DEFAULT_THEME, 1.0) is widgets.DEFAULT_THEME
