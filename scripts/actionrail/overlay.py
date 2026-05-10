"""Viewport overlay host for ActionRail widgets.

Purpose: position small Qt rail windows from Maya model-panel geometry.
Owns: active panel lookup, floating host lifecycle, cleanup, predicate timer.
Used by: runtime show/reload APIs and safe-start diagnostics.
Tests: `tests/test_overlay.py` and overlay cleanup/capture smoke scripts.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import suppress
from dataclasses import replace as dataclass_replace
from typing import Any
from weakref import ref

from .actions import ActionRegistry, create_default_registry
from .predicates import predicate_dependencies
from .qt import load
from .spec import StackSpec
from .state import MayaStateService, snapshot
from .widgets import (
    PredicateRefreshResult,
    SlotEditCallbacks,
    build_collapsed_handle,
    build_transform_stack,
    refresh_predicate_state,
    set_slot_key_label,
)

OBJECT_NAME_PREFIX = "ActionRailViewportOverlay"
CONTAINER_OBJECT_NAME_PREFIX = f"{OBJECT_NAME_PREFIX}Container"
DEFAULT_MARGIN = 12
COLLAPSED_HANDLE_EDGE_MARGIN = 4
PREDICATE_REFRESH_INTERVAL_MS = 250
_PREDICATE_REFRESH_SCHEDULERS: dict[tuple[int, int, int], PredicateRefreshScheduler] = {}

__all__ = [
    "CONTAINER_OBJECT_NAME_PREFIX",
    "DEFAULT_MARGIN",
    "OBJECT_NAME_PREFIX",
    "PREDICATE_REFRESH_INTERVAL_MS",
    "PredicateRefreshScheduler",
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


class PredicateRefreshScheduler:
    """One Qt timer that refreshes predicate-bearing overlay hosts together."""

    def __init__(self, qt: Any, cmds_module: Any, interval_ms: int) -> None:
        self.qt = qt
        self.cmds = cmds_module
        self.interval_ms = interval_ms
        self.service = MayaStateService(cmds_module)
        self.hosts: list[ref[ViewportOverlayHost]] = []
        self.timer: Any | None = None

    @classmethod
    def for_host(cls, host: ViewportOverlayHost) -> PredicateRefreshScheduler:
        if not hasattr(host, "cmds"):
            msg = "Predicate refresh requires a Maya cmds module."
            raise RuntimeError(msg)
        key = (id(host.qt), id(host.cmds), int(host.predicate_refresh_interval_ms))
        scheduler = _PREDICATE_REFRESH_SCHEDULERS.get(key)
        if scheduler is None:
            scheduler = cls(host.qt, host.cmds, host.predicate_refresh_interval_ms)
            _PREDICATE_REFRESH_SCHEDULERS[key] = scheduler
        return scheduler

    def register(self, host: ViewportOverlayHost) -> None:
        self._prune_hosts()
        if not any(existing() is host for existing in self.hosts):
            self.hosts.append(ref(host))
        self._ensure_timer()

    def unregister(self, host: ViewportOverlayHost) -> None:
        self.hosts = [
            existing
            for existing in self.hosts
            if existing() is not None and existing() is not host
        ]
        if not self.hosts:
            self.stop()

    def refresh(self) -> None:
        live_hosts = tuple(self._live_visible_hosts())
        if not live_hosts:
            self.stop()
            return

        panels = tuple({host.panel for host in live_hosts if getattr(host, "panel", "")})
        self.service.refresh(active_panels=panels)
        changed = self.service.changed_dependencies
        if not changed:
            return
        for host in live_hosts:
            dependencies = getattr(host, "_predicate_dependencies", frozenset())
            if dependencies and not dependencies.intersection(changed):
                continue
            host.refresh_state(
                state_snapshot=self.service.snapshot_for_panel(getattr(host, "panel", "")),
            )

    def stop(self) -> None:
        timer = self.timer
        if timer is not None:
            with suppress(Exception):
                timer.stop()
            with suppress(Exception):
                timer.deleteLater()
        self.timer = None
        self._remove_from_registry()

    def _ensure_timer(self) -> None:
        if self.timer is not None:
            return
        timer_class = getattr(self.qt.QtCore, "QTimer", None)
        if timer_class is None:
            return
        timer = timer_class()
        timer.setInterval(self.interval_ms)
        coarse_timer = getattr(self.qt.QtCore.Qt, "CoarseTimer", None)
        if coarse_timer is not None and hasattr(timer, "setTimerType"):
            timer.setTimerType(coarse_timer)
        timer.timeout.connect(self._refresh_from_timer)
        timer.start()
        self.timer = timer

    def _refresh_from_timer(self) -> None:
        try:
            self.refresh()
        except Exception:
            self.stop()

    def _live_visible_hosts(self) -> Iterator[ViewportOverlayHost]:
        self._prune_hosts()
        for host_ref in tuple(self.hosts):
            host = host_ref()
            if host is None or host.widget is None or not _qt_widget_is_valid(host.widget):
                continue
            with suppress(Exception):
                if host.widget.isVisible():
                    yield host

    def _prune_hosts(self) -> None:
        self.hosts = [host_ref for host_ref in self.hosts if host_ref() is not None]

    def _remove_from_registry(self) -> None:
        for key, scheduler in tuple(_PREDICATE_REFRESH_SCHEDULERS.items()):
            if scheduler is self:
                _PREDICATE_REFRESH_SCHEDULERS.pop(key, None)


def cleanup_overlay_widgets(parent: Any, spec_id: str, qt: Any | None = None) -> int:
    """Hide/delete stale ActionRail widgets under a Maya panel widget."""

    qt = qt or load()
    removed = sum(
        1 for widget in _stale_overlay_widgets(parent, spec_id, qt) if _close_stale_widget(widget)
    )
    if removed:
        _flush_qt_deferred_deletes(qt)
    return removed


def _cleanup_search_roots(parent: Any, qt: Any) -> list[Any]:
    roots = [parent]
    outer_panel = getattr(parent, "_actionrail_outer_panel_widget", None)
    if outer_panel is not None and outer_panel is not parent:
        roots.append(outer_panel)

    qt_widgets = getattr(qt, "QtWidgets", None)
    app = getattr(qt_widgets, "QApplication", None)
    if app is not None:
        try:
            instance = app.instance()
            if instance is not None:
                roots.extend(instance.allWidgets())
        except Exception:
            pass
    return roots


def _iter_widget_candidates(root: Any, qt_widgets: Any) -> Iterator[Any]:
    if root is None or not _qt_widget_is_valid(root):
        return

    yield root
    find_children = getattr(root, "findChildren", None)
    if find_children is None or qt_widgets is None:
        return

    try:
        children = find_children(qt_widgets.QWidget) or []
    except Exception:
        return

    yield from children


def _stale_overlay_widgets(parent: Any, spec_id: str, qt: Any) -> list[Any]:
    qt_widgets = getattr(qt, "QtWidgets", None)
    object_names = {
        f"{OBJECT_NAME_PREFIX}_{spec_id}",
        f"{CONTAINER_OBJECT_NAME_PREFIX}_{spec_id}",
    }
    stale_widgets: list[Any] = []
    seen: set[int] = set()

    for root in _cleanup_search_roots(parent, qt):
        if root is None or not _qt_widget_is_valid(root):
            continue
        for widget in _iter_widget_candidates(root, qt_widgets):
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

    return stale_widgets


def _close_stale_widget(widget: Any) -> bool:
    if not _qt_widget_is_valid(widget):
        return False

    stale_host = getattr(widget, "_actionrail_host", None)
    close = getattr(stale_host, "close", None)
    if callable(close):
        try:
            close()
            return True
        except Exception:
            pass

    try:
        widget.hide()
        widget.setParent(None)
        widget.deleteLater()
    except Exception:
        return False
    return True


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
        self._collapsed = bool(spec.collapse.enabled and spec.collapse.default_collapsed)
        self._slot_edit_unlocked = False
        self._runtime_key_labels: dict[str, str] = {}
        self._predicate_dependencies = _spec_predicate_dependencies(spec)
        self._predicate_refresh_scheduler: PredicateRefreshScheduler | None = None
        self.widget = self._build_widget(snapshot(self.cmds, active_panel=self.panel))
        self.widget.hide()
        self._resize_filter = _ResizeEventFilter(self)
        self._filter_targets: list[Any] = []
        self._predicate_refresh_timer: Any | None = None
        self._install_event_filter(self.parent)
        self._install_event_filter(self.window_parent)

    def _build_widget(self, state_snapshot: object) -> Any:
        if getattr(self, "_collapsed", False) and self.spec.collapse.enabled:
            widget = build_collapsed_handle(self.spec, self.expand)
        else:
            widget = build_transform_stack(
                self.spec,
                self.registry,
                state_snapshot=state_snapshot,
                cmds_module=self.cmds,
                slot_edit_callbacks=self._slot_edit_callbacks(),
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
        if getattr(self, "_collapsed", False) and self.spec.collapse.enabled:
            x_pos, y_pos = _collapsed_handle_position(
                self.spec.collapse.edge,
                parent_rect.width(),
                parent_rect.height(),
                size.width(),
                size.height(),
                self.spec.layout.offset,
            )
        else:
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

    def refresh_state(
        self,
        state_snapshot: object | None = None,
    ) -> PredicateRefreshResult:
        """Refresh predicate-driven button state from current Maya state."""

        if getattr(self, "_collapsed", False) and self.spec.collapse.enabled:
            return PredicateRefreshResult(
                refreshed=0,
                needs_rebuild=False,
                visible_slot_ids=(),
                rendered_slot_ids=(),
            )

        if state_snapshot is None:
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
        if hasattr(self, "spec"):
            self._predicate_dependencies = _spec_predicate_dependencies(self.spec)
        key_labels = {
            **_rendered_key_labels(old_widget, self.qt),
            **getattr(self, "_runtime_key_labels", {}),
        }
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

        if not hasattr(self, "_runtime_key_labels"):
            self._runtime_key_labels = {}
        if key_label:
            self._runtime_key_labels[slot_id] = key_label
        else:
            self._runtime_key_labels.pop(slot_id, None)
        if self.widget is None or getattr(self, "_collapsed", False):
            return 0
        return set_slot_key_label(self.widget, slot_id, key_label)

    def set_slot_edit_unlocked(self, unlocked: bool) -> bool:
        """Toggle Normal Mode slot payload editing for this active rail."""

        unlocked = bool(unlocked)
        if self._slot_edit_unlocked == unlocked:
            return True
        self._slot_edit_unlocked = unlocked
        self._rebuild_widget(snapshot(self.cmds, active_panel=self.panel))
        return True

    def slot_edit_unlocked(self) -> bool:
        """Return whether Normal Mode slot payload editing is active."""

        return bool(getattr(self, "_slot_edit_unlocked", False))

    def assign_slot_action_payload(self, slot_id: str, action_id: str) -> bool:
        """Assign an action payload to a stable slot while the rail is unlocked."""

        if not self.slot_edit_unlocked():
            return False
        try:
            from .slot_payloads import spec_with_slot_action_payload

            self.spec = spec_with_slot_action_payload(self.spec, slot_id, action_id)
        except Exception:
            return False
        self._rebuild_widget(snapshot(self.cmds, active_panel=self.panel))
        return True

    def clear_slot_payload(self, slot_id: str) -> bool:
        """Clear an action payload from a stable slot while the rail is unlocked."""

        if not self.slot_edit_unlocked():
            return False
        try:
            from .slot_payloads import spec_with_empty_slot_payload

            self.spec = spec_with_empty_slot_payload(self.spec, slot_id)
        except Exception:
            return False
        self._rebuild_widget(snapshot(self.cmds, active_panel=self.panel))
        return True

    def move_slot_payload(self, source_slot_id: str, target_slot_id: str) -> bool:
        """Move or swap a slot payload while the rail is unlocked."""

        if not self.slot_edit_unlocked():
            return False
        try:
            from .slot_payloads import spec_with_moved_slot_payload

            updated_spec = spec_with_moved_slot_payload(
                self.spec,
                source_slot_id,
                target_slot_id,
            )
        except Exception:
            return False
        if updated_spec is self.spec:
            return True
        self.spec = updated_spec
        self._rebuild_widget(snapshot(self.cmds, active_panel=self.panel))
        return True

    def transfer_slot_payload(
        self,
        source_slot_id: str,
        target_callbacks: SlotEditCallbacks,
        target_slot_id: str,
    ) -> bool:
        """Move or swap a slot payload onto another unlocked active rail."""

        target_host = getattr(target_callbacks, "owner", None)
        if target_host is self:
            return self.move_slot_payload(source_slot_id, target_slot_id)
        if (
            target_host is None
            or not self.slot_edit_unlocked()
            or not getattr(target_callbacks, "unlocked", False)
        ):
            return False
        target_unlocked = getattr(target_host, "slot_edit_unlocked", None)
        if not callable(target_unlocked) or not target_unlocked():
            return False
        try:
            from .slot_payloads import (
                SlotPayload,
                slot_has_payload,
                slot_payload_from_spec,
                spec_with_slot_payload,
            )

            if not slot_has_payload(self.spec, source_slot_id):
                return False
            source_payload = slot_payload_from_spec(self.spec, source_slot_id)
            target_has_payload = slot_has_payload(target_host.spec, target_slot_id)
            target_payload = (
                slot_payload_from_spec(target_host.spec, target_slot_id)
                if target_has_payload
                else SlotPayload()
            )
            source_spec = spec_with_slot_payload(
                self.spec,
                source_slot_id,
                target_payload,
            )
            target_spec = spec_with_slot_payload(
                target_host.spec,
                target_slot_id,
                source_payload,
            )
        except Exception:
            return False

        self.spec = source_spec
        target_host.spec = target_spec
        state_snapshot = snapshot(self.cmds, active_panel=self.panel)
        self._rebuild_widget(state_snapshot)
        target_cmds = getattr(target_host, "cmds", self.cmds)
        target_panel = getattr(target_host, "panel", self.panel)
        target_host._rebuild_widget(snapshot(target_cmds, active_panel=target_panel))
        return True

    def _slot_edit_callbacks(self) -> SlotEditCallbacks:
        return SlotEditCallbacks(
            unlocked=bool(getattr(self, "_slot_edit_unlocked", False)),
            unlock_rail=lambda: self.set_slot_edit_unlocked(True),
            lock_rail=lambda: self.set_slot_edit_unlocked(False),
            assign_action=self.assign_slot_action_payload,
            clear_slot=self.clear_slot_payload,
            move_slot=self.move_slot_payload,
            owner=self,
            transfer_slot=self.transfer_slot_payload,
        )

    def expand(self) -> bool:
        """Expand this rail when its collapsed edge handle is activated."""

        return self.set_collapsed(False)

    def set_collapsed(self, collapsed: bool, *, persist_default: bool = False) -> bool:
        """Set the live collapsed state and optionally update the spec default."""

        if not self.spec.collapse.enabled:
            return False
        collapsed = bool(collapsed)
        if persist_default and self.spec.collapse.default_collapsed != collapsed:
            self.spec = dataclass_replace(
                self.spec,
                collapse=dataclass_replace(
                    self.spec.collapse,
                    default_collapsed=collapsed,
                ),
            )
        if self._collapsed == collapsed:
            self.position()
            return True
        self._collapsed = collapsed
        self._rebuild_widget(snapshot(self.cmds, active_panel=self.panel))
        return True

    def update_layout_offset(self, offset: tuple[int, int]) -> tuple[int, int]:
        """Move this rail by updating its in-memory layout offset."""

        normalized = (int(offset[0]), int(offset[1]))
        self.spec = dataclass_replace(
            self.spec,
            layout=dataclass_replace(self.spec.layout, offset=normalized),
        )
        self.position()
        return normalized

    def _start_predicate_refresh_timer(self) -> None:
        if self.predicate_refresh_interval_ms <= 0 or self._predicate_refresh_timer is not None:
            return
        if not _spec_uses_predicates(self.spec):
            return
        if not hasattr(self, "cmds"):
            return
        scheduler = PredicateRefreshScheduler.for_host(self)
        scheduler.register(self)
        self._predicate_refresh_scheduler = scheduler
        self._predicate_refresh_timer = scheduler.timer

    def _stop_predicate_refresh_timer(self) -> None:
        scheduler = getattr(self, "_predicate_refresh_scheduler", None)
        if scheduler is not None:
            scheduler.unregister(self)
        else:
            timer = self._predicate_refresh_timer
            if timer is not None:
                with suppress(Exception):
                    timer.stop()
                with suppress(Exception):
                    timer.deleteLater()
        self._predicate_refresh_scheduler = None
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


def _spec_predicate_dependencies(spec: StackSpec) -> frozenset[str]:
    dependencies: set[str] = set()
    for item in spec.items:
        for predicate in (item.visible_when, item.enabled_when, item.active_when):
            if predicate.strip():
                dependencies.update(predicate_dependencies(predicate))
    return frozenset(dependencies)


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


def _collapsed_handle_position(
    edge: str,
    parent_width: int,
    parent_height: int,
    widget_width: int,
    widget_height: int,
    layout_offset: tuple[int, int],
    *,
    margin: int = COLLAPSED_HANDLE_EDGE_MARGIN,
) -> tuple[int, int]:
    """Return a small edge-tab position without reusing the rail's inward offset."""

    offset_x, offset_y = layout_offset
    if edge == "right":
        x_pos = parent_width - widget_width - margin
        y_pos = int((parent_height - widget_height) / 2) + offset_y
    elif edge == "top":
        x_pos = int((parent_width - widget_width) / 2) + offset_x
        y_pos = margin
    elif edge == "bottom":
        x_pos = int((parent_width - widget_width) / 2) + offset_x
        y_pos = parent_height - widget_height - margin
    else:
        x_pos = margin
        y_pos = int((parent_height - widget_height) / 2) + offset_y

    max_x = max(margin, parent_width - widget_width - margin)
    max_y = max(margin, parent_height - widget_height - margin)
    return (
        min(max(margin, x_pos), max_x),
        min(max(margin, y_pos), max_y),
    )


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
