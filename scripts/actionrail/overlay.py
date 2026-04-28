"""Viewport overlay host for ActionRail widgets."""

from __future__ import annotations

from typing import Any

from .actions import ActionRegistry, create_default_registry
from .qt import load
from .spec import StackSpec
from .state import snapshot
from .widgets import build_transform_stack, set_slot_key_label

OBJECT_NAME_PREFIX = "ActionRailViewportOverlay"
DEFAULT_MARGIN = 12


def _require_cmds(cmds_module: Any | None = None) -> Any:
    if cmds_module is not None:
        return cmds_module

    try:
        import maya.cmds as cmds  # type: ignore[import-not-found]
    except Exception as exc:  # pragma: no cover - exercised only inside Maya.
        msg = "ActionRail viewport overlays require maya.cmds inside Maya."
        raise RuntimeError(msg) from exc
    return cmds


def active_model_panel(cmds_module: Any | None = None) -> str:
    """Return the active or first visible Maya model panel."""

    cmds = _require_cmds(cmds_module)

    focused = cmds.getPanel(withFocus=True)
    if focused and cmds.getPanel(typeOf=focused) == "modelPanel":
        return focused

    for panel in cmds.getPanel(visiblePanels=True) or []:
        if cmds.getPanel(typeOf=panel) == "modelPanel":
            return panel

    panels = cmds.getPanel(type="modelPanel") or []
    if panels:
        return panels[0]

    msg = "No Maya modelPanel is available for ActionRail."
    raise RuntimeError(msg)


def model_panel_widget(panel: str, cmds_module: Any | None = None) -> Any:
    """Wrap Maya's viewport-area widget for a model panel as a QWidget."""

    qt = load()
    cmds = _require_cmds(cmds_module)

    try:
        from maya import OpenMayaUI as omui  # type: ignore[import-not-found]
    except Exception as exc:  # pragma: no cover - exercised only inside Maya.
        msg = "ActionRail viewport overlays require maya.OpenMayaUI inside Maya."
        raise RuntimeError(msg) from exc

    pointers: list[Any] = []

    try:
        editor = cmds.modelPanel(panel, query=True, modelEditor=True)
    except Exception:
        editor = None

    if editor:
        pointers.append(omui.MQtUtil.findControl(editor))

    pointers.extend(
        [
            omui.MQtUtil.findControl(panel),
            omui.MQtUtil.findLayout(panel),
        ]
    )

    pointer = next((candidate for candidate in pointers if candidate), None)
    if not pointer:
        msg = f"Unable to locate Qt widget for Maya model panel: {panel}"
        raise RuntimeError(msg)

    panel_widget = qt.wrap_instance(int(pointer), qt.QtWidgets.QWidget)
    return _viewport_area_widget(panel_widget, panel, qt)


def _viewport_area_widget(panel_widget: Any, panel: str, qt: Any) -> Any:
    """Return the inner model-panel viewport widget when Maya exposes one.

    Maya can expose an outer model-panel widget that also owns the model-panel
    toolbar. Parenting a transparent overlay to that outer widget can leave
    transient paint artifacts when Maya repaints toolbar controls. The large
    inset child with the same object name is the viewport area used for stable
    overlay parenting.
    """

    find_children = getattr(panel_widget, "findChildren", None)
    if find_children is None:
        return panel_widget

    try:
        children = find_children(qt.QtWidgets.QWidget, panel)
    except Exception:
        return panel_widget

    candidates = [
        child
        for child in children or []
        if child is not panel_widget
        and _qt_widget_is_valid(child)
        and _widget_dimension(child, "width") > 100
        and _widget_dimension(child, "height") > 100
    ]
    if not candidates:
        return panel_widget

    parent_width = _widget_dimension(panel_widget, "width")
    parent_height = _widget_dimension(panel_widget, "height")

    def score(widget: Any) -> tuple[bool, int]:
        inset = (
            _widget_dimension(widget, "x") > 0
            or _widget_dimension(widget, "y") > 0
            or _widget_dimension(widget, "width") < parent_width
            or _widget_dimension(widget, "height") < parent_height
        )
        area = _widget_dimension(widget, "width") * _widget_dimension(widget, "height")
        return (inset, area)

    selected = max(candidates, key=score)
    selected._actionrail_outer_panel_widget = panel_widget
    return selected


def _widget_dimension(widget: Any, method_name: str) -> int:
    method = getattr(widget, method_name, None)
    if method is None:
        return 0
    try:
        return int(method())
    except Exception:
        return 0


def _qt_widget_is_valid(widget: Any) -> bool:
    try:
        from shiboken6 import isValid  # type: ignore[import-not-found]
    except Exception:
        try:
            from shiboken2 import isValid  # type: ignore[import-not-found,no-redef]
        except Exception:
            return True

    try:
        return bool(isValid(widget))
    except Exception:
        return False


class _ResizeEventFilter:
    """Qt event filter that keeps the rail positioned as the panel resizes."""

    def __init__(self, host: ViewportOverlayHost) -> None:
        qt = load()
        host_ref = host

        class _Filter(qt.QtCore.QObject):
            def eventFilter(self, watched: Any, event: Any) -> bool:  # noqa: N802
                event_type = event.type()
                if event_type in {
                    qt.QtCore.QEvent.Resize,
                    qt.QtCore.QEvent.Show,
                    qt.QtCore.QEvent.LayoutRequest,
                }:
                    host_ref.position()
                return False

        self._object = _Filter()

    @property
    def object(self) -> Any:
        return self._object


class ViewportOverlayHost:
    """Owns one ActionRail widget parented under a Maya model panel."""

    def __init__(
        self,
        spec: StackSpec,
        *,
        panel: str | None = None,
        parent: Any | None = None,
        registry: ActionRegistry | None = None,
        cmds_module: Any | None = None,
        margin: int = DEFAULT_MARGIN,
    ) -> None:
        self.qt = load()
        self.cmds = _require_cmds(cmds_module)
        self.spec = spec
        self.panel = panel or active_model_panel(self.cmds)
        self.parent = parent or model_panel_widget(self.panel, self.cmds)
        self.registry = registry or create_default_registry()
        self.margin = margin
        self.widget = build_transform_stack(
            spec,
            self.registry,
            state_snapshot=snapshot(self.cmds, active_panel=self.panel),
            cmds_module=self.cmds,
        )
        self.widget.setObjectName(f"{OBJECT_NAME_PREFIX}_{spec.id}")
        self.widget.setParent(self.parent)
        self.widget.setWindowFlags(self.qt.QtCore.Qt.Widget)
        self.widget.hide()
        self._resize_filter = _ResizeEventFilter(self)
        self.parent.installEventFilter(self._resize_filter.object)

    def show(self) -> None:
        self.position()
        self.widget.show()
        self.widget.raise_()

    def position(self) -> None:
        if self.widget is None or self.parent is None:
            return

        size = self.widget.sizeHint()
        if size.width() <= 0 or size.height() <= 0:
            self.widget.adjustSize()
            size = self.widget.size()

        parent_rect = self.parent.rect()
        x_pos, y_pos = _anchored_position(
            self.spec.anchor,
            parent_rect.width(),
            parent_rect.height(),
            size.width(),
            size.height(),
            self.margin,
        )
        x_pos += self.spec.layout.offset[0]
        y_pos += self.spec.layout.offset[1]
        self.widget.move(x_pos, y_pos)

    def close(self) -> None:
        if self.parent is not None and self._resize_filter is not None:
            self.parent.removeEventFilter(self._resize_filter.object)

        if self.widget is not None:
            self.widget.hide()
            self.widget.setParent(None)
            self.widget.deleteLater()

        self.widget = None
        self.parent = None
        self._resize_filter = None

    def update_slot_key_label(self, slot_id: str, key_label: str) -> int:
        """Update the key label for a rendered slot."""

        if self.widget is None:
            return 0
        return set_slot_key_label(self.widget, slot_id, key_label)


def _anchored_position(
    anchor: str,
    parent_width: int,
    parent_height: int,
    widget_width: int,
    widget_height: int,
    margin: int,
) -> tuple[int, int]:
    horizontal = "center"
    vertical = "center"

    parts = anchor.split(".")
    if "left" in parts:
        horizontal = "left"
    elif "right" in parts:
        horizontal = "right"

    if "top" in parts:
        vertical = "top"
    elif "bottom" in parts:
        vertical = "bottom"

    if horizontal == "left":
        x_pos = margin
    elif horizontal == "right":
        x_pos = parent_width - widget_width - margin
    else:
        x_pos = int((parent_width - widget_width) / 2)

    if vertical == "top":
        y_pos = margin
    elif vertical == "bottom":
        y_pos = parent_height - widget_height - margin
    else:
        y_pos = int((parent_height - widget_height) / 2)

    return max(margin, x_pos), max(margin, y_pos)
