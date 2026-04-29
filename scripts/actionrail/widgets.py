"""Qt widgets for ActionRail stack specs."""

from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass, replace

from .actions import ActionRegistry
from .icons import resolve_icon_path
from .predicates import PredicateContext, availability_blocking_targets, evaluate_predicate
from .qt import load
from .spec import StackItem, StackSpec
from .state import MayaStateSnapshot
from .theme import DEFAULT_THEME, ActionRailTheme, generate_style_sheet

BUTTON_SIZE = DEFAULT_THEME.button_size
BUTTON_OUTER_SIZE = DEFAULT_THEME.button_outer_size
FRAME_PADDING = DEFAULT_THEME.frame_padding
FRAME_SPACING = DEFAULT_THEME.frame_spacing
RAIL_WIDTH = DEFAULT_THEME.rail_width
STYLE_SHEET = generate_style_sheet(DEFAULT_THEME)


@dataclass(frozen=True)
class PredicateRefreshResult:
    """Result of applying fresh predicate state to an existing rail widget."""

    refreshed: int
    needs_rebuild: bool
    visible_slot_ids: tuple[str, ...]
    rendered_slot_ids: tuple[str, ...]


@dataclass(frozen=True)
class SlotRenderState:
    """Resolved, mutable-at-runtime state for one rendered action slot."""

    label: str
    key_label: str
    icon: str
    icon_path: str
    tone: str
    tooltip: str
    enabled: bool
    active: bool
    diagnostic_code: str = ""
    diagnostic_severity: str = ""
    diagnostic_badge: str = ""

    @property
    def text(self) -> str:
        return _button_text(self.label, self.key_label, self.diagnostic_badge)

    @property
    def active_property(self) -> str:
        return "true" if self.active else "false"


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


def build_transform_stack(
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

    layout_class = (
        qt.QtWidgets.QHBoxLayout
        if spec.layout.orientation == "horizontal"
        else qt.QtWidgets.QVBoxLayout
    )
    layout = layout_class(root)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)

    pending_tools: list[StackItem] = []
    for item in spec.items:
        if not _is_item_visible(item, context):
            continue

        if item.type == "toolButton":
            pending_tools.append(item)
            continue

        if pending_tools:
            layout.addWidget(
                _build_cluster(
                    tuple(pending_tools),
                    registry,
                    theme,
                    spec.layout.orientation,
                    context,
                )
            )
            pending_tools.clear()

        if item.type == "spacer":
            layout.addSpacing(item.size)
            continue

        layout.addWidget(
            _build_single_button(item, registry, theme, spec.layout.orientation, context),
            0,
            qt.QtCore.Qt.AlignLeft,
        )

    if pending_tools:
        layout.addWidget(
            _build_cluster(tuple(pending_tools), registry, theme, spec.layout.orientation, context)
        )

    root.adjustSize()
    root.setFixedSize(root.sizeHint())
    return root


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


def _build_button(
    item: StackItem,
    registry: ActionRegistry,
    theme: ActionRailTheme,
    context: PredicateContext | None = None,
) -> object:
    qt = load()
    state = _slot_render_state(item, registry, context)
    button = qt.QtWidgets.QPushButton(state.text)
    button.setProperty("actionRailRole", "button")
    button.setProperty("actionRailSlotId", item.id)
    _apply_slot_render_state(button, state)
    button.setFixedSize(theme.button_outer_size, theme.button_outer_size)
    button.setFocusPolicy(qt.QtCore.Qt.NoFocus)
    button.setCursor(qt.QtCore.Qt.PointingHandCursor)
    button.clicked.connect(lambda _checked=False, action_id=item.action: registry.run(action_id))
    return button


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
        state = _slot_render_state(
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


def _button_text(label: str, key_label: str, diagnostic_badge: str = "") -> str:
    secondary = _button_secondary_text(key_label, diagnostic_badge)
    return label if not secondary else f"{label}\n{secondary}"


def _button_secondary_text(key_label: str, diagnostic_badge: str = "") -> str:
    if key_label and diagnostic_badge:
        return f"{key_label}{diagnostic_badge}"
    return key_label or diagnostic_badge


def _slot_render_state(
    item: StackItem,
    registry: ActionRegistry,
    context: PredicateContext | None = None,
    *,
    key_label: str | None = None,
) -> SlotRenderState:
    item_context = _item_context(item, registry, context)
    diagnostic = _slot_diagnostic(item, registry, item_context)
    return SlotRenderState(
        label=item.label,
        key_label=item.key_label if key_label is None else key_label,
        icon=item.icon,
        icon_path=str(resolve_icon_path(item.icon) or "") if item.icon else "",
        tone=item.tone,
        tooltip=_diagnostic_tooltip(_item_tooltip(item, registry), diagnostic),
        enabled=evaluate_predicate(item.enabled_when, item_context)
        and not _diagnostic_blocks_enabled(diagnostic),
        active=_is_item_active(item, item_context),
        diagnostic_code=diagnostic[0],
        diagnostic_severity=diagnostic[1],
        diagnostic_badge=diagnostic[2],
    )


def _item_tooltip(item: StackItem, registry: ActionRegistry | None = None) -> str:
    if item.tooltip:
        return item.tooltip

    get_action = getattr(registry, "get", None)
    if get_action is None:
        return ""

    try:
        action = get_action(item.action)
    except Exception:
        return ""

    tooltip = getattr(action, "tooltip", "")
    return tooltip if isinstance(tooltip, str) else ""


def _slot_diagnostic(
    item: StackItem,
    registry: ActionRegistry | None = None,
    context: PredicateContext | None = None,
) -> tuple[str, str, str, str]:
    get_action = getattr(registry, "get", None)
    if item.action and get_action is not None:
        try:
            get_action(item.action)
        except Exception:
            return (
                "missing_action",
                "error",
                "!",
                f"Missing ActionRail action: {item.action}",
            )

    availability_diagnostic = _availability_diagnostic(item, context)
    if availability_diagnostic[0]:
        return availability_diagnostic

    if item.icon and resolve_icon_path(item.icon) is None:
        return (
            "missing_icon",
            "warning",
            "?",
            f"Missing ActionRail icon: {item.icon}",
        )

    return ("", "", "", "")


def _availability_diagnostic(
    item: StackItem,
    context: PredicateContext | None,
) -> tuple[str, str, str, str]:
    if context is None:
        return ("", "", "", "")

    for field_name in ("enabled_when", "visible_when", "active_when"):
        predicate = getattr(item, field_name)
        if not predicate.strip():
            continue
        for kind, target in availability_blocking_targets(predicate, context):
            if kind == "command":
                return (
                    "missing_command",
                    "warning",
                    "?",
                    f"Unavailable Maya command in {field_name}: {target}",
                )
            if kind == "plugin":
                return (
                    "missing_plugin",
                    "warning",
                    "?",
                    f"Unavailable Maya plugin in {field_name}: {target}",
                )

    return ("", "", "", "")


def _diagnostic_blocks_enabled(diagnostic: tuple[str, str, str, str]) -> bool:
    return diagnostic[1] == "error" or diagnostic[0] in {"missing_command", "missing_plugin"}


def _diagnostic_tooltip(base_tooltip: str, diagnostic: tuple[str, str, str, str]) -> str:
    message = diagnostic[3]
    if not message:
        return base_tooltip
    if not base_tooltip:
        return message
    return f"{base_tooltip}\n{message}"


def _apply_slot_render_state(button: object, state: SlotRenderState) -> int:
    refreshed = 0
    style_needs_refresh = False

    refreshed += _set_button_property(button, "actionRailLabel", state.label)
    refreshed += _set_button_property(button, "actionRailKeyLabel", state.key_label)
    refreshed += _set_button_property(button, "actionRailIcon", state.icon)
    refreshed += _set_button_property(button, "actionRailIconPath", state.icon_path)
    tone_changed = _set_button_property(button, "actionRailTone", state.tone)
    active_changed = _set_button_property(
        button,
        "actionRailActive",
        state.active_property,
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
    refreshed += tone_changed + active_changed
    refreshed += diagnostic_code_changed + diagnostic_severity_changed
    style_needs_refresh = bool(
        tone_changed
        or active_changed
        or diagnostic_code_changed
        or diagnostic_severity_changed
    )
    refreshed += _apply_button_icon(button, state.icon_path)

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


def _apply_button_icon(button: object, icon_path: str) -> int:
    set_icon = getattr(button, "setIcon", None)
    if not callable(set_icon):
        return 0

    try:
        current = button.property("actionRailAppliedIconPath")
    except Exception:
        current = None

    if current == icon_path:
        return 0

    try:
        qt = load()
        set_icon(qt.QtGui.QIcon(icon_path) if icon_path else qt.QtGui.QIcon())
        set_icon_size = getattr(button, "setIconSize", None)
        if callable(set_icon_size) and icon_path:
            set_icon_size(qt.QtCore.QSize(18, 18))
        button.setProperty("actionRailAppliedIconPath", icon_path)
    except Exception:
        return 0
    return 1


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


def _is_item_visible(item: StackItem, context: PredicateContext | None = None) -> bool:
    item_context = _item_context(item, context=context)
    if evaluate_predicate(item.visible_when, item_context):
        return True
    return bool(availability_blocking_targets(item.visible_when, item_context))


def _is_item_active(item: StackItem, context: PredicateContext | None = None) -> bool:
    return bool(item.active_when.strip()) and evaluate_predicate(
        item.active_when,
        _item_context(item, context=context),
    )


def _item_context(
    item: StackItem,
    registry: ActionRegistry | None = None,
    context: PredicateContext | None = None,
) -> PredicateContext:
    context = context or PredicateContext()
    return PredicateContext(
        state=context.state,
        registry=registry or context.registry,
        item=item,
        cmds_module=context.cmds_module,
    )


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


def _visible_action_items(
    spec: StackSpec,
    context: PredicateContext | None = None,
) -> tuple[StackItem, ...]:
    return tuple(
        item
        for item in spec.items
        if item.type in {"button", "toolButton"} and _is_item_visible(item, context)
    )


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
