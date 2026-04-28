from __future__ import annotations

from typing import Any

import pytest

import actionrail.overlay as overlay
from actionrail.overlay import _anchored_position, _viewport_area_widget, active_model_panel
from actionrail.spec import RailLayout, StackSpec


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
