from __future__ import annotations

from typing import Any

import pytest

import actionrail.overlay as overlay
from actionrail.overlay import (
    _anchored_position,
    _viewport_area_widget,
    active_model_panel,
    cleanup_overlay_widgets,
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
