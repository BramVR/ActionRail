from __future__ import annotations

import actionrail.slot_state as slot_state
import actionrail.widgets as widgets
from actionrail.actions import create_default_registry
from actionrail.predicates import PredicateContext
from actionrail.qt import QtBinding
from actionrail.spec import (
    RailAppearance,
    RailBackground,
    RailBorder,
    RailCollapse,
    RailLayout,
    StackItem,
    StackSpec,
)
from actionrail.state import MayaStateSnapshot
from actionrail.widgets import (
    SlotRenderState,
    refresh_predicate_state,
    resolve_slot_render_state,
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
        self.text_value = widgets._button_text(label, key_label)
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


def test_collapsed_handle_size_uses_larger_click_target_and_scale() -> None:
    vertical_spec = StackSpec(
        id="edge",
        layout=RailLayout(anchor="viewport.left.center", scale=1.0),
        items=(StackItem(type="button", id="edge.move", label="M"),),
        collapse=RailCollapse(enabled=True, edge="left"),
    )
    horizontal_spec = StackSpec(
        id="edge",
        layout=RailLayout(anchor="viewport.top.center", scale=1.5),
        items=(StackItem(type="button", id="edge.move", label="M"),),
        collapse=RailCollapse(enabled=True, edge="top"),
    )

    assert widgets._collapsed_handle_size(vertical_spec) == (24, 52)
    assert widgets._collapsed_handle_size(horizontal_spec) == (78, 36)


class FakeLayout:
    def __init__(self, parent) -> None:
        self.parent = parent
        self.items = []
        parent.layout = self

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
    QGridLayout = FakeLayout


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


def _built_buttons(
    monkeypatch,
    spec: StackSpec,
    *,
    state_snapshot: MayaStateSnapshot | None = None,
    cmds_module: object | None = None,
) -> list[BuildButton]:
    monkeypatch.setattr(widgets, "load", build_qt_binding)
    cmds = cmds_module or BuildCmds()
    root = widgets.build_transform_stack(
        spec,
        create_default_registry(cmds),
        state_snapshot=state_snapshot,
        cmds_module=cmds,
    )
    return root.findChildren(BuildButton)


def test_literal_false_visibility_skips_item_before_frame_building(monkeypatch) -> None:
    spec = StackSpec(
        id="visibility",
        layout=RailLayout(anchor="viewport.left.center"),
        items=(
            StackItem(type="button", id="visibility.default", label="D"),
            StackItem(type="button", id="visibility.true", label="T", visible_when="true"),
            StackItem(type="button", id="visibility.false", label="F", visible_when="false"),
        ),
    )

    buttons = _built_buttons(monkeypatch, spec)

    assert [button.property("actionRailSlotId") for button in buttons] == [
        "visibility.default",
        "visibility.true",
    ]


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
    assert root.properties["actionRailRoot"] == "true"


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


def test_build_transform_stack_marks_unlocked_slot_edit_buttons(monkeypatch) -> None:
    monkeypatch.setattr(widgets, "load", build_qt_binding)
    cmds = BuildCmds()
    callbacks = widgets.SlotEditCallbacks(
        unlocked=True,
        unlock_rail=lambda: True,
        lock_rail=lambda: True,
        assign_action=lambda _slot_id, _action_id: True,
        clear_slot=lambda _slot_id: True,
    )
    spec = StackSpec(
        id="slot_edit",
        layout=RailLayout(anchor="viewport.left.center"),
        items=(
            StackItem(
                type="button",
                id="slot_edit.move",
                label="M",
                action="maya.tool.move",
            ),
        ),
    )

    root = widgets.build_transform_stack(
        spec,
        create_default_registry(cmds),
        slot_edit_callbacks=callbacks,
    )
    button = root.findChildren(BuildButton)[0]

    assert button.property("actionRailSlotEditUnlocked") == "true"
    button.clicked.emit()
    assert cmds.calls == []


def test_build_transform_stack_locked_slot_edit_menu_keeps_actions_enabled(
    monkeypatch,
) -> None:
    monkeypatch.setattr(widgets, "load", build_qt_binding)
    cmds = BuildCmds()
    callbacks = widgets.SlotEditCallbacks(
        unlocked=False,
        unlock_rail=lambda: True,
        lock_rail=lambda: True,
        assign_action=lambda _slot_id, _action_id: True,
        clear_slot=lambda _slot_id: True,
    )
    spec = StackSpec(
        id="slot_edit_locked",
        layout=RailLayout(anchor="viewport.left.center"),
        items=(
            StackItem(
                type="button",
                id="slot_edit_locked.move",
                label="M",
                action="maya.tool.move",
            ),
        ),
    )

    root = widgets.build_transform_stack(
        spec,
        create_default_registry(cmds),
        slot_edit_callbacks=callbacks,
    )
    button = root.findChildren(BuildButton)[0]

    assert button.property("actionRailSlotEditUnlocked") == "false"
    button.clicked.emit()
    assert cmds.calls == [("setToolTo", "moveSuperContext")]


def test_unlocked_slot_accepts_action_book_drop_payload() -> None:
    events: list[tuple[str, str]] = []

    class DropButton:
        def __init__(self) -> None:
            self.accept_drops = False

        def setAcceptDrops(self, enabled: bool) -> None:  # noqa: N802
            self.accept_drops = enabled

    class MimeData:
        def hasFormat(self, mime_type: str) -> bool:  # noqa: N802
            return mime_type == "application/x-actionrail-action-id"

        def data(self, _mime_type: str) -> bytes:
            return b"maya.tool.scale"

    class DropEvent:
        def __init__(self) -> None:
            self.accepted = False

        def mimeData(self) -> MimeData:  # noqa: N802
            return MimeData()

        def acceptProposedAction(self) -> None:  # noqa: N802
            self.accepted = True

    button = DropButton()
    callbacks = widgets.SlotEditCallbacks(
        unlocked=True,
        unlock_rail=lambda: True,
        lock_rail=lambda: True,
        assign_action=lambda slot_id, action_id: events.append((slot_id, action_id)) or True,
        clear_slot=lambda _slot_id: True,
    )
    button._actionrail_slot_edit_callbacks = callbacks

    widgets._install_action_book_drop(
        button,
        StackItem(type="button", id="drop.slot", label="New"),
        callbacks,
    )
    drag_event = DropEvent()
    drop_event = DropEvent()

    button.dragEnterEvent(drag_event)
    button.dropEvent(drop_event)

    assert button.accept_drops is True
    assert drag_event.accepted is True
    assert drop_event.accepted is True
    assert events == [("drop.slot", "maya.tool.scale")]


def test_action_book_drop_event_filter_accepts_drag_enter_and_drop() -> None:
    events: list[tuple[str, str]] = []

    class QObject:
        def __init__(self, _parent: object | None = None) -> None:
            pass

    class QEvent:
        DragEnter = 1
        DragMove = 2
        Drop = 3

    qt_core = type("QtCore", (), {"QObject": QObject, "QEvent": QEvent})
    qt = type("Qt", (), {"QtCore": qt_core})

    class Button:
        def __init__(self) -> None:
            self.event_filter = None

        def installEventFilter(self, event_filter: object) -> None:  # noqa: N802
            self.event_filter = event_filter

    class MimeData:
        def hasFormat(self, mime_type: str) -> bool:  # noqa: N802
            return mime_type == "application/x-actionrail-action-id"

        def data(self, _mime_type: str) -> bytes:
            return b"maya.tool.scale"

    class DropEvent:
        def __init__(self, event_type: int) -> None:
            self._event_type = event_type
            self.accepted = False

        def type(self) -> int:
            return self._event_type

        def mimeData(self) -> MimeData:  # noqa: N802
            return MimeData()

        def acceptProposedAction(self) -> None:  # noqa: N802
            self.accepted = True

    button = Button()
    callbacks = widgets.SlotEditCallbacks(
        unlocked=True,
        unlock_rail=lambda: True,
        lock_rail=lambda: True,
        assign_action=lambda slot_id, action_id: events.append((slot_id, action_id)) or True,
        clear_slot=lambda _slot_id: True,
    )
    button._actionrail_slot_edit_callbacks = callbacks

    installed = widgets._install_action_book_drop_event_filter(
        qt,
        button,
        StackItem(type="button", id="drop.slot", label="New"),
        callbacks,
    )

    drag_event = DropEvent(QEvent.DragEnter)
    drop_event = DropEvent(QEvent.Drop)

    assert installed is True
    assert button.event_filter.eventFilter(button, drag_event) is True
    assert drag_event.accepted is True
    assert button.event_filter.eventFilter(button, drop_event) is True
    assert drop_event.accepted is True
    assert events == [("drop.slot", "maya.tool.scale")]


def test_locked_slot_ignores_action_book_drop_payload() -> None:
    events: list[tuple[str, str]] = []

    class DropButton:
        def setAcceptDrops(self, _enabled: bool) -> None:  # noqa: N802
            return None

    class MimeData:
        def hasFormat(self, _mime_type: str) -> bool:  # noqa: N802
            return True

        def data(self, _mime_type: str) -> bytes:
            return b"maya.tool.scale"

    class DropEvent:
        accepted = False

        def mimeData(self) -> MimeData:  # noqa: N802
            return MimeData()

        def acceptProposedAction(self) -> None:  # noqa: N802
            self.accepted = True

    button = DropButton()
    callbacks = widgets.SlotEditCallbacks(
        unlocked=False,
        unlock_rail=lambda: True,
        lock_rail=lambda: True,
        assign_action=lambda slot_id, action_id: events.append((slot_id, action_id)) or True,
        clear_slot=lambda _slot_id: True,
    )
    button._actionrail_slot_edit_callbacks = callbacks

    widgets._install_action_book_drop(
        button,
        StackItem(type="button", id="drop.slot", label="New"),
        callbacks,
    )
    event = DropEvent()

    button.dropEvent(event)

    assert event.accepted is False
    assert events == []


def test_unlocked_shift_drag_moves_or_clears_slot_payload(monkeypatch) -> None:
    events: list[tuple[str, ...]] = []

    class Point:
        def __init__(self, x_pos: int, y_pos: int) -> None:
            self._x_pos = x_pos
            self._y_pos = y_pos

        def x(self) -> int:
            return self._x_pos

        def y(self) -> int:
            return self._y_pos

    class Event:
        def __init__(self, x_pos: int, y_pos: int) -> None:
            self._point = Point(x_pos, y_pos)
            self.accepted = False

        def button(self) -> int:
            return 1

        def modifiers(self) -> int:
            return 2

        def globalPos(self) -> Point:  # noqa: N802
            return self._point

        def accept(self) -> None:
            self.accepted = True

    class Root:
        def objectName(self) -> str:  # noqa: N802
            return "ActionRailViewportOverlay_transform_stack"

        def parent(self) -> None:
            return None

    class DragButton:
        def __init__(self, slot_id: str, parent: object) -> None:
            self.slot_id = slot_id
            self._parent = parent
            self.base_events: list[str] = []

        def property(self, name: str) -> object:
            if name == "actionRailSlotId":
                return self.slot_id
            return None

        def parent(self) -> object:
            return self._parent

        def mousePressEvent(self, _event: object) -> None:  # noqa: N802
            self.base_events.append("press")

        def mouseMoveEvent(self, _event: object) -> None:  # noqa: N802
            self.base_events.append("move")

        def mouseReleaseEvent(self, _event: object) -> None:  # noqa: N802
            self.base_events.append("release")

    class DragQt:
        class QtCore:
            class Qt:
                LeftButton = 1
                ShiftModifier = 2

        class QtWidgets:
            QPushButton = DragButton
            target: object | None = None

            class QApplication:
                @staticmethod
                def startDragDistance() -> int:  # noqa: N802
                    return 4

                @staticmethod
                def widgetAt(_point: object) -> object | None:  # noqa: N802
                    return DragQt.QtWidgets.target

    monkeypatch.setattr(widgets, "load", lambda: DragQt)
    root = Root()
    source = DragButton("drag.source", root)
    target = DragButton("drag.target", root)
    callbacks = widgets.SlotEditCallbacks(
        unlocked=True,
        unlock_rail=lambda: True,
        lock_rail=lambda: True,
        assign_action=lambda _slot_id, _action_id: True,
        clear_slot=lambda slot_id: events.append(("clear", slot_id)) is None,
        move_slot=lambda source_id, target_id: events.append((source_id, target_id)) is None,
        transfer_slot=lambda source_id, _target_callbacks, target_id: events.append(
            ("transfer", source_id, target_id)
        )
        is None,
    )

    widgets._install_slot_drag_edit(
        source,
        StackItem(
            type="button",
            id="drag.source",
            label="Move",
            action="maya.tool.move",
        ),
        callbacks,
    )

    DragQt.QtWidgets.target = target
    source.mousePressEvent(Event(0, 0))
    source.mouseMoveEvent(Event(10, 0))
    source.mouseReleaseEvent(Event(10, 0))
    assert events == [("drag.source", "drag.target")]

    other_root = Root()
    other_target = DragButton("drag.other", other_root)
    other_target._actionrail_slot_edit_callbacks = widgets.SlotEditCallbacks(
        unlocked=True,
        unlock_rail=lambda: True,
        lock_rail=lambda: True,
        assign_action=lambda _slot_id, _action_id: True,
        clear_slot=lambda _slot_id: True,
        move_slot=lambda _source_id, _target_id: True,
    )
    DragQt.QtWidgets.target = other_target
    source.mousePressEvent(Event(0, 0))
    source.mouseMoveEvent(Event(10, 0))
    source.mouseReleaseEvent(Event(10, 0))
    assert events == [
        ("drag.source", "drag.target"),
        ("transfer", "drag.source", "drag.other"),
    ]

    locked_root = Root()
    locked_target = DragButton("drag.locked", locked_root)
    locked_target._actionrail_slot_edit_callbacks = widgets.SlotEditCallbacks(
        unlocked=False,
        unlock_rail=lambda: True,
        lock_rail=lambda: True,
        assign_action=lambda _slot_id, _action_id: True,
        clear_slot=lambda _slot_id: True,
        move_slot=lambda _source_id, _target_id: True,
    )
    DragQt.QtWidgets.target = locked_target
    source.mousePressEvent(Event(0, 0))
    source.mouseMoveEvent(Event(10, 0))
    source.mouseReleaseEvent(Event(10, 0))
    assert events == [
        ("drag.source", "drag.target"),
        ("transfer", "drag.source", "drag.other"),
    ]

    DragQt.QtWidgets.target = None
    source.mousePressEvent(Event(0, 0))
    source.mouseMoveEvent(Event(0, 10))
    source.mouseReleaseEvent(Event(0, 10))
    assert events == [
        ("drag.source", "drag.target"),
        ("transfer", "drag.source", "drag.other"),
        ("clear", "drag.source"),
    ]

    DragQt.QtWidgets.target = source
    source.mousePressEvent(Event(0, 0))
    source.mouseMoveEvent(Event(10, 0))
    source.mouseReleaseEvent(Event(10, 0))
    assert events == [
        ("drag.source", "drag.target"),
        ("transfer", "drag.source", "drag.other"),
        ("clear", "drag.source"),
        ("clear", "drag.source"),
    ]
    assert source.base_events == []


def test_slot_drag_release_target_prefers_rail_geometry_over_widget_at() -> None:
    class Point:
        def __init__(self, x_pos: int, y_pos: int) -> None:
            self._x_pos = x_pos
            self._y_pos = y_pos

        def x(self) -> int:
            return self._x_pos

        def y(self) -> int:
            return self._y_pos

    class Rect:
        def __init__(self, x_pos: int, y_pos: int, width: int, height: int) -> None:
            self.x_pos = x_pos
            self.y_pos = y_pos
            self.width = width
            self.height = height

        def contains(self, point: Point) -> bool:
            return (
                self.x_pos <= point.x() < self.x_pos + self.width
                and self.y_pos <= point.y() < self.y_pos + self.height
            )

    class Root:
        def __init__(self) -> None:
            self.buttons: list[DragButton] = []

        def objectName(self) -> str:  # noqa: N802
            return "ActionRailViewportOverlay_transform_stack"

        def parent(self) -> None:
            return None

        def mapFromGlobal(self, point: Point) -> Point:  # noqa: N802
            return point

        def rect(self) -> Rect:
            return Rect(0, 0, 120, 40)

        def findChildren(self, _button_class: object) -> list[object]:  # noqa: N802
            return list(self.buttons)

    class DragButton:
        def __init__(self, slot_id: str, parent: Root, rect: Rect) -> None:
            self.slot_id = slot_id
            self._parent = parent
            self._rect = rect
            parent.buttons.append(self)

        def property(self, name: str) -> object:
            if name == "actionRailSlotId":
                return self.slot_id
            return None

        def parent(self) -> object:
            return self._parent

        def mapFromGlobal(self, point: Point) -> Point:  # noqa: N802
            return point

        def mapToGlobal(self, point: Point) -> Point:  # noqa: N802
            return point

        def rect(self) -> Rect:
            return self._rect

    class Event:
        def __init__(self, global_point: Point, local_point: Point) -> None:
            self._global_point = global_point
            self._local_point = local_point

        def globalPos(self) -> Point:  # noqa: N802
            return self._global_point

        def pos(self) -> Point:
            return self._local_point

    class DragQt:
        class QtWidgets:
            QPushButton = DragButton

            class QApplication:
                @staticmethod
                def widgetAt(_point: Point) -> object | None:  # noqa: N802
                    return None

    root = Root()
    source = DragButton("drag.source", root, Rect(0, 0, 40, 40))
    DragButton("drag.target", root, Rect(80, 0, 40, 40))

    assert widgets._slot_drag_release_target(DragQt, source, Point(90, 12)) == (
        "drag.target",
        True,
    )
    assert widgets._slot_drag_release_target(DragQt, source, Point(200, 12)) == (
        None,
        False,
    )
    assert widgets._slot_drag_release_target(DragQt, source, Point(60, 12)) == (
        None,
        True,
    )
    assert widgets._slot_drag_release_target_from_points(
        DragQt,
        source,
        (Point(12, 12), Point(200, 12)),
    ) == (None, False)
    assert widgets._slot_drag_release_target_from_points(
        DragQt,
        source,
        (Point(12, 12), Point(90, 12)),
    ) == ("drag.target", True)
    state: dict[str, object] = {}
    widgets._record_slot_drag_points(state, (Point(200, 12),))
    combined = widgets._combined_slot_drag_points(state, (Point(12, 12),))
    assert [(point.x(), point.y()) for point in combined] == [(12, 12), (200, 12)]
    assert widgets._slot_drag_release_target_from_points(DragQt, source, combined) == (
        None,
        False,
    )
    event_points = widgets._slot_drag_event_points(
        DragQt,
        source,
        Event(Point(12, 12), Point(200, 12)),
    )
    assert [(point.x(), point.y()) for point in event_points] == [(12, 12), (200, 12)]


def test_slot_drag_cross_rail_target_falls_back_to_application_geometry() -> None:
    class Point:
        def __init__(self, x_pos: int, y_pos: int) -> None:
            self._x_pos = x_pos
            self._y_pos = y_pos

        def x(self) -> int:
            return self._x_pos

        def y(self) -> int:
            return self._y_pos

    class Rect:
        def __init__(self, x_pos: int, y_pos: int, width: int, height: int) -> None:
            self.x_pos = x_pos
            self.y_pos = y_pos
            self.width = width
            self.height = height

        def contains(self, point: Point) -> bool:
            return (
                self.x_pos <= point.x() < self.x_pos + self.width
                and self.y_pos <= point.y() < self.y_pos + self.height
            )

    class Root:
        def __init__(self, name: str, rect: Rect) -> None:
            self._name = name
            self._rect = rect

        def objectName(self) -> str:  # noqa: N802
            return self._name

        def parent(self) -> None:
            return None

        def mapFromGlobal(self, point: Point) -> Point:  # noqa: N802
            return point

        def rect(self) -> Rect:
            return self._rect

    class DragButton:
        def __init__(self, slot_id: str, parent: Root, rect: Rect) -> None:
            self.slot_id = slot_id
            self._parent = parent
            self._rect = rect
            self._actionrail_slot_edit_callbacks = widgets.SlotEditCallbacks(
                unlocked=True,
                unlock_rail=lambda: True,
                lock_rail=lambda: True,
                assign_action=lambda _slot_id, _action_id: True,
                clear_slot=lambda _slot_id: True,
                move_slot=lambda _source_id, _target_id: True,
            )

        def property(self, name: str) -> object:
            if name == "actionRailSlotId":
                return self.slot_id
            return None

        def parent(self) -> Root:
            return self._parent

        def mapFromGlobal(self, point: Point) -> Point:  # noqa: N802
            return point

        def rect(self) -> Rect:
            return self._rect

    source_root = Root("ActionRailViewportOverlay_source", Rect(0, 0, 40, 40))
    target_root = Root("ActionRailViewportOverlay_target", Rect(80, 0, 40, 40))
    source = DragButton("source.move", source_root, Rect(0, 0, 40, 40))
    target = DragButton("target.empty", target_root, Rect(80, 0, 40, 40))

    class DragQt:
        class QtWidgets:
            class QApplication:
                @staticmethod
                def widgetAt(_point: Point) -> None:  # noqa: N802
                    return None

                @staticmethod
                def allWidgets() -> list[object]:  # noqa: N802
                    return [source_root, target_root, source, target]

    drop_target = widgets._slot_drag_cross_rail_target(
        DragQt,
        source_root,
        (Point(88, 12),),
    )

    assert drop_target.slot_id == "target.empty"
    assert drop_target.callbacks is target._actionrail_slot_edit_callbacks
    assert drop_target.inside_action_rail is True
    assert drop_target.same_rail is False


def test_slot_drag_cross_rail_target_resolves_slot_when_widget_at_returns_root() -> None:
    class Point:
        def __init__(self, x_pos: int, y_pos: int) -> None:
            self._x_pos = x_pos
            self._y_pos = y_pos

        def x(self) -> int:
            return self._x_pos

        def y(self) -> int:
            return self._y_pos

    class Rect:
        def __init__(self, x_pos: int, y_pos: int, width: int, height: int) -> None:
            self.x_pos = x_pos
            self.y_pos = y_pos
            self.width = width
            self.height = height

        def contains(self, point: Point) -> bool:
            return (
                self.x_pos <= point.x() < self.x_pos + self.width
                and self.y_pos <= point.y() < self.y_pos + self.height
            )

    class Root:
        def __init__(self, name: str) -> None:
            self._name = name
            self.buttons: list[DragButton] = []

        def objectName(self) -> str:  # noqa: N802
            return self._name

        def parent(self) -> None:
            return None

        def findChildren(self, _button_class: object) -> list[object]:  # noqa: N802
            return list(self.buttons)

    class DragButton:
        def __init__(self, slot_id: str, parent: Root, rect: Rect) -> None:
            self.slot_id = slot_id
            self._parent = parent
            self._rect = rect
            self._actionrail_slot_edit_callbacks = widgets.SlotEditCallbacks(
                unlocked=True,
                unlock_rail=lambda: True,
                lock_rail=lambda: True,
                assign_action=lambda _slot_id, _action_id: True,
                clear_slot=lambda _slot_id: True,
                move_slot=lambda _source_id, _target_id: True,
            )
            parent.buttons.append(self)

        def property(self, name: str) -> object:
            if name == "actionRailSlotId":
                return self.slot_id
            return None

        def parent(self) -> Root:
            return self._parent

        def mapFromGlobal(self, point: Point) -> Point:  # noqa: N802
            return point

        def rect(self) -> Rect:
            return self._rect

    source_root = Root("ActionRailViewportOverlay_source")
    target_root = Root("ActionRailViewportOverlay_target")
    source = DragButton("source.move", source_root, Rect(0, 0, 40, 40))
    target = DragButton("target.empty", target_root, Rect(80, 0, 40, 40))

    class DragQt:
        class QtWidgets:
            QPushButton = DragButton

            class QApplication:
                @staticmethod
                def widgetAt(_point: Point) -> Root:  # noqa: N802
                    return target_root

    drop_target = widgets._slot_drag_cross_rail_target(
        DragQt,
        source_root,
        (Point(88, 12),),
    )

    assert drop_target.slot_id == "target.empty"
    assert drop_target.callbacks is target._actionrail_slot_edit_callbacks
    assert drop_target.inside_action_rail is True
    assert drop_target.same_rail is False
    assert source.parent() is source_root


def test_slot_edit_callbacks_from_button_uses_live_owner_unlock_state() -> None:
    class Owner:
        def slot_edit_unlocked(self) -> bool:
            return True

    class Button:
        pass

    button = Button()
    button._actionrail_slot_edit_callbacks = widgets.SlotEditCallbacks(
        unlocked=False,
        unlock_rail=lambda: True,
        lock_rail=lambda: True,
        assign_action=lambda _slot_id, _action_id: True,
        clear_slot=lambda _slot_id: True,
        move_slot=lambda _source_id, _target_id: True,
        owner=Owner(),
    )

    callbacks = widgets._slot_edit_callbacks_from_button(button)

    assert callbacks is not None
    assert callbacks.unlocked is True
    assert button._actionrail_slot_edit_callbacks.unlocked is False


def test_build_transform_stack_wraps_multi_row_layout(monkeypatch) -> None:
    monkeypatch.setattr(widgets, "load", build_qt_binding)
    spec = StackSpec(
        id="wrapped",
        layout=RailLayout(
            anchor="viewport.bottom.center",
            orientation="horizontal",
            rows=2,
            columns=3,
        ),
        items=tuple(
            StackItem(type="button", id=f"wrapped.{index}", label=str(index))
            for index in range(5)
        ),
    )

    root = widgets.build_transform_stack(spec, create_default_registry(BuildCmds()))

    assert [item[2] for item in root.layout.items] == [
        (0, 0, BuildQtCore.Qt.AlignLeft),
        (0, 1, BuildQtCore.Qt.AlignLeft),
        (0, 2, BuildQtCore.Qt.AlignLeft),
        (1, 0, BuildQtCore.Qt.AlignLeft),
        (1, 1, BuildQtCore.Qt.AlignLeft),
    ]


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
    assert root.children[0].layout.margins == (6, 6, 6, 6)


def test_build_transform_stack_applies_spec_appearance(monkeypatch) -> None:
    monkeypatch.setattr(widgets, "load", build_qt_binding)
    spec = StackSpec(
        id="styled",
        layout=RailLayout(anchor="viewport.left.center"),
        items=(StackItem(type="button", id="styled.move", label="M"),),
        appearance=RailAppearance(
            background=RailBackground(color="#111722", pattern="none"),
            border=RailBorder(width=3),
        ),
    )

    root = widgets.build_transform_stack(spec, create_default_registry(BuildCmds()))

    assert "min-width: 32px;" in root.style_sheet
    assert root.children[0].layout.margins == (7, 7, 7, 7)


def test_set_slot_key_label_updates_matching_buttons(monkeypatch) -> None:
    monkeypatch.setattr(widgets, "load", build_qt_binding)
    button = BuildButton("M")
    button.setProperty("actionRailSlotId", "slot.move")
    button.setProperty("actionRailLabel", None)
    button.setProperty("actionRailDiagnosticBadge", "?")
    button.setText("Move")
    empty_label_button = BuildButton("")
    empty_label_button.setProperty("actionRailSlotId", "slot.empty")
    empty_label_button.setProperty("actionRailLabel", "")
    empty_label_button.setProperty("actionRailDiagnosticBadge", "")
    empty_label_button.setText("Old")
    root = FakeRoot([button, empty_label_button])

    assert set_slot_key_label(root, "slot.move", "Ctrl+M") == 1
    assert button.text() == "Move\nCtrl+M?"
    assert set_slot_key_label(root, "slot.empty", "1") == 1
    assert empty_label_button.text() == "1"
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


def test_state_visibility_skips_item_before_frame_building(monkeypatch) -> None:
    spec = StackSpec(
        id="selection_visibility",
        layout=RailLayout(anchor="viewport.left.center"),
        items=(
            StackItem(
                type="button",
                id="selection_visibility.slot",
                label="S",
                visible_when="selection.count > 0",
            ),
        ),
    )

    assert (
        _built_buttons(
            monkeypatch,
            spec,
            state_snapshot=MayaStateSnapshot(current_tool="", selection_count=0),
        )
        == []
    )
    buttons = _built_buttons(
        monkeypatch,
        spec,
        state_snapshot=MayaStateSnapshot(current_tool="", selection_count=1),
    )

    assert [button.property("actionRailSlotId") for button in buttons] == [
        "selection_visibility.slot"
    ]


def test_missing_visible_dependency_keeps_item_visible_for_badge(monkeypatch) -> None:
    spec = StackSpec(
        id="missing_visible_dependency",
        layout=RailLayout(anchor="viewport.left.center"),
        items=(
            StackItem(
                type="button",
                id="missing_visible_dependency.plugin",
                label="P",
                action="maya.anim.set_key",
                visible_when="plugin.exists('missingPlugin')",
            ),
        ),
    )

    button = _built_buttons(monkeypatch, spec, cmds_module=AvailabilityCmds())[0]

    assert button.property("actionRailSlotId") == "missing_visible_dependency.plugin"
    assert button.property("actionRailDiagnosticCode") == "missing_plugin"


def test_missing_visible_dependency_preserves_other_visibility_clauses(monkeypatch) -> None:
    spec = StackSpec(
        id="compound_visibility",
        layout=RailLayout(anchor="viewport.left.center"),
        items=(
            StackItem(
                type="button",
                id="compound_visibility.plugin",
                label="P",
                action="maya.anim.set_key",
                visible_when="selection.count > 0 and plugin.exists('missingPlugin')",
            ),
        ),
    )

    assert (
        _built_buttons(
            monkeypatch,
            spec,
            state_snapshot=MayaStateSnapshot(current_tool="", selection_count=0),
            cmds_module=AvailabilityCmds(),
        )
        == []
    )
    buttons = _built_buttons(
        monkeypatch,
        spec,
        state_snapshot=MayaStateSnapshot(current_tool="", selection_count=1),
        cmds_module=AvailabilityCmds(),
    )

    assert [button.property("actionRailDiagnosticCode") for button in buttons] == [
        "missing_plugin"
    ]


def test_negated_missing_visible_dependency_does_not_get_forced_badge_state(
    monkeypatch,
) -> None:
    spec = StackSpec(
        id="negated_visibility",
        layout=RailLayout(anchor="viewport.left.center"),
        items=(
            StackItem(
                type="button",
                id="negated_visibility.plugin",
                label="P",
                action="maya.anim.set_key",
                visible_when="not plugin.exists('missingPlugin')",
            ),
        ),
    )

    button = _built_buttons(monkeypatch, spec, cmds_module=AvailabilityCmds())[0]

    assert button.property("actionRailSlotId") == "negated_visibility.plugin"
    assert button.property("actionRailDiagnosticCode") == ""

def test_empty_active_predicate_is_inactive_by_default() -> None:
    registry = create_default_registry(object())

    inactive = resolve_slot_render_state(
        StackItem(type="button", action="maya.anim.set_key", active_when=""),
        registry,
    )
    active = resolve_slot_render_state(
        StackItem(type="button", action="maya.anim.set_key", active_when="true"),
        registry,
    )

    assert inactive.active is False
    assert active.active is True


def test_button_text_adds_key_label_on_second_line() -> None:
    assert widgets._button_text("K", "") == "K"
    assert widgets._button_text("K", "Ctrl+S") == "K\nCtrl+S"
    assert widgets._button_text("K", "Ctrl+S", "?") == "K\nCtrl+S?"
    assert widgets._button_text("", "1") == "1"


def test_button_paint_text_helpers_use_properties_and_text_fallback() -> None:
    button = FakeButton("slot", label="", key_label="7")
    button.setProperty("actionRailDiagnosticBadge", "?")

    assert widgets._button_label(button) == ""
    assert widgets._button_secondary(button) == "7?"

    button.setProperty("actionRailLabel", "Move\nCtrl+M")
    assert widgets._button_label(button) == "Move"

    button.setProperty("actionRailLabel", None)
    button.setText("Move\nCtrl+M")
    button.setProperty("actionRailKeyLabel", None)
    button.setProperty("actionRailDiagnosticBadge", None)

    assert widgets._button_label(button) == "Move"
    assert widgets._button_secondary(button) == ""

    class BrokenButton:
        def property(self, _name: str) -> object:
            raise RuntimeError("deleted")

        def text(self) -> str:
            raise RuntimeError("deleted")

    broken = BrokenButton()

    assert widgets._button_label(broken) == ""
    assert widgets._button_secondary(broken) == ""


def test_action_rail_button_paints_hotkey_in_bottom_right() -> None:
    events = []

    class Rect:
        def __init__(self, adjusted: tuple[int, int, int, int] | None = None) -> None:
            self.adjusted_args = adjusted

        def adjusted(self, left: int, top: int, right: int, bottom: int) -> Rect:
            return Rect((left, top, right, bottom))

        def size(self) -> tuple[int, int]:
            return (32, 32)

        def right(self) -> int:
            return 31

        def bottom(self) -> int:
            return 31

    class TextRect:
        def __init__(self, left: int, top: int, width: int, height: int) -> None:
            self.geometry = (left, top, width, height)
            self.adjusted_args = None

    class Pixmap:
        def isNull(self) -> bool:  # noqa: N802
            return False

    class Icon:
        def isNull(self) -> bool:  # noqa: N802
            return False

        def pixmap(self, size: tuple[int, int]) -> Pixmap:
            events.append(("pixmap", size))
            return Pixmap()

    class Font:
        def __init__(self, other: object | None = None) -> None:
            self.size = getattr(other, "size", 13)

        def pointSize(self) -> int:  # noqa: N802
            return self.size

        def setPointSize(self, size: int) -> None:  # noqa: N802
            self.size = size

    class Color:
        def color(self) -> str:
            return "#ffffff"

    class Palette:
        def buttonText(self) -> Color:  # noqa: N802
            return Color()

    class Painter:
        def __init__(self, _button: object) -> None:
            self.font_size = 0

        def setFont(self, font: Font) -> None:  # noqa: N802
            self.font_size = font.pointSize()

        def setPen(self, pen: str) -> None:  # noqa: N802
            events.append(("pen", pen))

        def fillRect(self, rect: Rect, color: str) -> None:  # noqa: N802
            events.append(("fill", rect.adjusted_args, color))

        def drawRect(self, rect: Rect) -> None:  # noqa: N802
            events.append(("rect", rect.adjusted_args))

        def drawPixmap(self, rect: Rect, _pixmap: Pixmap) -> None:  # noqa: N802
            events.append(("pixmap_drawn", rect.adjusted_args))

        def drawText(self, rect: Rect | TextRect, flags: int, text: str) -> None:  # noqa: N802
            geometry = getattr(rect, "geometry", None)
            events.append(("text", text, flags, rect.adjusted_args, geometry, self.font_size))

        def end(self) -> None:
            events.append(("end",))

    class StyleOptionButton:
        text = "old"
        icon = object()

    class EmptyIcon:
        pass

    class Style:
        def drawControl(  # noqa: N802
            self,
            control: int,
            option: StyleOptionButton,
            _painter: Painter,
            _button: object,
        ) -> None:
            events.append(("control", control, option.text, isinstance(option.icon, EmptyIcon)))

    class BaseButton:
        def __init__(self, text: str) -> None:
            self.text_value = text
            self.properties = {
                "actionRailLabel": "M",
                "actionRailKeyLabel": "7",
                "actionRailDiagnosticBadge": "",
                "actionRailActive": "true",
                "actionRailButtonActiveBorder": "#8ccf3f",
                "actionRailButtonBackplateInset": 2,
                "actionRailButtonIconInset": 3,
            }

        def initStyleOption(self, _option: StyleOptionButton) -> None:  # noqa: N802
            events.append(("init",))

        def style(self) -> Style:
            return Style()

        def icon(self) -> Icon:
            return Icon()

        def rect(self) -> Rect:
            return Rect()

        def property(self, name: str) -> object:
            return self.properties.get(name)

        def font(self) -> Font:
            return Font()

        def palette(self) -> Palette:
            return Palette()

        def text(self) -> str:
            return self.text_value

    class PaintQt:
        class QtCore:
            QRect = TextRect

            class Qt:
                AlignCenter = 1
                TextWordWrap = 2
                AlignRight = 4
                AlignBottom = 8

        class QtGui:
            QPainter = Painter
            QFont = Font
            QIcon = EmptyIcon

        class QtWidgets:
            QPushButton = BaseButton
            QStyleOptionButton = StyleOptionButton

            class QStyle:
                CE_PushButton = 11

    button = widgets._button_class(PaintQt)("M\n7")
    button.paintEvent(object())

    assert ("control", 11, "", True) not in events
    assert ("fill", (2, 2, -2, -2), "#444341") in events
    assert ("pen", "#171716") in events
    assert ("pen", "#8ccf3f") in events
    assert ("rect", (0, 0, -1, -1)) in events
    assert ("pixmap", (32, 32)) in events
    assert ("pixmap_drawn", (3, 3, -3, -3)) in events
    assert ("text", "M", 3, None, None, 13) in events
    assert ("text", "7", 12, None, (21, 21, 8, 9), 7) in events
    assert events[-1] == ("end",)


def test_secondary_hotkey_badge_uses_fitting_display_text() -> None:
    class HorizontalMetrics:
        def __init__(self, _font: object) -> None:
            pass

        def horizontalAdvance(self, text: str) -> int:  # noqa: N802
            return len(text) * 4

    class WidthMetrics:
        def __init__(self, _font: object) -> None:
            pass

        def width(self, text: str) -> int:
            return len(text) * 3

    class MetricsQt:
        class QtGui:
            QFontMetrics = HorizontalMetrics

    class WidthMetricsQt:
        class QtGui:
            QFontMetrics = WidthMetrics

    class FallbackQt:
        class QtGui:
            pass

    font = object()

    assert widgets._button_secondary_display_text(MetricsQt, font, "Ctrl+K", 28) == "Ctrl+K"
    assert (
        widgets._button_secondary_display_text(
            MetricsQt,
            font,
            "Ctrl+Alt+Shift+Command+K",
            28,
        )
        == "CASM+K"
    )
    assert widgets._button_secondary_display_text(WidthMetricsQt, font, "Ctrl+K", 12) == "C+K"
    assert widgets._compact_hotkey_label("Control+Alt+Shift+Command+K") == "C+A+S+M+K"
    assert widgets._dense_hotkey_label("F12") == "F12"
    assert widgets._dense_hotkey_label("Ctrl+Alt+K") == "CA+K"
    assert widgets._button_secondary_display_text(FallbackQt, font, "ABCDEFG", 25) == "A...G"
    assert widgets._elide_text(FallbackQt, font, "F12", 15) == "F12"
    assert widgets._elide_text(FallbackQt, font, "ABCDEFG", 25) == "A...G"
    assert widgets._elide_text(FallbackQt, font, "ABCDEFG", 10) == "G"


def test_secondary_hotkey_badge_rect_uses_available_button_width() -> None:
    class Rect:
        def width(self) -> int:
            return 32

        def right(self) -> int:
            return 31

        def bottom(self) -> int:
            return 31

    class TextRect:
        def __init__(self, left: int, top: int, width: int, height: int) -> None:
            self.geometry = (left, top, width, height)

    class Button:
        def rect(self) -> Rect:
            return Rect()

    class Metrics:
        def __init__(self, _font: object) -> None:
            pass

        def horizontalAdvance(self, text: str) -> int:  # noqa: N802
            return {"Ctrl+K": 24}.get(text, len(text) * 4)

    class MetricsQt:
        class QtCore:
            QRect = TextRect

        class QtGui:
            QFontMetrics = Metrics

    rect = widgets._button_secondary_rect(Button(), MetricsQt, "Ctrl+K", object())

    assert rect.geometry == (2, 21, 27, 9)
    assert widgets._button_secondary_max_width(Button()) == 28


def test_button_icon_metric_helpers_fall_back_after_property_errors() -> None:
    class BrokenButton:
        def property(self, _name: str) -> object:
            raise RuntimeError("deleted")

    button = BrokenButton()

    assert widgets._secondary_font_size(0) == 6
    assert widgets._secondary_font_size(13) == 7
    assert widgets._button_secondary_max_width(button) == 28
    assert widgets._button_icon_size(button) == 18
    assert widgets._button_icon_inset(button) == 0


def test_slot_render_state_uses_action_tooltip_fallback() -> None:
    registry = create_default_registry(object())
    item = StackItem(
        type="button",
        id="tooltip_test.set_key",
        label="K",
        action="maya.anim.set_key",
    )

    state = resolve_slot_render_state(item, registry)

    assert state.tooltip == "Set keyframe"


def test_slot_render_state_marks_missing_action_as_error() -> None:
    registry = create_default_registry(object())
    item = StackItem(
        type="button",
        id="broken.missing",
        label="X",
        action="maya.missing.action",
    )

    state = resolve_slot_render_state(item, registry)

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

    state = resolve_slot_render_state(item, registry)

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

    state = resolve_slot_render_state(item, registry)

    assert state.enabled is True
    assert state.icon == "missing.icon"
    assert state.icon_path == ""
    assert state.diagnostic_code == "missing_icon"
    assert state.diagnostic_severity == "warning"
    assert state.text == "I\n?"


def test_icon_diagnostic_handles_status_without_issue(monkeypatch) -> None:
    monkeypatch.setattr(
        slot_state,
        "icon_status",
        lambda _icon_id: type("Status", (), {"ok": False, "issue": None})(),
    )

    assert widgets._icon_diagnostic("missing.icon").code == "missing_icon"


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

    state = resolve_slot_render_state(item, registry)

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

    state = resolve_slot_render_state(item, registry)

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

    state = resolve_slot_render_state(
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

    state = resolve_slot_render_state(
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

    state = resolve_slot_render_state(
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

    refreshed = widgets._apply_slot_render_state(
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


def test_apply_slot_render_state_skips_active_drag_source(monkeypatch) -> None:
    monkeypatch.setattr(widgets, "load", build_qt_binding)
    button = FakeButton("drag.source", label="Move", key_label="1")
    button.setProperty("actionRailSlotDragSource", "true")
    refreshed = widgets._apply_slot_render_state(
        button,
        SlotRenderState(
            label="Move",
            key_label="1",
            icon="maya.move",
            icon_path="",
            icon_name="move_M.png",
            tone="neutral",
            tooltip="Move tool",
            enabled=True,
            active=True,
        ),
    )

    assert refreshed == 0
    assert button.property("actionRailLabel") == "Move"
    assert button.property("actionRailIconName") == ""


def test_apply_slot_render_state_ignores_tooltip_access_errors(monkeypatch) -> None:
    monkeypatch.setattr(widgets, "load", build_qt_binding)

    class TooltipButton(BuildButton):
        def toolTip(self) -> str:  # noqa: N802
            raise RuntimeError("deleted")

        def setToolTip(self, _tooltip: str) -> None:  # noqa: N802
            raise RuntimeError("deleted")

    refreshed = widgets._apply_slot_render_state(
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

    assert widgets._apply_button_icon(button, "") == 1
    assert widgets._apply_button_icon(button, "") == 0
    assert widgets._apply_button_icon(button, "icons/test.svg") == 1
    assert button.icon_size.width == 32
    assert button.icon_size.height == 32
    assert widgets._apply_button_icon(button, "", "move_M.png") == 1
    assert button.icons[-1].path == ":/move_M.png"
    assert button.property("actionRailAppliedIconSource") == ":/move_M.png"
    assert widgets._apply_button_icon(button, "", ":/rotate_M.png") == 1
    assert button.icons[-1].path == ":/rotate_M.png"

    class FailingIconButton(BuildButton):
        def property(self, _name: str) -> object:
            raise RuntimeError("deleted")

        def setIcon(self, _icon) -> None:  # noqa: N802
            raise RuntimeError("deleted")

    assert widgets._apply_button_icon(FailingIconButton("Icon"), "icons/test.svg") == 0


def test_set_button_property_and_diagnostic_tooltip_helpers() -> None:
    class BrokenPropertyButton:
        def property(self, _name: str) -> object:
            raise RuntimeError("deleted")

        def setProperty(self, _name: str, _value: object) -> None:  # noqa: N802
            raise RuntimeError("deleted")

    assert widgets._set_button_property(BrokenPropertyButton(), "name", "value") == 0
    assert (
        widgets._diagnostic_tooltip("", widgets._SlotDiagnostic(message="Problem"))
        == "Problem"
    )
    assert widgets._scaled_theme(widgets.DEFAULT_THEME, 1.0) is widgets.DEFAULT_THEME
