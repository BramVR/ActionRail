"""Qt widgets for ActionRail stack specs."""

from __future__ import annotations

from dataclasses import replace

from .actions import ActionRegistry
from .predicates import PredicateContext, evaluate_predicate
from .qt import load
from .spec import StackItem, StackSpec
from .state import MayaStateSnapshot
from .theme import DEFAULT_THEME, ActionRailTheme, generate_style_sheet

BUTTON_SIZE = DEFAULT_THEME.button_size
FRAME_PADDING = DEFAULT_THEME.frame_padding
FRAME_SPACING = DEFAULT_THEME.frame_spacing
RAIL_WIDTH = DEFAULT_THEME.rail_width
STYLE_SHEET = generate_style_sheet(DEFAULT_THEME)


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
    if orientation == "vertical":
        frame.setFixedWidth(theme.rail_width)

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

    frame.adjustSize()
    frame.setFixedSize(frame.sizeHint())
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
    if orientation == "vertical":
        frame.setFixedWidth(theme.rail_width)

    layout = qt.QtWidgets.QVBoxLayout(frame)
    layout.setContentsMargins(
        theme.frame_padding,
        theme.frame_padding,
        theme.frame_padding,
        theme.frame_padding,
    )
    layout.setSpacing(0)
    layout.addWidget(_build_button(item, registry, theme, context))

    frame.adjustSize()
    frame.setFixedSize(frame.sizeHint())
    return frame


def _build_button(
    item: StackItem,
    registry: ActionRegistry,
    theme: ActionRailTheme,
    context: PredicateContext | None = None,
) -> object:
    qt = load()
    item_context = _item_context(item, registry, context)
    button = qt.QtWidgets.QPushButton(_button_text(item.label, item.key_label))
    button.setProperty("actionRailRole", "button")
    button.setProperty("actionRailLabel", item.label)
    button.setProperty("actionRailKeyLabel", item.key_label)
    button.setProperty("actionRailSlotId", item.id)
    button.setProperty("actionRailTone", item.tone)
    is_active = _is_item_active(item, item_context)
    button.setProperty(
        "actionRailActive",
        "true" if is_active else "false",
    )
    button.setFixedSize(theme.button_size, theme.button_size)
    button.setFocusPolicy(qt.QtCore.Qt.NoFocus)
    button.setCursor(qt.QtCore.Qt.PointingHandCursor)
    if item.tooltip:
        button.setToolTip(item.tooltip)
    button.setEnabled(evaluate_predicate(item.enabled_when, item_context))
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
        button.setProperty("actionRailKeyLabel", key_label)
        button.setText(_button_text(label, key_label))
        updated += 1

    return updated


def _button_text(label: str, key_label: str) -> str:
    return label if not key_label else f"{label}\n{key_label}"


def _is_item_visible(item: StackItem, context: PredicateContext | None = None) -> bool:
    return evaluate_predicate(item.visible_when, _item_context(item, context=context))


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
        button_border_radius=scaled(theme.button_border_radius, minimum=0),
        button_font_size=scaled(theme.button_font_size),
    )
