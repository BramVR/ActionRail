from __future__ import annotations

import sys
import types
from typing import Any

import pytest

import actionrail.overlay as overlay
from actionrail.overlay import (
    _anchored_position,
    _map_to_global,
    _qt_widget_identity,
    _qt_widget_is_valid,
    _rendered_key_labels,
    _ResizeEventFilter,
    _viewport_area_widget,
    _widget_dimension,
    active_model_panel,
    cleanup_overlay_widgets,
    maya_main_window,
    model_panel_widget,
)
from actionrail.spec import RailLayout, StackItem, StackSpec


class FakeCmds:
    def __init__(
        self,
        *,
        focused: str | None = None,
        visible_panels: list[str] | None = None,
        model_panels: list[str] | None = None,
    ) -> None:
        self.focused = focused
        self.visible_panels = visible_panels or []
        self.model_panels = model_panels or []

    def getPanel(self, **kwargs: object) -> object:  # noqa: N802
        if kwargs.get("withFocus"):
            return self.focused
        if "typeOf" in kwargs:
            panel = kwargs["typeOf"]
            return "modelPanel" if panel in self.model_panels else "scriptedPanel"
        if kwargs.get("visiblePanels"):
            return self.visible_panels
        if kwargs.get("type") == "modelPanel":
            return self.model_panels
        return None


def test_anchored_position_supports_common_viewport_anchors() -> None:
    assert _anchored_position("viewport.left.center", 800, 600, 40, 196, 12) == (12, 202)
    assert _anchored_position("viewport.right.top", 800, 600, 40, 196, 12) == (748, 12)
    assert _anchored_position("viewport.bottom.center", 800, 600, 200, 40, 12) == (300, 548)


def test_active_model_panel_prefers_focused_model_panel() -> None:
    cmds = FakeCmds(
        focused="modelPanel4",
        visible_panels=["modelPanel1"],
        model_panels=["modelPanel1", "modelPanel4"],
    )

    assert active_model_panel(cmds) == "modelPanel4"


def test_active_model_panel_falls_back_to_visible_model_panel() -> None:
    cmds = FakeCmds(
        focused="outlinerPanel1",
        visible_panels=["scriptEditorPanel1", "modelPanel2"],
        model_panels=["modelPanel2", "modelPanel3"],
    )

    assert active_model_panel(cmds) == "modelPanel2"


def test_active_model_panel_falls_back_to_any_model_panel() -> None:
    cmds = FakeCmds(
        focused="outlinerPanel1",
        visible_panels=["scriptEditorPanel1"],
        model_panels=["modelPanel3"],
    )

    assert active_model_panel(cmds) == "modelPanel3"


def test_active_model_panel_raises_when_no_model_panel_exists() -> None:
    cmds = FakeCmds(focused="outlinerPanel1", visible_panels=["scriptEditorPanel1"])

    with pytest.raises(RuntimeError, match="No Maya modelPanel"):
        active_model_panel(cmds)


def test_cleanup_overlay_widgets_closes_owning_host_before_delete() -> None:
    closed: list[bool] = []

    class FakeHost:
        def close(self) -> None:
            closed.append(True)

    class FakeQt:
        class QtWidgets:
            QWidget = object

            class QApplication:
                @staticmethod
                def instance() -> None:
                    return None

    class FakeWidget:
        def __init__(self, object_name: str) -> None:
            self._object_name = object_name
            self._actionrail_host = FakeHost()
            self.deleted = False

        def objectName(self) -> str:  # noqa: N802
            return self._object_name

        def hide(self) -> None:
            raise AssertionError("owning host should close the stale widget")

        def setParent(self, _parent: object) -> None:  # noqa: N802
            raise AssertionError("owning host should close the stale widget")

        def deleteLater(self) -> None:  # noqa: N802
            self.deleted = True

    class FakeParent:
        def __init__(self, children: list[FakeWidget]) -> None:
            self.children = children

        def objectName(self) -> str:  # noqa: N802
            return "modelPanel4"

        def findChildren(self, _widget_type: object) -> list[FakeWidget]:  # noqa: N802
            return self.children

    stale = FakeWidget("ActionRailViewportOverlay_transform_stack")

    removed = cleanup_overlay_widgets(FakeParent([stale]), "transform_stack", FakeQt)

    assert removed == 1
    assert closed == [True]
    assert stale.deleted is False


def test_cleanup_overlay_widgets_finds_floating_widget_from_qapplication() -> None:
    class FakeWidget:
        def __init__(self, object_name: str) -> None:
            self._object_name = object_name
            self.hidden = False
            self.parent = object()
            self.deleted = False

        def objectName(self) -> str:  # noqa: N802
            return self._object_name

        def hide(self) -> None:
            self.hidden = True

        def setParent(self, parent: object | None) -> None:  # noqa: N802
            self.parent = parent

        def deleteLater(self) -> None:  # noqa: N802
            self.deleted = True

    class FakeApp:
        def __init__(self, widgets: list[FakeWidget]) -> None:
            self._widgets = widgets

        def allWidgets(self) -> list[FakeWidget]:  # noqa: N802
            return self._widgets

        def sendPostedEvents(self, *_args: object) -> None:  # noqa: N802
            return None

    class FakeQt:
        class QtCore:
            class QEvent:
                DeferredDelete = object()

        class QtWidgets:
            QWidget = object
            app: FakeApp | None = None

            class QApplication:
                @staticmethod
                def instance() -> FakeApp | None:
                    return FakeQt.QtWidgets.app

    class FakeParent:
        def objectName(self) -> str:  # noqa: N802
            return "modelPanel4"

        def findChildren(self, _widget_type: object) -> list[object]:  # noqa: N802
            return []

    stale = FakeWidget("ActionRailViewportOverlay_transform_stack")
    FakeQt.QtWidgets.app = FakeApp([stale])

    removed = cleanup_overlay_widgets(FakeParent(), "transform_stack", FakeQt)

    assert removed == 1
    assert stale.hidden is True
    assert stale.parent is None
    assert stale.deleted is True


def test_cleanup_overlay_widgets_deletes_when_owning_host_close_fails() -> None:
    class FakeHost:
        def close(self) -> None:
            raise RuntimeError("close failed")

    class FakeQt:
        class QtWidgets:
            QWidget = object

            class QApplication:
                @staticmethod
                def instance() -> None:
                    return None

    class FakeWidget:
        def __init__(self) -> None:
            self._actionrail_host = FakeHost()
            self.deleted = False

        def objectName(self) -> str:  # noqa: N802
            return "ActionRailViewportOverlay_transform_stack"

        def hide(self) -> None:
            return None

        def setParent(self, _parent: object | None) -> None:  # noqa: N802
            return None

        def deleteLater(self) -> None:  # noqa: N802
            self.deleted = True

    class FakeParent:
        def __init__(self, children: list[FakeWidget]) -> None:
            self.children = children

        def objectName(self) -> str:  # noqa: N802
            return "modelPanel4"

        def findChildren(self, _widget_type: object) -> list[FakeWidget]:  # noqa: N802
            return self.children

    stale = FakeWidget()

    removed = cleanup_overlay_widgets(FakeParent([stale]), "transform_stack", FakeQt)

    assert removed == 1
    assert stale.deleted is True


def test_overlay_snapshot_uses_resolved_panel(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class FakeQt:
        class QtCore:
            class Qt:
                Widget = 0

    class FakeWidget:
        def setObjectName(self, name: str) -> None:  # noqa: N802
            captured["object_name"] = name

        def setParent(self, parent: object) -> None:  # noqa: N802
            captured["parent"] = parent

        def setWindowFlags(self, flags: object) -> None:  # noqa: N802
            captured["window_flags"] = flags

        def hide(self) -> None:
            captured["hidden"] = True

    class FakeParent:
        def installEventFilter(self, event_filter: object) -> None:  # noqa: N802
            captured["event_filter"] = event_filter

    class FakeResizeEventFilter:
        object = object()

        def __init__(self, host: object) -> None:
            captured["resize_host"] = host

    def fake_snapshot(cmds_module: object, active_panel: str | None = None) -> object:
        captured["snapshot_cmds"] = cmds_module
        captured["snapshot_active_panel"] = active_panel
        return object()

    def fake_build_transform_stack(
        spec: StackSpec,
        registry: object,
        *,
        state_snapshot: object | None = None,
        cmds_module: object | None = None,
    ) -> FakeWidget:
        captured["build_state_snapshot"] = state_snapshot
        captured["build_cmds"] = cmds_module
        return FakeWidget()

    monkeypatch.setattr(overlay, "load", lambda: FakeQt)
    monkeypatch.setattr(overlay, "snapshot", fake_snapshot)
    monkeypatch.setattr(overlay, "build_transform_stack", fake_build_transform_stack)
    monkeypatch.setattr(overlay, "_ResizeEventFilter", FakeResizeEventFilter)

    cmds = FakeCmds(
        focused="outlinerPanel1",
        visible_panels=["modelPanel2"],
        model_panels=["modelPanel2"],
    )
    parent = FakeParent()
    spec = StackSpec(
        id="predicate_panel_regression",
        layout=RailLayout(anchor="viewport.left.center"),
        items=(),
    )

    host = overlay.ViewportOverlayHost(spec, parent=parent, registry=object(), cmds_module=cmds)

    assert host.panel == "modelPanel2"
    assert captured["snapshot_cmds"] is cmds
    assert captured["snapshot_active_panel"] == "modelPanel2"
    assert captured["build_cmds"] is cmds
    assert captured["parent"] is parent


def test_overlay_uses_floating_maya_window_parent(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class FakeQt:
        class QtCore:
            class Qt:
                Widget = 0
                Tool = 1
                FramelessWindowHint = 2
                NoDropShadowWindowHint = 4
                WindowDoesNotAcceptFocus = 8
                WA_ShowWithoutActivating = 16

    class FakeWidget:
        def setObjectName(self, name: str) -> None:  # noqa: N802
            captured["object_name"] = name

        def setParent(self, parent: object) -> None:  # noqa: N802
            captured["widget_parent"] = parent

        def setWindowFlags(self, flags: object) -> None:  # noqa: N802
            captured["window_flags"] = flags

        def setAttribute(self, attribute: object, enabled: bool) -> None:  # noqa: N802
            captured["show_without_activating"] = (attribute, enabled)

        def hide(self) -> None:
            captured["hidden"] = True

    class FakeEventTarget:
        def __init__(self, name: str) -> None:
            self.name = name

        def installEventFilter(self, event_filter: object) -> None:  # noqa: N802
            captured.setdefault("event_targets", []).append((self.name, event_filter))

    class FakeResizeEventFilter:
        object = object()

        def __init__(self, host: object) -> None:
            captured["resize_host"] = host

    def fake_build_transform_stack(
        spec: StackSpec,
        registry: object,
        *,
        state_snapshot: object | None = None,
        cmds_module: object | None = None,
    ) -> FakeWidget:
        return FakeWidget()

    monkeypatch.setattr(overlay, "load", lambda: FakeQt)
    monkeypatch.setattr(overlay, "snapshot", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(overlay, "build_transform_stack", fake_build_transform_stack)
    monkeypatch.setattr(overlay, "_ResizeEventFilter", FakeResizeEventFilter)

    cmds = FakeCmds(
        focused="modelPanel2",
        visible_panels=["modelPanel2"],
        model_panels=["modelPanel2"],
    )
    parent = FakeEventTarget("viewport")
    window_parent = FakeEventTarget("maya_window")
    monkeypatch.setattr(overlay, "maya_main_window", lambda _qt: window_parent)
    spec = StackSpec(
        id="floating_parent_regression",
        layout=RailLayout(anchor="viewport.left.center"),
        items=(),
    )

    host = overlay.ViewportOverlayHost(spec, parent=parent, registry=object(), cmds_module=cmds)

    assert host.window_parent is window_parent
    assert captured["widget_parent"] is window_parent
    assert captured["window_flags"] == 15
    assert captured["show_without_activating"] == (16, True)
    assert captured["event_targets"] == [
        ("viewport", FakeResizeEventFilter.object),
        ("maya_window", FakeResizeEventFilter.object),
    ]


def test_overlay_starts_predicate_refresh_timer_and_stops_on_close(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {"refreshes": 0}

    class FakeSize:
        def __init__(self, width: int, height: int) -> None:
            self._width = width
            self._height = height

        def width(self) -> int:
            return self._width

        def height(self) -> int:
            return self._height

    class FakeRect(FakeSize):
        pass

    class FakeSignal:
        def __init__(self) -> None:
            self.callback = None

        def connect(self, callback: object) -> None:
            self.callback = callback

        def emit(self) -> None:
            assert self.callback is not None
            self.callback()

    class FakeTimer:
        instances: list[FakeTimer] = []

        def __init__(self) -> None:
            self.timeout = FakeSignal()
            self.interval = 0
            self.timer_type = None
            self.started = False
            self.stopped = False
            self.deleted = False
            FakeTimer.instances.append(self)

        def setInterval(self, interval: int) -> None:  # noqa: N802
            self.interval = interval

        def setTimerType(self, timer_type: object) -> None:  # noqa: N802
            self.timer_type = timer_type

        def start(self) -> None:
            self.started = True

        def stop(self) -> None:
            self.stopped = True

        def deleteLater(self) -> None:  # noqa: N802
            self.deleted = True

    class FakeQt:
        class QtCore:
            class Qt:
                Widget = 0
                CoarseTimer = 1

            QTimer = FakeTimer

        class QtWidgets:
            QWidget = object

    class FakeWidget:
        def __init__(self) -> None:
            self.visible = False
            self.deleted = False

        def setObjectName(self, name: str) -> None:  # noqa: N802
            captured["object_name"] = name

        def setParent(self, parent: object | None) -> None:  # noqa: N802
            captured["parent"] = parent

        def setWindowFlags(self, flags: object) -> None:  # noqa: N802
            captured["window_flags"] = flags

        def hide(self) -> None:
            self.visible = False

        def show(self) -> None:
            self.visible = True

        def raise_(self) -> None:
            captured["raised"] = True

        def isVisible(self) -> bool:  # noqa: N802
            return self.visible

        def sizeHint(self) -> FakeSize:  # noqa: N802
            return FakeSize(46, 138)

        def move(self, x_pos: int, y_pos: int) -> None:
            captured["move"] = (x_pos, y_pos)

        def deleteLater(self) -> None:  # noqa: N802
            self.deleted = True

    class FakeParent:
        def rect(self) -> FakeRect:
            return FakeRect(800, 600)

        def installEventFilter(self, event_filter: object) -> None:  # noqa: N802
            captured["installed_filter"] = event_filter

        def removeEventFilter(self, event_filter: object) -> None:  # noqa: N802
            captured["removed_filter"] = event_filter

        def objectName(self) -> str:  # noqa: N802
            return ""

        def findChildren(self, _widget_type: object) -> list[object]:  # noqa: N802
            return []

    class FakeResizeEventFilter:
        object = object()

        def __init__(self, host: object) -> None:
            captured["resize_host"] = host

    def fake_refresh_predicate_state(*_args: object, **_kwargs: object) -> object:
        captured["refreshes"] = int(captured["refreshes"]) + 1
        return overlay.PredicateRefreshResult(
            refreshed=1,
            needs_rebuild=False,
            visible_slot_ids=(),
            rendered_slot_ids=(),
        )

    monkeypatch.setattr(overlay, "load", lambda: FakeQt)
    monkeypatch.setattr(overlay, "snapshot", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(overlay, "build_transform_stack", lambda *_args, **_kwargs: FakeWidget())
    monkeypatch.setattr(overlay, "refresh_predicate_state", fake_refresh_predicate_state)
    monkeypatch.setattr(overlay, "_ResizeEventFilter", FakeResizeEventFilter)

    cmds = FakeCmds(
        focused="modelPanel2",
        visible_panels=["modelPanel2"],
        model_panels=["modelPanel2"],
    )
    spec = StackSpec(
        id="timer_refresh_regression",
        layout=RailLayout(anchor="viewport.left.center"),
        items=(
            StackItem(
                type="button",
                id="timer_refresh.button",
                label="TR",
                enabled_when="selection.count > 0",
            ),
        ),
    )

    host = overlay.ViewportOverlayHost(
        spec,
        parent=FakeParent(),
        registry=object(),
        cmds_module=cmds,
        predicate_refresh_interval_ms=500,
    )

    host.show()
    timer = FakeTimer.instances[-1]
    timer.timeout.emit()
    host.close()

    assert timer.interval == 500
    assert timer.timer_type == 1
    assert timer.started is True
    assert captured["refreshes"] == 1
    assert timer.stopped is True
    assert timer.deleted is True


def test_position_ignores_deleted_qt_widget(monkeypatch: pytest.MonkeyPatch) -> None:
    class DeletedWidget:
        def sizeHint(self) -> object:  # noqa: N802
            raise RuntimeError("Internal C++ object already deleted")

    class FakeParent:
        def rect(self) -> object:
            raise AssertionError("position should return before reading parent geometry")

    host = object.__new__(overlay.ViewportOverlayHost)
    host.widget = DeletedWidget()
    host.parent = FakeParent()
    host.qt = object()

    monkeypatch.setattr(
        overlay,
        "_qt_widget_is_valid",
        lambda widget: not isinstance(widget, DeletedWidget),
    )

    host.position()


def test_viewport_area_widget_prefers_large_inset_panel_child() -> None:
    class FakeQt:
        class QtWidgets:
            QWidget = object

    class FakeWidget:
        def __init__(
            self,
            *,
            name: str = "modelPanel4",
            x_pos: int = 0,
            y_pos: int = 0,
            width: int = 0,
            height: int = 0,
            children: list[Any] | None = None,
        ) -> None:
            self._name = name
            self._x = x_pos
            self._y = y_pos
            self._width = width
            self._height = height
            self._children = children or []

        def x(self) -> int:
            return self._x

        def y(self) -> int:
            return self._y

        def width(self) -> int:
            return self._width

        def height(self) -> int:
            return self._height

        def findChildren(self, _widget_type: object, name: str) -> list[Any]:  # noqa: N802
            return [child for child in self._children if child._name == name]

    tiny_stack = FakeWidget(width=98, height=0)
    inner_viewport = FakeWidget(x_pos=1, y_pos=22, width=1957, height=1086)
    outer_panel = FakeWidget(
        width=1959,
        height=1109,
        children=[tiny_stack, inner_viewport],
    )

    assert _viewport_area_widget(outer_panel, "modelPanel4", FakeQt) is inner_viewport
    assert inner_viewport._actionrail_outer_panel_widget is outer_panel


def test_overlay_import_boundaries_and_maya_widget_lookup(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(RuntimeError, match="require maya.cmds"):
        overlay._require_cmds()

    fake_cmds_module = types.ModuleType("maya.cmds")
    fake_maya = types.ModuleType("maya")
    fake_maya.__path__ = []
    fake_maya.cmds = fake_cmds_module
    monkeypatch.setitem(sys.modules, "maya", fake_maya)
    monkeypatch.setitem(sys.modules, "maya.cmds", fake_cmds_module)
    assert overlay._require_cmds() is fake_cmds_module

    class FakeQt:
        class QtWidgets:
            QWidget = object

        @staticmethod
        def wrap_instance(pointer: int, base: object) -> object:
            return {"pointer": pointer, "base": base}

    class FakeMQtUtil:
        @staticmethod
        def mainWindow() -> int:  # noqa: N802
            return 123

        @staticmethod
        def findControl(name: str) -> int:  # noqa: N802
            return 456 if name == "editor" else 0

        @staticmethod
        def findLayout(name: str) -> int:  # noqa: N802
            return 0

    fake_omui = types.ModuleType("maya.OpenMayaUI")
    fake_omui.MQtUtil = FakeMQtUtil
    fake_maya.OpenMayaUI = fake_omui
    monkeypatch.setitem(sys.modules, "maya.OpenMayaUI", fake_omui)
    monkeypatch.setattr(overlay, "load", lambda: FakeQt)

    class ModelCmds:
        def modelPanel(self, panel: str, **kwargs: object) -> str:  # noqa: N802
            return "editor"

    assert model_panel_widget("modelPanel4", ModelCmds())["pointer"] == 456
    assert maya_main_window(FakeQt)["pointer"] == 123

    class NoPointerMQtUtil(FakeMQtUtil):
        @staticmethod
        def mainWindow() -> int:  # noqa: N802
            return 0

        @staticmethod
        def findControl(name: str) -> int:  # noqa: N802
            return 0

    fake_omui.MQtUtil = NoPointerMQtUtil
    assert maya_main_window(FakeQt) is None
    with pytest.raises(RuntimeError, match="Unable to locate"):
        model_panel_widget("modelPanel4", ModelCmds())


def test_viewport_widget_and_qt_identity_helpers(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeQt:
        class QtWidgets:
            QWidget = object

    class BrokenWidget:
        def width(self) -> int:
            raise RuntimeError("deleted")

        def findChildren(self, *_args: object) -> list[object]:  # noqa: N802
            raise RuntimeError("deleted")

    widget = BrokenWidget()
    assert _viewport_area_widget(object(), "modelPanel4", FakeQt) is not None
    assert _viewport_area_widget(widget, "modelPanel4", FakeQt) is widget
    assert _widget_dimension(object(), "width") == 0
    assert _widget_dimension(widget, "width") == 0
    assert _qt_widget_is_valid(widget) is True
    assert _qt_widget_identity(widget) == id(widget)

    shiboken6 = types.ModuleType("shiboken6")
    shiboken6.isValid = lambda _widget: False
    shiboken6.getCppPointer = lambda _widget: (789,)
    monkeypatch.setitem(sys.modules, "shiboken6", shiboken6)
    assert _qt_widget_is_valid(widget) is False
    assert _qt_widget_identity(widget) == 789

    shiboken6.isValid = lambda _widget: (_ for _ in ()).throw(RuntimeError("deleted"))
    shiboken6.getCppPointer = lambda _widget: (_ for _ in ()).throw(RuntimeError("deleted"))
    assert _qt_widget_is_valid(widget) is False
    assert _qt_widget_identity(widget) == id(widget)


def test_resize_event_filter_positions_host_on_geometry_events(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    positioned = []

    class FakeQt:
        class QtCore:
            class QEvent:
                Move = 1
                Resize = 2
                Show = 3
                LayoutRequest = 4
                WindowStateChange = 5

            class QObject:
                pass

    monkeypatch.setattr(overlay, "load", lambda: FakeQt)

    class Host:
        def position(self) -> None:
            positioned.append(True)

    class Event:
        def __init__(self, event_type: int) -> None:
            self._event_type = event_type

        def type(self) -> int:
            return self._event_type

    host = Host()
    event_filter = _ResizeEventFilter(host).object

    assert event_filter.eventFilter(object(), Event(1)) is False
    assert event_filter.eventFilter(object(), Event(999)) is False
    assert positioned == [True]


def test_cleanup_helpers_handle_invalid_roots_and_close_failures() -> None:
    class FakeQt:
        class QtWidgets:
            QWidget = object

            class QApplication:
                @staticmethod
                def instance() -> object:
                    raise RuntimeError("app deleted")

    class BadRoot:
        def findChildren(self, *_args: object) -> list[object]:  # noqa: N802
            raise RuntimeError("deleted")

    class BadWidget:
        def objectName(self) -> str:  # noqa: N802
            raise RuntimeError("deleted")

    class DeleteFailWidget:
        def objectName(self) -> str:  # noqa: N802
            return f"{overlay.OBJECT_NAME_PREFIX}_spec"

        def hide(self) -> None:
            raise RuntimeError("deleted")

    bad_root = BadRoot()
    assert list(overlay._iter_widget_candidates(None, FakeQt.QtWidgets)) == []
    assert list(overlay._iter_widget_candidates(bad_root, FakeQt.QtWidgets)) == [bad_root]
    assert overlay._stale_overlay_widgets(BadWidget(), "spec", FakeQt) == []
    assert overlay._close_stale_widget(DeleteFailWidget()) is False
    assert overlay._cleanup_search_roots(object(), FakeQt)


def test_model_panel_widget_handles_missing_editor_and_main_window_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeQt:
        class QtWidgets:
            QWidget = object

        @staticmethod
        def wrap_instance(pointer: int, base: object) -> object:
            return {"pointer": pointer, "base": base}

    class FakeMQtUtil:
        @staticmethod
        def mainWindow() -> int:  # noqa: N802
            raise RuntimeError("main missing")

        @staticmethod
        def findControl(name: str) -> int:  # noqa: N802
            return 321 if name == "modelPanel4" else 0

        @staticmethod
        def findLayout(name: str) -> int:  # noqa: N802
            return 0

    fake_maya = types.ModuleType("maya")
    fake_omui = types.ModuleType("maya.OpenMayaUI")
    fake_omui.MQtUtil = FakeMQtUtil
    fake_maya.OpenMayaUI = fake_omui
    monkeypatch.setitem(sys.modules, "maya", fake_maya)
    monkeypatch.setitem(sys.modules, "maya.OpenMayaUI", fake_omui)
    monkeypatch.setattr(overlay, "load", lambda: FakeQt)

    class BrokenEditorCmds:
        def modelPanel(self, panel: str, **kwargs: object) -> str:  # noqa: N802
            raise RuntimeError("editor missing")

    assert model_panel_widget("modelPanel4", BrokenEditorCmds())["pointer"] == 321
    assert maya_main_window(FakeQt) is None


def test_viewport_area_widget_returns_outer_panel_without_large_candidates() -> None:
    class FakeQt:
        class QtWidgets:
            QWidget = object

    class TinyWidget:
        def width(self) -> int:
            return 50

        def height(self) -> int:
            return 50

    class OuterWidget(TinyWidget):
        def findChildren(self, *_args: object) -> list[object]:  # noqa: N802
            return [TinyWidget()]

    outer = OuterWidget()

    assert _viewport_area_widget(outer, "modelPanel4", FakeQt) is outer


def test_resize_event_filter_ignores_deleted_host(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeQt:
        class QtCore:
            class QEvent:
                Move = 1
                Resize = 2
                Show = 3
                LayoutRequest = 4
                WindowStateChange = 5

            class QObject:
                pass

    monkeypatch.setattr(overlay, "load", lambda: FakeQt)

    class Host:
        def position(self) -> None:
            raise AssertionError("host should be gone")

    event_filter = _ResizeEventFilter(Host()).object

    event = type("Event", (), {"type": lambda self: 1})()

    assert event_filter.eventFilter(object(), event) is False


def test_stale_widget_helpers_dedupe_outer_roots_and_invalid_widgets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(overlay, "_qt_widget_identity", id)

    class FakeQt:
        class QtWidgets:
            QWidget = object

    class Widget:
        def __init__(self, name: str, children: list[object] | None = None) -> None:
            self.name = name
            self.children = children or []

        def objectName(self) -> str:  # noqa: N802
            return self.name

        def findChildren(self, *_args: object) -> list[object]:  # noqa: N802
            return self.children

    stale = Widget(f"{overlay.OBJECT_NAME_PREFIX}_spec")
    outer = Widget("outer", [stale])
    parent = Widget("parent", [stale])
    parent._actionrail_outer_panel_widget = outer

    stale_widgets = overlay._stale_overlay_widgets(parent, "spec", FakeQt)

    assert stale_widgets == [stale]
    monkeypatch.setattr(overlay, "_qt_widget_is_valid", lambda widget: widget is not stale)
    assert overlay._stale_overlay_widgets(parent, "spec", FakeQt) == []
    monkeypatch.setattr(overlay, "_qt_widget_is_valid", lambda _widget: False)
    assert overlay._stale_overlay_widgets(parent, "spec", FakeQt) == []
    assert overlay._close_stale_widget(stale) is False


def test_install_event_filter_ignores_install_errors() -> None:
    host = object.__new__(overlay.ViewportOverlayHost)
    host._filter_targets = []
    host._resize_filter = type("Filter", (), {"object": object()})()

    class BrokenTarget:
        def installEventFilter(self, _filter: object) -> None:  # noqa: N802
            raise RuntimeError("deleted")

    host._install_event_filter(BrokenTarget())

    assert host._filter_targets == []


def test_host_position_close_rebuild_and_timer_edge_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    class Size:
        def __init__(self, width: int, height: int) -> None:
            self._width = width
            self._height = height

        def width(self) -> int:
            return self._width

        def height(self) -> int:
            return self._height

    class Rect(Size):
        pass

    class Point:
        def __init__(self, x_pos: int, y_pos: int) -> None:
            self.x_pos = x_pos
            self.y_pos = y_pos

    class FakeQt:
        class QtCore:
            class Qt:
                Widget = 0
                Tool = 1
                FramelessWindowHint = 2

            QPoint = Point

        class QtWidgets:
            QWidget = object
            QPushButton = object

    class Parent:
        def __init__(self) -> None:
            self.removed = []

        def rect(self) -> Rect:
            return Rect(800, 600)

        def mapToGlobal(self, point: Point) -> tuple[int, int]:  # noqa: N802
            return (point.x_pos + 10, point.y_pos + 20)

        def removeEventFilter(self, event_filter: object) -> None:  # noqa: N802
            self.removed.append(event_filter)

    class Widget:
        def __init__(self, visible: bool = True) -> None:
            self.visible = visible
            self.deleted = False
            self.parent = object()
            self.moved = None
            self.children = []

        def sizeHint(self) -> Size:  # noqa: N802
            return Size(0, 0)

        def adjustSize(self) -> None:  # noqa: N802
            self.adjusted = True

        def size(self) -> Size:
            return Size(40, 100)

        def move(self, *args: object) -> None:
            self.moved = args

        def isVisible(self) -> bool:  # noqa: N802
            return self.visible

        def hide(self) -> None:
            self.visible = False

        def show(self) -> None:
            self.visible = True

        def raise_(self) -> None:
            return None

        def setParent(self, parent: object | None) -> None:  # noqa: N802
            self.parent = parent

        def setWindowFlags(self, flags: object) -> None:  # noqa: N802
            self.flags = flags

        def setAttribute(self, *args: object) -> None:  # noqa: N802
            self.attribute = args

        def setObjectName(self, name: str) -> None:  # noqa: N802
            self.name = name

        def deleteLater(self) -> None:  # noqa: N802
            self.deleted = True

        def findChildren(self, _type: object) -> list[object]:  # noqa: N802
            return self.children

    parent = Parent()
    spec = StackSpec(
        id="spec",
        layout=RailLayout(anchor="viewport.right.bottom", offset=(1, 2)),
        items=(StackItem(type="button", id="spec.button", label="B", visible_when="true"),),
    )
    host = object.__new__(overlay.ViewportOverlayHost)
    host.qt = FakeQt
    host.cmds = object()
    host.spec = spec
    host.panel = "modelPanel4"
    host.parent = parent
    host.window_parent = object()
    host.registry = object()
    host.margin = 12
    host.predicate_refresh_interval_ms = 0
    host._floating = True
    host.widget = Widget()
    host._resize_filter = type("Filter", (), {"object": object()})()
    host._filter_targets = [parent]
    host._predicate_refresh_timer = None

    host.position()
    assert host.widget.moved == ((759, 510),)

    host.parent = None
    host.position()
    host.widget = None
    assert host.update_slot_key_label("slot", "K") == 0
    host._start_predicate_refresh_timer()

    host.widget = Widget()
    monkeypatch.setattr(overlay, "snapshot", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(
        overlay,
        "refresh_predicate_state",
        lambda *_args, **_kwargs: overlay.PredicateRefreshResult(0, True, (), ()),
    )
    rebuilt = Widget(visible=False)
    monkeypatch.setattr(host, "_build_widget", lambda _state: rebuilt)
    monkeypatch.setattr(overlay, "set_slot_key_label", lambda *_args: 1)

    host.refresh_state()
    assert host.widget is rebuilt
    assert host.update_slot_key_label("spec.button", "K") == 1

    host.close()
    assert parent.removed


def test_rebuild_widget_restores_key_labels_and_visible_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeQt:
        class QtWidgets:
            QPushButton = object

    class Button:
        def property(self, name: str) -> object:
            return {"actionRailSlotId": "slot", "actionRailKeyLabel": "K"}[name]

    class OldWidget:
        def __init__(self) -> None:
            self.hidden = False
            self.deleted = False

        def isVisible(self) -> bool:  # noqa: N802
            return True

        def findChildren(self, _type: object) -> list[object]:  # noqa: N802
            return [Button()]

        def hide(self) -> None:
            self.hidden = True

        def setParent(self, _parent: object | None) -> None:  # noqa: N802
            return None

        def deleteLater(self) -> None:  # noqa: N802
            self.deleted = True

    class NewWidget:
        pass

    host = object.__new__(overlay.ViewportOverlayHost)
    host.qt = FakeQt
    host.widget = OldWidget()
    host._build_widget = lambda _state: NewWidget()
    shown = []
    host.show = lambda: shown.append(True)
    labels = []

    def set_slot_key_label(_widget: object, slot: str, key: str) -> int:
        labels.append((slot, key))
        return 1

    monkeypatch.setattr(overlay, "set_slot_key_label", set_slot_key_label)

    host._rebuild_widget(object())

    assert labels == [("slot", "K")]
    assert shown == [True]


def test_start_predicate_refresh_timer_early_exits(monkeypatch: pytest.MonkeyPatch) -> None:
    class QtWithoutTimer:
        class QtCore:
            pass

    spec_without_predicates = StackSpec(
        id="plain",
        layout=RailLayout(anchor="viewport.left.center"),
        items=(StackItem(type="button", id="plain.button", label="B"),),
    )
    spec_with_predicates = StackSpec(
        id="pred",
        layout=RailLayout(anchor="viewport.left.center"),
        items=(StackItem(type="button", id="pred.button", label="B", visible_when="true"),),
    )
    host = object.__new__(overlay.ViewportOverlayHost)
    host.predicate_refresh_interval_ms = 0
    host._predicate_refresh_timer = None
    host.spec = spec_with_predicates
    host.qt = QtWithoutTimer
    host._start_predicate_refresh_timer()
    assert host._predicate_refresh_timer is None

    host.predicate_refresh_interval_ms = 250
    host._predicate_refresh_timer = object()
    host._start_predicate_refresh_timer()
    assert host._predicate_refresh_timer is not None

    host._predicate_refresh_timer = None
    host.spec = spec_without_predicates
    host._start_predicate_refresh_timer()
    assert host._predicate_refresh_timer is None

    host.spec = spec_with_predicates
    host._start_predicate_refresh_timer()
    assert host._predicate_refresh_timer is None


def test_timer_and_rendered_key_label_helpers(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeQt:
        class QtWidgets:
            QPushButton = object

    class Button:
        def __init__(self, slot_id: object, key_label: object) -> None:
            self.values = {
                "actionRailSlotId": slot_id,
                "actionRailKeyLabel": key_label,
            }

        def property(self, name: str) -> object:
            return self.values[name]

    class Widget:
        def __init__(self, raises: bool = False) -> None:
            self.raises = raises

        def findChildren(self, _type: object) -> list[object]:  # noqa: N802
            if self.raises:
                raise RuntimeError("deleted")
            return [Button("slot", "K"), Button("empty", ""), Button(123, "X")]

    assert _rendered_key_labels(None, FakeQt) == {}
    assert _rendered_key_labels(Widget(True), FakeQt) == {}
    assert _rendered_key_labels(Widget(), FakeQt) == {"slot": "K"}

    class Host:
        def __init__(self) -> None:
            self.widget = None
            self.stopped = False

        def _stop_predicate_refresh_timer(self) -> None:
            self.stopped = True

        def refresh_state(self) -> None:
            raise RuntimeError("refresh failed")

    host = object.__new__(overlay.ViewportOverlayHost)
    host.widget = None
    host._stop_predicate_refresh_timer = lambda: setattr(host, "stopped", True)
    host._refresh_predicates_from_timer()
    assert host.stopped is True

    host.widget = type("Invisible", (), {"isVisible": lambda self: False})()
    host.stopped = False
    host._refresh_predicates_from_timer()
    assert host.stopped is False

    host.widget = type("Visible", (), {"isVisible": lambda self: True})()
    host.refresh_state = lambda: (_ for _ in ()).throw(RuntimeError("failed"))
    host._refresh_predicates_from_timer()
    assert host.stopped is True


def test_map_to_global_and_deferred_delete_helpers_handle_failures() -> None:
    class Qt:
        class QtCore:
            class QEvent:
                DeferredDelete = object()

            class QPoint:
                def __init__(self, x_pos: int, y_pos: int) -> None:
                    self.x_pos = x_pos
                    self.y_pos = y_pos

        class QtWidgets:
            class QApplication:
                @staticmethod
                def instance() -> object:
                    raise RuntimeError("app missing")

    class BrokenParent:
        def mapToGlobal(self, point: object) -> object:  # noqa: N802
            raise RuntimeError("deleted")

    point = _map_to_global(object(), 1, 2, Qt)
    assert point.x_pos == 1
    assert point.y_pos == 2
    assert _map_to_global(BrokenParent(), 3, 4, Qt).x_pos == 3
    overlay._flush_qt_deferred_deletes(Qt)

    class App:
        def sendPostedEvents(self, *_args: object) -> None:  # noqa: N802
            raise RuntimeError("deleted")

    class QtWithBrokenApp(Qt):
        class QtWidgets:
            class QApplication:
                @staticmethod
                def instance() -> object:
                    return App()

    overlay._flush_qt_deferred_deletes(QtWithBrokenApp)
