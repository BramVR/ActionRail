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
from .actions import ActionRegistry
from .predicates import PredicateContext
from .qt import load
from .spec import RailLayout, StackItem, StackSpec
from .state import MayaStateSnapshot
from .theme import DEFAULT_THEME, ActionRailTheme, generate_style_sheet

BUTTON_SIZE = DEFAULT_THEME.button_size
BUTTON_OUTER_SIZE = DEFAULT_THEME.button_outer_size
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
    "PredicateRefreshResult",
    "SlotRenderState",
    "build_rail",
    "build_collapsed_handle",
    "build_transform_stack",
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
                self.setObjectName("ActionRailRoot")
                self.setAttribute(qt.QtCore.Qt.WA_TranslucentBackground, True)
                self.setAttribute(qt.QtCore.Qt.WA_NoSystemBackground, True)
                self.setFocusPolicy(qt.QtCore.Qt.NoFocus)

            def mousePressEvent(self, event):  # type: ignore[no-untyped-def]
                event.ignore()

            def mouseMoveEvent(self, event):  # type: ignore[no-untyped-def]
                event.ignore()

            def mouseReleaseEvent(self, event):  # type: ignore[no-untyped-def]
                event.ignore()

            def wheelEvent(self, event):  # type: ignore[no-untyped-def]
                event.ignore()

        return _ActionRailRoot()


def build_rail(
    spec: StackSpec,
    registry: ActionRegistry,
    theme: ActionRailTheme = DEFAULT_THEME,
    state_snapshot: MayaStateSnapshot | None = None,
    cmds_module: object | None = None,
) -> object:
    """Build an ActionRail widget from a stack spec."""

    qt = load()
    theme = _scaled_theme(theme, spec.layout.scale)
    context = PredicateContext(state=state_snapshot, registry=registry, cmds_module=cmds_module)
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

        if item.type == "toolButton":
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
                        spec.layout.orientation,
                        context,
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
                    spec.layout.orientation,
                    context,
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
                    spec.layout.orientation,
                    context,
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
    return root


def build_collapsed_handle(
    spec: StackSpec,
    on_reveal: Callable[[], None],
    theme: ActionRailTheme = DEFAULT_THEME,
) -> object:
    """Build the small edge-tab handle shown while a rail is collapsed."""

    qt = load()
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
) -> object:
    """Compatibility wrapper for the generic ActionRail rail builder."""

    return build_rail(
        spec,
        registry,
        theme=theme,
        state_snapshot=state_snapshot,
        cmds_module=cmds_module,
    )


def _build_cluster(
    items: tuple[StackItem, ...],
    registry: ActionRegistry,
    theme: ActionRailTheme,
    orientation: str,
    context: PredicateContext | None = None,
) -> object:
    qt = load()
    frame = qt.QtWidgets.QFrame()
    frame.setProperty("actionRailRole", "cluster")
    layout_class = (
        qt.QtWidgets.QHBoxLayout
        if orientation == "horizontal"
        else qt.QtWidgets.QVBoxLayout
    )
    layout = layout_class(frame)
    layout.setContentsMargins(
        theme.frame_padding,
        theme.frame_padding,
        theme.frame_padding,
        theme.frame_padding,
    )
    layout.setSpacing(theme.frame_spacing)

    for item in items:
        layout.addWidget(_build_button(item, registry, theme, context))

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
    orientation: str,
    context: PredicateContext | None = None,
) -> object:
    qt = load()
    frame = qt.QtWidgets.QFrame()
    frame.setProperty("actionRailRole", "cluster")
    layout = qt.QtWidgets.QVBoxLayout(frame)
    layout.setContentsMargins(
        theme.frame_padding,
        theme.frame_padding,
        theme.frame_padding,
        theme.frame_padding,
    )
    layout.setSpacing(0)
    layout.addWidget(_build_button(item, registry, theme, context))

    frame.setFixedSize(theme.rail_width, theme.rail_width)
    return frame


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
    context: PredicateContext | None = None,
) -> object:
    qt = load()
    state = resolve_slot_render_state(item, registry, context)
    button = _button_class(qt)(state.text)
    button.setProperty("actionRailRole", "button")
    button.setProperty("actionRailSlotId", item.id)
    button.setProperty("actionRailButtonIconSize", theme.button_size)
    button.setProperty("actionRailButtonIconInset", theme.button_border_width)
    button.setFixedSize(theme.button_outer_size, theme.button_outer_size)
    button.setFocusPolicy(qt.QtCore.Qt.NoFocus)
    button.setCursor(
        qt.QtCore.Qt.PointingHandCursor if item.action else qt.QtCore.Qt.ArrowCursor
    )
    _apply_slot_render_state(button, state)
    if item.action:
        button.clicked.connect(
            lambda _checked=False, action_id=item.action: registry.run(action_id)
        )
    return button


def _button_class(qt: object) -> type:
    base = qt.QtWidgets.QPushButton
    if (
        not hasattr(qt.QtWidgets, "QStyleOptionButton")
        or not hasattr(qt.QtWidgets, "QStyle")
        or not hasattr(qt.QtGui, "QPainter")
    ):
        return base

    class ActionRailButton(base):  # type: ignore[misc, valid-type]
        def paintEvent(self, event):  # type: ignore[no-untyped-def]  # noqa: N802
            painter = qt.QtGui.QPainter(self)
            try:
                option = qt.QtWidgets.QStyleOptionButton()
                self.initStyleOption(option)
                option.text = ""
                option.icon = qt.QtGui.QIcon()
                self.style().drawControl(qt.QtWidgets.QStyle.CE_PushButton, option, painter, self)

                icon = self.icon()
                if not icon.isNull():
                    target = self.rect()
                    inset = _button_icon_inset(self)
                    if inset:
                        target = target.adjusted(inset, inset, -inset, -inset)
                    pixmap = icon.pixmap(target.size())
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


def set_slot_key_label(root: object, slot_id: str, key_label: str) -> int:
    """Update rendered button text for a slot and return the number of matches."""

    qt = load()
    updated = 0
    for button in root.findChildren(qt.QtWidgets.QPushButton):
        if button.property("actionRailSlotId") != slot_id:
            continue

        label = button.property("actionRailLabel")
        if not isinstance(label, str) or not label:
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
    try:
        current = button.property(name)
    except Exception:
        current = None

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
