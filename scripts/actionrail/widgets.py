"""Qt widgets for ActionRail stack specs."""

from __future__ import annotations

from .actions import ActionRegistry
from .qt import load
from .spec import StackItem, StackSpec

BUTTON_SIZE = 32
FRAME_PADDING = 4
FRAME_SPACING = 2
RAIL_WIDTH = BUTTON_SIZE + (FRAME_PADDING * 2)

STYLE_SHEET = """
QWidget#ActionRailRoot {
    background: transparent;
}
QFrame[actionRailRole="cluster"] {
    background: #4a4a4f;
    border: 2px solid #323238;
    border-radius: 2px;
}
QPushButton[actionRailRole="button"] {
    min-width: 32px;
    max-width: 32px;
    min-height: 32px;
    max-height: 32px;
    border: 1px solid #696972;
    border-radius: 1px;
    background: #666670;
    color: #d9d9de;
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0px;
    padding: 0px;
}
QPushButton[actionRailRole="button"]:hover {
    background: #74747e;
    border-color: #888894;
}
QPushButton[actionRailRole="button"]:pressed {
    background: #555560;
}
QPushButton[actionRailTone="pink"] {
    background: #8b667f;
    border-color: #a9839e;
}
QPushButton[actionRailTone="pink"]:hover {
    background: #9c7390;
}
QPushButton[actionRailTone="teal"] {
    background: #22a79b;
    border-color: #45c6bb;
    color: #e9fffb;
}
QPushButton[actionRailTone="teal"]:hover {
    background: #29b9ad;
}
"""


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


def build_transform_stack(spec: StackSpec, registry: ActionRegistry) -> object:
    """Build a vertical ActionRail widget from a stack spec."""

    qt = load()
    root = ActionRailRoot.create()
    root.setStyleSheet(STYLE_SHEET)

    layout = qt.QtWidgets.QVBoxLayout(root)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)

    pending_tools: list[StackItem] = []
    for item in spec.items:
        if item.type == "toolButton":
            pending_tools.append(item)
            continue

        if pending_tools:
            layout.addWidget(_build_cluster(tuple(pending_tools), registry))
            pending_tools.clear()

        if item.type == "spacer":
            layout.addSpacing(item.size)
            continue

        layout.addWidget(_build_single_button(item, registry), 0, qt.QtCore.Qt.AlignLeft)

    if pending_tools:
        layout.addWidget(_build_cluster(tuple(pending_tools), registry))

    root.adjustSize()
    root.setFixedSize(root.sizeHint())
    return root


def _build_cluster(items: tuple[StackItem, ...], registry: ActionRegistry) -> object:
    qt = load()
    frame = qt.QtWidgets.QFrame()
    frame.setProperty("actionRailRole", "cluster")
    frame.setFixedWidth(RAIL_WIDTH)

    layout = qt.QtWidgets.QVBoxLayout(frame)
    layout.setContentsMargins(FRAME_PADDING, FRAME_PADDING, FRAME_PADDING, FRAME_PADDING)
    layout.setSpacing(FRAME_SPACING)

    for item in items:
        layout.addWidget(_build_button(item, registry))

    frame.adjustSize()
    frame.setFixedSize(frame.sizeHint())
    return frame


def _build_single_button(item: StackItem, registry: ActionRegistry) -> object:
    qt = load()
    frame = qt.QtWidgets.QFrame()
    frame.setProperty("actionRailRole", "cluster")
    frame.setFixedWidth(RAIL_WIDTH)

    layout = qt.QtWidgets.QVBoxLayout(frame)
    layout.setContentsMargins(FRAME_PADDING, FRAME_PADDING, FRAME_PADDING, FRAME_PADDING)
    layout.setSpacing(0)
    layout.addWidget(_build_button(item, registry))

    frame.adjustSize()
    frame.setFixedSize(frame.sizeHint())
    return frame


def _build_button(item: StackItem, registry: ActionRegistry) -> object:
    qt = load()
    button = qt.QtWidgets.QPushButton(item.label)
    button.setProperty("actionRailRole", "button")
    button.setProperty("actionRailTone", item.tone)
    button.setFixedSize(BUTTON_SIZE, BUTTON_SIZE)
    button.setFocusPolicy(qt.QtCore.Qt.NoFocus)
    button.setCursor(qt.QtCore.Qt.PointingHandCursor)
    if item.tooltip:
        button.setToolTip(item.tooltip)
    button.clicked.connect(lambda _checked=False, action_id=item.action: registry.run(action_id))
    return button
