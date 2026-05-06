"""Edit Mode layout-map overlay for ActionRail rails.

Purpose: show edit-only grid, rail footprints, selection, and placement controls.
Owns: global Edit Mode state, layout-map painting, rail nudging, and layout saves.
Used by: public ActionRail API and Maya menu commands.
Tests: `tests/test_edit_mode.py` and `tests/maya_smoke/actionrail_edit_mode_smoke.py`.
"""

from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass
from dataclasses import replace as dataclass_replace
from pathlib import Path
from typing import Any

from .qt import load

DEFAULT_GRID_SIZE = 32
STICKY_SNAP_THRESHOLD = 8
SAFE_MARGIN = 8
DEFAULT_SAFE_BOUNDS = (4096, 4096)
MIN_GRID_SIZE = 16
MAX_GRID_SIZE = 512
EDIT_OVERLAY_OBJECT_NAME = "ActionRailEditModeOverlay"
EDIT_PANEL_OBJECT_NAME = "ActionRailEditModePanel"
POSITION_POPOVER_OBJECT_NAME = "ActionRailEditModePositionPopover"
FRAME_OPTIONS_POPOVER_OBJECT_NAME = "ActionRailEditModeFrameOptionsPopover"

__all__ = [
    "DEFAULT_GRID_SIZE",
    "EDIT_OVERLAY_OBJECT_NAME",
    "EDIT_PANEL_OBJECT_NAME",
    "FRAME_OPTIONS_POPOVER_OBJECT_NAME",
    "POSITION_POPOVER_OBJECT_NAME",
    "EditModeSettings",
    "EditModeState",
    "RailFrameInfo",
    "STICKY_SNAP_THRESHOLD",
    "edit_mode_state",
    "enter_edit_mode",
    "exit_edit_mode",
    "refresh_edit_mode",
    "save_edit_mode_layout",
    "select_edit_mode_rail",
    "set_edit_mode_options",
    "toggle_edit_mode",
]


@dataclass(frozen=True)
class EditModeSettings:
    """User-visible edit-mode placement options."""

    show_grid: bool = True
    snap_to_grid: bool = False
    sticky_frames: bool = False
    grid_size: int = DEFAULT_GRID_SIZE

    def normalized(self) -> EditModeSettings:
        return dataclass_replace(
            self,
            grid_size=max(MIN_GRID_SIZE, min(MAX_GRID_SIZE, int(self.grid_size))),
        )


@dataclass(frozen=True)
class RailFrameInfo:
    """Viewport-local edit footprint for one active rail."""

    preset_id: str
    label: str
    x: int
    y: int
    width: int
    height: int
    anchor: str
    offset: tuple[int, int]
    orientation: str
    rows: int
    columns: int
    scale: float
    opacity: float
    locked: bool
    collapse_enabled: bool = False
    collapse_edge: str = "left"
    collapsed: bool = False
    source_layer: str = "runtime"

    @property
    def right(self) -> int:
        return self.x + self.width

    @property
    def bottom(self) -> int:
        return self.y + self.height

    def contains(self, x_pos: int, y_pos: int) -> bool:
        return self.x <= x_pos <= self.right and self.y <= y_pos <= self.bottom


@dataclass(frozen=True)
class EditModeState:
    """Public summary of the current Edit Mode session."""

    enabled: bool
    selected_preset_id: str
    settings: EditModeSettings
    rail_count: int
    options_preset_id: str = ""


_EDIT_HOST: EditModeOverlayHost | None = None
_SETTINGS = EditModeSettings()
_SELECTED_PRESET_ID = ""
_OPTIONS_PRESET_ID = ""


def enter_edit_mode(
    *,
    panel: str | None = None,
    settings: EditModeSettings | None = None,
) -> EditModeState:
    """Enter the edit-only layout-map overlay."""

    global _EDIT_HOST, _SETTINGS
    if settings is not None:
        _SETTINGS = settings.normalized()

    if _EDIT_HOST is not None:
        _EDIT_HOST.close()

    _EDIT_HOST = EditModeOverlayHost(panel=panel, settings=_SETTINGS)
    _EDIT_HOST.show()
    return edit_mode_state()


def exit_edit_mode() -> EditModeState:
    """Close the Edit Mode overlay and return to normal action execution."""

    global _EDIT_HOST, _SELECTED_PRESET_ID, _OPTIONS_PRESET_ID
    if _EDIT_HOST is not None:
        _EDIT_HOST.close()
    _EDIT_HOST = None
    _SELECTED_PRESET_ID = ""
    _OPTIONS_PRESET_ID = ""
    return edit_mode_state()


def toggle_edit_mode(
    *,
    panel: str | None = None,
    settings: EditModeSettings | None = None,
) -> EditModeState:
    """Toggle ActionRail Edit Mode."""

    if _EDIT_HOST is None:
        return enter_edit_mode(panel=panel, settings=settings)
    return exit_edit_mode()


def set_edit_mode_options(
    *,
    show_grid: bool | None = None,
    snap_to_grid: bool | None = None,
    sticky_frames: bool | None = None,
    grid_size: int | None = None,
) -> EditModeState:
    """Update user-visible Edit Mode grid and snapping options."""

    global _SETTINGS
    _SETTINGS = EditModeSettings(
        show_grid=_SETTINGS.show_grid if show_grid is None else bool(show_grid),
        snap_to_grid=_SETTINGS.snap_to_grid if snap_to_grid is None else bool(snap_to_grid),
        sticky_frames=(
            _SETTINGS.sticky_frames if sticky_frames is None else bool(sticky_frames)
        ),
        grid_size=_SETTINGS.grid_size if grid_size is None else int(grid_size),
    ).normalized()
    if _EDIT_HOST is not None:
        _EDIT_HOST.set_settings(_SETTINGS)
    return edit_mode_state()


def refresh_edit_mode() -> EditModeState:
    """Refresh the Edit Mode overlay after rail runtime changes."""

    if _EDIT_HOST is not None:
        _EDIT_HOST.refresh()
    return edit_mode_state()


def save_edit_mode_layout(
    preset_id: str | None = None,
    *,
    user_preset_dir: str | Path | None = None,
    overwrite: bool = True,
) -> Path:
    """Persist the selected active rail's current layout as a user preset."""

    if _EDIT_HOST is None:
        msg = "ActionRail Edit Mode is not active."
        raise RuntimeError(msg)
    return _EDIT_HOST.save_layout(
        preset_id or _SELECTED_PRESET_ID,
        user_preset_dir=user_preset_dir,
        overwrite=overwrite,
    )


def select_edit_mode_rail(preset_id: str) -> EditModeState:
    """Select an active rail in Edit Mode."""

    global _SELECTED_PRESET_ID
    _SELECTED_PRESET_ID = preset_id
    if _EDIT_HOST is not None:
        _EDIT_HOST.select_rail(preset_id)
    return edit_mode_state()


def edit_mode_state() -> EditModeState:
    """Return a compact summary of the current Edit Mode state."""

    rail_count = 0
    if _EDIT_HOST is not None:
        rail_count = len(_EDIT_HOST.frames)
    return EditModeState(
        enabled=_EDIT_HOST is not None,
        selected_preset_id=_SELECTED_PRESET_ID,
        settings=_SETTINGS,
        rail_count=rail_count,
        options_preset_id=_OPTIONS_PRESET_ID,
    )


class EditModeOverlayHost:  # pragma: no cover - covered by Maya smoke tests.
    """Owns the full-viewport edit-only layout-map widget."""

    def __init__(
        self,
        *,
        panel: str | None = None,
        settings: EditModeSettings | None = None,
        cmds_module: Any | None = None,
    ) -> None:
        from .overlay import (
            _floating_window_flags,
            _map_to_global,
            _qt_widget_is_valid,
            _ResizeEventFilter,
            active_model_panel,
            maya_main_window,
            model_panel_widget,
        )

        self.qt = load()
        self.cmds = _require_cmds(cmds_module)
        self.panel = panel or active_model_panel(self.cmds)
        self.parent = model_panel_widget(self.panel, self.cmds)
        self.window_parent = maya_main_window(self.qt)
        self.settings = (settings or _SETTINGS).normalized()
        self.frames: tuple[RailFrameInfo, ...] = ()
        self._original_offsets: dict[str, tuple[int, int]] = {}
        self._qt_widget_is_valid = _qt_widget_is_valid
        self._map_to_global = _map_to_global
        self._floating = self.window_parent is not None
        self.widget = _EditModeCanvas(self)
        self.widget.setObjectName(EDIT_OVERLAY_OBJECT_NAME)
        self.widget.hide()
        if self._floating:
            self.widget.setParent(self.window_parent)
            self.widget.setWindowFlags(_floating_window_flags(self.qt))
            self.widget.setAttribute(self.qt.QtCore.Qt.WA_ShowWithoutActivating, True)
        else:
            self.widget.setParent(self.parent)
            self.widget.setWindowFlags(self.qt.QtCore.Qt.Widget)
        self._resize_filter = _ResizeEventFilter(self)
        self._filter_targets: list[Any] = []
        self._install_event_filter(self.parent)
        self._install_event_filter(self.window_parent)

    def _install_event_filter(self, target: Any | None) -> None:
        if target is None or not self._qt_widget_is_valid(target):
            return
        with suppress(Exception):
            target.installEventFilter(self._resize_filter.object)
            self._filter_targets.append(target)

    def show(self) -> None:
        self.refresh()
        self.position()
        self.widget.show()
        self.widget.raise_()
        self.position()

    def close(self) -> None:
        for target in self._filter_targets:
            if target is not None and self._qt_widget_is_valid(target):
                with suppress(Exception):
                    target.removeEventFilter(self._resize_filter.object)
        self._filter_targets = []
        if self.widget is not None and self._qt_widget_is_valid(self.widget):
            self.widget.hide()
            self.widget.setParent(None)
            self.widget.deleteLater()
        self.widget = None
        self.parent = None
        self.window_parent = None

    def position(self) -> None:
        if self.widget is None or self.parent is None:
            return
        if not self._qt_widget_is_valid(self.widget) or not self._qt_widget_is_valid(
            self.parent
        ):
            return
        rect = self.parent.rect()
        self.widget.resize(rect.width(), rect.height())
        if self._floating:
            self.widget.move(self._map_to_global(self.parent, 0, 0, self.qt))
        else:
            self.widget.move(0, 0)
        self.refresh()

    def refresh(self) -> None:
        global _OPTIONS_PRESET_ID, _SELECTED_PRESET_ID
        self.frames = tuple(_rail_frame_infos(self.qt, self.parent))
        for frame in self.frames:
            self._original_offsets.setdefault(frame.preset_id, frame.offset)
        active_preset_ids = {frame.preset_id for frame in self.frames}
        if _SELECTED_PRESET_ID not in active_preset_ids:
            _SELECTED_PRESET_ID = ""
        if _OPTIONS_PRESET_ID not in active_preset_ids:
            _OPTIONS_PRESET_ID = ""
        self.widget.refresh_from_host()

    def set_settings(self, settings: EditModeSettings) -> None:
        self.settings = settings.normalized()
        self.widget.refresh_from_host()

    def select_rail(self, preset_id: str) -> None:
        global _OPTIONS_PRESET_ID, _SELECTED_PRESET_ID
        _SELECTED_PRESET_ID = (
            preset_id if any(frame.preset_id == preset_id for frame in self.frames) else ""
        )
        if _OPTIONS_PRESET_ID and _OPTIONS_PRESET_ID != _SELECTED_PRESET_ID:
            _OPTIONS_PRESET_ID = ""
        self.widget.refresh_from_host()

    def open_options(self, preset_id: str) -> None:
        global _OPTIONS_PRESET_ID, _SELECTED_PRESET_ID
        _SELECTED_PRESET_ID = (
            preset_id if any(frame.preset_id == preset_id for frame in self.frames) else ""
        )
        _OPTIONS_PRESET_ID = _SELECTED_PRESET_ID
        self.widget.refresh_from_host()

    def nudge_selected(self, dx: int, dy: int) -> None:
        selected = self.selected_frame()
        if selected is None or selected.locked:
            return
        settings = getattr(self, "settings", EditModeSettings()).normalized()
        dx_pos = _nudge_delta(dx, settings.grid_size) if settings.snap_to_grid else dx
        dy_pos = _nudge_delta(dy, settings.grid_size) if settings.snap_to_grid else dy
        self.set_selected_position(
            selected.x + dx_pos,
            selected.y + dy_pos,
            apply_snapping=True,
            snap_axes=_snap_axes_for_delta(dx, dy),
        )

    def set_selected_position(
        self,
        x_pos: int,
        y_pos: int,
        *,
        apply_snapping: bool = False,
        snap_axes: tuple[str, ...] = ("x", "y"),
    ) -> None:
        selected = self.selected_frame()
        if selected is None or selected.locked:
            return
        host = _runtime_hosts().get(selected.preset_id)
        if host is None:
            return
        if apply_snapping:
            x_pos, y_pos = _snapped_position(
                selected,
                int(x_pos),
                int(y_pos),
                getattr(self, "settings", EditModeSettings()).normalized(),
                self.frames,
                snap_axes=snap_axes,
                bounds=_safe_widget_size(self.widget),
            )
        base_x = selected.x - selected.offset[0]
        base_y = selected.y - selected.offset[1]
        new_offset = (int(x_pos) - base_x, int(y_pos) - base_y)
        _set_host_offset(host, new_offset)
        self.refresh()

    def reset_selected_position(self) -> None:
        selected = self.selected_frame()
        if selected is None or selected.locked:
            return
        original = self._original_offsets.get(selected.preset_id, (0, 0))
        host = _runtime_hosts().get(selected.preset_id)
        if host is None:
            return
        _set_host_offset(host, original)
        self.refresh()

    def add_slot_to_selected(self) -> bool:
        selected = self.selected_frame()
        if selected is None or selected.locked:
            return False
        host = _runtime_hosts().get(selected.preset_id)
        spec = getattr(host, "spec", None)
        if host is None or spec is None:
            return False
        from .spec import StackItem

        slot_number = _next_slot_number(spec)
        slot_id = f"{spec.id}.slot_{slot_number}"
        item = StackItem(type="button", id=slot_id, label="New")
        _replace_host_spec(host, dataclass_replace(spec, items=(*spec.items, item)))
        self.refresh()
        return True

    def remove_slot_from_selected(self) -> bool:
        selected = self.selected_frame()
        if selected is None or selected.locked:
            return False
        host = _runtime_hosts().get(selected.preset_id)
        spec = getattr(host, "spec", None)
        if host is None or spec is None:
            return False
        index = _last_action_item_index(spec.items)
        if index is None:
            return False
        items = (*spec.items[:index], *spec.items[index + 1 :])
        _replace_host_spec(host, dataclass_replace(spec, items=items))
        self.refresh()
        return True

    def reorder_selected_slot(self, delta: int) -> bool:
        selected = self.selected_frame()
        if selected is None or selected.locked or delta == 0:
            return False
        host = _runtime_hosts().get(selected.preset_id)
        spec = getattr(host, "spec", None)
        if host is None or spec is None:
            return False
        index = _last_action_item_index(spec.items)
        if index is None:
            return False
        target = max(0, min(len(spec.items) - 1, index + delta))
        if target == index:
            return False
        items = list(spec.items)
        item = items.pop(index)
        items.insert(target, item)
        _replace_host_spec(host, dataclass_replace(spec, items=tuple(items)))
        self.refresh()
        return True

    def toggle_selected_edge_tab(self) -> bool:
        selected = self.selected_frame()
        if selected is None or selected.locked or not _is_edge_anchor(selected.anchor):
            return False
        host = _runtime_hosts().get(selected.preset_id)
        spec = getattr(host, "spec", None)
        if host is None or spec is None:
            return False
        from .spec import RailCollapse

        edge = spec.collapse.edge if spec.collapse.enabled else _edge_from_anchor(selected.anchor)
        collapsed = not bool(getattr(host, "_collapsed", False))
        collapse = dataclass_replace(
            spec.collapse if spec.collapse.enabled else RailCollapse(enabled=True),
            enabled=True,
            edge=edge,
            default_collapsed=collapsed,
        )
        host.spec = dataclass_replace(spec, collapse=collapse)
        set_collapsed = getattr(host, "set_collapsed", None)
        if callable(set_collapsed):
            set_collapsed(collapsed, persist_default=True)
        else:
            _replace_host_spec(host, host.spec)
        self.refresh()
        return True

    def save_selected_layout(
        self,
        *,
        user_preset_dir: str | Path | None = None,
        overwrite: bool = True,
    ) -> Path:
        """Persist the currently selected rail's layout to the user preset store."""

        return self.save_layout(
            _SELECTED_PRESET_ID,
            user_preset_dir=user_preset_dir,
            overwrite=overwrite,
        )

    def save_layout(
        self,
        preset_id: str,
        *,
        user_preset_dir: str | Path | None = None,
        overwrite: bool = True,
    ) -> Path:
        """Persist an active rail's current spec to the user preset store."""

        if not preset_id:
            msg = "Select an ActionRail frame before saving its layout."
            raise ValueError(msg)
        frame = self.frame_for_preset(preset_id)
        if frame is None:
            msg = f"ActionRail rail is not active in Edit Mode: {preset_id}"
            raise KeyError(msg)
        if frame.locked:
            msg = f"ActionRail rail is locked and cannot be saved from Edit Mode: {preset_id}"
            raise ValueError(msg)
        host = _runtime_hosts().get(preset_id)
        spec = getattr(host, "spec", None)
        if host is None or spec is None:
            msg = f"ActionRail runtime host is unavailable for rail: {preset_id}"
            raise KeyError(msg)
        from .authoring import save_user_preset

        if frame.source_layer in {"builtin", "studio"}:
            spec = _user_override_spec(spec)
        target_preset_dir = (
            user_preset_dir
            if user_preset_dir is not None
            else getattr(host, "user_preset_dir", None)
        )
        return save_user_preset(
            spec,
            preset_dir=target_preset_dir,
            overwrite=overwrite,
        )

    def frame_for_preset(self, preset_id: str) -> RailFrameInfo | None:
        for frame in self.frames:
            if frame.preset_id == preset_id:
                return frame
        return None

    def selected_frame(self) -> RailFrameInfo | None:
        return self.frame_for_preset(_SELECTED_PRESET_ID)


class _EditModeCanvas:  # pragma: no cover - covered by Maya smoke tests.
    """Factory wrapper around the Qt canvas class."""

    def __new__(cls, host: EditModeOverlayHost) -> Any:
        qt = load()

        class _Canvas(qt.QtWidgets.QWidget):
            def __init__(self, edit_host: EditModeOverlayHost) -> None:
                super().__init__()
                self._host = edit_host
                self._drag_preset_id = ""
                self._drag_offset = (0, 0)
                self.setAttribute(qt.QtCore.Qt.WA_TranslucentBackground, True)
                self.setMouseTracking(True)
                self.setFocusPolicy(qt.QtCore.Qt.NoFocus)
                self._panel = _EditModePanel(self)
                self._popover = _PositionPopover(self)
                self._options_popover = _FrameOptionsPopover(self)
                self._popover.hide()
                self._options_popover.hide()

            def refresh_from_host(self) -> None:
                self._panel.sync()
                self._sync_popover()
                self._sync_options_popover()
                self.update()

            def paintEvent(self, event: Any) -> None:  # noqa: N802
                painter = qt.QtGui.QPainter(self)
                try:
                    painter.setRenderHint(qt.QtGui.QPainter.Antialiasing, False)
                    if self._host.settings.show_grid:
                        _paint_grid(qt, painter, self.rect(), self._host.settings.grid_size)
                    selected = self._host.selected_frame()
                    if selected is not None:
                        _paint_guides(
                            qt,
                            painter,
                            self.rect(),
                            selected,
                            self._host.frames,
                            self._host.settings,
                        )
                    for frame in self._host.frames:
                        _paint_frame(qt, painter, frame, frame.preset_id == _SELECTED_PRESET_ID)
                finally:
                    painter.end()
                    _ = event

            def mousePressEvent(self, event: Any) -> None:  # noqa: N802
                frame = self._frame_at_event(event)
                if frame is None:
                    self._host.select_rail("")
                    self._drag_preset_id = ""
                    event.accept()
                    return
                if event.button() == qt.QtCore.Qt.RightButton:
                    self._host.open_options(frame.preset_id)
                else:
                    self._host.select_rail(frame.preset_id)
                    if not frame.locked:
                        point = event.pos()
                        self._drag_preset_id = frame.preset_id
                        self._drag_offset = (point.x() - frame.x, point.y() - frame.y)
                event.accept()

            def mouseMoveEvent(self, event: Any) -> None:  # noqa: N802
                if not self._drag_preset_id:
                    event.accept()
                    return
                point = event.pos()
                self._host.set_selected_position(
                    point.x() - self._drag_offset[0],
                    point.y() - self._drag_offset[1],
                    apply_snapping=True,
                )
                event.accept()

            def mouseReleaseEvent(self, event: Any) -> None:  # noqa: N802
                self._drag_preset_id = ""
                event.accept()

            def resizeEvent(self, event: Any) -> None:  # noqa: N802
                self._panel.sync()
                self._panel.move(
                    max(8, int((self.width() - self._panel.width()) / 2)),
                    18,
                )
                self._sync_popover()
                self._sync_options_popover()
                super().resizeEvent(event)

            def _frame_at_event(self, event: Any) -> RailFrameInfo | None:
                point = event.pos()
                return _topmost_frame_at(self._host.frames, point.x(), point.y())

            def _sync_popover(self) -> None:
                frame = self._host.selected_frame()
                self._popover.sync(frame)

            def _sync_options_popover(self) -> None:
                frame = self._host.selected_frame()
                if frame is not None and frame.preset_id != _OPTIONS_PRESET_ID:
                    frame = None
                self._options_popover.sync(frame)

        return _Canvas(host)


class _EditModePanel:  # pragma: no cover - covered by Maya smoke tests.
    def __new__(cls, canvas: Any) -> Any:
        qt = load()

        class _Panel(qt.QtWidgets.QFrame):
            def __init__(self, owner: Any) -> None:
                super().__init__(owner)
                self._owner = owner
                self.setObjectName(EDIT_PANEL_OBJECT_NAME)
                self.setFrameShape(qt.QtWidgets.QFrame.StyledPanel)
                self.setStyleSheet(_panel_style_sheet())
                layout = qt.QtWidgets.QGridLayout(self)
                layout.setContentsMargins(12, 8, 12, 8)
                layout.setHorizontalSpacing(8)
                layout.setVerticalSpacing(4)

                self.title = qt.QtWidgets.QLabel("ActionRail Edit Mode")
                self.title.setAlignment(qt.QtCore.Qt.AlignCenter)
                self.summary = qt.QtWidgets.QLabel("")
                self.summary.setAlignment(qt.QtCore.Qt.AlignCenter)
                self.summary.setWordWrap(True)
                self.grid_check = qt.QtWidgets.QCheckBox("Grid")
                self.snap_check = qt.QtWidgets.QCheckBox("Snap to Grid")
                self.sticky_check = qt.QtWidgets.QCheckBox("Sticky Frames")
                self.grid_size = qt.QtWidgets.QSpinBox()
                self.grid_size.setRange(MIN_GRID_SIZE, MAX_GRID_SIZE)
                self.grid_size.setSingleStep(4)
                self.grid_size_label = qt.QtWidgets.QLabel("Grid Size")
                self.lock_button = qt.QtWidgets.QPushButton("Lock")
                self.lock_button.setEnabled(False)

                layout.addWidget(self.title, 0, 0, 1, 4)
                layout.addWidget(self.summary, 1, 0, 1, 4)
                layout.addWidget(self.grid_check, 2, 0)
                layout.addWidget(self.grid_size_label, 2, 1)
                layout.addWidget(self.grid_size, 2, 2)
                layout.addWidget(self.lock_button, 2, 3)
                layout.addWidget(self.snap_check, 3, 0, 1, 2)
                layout.addWidget(self.sticky_check, 3, 2, 1, 2)
                self.adjustSize()
                self._resize_to_owner()

                self.grid_check.toggled.connect(
                    lambda checked: set_edit_mode_options(show_grid=checked)
                )
                self.snap_check.toggled.connect(
                    lambda checked: set_edit_mode_options(snap_to_grid=checked)
                )
                self.sticky_check.toggled.connect(
                    lambda checked: set_edit_mode_options(sticky_frames=checked)
                )
                self.grid_size.valueChanged.connect(
                    lambda value: set_edit_mode_options(grid_size=value)
                )
                self.sync()

            def sync(self) -> None:
                settings = self._owner._host.settings
                selected = self._owner._host.selected_frame()
                self._set_checked(self.grid_check, settings.show_grid)
                self._set_checked(self.snap_check, settings.snap_to_grid)
                self._set_checked(self.sticky_check, settings.sticky_frames)
                self._set_spin_value(self.grid_size, settings.grid_size)
                self.grid_size.setEnabled(settings.show_grid)
                self.grid_size_label.setEnabled(settings.show_grid)
                self.summary.setText(
                    _panel_summary_text(
                        selected,
                        len(self._owner._host.frames),
                        _OPTIONS_PRESET_ID,
                    )
                )
                self.lock_button.setText(_lock_button_text(selected))
                self._resize_to_owner()
                self.setFixedHeight(self.sizeHint().height())

            def _resize_to_owner(self) -> None:
                self.setFixedWidth(
                    _panel_width(
                        self._owner.width(),
                        max(540, self.sizeHint().width()),
                    )
                )

            def _set_checked(self, checkbox: Any, checked: bool) -> None:
                blocked = checkbox.blockSignals(True)
                checkbox.setChecked(checked)
                checkbox.blockSignals(blocked)

            def _set_spin_value(self, spinbox: Any, value: int) -> None:
                blocked = spinbox.blockSignals(True)
                spinbox.setValue(value)
                spinbox.blockSignals(blocked)

        return _Panel(canvas)


class _PositionPopover:  # pragma: no cover - covered by Maya smoke tests.
    def __new__(cls, canvas: Any) -> Any:
        qt = load()

        class _Popover(qt.QtWidgets.QFrame):
            def __init__(self, owner: Any) -> None:
                super().__init__(owner)
                self._owner = owner
                self._syncing = False
                self.setObjectName(POSITION_POPOVER_OBJECT_NAME)
                self.setFrameShape(qt.QtWidgets.QFrame.StyledPanel)
                self.setStyleSheet(_panel_style_sheet())
                layout = qt.QtWidgets.QGridLayout(self)
                layout.setContentsMargins(8, 6, 8, 6)
                layout.setHorizontalSpacing(5)
                layout.setVerticalSpacing(4)
                self.name_label = qt.QtWidgets.QLabel("")
                self.name_label.setAlignment(qt.QtCore.Qt.AlignCenter)
                self.up = qt.QtWidgets.QToolButton()
                self.left = qt.QtWidgets.QToolButton()
                self.right = qt.QtWidgets.QToolButton()
                self.down = qt.QtWidgets.QToolButton()
                self.up.setText("^")
                self.left.setText("<")
                self.right.setText(">")
                self.down.setText("v")
                self.x_spin = qt.QtWidgets.QSpinBox()
                self.y_spin = qt.QtWidgets.QSpinBox()
                for spin in (self.x_spin, self.y_spin):
                    spin.setRange(-10000, 10000)
                self.reset = qt.QtWidgets.QPushButton("Reset")
                layout.addWidget(self.name_label, 0, 0, 1, 4)
                layout.addWidget(self.up, 1, 1)
                layout.addWidget(self.left, 2, 0)
                layout.addWidget(self.right, 2, 2)
                layout.addWidget(self.down, 3, 1)
                layout.addWidget(qt.QtWidgets.QLabel("X"), 1, 3)
                layout.addWidget(self.x_spin, 2, 3)
                layout.addWidget(qt.QtWidgets.QLabel("Y"), 3, 3)
                layout.addWidget(self.y_spin, 4, 3)
                layout.addWidget(self.reset, 4, 0, 1, 3)
                self.adjustSize()
                self.setFixedSize(max(210, self.sizeHint().width()), self.sizeHint().height())
                self.up.clicked.connect(lambda: self._owner._host.nudge_selected(0, -1))
                self.down.clicked.connect(lambda: self._owner._host.nudge_selected(0, 1))
                self.left.clicked.connect(lambda: self._owner._host.nudge_selected(-1, 0))
                self.right.clicked.connect(lambda: self._owner._host.nudge_selected(1, 0))
                self.reset.clicked.connect(self._owner._host.reset_selected_position)
                self.x_spin.valueChanged.connect(lambda _value: self._spin_changed("x"))
                self.y_spin.valueChanged.connect(lambda _value: self._spin_changed("y"))

            def sync(self, frame: RailFrameInfo | None) -> None:
                if frame is None:
                    self.hide()
                    return
                self._syncing = True
                self.name_label.setText(frame.label)
                self.x_spin.setValue(frame.x)
                self.y_spin.setValue(frame.y)
                self._syncing = False
                locked = frame.locked
                for control in (
                    self.up,
                    self.down,
                    self.left,
                    self.right,
                    self.x_spin,
                    self.y_spin,
                    self.reset,
                ):
                    control.setEnabled(not locked)
                self.move(_popover_position(self._owner, frame, self.width(), self.height()))
                self.show()
                self.raise_()

            def _spin_changed(self, axis: str) -> None:
                if self._syncing:
                    return
                self._owner._host.set_selected_position(
                    self.x_spin.value(),
                    self.y_spin.value(),
                    apply_snapping=True,
                    snap_axes=(axis,),
                )

        return _Popover(canvas)


class _FrameOptionsPopover:  # pragma: no cover - covered by Maya smoke tests.
    def __new__(cls, canvas: Any) -> Any:
        qt = load()

        class _Options(qt.QtWidgets.QFrame):
            def __init__(self, owner: Any) -> None:
                super().__init__(owner)
                self._owner = owner
                self.setObjectName(FRAME_OPTIONS_POPOVER_OBJECT_NAME)
                self.setFrameShape(qt.QtWidgets.QFrame.StyledPanel)
                self.setStyleSheet(_panel_style_sheet())
                layout = qt.QtWidgets.QGridLayout(self)
                layout.setContentsMargins(10, 8, 10, 8)
                layout.setHorizontalSpacing(6)
                layout.setVerticalSpacing(5)
                self.title = qt.QtWidgets.QLabel("")
                self.title.setAlignment(qt.QtCore.Qt.AlignCenter)
                self.details = qt.QtWidgets.QLabel("")
                self.details.setWordWrap(True)
                self.status = qt.QtWidgets.QLabel("")
                self.status.setWordWrap(True)
                self.save = qt.QtWidgets.QPushButton("Save Position")
                self.reset = qt.QtWidgets.QPushButton("Reset Position")
                self.add_slot = qt.QtWidgets.QPushButton("Add Slot")
                self.remove_slot = qt.QtWidgets.QPushButton("Remove Slot")
                self.slot_up = qt.QtWidgets.QPushButton("Slot Up")
                self.slot_down = qt.QtWidgets.QPushButton("Slot Down")
                self.collapse = qt.QtWidgets.QPushButton("Collapse Edge Tab")
                self.close_button = qt.QtWidgets.QToolButton()
                self.close_button.setText("x")
                layout.addWidget(self.title, 0, 0, 1, 2)
                layout.addWidget(self.close_button, 0, 2)
                layout.addWidget(self.details, 1, 0, 1, 3)
                layout.addWidget(self.status, 2, 0, 1, 3)
                layout.addWidget(self.save, 3, 0, 1, 3)
                layout.addWidget(self.reset, 4, 0, 1, 3)
                layout.addWidget(self.add_slot, 5, 0, 1, 3)
                layout.addWidget(self.remove_slot, 6, 0, 1, 3)
                layout.addWidget(self.slot_up, 7, 0)
                layout.addWidget(self.slot_down, 7, 1)
                layout.addWidget(self.collapse, 8, 0, 1, 3)
                self.setFixedWidth(260)
                self.close_button.clicked.connect(self._close_options)
                self.save.clicked.connect(self._save_options)
                self.reset.clicked.connect(self._owner._host.reset_selected_position)
                self.add_slot.clicked.connect(self._add_slot)
                self.remove_slot.clicked.connect(self._remove_slot)
                self.slot_up.clicked.connect(lambda: self._move_slot(-1))
                self.slot_down.clicked.connect(lambda: self._move_slot(1))
                self.collapse.clicked.connect(self._collapse_edge_tab)

            def sync(self, frame: RailFrameInfo | None) -> None:
                if frame is None:
                    self.hide()
                    return
                self.title.setText(f"{frame.label} Options")
                lock_text = "Locked" if frame.locked else "Unlocked"
                self.details.setText(
                    f"{frame.source_layer.title()} rail\n"
                    f"{frame.anchor}\n"
                    f"Offset {frame.offset[0]}, {frame.offset[1]} | {lock_text}\n"
                    f"Collapse {frame.collapse_edge} | "
                    f"{'collapsed' if frame.collapsed else 'expanded'}"
                )
                self.status.setText(_save_status_text(frame))
                self.save.setEnabled(_can_save_frame(frame))
                self.reset.setEnabled(not frame.locked)
                self.add_slot.setEnabled(not frame.locked)
                self.remove_slot.setEnabled(not frame.locked)
                self.slot_up.setEnabled(not frame.locked)
                self.slot_down.setEnabled(not frame.locked)
                self.collapse.setEnabled(not frame.locked and _is_edge_anchor(frame.anchor))
                self.collapse.setText(
                    "Expand Edge Tab" if frame.collapsed else "Collapse Edge Tab"
                )
                self.setFixedHeight(self.sizeHint().height())
                self.move(
                    _options_popover_position(
                        self._owner,
                        frame,
                        self.width(),
                        self.height(),
                    )
                )
                self.show()
                self.raise_()

            def _close_options(self) -> None:
                global _OPTIONS_PRESET_ID
                _OPTIONS_PRESET_ID = ""
                self._owner.refresh_from_host()

            def _save_options(self) -> None:
                try:
                    path = self._owner._host.save_selected_layout()
                except Exception as exc:
                    self.status.setText(str(exc))
                    self.save.setEnabled(False)
                    self.setFixedHeight(self.sizeHint().height())
                    return
                self.status.setText(f"Saved {path.name}")
                self.setFixedHeight(self.sizeHint().height())

            def _add_slot(self) -> None:
                self._set_action_status(self._owner._host.add_slot_to_selected(), "Added slot")

            def _remove_slot(self) -> None:
                self._set_action_status(
                    self._owner._host.remove_slot_from_selected(),
                    "Removed slot",
                )

            def _move_slot(self, delta: int) -> None:
                self._set_action_status(
                    self._owner._host.reorder_selected_slot(delta),
                    "Reordered slot",
                )

            def _collapse_edge_tab(self) -> None:
                self._set_action_status(
                    self._owner._host.toggle_selected_edge_tab(),
                    "Toggled edge tab",
                )

            def _set_action_status(self, ok: bool, text: str) -> None:
                self.status.setText(text if ok else "Action unavailable")
                self.setFixedHeight(self.sizeHint().height())

        return _Options(canvas)


def _rail_frame_infos(qt: Any, edit_parent: Any) -> tuple[RailFrameInfo, ...]:
    frames: list[RailFrameInfo] = []
    for preset_id, host in _runtime_hosts().items():
        frame = _rail_frame_info(qt, edit_parent, preset_id, host)
        if frame is not None:
            frames.append(frame)
    return tuple(frames)


def _rail_frame_info(
    qt: Any,
    edit_parent: Any,
    preset_id: str,
    host: Any,
) -> RailFrameInfo | None:
    widget = getattr(host, "widget", None)
    if widget is None or not _safe_widget_visible(widget):
        return None

    width = _safe_widget_dimension(widget, "width")
    height = _safe_widget_dimension(widget, "height")
    if width <= 0 or height <= 0:
        return None

    x_pos, y_pos = _widget_position_in_parent(qt, edit_parent, widget)
    spec = getattr(host, "spec", None)
    layout = getattr(spec, "layout", None)
    if spec is None or layout is None:
        return None
    collapse = getattr(spec, "collapse", None)
    return RailFrameInfo(
        preset_id=preset_id,
        label=_frame_label(preset_id),
        x=x_pos,
        y=y_pos,
        width=width,
        height=height,
        anchor=str(getattr(layout, "anchor", "")),
        offset=tuple(getattr(layout, "offset", (0, 0))),
        orientation=str(getattr(layout, "orientation", "")),
        rows=int(getattr(layout, "rows", 1)),
        columns=int(getattr(layout, "columns", 1)),
        scale=float(getattr(layout, "scale", 1.0)),
        opacity=float(getattr(layout, "opacity", 1.0)),
        locked=bool(getattr(layout, "locked", False)),
        collapse_enabled=bool(getattr(collapse, "enabled", False)),
        collapse_edge=str(getattr(collapse, "edge", "left")),
        collapsed=bool(getattr(host, "_collapsed", False)),
        source_layer=_preset_source_layer(
            preset_id,
            user_preset_dir=getattr(host, "user_preset_dir", None),
        ),
    )


def _runtime_hosts() -> dict[str, Any]:
    from . import runtime

    return dict(runtime._active_overlay_hosts())


def _set_host_offset(host: Any, offset: tuple[int, int]) -> None:
    update = getattr(host, "update_layout_offset", None)
    if callable(update):
        update(offset)
        return
    spec = getattr(host, "spec", None)
    layout = getattr(spec, "layout", None)
    if spec is None or layout is None:
        return
    host.spec = dataclass_replace(spec, layout=dataclass_replace(layout, offset=offset))
    position = getattr(host, "position", None)
    if callable(position):
        position()


def _replace_host_spec(host: Any, spec: Any) -> None:
    host.spec = spec
    rebuild = getattr(host, "_rebuild_widget", None)
    if callable(rebuild):
        state_snapshot = None
        snapshot_fn = getattr(host, "cmds", None)
        try:
            from .state import snapshot

            state_snapshot = snapshot(snapshot_fn, active_panel=getattr(host, "panel", None))
        except Exception:
            state_snapshot = None
        rebuild(state_snapshot)
        return
    position = getattr(host, "position", None)
    if callable(position):
        position()


def _next_slot_number(spec: Any) -> int:
    prefix = f"{spec.id}.slot_"
    used: set[int] = set()
    for item in spec.items:
        item_id = str(getattr(item, "id", ""))
        if not item_id.startswith(prefix):
            continue
        suffix = item_id.removeprefix(prefix)
        if suffix.isdigit():
            used.add(int(suffix))
    number = 1
    while number in used:
        number += 1
    return number


def _last_action_item_index(items: tuple[Any, ...]) -> int | None:
    for index in range(len(items) - 1, -1, -1):
        if getattr(items[index], "type", "") != "spacer":
            return index
    return None


def _is_edge_anchor(anchor: str) -> bool:
    return any(f".{edge}." in anchor for edge in ("left", "right", "top", "bottom"))


def _edge_from_anchor(anchor: str) -> str:
    for edge in ("left", "right", "top", "bottom"):
        if f".{edge}." in anchor:
            return edge
    return "left"


def _user_override_spec(spec: Any) -> Any:
    return dataclass_replace(
        spec,
        id=_user_override_id(str(getattr(spec, "id", ""))),
        layout=dataclass_replace(spec.layout, locked=False),
        items=tuple(_override_item_id(spec.id, item) for item in spec.items),
    )


def _user_override_id(preset_id: str) -> str:
    from .preset_store import preset_user_override_id

    return preset_user_override_id(preset_id)


def _override_item_id(preset_id: str, item: Any) -> Any:
    override_id = _user_override_id(preset_id)
    item_id = str(getattr(item, "id", ""))
    prefix = f"{preset_id}."
    if item_id.startswith(prefix):
        item_id = f"{override_id}.{item_id.removeprefix(prefix)}"
    return dataclass_replace(item, id=item_id)


def _preset_source_layer(
    preset_id: str,
    *,
    user_preset_dir: str | Path | None = None,
) -> str:
    try:
        from .preset_store import PresetStore

        store = PresetStore(
            user_preset_dir=user_preset_dir,
            studio_preset_dir=_studio_preset_dir_from_runtime_host(preset_id),
        )
        source = store.entry(preset_id).source
        if source in {"builtin_override", "studio_override"}:
            return source.removesuffix("_override")
        return source
    except Exception:
        return "runtime"
    return "runtime"


def _studio_preset_dir_from_runtime_host(preset_id: str) -> Path | None:
    host = _runtime_hosts().get(preset_id)
    value = getattr(host, "studio_preset_dir", None)
    return Path(value) if value is not None else None


def _widget_position_in_parent(qt: Any, parent: Any, widget: Any) -> tuple[int, int]:
    try:
        origin = qt.QtCore.QPoint(0, 0)
        global_pos = widget.mapToGlobal(origin)
        local_pos = parent.mapFromGlobal(global_pos)
        return int(local_pos.x()), int(local_pos.y())
    except Exception:
        pass
    try:
        geometry = widget.geometry()
        return int(geometry.x()), int(geometry.y())
    except Exception:
        return (0, 0)


def _safe_widget_visible(widget: Any) -> bool:
    visible = getattr(widget, "isVisible", None)
    if not callable(visible):
        return False
    try:
        return bool(visible())
    except Exception:
        return False


def _safe_widget_dimension(widget: Any, method_name: str) -> int:
    method = getattr(widget, method_name, None)
    if not callable(method):
        return 0
    try:
        return int(method())
    except Exception:
        return 0


def _topmost_frame_at(
    frames: tuple[RailFrameInfo, ...],
    x_pos: int,
    y_pos: int,
) -> RailFrameInfo | None:
    for frame in reversed(frames):
        if frame.contains(x_pos, y_pos):
            return frame
    return None


def _snapped_position(
    frame: RailFrameInfo,
    x_pos: int,
    y_pos: int,
    settings: EditModeSettings,
    frames: tuple[RailFrameInfo, ...],
    *,
    snap_axes: tuple[str, ...] = ("x", "y"),
    bounds: tuple[int, int] | None = None,
) -> tuple[int, int]:
    snap_x = "x" in snap_axes
    snap_y = "y" in snap_axes
    if settings.sticky_frames:
        sticky_x, sticky_y = _sticky_snap_position(frame, x_pos, y_pos, frames)
        x_pos = sticky_x if snap_x else x_pos
        y_pos = sticky_y if snap_y else y_pos
    if settings.snap_to_grid:
        if snap_x:
            x_pos = _snap_value_to_grid(x_pos, settings.grid_size)
        if snap_y:
            y_pos = _snap_value_to_grid(y_pos, settings.grid_size)
    return _clamped_frame_position(frame, x_pos, y_pos, frames, bounds=bounds)


def _snap_axes_for_delta(dx: int, dy: int) -> tuple[str, ...]:
    axes = []
    if dx:
        axes.append("x")
    if dy:
        axes.append("y")
    return tuple(axes) or ("x", "y")


def _nudge_delta(delta: int, step: int) -> int:
    if delta == 0:
        return 0
    return step if delta > 0 else -step


def _snap_value_to_grid(value: int, grid_size: int) -> int:
    grid_size = max(MIN_GRID_SIZE, int(grid_size))
    return int(round(value / grid_size) * grid_size)


def _clamped_frame_position(
    frame: RailFrameInfo,
    x_pos: int,
    y_pos: int,
    frames: tuple[RailFrameInfo, ...],
    *,
    bounds: tuple[int, int] | None = None,
) -> tuple[int, int]:
    _ = frames
    width, height = bounds or DEFAULT_SAFE_BOUNDS
    max_x = max(SAFE_MARGIN, width - frame.width - SAFE_MARGIN)
    max_y = max(SAFE_MARGIN, height - frame.height - SAFE_MARGIN)
    return (
        min(max(SAFE_MARGIN, x_pos), max_x),
        min(max(SAFE_MARGIN, y_pos), max_y),
    )


def _safe_widget_size(widget: Any) -> tuple[int, int] | None:
    width = _safe_widget_dimension(widget, "width")
    height = _safe_widget_dimension(widget, "height")
    if width <= 0 or height <= 0:
        return None
    return (width, height)


def _sticky_snap_position(
    frame: RailFrameInfo,
    x_pos: int,
    y_pos: int,
    frames: tuple[RailFrameInfo, ...],
) -> tuple[int, int]:
    x_candidates = _edge_candidates(x_pos, frame.width)
    y_candidates = _edge_candidates(y_pos, frame.height)
    other_x_edges: list[int] = []
    other_y_edges: list[int] = []
    for other in frames:
        if other.preset_id == frame.preset_id:
            continue
        other_x_edges.extend(_edge_candidates(other.x, other.width))
        other_y_edges.extend(_edge_candidates(other.y, other.height))
    return (
        _snap_axis_position(x_pos, x_candidates, other_x_edges),
        _snap_axis_position(y_pos, y_candidates, other_y_edges),
    )


def _edge_candidates(position: int, size: int) -> tuple[int, int, int]:
    return (position, position + int(size / 2), position + size)


def _snap_axis_position(
    position: int,
    candidates: tuple[int, int, int],
    targets: list[int],
) -> int:
    best_delta = 0
    best_distance = STICKY_SNAP_THRESHOLD + 1
    for candidate in candidates:
        for target in targets:
            distance = abs(candidate - target)
            if distance < best_distance:
                best_distance = distance
                best_delta = target - candidate
    if best_distance <= STICKY_SNAP_THRESHOLD:
        return position + best_delta
    return position


def _paint_guides(  # pragma: no cover - covered by Maya smoke screenshots.
    qt: Any,
    painter: Any,
    rect: Any,
    frame: RailFrameInfo,
    frames: tuple[RailFrameInfo, ...],
    settings: EditModeSettings,
) -> None:
    guide = qt.QtGui.QColor(112, 226, 255, 135)
    painter.setPen(qt.QtGui.QPen(guide, 1))
    for x_pos in (frame.x, frame.x + int(frame.width / 2), frame.right):
        painter.drawLine(x_pos, 0, x_pos, rect.height())
    for y_pos in (frame.y, frame.y + int(frame.height / 2), frame.bottom):
        painter.drawLine(0, y_pos, rect.width(), y_pos)
    if not settings.sticky_frames:
        return
    for other in frames:
        if other.preset_id == frame.preset_id:
            continue
        if abs(other.x - frame.right) <= STICKY_SNAP_THRESHOLD:
            painter.drawLine(frame.right, frame.y, other.x, other.y)
        if abs(other.y - frame.bottom) <= STICKY_SNAP_THRESHOLD:
            painter.drawLine(frame.x, frame.bottom, other.x, other.y)


def _paint_grid(  # pragma: no cover - covered by Maya smoke screenshots.
    qt: Any,
    painter: Any,
    rect: Any,
    grid_size: int,
) -> None:
    minor = qt.QtGui.QColor(20, 80, 110, 105)
    major = qt.QtGui.QColor(42, 167, 227, 145)
    grid_size = max(MIN_GRID_SIZE, int(grid_size))
    painter.setPen(qt.QtGui.QPen(minor, 1))
    for x_pos in range(0, rect.width() + grid_size, grid_size):
        painter.setPen(qt.QtGui.QPen(major if x_pos % (grid_size * 4) == 0 else minor, 1))
        painter.drawLine(x_pos, 0, x_pos, rect.height())
    for y_pos in range(0, rect.height() + grid_size, grid_size):
        painter.setPen(qt.QtGui.QPen(major if y_pos % (grid_size * 4) == 0 else minor, 1))
        painter.drawLine(0, y_pos, rect.width(), y_pos)


def _paint_frame(  # pragma: no cover - covered by Maya smoke screenshots.
    qt: Any,
    painter: Any,
    frame: RailFrameInfo,
    selected: bool,
) -> None:
    rect = qt.QtCore.QRect(frame.x, frame.y, frame.width, frame.height)
    painter.fillRect(rect, qt.QtGui.QColor(2, 8, 12, 178))
    outline = qt.QtGui.QColor(0, 176, 255, 235)
    if selected:
        outline = qt.QtGui.QColor(255, 211, 0, 255)
    painter.setPen(qt.QtGui.QPen(outline, 2 if selected else 1))
    painter.drawRect(rect.adjusted(0, 0, -1, -1))
    _paint_drag_handle(qt, painter, frame)
    _paint_anchor_pin(qt, painter, frame)
    painter.setPen(qt.QtGui.QColor(0, 184, 255, 255))
    font = painter.font()
    font.setBold(True)
    font.setPointSize(_frame_label_font_size(frame))
    painter.setFont(font)
    label = f"{frame.label}\n{frame.source_layer.title()}"
    if frame.locked:
        label = f"{label}\nLocked"
    elif frame.collapse_enabled:
        label = f"{label}\n{'Collapsed' if frame.collapsed else 'Expanded'}"
    painter.drawText(rect, qt.QtCore.Qt.AlignCenter | qt.QtCore.Qt.TextWordWrap, label)


def _paint_drag_handle(  # pragma: no cover - covered by Maya smoke screenshots.
    qt: Any,
    painter: Any,
    frame: RailFrameInfo,
) -> None:
    handle = qt.QtCore.QRect(frame.right - 16, frame.y + 4, 12, 12)
    painter.fillRect(handle, qt.QtGui.QColor(112, 226, 255, 190))


def _paint_anchor_pin(  # pragma: no cover - covered by Maya smoke screenshots.
    qt: Any,
    painter: Any,
    frame: RailFrameInfo,
) -> None:
    radius = 5
    x_pos = frame.x + int(frame.width / 2)
    y_pos = frame.y + int(frame.height / 2)
    if ".left." in frame.anchor:
        x_pos = frame.x + radius + 2
    elif ".right." in frame.anchor:
        x_pos = frame.right - radius - 2
    if ".top." in frame.anchor:
        y_pos = frame.y + radius + 2
    elif ".bottom." in frame.anchor:
        y_pos = frame.bottom - radius - 2
    painter.setBrush(qt.QtGui.QColor(155, 216, 200, 210))
    painter.setPen(qt.QtGui.QPen(qt.QtGui.QColor(5, 30, 38, 220), 1))
    painter.drawEllipse(x_pos - radius, y_pos - radius, radius * 2, radius * 2)


def _frame_label_font_size(frame: RailFrameInfo) -> int:
    longest_word = max((len(word) for word in frame.label.split()), default=1)
    width_limited = int((frame.width / max(longest_word, 1)) * 1.4)
    height_limited = int(frame.height / 3)
    return max(6, min(10, width_limited, height_limited))


def _popover_position(canvas: Any, frame: RailFrameInfo, width: int, height: int) -> Any:
    x_pos = min(max(8, frame.right + 8), max(8, canvas.width() - width - 8))
    y_pos = min(max(8, frame.y), max(8, canvas.height() - height - 8))
    return canvas._host.qt.QtCore.QPoint(x_pos, y_pos)


def _panel_width(canvas_width: int, desired_width: int) -> int:
    desired_width = max(320, desired_width)
    if canvas_width <= 0:
        return desired_width
    return min(desired_width, max(1, canvas_width - 16))


def _options_popover_position(canvas: Any, frame: RailFrameInfo, width: int, height: int) -> Any:
    x_pos = min(max(8, frame.x), max(8, canvas.width() - width - 8))
    y_pos = min(max(8, frame.bottom + 8), max(8, canvas.height() - height - 8))
    return canvas._host.qt.QtCore.QPoint(x_pos, y_pos)


def _panel_summary_text(
    selected: RailFrameInfo | None,
    frame_count: int,
    options_preset_id: str,
) -> str:
    if selected is None:
        text = f"{frame_count} rail frame(s) | no frame selected"
    else:
        text = (
            f"{selected.label}\n"
            f"{selected.source_layer} | {selected.anchor} | x {selected.x}, y {selected.y}"
        )
    if options_preset_id:
        text = f"{text}\noptions: {options_preset_id}"
    return text


def _lock_button_text(selected: RailFrameInfo | None) -> str:
    if selected is None:
        return "No selection"
    return "Locked" if selected.locked else "Unlocked"


def _can_save_frame(frame: RailFrameInfo) -> bool:
    return not frame.locked


def _save_status_text(frame: RailFrameInfo) -> str:
    if frame.locked:
        return "Locked rails are read-only."
    if frame.source_layer == "builtin":
        return f"Save Position writes {_user_override_id(frame.preset_id)}."
    if frame.source_layer == "studio":
        return f"Save Position writes {_user_override_id(frame.preset_id)}."
    if frame.source_layer == "runtime":
        return "Save creates a user preset."
    return "Save updates the user preset."


def _frame_label(preset_id: str) -> str:
    return preset_id.replace("_", " ").title()


def _panel_style_sheet() -> str:
    return """
    QFrame {
        background: rgba(4, 8, 11, 205);
        border: 1px solid #00a8f5;
        color: #dff7ff;
    }
    QLabel {
        color: #dff7ff;
        border: 0;
        background: transparent;
    }
    QCheckBox {
        color: #ffd400;
        border: 0;
        background: transparent;
    }
    QSpinBox, QPushButton, QToolButton {
        background: #111820;
        border: 1px solid #00a8f5;
        color: #ffffff;
        min-height: 18px;
    }
    """


def _require_cmds(cmds_module: Any | None = None) -> Any:
    if cmds_module is not None:
        return cmds_module
    try:
        import maya.cmds as cmds  # type: ignore[import-not-found]
    except Exception as exc:  # pragma: no cover - exercised only inside Maya.
        msg = "ActionRail Edit Mode requires maya.cmds inside Maya."
        raise RuntimeError(msg) from exc
    return cmds
