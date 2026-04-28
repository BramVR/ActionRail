"""Qt widgets for ActionRail stack specs."""

from __future__ import annotations

from dataclasses import replace

from .actions import ActionRegistry
from .qt import load
from .spec import StackItem, StackSpec
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
) -> object:
    """Build an ActionRail widget from a stack spec."""

    qt = load()
    theme = _scaled_theme(theme, spec.layout.scale)
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
        if not _is_item_visible(item):
            continue

        if item.type == "toolButton":
            pending_tools.append(item)
            continue

        if pending_tools:
            layout.addWidget(
                _build_cluster(tuple(pending_tools), registry, theme, spec.layout.orientation)
            )
            pending_tools.clear()

        if item.type == "spacer":
            layout.addSpacing(item.size)
            continue

        layout.addWidget(
            _build_single_button(item, registry, theme, spec.layout.orientation),
            0,
            qt.QtCore.Qt.AlignLeft,
        )

    if pending_tools:
        layout.addWidget(
            _build_cluster(tuple(pending_tools), registry, theme, spec.layout.orientation)
        )

    root.adjustSize()
    root.setFixedSize(root.sizeHint())
    return root


def _build_cluster(
    items: tuple[StackItem, ...],
    registry: ActionRegistry,
    theme: ActionRailTheme,
    orientation: str,
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
        layout.addWidget(_build_button(item, registry, theme))

    frame.adjustSize()
    frame.setFixedSize(frame.sizeHint())
    return frame


def _build_single_button(
    item: StackItem,
    registry: ActionRegistry,
    theme: ActionRailTheme,
    orientation: str,
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
    layout.addWidget(_build_button(item, registry, theme))

    frame.adjustSize()
    frame.setFixedSize(frame.sizeHint())
    return frame


def _build_button(item: StackItem, registry: ActionRegistry, theme: ActionRailTheme) -> object:
    qt = load()
    button_text = item.label if not item.key_label else f"{item.label}\n{item.key_label}"
    button = qt.QtWidgets.QPushButton(button_text)
    button.setProperty("actionRailRole", "button")
    button.setProperty("actionRailSlotId", item.id)
    button.setProperty("actionRailTone", item.tone)
    button.setFixedSize(theme.button_size, theme.button_size)
    button.setFocusPolicy(qt.QtCore.Qt.NoFocus)
    button.setCursor(qt.QtCore.Qt.PointingHandCursor)
    if item.tooltip:
        button.setToolTip(item.tooltip)
    button.setEnabled(item.enabled_when != "false")
    button.clicked.connect(lambda _checked=False, action_id=item.action: registry.run(action_id))
    return button


def _is_item_visible(item: StackItem) -> bool:
    return item.visible_when != "false"


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
