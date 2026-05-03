from __future__ import annotations

import pytest

import actionrail.diagnostics_ui as diagnostics_ui
from actionrail.diagnostics import DiagnosticIssue, DiagnosticOverlayState, DiagnosticReport
from actionrail.diagnostics_ui import (
    _filter_empty_label,
    _filtered_issues,
    _issue_detail,
    _issue_filter_value,
    _issue_title,
    _summary_text,
)
from actionrail.qt import QtBinding


class FakeSignal:
    def __init__(self) -> None:
        self.callbacks = []

    def connect(self, callback) -> None:
        self.callbacks.append(callback)

    def emit(self) -> None:
        for callback in list(self.callbacks):
            callback()


class FakeClipboard:
    def __init__(self) -> None:
        self.text = ""

    def setText(self, text: str) -> None:  # noqa: N802
        self.text = text


class FakeApp:
    def __init__(self) -> None:
        self.sent_events = []

    def sendPostedEvents(self, *args) -> None:  # noqa: N802
        self.sent_events.append(args)


class FakeDialog:
    def __init__(self, parent=None) -> None:
        self.parent = parent
        self.destroyed = FakeSignal()
        self.closed = False
        self.deleted = False
        self.shown = False
        self.raised = False
        self.activated = False

    def setObjectName(self, name: str) -> None:  # noqa: N802
        self.object_name = name

    def setWindowTitle(self, title: str) -> None:  # noqa: N802
        self.title = title

    def setMinimumSize(self, width: int, height: int) -> None:  # noqa: N802
        self.minimum_size = (width, height)

    def resize(self, width: int, height: int) -> None:
        self.size = (width, height)

    def setModal(self, modal: bool) -> None:  # noqa: N802
        self.modal = modal

    def setAttribute(self, attribute, value: bool) -> None:  # noqa: N802
        self.attribute = (attribute, value)

    def setStyleSheet(self, style: str) -> None:  # noqa: N802
        self.style = style

    def show(self) -> None:
        self.shown = True

    def raise_(self) -> None:
        self.raised = True

    def activateWindow(self) -> None:  # noqa: N802
        self.activated = True

    def close(self) -> None:
        self.closed = True

    def deleteLater(self) -> None:  # noqa: N802
        self.deleted = True


class FakeLayout:
    def __init__(self, parent=None) -> None:
        self.parent = parent
        self.children = []

    def setContentsMargins(self, *margins) -> None:  # noqa: N802
        self.margins = margins

    def setSpacing(self, spacing: int) -> None:  # noqa: N802
        self.spacing = spacing

    def addWidget(self, widget, *args) -> None:  # noqa: N802
        self.children.append(("widget", widget, args))

    def addLayout(self, layout) -> None:  # noqa: N802
        self.children.append(("layout", layout))

    def insertStretch(self, index: int, stretch: int) -> None:  # noqa: N802
        self.children.append(("stretch", index, stretch))

    def addStretch(self, stretch: int) -> None:  # noqa: N802
        self.children.append(("stretch", stretch))


class FakeLabel:
    def __init__(self, text: str = "") -> None:
        self.text_value = text

    def setObjectName(self, name: str) -> None:  # noqa: N802
        self.object_name = name

    def setTextInteractionFlags(self, flags) -> None:  # noqa: N802
        self.flags = flags

    def setWordWrap(self, wrap: bool) -> None:  # noqa: N802
        self.wrap = wrap

    def setText(self, text: str) -> None:  # noqa: N802
        self.text_value = text


class FakeSplitter:
    def __init__(self, orientation) -> None:
        self.orientation = orientation
        self.widgets = []

    def setChildrenCollapsible(self, value: bool) -> None:  # noqa: N802
        self.collapsible = value

    def addWidget(self, widget) -> None:  # noqa: N802
        self.widgets.append(widget)

    def setSizes(self, sizes: list[int]) -> None:  # noqa: N802
        self.sizes = sizes


class FakeListItem:
    def __init__(self, text: str) -> None:
        self._text = text
        self._data = {}
        self._flags = 7

    def setData(self, role, value) -> None:  # noqa: N802
        self._data[role] = value

    def data(self, role):
        return self._data.get(role)

    def setToolTip(self, tooltip: str) -> None:  # noqa: N802
        self.tooltip = tooltip

    def setForeground(self, color) -> None:  # noqa: N802
        self.foreground = color

    def setBackground(self, color) -> None:  # noqa: N802
        self.background = color

    def flags(self) -> int:
        return self._flags

    def setFlags(self, flags: int) -> None:  # noqa: N802
        self._flags = flags

    def text(self) -> str:
        return self._text


class FakeListWidget:
    def __init__(self) -> None:
        self.items = []
        self.current_row = -1
        self.selected = []
        self.itemSelectionChanged = FakeSignal()

    def setObjectName(self, name: str) -> None:  # noqa: N802
        self.object_name = name

    def setSelectionMode(self, mode) -> None:  # noqa: N802
        self.mode = mode

    def setAlternatingRowColors(self, value: bool) -> None:  # noqa: N802
        self.alternating = value

    def addItem(self, item) -> None:  # noqa: N802
        self.items.append(item)

    def selectedItems(self) -> list[FakeListItem]:  # noqa: N802
        return self.selected

    def currentItem(self):  # noqa: N802
        if self.current_row < 0:
            return None
        return self.items[self.current_row]

    def setCurrentRow(self, row: int) -> None:  # noqa: N802
        self.current_row = row

    def count(self) -> int:
        return len(self.items)

    def item(self, index: int):
        return self.items[index]

    def clear(self) -> None:
        self.items.clear()
        self.current_row = -1


class FakeCursor:
    def __init__(self, text: str = "") -> None:
        self.text = text

    def selectedText(self) -> str:  # noqa: N802
        return self.text


class FakeTextEdit:
    WidgetWidth = 1
    NoWrap = 2

    def __init__(self) -> None:
        self.plain_text = ""
        self.cursor = FakeCursor()

    def setObjectName(self, name: str) -> None:  # noqa: N802
        self.object_name = name

    def setReadOnly(self, value: bool) -> None:  # noqa: N802
        self.read_only = value

    def setAcceptRichText(self, value: bool) -> None:  # noqa: N802
        self.accept_rich = value

    def setLineWrapMode(self, mode) -> None:  # noqa: N802
        self.wrap_mode = mode

    def setMinimumHeight(self, height: int) -> None:  # noqa: N802
        self.minimum_height = height

    def setPlainText(self, text: str) -> None:  # noqa: N802
        self.plain_text = text

    def toPlainText(self) -> str:  # noqa: N802
        return self.plain_text

    def textCursor(self) -> FakeCursor:  # noqa: N802
        return self.cursor


class FakeButton:
    def __init__(self, text: str) -> None:
        self.text = text
        self.clicked = FakeSignal()

    def setProperty(self, name: str, value) -> None:  # noqa: N802
        setattr(self, name, value)


class FakeComboBox:
    def __init__(self) -> None:
        self.items = []
        self.current_index = 0
        self.currentIndexChanged = FakeSignal()

    def setObjectName(self, name: str) -> None:  # noqa: N802
        self.object_name = name

    def setProperty(self, name: str, value) -> None:  # noqa: N802
        setattr(self, name, value)

    def addItems(self, items) -> None:  # noqa: N802
        self.items.extend(items)

    def currentText(self) -> str:  # noqa: N802
        if not self.items:
            return ""
        return self.items[self.current_index]

    def setCurrentIndex(self, index: int) -> None:  # noqa: N802
        self.current_index = index
        self.currentIndexChanged.emit()


class FakeQtWidgets:
    app = FakeApp()
    clipboard = FakeClipboard()
    lists = []
    text_edits = []
    buttons = []
    combos = []
    dialogs = []

    class QApplication:
        @staticmethod
        def instance():
            return FakeQtWidgets.app

        @staticmethod
        def clipboard():
            return FakeQtWidgets.clipboard

    QDialog = FakeDialog
    QVBoxLayout = FakeLayout
    QHBoxLayout = FakeLayout
    QLabel = FakeLabel
    QSplitter = FakeSplitter
    QListWidgetItem = FakeListItem

    class QListWidget(FakeListWidget):
        def __init__(self) -> None:
            super().__init__()
            FakeQtWidgets.lists.append(self)

    class QTextEdit(FakeTextEdit):
        def __init__(self) -> None:
            super().__init__()
            FakeQtWidgets.text_edits.append(self)

    class QPushButton(FakeButton):
        def __init__(self, text: str) -> None:
            super().__init__(text)
            FakeQtWidgets.buttons.append(self)

    class QComboBox(FakeComboBox):
        def __init__(self) -> None:
            super().__init__()
            FakeQtWidgets.combos.append(self)

    class QAbstractItemView:
        ExtendedSelection = 1


class FakeQtCore:
    class Qt:
        WA_DeleteOnClose = 1
        TextSelectableByMouse = 2
        Vertical = 3
        UserRole = 4
        ItemIsSelectable = 1

    class QEvent:
        DeferredDelete = 5


class FakeQtGui:
    QColor = str


@pytest.fixture()
def fake_qt() -> QtBinding:
    FakeQtWidgets.app = FakeApp()
    FakeQtWidgets.clipboard = FakeClipboard()
    FakeQtWidgets.lists = []
    FakeQtWidgets.text_edits = []
    FakeQtWidgets.buttons = []
    FakeQtWidgets.combos = []
    return QtBinding("Fake", FakeQtCore, FakeQtGui, FakeQtWidgets, lambda pointer, base: base)


def test_issue_detail_includes_import_path_and_field() -> None:
    issue = DiagnosticIssue(
        code="invalid_icon_import_metadata",
        severity="error",
        message="Icon id must use letters, numbers, dots, underscores, or hyphens.",
        target="bad id",
        path="icons/custom/arrow.svg",
        field="icon_id",
        hint="Use a valid icon id.",
    )

    detail = _issue_detail(issue)

    assert "Target: bad id" in detail
    assert "Path: icons/custom/arrow.svg" in detail
    assert "Field: icon_id" in detail
    assert "Hint: Use a valid icon id." in detail


def test_issue_title_uses_path_when_no_stronger_target_exists() -> None:
    issue = DiagnosticIssue(
        code="missing_icon_fallback_file",
        severity="warning",
        message="Icon points to a missing PNG fallback.",
        path="icons/custom/arrow@3x.png",
    )

    assert (
        _issue_title(issue)
        == "WARNING missing_icon_fallback_file - icons/custom/arrow@3x.png"
    )


def test_summary_text_includes_overlay_support_counts() -> None:
    report = DiagnosticReport(
        active_overlay_ids=("transform_stack",),
        published_runtime_commands=("ActionRail_action_maya_tool_move",),
        active_overlay_states=(
            DiagnosticOverlayState(
                preset_id="transform_stack",
                filter_target_count=2,
                predicate_timer_active=True,
            ),
        ),
    )

    summary = _summary_text(report)

    assert "Published commands: 1." in summary
    assert "Event filters: 2." in summary
    assert "Refresh timers: 1." in summary


def test_filtered_issues_selects_severity() -> None:
    error = DiagnosticIssue("missing_action", "error", "Missing action.")
    warning = DiagnosticIssue("missing_icon", "warning", "Missing icon.")
    info = DiagnosticIssue("note", "info", "Note.")
    report = DiagnosticReport((error, warning, info))

    assert _filtered_issues(report, "all") == (error, warning, info)
    assert _filtered_issues(report, "error") == (error,)
    assert _filtered_issues(report, "warning") == (warning,)
    assert _filtered_issues(report, "info") == (info,)


def test_issue_filter_value_and_empty_labels_cover_supported_filters() -> None:
    combo = FakeComboBox()
    combo.addItems(("All Issues", "Errors", "Warnings", "Info"))

    assert _issue_filter_value(combo) == "all"
    assert _filter_empty_label("all") == "issues"
    combo.setCurrentIndex(1)
    assert _issue_filter_value(combo) == "error"
    assert _filter_empty_label("error") == "errors"
    combo.setCurrentIndex(2)
    assert _issue_filter_value(combo) == "warning"
    assert _filter_empty_label("warning") == "warnings"
    combo.setCurrentIndex(3)
    assert _issue_filter_value(combo) == "info"
    assert _filter_empty_label("info") == "info issues"


def test_show_report_window_builds_interactive_window(fake_qt: QtBinding, monkeypatch) -> None:
    cleared = []
    hidden = []
    monkeypatch.setattr(diagnostics_ui, "maya_main_window", lambda _qt: "mayaWindow")
    report = DiagnosticReport(
        (
            DiagnosticIssue("missing_action", "error", "Missing action.", slot_id="slot"),
            DiagnosticIssue("missing_plugin", "warning", "Missing plugin.", target="plugin"),
        )
    )

    window = diagnostics_ui.show_report_window(
        report,
        "full report",
        on_clear=lambda: cleared.append(True),
        on_hide_overlays=lambda: hidden.append(True),
        qt_binding=fake_qt,
    )

    assert window.parent == "mayaWindow"
    assert window.shown is True
    assert window.raised is True
    assert window.activated is True
    issue_list = FakeQtWidgets.lists[-1]
    issue_filter = FakeQtWidgets.combos[-1]
    issue_detail, report_box = FakeQtWidgets.text_edits[-2:]
    assert issue_list.count() == 2
    assert issue_detail.toPlainText().startswith("Severity: error")
    assert report_box.toPlainText() == "full report"

    issue_filter.setCurrentIndex(2)
    assert issue_list.count() == 1
    assert issue_list.item(0).text().startswith("WARNING missing_plugin")
    assert issue_detail.toPlainText().startswith("Severity: warning")

    issue_filter.setCurrentIndex(3)
    assert issue_list.count() == 1
    assert issue_list.item(0).text() == "No info issues found."

    copy_selected, copy_full, hide_overlays, clear_button, close_button = (
        FakeQtWidgets.buttons[-5:]
    )
    issue_filter.setCurrentIndex(0)
    issue_list.selected = [issue_list.item(1)]
    issue_list.itemSelectionChanged.emit()
    assert issue_detail.toPlainText().startswith("Severity: warning")

    issue_list.selected = [issue_list.item(0)]
    copy_selected.clicked.emit()
    assert FakeQtWidgets.clipboard.text.startswith("Severity: error")

    issue_list.selected = []
    issue_list.current_row = -1
    report_box.cursor = FakeCursor("selected\u2029text")
    copy_selected.clicked.emit()
    assert FakeQtWidgets.clipboard.text == "selected\ntext"

    copy_full.clicked.emit()
    assert FakeQtWidgets.clipboard.text == "full report"

    hide_overlays.clicked.emit()
    assert hidden == [True]

    clear_button.clicked.emit()
    assert cleared == [True]
    assert issue_list.item(0).text() == "No ActionRail diagnostic report has been recorded."
    assert report_box.toPlainText() == "No ActionRail diagnostic report has been recorded."

    close_button.clicked.emit()
    assert window.closed is True
    window.destroyed.emit()
    assert diagnostics_ui._WINDOW is None


def test_show_report_window_requires_qapplication(fake_qt: QtBinding) -> None:
    FakeQtWidgets.app = None

    with pytest.raises(RuntimeError, match="requires a QApplication"):
        diagnostics_ui.show_report_window(None, "report", qt_binding=fake_qt)


def test_show_report_window_closes_existing_window(fake_qt: QtBinding, monkeypatch) -> None:
    old_window = FakeDialog()
    diagnostics_ui._WINDOW = old_window
    monkeypatch.setattr(diagnostics_ui, "maya_main_window", lambda _qt: None)

    window = diagnostics_ui.show_report_window(None, "report", qt_binding=fake_qt)

    assert old_window.closed is True
    assert old_window.deleted is True
    assert FakeQtWidgets.app.sent_events
    assert diagnostics_ui._WINDOW is window
    diagnostics_ui._forget_window()


def test_close_existing_window_ignores_close_errors(fake_qt: QtBinding) -> None:
    class BrokenWindow(FakeDialog):
        def close(self) -> None:
            raise RuntimeError("already deleted")

    diagnostics_ui._WINDOW = BrokenWindow()

    diagnostics_ui._close_existing_window(fake_qt)

    assert diagnostics_ui._WINDOW is None

    diagnostics_ui._close_existing_window(fake_qt)


def test_issue_list_helpers_cover_empty_and_current_item_paths(fake_qt: QtBinding) -> None:
    issue_list = fake_qt.QtWidgets.QListWidget()

    diagnostics_ui._populate_issue_list(issue_list, fake_qt, None)
    assert diagnostics_ui._selected_issue_text(issue_list, fake_qt) == ""
    assert diagnostics_ui._current_issue_detail_text(issue_list, fake_qt) == "No recorded report."

    issue_list.clear()
    diagnostics_ui._populate_issue_list(issue_list, fake_qt, DiagnosticReport())
    assert diagnostics_ui._current_issue_detail_text(issue_list, fake_qt) == "No issues found."

    issue_list.clear()
    assert diagnostics_ui._current_issue_detail_text(issue_list, fake_qt) == "No issues found."
    assert diagnostics_ui._style_sheet().strip().startswith("QDialog#ActionRailDiagnosticsWindow")
