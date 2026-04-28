"""Qt widgets for ActionRail stack specs."""

from __future__ import annotations

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
    """Build a vertical ActionRail widget from a stack spec."""

    qt = load()
    root = ActionRailRoot.create()
    root.setStyleSheet(generate_style_sheet(theme))

    layout = qt.QtWidgets.QVBoxLayout(root)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)

    pending_tools: list[StackItem] = []
    for item in spec.items:
        if item.type == "toolButton":
            pending_tools.append(item)
            continue

        if pending_tools:
            layout.addWidget(_build_cluster(tuple(pending_tools), registry, theme))
            pending_tools.clear()

        if item.type == "spacer":
            layout.addSpacing(item.size)
            continue

        layout.addWidget(_build_single_button(item, registry, theme), 0, qt.QtCore.Qt.AlignLeft)

    if pending_tools:
        layout.addWidget(_build_cluster(tuple(pending_tools), registry, theme))

    root.adjustSize()
    root.setFixedSize(root.sizeHint())
    return root


def _build_cluster(
    items: tuple[StackItem, ...],
    registry: ActionRegistry,
    theme: ActionRailTheme,
) -> object:
    qt = load()
    frame = qt.QtWidgets.QFrame()
    frame.setProperty("actionRailRole", "cluster")
    frame.setFixedWidth(theme.rail_width)

    layout = qt.QtWidgets.QVBoxLayout(frame)
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
) -> object:
    qt = load()
    frame = qt.QtWidgets.QFrame()
    frame.setProperty("actionRailRole", "cluster")
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
    button = qt.QtWidgets.QPushButton(item.label)
    button.setProperty("actionRailRole", "button")
    button.setProperty("actionRailTone", item.tone)
    button.setFixedSize(theme.button_size, theme.button_size)
    button.setFocusPolicy(qt.QtCore.Qt.NoFocus)
    button.setCursor(qt.QtCore.Qt.PointingHandCursor)
    if item.tooltip:
        button.setToolTip(item.tooltip)
    button.clicked.connect(lambda _checked=False, action_id=item.action: registry.run(action_id))
    return button
