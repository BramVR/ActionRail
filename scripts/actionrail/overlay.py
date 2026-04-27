"""Viewport overlay host for ActionRail widgets."""

from __future__ import annotations

from typing import Any

from .actions import ActionRegistry, create_default_registry
from .qt import load
from .spec import StackSpec
from .widgets import build_transform_stack

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
    """Wrap Maya's model panel/editor Qt pointer as a QWidget."""

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

    return qt.wrap_instance(int(pointer), qt.QtWidgets.QWidget)


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
        self.spec = spec
        self.panel = panel or active_model_panel(cmds_module)
        self.parent = parent or model_panel_widget(self.panel, cmds_module)
        self.registry = registry or create_default_registry()
        self.margin = margin
        self.widget = build_transform_stack(spec, self.registry)
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
        x_pos = self.margin
        y_pos = max(self.margin, int((parent_rect.height() - size.height()) / 2))
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
