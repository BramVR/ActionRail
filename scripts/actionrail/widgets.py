"""Qt widgets for ActionRail stack specs.

Purpose: turn validated preset data into compact Qt rail widgets.
Owns: button layout, custom painting, diagnostic badge application, predicate refresh.
Used by: the viewport overlay host; imports Qt only when building widgets.
Tests: `tests/test_widgets.py` and widget-focused Maya smoke scripts.
"""

from __future__ import annotations

from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass, replace

from . import slot_state as _slot_state
from .action_book import ACTION_BOOK_MIME_TYPE, action_book_action_id_from_mime_text
from .actions import ActionRegistry
from .bind_mode import HotkeyChord
from .hotkeys import HotkeyConflictError
from .predicates import PredicateContext
from .qt import load
from .slot_payloads import item_has_payload
from .spec import RailLayout, StackItem, StackSpec
from .state import MayaStateSnapshot
from .theme import (
    DEFAULT_THEME,
    ActionRailTheme,
    apply_appearance_overrides,
    generate_style_sheet,
)

BUTTON_SIZE = DEFAULT_THEME.button_size
BUTTON_OUTER_SIZE = DEFAULT_THEME.button_outer_size
DENSE_ACTION_BAR_MIN_SLOTS = 48
ACTION_RAIL_ROOT_OBJECT_NAME = "ActionRailRoot"
ACTION_RAIL_ROOT_PROPERTY = "actionRailRoot"
ACTION_RAIL_VIEWPORT_OVERLAY_PREFIX = "ActionRailViewportOverlay_"
COLLAPSED_HANDLE_SHORT_SIDE = 24
COLLAPSED_HANDLE_LONG_SIDE = 52
FRAME_PADDING = DEFAULT_THEME.frame_padding
FRAME_SPACING = DEFAULT_THEME.frame_spacing
RAIL_WIDTH = DEFAULT_THEME.rail_width
STYLE_SHEET = generate_style_sheet(DEFAULT_THEME)

__all__ = [
    "BUTTON_OUTER_SIZE",
    "BUTTON_SIZE",
    "COLLAPSED_HANDLE_LONG_SIDE",
    "COLLAPSED_HANDLE_SHORT_SIDE",
    "FRAME_PADDING",
    "FRAME_SPACING",
    "RAIL_WIDTH",
    "STYLE_SHEET",
    "ActionRailRoot",
    "DENSE_ACTION_BAR_MIN_SLOTS",
    "PredicateRefreshResult",
    "SlotEditCallbacks",
    "SlotRenderState",
    "build_rail",
    "build_collapsed_handle",
    "build_transform_stack",
    "event_should_pass_through_to_maya",
    "refresh_predicate_state",
    "resolve_slot_render_state",
    "set_slot_key_label",
]

SlotRenderState = _slot_state.SlotRenderState
_SlotDiagnostic = _slot_state._SlotDiagnostic
_availability_diagnostic = _slot_state._availability_diagnostic
_button_secondary_text = _slot_state.button_secondary_text
_button_text = _slot_state.button_text
_diagnostic_tooltip = _slot_state._diagnostic_tooltip
_icon_diagnostic = _slot_state._icon_diagnostic
_is_item_active = _slot_state.is_item_active
_is_item_visible = _slot_state.is_item_visible
_item_context = _slot_state._item_context
_slot_render_state = _slot_state.resolve_slot_render_state
_visible_action_items = _slot_state.visible_action_items


@dataclass(frozen=True)
class PredicateRefreshResult:
    """Result of applying fresh predicate state to an existing rail widget."""

    refreshed: int
    needs_rebuild: bool
    visible_slot_ids: tuple[str, ...]
    rendered_slot_ids: tuple[str, ...]


@dataclass(frozen=True)
class SlotEditCallbacks:
    """Runtime slot-edit hooks used when a rail is unlocked in Normal Mode."""

    unlocked: bool
    unlock_rail: Callable[[], bool]
    lock_rail: Callable[[], bool]
    assign_action: Callable[[str, str], bool]
    clear_slot: Callable[[str], bool]
    move_slot: Callable[[str, str], bool] | None = None
    owner: object | None = None
    transfer_slot: Callable[[str, SlotEditCallbacks, str], bool] | None = None


@dataclass(frozen=True)
class _SlotDragDropTarget:
    slot_id: str | None = None
    callbacks: SlotEditCallbacks | None = None
    inside_action_rail: bool = False
    same_rail: bool = False


@dataclass(frozen=True)
class _DenseSlot:
    item: StackItem
    state: SlotRenderState
    rect: object


class ActionRailRoot:
    """Factory wrapper for the root widget class.

    The actual class is built after loading Qt so importing this module outside
    Maya fails only when widgets are constructed.
    """

    @staticmethod
    def create() -> object:
        qt = load()

        class _ActionRailRoot(qt.QtWidgets.QWidget):
            def __init__(self) -> None:
                super().__init__()
                self.setObjectName(ACTION_RAIL_ROOT_OBJECT_NAME)
                self.setProperty(ACTION_RAIL_ROOT_PROPERTY, "true")
                self.setAttribute(qt.QtCore.Qt.WA_TranslucentBackground, True)
                self.setAttribute(qt.QtCore.Qt.WA_NoSystemBackground, True)
                self.setFocusPolicy(qt.QtCore.Qt.NoFocus)

            def mousePressEvent(self, event):  # type: ignore[no-untyped-def]
                if event_should_pass_through_to_maya(event, qt=qt):
                    event.ignore()
                    return None
                event.ignore()

            def mouseMoveEvent(self, event):  # type: ignore[no-untyped-def]
                if event_should_pass_through_to_maya(event, qt=qt):
                    event.ignore()
                    return None
                event.ignore()

            def mouseReleaseEvent(self, event):  # type: ignore[no-untyped-def]
                if event_should_pass_through_to_maya(event, qt=qt):
                    event.ignore()
                    return None
                event.ignore()

            def wheelEvent(self, event):  # type: ignore[no-untyped-def]
                if event_should_pass_through_to_maya(event, qt=qt):
                    event.ignore()
                    return None
                event.ignore()

        return _ActionRailRoot()


def build_rail(
    spec: StackSpec,
    registry: ActionRegistry,
    theme: ActionRailTheme = DEFAULT_THEME,
    state_snapshot: MayaStateSnapshot | None = None,
    cmds_module: object | None = None,
    slot_edit_callbacks: SlotEditCallbacks | None = None,
) -> object:
    """Build an ActionRail widget from a stack spec."""

    qt = load()
    theme = apply_appearance_overrides(theme, getattr(spec, "appearance", None))
    theme = _scaled_theme(theme, spec.layout.scale)
    context = PredicateContext(state=state_snapshot, registry=registry, cmds_module=cmds_module)
    if _should_use_dense_canvas(spec, slot_edit_callbacks):
        return _build_dense_action_bar(
            spec,
            registry,
            theme,
            context,
        )

    root = ActionRailRoot.create()
    root.setStyleSheet(generate_style_sheet(theme))
    root.setWindowOpacity(spec.layout.opacity)

    if _uses_wrapped_layout(spec.layout):
        layout = qt.QtWidgets.QGridLayout(root)
    else:
        layout_class = (
            qt.QtWidgets.QHBoxLayout
            if spec.layout.orientation == "horizontal"
            else qt.QtWidgets.QVBoxLayout
        )
        layout = layout_class(root)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)

    pending_tools: list[StackItem] = []
    rendered_entries: list[tuple[str, object | int]] = []
    for item in spec.items:
        if not _is_item_visible(item, context):
            continue

        if _should_group_slot_item(item, spec.layout):
            pending_tools.append(item)
            continue

        if pending_tools:
            rendered_entries.append(
                (
                    "widget",
                    _build_cluster(
                        tuple(pending_tools),
                        registry,
                        theme,
                        spec.id,
                        spec.layout.orientation,
                        context,
                        slot_edit_callbacks,
                    ),
                )
            )
            pending_tools.clear()

        if item.type == "spacer":
            if _uses_wrapped_layout(spec.layout):
                rendered_entries.append(
                    ("widget", _build_spacer(qt, item.size, spec.layout.orientation))
                )
            else:
                rendered_entries.append(("spacing", item.size))
            continue

        rendered_entries.append(
            (
                "widget",
                _build_single_button(
                    item,
                    registry,
                    theme,
                    spec.id,
                    spec.layout.orientation,
                    context,
                    slot_edit_callbacks,
                ),
            )
        )

    if pending_tools:
        rendered_entries.append(
            (
                "widget",
                _build_cluster(
                    tuple(pending_tools),
                    registry,
                    theme,
                    spec.id,
                    spec.layout.orientation,
                    context,
                    slot_edit_callbacks,
                ),
            )
        )

    widget_index = 0
    for entry_type, value in rendered_entries:
        if entry_type == "spacing":
            layout.addSpacing(value)
            continue
        widget = value
        if _uses_wrapped_layout(spec.layout):
            row, column = _grid_position(widget_index, spec.layout)
            layout.addWidget(widget, row, column, qt.QtCore.Qt.AlignLeft)
        else:
            layout.addWidget(widget, 0, qt.QtCore.Qt.AlignLeft)
        widget_index += 1

    root.adjustSize()
    root.setFixedSize(root.sizeHint())
    if slot_edit_callbacks is not None:
        _install_action_book_root_drop(qt, root, slot_edit_callbacks)
    return root


def build_collapsed_handle(
    spec: StackSpec,
    on_reveal: Callable[[], None],
    theme: ActionRailTheme = DEFAULT_THEME,
) -> object:
    """Build the small edge-tab handle shown while a rail is collapsed."""

    qt = load()
    theme = apply_appearance_overrides(theme, getattr(spec, "appearance", None))
    theme = _scaled_theme(theme, spec.layout.scale)
    root = ActionRailRoot.create()
    root.setStyleSheet(generate_style_sheet(theme))
    root.setWindowOpacity(spec.layout.opacity)

    layout = qt.QtWidgets.QVBoxLayout(root)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)
    handle = _collapsed_handle_button(qt, spec, on_reveal)
    layout.addWidget(handle)
    root.adjustSize()
    root.setFixedSize(root.sizeHint())
    return root


def _collapsed_handle_button(qt: object, spec: StackSpec, on_reveal: Callable[[], None]) -> object:
    button = qt.QtWidgets.QPushButton(_collapse_handle_label(spec))
    button.setProperty("actionRailRole", "collapsedHandle")
    button.setProperty("actionRailCollapsedPresetId", spec.id)
    button.setFocusPolicy(qt.QtCore.Qt.NoFocus)
    button.setCursor(qt.QtCore.Qt.PointingHandCursor)
    button.setToolTip(f"Show ActionRail rail: {spec.id}")
    button.setFixedSize(*_collapsed_handle_size(spec))
    button.clicked.connect(lambda _checked=False: on_reveal())
    if spec.collapse.reveal_trigger == "hover":
        base_enter = button.enterEvent

        def enter_event(event):  # type: ignore[no-untyped-def]
            on_reveal()
            return base_enter(event)

        button.enterEvent = enter_event  # type: ignore[method-assign]
    return button


def _collapsed_handle_size(spec: StackSpec) -> tuple[int, int]:
    short_side = max(
        COLLAPSED_HANDLE_SHORT_SIDE,
        round(COLLAPSED_HANDLE_SHORT_SIDE * spec.layout.scale),
    )
    long_side = max(
        COLLAPSED_HANDLE_LONG_SIDE,
        round(COLLAPSED_HANDLE_LONG_SIDE * spec.layout.scale),
    )
    if spec.collapse.edge in {"left", "right"}:
        return short_side, long_side
    return long_side, short_side


def _collapse_handle_label(spec: StackSpec) -> str:
    icon = spec.collapse.handle_icon
    chevrons = {
        "chevron-left": "<",
        "chevron-right": ">",
        "chevron-up": "^",
        "chevron-down": "v",
    }
    if icon in chevrons:
        return chevrons[icon]
    if icon:
        return icon[:3]
    return {
        "left": ">",
        "right": "<",
        "top": "v",
        "bottom": "^",
    }.get(spec.collapse.edge, ">")


def build_transform_stack(
    spec: StackSpec,
    registry: ActionRegistry,
    theme: ActionRailTheme = DEFAULT_THEME,
    state_snapshot: MayaStateSnapshot | None = None,
    cmds_module: object | None = None,
    slot_edit_callbacks: SlotEditCallbacks | None = None,
) -> object:
    """Compatibility wrapper for the generic ActionRail rail builder."""

    return build_rail(
        spec,
        registry,
        theme=theme,
        state_snapshot=state_snapshot,
        cmds_module=cmds_module,
        slot_edit_callbacks=slot_edit_callbacks,
    )


def _should_use_dense_canvas(
    spec: StackSpec,
    slot_edit_callbacks: SlotEditCallbacks | None = None,
) -> bool:
    if slot_edit_callbacks is not None and slot_edit_callbacks.unlocked:
        return False
    return _dense_slot_count(spec) >= DENSE_ACTION_BAR_MIN_SLOTS


def _dense_slot_count(spec: StackSpec) -> int:
    return sum(1 for item in spec.items if item.type in {"button", "toolButton"})


def _build_dense_action_bar(
    spec: StackSpec,
    registry: ActionRegistry,
    theme: ActionRailTheme,
    context: PredicateContext,
) -> object:
    qt = load()
    base = qt.QtWidgets.QWidget

    class DenseActionBar(base):  # type: ignore[misc, valid-type]
        def __init__(self) -> None:
            super().__init__()
            self.setObjectName(ACTION_RAIL_ROOT_OBJECT_NAME)
            self.setProperty(ACTION_RAIL_ROOT_PROPERTY, "true")
            self.setProperty("actionRailDense", "true")
            self.setAttribute(qt.QtCore.Qt.WA_TranslucentBackground, True)
            self.setAttribute(qt.QtCore.Qt.WA_NoSystemBackground, True)
            self.setFocusPolicy(qt.QtCore.Qt.NoFocus)
            self.setStyleSheet(generate_style_sheet(theme))
            self.setWindowOpacity(spec.layout.opacity)
            self._actionrail_spec = spec
            self._actionrail_registry = registry
            self._actionrail_theme = theme
            self._actionrail_slots: dict[str, _DenseSlot] = {}
            self._actionrail_visible_slot_ids: tuple[str, ...] = ()
            self._actionrail_icon_cache: dict[str, object] = {}
            self._actionrail_pixmap_cache: dict[tuple[str, int, int, float], object] = {}
            self._actionrail_refresh_dense(context)

        def _actionrail_refresh_dense(
            self,
            predicate_context: PredicateContext,
        ) -> PredicateRefreshResult:
            visible_items = tuple(_visible_action_items(spec, predicate_context))
            visible_slot_ids = tuple(item.id for item in visible_items)
            rendered_slot_ids = tuple(self._actionrail_slots)
            if rendered_slot_ids and visible_slot_ids != rendered_slot_ids:
                return PredicateRefreshResult(
                    refreshed=0,
                    needs_rebuild=True,
                    visible_slot_ids=visible_slot_ids,
                    rendered_slot_ids=rendered_slot_ids,
                )

            rects = _dense_slot_rects(qt, len(visible_items), spec.layout, theme)
            refreshed = 0
            slots: dict[str, _DenseSlot] = {}
            for item, rect in zip(visible_items, rects, strict=True):
                previous = self._actionrail_slots.get(item.id)
                previous_key = previous.state.key_label if previous is not None else None
                state = resolve_slot_render_state(
                    item,
                    registry,
                    predicate_context,
                    key_label=previous_key,
                )
                slots[item.id] = _DenseSlot(item=item, state=state, rect=rect)
                if previous is None or previous.state != state:
                    refreshed += 1
                    with suppress(Exception):
                        self.update(rect)
            self._actionrail_slots = slots
            self._actionrail_visible_slot_ids = visible_slot_ids
            size = _dense_bar_size(len(visible_items), spec.layout, theme)
            self.setFixedSize(size[0], size[1])
            return PredicateRefreshResult(
                refreshed=refreshed,
                needs_rebuild=False,
                visible_slot_ids=visible_slot_ids,
                rendered_slot_ids=visible_slot_ids,
            )

        def _actionrail_set_slot_key_label(self, slot_id: str, key_label: str) -> int:
            slot = self._actionrail_slots.get(slot_id)
            if slot is None:
                return 0
            state = replace(slot.state, key_label=key_label)
            self._actionrail_slots[slot_id] = replace(slot, state=state)
            with suppress(Exception):
                self.update(slot.rect)
            return 1

        def paintEvent(self, event):  # type: ignore[no-untyped-def]  # noqa: N802
            painter_class = getattr(qt.QtGui, "QPainter", None)
            if painter_class is None:
                return super().paintEvent(event)
            painter = painter_class(self)
            try:
                _paint_dense_backing(qt, painter, self.rect(), theme)
                for slot in self._actionrail_slots.values():
                    _paint_dense_slot(
                        qt,
                        painter,
                        slot,
                        theme,
                        icon_cache=self._actionrail_icon_cache,
                        pixmap_cache=self._actionrail_pixmap_cache,
                    )
            finally:
                painter.end()

        def mousePressEvent(self, event):  # type: ignore[no-untyped-def]  # noqa: N802
            if event_should_pass_through_to_maya(event, qt=qt):
                event.ignore()
                return None
            slot = _dense_slot_at_point(self._actionrail_slots.values(), _event_local_point(event))
            if slot is None or not slot.state.enabled:
                event.ignore()
                return None
            action_id = slot.item.action
            if action_id:
                registry.run(action_id)
                _accept_event(event)
                return None
            event.ignore()
            return None

        def mouseMoveEvent(self, event):  # type: ignore[no-untyped-def]  # noqa: N802
            event.ignore()

        def mouseReleaseEvent(self, event):  # type: ignore[no-untyped-def]  # noqa: N802
            event.ignore()

        def wheelEvent(self, event):  # type: ignore[no-untyped-def]  # noqa: N802
            if event_should_pass_through_to_maya(event, qt=qt):
                event.ignore()
                return None
            return super().wheelEvent(event)

    return DenseActionBar()


def _dense_bar_grid(slot_count: int, layout: RailLayout) -> tuple[int, int]:
    if slot_count <= 0:
        return (0, 0)
    if _uses_wrapped_layout(layout):
        columns = max(1, min(layout.columns, slot_count))
        rows = max(1, (slot_count + columns - 1) // columns)
        return rows, columns
    if layout.orientation == "horizontal":
        return 1, slot_count
    return slot_count, 1


def _dense_bar_size(
    slot_count: int,
    layout: RailLayout,
    theme: ActionRailTheme,
) -> tuple[int, int]:
    rows, columns = _dense_bar_grid(slot_count, layout)
    pad = theme.frame_padding + theme.cluster_border_width
    if rows == 0 or columns == 0:
        return theme.rail_width, theme.rail_width
    width = columns * theme.button_outer_size + max(0, columns - 1) * theme.frame_spacing
    height = rows * theme.button_outer_size + max(0, rows - 1) * theme.frame_spacing
    return width + pad * 2, height + pad * 2


def _dense_slot_rects(
    qt: object,
    slot_count: int,
    layout: RailLayout,
    theme: ActionRailTheme,
) -> tuple[object, ...]:
    rows, columns = _dense_bar_grid(slot_count, layout)
    if rows == 0 or columns == 0:
        return ()
    rects: list[object] = []
    pad = theme.frame_padding + theme.cluster_border_width
    for index in range(slot_count):
        if _uses_wrapped_layout(layout):
            row, column = _grid_position(index, layout)
        elif layout.orientation == "horizontal":
            row, column = 0, index
        else:
            row, column = index, 0
        x_pos = pad + column * (theme.button_outer_size + theme.frame_spacing)
        y_pos = pad + row * (theme.button_outer_size + theme.frame_spacing)
        rects.append(
            qt.QtCore.QRect(
                x_pos,
                y_pos,
                theme.button_outer_size,
                theme.button_outer_size,
            )
        )
    return tuple(rects)


def _paint_dense_backing(
    qt: object,
    painter: object,
    rect: object,
    theme: ActionRailTheme,
) -> None:
    painter.fillRect(
        rect,
        _qt_rgb_color(qt, *theme.cluster_base_rgb, alpha=theme.cluster_base_opacity),
    )
    pen = qt.QtGui.QPen(
        _qt_rgb_color(qt, *theme.cluster_stripe_rgb, alpha=theme.cluster_stripe_opacity)
    )
    pen.setWidth(max(1, int(round(theme.cluster_border_width * 0.5))))
    painter.setPen(pen)
    spacing = max(4, int(round(theme.button_size * 0.18 * theme.cluster_pattern_scale)))
    height = _rect_dimension(rect, "height")
    left = _rect_edge(rect, "left")
    right = _rect_edge(rect, "right")
    bottom = _rect_edge(rect, "bottom")
    top = _rect_edge(rect, "top")
    for x_pos in range(left - height, right + height + spacing, spacing):
        painter.drawLine(x_pos, bottom + 1, x_pos + height + spacing, top - 1)
    if theme.cluster_border_width:
        border_pen = qt.QtGui.QPen(_qt_color(qt, theme.cluster_border))
        border_pen.setWidth(theme.cluster_border_width)
        painter.setPen(border_pen)
        painter.setBrush(qt.QtCore.Qt.NoBrush)
        painter.drawRect(_adjusted_rect(rect, 0, 0, -1, -1))


def _paint_dense_slot(
    qt: object,
    painter: object,
    slot: _DenseSlot,
    theme: ActionRailTheme,
    *,
    icon_cache: dict[str, object] | None = None,
    pixmap_cache: dict[tuple[str, int, int, float], object] | None = None,
) -> None:
    state = slot.state
    rect = slot.rect
    painter.fillRect(rect, _qt_color(qt, theme.button_background))
    border = theme.button_active_border if state.active else theme.button_border
    if not state.enabled:
        border = theme.button_disabled_border
    pen = qt.QtGui.QPen(_qt_color(qt, border))
    pen.setWidth(max(1, theme.button_border_width))
    painter.setPen(pen)
    painter.setBrush(qt.QtCore.Qt.NoBrush)
    painter.drawRect(_adjusted_rect(rect, 0, 0, -1, -1))

    icon_source = _qt_icon_source(state.icon_path, state.icon_name)
    if icon_source:
        icon = _cached_icon(qt, icon_source, icon_cache)
        target = _adjusted_rect(rect, 3, 3, -3, -3)
        pixmap = _cached_icon_pixmap_for_painter(
            qt,
            painter,
            icon,
            target,
            icon_source,
            pixmap_cache,
        )
        if pixmap:
            painter.drawPixmap(target, pixmap)
    elif state.label:
        painter.setPen(_qt_color(qt, theme.button_color))
        painter.drawText(rect, qt.QtCore.Qt.AlignCenter, state.label)

    secondary = _button_secondary_text(state.key_label, state.diagnostic_badge)
    if secondary:
        font = painter.font()
        with suppress(Exception):
            font.setPointSize(_secondary_font_size(font.pointSize()))
            painter.setFont(font)
        painter.setPen(_qt_color(qt, theme.accent))
        painter.drawText(
            _adjusted_rect(rect, 2, 2, -2, -1),
            qt.QtCore.Qt.AlignRight | qt.QtCore.Qt.AlignBottom,
            secondary,
        )


def _cached_icon(
    qt: object,
    icon_source: str,
    icon_cache: dict[str, object] | None,
) -> object:
    if icon_cache is None:
        return qt.QtGui.QIcon(icon_source)
    icon = icon_cache.get(icon_source)
    if icon is None:
        icon = qt.QtGui.QIcon(icon_source)
        icon_cache[icon_source] = icon
    return icon


def _cached_icon_pixmap_for_painter(
    qt: object,
    painter: object,
    icon: object,
    target: object,
    icon_source: str,
    pixmap_cache: dict[tuple[str, int, int, float], object] | None,
) -> object:
    if pixmap_cache is None:
        return _icon_pixmap_for_painter(qt, painter, icon, target)
    key = _icon_pixmap_cache_key(painter, target, icon_source)
    pixmap = pixmap_cache.get(key)
    if pixmap is None:
        pixmap = _icon_pixmap_for_painter(qt, painter, icon, target)
        pixmap_cache[key] = pixmap
    return pixmap


def _icon_pixmap_cache_key(
    painter: object,
    target: object,
    icon_source: str,
) -> tuple[str, int, int, float]:
    size = target.size()
    return (
        icon_source,
        _qt_size_value(size, "width"),
        _qt_size_value(size, "height"),
        round(_painter_device_scale(painter), 3),
    )


def _rect_dimension(rect: object, method_name: str) -> int:
    method = getattr(rect, method_name, None)
    if callable(method):
        with suppress(Exception):
            return int(method())
    return 0


def _rect_edge(rect: object, method_name: str) -> int:
    method = getattr(rect, method_name, None)
    if callable(method):
        with suppress(Exception):
            return int(method())
    return 0


def _dense_slot_at_point(slots: object, point: object | None) -> _DenseSlot | None:
    if point is None:
        return None
    for slot in slots:
        contains = getattr(slot.rect, "contains", None)
        if callable(contains):
            with suppress(Exception):
                if contains(point):
                    return slot
    return None


def _build_cluster(
    items: tuple[StackItem, ...],
    registry: ActionRegistry,
    theme: ActionRailTheme,
    preset_id: str,
    orientation: str,
    context: PredicateContext | None = None,
    slot_edit_callbacks: SlotEditCallbacks | None = None,
) -> object:
    qt = load()
    frame = _cluster_frame_class(qt, theme)()
    frame.setProperty("actionRailRole", "cluster")
    layout_class = (
        qt.QtWidgets.QHBoxLayout
        if orientation == "horizontal"
        else qt.QtWidgets.QVBoxLayout
    )
    layout = layout_class(frame)
    content_margin = theme.frame_padding + theme.cluster_border_width
    layout.setContentsMargins(
        content_margin,
        content_margin,
        content_margin,
        content_margin,
    )
    layout.setSpacing(theme.frame_spacing)

    for item in items:
        layout.addWidget(
            _build_button(item, registry, theme, preset_id, context, slot_edit_callbacks)
        )

    main_axis_size = _frame_main_axis_size(len(items), theme)
    if orientation == "horizontal":
        frame.setFixedSize(main_axis_size, theme.rail_width)
    else:
        frame.setFixedSize(theme.rail_width, main_axis_size)
    return frame


def _build_single_button(
    item: StackItem,
    registry: ActionRegistry,
    theme: ActionRailTheme,
    preset_id: str,
    orientation: str,
    context: PredicateContext | None = None,
    slot_edit_callbacks: SlotEditCallbacks | None = None,
) -> object:
    qt = load()
    frame = _cluster_frame_class(qt, theme)()
    frame.setProperty("actionRailRole", "cluster")
    layout = qt.QtWidgets.QVBoxLayout(frame)
    content_margin = theme.frame_padding + theme.cluster_border_width
    layout.setContentsMargins(
        content_margin,
        content_margin,
        content_margin,
        content_margin,
    )
    layout.setSpacing(0)
    layout.addWidget(_build_button(item, registry, theme, preset_id, context, slot_edit_callbacks))

    frame.setFixedSize(theme.rail_width, theme.rail_width)
    return frame


def _cluster_frame_class(qt: object, theme: ActionRailTheme) -> type:
    base = qt.QtWidgets.QFrame
    if not hasattr(qt.QtGui, "QPainter") or not hasattr(qt.QtGui, "QPen"):
        return base

    class ActionRailClusterFrame(base):  # type: ignore[misc, valid-type]
        def paintEvent(self, event):  # type: ignore[no-untyped-def]  # noqa: N802
            painter = qt.QtGui.QPainter(self)
            try:
                border_width = max(0, int(theme.cluster_border_width))
                rect = self.rect()
                inner = rect.adjusted(
                    border_width,
                    border_width,
                    -border_width,
                    -border_width,
                )
                if theme.cluster_background_enabled:
                    painter.fillRect(
                        inner,
                        _qt_rgb_color(
                            qt,
                            *theme.cluster_base_rgb,
                            alpha=theme.cluster_base_opacity,
                        ),
                    )

                painter.save()
                try:
                    painter.setClipRect(inner)
                    pen = qt.QtGui.QPen(
                        _qt_rgb_color(
                            qt,
                            *theme.cluster_stripe_rgb,
                            alpha=theme.cluster_stripe_opacity,
                        )
                    )
                    pen.setWidth(max(1, int(round(border_width * 0.5))))
                    pen.setCapStyle(qt.QtCore.Qt.FlatCap)
                    painter.setPen(pen)
                    if (
                        theme.cluster_background_enabled
                        and theme.cluster_pattern == "diagonal_stripes"
                    ):
                        spacing = max(
                            4,
                            int(
                                round(
                                    theme.button_size
                                    * 0.18
                                    * theme.cluster_pattern_scale
                                )
                            ),
                        )
                        span = inner.height() + spacing
                        start = inner.left() - inner.height() - spacing
                        stop = inner.right() + inner.height() + spacing
                        for x_pos in range(start, stop, spacing):
                            painter.drawLine(
                                x_pos,
                                inner.bottom() + 1,
                                x_pos + span,
                                inner.top() - 1,
                            )
                finally:
                    painter.restore()

                if border_width:
                    pen = qt.QtGui.QPen(_qt_color(qt, theme.cluster_border))
                    pen.setWidth(border_width)
                    painter.setPen(pen)
                    painter.setBrush(qt.QtCore.Qt.NoBrush)
                    inset = max(0, int(border_width / 2))
                    border_rect = rect.adjusted(inset, inset, -inset - 1, -inset - 1)
                    painter.drawRect(border_rect)
            finally:
                painter.end()
                _ = event

    return ActionRailClusterFrame


def _build_spacer(qt: object, size: int, orientation: str) -> object:
    spacer = qt.QtWidgets.QWidget()
    if orientation == "horizontal":
        spacer.setFixedSize(size, 1)
    else:
        spacer.setFixedSize(1, size)
    return spacer


def _build_button(
    item: StackItem,
    registry: ActionRegistry,
    theme: ActionRailTheme,
    preset_id: str,
    context: PredicateContext | None = None,
    slot_edit_callbacks: SlotEditCallbacks | None = None,
) -> object:
    qt = load()
    state = resolve_slot_render_state(item, registry, context)
    button = _button_class(qt)(state.text)
    button.setProperty("actionRailRole", "button")
    button.setProperty("actionRailPresetId", preset_id)
    button.setProperty("actionRailSlotId", item.id)
    button.setProperty(
        "actionRailSlotEditUnlocked",
        "true" if slot_edit_callbacks is not None and slot_edit_callbacks.unlocked else "false",
    )
    button.setProperty("actionRailButtonIconSize", theme.button_size)
    button.setProperty("actionRailButtonBackplateInset", 0)
    button.setProperty("actionRailButtonIconInset", max(0, theme.spell_icon_inset - 1))
    button.setProperty("actionRailIconBackplate", theme.spell_icon_background)
    button.setProperty("actionRailIconBorder", theme.spell_icon_border)
    button.setProperty("actionRailButtonActiveBorder", theme.button_active_border)
    button.setFixedSize(theme.button_outer_size, theme.button_outer_size)
    button.setFocusPolicy(qt.QtCore.Qt.NoFocus)
    button.setCursor(
        qt.QtCore.Qt.PointingHandCursor if item.action else qt.QtCore.Qt.ArrowCursor
    )
    _apply_slot_render_state(button, state)
    if slot_edit_callbacks is not None:
        button._actionrail_slot_edit_callbacks = slot_edit_callbacks
        _install_slot_edit_menu(button, item, registry, slot_edit_callbacks)
        _install_action_book_drop(button, item, slot_edit_callbacks)
        _install_slot_drag_edit(button, item, slot_edit_callbacks)
    _install_bind_mode_capture(qt, button, item, preset_id)
    if item.action and not (
        slot_edit_callbacks is not None and slot_edit_callbacks.unlocked
    ):
        button.clicked.connect(
            lambda _checked=False, action_id=item.action: registry.run(action_id)
        )
    return button


def _install_slot_edit_menu(
    button: object,
    item: StackItem,
    registry: ActionRegistry,
    callbacks: SlotEditCallbacks,
) -> None:
    qt = load()
    with suppress(Exception):
        if callbacks.unlocked:
            button.setToolTip("Rail unlocked: right-click to edit this slot.")
    if not hasattr(button, "setContextMenuPolicy") or not hasattr(
        button, "customContextMenuRequested"
    ):
        return
    try:
        button.setContextMenuPolicy(qt.QtCore.Qt.CustomContextMenu)
        button.customContextMenuRequested.connect(
            lambda point, slot_id=item.id: _show_slot_edit_menu(
                button,
                point,
                slot_id,
                bool(item.action or item.icon or item.label.strip()),
                registry,
                callbacks,
            )
        )
    except Exception:
        return


def _show_slot_edit_menu(
    button: object,
    point: object,
    slot_id: str,
    has_payload: bool,
    registry: ActionRegistry,
    callbacks: SlotEditCallbacks,
) -> None:
    qt = load()
    menu_class = getattr(qt.QtWidgets, "QMenu", None)
    if menu_class is None:
        return
    menu = menu_class(button)
    if callbacks.unlocked:
        assign_menu = menu.addMenu("Assign Action")
        for action in sorted(registry.actions(), key=lambda item: item.label):
            action_item = assign_menu.addAction(action.label)
            action_item.setToolTip(action.tooltip or action.id)
            action_item.triggered.connect(
                lambda _checked=False, target=slot_id, action_id=action.id: (
                    callbacks.assign_action(
                        target,
                        action_id,
                    )
                )
            )
        clear_action = menu.addAction("Clear Slot")
        clear_action.setEnabled(has_payload)
        clear_action.triggered.connect(lambda _checked=False: callbacks.clear_slot(slot_id))
        menu.addSeparator()
        lock_action = menu.addAction("Lock Rail")
        lock_action.triggered.connect(lambda _checked=False: callbacks.lock_rail())
    else:
        unlock_action = menu.addAction("Unlock Rail")
        unlock_action.triggered.connect(lambda _checked=False: callbacks.unlock_rail())
    with suppress(Exception):
        menu.exec(button.mapToGlobal(point))


def _install_bind_mode_capture(
    qt: object,
    button: object,
    item: StackItem,
    preset_id: str,
) -> bool:
    """Install the hover/key capture used by ActionRail Bind Mode."""

    if not item.action:
        return False
    object_class = getattr(getattr(qt, "QtCore", None), "QObject", None)
    event_class = getattr(getattr(qt, "QtCore", None), "QEvent", None)
    install_event_filter = getattr(button, "installEventFilter", None)
    if object_class is None or event_class is None or not callable(install_event_filter):
        return False

    enter_type = getattr(event_class, "Enter", None)
    leave_type = getattr(event_class, "Leave", None)
    key_release_type = getattr(event_class, "KeyRelease", None)
    mouse_press_type = getattr(event_class, "MouseButtonPress", None)
    mouse_release_type = getattr(event_class, "MouseButtonRelease", None)
    if enter_type is None or leave_type is None or key_release_type is None:
        return False

    slot_id = _slot_suffix(preset_id, item.id)

    class _BindModeFilter(object_class):  # type: ignore[misc, valid-type]
        def eventFilter(self, watched: object, event: object) -> bool:  # noqa: N802
            from . import bind_mode

            if not bind_mode.bind_mode_state().enabled:
                return False

            event_type = event.type()
            if event_type == enter_type:
                bind_mode.select_bind_mode_slot(preset_id, slot_id)
                _grab_bind_mode_keyboard(watched)
                return False

            if event_type == leave_type:
                _release_bind_mode_keyboard(watched)
                return False

            if event_type in (mouse_press_type, mouse_release_type):
                bind_mode.select_bind_mode_slot(preset_id, slot_id)
                _accept_event(event)
                return True

            if event_type != key_release_type:
                return False

            bind_mode.select_bind_mode_slot(preset_id, slot_id)
            chord = _bind_mode_chord_from_key_event(qt, event)
            if chord is None:
                return False
            if _hotkey_chord_is_escape(chord):
                bind_mode.clear_hovered_hotkey()
                _accept_event(event)
                return True
            try:
                bind_mode.assign_hovered_hotkey(
                    chord.key,
                    ctrl=chord.ctrl,
                    alt=chord.alt,
                    shift=chord.shift,
                    command=chord.command,
                    release=chord.release,
                )
                _clear_bind_mode_conflict(watched)
            except HotkeyConflictError as exc:
                _record_bind_mode_conflict(watched, str(exc))
            _accept_event(event)
            return True

    bind_filter = _BindModeFilter()
    try:
        install_event_filter(bind_filter)
    except Exception:
        return False
    button._actionrail_bind_mode_filter = bind_filter
    return True


def _bind_mode_chord_from_key_event(qt: object, event: object) -> HotkeyChord | None:
    key_value = _event_key_value(event)
    if key_value is None or _is_modifier_key(qt, key_value):
        return None
    key = _qt_key_text(qt, key_value)
    if not key:
        return None
    modifiers = _event_modifier_value(event)
    qt_constants = getattr(getattr(qt, "QtCore", None), "Qt", object())
    return HotkeyChord(
        key,
        ctrl=bool(modifiers & getattr(qt_constants, "ControlModifier", 0)),
        alt=bool(modifiers & getattr(qt_constants, "AltModifier", 0)),
        shift=bool(modifiers & getattr(qt_constants, "ShiftModifier", 0)),
        command=bool(modifiers & getattr(qt_constants, "MetaModifier", 0)),
    )


def _event_key_value(event: object) -> int | None:
    key = getattr(event, "key", None)
    if not callable(key):
        return None
    with suppress(Exception):
        return int(key())
    return None


def _event_modifier_value(event: object) -> int:
    modifiers = getattr(event, "modifiers", None)
    if not callable(modifiers):
        return 0
    with suppress(Exception):
        return int(modifiers())
    return 0


def _qt_key_text(qt: object, key_value: int) -> str:
    key_sequence = getattr(getattr(qt, "QtGui", None), "QKeySequence", None)
    if key_sequence is not None:
        with suppress(Exception):
            text = key_sequence(key_value).toString()
            if isinstance(text, str) and text:
                return text.split("+")[-1]
    return chr(key_value).upper() if 32 < key_value < 127 else ""


def _is_modifier_key(qt: object, key_value: int) -> bool:
    qt_constants = getattr(getattr(qt, "QtCore", None), "Qt", object())
    modifier_keys = (
        getattr(qt_constants, "Key_Shift", None),
        getattr(qt_constants, "Key_Control", None),
        getattr(qt_constants, "Key_Alt", None),
        getattr(qt_constants, "Key_Meta", None),
        getattr(qt_constants, "Key_unknown", None),
    )
    return any(value is not None and key_value == int(value) for value in modifier_keys)


def _hotkey_chord_is_escape(chord: HotkeyChord) -> bool:
    return chord.key.lower() in {"esc", "escape"}


def _slot_suffix(preset_id: str, slot_id: str) -> str:
    prefix = f"{preset_id}."
    if slot_id.startswith(prefix):
        return slot_id.removeprefix(prefix)
    return slot_id


def _grab_bind_mode_keyboard(widget: object) -> None:
    grab_keyboard = getattr(widget, "grabKeyboard", None)
    if callable(grab_keyboard):
        with suppress(Exception):
            grab_keyboard()


def _release_bind_mode_keyboard(widget: object) -> None:
    release_keyboard = getattr(widget, "releaseKeyboard", None)
    if callable(release_keyboard):
        with suppress(Exception):
            release_keyboard()


def _record_bind_mode_conflict(widget: object, message: str) -> None:
    with suppress(Exception):
        widget.setProperty("actionRailBindConflict", message)
    if hasattr(widget, "setToolTip"):
        with suppress(Exception):
            widget.setToolTip(message)


def _clear_bind_mode_conflict(widget: object) -> None:
    with suppress(Exception):
        widget.setProperty("actionRailBindConflict", "")


def _install_action_book_drop(
    button: object,
    item: StackItem,
    callbacks: SlotEditCallbacks,
) -> None:
    set_accept_drops = getattr(button, "setAcceptDrops", None)
    if not callable(set_accept_drops):
        return
    with suppress(Exception):
        set_accept_drops(True)

    if callable(getattr(button, "installEventFilter", None)):
        _install_action_book_drop_event_filter(load(), button, item, callbacks)

    base_drag_enter = getattr(button, "dragEnterEvent", None)
    base_drop = getattr(button, "dropEvent", None)

    def drag_enter_event(event: object) -> object | None:
        if _action_book_drop_can_accept(button, callbacks, event):
            _accept_proposed_event(event)
            return None
        if callable(base_drag_enter):
            return base_drag_enter(event)
        return None

    def drop_event(event: object) -> object | None:
        if not _assign_action_book_drop(button, item.id, callbacks, event):
            if callable(base_drop):
                return base_drop(event)
            return None
        _accept_proposed_event(event)
        return None

    button.dragEnterEvent = drag_enter_event  # type: ignore[method-assign]
    button.dropEvent = drop_event  # type: ignore[method-assign]


def _install_action_book_drop_event_filter(
    qt: object,
    button: object,
    item: StackItem,
    callbacks: SlotEditCallbacks,
) -> bool:
    object_class = getattr(getattr(qt, "QtCore", None), "QObject", None)
    event_class = getattr(getattr(qt, "QtCore", None), "QEvent", None)
    install_event_filter = getattr(button, "installEventFilter", None)
    if object_class is None or event_class is None or not callable(install_event_filter):
        return False

    drag_enter_type = getattr(event_class, "DragEnter", None)
    drag_move_type = getattr(event_class, "DragMove", None)
    drop_type = getattr(event_class, "Drop", None)
    if drag_enter_type is None or drag_move_type is None or drop_type is None:
        return False

    class _ActionBookDropFilter(object_class):  # type: ignore[misc, valid-type]
        def eventFilter(self, watched: object, event: object) -> bool:  # noqa: N802
            event_type = event.type()
            if event_type in (drag_enter_type, drag_move_type):
                if _action_book_drop_can_accept(watched, callbacks, event):
                    _accept_proposed_event(event)
                    return True
                return False

            if event_type != drop_type:
                return False

            if _assign_action_book_drop(watched, item.id, callbacks, event):
                _accept_proposed_event(event)
                return True
            return False

    try:
        event_filter = _ActionBookDropFilter(button)
        install_event_filter(event_filter)
        button._actionrail_action_book_drop_event_filter = event_filter
    except Exception:
        return False
    return True


def _install_action_book_root_drop(
    qt: object,
    root: object,
    callbacks: SlotEditCallbacks,
) -> bool:
    set_accept_drops = getattr(root, "setAcceptDrops", None)
    install_event_filter = getattr(root, "installEventFilter", None)
    object_class = getattr(getattr(qt, "QtCore", None), "QObject", None)
    event_class = getattr(getattr(qt, "QtCore", None), "QEvent", None)
    if (
        not callable(set_accept_drops)
        or not callable(install_event_filter)
        or object_class is None
        or event_class is None
    ):
        return False

    drag_enter_type = getattr(event_class, "DragEnter", None)
    drag_move_type = getattr(event_class, "DragMove", None)
    drop_type = getattr(event_class, "Drop", None)
    if drag_enter_type is None or drag_move_type is None or drop_type is None:
        return False

    with suppress(Exception):
        set_accept_drops(True)

    class _ActionBookRootDropFilter(object_class):  # type: ignore[misc, valid-type]
        def eventFilter(self, watched: object, event: object) -> bool:  # noqa: N802
            event_type = event.type()
            if event_type not in (drag_enter_type, drag_move_type, drop_type):
                return False

            target_button = _action_book_drop_button_from_root_event(qt, watched, event)
            if target_button is None:
                return False

            target_callbacks = _slot_edit_callbacks_from_button(target_button) or callbacks
            if event_type in (drag_enter_type, drag_move_type):
                if _action_book_drop_can_accept(target_button, target_callbacks, event):
                    _accept_proposed_event(event)
                    return True
                return False

            slot_id = _slot_id_from_button(target_button)
            if slot_id and _assign_action_book_drop(
                target_button,
                slot_id,
                target_callbacks,
                event,
            ):
                _accept_proposed_event(event)
                return True
            return False

    try:
        event_filter = _ActionBookRootDropFilter(root)
        install_event_filter(event_filter)
        root._actionrail_action_book_drop_event_filter = event_filter
    except Exception:
        return False
    return True


def _action_book_drop_button_from_root_event(
    qt: object,
    root: object,
    event: object,
) -> object | None:
    local_point = _event_local_point(event)
    map_to_global = getattr(root, "mapToGlobal", None)
    if local_point is None or not callable(map_to_global):
        return None
    with suppress(Exception):
        return _slot_button_at_global_point(qt, root, map_to_global(local_point))
    return None


def _slot_id_from_button(button: object) -> str:
    with suppress(Exception):
        slot_id = button.property("actionRailSlotId")
        if isinstance(slot_id, str):
            return slot_id
    return ""


def _action_book_drop_can_accept(
    button: object,
    callbacks: SlotEditCallbacks,
    event: object,
) -> bool:
    live_callbacks = _slot_edit_callbacks_from_button(button) or callbacks
    return bool(
        getattr(live_callbacks, "unlocked", False)
        and _action_book_action_id_from_event(event)
    )


def _assign_action_book_drop(
    button: object,
    slot_id: str,
    callbacks: SlotEditCallbacks,
    event: object,
) -> bool:
    live_callbacks = _slot_edit_callbacks_from_button(button) or callbacks
    action_id = _action_book_action_id_from_event(event)
    if not getattr(live_callbacks, "unlocked", False) or not action_id:
        return False
    return bool(live_callbacks.assign_action(slot_id, action_id))


def _action_book_action_id_from_event(event: object) -> str:
    mime_data = _mime_data_from_event(event)
    if mime_data is None:
        return ""
    raw_text = _mime_payload_text(mime_data)
    if not raw_text:
        return ""
    with suppress(Exception):
        return action_book_action_id_from_mime_text(raw_text)
    return ""


def _mime_data_from_event(event: object) -> object | None:
    mime_data = getattr(event, "mimeData", None)
    if callable(mime_data):
        with suppress(Exception):
            return mime_data()
    return None


def _mime_payload_text(mime_data: object) -> str:
    has_format = getattr(mime_data, "hasFormat", None)
    data = getattr(mime_data, "data", None)
    if callable(has_format) and callable(data):
        with suppress(Exception):
            if has_format(ACTION_BOOK_MIME_TYPE):
                return _decode_mime_bytes(data(ACTION_BOOK_MIME_TYPE))
    has_text = getattr(mime_data, "hasText", None)
    text = getattr(mime_data, "text", None)
    if callable(has_text) and callable(text):
        with suppress(Exception):
            if has_text():
                return str(text())
    return ""


def _decode_mime_bytes(value: object) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8")
    try:
        return bytes(value).decode("utf-8")
    except Exception:
        return str(value)


def _accept_proposed_event(event: object) -> None:
    accept_proposed = getattr(event, "acceptProposedAction", None)
    if callable(accept_proposed):
        with suppress(Exception):
            accept_proposed()
            return
    _accept_event(event)


def _install_slot_drag_edit(
    button: object,
    item: StackItem,
    callbacks: SlotEditCallbacks,
) -> None:
    if not callbacks.unlocked or not item_has_payload(item):
        return
    if (
        callbacks.move_slot is None
        or not hasattr(button, "mousePressEvent")
        or not hasattr(button, "mouseMoveEvent")
        or not hasattr(button, "mouseReleaseEvent")
    ):
        return

    qt = load()
    if _install_slot_drag_event_filter(qt, button, item.id, callbacks):
        return

    button._actionrail_slot_drag_item_id = item.id
    button._actionrail_slot_drag_callbacks = callbacks
    button._actionrail_slot_drag_qt = qt
    if getattr(button, "_actionrail_supports_slot_drag_events", False):
        return

    base_press = button.mousePressEvent
    base_move = button.mouseMoveEvent
    base_release = button.mouseReleaseEvent

    def mouse_press(event):  # type: ignore[no-untyped-def]
        if not _handle_slot_drag_press(button, event):
            return base_press(event)
        return None

    def mouse_move(event):  # type: ignore[no-untyped-def]
        if not _handle_slot_drag_move(button, event):
            return base_move(event)
        return None

    def mouse_release(event):  # type: ignore[no-untyped-def]
        if not _handle_slot_drag_release(button, event):
            return base_release(event)
        return None

    button.mousePressEvent = mouse_press  # type: ignore[method-assign]
    button.mouseMoveEvent = mouse_move  # type: ignore[method-assign]
    button.mouseReleaseEvent = mouse_release  # type: ignore[method-assign]


def _install_slot_drag_event_filter(
    qt: object,
    button: object,
    source_slot_id: str,
    callbacks: SlotEditCallbacks,
) -> bool:
    object_class = getattr(getattr(qt, "QtCore", None), "QObject", None)
    event_class = getattr(getattr(qt, "QtCore", None), "QEvent", None)
    install_event_filter = getattr(button, "installEventFilter", None)
    if object_class is None or event_class is None or not callable(install_event_filter):
        return False

    class _SlotDragFilter(object_class):  # type: ignore[misc, valid-type]
        def __init__(self) -> None:
            super().__init__(button)
            self._state: dict[str, object] | None = None

        def eventFilter(self, watched: object, event: object) -> bool:  # noqa: N802
            event_type = event.type()
            if event_type == event_class.MouseButtonPress:
                if not _slot_drag_press_matches(qt, event):
                    return False
                self._state = {
                    "slot_id": source_slot_id,
                    "start": _event_global_point(event),
                    "dragging": False,
                    "source_button": watched,
                }
                _grab_slot_drag_mouse(watched)
                _accept_event(event)
                return True

            if event_type == event_class.MouseMove and self._state is not None:
                move_points = _slot_drag_event_points(qt, watched, event)
                _record_slot_drag_points(self._state, move_points)
                move_point = move_points[0] if move_points else None
                if not self._state.get("dragging") and _drag_threshold_exceeded(
                    qt,
                    self._state.get("start"),
                    move_point,
                ):
                    self._state["dragging"] = True
                if self._state.get("dragging"):
                    _ensure_slot_drag_preview(
                        qt,
                        self._state,
                        watched,
                        move_point,
                    )
                _accept_event(event)
                return True

            if event_type != event_class.MouseButtonRelease or self._state is None:
                return False

            state = self._state
            self._state = None
            _release_slot_drag_mouse(state)
            release_points = _combined_slot_drag_points(
                state,
                _slot_drag_event_points(qt, watched, event),
            )
            release_point = release_points[0] if release_points else None
            if not state.get("dragging") and _drag_threshold_exceeded(
                qt,
                state.get("start"),
                release_point,
            ):
                state["dragging"] = True
                _ensure_slot_drag_preview(qt, state, watched, release_point)
            if not state.get("dragging"):
                return False

            target = _slot_drag_release_target_info_from_points(
                qt,
                watched,
                release_points,
            )
            changed = _commit_slot_drag_drop(
                callbacks,
                source_slot_id,
                target,
            )
            _finish_slot_drag(state, restore_source=not changed)
            _accept_event(event)
            return True

    try:
        event_filter = _SlotDragFilter()
        install_event_filter(event_filter)
        button._actionrail_slot_drag_event_filter = event_filter
    except Exception:
        return False
    return True


def _handle_slot_drag_press(button: object, event: object) -> bool:
    callbacks = getattr(button, "_actionrail_slot_drag_callbacks", None)
    qt = getattr(button, "_actionrail_slot_drag_qt", None) or load()
    source_slot_id = getattr(button, "_actionrail_slot_drag_item_id", None)
    if (
        callbacks is None
        or not getattr(callbacks, "unlocked", False)
        or not isinstance(source_slot_id, str)
        or not _slot_drag_press_matches(qt, event)
    ):
        return False
    button._actionrail_slot_drag = {
        "slot_id": source_slot_id,
        "start": _event_global_point(event),
        "dragging": False,
        "source_button": button,
    }
    _grab_slot_drag_mouse(button)
    _accept_event(event)
    return True


def _handle_slot_drag_move(button: object, event: object) -> bool:
    state = getattr(button, "_actionrail_slot_drag", None)
    if not isinstance(state, dict):
        return False
    qt = getattr(button, "_actionrail_slot_drag_qt", None) or load()
    move_points = _slot_drag_event_points(qt, button, event)
    _record_slot_drag_points(state, move_points)
    move_point = move_points[0] if move_points else None
    if not state.get("dragging") and _drag_threshold_exceeded(
        qt,
        state.get("start"),
        move_point,
    ):
        state["dragging"] = True
    if state.get("dragging"):
        _ensure_slot_drag_preview(qt, state, button, move_point)
    _accept_event(event)
    return True


def _handle_slot_drag_release(button: object, event: object) -> bool:
    state = getattr(button, "_actionrail_slot_drag", None)
    if not isinstance(state, dict):
        return False
    with suppress(Exception):
        delattr(button, "_actionrail_slot_drag")
    _release_slot_drag_mouse(state)
    qt = getattr(button, "_actionrail_slot_drag_qt", None) or load()
    release_points = _combined_slot_drag_points(
        state,
        _slot_drag_event_points(qt, button, event),
    )
    release_point = release_points[0] if release_points else None
    if not state.get("dragging") and _drag_threshold_exceeded(
        qt,
        state.get("start"),
        release_point,
    ):
        state["dragging"] = True
        _ensure_slot_drag_preview(qt, state, button, release_point)
    if not state.get("dragging"):
        return False

    callbacks = getattr(button, "_actionrail_slot_drag_callbacks", None)
    target = _slot_drag_release_target_info_from_points(
        qt,
        button,
        release_points,
    )
    source_slot_id = state.get("slot_id")
    changed = False
    if callbacks is not None and isinstance(source_slot_id, str):
        changed = _commit_slot_drag_drop(
            callbacks,
            source_slot_id,
            target,
        )
    _finish_slot_drag(state, restore_source=not changed)
    _accept_event(event)
    return True


def _commit_slot_drag_drop(
    callbacks: SlotEditCallbacks,
    source_slot_id: str,
    target: _SlotDragDropTarget,
) -> bool:
    target_slot_id = target.slot_id
    if target_slot_id and target_slot_id != source_slot_id:
        if target.same_rail:
            return bool(callbacks.move_slot(source_slot_id, target_slot_id))
        if (
            target.callbacks is not None
            and target.callbacks.unlocked
            and callbacks.transfer_slot is not None
        ):
            return bool(
                callbacks.transfer_slot(
                    source_slot_id,
                    target.callbacks,
                    target_slot_id,
                )
            )
        return False
    if target.inside_action_rail and not target.same_rail:
        return False
    return bool(callbacks.clear_slot(source_slot_id))


def _ensure_slot_drag_preview(
    qt: object,
    state: dict[str, object],
    source_button: object,
    global_point: object | None,
) -> None:
    preview = state.get("preview")
    if preview is None:
        preview = _create_slot_drag_preview(qt, source_button, global_point)
        if preview is not None:
            state["preview"] = preview
            _empty_slot_drag_source(qt, state, source_button)
    if preview is not None:
        _move_slot_drag_preview(preview, global_point)


def _create_slot_drag_preview(
    qt: object,
    source_button: object,
    global_point: object | None,
) -> object | None:
    label_class = getattr(getattr(qt, "QtWidgets", None), "QLabel", None)
    if label_class is None:
        return None
    try:
        preview = label_class()
    except Exception:
        return None

    pixmap = _slot_drag_preview_pixmap(source_button)
    if pixmap is not None:
        with suppress(Exception):
            preview.setPixmap(pixmap)
    else:
        with suppress(Exception):
            preview.setText(_slot_drag_preview_text(source_button))

    with suppress(Exception):
        preview.setObjectName("ActionRailSlotDragPreview")
    with suppress(Exception):
        preview.setWindowFlags(_slot_drag_preview_flags(qt))
    transparent_for_mouse = _qt_enum_value(
        qt,
        "WA_TransparentForMouseEvents",
        group="WidgetAttribute",
    )
    show_without_activating = _qt_enum_value(
        qt,
        "WA_ShowWithoutActivating",
        group="WidgetAttribute",
    )
    if transparent_for_mouse is not None:
        with suppress(Exception):
            preview.setAttribute(transparent_for_mouse, True)
    if show_without_activating is not None:
        with suppress(Exception):
            preview.setAttribute(show_without_activating, True)
    with suppress(Exception):
        preview.setWindowOpacity(0.92)
    _copy_slot_drag_preview_size(preview, source_button, pixmap)
    _move_slot_drag_preview(preview, global_point)
    with suppress(Exception):
        preview.show()
    with suppress(Exception):
        preview.raise_()
    return preview


def _slot_drag_preview_flags(qt: object) -> object:
    qt_namespace = getattr(getattr(qt, "QtCore", None), "Qt", None)
    flags = 0
    for name in ("Tool", "FramelessWindowHint", "WindowStaysOnTopHint", "WindowDoesNotAcceptFocus"):
        value = getattr(qt_namespace, name, None) if qt_namespace is not None else None
        if value is not None:
            flags |= value
    return flags


def _slot_drag_preview_pixmap(source_button: object) -> object | None:
    grab = getattr(source_button, "grab", None)
    if not callable(grab):
        return None
    with suppress(Exception):
        pixmap = grab()
        is_null = getattr(pixmap, "isNull", None)
        if callable(is_null) and is_null():
            return None
        return pixmap
    return None


def _copy_slot_drag_preview_size(
    preview: object,
    source_button: object,
    pixmap: object | None,
) -> None:
    width = _pixmap_size_value(pixmap, "width") or _widget_size_value(source_button, "width")
    height = _pixmap_size_value(pixmap, "height") or _widget_size_value(source_button, "height")
    if width <= 0 or height <= 0:
        return
    with suppress(Exception):
        preview.setFixedSize(width, height)


def _pixmap_size_value(pixmap: object | None, method_name: str) -> int:
    if pixmap is None:
        return 0
    method = getattr(pixmap, method_name, None)
    if callable(method):
        with suppress(Exception):
            return int(method())
    return 0


def _widget_size_value(widget: object, method_name: str) -> int:
    method = getattr(widget, method_name, None)
    if callable(method):
        with suppress(Exception):
            return int(method())
    return 0


def _move_slot_drag_preview(preview: object, global_point: object | None) -> None:
    if global_point is None:
        return
    with suppress(Exception):
        preview.move(_point_x(global_point) + 12, _point_y(global_point) + 12)


def _finish_slot_drag(state: dict[str, object], *, restore_source: bool) -> None:
    _clear_slot_drag_preview(state)
    if restore_source:
        _restore_slot_drag_source(state)


def _clear_slot_drag_preview(state: dict[str, object]) -> None:
    preview = state.pop("preview", None)
    if preview is None:
        return
    with suppress(Exception):
        preview.hide()
    with suppress(Exception):
        preview.deleteLater()


def _grab_slot_drag_mouse(source_button: object) -> None:
    grab_mouse = getattr(source_button, "grabMouse", None)
    if callable(grab_mouse):
        with suppress(Exception):
            grab_mouse()


def _release_slot_drag_mouse(state: dict[str, object]) -> None:
    source_button = state.get("source_button")
    release_mouse = getattr(source_button, "releaseMouse", None)
    if callable(release_mouse):
        with suppress(Exception):
            release_mouse()


def _empty_slot_drag_source(qt: object, state: dict[str, object], source_button: object) -> None:
    if state.get("source_emptied"):
        return
    state["source_button"] = source_button
    state["source_visual"] = _snapshot_slot_drag_source(source_button)
    state["source_emptied"] = True

    key_label = ""
    visual = state.get("source_visual")
    if isinstance(visual, dict):
        key_label_value = visual.get("actionRailKeyLabel")
        if isinstance(key_label_value, str):
            key_label = key_label_value

    for name, value in (
        ("actionRailLabel", ""),
        ("actionRailKeyLabel", key_label),
        ("actionRailIcon", ""),
        ("actionRailIconPath", ""),
        ("actionRailIconName", ""),
        ("actionRailAppliedIconSource", ""),
        ("actionRailTone", "neutral"),
        ("actionRailActive", "false"),
        ("actionRailLocked", "true"),
        ("actionRailDiagnosticCode", ""),
        ("actionRailDiagnosticSeverity", ""),
        ("actionRailDiagnosticBadge", ""),
        ("actionRailSlotDragSource", "true"),
    ):
        with suppress(Exception):
            source_button.setProperty(name, value)
    with suppress(Exception):
        source_button.setText(_button_text("", key_label))
    with suppress(Exception):
        source_button.setIcon(qt.QtGui.QIcon())
    _refresh_button_style(source_button)
    with suppress(Exception):
        source_button.update()


def _snapshot_slot_drag_source(source_button: object) -> dict[str, object]:
    snapshot: dict[str, object] = {}
    for name in (
        "actionRailLabel",
        "actionRailKeyLabel",
        "actionRailIcon",
        "actionRailIconPath",
        "actionRailIconName",
        "actionRailAppliedIconSource",
        "actionRailTone",
        "actionRailActive",
        "actionRailLocked",
        "actionRailDiagnosticCode",
        "actionRailDiagnosticSeverity",
        "actionRailDiagnosticBadge",
        "actionRailSlotDragSource",
    ):
        with suppress(Exception):
            snapshot[name] = source_button.property(name)
    text = getattr(source_button, "text", None)
    if callable(text):
        with suppress(Exception):
            snapshot["text"] = text()
    with suppress(Exception):
        snapshot["visible"] = source_button.isVisible()
    with suppress(Exception):
        snapshot["graphics_effect"] = source_button.graphicsEffect()
    return snapshot


def _restore_slot_drag_source(state: dict[str, object]) -> None:
    source_button = state.pop("source_button", None)
    visual = state.pop("source_visual", None)
    state.pop("source_emptied", None)
    if source_button is None or not isinstance(visual, dict):
        return
    with suppress(Exception):
        source_button.setGraphicsEffect(visual.get("graphics_effect"))
    if "visible" in visual:
        with suppress(Exception):
            source_button.setVisible(bool(visual["visible"]))
    for name, value in visual.items():
        if name in {"text", "visible", "graphics_effect"}:
            continue
        with suppress(Exception):
            source_button.setProperty(name, value)
    if "text" in visual:
        with suppress(Exception):
            source_button.setText(str(visual["text"]))
    with suppress(Exception):
        _apply_button_icon(
            source_button,
            str(visual.get("actionRailIconPath", "") or ""),
            str(visual.get("actionRailIconName", "") or ""),
        )
    with suppress(Exception):
        source_button.update()


def _slot_drag_preview_text(source_button: object) -> str:
    try:
        label = source_button.property("actionRailLabel")
    except Exception:
        label = None
    if isinstance(label, str) and label.strip():
        return label.strip().split("\n", 1)[0]
    text = getattr(source_button, "text", None)
    if callable(text):
        with suppress(Exception):
            return str(text()).split("\n", 1)[0]
    return "Slot"


def _slot_drag_press_matches(qt: object, event: object) -> bool:
    return _event_has_button(qt, event, "LeftButton") and _event_has_modifier(
        qt,
        event,
        "ShiftModifier",
    )


def _event_has_button(qt: object, event: object, name: str) -> bool:
    button = getattr(event, "button", None)
    if not callable(button):
        return False
    expected = _qt_enum_value(qt, name, group="MouseButton")
    if expected is None:
        return False
    with suppress(Exception):
        return button() == expected
    return False


def _event_has_modifier(qt: object, event: object, name: str) -> bool:
    modifiers = getattr(event, "modifiers", None)
    if not callable(modifiers):
        return False
    expected = _qt_enum_value(qt, name, group="KeyboardModifier")
    if expected is None:
        return False
    with suppress(Exception):
        return bool(modifiers() & expected)
    return False


def _qt_enum_value(qt: object, name: str, *, group: str) -> object | None:
    qt_namespace = getattr(getattr(qt, "QtCore", None), "Qt", None)
    if qt_namespace is None:
        return None
    direct = getattr(qt_namespace, name, None)
    if direct is not None:
        return direct
    enum_group = getattr(qt_namespace, group, None)
    if enum_group is not None:
        return getattr(enum_group, name, None)
    return None


def _event_global_point(event: object) -> object | None:
    global_position = getattr(event, "globalPosition", None)
    if callable(global_position):
        with suppress(Exception):
            point = global_position()
            to_point = getattr(point, "toPoint", None)
            return to_point() if callable(to_point) else point
    global_pos = getattr(event, "globalPos", None)
    if callable(global_pos):
        with suppress(Exception):
            return global_pos()
    return None


def _drag_global_point(qt: object, event: object) -> object | None:
    points = _drag_global_points(qt, event)
    return points[0] if points else None


def _slot_drag_event_points(
    qt: object,
    source_button: object,
    event: object,
) -> tuple[object, ...]:
    points = list(_drag_global_points(qt, event))
    local_point = _event_local_point(event)
    map_to_global = getattr(source_button, "mapToGlobal", None)
    if local_point is not None and callable(map_to_global):
        with suppress(Exception):
            _append_unique_global_point(points, map_to_global(local_point))
    return tuple(points)


def _drag_global_points(qt: object, event: object) -> tuple[object, ...]:
    points: list[object] = []
    cursor_class = getattr(getattr(qt, "QtGui", None), "QCursor", None)
    cursor_pos = getattr(cursor_class, "pos", None)
    if callable(cursor_pos):
        with suppress(Exception):
            _append_unique_global_point(points, cursor_pos())
    event_point = _event_global_point(event)
    if event_point is not None:
        _append_unique_global_point(points, event_point)
    return tuple(points)


def _event_local_point(event: object) -> object | None:
    position = getattr(event, "position", None)
    if callable(position):
        with suppress(Exception):
            point = position()
            to_point = getattr(point, "toPoint", None)
            return to_point() if callable(to_point) else point
    pos = getattr(event, "pos", None)
    if callable(pos):
        with suppress(Exception):
            return pos()
    return None


def _append_unique_global_point(points: list[object], point: object | None) -> None:
    if point is None:
        return
    for existing in points:
        if _point_x(existing) == _point_x(point) and _point_y(existing) == _point_y(point):
            return
    points.append(point)


def _record_slot_drag_points(
    state: dict[str, object],
    points: tuple[object, ...],
) -> None:
    if points:
        state["last_global_points"] = points


def _combined_slot_drag_points(
    state: dict[str, object],
    release_points: tuple[object, ...],
) -> tuple[object, ...]:
    points: list[object] = []
    for point in release_points:
        _append_unique_global_point(points, point)
    last_points = state.get("last_global_points")
    if isinstance(last_points, tuple):
        for point in last_points:
            _append_unique_global_point(points, point)
    return tuple(points)


def _drag_threshold_exceeded(qt: object, start: object, current: object) -> bool:
    if start is None or current is None:
        return True
    distance = _point_distance(start, current)
    return distance >= _start_drag_distance(qt)


def _point_distance(start: object, current: object) -> int:
    with suppress(Exception):
        delta = current - start
        manhattan = getattr(delta, "manhattanLength", None)
        if callable(manhattan):
            return int(manhattan())
    return abs(_point_x(current) - _point_x(start)) + abs(_point_y(current) - _point_y(start))


def _point_x(point: object) -> int:
    value = getattr(point, "x", None)
    if callable(value):
        with suppress(Exception):
            return int(value())
    return int(getattr(point, "x_pos", 0))


def _point_y(point: object) -> int:
    value = getattr(point, "y", None)
    if callable(value):
        with suppress(Exception):
            return int(value())
    return int(getattr(point, "y_pos", 0))


def _start_drag_distance(qt: object) -> int:
    app_class = getattr(getattr(qt, "QtWidgets", None), "QApplication", None)
    if app_class is not None:
        start_drag_distance = getattr(app_class, "startDragDistance", None)
        if callable(start_drag_distance):
            with suppress(Exception):
                return max(1, int(start_drag_distance()))
    return 4


def _slot_drag_release_target(
    qt: object,
    source_button: object,
    global_point: object | None,
) -> tuple[str | None, bool]:
    target = _slot_drag_release_target_info_from_points(qt, source_button, (global_point,))
    return target.slot_id, target.inside_action_rail


def _slot_drag_release_target_from_points(
    qt: object,
    source_button: object,
    global_points: tuple[object | None, ...],
) -> tuple[str | None, bool]:
    target = _slot_drag_release_target_info_from_points(qt, source_button, global_points)
    return target.slot_id, target.inside_action_rail


def _slot_drag_release_target_info_from_points(
    qt: object,
    source_button: object,
    global_points: tuple[object | None, ...],
) -> _SlotDragDropTarget:
    points = tuple(point for point in global_points if point is not None)
    if not points:
        return _SlotDragDropTarget()
    source_root = _rail_root_widget(source_button)
    source_slot_id = _slot_id_from_button(source_button)
    over_source_slot = False
    if source_root is not None:
        for point in points:
            if _global_point_inside_widget(source_root, point):
                target_slot_id = _slot_id_at_global_point(qt, source_root, point)
                if target_slot_id is not None:
                    if target_slot_id != source_slot_id:
                        return _SlotDragDropTarget(
                            slot_id=target_slot_id,
                            callbacks=_slot_edit_callbacks_from_button(
                                _slot_button_at_global_point(qt, source_root, point)
                            ),
                            inside_action_rail=True,
                            same_rail=True,
                        )
                    over_source_slot = True
        if _widget_has_global_geometry(source_root):
            if any(not _global_point_inside_widget(source_root, point) for point in points):
                cross_target = _slot_drag_cross_rail_target(qt, source_root, points)
                if cross_target.inside_action_rail:
                    return cross_target
                return _SlotDragDropTarget()
            return _SlotDragDropTarget(
                slot_id=source_slot_id if over_source_slot else None,
                callbacks=_slot_edit_callbacks_from_button(source_button),
                inside_action_rail=True,
                same_rail=True,
            )

    hit_widget = _first_widget_at_global_points(qt, points)
    if hit_widget is None:
        return _SlotDragDropTarget(
            inside_action_rail=source_root is not None
            and _widget_has_global_geometry(source_root),
            same_rail=source_root is not None,
        )

    target_button = _slot_button_ancestor(qt, hit_widget)
    target_root = _rail_root_widget(target_button) if target_button is not None else None
    if target_button is not None and target_root is source_root:
        slot_id = target_button.property("actionRailSlotId")
        return _SlotDragDropTarget(
            slot_id=slot_id if isinstance(slot_id, str) else None,
            callbacks=_slot_edit_callbacks_from_button(target_button),
            inside_action_rail=True,
            same_rail=True,
        )
    if target_button is not None and target_root is not None:
        slot_id = target_button.property("actionRailSlotId")
        return _SlotDragDropTarget(
            slot_id=slot_id if isinstance(slot_id, str) else None,
            callbacks=_slot_edit_callbacks_from_button(target_button),
            inside_action_rail=True,
            same_rail=False,
        )

    hit_root = _rail_root_widget(hit_widget)
    if hit_root is not None:
        return _SlotDragDropTarget(
            inside_action_rail=True,
            same_rail=hit_root is source_root,
        )

    return _SlotDragDropTarget()


def _slot_drag_cross_rail_target(
    qt: object,
    source_root: object,
    points: tuple[object, ...],
) -> _SlotDragDropTarget:
    for point in points:
        hit_widget = _widget_at_global_point(qt, point)
        target_button = _slot_button_ancestor(qt, hit_widget)
        target_root = _rail_root_widget(target_button) if target_button is not None else None
        if target_button is not None and target_root is not None and target_root is not source_root:
            slot_id = target_button.property("actionRailSlotId")
            return _SlotDragDropTarget(
                slot_id=slot_id if isinstance(slot_id, str) else None,
                callbacks=_slot_edit_callbacks_from_button(target_button),
                inside_action_rail=True,
                same_rail=False,
            )
        hit_root = _rail_root_widget(hit_widget)
        if hit_root is not None and hit_root is not source_root:
            target_button = _slot_button_at_global_point(qt, hit_root, point)
            if target_button is not None:
                slot_id = target_button.property("actionRailSlotId")
                return _SlotDragDropTarget(
                    slot_id=slot_id if isinstance(slot_id, str) else None,
                    callbacks=_slot_edit_callbacks_from_button(target_button),
                    inside_action_rail=True,
                    same_rail=False,
                )
            return _SlotDragDropTarget(inside_action_rail=True)
    return _slot_drag_cross_rail_target_from_geometry(qt, source_root, points)


def _slot_drag_cross_rail_target_from_geometry(
    qt: object,
    source_root: object,
    points: tuple[object, ...],
) -> _SlotDragDropTarget:
    widgets = _application_widgets(qt)
    if not widgets:
        return _SlotDragDropTarget()

    for widget in widgets:
        slot_id = _slot_id_from_button(widget)
        if slot_id is None:
            continue
        target_root = _rail_root_widget(widget)
        if target_root is None or target_root is source_root:
            continue
        if any(_global_point_inside_widget(widget, point) for point in points):
            return _SlotDragDropTarget(
                slot_id=slot_id,
                callbacks=_slot_edit_callbacks_from_button(widget),
                inside_action_rail=True,
                same_rail=False,
            )

    seen_roots: set[int] = set()
    for widget in widgets:
        target_root = _rail_root_widget(widget)
        if target_root is None or target_root is source_root:
            continue
        root_identity = id(target_root)
        if root_identity in seen_roots:
            continue
        seen_roots.add(root_identity)
        if any(_global_point_inside_widget(target_root, point) for point in points):
            return _SlotDragDropTarget(inside_action_rail=True, same_rail=False)

    return _SlotDragDropTarget()


def _slot_edit_callbacks_from_button(button: object | None) -> SlotEditCallbacks | None:
    callbacks = getattr(button, "_actionrail_slot_edit_callbacks", None)
    if not isinstance(callbacks, SlotEditCallbacks):
        return None
    owner = callbacks.owner
    slot_edit_unlocked = getattr(owner, "slot_edit_unlocked", None)
    if not callable(slot_edit_unlocked):
        return callbacks
    with suppress(Exception):
        live_unlocked = bool(slot_edit_unlocked())
        if live_unlocked != callbacks.unlocked:
            return replace(callbacks, unlocked=live_unlocked)
    return callbacks


def _slot_id_from_button(button: object) -> str | None:
    try:
        slot_id = button.property("actionRailSlotId")
    except Exception:
        return None
    return slot_id if isinstance(slot_id, str) else None


def _first_widget_at_global_points(qt: object, points: tuple[object, ...]) -> object | None:
    for point in points:
        hit_widget = _widget_at_global_point(qt, point)
        if hit_widget is not None:
            return hit_widget
    return None


def _slot_id_at_global_point(
    qt: object,
    source_root: object,
    global_point: object | None,
) -> str | None:
    button = _slot_button_at_global_point(qt, source_root, global_point)
    if button is None:
        return None
    try:
        slot_id = button.property("actionRailSlotId")
    except Exception:
        return None
    return slot_id if isinstance(slot_id, str) else None


def _slot_button_at_global_point(
    qt: object,
    source_root: object,
    global_point: object | None,
) -> object | None:
    button_class = getattr(getattr(qt, "QtWidgets", None), "QPushButton", None)
    find_children = getattr(source_root, "findChildren", None)
    if button_class is None or not callable(find_children):
        return None
    with suppress(Exception):
        buttons = find_children(button_class)
    if not buttons:
        return None
    for button in buttons:
        try:
            slot_id = button.property("actionRailSlotId")
        except Exception:
            continue
        if isinstance(slot_id, str) and _global_point_inside_widget(button, global_point):
            return button
    return None


def _global_point_inside_widget(widget: object, global_point: object | None) -> bool:
    if global_point is None:
        return False
    map_from_global = getattr(widget, "mapFromGlobal", None)
    rect = getattr(widget, "rect", None)
    if not callable(map_from_global) or not callable(rect):
        return True
    with suppress(Exception):
        local_point = map_from_global(global_point)
        contains = getattr(rect(), "contains", None)
        if callable(contains):
            return bool(contains(local_point))
    return True


def _widget_has_global_geometry(widget: object) -> bool:
    return callable(getattr(widget, "mapFromGlobal", None)) and callable(
        getattr(widget, "rect", None)
    )


def _widget_at_global_point(qt: object, global_point: object | None) -> object | None:
    app_class = getattr(getattr(qt, "QtWidgets", None), "QApplication", None)
    widget_at = getattr(app_class, "widgetAt", None)
    if global_point is None or not callable(widget_at):
        return None
    with suppress(Exception):
        return widget_at(global_point)
    return None


def _application_widgets(qt: object) -> tuple[object, ...]:
    app_class = getattr(getattr(qt, "QtWidgets", None), "QApplication", None)
    if app_class is None:
        return ()

    owners: list[object] = [app_class]
    instance = getattr(app_class, "instance", None)
    if callable(instance):
        with suppress(Exception):
            app = instance()
            if app is not None:
                owners.append(app)

    for owner in owners:
        all_widgets = getattr(owner, "allWidgets", None)
        if not callable(all_widgets):
            continue
        with suppress(Exception):
            widgets = all_widgets()
            return tuple(widgets) if widgets is not None else ()
    return ()


def _slot_button_ancestor(qt: object, widget: object | None) -> object | None:
    button_class = getattr(getattr(qt, "QtWidgets", None), "QPushButton", None)
    while widget is not None:
        if button_class is not None and isinstance(widget, button_class):
            try:
                if isinstance(widget.property("actionRailSlotId"), str):
                    return widget
            except Exception:
                return None
        parent = getattr(widget, "parent", None)
        widget = parent() if callable(parent) else None
    return None


def _rail_root_widget(widget: object | None) -> object | None:
    while widget is not None:
        property_value = getattr(widget, "property", None)
        with suppress(Exception):
            if callable(property_value) and property_value(ACTION_RAIL_ROOT_PROPERTY) == "true":
                return widget
        object_name = getattr(widget, "objectName", None)
        with suppress(Exception):
            if callable(object_name) and _is_action_rail_root_object_name(object_name()):
                return widget
        parent = getattr(widget, "parent", None)
        widget = parent() if callable(parent) else None
    return None


def _is_action_rail_root_object_name(name: object) -> bool:
    return name == ACTION_RAIL_ROOT_OBJECT_NAME or (
        isinstance(name, str) and name.startswith(ACTION_RAIL_VIEWPORT_OVERLAY_PREFIX)
    )


def _accept_event(event: object) -> None:
    accept = getattr(event, "accept", None)
    if callable(accept):
        with suppress(Exception):
            accept()


def event_should_pass_through_to_maya(
    event: object,
    *,
    qt: object | None = None,
    captures_navigation: bool = False,
) -> bool:
    """Return whether a Qt input event should be ignored so Maya handles it."""

    if captures_navigation:
        return False
    if qt is None:
        qt = load()

    if _event_is_wheel(event, qt):
        return True
    if _event_has_alt_modifier(event, qt):
        return True
    return _event_uses_navigation_button(event, qt)


def _event_is_wheel(event: object, qt: object) -> bool:
    event_type = getattr(event, "type", None)
    wheel_type = getattr(getattr(getattr(qt, "QtCore", None), "QEvent", object), "Wheel", None)
    if wheel_type is None:
        return False
    if callable(event_type):
        with suppress(Exception):
            return event_type() == wheel_type
    return False


def _event_has_alt_modifier(event: object, qt: object) -> bool:
    modifiers = getattr(event, "modifiers", None)
    alt_modifier = getattr(getattr(getattr(qt, "QtCore", None), "Qt", object), "AltModifier", 0)
    if not alt_modifier:
        return False
    if callable(modifiers):
        with suppress(Exception):
            return bool(modifiers() & alt_modifier)
    return False


def _event_uses_navigation_button(event: object, qt: object) -> bool:
    button = getattr(event, "button", None)
    buttons = getattr(event, "buttons", None)
    qt_constants = getattr(getattr(qt, "QtCore", None), "Qt", object())
    navigation_buttons = (
        getattr(qt_constants, "MiddleButton", 0),
        getattr(qt_constants, "RightButton", 0),
    )
    for value_method in (button, buttons):
        if callable(value_method):
            with suppress(Exception):
                value = value_method()
                if any(value & button_value for button_value in navigation_buttons):
                    return True
    return False


def _button_class(qt: object) -> type:
    base = qt.QtWidgets.QPushButton
    if (
        not hasattr(qt.QtWidgets, "QStyleOptionButton")
        or not hasattr(qt.QtWidgets, "QStyle")
        or not hasattr(qt.QtGui, "QPainter")
    ):
        return base

    class ActionRailButton(base):  # type: ignore[misc, valid-type]
        _actionrail_supports_slot_drag_events = True

        def mousePressEvent(self, event):  # type: ignore[no-untyped-def]  # noqa: N802
            if event_should_pass_through_to_maya(event, qt=qt):
                event.ignore()
                return None
            if _handle_slot_drag_press(self, event):
                return None
            return super().mousePressEvent(event)

        def mouseMoveEvent(self, event):  # type: ignore[no-untyped-def]  # noqa: N802
            if event_should_pass_through_to_maya(event, qt=qt):
                event.ignore()
                return None
            if _handle_slot_drag_move(self, event):
                return None
            return super().mouseMoveEvent(event)

        def mouseReleaseEvent(self, event):  # type: ignore[no-untyped-def]  # noqa: N802
            if event_should_pass_through_to_maya(event, qt=qt):
                event.ignore()
                return None
            if _handle_slot_drag_release(self, event):
                return None
            return super().mouseReleaseEvent(event)

        def wheelEvent(self, event):  # type: ignore[no-untyped-def]  # noqa: N802
            if event_should_pass_through_to_maya(event, qt=qt):
                event.ignore()
                return None
            return super().wheelEvent(event)

        def paintEvent(self, event):  # type: ignore[no-untyped-def]  # noqa: N802
            painter = qt.QtGui.QPainter(self)
            try:
                option = qt.QtWidgets.QStyleOptionButton()
                self.initStyleOption(option)
                option.text = ""
                option.icon = qt.QtGui.QIcon()
                icon = self.icon()

                if icon.isNull():
                    self.style().drawControl(
                        qt.QtWidgets.QStyle.CE_PushButton,
                        option,
                        painter,
                        self,
                    )
                else:
                    backplate = self.rect()
                    backplate_inset = _button_backplate_inset(self)
                    if backplate_inset:
                        backplate = backplate.adjusted(
                            backplate_inset,
                            backplate_inset,
                            -backplate_inset,
                            -backplate_inset,
                        )
                    _draw_icon_backplate(
                        qt,
                        painter,
                        backplate,
                        _button_icon_backplate(self),
                        _button_icon_border(self),
                    )
                    if _button_is_active(self):
                        _draw_icon_backplate_border(
                            qt,
                            painter,
                            backplate,
                            _button_active_border(self),
                        )
                    target = backplate
                    icon_inset = _button_icon_inset(self)
                    if icon_inset:
                        target = target.adjusted(
                            icon_inset,
                            icon_inset,
                            -icon_inset,
                            -icon_inset,
                        )
                    pixmap = _icon_pixmap_for_painter(qt, painter, icon, target)
                    if not pixmap.isNull():
                        painter.drawPixmap(target, pixmap)

                label = _button_label(self)
                if label:
                    painter.setFont(self.font())
                    painter.setPen(self.palette().buttonText().color())
                    painter.drawText(
                        self.rect(),
                        qt.QtCore.Qt.AlignCenter | qt.QtCore.Qt.TextWordWrap,
                        label,
                    )

                secondary = _button_secondary(self)
                if secondary:
                    font = qt.QtGui.QFont(self.font())
                    font.setPointSize(_secondary_font_size(font.pointSize()))
                    secondary = _button_secondary_display_text(
                        qt,
                        font,
                        secondary,
                        _button_secondary_max_width(self),
                    )
                    painter.setFont(font)
                    painter.setPen(self.palette().buttonText().color())
                    painter.drawText(
                        _button_secondary_rect(self, qt, secondary, font),
                        qt.QtCore.Qt.AlignRight | qt.QtCore.Qt.AlignBottom,
                        secondary,
                    )
            finally:
                painter.end()
                _ = event

    return ActionRailButton


def _draw_icon_backplate(
    qt: object,
    painter: object,
    rect: object,
    color: str = DEFAULT_THEME.spell_icon_background,
    border_color: str = DEFAULT_THEME.spell_icon_border,
) -> bool:
    fill_rect = getattr(painter, "fillRect", None)
    if not callable(fill_rect):
        return False
    try:
        fill_rect(rect, _qt_color(qt, color))
    except Exception:
        return False
    _draw_icon_backplate_border(qt, painter, rect, border_color)
    return True


def _draw_icon_backplate_border(
    qt: object,
    painter: object,
    rect: object,
    color: str,
) -> bool:
    draw_rect = getattr(painter, "drawRect", None)
    if not callable(draw_rect):
        return False
    try:
        set_pen = getattr(painter, "setPen", None)
        if callable(set_pen):
            set_pen(_qt_color(qt, color))
        draw_rect(_adjusted_rect(rect, 0, 0, -1, -1))
    except Exception:
        return False
    return True


def _button_is_active(button: object) -> bool:
    try:
        return button.property("actionRailActive") == "true"
    except Exception:
        return False


def _button_active_border(button: object) -> str:
    try:
        color = button.property("actionRailButtonActiveBorder")
    except Exception:
        color = None
    return color if isinstance(color, str) and color else DEFAULT_THEME.button_active_border


def _button_icon_backplate(button: object) -> str:
    try:
        color = button.property("actionRailIconBackplate")
    except Exception:
        color = None
    return color if isinstance(color, str) and color else DEFAULT_THEME.spell_icon_background


def _button_icon_border(button: object) -> str:
    try:
        color = button.property("actionRailIconBorder")
    except Exception:
        color = None
    return color if isinstance(color, str) and color else DEFAULT_THEME.spell_icon_border


def _button_backplate_inset(button: object) -> int:
    try:
        raw_inset = button.property("actionRailButtonBackplateInset")
    except Exception:
        raw_inset = None
    if isinstance(raw_inset, int) and raw_inset > 0:
        return raw_inset
    return 0


def _icon_pixmap_for_painter(qt: object, painter: object, icon: object, target: object) -> object:
    size = target.size()
    width = _qt_size_value(size, "width")
    height = _qt_size_value(size, "height")
    scale = _painter_device_scale(painter)
    if scale <= 1.0 or width <= 0 or height <= 0:
        return icon.pixmap(size)

    scaled_size = qt.QtCore.QSize(
        max(1, int(round(width * scale))),
        max(1, int(round(height * scale))),
    )
    pixmap = icon.pixmap(scaled_size)
    with suppress(Exception):
        pixmap.setDevicePixelRatio(scale)
    return pixmap


def _painter_device_scale(painter: object) -> float:
    device_transform = getattr(painter, "deviceTransform", None)
    if callable(device_transform):
        with suppress(Exception):
            transform = device_transform()
            m11 = getattr(transform, "m11", None)
            m22 = getattr(transform, "m22", None)
            x_scale = abs(float(m11())) if callable(m11) else 1.0
            y_scale = abs(float(m22())) if callable(m22) else 1.0
            return max(x_scale, y_scale, 1.0)

    device = getattr(painter, "device", None)
    if callable(device):
        with suppress(Exception):
            pixel_ratio = getattr(device(), "devicePixelRatioF", None)
            if callable(pixel_ratio):
                return max(float(pixel_ratio()), 1.0)
    return 1.0


def _qt_size_value(size: object, method_name: str) -> int:
    value = getattr(size, method_name, None)
    if callable(value):
        with suppress(Exception):
            return int(value())
    raw = getattr(size, method_name, 0)
    return int(raw) if isinstance(raw, int) else 0


def _qt_color(qt: object, color: str) -> object:
    color_class = getattr(getattr(qt, "QtGui", None), "QColor", None)
    if color_class is None:
        return color
    with suppress(Exception):
        return color_class(color)
    return color


def _qt_rgb_color(
    qt: object,
    red: int,
    green: int,
    blue: int,
    *,
    alpha: float = 1.0,
) -> object:
    color_class = getattr(getattr(qt, "QtGui", None), "QColor", None)
    alpha = max(0.0, min(1.0, float(alpha)))
    if color_class is None:
        if alpha >= 1.0:
            return f"rgb({red}, {green}, {blue})"
        return f"rgba({red}, {green}, {blue}, {round(alpha * 255)})"
    with suppress(Exception):
        if alpha >= 1.0:
            return color_class(red, green, blue)
        return color_class(red, green, blue, round(alpha * 255))
    if alpha >= 1.0:
        return f"rgb({red}, {green}, {blue})"
    return f"rgba({red}, {green}, {blue}, {round(alpha * 255)})"


def _adjusted_rect(rect: object, left: int, top: int, right: int, bottom: int) -> object:
    adjusted = getattr(rect, "adjusted", None)
    if callable(adjusted):
        with suppress(Exception):
            return adjusted(left, top, right, bottom)
    return rect


def set_slot_key_label(root: object, slot_id: str, key_label: str) -> int:
    """Update rendered button text for a slot and return the number of matches."""

    dense_setter = getattr(root, "_actionrail_set_slot_key_label", None)
    if callable(dense_setter):
        with suppress(Exception):
            return int(dense_setter(slot_id, key_label))

    qt = load()
    updated = 0
    for button in root.findChildren(qt.QtWidgets.QPushButton):
        if button.property("actionRailSlotId") != slot_id:
            continue

        label = button.property("actionRailLabel")
        if not isinstance(label, str):
            label = button.text().split("\n", 1)[0]
        diagnostic_badge = button.property("actionRailDiagnosticBadge")
        button.setProperty("actionRailKeyLabel", key_label)
        button.setText(
            _button_text(
                label,
                key_label,
                diagnostic_badge if isinstance(diagnostic_badge, str) else "",
            )
        )
        updated += 1

    return updated


def resolve_slot_render_state(
    item: StackItem,
    registry: ActionRegistry,
    context: PredicateContext | None = None,
    *,
    key_label: str | None = None,
) -> SlotRenderState:
    """Resolve the public render-state contract for one action slot."""

    return _slot_state.resolve_slot_render_state(
        item,
        registry,
        context,
        key_label=key_label,
    )


def refresh_predicate_state(
    root: object,
    spec: StackSpec,
    registry: ActionRegistry,
    *,
    state_snapshot: MayaStateSnapshot | None = None,
    cmds_module: object | None = None,
) -> PredicateRefreshResult:
    """Apply fresh predicate-driven enabled/active state to rendered buttons.

    If the predicate-visible slot set differs from the currently rendered
    buttons, the caller should rebuild the rail so hidden slots can be inserted
    or removed without leaving empty cluster frames.
    """

    context = PredicateContext(state=state_snapshot, registry=registry, cmds_module=cmds_module)
    dense_refresh = getattr(root, "_actionrail_refresh_dense", None)
    if callable(dense_refresh):
        with suppress(Exception):
            return dense_refresh(context)

    visible_items = tuple(_visible_action_items(spec, context))
    visible_slot_ids = tuple(item.id for item in visible_items)
    buttons = _slot_buttons(root)
    rendered_slot_ids = tuple(buttons)
    if visible_slot_ids != rendered_slot_ids:
        return PredicateRefreshResult(
            refreshed=0,
            needs_rebuild=True,
            visible_slot_ids=visible_slot_ids,
            rendered_slot_ids=rendered_slot_ids,
        )

    refreshed = 0
    for item in visible_items:
        button = buttons.get(item.id)
        if button is None:
            continue

        key_label = button.property("actionRailKeyLabel")
        state = resolve_slot_render_state(
            item,
            registry,
            context,
            key_label=key_label if isinstance(key_label, str) else None,
        )
        refreshed += _apply_slot_render_state(button, state)

    return PredicateRefreshResult(
        refreshed=refreshed,
        needs_rebuild=False,
        visible_slot_ids=visible_slot_ids,
        rendered_slot_ids=rendered_slot_ids,
    )


def _button_label(button: object) -> str:
    try:
        label = button.property("actionRailLabel")
    except Exception:
        label = None
    if isinstance(label, str):
        return label.split("\n", 1)[0]

    text = getattr(button, "text", None)
    if callable(text):
        with suppress(Exception):
            return text().split("\n", 1)[0]
    return ""


def _button_secondary(button: object) -> str:
    try:
        key_label = button.property("actionRailKeyLabel")
    except Exception:
        key_label = ""
    try:
        diagnostic_badge = button.property("actionRailDiagnosticBadge")
    except Exception:
        diagnostic_badge = ""
    return _button_secondary_text(
        key_label if isinstance(key_label, str) else "",
        diagnostic_badge if isinstance(diagnostic_badge, str) else "",
    )


def _secondary_font_size(point_size: int) -> int:
    if point_size <= 0:
        return 6
    return max(6, int(point_size * 0.6))


def _button_secondary_display_text(
    qt: object,
    font: object,
    secondary: str,
    max_width: int,
) -> str:
    candidates = (
        secondary,
        _compact_hotkey_label(secondary),
        _dense_hotkey_label(secondary),
    )
    for candidate in dict.fromkeys(candidates):
        if _text_width(qt, font, candidate) <= max_width:
            return candidate
    return _elide_text(qt, font, candidates[-1], max_width)


def _compact_hotkey_label(label: str) -> str:
    replacements = {
        "Control": "C",
        "Ctrl": "C",
        "Shift": "S",
        "Alt": "A",
        "Command": "M",
        "Cmd": "M",
        "Meta": "M",
    }
    return "+".join(replacements.get(part, part) for part in label.split("+"))


def _dense_hotkey_label(label: str) -> str:
    parts = _compact_hotkey_label(label).split("+")
    if len(parts) < 2:
        return label
    return "".join(parts[:-1]) + f"+{parts[-1]}"


def _elide_text(qt: object, font: object, text: str, max_width: int) -> str:
    if _text_width(qt, font, text) <= max_width:
        return text

    marker = "..."
    if _text_width(qt, font, marker) > max_width:
        return text[-1:]

    best = marker
    for prefix_length in range(1, len(text)):
        for suffix_length in range(1, len(text) - prefix_length + 1):
            candidate = f"{text[:prefix_length]}{marker}{text[-suffix_length:]}"
            if _text_width(qt, font, candidate) <= max_width:
                best = candidate
                continue
            break
    return best


def _button_secondary_rect(
    button: object,
    qt: object,
    secondary: str,
    font: object,
) -> object:
    rect = button.rect()
    max_width = _button_secondary_max_width(button)
    width = max(8, min(max_width, _text_width(qt, font, secondary) + 3))
    height = 9
    return qt.QtCore.QRect(
        rect.right() - width - 2,
        rect.bottom() - height - 1,
        width,
        height,
    )


def _button_secondary_max_width(button: object) -> int:
    try:
        return max(8, button.rect().width() - 4)
    except Exception:
        return 28


def _text_width(qt: object, font: object, text: str) -> int:
    metrics_class = getattr(qt.QtGui, "QFontMetrics", None)
    if metrics_class is not None:
        with suppress(Exception):
            metrics = metrics_class(font)
            horizontal_advance = getattr(metrics, "horizontalAdvance", None)
            if callable(horizontal_advance):
                return int(horizontal_advance(text))
            width = getattr(metrics, "width", None)
            if callable(width):
                return int(width(text))
    return len(text) * 5


def _apply_slot_render_state(button: object, state: SlotRenderState) -> int:
    if _button_property(button, "actionRailSlotDragSource") == "true":
        return 0

    refreshed = 0
    style_needs_refresh = False

    refreshed += _set_button_property(button, "actionRailLabel", state.label)
    refreshed += _set_button_property(button, "actionRailKeyLabel", state.key_label)
    refreshed += _set_button_property(button, "actionRailIcon", state.icon)
    refreshed += _set_button_property(button, "actionRailIconPath", state.icon_path)
    refreshed += _set_button_property(button, "actionRailIconName", state.icon_name)
    tone_changed = _set_button_property(button, "actionRailTone", state.tone)
    active_changed = _set_button_property(
        button,
        "actionRailActive",
        state.active_property,
    )
    locked_changed = _set_button_property(
        button,
        "actionRailLocked",
        "true" if state.locked else "false",
    )
    diagnostic_code_changed = _set_button_property(
        button,
        "actionRailDiagnosticCode",
        state.diagnostic_code,
    )
    diagnostic_severity_changed = _set_button_property(
        button,
        "actionRailDiagnosticSeverity",
        state.diagnostic_severity,
    )
    refreshed += _set_button_property(
        button,
        "actionRailDiagnosticBadge",
        state.diagnostic_badge,
    )
    refreshed += tone_changed + active_changed + locked_changed
    refreshed += diagnostic_code_changed + diagnostic_severity_changed
    style_needs_refresh = bool(
        tone_changed
        or active_changed
        or locked_changed
        or diagnostic_code_changed
        or diagnostic_severity_changed
    )
    refreshed += _apply_button_icon(button, state.icon_path, state.icon_name)

    text = getattr(button, "text", None)
    set_text = getattr(button, "setText", None)
    if callable(text) and callable(set_text):
        try:
            if text() != state.text:
                set_text(state.text)
                refreshed += 1
        except Exception:
            pass

    tool_tip = getattr(button, "toolTip", None)
    set_tool_tip = getattr(button, "setToolTip", None)
    if callable(tool_tip) and callable(set_tool_tip):
        try:
            if tool_tip() != state.tooltip:
                set_tool_tip(state.tooltip)
                refreshed += 1
        except Exception:
            pass
    elif state.tooltip:
        with suppress(Exception):
            button.setToolTip(state.tooltip)

    is_enabled = getattr(button, "isEnabled", None)
    set_enabled = getattr(button, "setEnabled", None)
    if callable(is_enabled) and callable(set_enabled):
        try:
            if bool(is_enabled()) != state.enabled:
                set_enabled(state.enabled)
                refreshed += 1
        except Exception:
            pass

    if style_needs_refresh:
        _refresh_button_style(button)

    return refreshed


def _apply_button_icon(button: object, icon_path: str, icon_name: str = "") -> int:
    set_icon = getattr(button, "setIcon", None)
    if not callable(set_icon):
        return 0

    icon_source = _qt_icon_source(icon_path, icon_name)
    try:
        current = button.property("actionRailAppliedIconSource")
    except Exception:
        current = None

    if current == icon_source:
        return 0

    try:
        qt = load()
        set_icon(qt.QtGui.QIcon(icon_source) if icon_source else qt.QtGui.QIcon())
        set_icon_size = getattr(button, "setIconSize", None)
        if callable(set_icon_size) and icon_source:
            icon_size = _button_icon_size(button)
            set_icon_size(qt.QtCore.QSize(icon_size, icon_size))
        button.setProperty("actionRailAppliedIconSource", icon_source)
    except Exception:
        return 0
    return 1


def _qt_icon_source(icon_path: str, icon_name: str = "") -> str:
    if icon_path:
        return icon_path
    if not icon_name or icon_name.startswith(":"):
        return icon_name
    return f":/{icon_name}"


def _button_icon_size(button: object) -> int:
    try:
        raw_size = button.property("actionRailButtonIconSize")
    except Exception:
        raw_size = None
    if isinstance(raw_size, int) and raw_size > 0:
        return raw_size
    return 18


def _button_icon_inset(button: object) -> int:
    try:
        raw_inset = button.property("actionRailButtonIconInset")
    except Exception:
        raw_inset = None
    if isinstance(raw_inset, int) and raw_inset > 0:
        return raw_inset
    return 0


def _set_button_property(button: object, name: str, value: object) -> int:
    current = _button_property(button, name)

    if current == value:
        return 0

    try:
        button.setProperty(name, value)
    except Exception:
        return 0
    return 1


def _scaled_theme(theme: ActionRailTheme, scale: float) -> ActionRailTheme:
    if scale == 1.0:
        return theme

    def scaled(value: int, *, minimum: int = 1) -> int:
        return max(minimum, round(value * scale))

    return replace(
        theme,
        button_size=scaled(theme.button_size),
        frame_padding=scaled(theme.frame_padding),
        frame_spacing=scaled(theme.frame_spacing, minimum=0),
        cluster_border_width=scaled(theme.cluster_border_width),
        cluster_border_radius=scaled(theme.cluster_border_radius, minimum=0),
        button_border_width=scaled(theme.button_border_width),
        button_border_radius=scaled(theme.button_border_radius, minimum=0),
        button_font_size=scaled(theme.button_font_size),
    )


def _frame_main_axis_size(item_count: int, theme: ActionRailTheme) -> int:
    spacing = theme.frame_spacing * max(item_count - 1, 0)
    outer_padding = (theme.frame_padding + theme.cluster_border_width) * 2
    return (theme.button_outer_size * item_count) + spacing + outer_padding


def _uses_wrapped_layout(layout: RailLayout) -> bool:
    return layout.rows > 1 and layout.columns > 1


def _should_group_slot_item(item: StackItem, layout: RailLayout) -> bool:
    if item.type == "toolButton":
        return True
    return item.type == "button" and not _uses_wrapped_layout(layout)


def _grid_position(index: int, layout: RailLayout) -> tuple[int, int]:
    if layout.orientation == "horizontal":
        return index // layout.columns, index % layout.columns
    return index % layout.rows, index // layout.rows


def _slot_buttons(root: object) -> dict[str, object]:
    qt = load()
    buttons: dict[str, object] = {}
    for button in root.findChildren(qt.QtWidgets.QPushButton):
        slot_id = button.property("actionRailSlotId")
        if isinstance(slot_id, str) and slot_id:
            buttons[slot_id] = button
    return buttons


def _refresh_button_style(button: object) -> None:
    with suppress(Exception):
        style = button.style()
        style.unpolish(button)
        style.polish(button)
    with suppress(Exception):
        button.update()


def _button_property(button: object, name: str) -> object:
    try:
        return button.property(name)
    except Exception:
        return None
