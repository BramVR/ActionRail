"""Searchable Action Book UI for ActionRail placeable actions."""

from __future__ import annotations

from collections import defaultdict
from contextlib import suppress
from typing import Any

from .action_book import (
    ACTION_BOOK_MIME_TYPE,
    ActionBookEntry,
    action_book_mime_text,
    action_book_search,
)
from .actions import ActionRegistry, create_default_registry
from .icon_catalog import icon_status
from .overlay import maya_main_window
from .qt import QtBinding, load
from .theme import DEFAULT_THEME

ActionBookGroup = tuple[str, tuple[ActionBookEntry, ...]]

PANEL_OBJECT_NAME = "ActionRailActionBookPanel"
SEARCH_OBJECT_NAME = "ActionRailActionBookSearch"
STATUS_OBJECT_NAME = "ActionRailActionBookStatus"
FILTER_TABS_OBJECT_NAME = "ActionRailActionBookFilterTabs"
ENTRY_BUTTON_OBJECT_NAME_PREFIX = "ActionRailActionBookEntry"

_PANEL: Any | None = None

__all__ = [
    "ENTRY_BUTTON_OBJECT_NAME_PREFIX",
    "FILTER_TABS_OBJECT_NAME",
    "PANEL_OBJECT_NAME",
    "SEARCH_OBJECT_NAME",
    "STATUS_OBJECT_NAME",
    "show_action_book_panel",
]


def show_action_book_panel(  # pragma: no cover - Maya-hosted Qt panel.
    *,
    qt_binding: QtBinding | None = None,
    parent: Any | None = None,
    registry: ActionRegistry | None = None,
) -> Any:
    """Show the searchable Action Book panel and return it."""

    global _PANEL

    qt = qt_binding or load()
    app = qt.QtWidgets.QApplication.instance()
    if app is None:
        msg = "ActionRail Action Book requires a QApplication inside Maya."
        raise RuntimeError(msg)

    if _PANEL is not None:
        _close_existing_panel(qt)

    panel_parent = parent if parent is not None else maya_main_window(qt)
    panel = qt.QtWidgets.QWidget(panel_parent)
    panel.setObjectName(PANEL_OBJECT_NAME)
    panel.setWindowTitle("ActionRail Action Book")
    panel.setMinimumSize(620, 520)
    panel.resize(680, 620)
    panel.setAttribute(qt.QtCore.Qt.WA_DeleteOnClose, True)
    if panel_parent is None:
        panel.setWindowFlags(qt.QtCore.Qt.Tool)
    else:
        _sync_to_parent_size(panel, panel_parent)
        _install_parent_resize_filter(qt, panel, panel_parent)

    _build_panel(panel, qt, registry=registry or create_default_registry())
    panel.destroyed.connect(_forget_panel)
    _PANEL = panel
    panel.show()
    panel.raise_()
    panel.activateWindow()
    return panel


def _install_parent_resize_filter(qt: QtBinding, panel: Any, panel_parent: Any) -> None:
    class ParentResizeFilter(qt.QtCore.QObject):  # type: ignore[misc, valid-type]
        def eventFilter(self, watched: Any, event: Any) -> bool:  # noqa: N802
            if event.type() in (
                qt.QtCore.QEvent.Resize,
                qt.QtCore.QEvent.Show,
                qt.QtCore.QEvent.LayoutRequest,
            ):
                _sync_to_parent_size(panel, watched)
            return False

    resize_filter = ParentResizeFilter(panel)
    panel_parent.installEventFilter(resize_filter)
    panel._actionrail_parent_resize_filter = resize_filter


def _sync_to_parent_size(panel: Any, panel_parent: Any) -> None:
    panel.setGeometry(panel_parent.rect())


def _build_panel(panel: Any, qt: QtBinding, *, registry: ActionRegistry) -> None:
    panel.setStyleSheet(_style_sheet())
    panel._actionrail_registry = registry

    root = qt.QtWidgets.QVBoxLayout(panel)
    root.setContentsMargins(12, 8, 12, 10)
    root.setSpacing(6)

    header = qt.QtWidgets.QWidget()
    header_layout = qt.QtWidgets.QHBoxLayout(header)
    header_layout.setContentsMargins(0, 0, 0, 0)
    header_layout.setSpacing(10)
    title = qt.QtWidgets.QLabel("Action Book")
    title.setObjectName("ActionRailActionBookTitle")
    header_layout.addWidget(title)
    header_layout.addStretch(1)

    search = qt.QtWidgets.QLineEdit()
    search.setObjectName(SEARCH_OBJECT_NAME)
    search.setPlaceholderText("Search Maya actions")
    search.setMinimumWidth(260)
    header_layout.addWidget(search)
    root.addWidget(header)

    filter_tabs = qt.QtWidgets.QTabBar()
    filter_tabs.setObjectName(FILTER_TABS_OBJECT_NAME)
    filter_tabs.setDrawBase(False)
    filter_tabs.setExpanding(False)
    filter_tabs.addTab("All")
    for category in _catalog_categories(registry):
        filter_tabs.addTab(category)
    root.addWidget(filter_tabs)

    scroll = qt.QtWidgets.QScrollArea()
    scroll.setObjectName("ActionRailActionBookScroll")
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(qt.QtWidgets.QFrame.NoFrame)
    root.addWidget(scroll, 1)

    content = qt.QtWidgets.QWidget()
    content.setObjectName("ActionRailActionBookPages")
    content_layout = qt.QtWidgets.QHBoxLayout(content)
    content_layout.setContentsMargins(8, 8, 8, 8)
    content_layout.setSpacing(8)
    scroll.setWidget(content)

    status = qt.QtWidgets.QLabel("")
    status.setObjectName(STATUS_OBJECT_NAME)
    root.addWidget(status)

    def refresh_entries() -> tuple[ActionBookEntry, ...]:
        query = search.text().strip()
        entries = _filter_entries(
            action_book_search(query, registry=registry),
            _current_filter(filter_tabs),
        )
        _populate_entries(qt, content_layout, entries, registry)
        status.setText(f"{len(entries)} action(s)" + (f" for '{query}'" if query else ""))
        panel._actionrail_entry_count = len(entries)
        panel._actionrail_entry_buttons = _entry_buttons(panel, qt)
        return entries

    panel._actionrail_refresh_entries = refresh_entries
    search.textChanged.connect(lambda _text: refresh_entries())
    filter_tabs.currentChanged.connect(lambda _index: refresh_entries())
    refresh_entries()


def _catalog_categories(registry: ActionRegistry) -> tuple[str, ...]:
    entries = action_book_search("", registry=registry)
    return tuple(sorted({entry.category for entry in entries}))


def _current_filter(filter_tabs: Any) -> str:
    current_index = filter_tabs.currentIndex()
    if current_index < 0:
        return "All"
    return str(filter_tabs.tabText(current_index))


def _filter_entries(
    entries: tuple[ActionBookEntry, ...],
    category: str,
) -> tuple[ActionBookEntry, ...]:
    if category == "All":
        return entries
    return tuple(entry for entry in entries if entry.category == category)


def _populate_entries(
    qt: QtBinding,
    content_layout: Any,
    entries: tuple[ActionBookEntry, ...],
    registry: ActionRegistry,
) -> None:
    _clear_layout(content_layout)
    if not entries:
        empty = qt.QtWidgets.QLabel("No matching actions")
        empty.setObjectName("ActionRailActionBookEmpty")
        empty.setAlignment(qt.QtCore.Qt.AlignCenter)
        content_layout.addWidget(empty, 1)
        return

    pages = _balanced_pages(_grouped_entries(entries))
    for page_index, page_groups in enumerate(pages):
        page = qt.QtWidgets.QWidget()
        page.setObjectName("ActionRailActionBookPage")
        page_layout = qt.QtWidgets.QVBoxLayout(page)
        page_layout.setContentsMargins(12, 10, 12, 12)
        page_layout.setSpacing(8)
        for category, category_entries in page_groups:
            header = qt.QtWidgets.QLabel(category)
            header.setObjectName("ActionRailActionBookCategory")
            page_layout.addWidget(header)
            grid_holder = qt.QtWidgets.QWidget()
            grid = qt.QtWidgets.QGridLayout(grid_holder)
            grid.setContentsMargins(0, 0, 0, 0)
            grid.setHorizontalSpacing(8)
            grid.setVerticalSpacing(4)
            for index, entry in enumerate(category_entries):
                grid.addWidget(_entry_button(qt, entry, registry), index, 0)
            grid.setColumnStretch(0, 1)
            page_layout.addWidget(grid_holder)
        page_layout.addStretch(1)
        content_layout.addWidget(page, 1)
        if page_index == 0:
            divider = qt.QtWidgets.QFrame()
            divider.setObjectName("ActionRailActionBookDivider")
            divider.setFrameShape(qt.QtWidgets.QFrame.VLine)
            content_layout.addWidget(divider)


def _grouped_entries(
    entries: tuple[ActionBookEntry, ...],
) -> tuple[ActionBookGroup, ...]:
    grouped: dict[str, list[ActionBookEntry]] = defaultdict(list)
    for entry in entries:
        grouped[entry.category].append(entry)
    return tuple((category, tuple(grouped[category])) for category in sorted(grouped))


def _balanced_pages(
    grouped: tuple[ActionBookGroup, ...],
) -> tuple[list[ActionBookGroup], list[ActionBookGroup]]:
    pages: tuple[list[ActionBookGroup], list[ActionBookGroup]] = ([], [])
    counts = [0, 0]
    for group in grouped:
        target = 0 if counts[0] <= counts[1] else 1
        pages[target].append(group)
        counts[target] += len(group[1])
    return pages


def _entry_button(qt: QtBinding, entry: ActionBookEntry, registry: ActionRegistry) -> Any:
    button = _spell_button_class(qt)(entry, registry)
    button.setObjectName(f"{ENTRY_BUTTON_OBJECT_NAME_PREFIX}_{_safe_object_suffix(entry.id)}")
    button.setProperty("actionRailActionBookActionId", entry.id)
    button.setProperty("actionRailIcon", entry.icon)
    button.setProperty("actionRailIconBackplate", DEFAULT_THEME.spell_icon_background)
    button.setText(_entry_button_text(entry))
    button.setToolTip(f"{entry.label}\n{entry.tooltip or entry.id}")
    button.setToolButtonStyle(qt.QtCore.Qt.ToolButtonTextBesideIcon)
    button.setIconSize(qt.QtCore.QSize(30, 30))
    button.setMinimumSize(220, 44)
    button.setMaximumHeight(50)
    button.setSizePolicy(
        qt.QtWidgets.QSizePolicy.Expanding,
        qt.QtWidgets.QSizePolicy.Fixed,
    )
    button.setCursor(qt.QtCore.Qt.PointingHandCursor)
    button.setFocusPolicy(qt.QtCore.Qt.NoFocus)
    _apply_entry_icon(qt, button, entry.icon)
    return button


def _spell_button_class(qt: QtBinding) -> type:
    class ActionBookButton(qt.QtWidgets.QToolButton):  # type: ignore[misc, valid-type]
        def __init__(self, entry: ActionBookEntry, registry: ActionRegistry) -> None:
            super().__init__()
            self._actionrail_entry = entry
            self._actionrail_registry = registry
            self._actionrail_drag_start = None
            self.clicked.connect(lambda _checked=False: registry.run(entry.id))

        def mousePressEvent(self, event):  # type: ignore[no-untyped-def]  # noqa: N802
            self._actionrail_drag_start = event.pos()
            return super().mousePressEvent(event)

        def mouseMoveEvent(self, event):  # type: ignore[no-untyped-def]  # noqa: N802
            if self._actionrail_drag_start is None:
                return super().mouseMoveEvent(event)
            if not _left_button_pressed(qt, event):
                return super().mouseMoveEvent(event)
            if not _drag_threshold_exceeded(qt, self._actionrail_drag_start, event.pos()):
                return super().mouseMoveEvent(event)
            self._actionrail_drag_start = None
            _start_entry_drag(qt, self, self._actionrail_entry)
            return None

    return ActionBookButton


def _left_button_pressed(qt: QtBinding, event: Any) -> bool:
    buttons = getattr(event, "buttons", None)
    if not callable(buttons):
        return False
    with suppress(Exception):
        return bool(buttons() & qt.QtCore.Qt.LeftButton)
    return False


def _drag_threshold_exceeded(qt: QtBinding, start: Any, current: Any) -> bool:
    try:
        delta = current - start
        return delta.manhattanLength() >= qt.QtWidgets.QApplication.startDragDistance()
    except Exception:
        return True


def _start_entry_drag(qt: QtBinding, source: Any, entry: ActionBookEntry) -> None:
    drag = qt.QtGui.QDrag(source)
    mime = qt.QtCore.QMimeData()
    payload = action_book_mime_text(entry.id)
    mime.setData(ACTION_BOOK_MIME_TYPE, payload.encode("utf-8"))
    mime.setText(payload)
    drag.setMimeData(mime)
    icon = source.icon()
    if not icon.isNull():
        pixmap = icon.pixmap(qt.QtCore.QSize(32, 32))
        if not pixmap.isNull():
            drag.setPixmap(pixmap)
    drag.exec(qt.QtCore.Qt.CopyAction)


def _entry_button_text(entry: ActionBookEntry) -> str:
    description = entry.tooltip or entry.id
    return f"{entry.label}\n{description}"


def _apply_entry_icon(qt: QtBinding, button: Any, icon_id: str) -> None:
    status = icon_status(icon_id)
    icon_source = _qt_icon_source(str(status.path or ""), status.qt_name)
    if icon_source:
        button.setIcon(_entry_icon_with_backplate(qt, icon_source))


def _entry_icon_with_backplate(qt: QtBinding, icon_source: str, size: int = 30) -> Any:
    pixmap_class = getattr(qt.QtGui, "QPixmap", None)
    painter_class = getattr(qt.QtGui, "QPainter", None)
    icon_class = getattr(qt.QtGui, "QIcon", None)
    color_class = getattr(qt.QtGui, "QColor", None)
    if (
        pixmap_class is None
        or painter_class is None
        or icon_class is None
        or color_class is None
    ):
        return qt.QtGui.QIcon(icon_source)

    try:
        canvas = pixmap_class(qt.QtCore.QSize(size, size))
        canvas.fill(color_class("#00000000"))
        painter = painter_class(canvas)
        try:
            rect = canvas.rect()
            painter.fillRect(rect, color_class(DEFAULT_THEME.spell_icon_background))
            painter.setPen(color_class(DEFAULT_THEME.spell_icon_border))
            painter.drawRect(rect.adjusted(0, 0, -1, -1))
            inset = DEFAULT_THEME.spell_icon_inset
            icon_rect = rect.adjusted(inset, inset, -inset, -inset)
            pixmap = icon_class(icon_source).pixmap(icon_rect.size())
            if not pixmap.isNull():
                painter.drawPixmap(icon_rect, pixmap)
        finally:
            painter.end()
        return icon_class(canvas)
    except Exception:
        return qt.QtGui.QIcon(icon_source)


def _qt_icon_source(icon_path: str, icon_name: str = "") -> str:
    if icon_path:
        return icon_path
    if not icon_name or icon_name.startswith(":"):
        return icon_name
    return f":/{icon_name}"


def _entry_buttons(panel: Any, qt: QtBinding) -> tuple[Any, ...]:
    return tuple(
        button
        for button in panel.findChildren(qt.QtWidgets.QToolButton)
        if str(button.objectName()).startswith(ENTRY_BUTTON_OBJECT_NAME_PREFIX)
    )


def _safe_object_suffix(action_id: str) -> str:
    return "".join(char if char.isalnum() else "_" for char in action_id).strip("_")


def _clear_layout(layout: Any) -> None:
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        child_layout = item.layout()
        if child_layout is not None:
            _clear_layout(child_layout)
        if widget is not None:
            widget.setParent(None)
            widget.deleteLater()


def _close_existing_panel(qt: QtBinding) -> None:
    global _PANEL
    if _PANEL is None:
        return
    with suppress(Exception):
        _PANEL.close()
        _PANEL.deleteLater()
        app = qt.QtWidgets.QApplication.instance()
        if app is not None:
            app.sendPostedEvents(None, qt.QtCore.QEvent.DeferredDelete)
    _PANEL = None


def _forget_panel(*_args: object) -> None:
    global _PANEL
    _PANEL = None


def _style_sheet() -> str:
    theme = DEFAULT_THEME
    return f"""
QWidget#{PANEL_OBJECT_NAME} {{
    background: {theme.panel_background};
    color: {theme.button_color};
}}
QLabel#ActionRailActionBookTitle {{
    color: {theme.button_color};
    font-size: 18px;
    font-weight: 700;
    letter-spacing: 0px;
}}
QLineEdit#{SEARCH_OBJECT_NAME} {{
    min-height: 26px;
    border: {theme.button_border_width}px solid {theme.button_border};
    border-radius: {theme.button_border_radius}px;
    background: {theme.button_background};
    color: {theme.button_color};
    padding: 4px 8px;
    font-size: 12px;
    letter-spacing: 0px;
}}
QTabBar#{FILTER_TABS_OBJECT_NAME} {{
    background: transparent;
}}
QTabBar#{FILTER_TABS_OBJECT_NAME}::tab {{
    min-height: 22px;
    padding: 3px 12px;
    margin-right: 4px;
    border: {theme.button_border_width}px solid {theme.button_border};
    border-bottom: none;
    border-top-left-radius: {theme.button_border_radius}px;
    border-top-right-radius: {theme.button_border_radius}px;
    background: {theme.panel_inset_background};
    color: {theme.text_muted};
    font-size: 11px;
    letter-spacing: 0px;
}}
QTabBar#{FILTER_TABS_OBJECT_NAME}::tab:selected {{
    background: {theme.button_active_background};
    color: {theme.button_color};
    border-color: {theme.button_active_border};
}}
QScrollArea#ActionRailActionBookScroll {{
    background: {theme.panel_inset_background};
    border: {theme.cluster_border_width}px solid {theme.cluster_border};
    border-top-color: {theme.accent_line};
    border-radius: {theme.cluster_border_radius}px;
}}
QWidget#ActionRailActionBookPages {{
    background: {theme.panel_inset_background};
}}
QWidget#ActionRailActionBookPage {{
    background: {theme.panel_profile_background};
    border: {theme.cluster_border_width}px solid {theme.cluster_border};
    border-top-color: {theme.accent_line};
    border-radius: {theme.cluster_border_radius}px;
}}
QFrame#ActionRailActionBookDivider {{
    color: {theme.button_border};
}}
QLabel#ActionRailActionBookCategory {{
    color: {theme.button_color};
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0px;
}}
QLabel#ActionRailActionBookEmpty {{
    color: {theme.text_muted};
    font-size: 12px;
    letter-spacing: 0px;
}}
QLabel#{STATUS_OBJECT_NAME} {{
    color: {theme.success};
    font-size: 12px;
    letter-spacing: 0px;
}}
QToolButton {{
    border: 1px solid transparent;
    border-radius: {theme.button_border_radius}px;
    background: transparent;
    color: {theme.button_color};
    padding: 4px 6px;
    font-size: 11px;
    letter-spacing: 0px;
    text-align: left;
}}
QToolButton:hover {{
    background: {theme.button_hover_background};
    border-color: {theme.button_hover_border};
}}
"""
