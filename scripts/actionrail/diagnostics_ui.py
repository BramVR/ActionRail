"""Qt diagnostics report window for ActionRail."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .diagnostics import DiagnosticIssue, DiagnosticReport
from .overlay import maya_main_window
from .qt import QtBinding, load
from .theme import DEFAULT_THEME

WINDOW_OBJECT_NAME = "ActionRailDiagnosticsWindow"
ISSUE_LIST_OBJECT_NAME = "ActionRailDiagnosticsIssueList"
ISSUE_DETAIL_OBJECT_NAME = "ActionRailDiagnosticsIssueDetail"
REPORT_TEXT_OBJECT_NAME = "ActionRailDiagnosticsReportText"
SUMMARY_OBJECT_NAME = "ActionRailDiagnosticsSummary"

_WINDOW: Any | None = None


def show_report_window(
    report: DiagnosticReport | None,
    report_text: str,
    *,
    on_clear: Callable[[], None] | None = None,
    qt_binding: QtBinding | None = None,
    parent: Any | None = None,
) -> Any:
    """Show a non-modal themed diagnostics window and return the Qt widget."""

    global _WINDOW

    qt = qt_binding or load()
    app = qt.QtWidgets.QApplication.instance()
    if app is None:
        msg = "ActionRail diagnostic UI requires a QApplication inside Maya."
        raise RuntimeError(msg)

    if _WINDOW is not None:
        _close_existing_window(qt)

    window_parent = parent if parent is not None else maya_main_window(qt)
    window = qt.QtWidgets.QDialog(window_parent)
    window.setObjectName(WINDOW_OBJECT_NAME)
    window.setWindowTitle("ActionRail Diagnostics")
    window.setMinimumSize(560, 420)
    window.resize(720, 520)
    window.setModal(False)
    window.setAttribute(qt.QtCore.Qt.WA_DeleteOnClose, True)

    _build_window(window, qt, report, report_text, on_clear)
    window.destroyed.connect(_forget_window)
    _WINDOW = window
    window.show()
    window.raise_()
    window.activateWindow()
    return window


def _build_window(
    window: Any,
    qt: QtBinding,
    report: DiagnosticReport | None,
    report_text: str,
    on_clear: Callable[[], None] | None,
) -> None:
    window.setStyleSheet(_style_sheet())

    root = qt.QtWidgets.QVBoxLayout(window)
    root.setContentsMargins(14, 14, 14, 14)
    root.setSpacing(10)

    title = qt.QtWidgets.QLabel("ActionRail Diagnostics")
    title.setObjectName("ActionRailDiagnosticsTitle")
    title.setTextInteractionFlags(qt.QtCore.Qt.TextSelectableByMouse)
    root.addWidget(title)

    summary = qt.QtWidgets.QLabel(_summary_text(report))
    summary.setObjectName(SUMMARY_OBJECT_NAME)
    summary.setTextInteractionFlags(qt.QtCore.Qt.TextSelectableByMouse)
    summary.setWordWrap(True)
    root.addWidget(summary)

    splitter = qt.QtWidgets.QSplitter(qt.QtCore.Qt.Vertical)
    splitter.setChildrenCollapsible(False)
    root.addWidget(splitter, 1)

    issue_list = qt.QtWidgets.QListWidget()
    issue_list.setObjectName(ISSUE_LIST_OBJECT_NAME)
    issue_list.setSelectionMode(qt.QtWidgets.QAbstractItemView.ExtendedSelection)
    issue_list.setAlternatingRowColors(True)
    _populate_issue_list(issue_list, qt, report)
    splitter.addWidget(issue_list)

    issue_detail = qt.QtWidgets.QTextEdit()
    issue_detail.setObjectName(ISSUE_DETAIL_OBJECT_NAME)
    issue_detail.setReadOnly(True)
    issue_detail.setAcceptRichText(False)
    issue_detail.setLineWrapMode(qt.QtWidgets.QTextEdit.WidgetWidth)
    issue_detail.setMinimumHeight(88)
    issue_detail.setPlainText(_current_issue_detail_text(issue_list, qt))
    splitter.addWidget(issue_detail)

    report_box = qt.QtWidgets.QTextEdit()
    report_box.setObjectName(REPORT_TEXT_OBJECT_NAME)
    report_box.setReadOnly(True)
    report_box.setAcceptRichText(False)
    report_box.setLineWrapMode(qt.QtWidgets.QTextEdit.NoWrap)
    report_box.setPlainText(report_text)
    splitter.addWidget(report_box)
    splitter.setSizes([180, 130, 220])

    button_row = qt.QtWidgets.QHBoxLayout()
    button_row.setContentsMargins(0, 0, 0, 0)
    button_row.setSpacing(8)
    root.addLayout(button_row)

    copy_selected = qt.QtWidgets.QPushButton("Copy Selected")
    copy_full = qt.QtWidgets.QPushButton("Copy Full Report")
    clear_button = qt.QtWidgets.QPushButton("Clear")
    close_button = qt.QtWidgets.QPushButton("Close")
    for button in (copy_selected, copy_full, clear_button, close_button):
        button.setProperty("actionRailRole", "dialogButton")
        button_row.addWidget(button)

    button_row.insertStretch(0, 1)

    def copy_selected_text() -> None:
        selected_text = _selected_issue_text(issue_list, qt)
        if not selected_text:
            selected_text = report_box.textCursor().selectedText().replace("\u2029", "\n")
        if selected_text:
            _set_clipboard(qt, selected_text)

    def copy_full_text() -> None:
        _set_clipboard(qt, report_box.toPlainText())

    def update_issue_detail() -> None:
        issue_detail.setPlainText(_current_issue_detail_text(issue_list, qt))

    def clear_report() -> None:
        if on_clear is not None:
            on_clear()
        issue_list.clear()
        _add_empty_issue_item(issue_list, qt, "No ActionRail diagnostic report has been recorded.")
        issue_detail.setPlainText("No ActionRail diagnostic report has been recorded.")
        summary.setText(_summary_text(None))
        report_box.setPlainText("No ActionRail diagnostic report has been recorded.")

    issue_list.itemSelectionChanged.connect(update_issue_detail)
    if report is not None and report.issues:
        issue_list.setCurrentRow(0)
    copy_selected.clicked.connect(copy_selected_text)
    copy_full.clicked.connect(copy_full_text)
    clear_button.clicked.connect(clear_report)
    close_button.clicked.connect(window.close)


def _populate_issue_list(issue_list: Any, qt: QtBinding, report: DiagnosticReport | None) -> None:
    if report is None:
        _add_empty_issue_item(issue_list, qt, "No recorded report.")
        return
    if not report.issues:
        _add_empty_issue_item(issue_list, qt, "No issues found.")
        return

    for issue in report.issues:
        item = qt.QtWidgets.QListWidgetItem(_issue_title(issue))
        item.setData(qt.QtCore.Qt.UserRole, _issue_detail(issue))
        item.setToolTip(issue.message)
        if issue.severity == "error":
            item.setForeground(qt.QtGui.QColor("#fff1f2"))
            item.setBackground(qt.QtGui.QColor("#724c52"))
        elif issue.severity == "warning":
            item.setForeground(qt.QtGui.QColor("#fff4d6"))
        issue_list.addItem(item)


def _add_empty_issue_item(issue_list: Any, qt: QtBinding, text: str) -> None:
    item = qt.QtWidgets.QListWidgetItem(text)
    item.setFlags(item.flags() & ~qt.QtCore.Qt.ItemIsSelectable)
    issue_list.addItem(item)


def _selected_issue_text(issue_list: Any, qt: QtBinding) -> str:
    items = issue_list.selectedItems()
    if not items:
        current = issue_list.currentItem()
        items = [current] if current is not None else []
    details = [
        item.data(qt.QtCore.Qt.UserRole)
        for item in items
        if item is not None and item.data(qt.QtCore.Qt.UserRole)
    ]
    return "\n\n".join(str(detail) for detail in details)


def _current_issue_detail_text(issue_list: Any, qt: QtBinding) -> str:
    selected_text = _selected_issue_text(issue_list, qt)
    if selected_text:
        return selected_text
    if issue_list.count():
        first_item = issue_list.item(0)
        detail = first_item.data(qt.QtCore.Qt.UserRole)
        if detail:
            return str(detail)
        return first_item.text()
    return "No issues found."


def _set_clipboard(qt: QtBinding, text: str) -> None:
    clipboard = qt.QtWidgets.QApplication.clipboard()
    clipboard.setText(text)


def _summary_text(report: DiagnosticReport | None) -> str:
    if report is None:
        return "No report recorded."

    issue_count = len(report.issues)
    error_count = len(report.errors)
    warning_count = len(report.warnings)
    status = "Errors found" if report.has_errors else "OK"
    overlay = "started" if report.overlay_started else "not started"
    active = ", ".join(report.active_overlay_ids) if report.active_overlay_ids else "none"
    return (
        f"{status} - {error_count} errors, {warning_count} warnings, "
        f"{issue_count} total issues. Overlay {overlay}. Active overlays: {active}."
    )


def _issue_title(issue: DiagnosticIssue) -> str:
    target = issue.slot_id or issue.preset_id or issue.action_id or issue.target or issue.path
    suffix = f" - {target}" if target else ""
    return f"{issue.severity.upper()} {issue.code}{suffix}"


def _issue_detail(issue: DiagnosticIssue) -> str:
    fields = [
        f"Severity: {issue.severity}",
        f"Code: {issue.code}",
        f"Message: {issue.message}",
    ]
    optional_fields = (
        ("Preset", issue.preset_id),
        ("Slot", issue.slot_id),
        ("Action", issue.action_id),
        ("Predicate field", issue.predicate_field),
        ("Predicate", issue.predicate),
        ("Target", issue.target),
        ("Path", issue.path),
        ("Field", issue.field),
        ("Hint", issue.hint),
        ("Exception", issue.exception_type),
    )
    fields.extend(f"{label}: {value}" for label, value in optional_fields if value)
    return "\n".join(fields)


def _style_sheet() -> str:
    theme = DEFAULT_THEME
    return f"""
QDialog#{WINDOW_OBJECT_NAME} {{
    background: {theme.cluster_background};
    color: {theme.button_color};
}}
QLabel#ActionRailDiagnosticsTitle {{
    color: {theme.button_color};
    font-size: 18px;
    font-weight: 700;
    letter-spacing: 0px;
}}
QLabel#{SUMMARY_OBJECT_NAME} {{
    color: {theme.button_color};
    font-size: 12px;
    letter-spacing: 0px;
}}
QListWidget#{ISSUE_LIST_OBJECT_NAME},
QTextEdit#{ISSUE_DETAIL_OBJECT_NAME},
QTextEdit#{REPORT_TEXT_OBJECT_NAME} {{
    background: #333338;
    color: {theme.button_color};
    border: {theme.cluster_border_width}px solid {theme.cluster_border};
    border-radius: {theme.cluster_border_radius}px;
    selection-background-color: {theme.button_active_background};
    selection-color: {theme.button_color};
    font-size: 12px;
    letter-spacing: 0px;
}}
QListWidget#{ISSUE_LIST_OBJECT_NAME}::item {{
    padding: 6px;
}}
QListWidget#{ISSUE_LIST_OBJECT_NAME}::item:alternate {{
    background: #3b3b40;
}}
QPushButton[actionRailRole="dialogButton"] {{
    min-height: 26px;
    border: {theme.button_border_width}px solid {theme.button_border};
    border-radius: {theme.button_border_radius}px;
    background: {theme.button_background};
    color: {theme.button_color};
    padding: 4px 10px;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0px;
}}
QPushButton[actionRailRole="dialogButton"]:hover {{
    background: {theme.button_hover_background};
    border-color: {theme.button_hover_border};
}}
QPushButton[actionRailRole="dialogButton"]:pressed {{
    background: {theme.button_pressed_background};
}}
"""


def _close_existing_window(qt: QtBinding) -> None:
    global _WINDOW
    if _WINDOW is None:
        return
    try:
        _WINDOW.close()
        _WINDOW.deleteLater()
        app = qt.QtWidgets.QApplication.instance()
        if app is not None:
            app.sendPostedEvents(None, qt.QtCore.QEvent.DeferredDelete)
    except Exception:
        pass
    _WINDOW = None


def _forget_window(*_args: Any) -> None:
    global _WINDOW
    _WINDOW = None
