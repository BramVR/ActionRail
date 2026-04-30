"""Viewport overlay host for ActionRail widgets.

Purpose: position small Qt rail windows from Maya model-panel geometry.
Owns: active panel lookup, floating host lifecycle, cleanup, predicate timer.
Used by: runtime show/reload APIs and safe-start diagnostics.
Tests: `tests/test_overlay.py` and overlay cleanup/capture smoke scripts.
"""

from __future__ import annotations

from contextlib import suppress
from typing import Any
from weakref import ref

from .actions import ActionRegistry, create_default_registry
from .qt import load
from .spec import StackSpec
from .state import snapshot
from .widgets import (
    PredicateRefreshResult,
    build_transform_stack,
    refresh_predicate_state,
    set_slot_key_label,
)

OBJECT_NAME_PREFIX = "ActionRailViewportOverlay"
CONTAINER_OBJECT_NAME_PREFIX = f"{OBJECT_NAME_PREFIX}Container"
DEFAULT_MARGIN = 12
PREDICATE_REFRESH_INTERVAL_MS = 250

__all__ = [
    "CONTAINER_OBJECT_NAME_PREFIX",
    "DEFAULT_MARGIN",
    "OBJECT_NAME_PREFIX",
    "PREDICATE_REFRESH_INTERVAL_MS",
    "ViewportOverlayHost",
    "active_model_panel",
    "cleanup_overlay_widgets",
    "maya_main_window",
    "model_panel_widget",
]


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


def maya_main_window(qt: Any | None = None) -> Any | None:
    """Return Maya's main Qt window when running inside Maya."""

    qt = qt or load()
    try:
        from maya import OpenMayaUI as omui  # type: ignore[import-not-found]
    except Exception:
        return None

    try:
        pointer = omui.MQtUtil.mainWindow()
    except Exception:
        return None
    if not pointer:
        return None
    return qt.wrap_instance(int(pointer), qt.QtWidgets.QWidget)


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


def _qt_widget_identity(widget: Any) -> int:
    try:
        from shiboken6 import getCppPointer  # type: ignore[import-not-found]
    except Exception:
        try:
            from shiboken2 import getCppPointer  # type: ignore[import-not-found,no-redef]
        except Exception:
            return id(widget)

    try:
        return int(getCppPointer(widget)[0])
    except Exception:
        return id(widget)


class _ResizeEventFilter:
    """Qt event filter that keeps the rail positioned as the panel resizes."""

    def __init__(self, host: ViewportOverlayHost) -> None:
        qt = load()
        host_ref = ref(host)

        class _Filter(qt.QtCore.QObject):
            def eventFilter(self, watched: Any, event: Any) -> bool:  # noqa: N802
                host = host_ref()
                if host is None:
                    return False

                event_type = event.type()
                if event_type in {
                    qt.QtCore.QEvent.Move,
                    qt.QtCore.QEvent.Resize,
                    qt.QtCore.QEvent.Show,
                    qt.QtCore.QEvent.LayoutRequest,
                    qt.QtCore.QEvent.WindowStateChange,
                }:
                    with suppress(Exception):
                        host.position()
                return False

        self._object = _Filter()

    @property
    def object(self) -> Any:
        return self._object


def cleanup_overlay_widgets(parent: Any, spec_id: str, qt: Any | None = None) -> int:
    """Hide/delete stale ActionRail widgets under a Maya panel widget."""

    qt = qt or load()
    qt_widgets = getattr(qt, "QtWidgets", None)
    object_names = {
        f"{OBJECT_NAME_PREFIX}_{spec_id}",
        f"{CONTAINER_OBJECT_NAME_PREFIX}_{spec_id}",
    }
    search_roots = [parent]
    outer_panel = getattr(parent, "_actionrail_outer_panel_widget", None)
    if outer_panel is not None and outer_panel is not parent:
        search_roots.append(outer_panel)

    stale_widgets: list[Any] = []
    seen: set[int] = set()

    app = getattr(qt_widgets, "QApplication", None)
    if app is not None:
        try:
            instance = app.instance()
            if instance is not None:
                search_roots.extend(instance.allWidgets())
        except Exception:
            pass

    for root in search_roots:
        if root is None or not _qt_widget_is_valid(root):
            continue
        candidates = [root]
        find_children = getattr(root, "findChildren", None)
        if find_children is not None and qt_widgets is not None:
            try:
                children = find_children(qt_widgets.QWidget) or []
            except Exception:
                children = []
            candidates.extend(children)
        for widget in candidates:
            if not _qt_widget_is_valid(widget):
                continue
            try:
                object_name = widget.objectName()
            except Exception:
                continue
            if object_name not in object_names:
                continue
            identifier = _qt_widget_identity(widget)
            if identifier in seen:
                continue
            stale_widgets.append(widget)
            seen.add(identifier)

    removed = 0
    for widget in stale_widgets:
        if not _qt_widget_is_valid(widget):
            continue
        stale_host = getattr(widget, "_actionrail_host", None)
        close = getattr(stale_host, "close", None)
        if callable(close):
            try:
                close()
                removed += 1
                continue
            except Exception:
                pass
        try:
            widget.hide()
            widget.setParent(None)
            widget.deleteLater()
            removed += 1
        except Exception:
            continue
    if removed:
        _flush_qt_deferred_deletes(qt)
    return removed


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
        predicate_refresh_interval_ms: int = PREDICATE_REFRESH_INTERVAL_MS,
    ) -> None:
        self.qt = load()
        self.cmds = _require_cmds(cmds_module)
        self.spec = spec
        self.panel = panel or active_model_panel(self.cmds)
        self.parent = parent or model_panel_widget(self.panel, self.cmds)
        self.window_parent = maya_main_window(self.qt)
        self.registry = registry or create_default_registry()
        self.margin = margin
        self.predicate_refresh_interval_ms = predicate_refresh_interval_ms
        cleanup_overlay_widgets(self.parent, spec.id, self.qt)
        self._floating = self.window_parent is not None
        self.widget = self._build_widget(snapshot(self.cmds, active_panel=self.panel))
        self.widget.hide()
        self._resize_filter = _ResizeEventFilter(self)
        self._filter_targets: list[Any] = []
        self._predicate_refresh_timer: Any | None = None
        self._install_event_filter(self.parent)
        self._install_event_filter(self.window_parent)

    def _build_widget(self, state_snapshot: object) -> Any:
        widget = build_transform_stack(
            self.spec,
            self.registry,
            state_snapshot=state_snapshot,
            cmds_module=self.cmds,
        )
        widget.setObjectName(f"{OBJECT_NAME_PREFIX}_{self.spec.id}")
        with suppress(Exception):
            widget._actionrail_host = self
        if self._floating:
            widget.setParent(self.window_parent)
            widget.setWindowFlags(_floating_window_flags(self.qt))
            widget.setAttribute(self.qt.QtCore.Qt.WA_ShowWithoutActivating, True)
        else:
            widget.setParent(self.parent)
            widget.setWindowFlags(self.qt.QtCore.Qt.Widget)
        return widget

    def _install_event_filter(self, target: Any | None) -> None:
        if target is None or not _qt_widget_is_valid(target):
            return
        try:
            target.installEventFilter(self._resize_filter.object)
        except Exception:
            return
        self._filter_targets.append(target)

    def show(self) -> None:
        self._start_predicate_refresh_timer()
        self.position()
        self.widget.show()
        self.widget.raise_()
        self.position()

    def position(self) -> None:
        if self.widget is None or self.parent is None:
            return
        if not _qt_widget_is_valid(self.widget) or not _qt_widget_is_valid(self.parent):
            return

        parent_rect = self.parent.rect()

        size = self.widget.sizeHint()
        if size.width() <= 0 or size.height() <= 0:
            self.widget.adjustSize()
            size = self.widget.size()

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
        if self._floating:
            self.widget.move(_map_to_global(self.parent, x_pos, y_pos, self.qt))
        else:
            self.widget.move(x_pos, y_pos)

    def close(self) -> None:
        self._stop_predicate_refresh_timer()

        if self._resize_filter is not None:
            for target in self._filter_targets:
                if target is not None and _qt_widget_is_valid(target):
                    target.removeEventFilter(self._resize_filter.object)

        if self.widget is not None and _qt_widget_is_valid(self.widget):
            with suppress(Exception):
                self.widget._actionrail_host = None
            self.widget.hide()
            self.widget.setParent(None)
            self.widget.deleteLater()

        self.widget = None
        self.parent = None
        self.window_parent = None
        self._filter_targets = []
        self._resize_filter = None
        self._predicate_refresh_timer = None

    def refresh_state(self) -> PredicateRefreshResult:
        """Refresh predicate-driven button state from current Maya state."""

        state_snapshot = snapshot(self.cmds, active_panel=self.panel)
        result = refresh_predicate_state(
            self.widget,
            self.spec,
            self.registry,
            state_snapshot=state_snapshot,
            cmds_module=self.cmds,
        )
        if result.needs_rebuild:
            self._rebuild_widget(state_snapshot)
        return result

    def _rebuild_widget(self, state_snapshot: object) -> None:
        old_widget = self.widget
        was_visible = bool(old_widget is not None and old_widget.isVisible())
        key_labels = _rendered_key_labels(old_widget, self.qt)
        self.widget = self._build_widget(state_snapshot)

        for slot_id, key_label in key_labels.items():
            set_slot_key_label(self.widget, slot_id, key_label)

        if old_widget is not None and _qt_widget_is_valid(old_widget):
            with suppress(Exception):
                old_widget._actionrail_host = None
            old_widget.hide()
            old_widget.setParent(None)
            old_widget.deleteLater()

        if was_visible:
            self.show()

    def update_slot_key_label(self, slot_id: str, key_label: str) -> int:
        """Update the key label for a rendered slot."""

        if self.widget is None:
            return 0
        return set_slot_key_label(self.widget, slot_id, key_label)

    def _start_predicate_refresh_timer(self) -> None:
        if self.predicate_refresh_interval_ms <= 0 or self._predicate_refresh_timer is not None:
            return
        if not _spec_uses_predicates(self.spec):
            return

        timer_class = getattr(self.qt.QtCore, "QTimer", None)
        if timer_class is None:
            return

        timer = timer_class()
        timer.setInterval(self.predicate_refresh_interval_ms)
        coarse_timer = getattr(self.qt.QtCore.Qt, "CoarseTimer", None)
        if coarse_timer is not None and hasattr(timer, "setTimerType"):
            timer.setTimerType(coarse_timer)
        timer.timeout.connect(self._refresh_predicates_from_timer)
        timer.start()
        self._predicate_refresh_timer = timer

    def _stop_predicate_refresh_timer(self) -> None:
        timer = self._predicate_refresh_timer
        if timer is None:
            return

        with suppress(Exception):
            timer.stop()
        with suppress(Exception):
            timer.deleteLater()
        self._predicate_refresh_timer = None

    def _refresh_predicates_from_timer(self) -> None:
        if self.widget is None or not _qt_widget_is_valid(self.widget):
            self._stop_predicate_refresh_timer()
            return

        try:
            if not self.widget.isVisible():
                return
            self.refresh_state()
        except Exception:
            # A failed Maya/Qt callback should not keep firing indefinitely.
            self._stop_predicate_refresh_timer()


def _spec_uses_predicates(spec: StackSpec) -> bool:
    return any(
        bool(item.visible_when.strip() or item.enabled_when.strip() or item.active_when.strip())
        for item in spec.items
    )


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


def _floating_window_flags(qt: Any) -> Any:
    flags = qt.QtCore.Qt.Tool | qt.QtCore.Qt.FramelessWindowHint
    for flag_name in ("NoDropShadowWindowHint", "WindowDoesNotAcceptFocus"):
        flag = getattr(qt.QtCore.Qt, flag_name, None)
        if flag is not None:
            flags |= flag
    return flags


def _map_to_global(parent: Any, x_pos: int, y_pos: int, qt: Any) -> Any:
    point = qt.QtCore.QPoint(x_pos, y_pos)
    map_to_global = getattr(parent, "mapToGlobal", None)
    if map_to_global is None:
        return point
    try:
        return map_to_global(point)
    except Exception:
        return point


def _rendered_key_labels(widget: Any, qt: Any) -> dict[str, str]:
    if widget is None or not _qt_widget_is_valid(widget):
        return {}

    key_labels: dict[str, str] = {}
    try:
        buttons = widget.findChildren(qt.QtWidgets.QPushButton)
    except Exception:
        return key_labels

    for button in buttons:
        slot_id = button.property("actionRailSlotId")
        key_label = button.property("actionRailKeyLabel")
        if isinstance(slot_id, str) and isinstance(key_label, str) and key_label:
            key_labels[slot_id] = key_label
    return key_labels


def _flush_qt_deferred_deletes(qt: Any) -> None:
    try:
        app = qt.QtWidgets.QApplication.instance()
    except Exception:
        app = None
    if app is None:
        return
    try:
        app.sendPostedEvents(None, qt.QtCore.QEvent.DeferredDelete)
    except Exception:
        return
