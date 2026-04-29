from __future__ import annotations

import json
import sys
from pathlib import Path

__args__ = globals().get("__args__", {})

repo_scripts = __args__.get("repo_scripts")
if repo_scripts and repo_scripts not in sys.path:
    sys.path.insert(0, repo_scripts)

output_path = Path(
    __args__.get(
        "output_path",
        "C:/PROJECTS/GG/ScreenUI/.gg-maya-sessiond/screenshots/"
        "actionrail_diagnostics_window.png",
    )
)
output_path.parent.mkdir(parents=True, exist_ok=True)

from maya import cmds  # noqa: E402
from PySide6 import QtWidgets  # noqa: E402

import actionrail  # noqa: E402
from actionrail.diagnostics import diagnose_spec  # noqa: E402
from actionrail.diagnostics_ui import (  # noqa: E402
    ISSUE_LIST_OBJECT_NAME,
    REPORT_TEXT_OBJECT_NAME,
    SUMMARY_OBJECT_NAME,
    WINDOW_OBJECT_NAME,
)
from actionrail.runtime import _OVERLAYS, active_overlay_ids  # noqa: E402
from actionrail.spec import RailLayout, StackItem, StackSpec  # noqa: E402

app = QtWidgets.QApplication.instance()
if app is None:
    raise RuntimeError("Maya QApplication is not available.")

cmds.file(new=True, force=True)

builtin_report = actionrail.collect_diagnostics(("transform_stack",))
if builtin_report.has_errors:
    raise AssertionError(f"Built-in preset diagnostics reported errors: {builtin_report.as_dict()}")

availability_spec = StackSpec(
    id="diagnostics_availability",
    layout=RailLayout(anchor="viewport.left.center"),
    items=(
        StackItem(
            type="button",
            id="diagnostics_availability.command",
            label="C",
            action="maya.anim.set_key",
            enabled_when="command.exists('definitelyMissingActionRailCommand')",
        ),
        StackItem(
            type="button",
            id="diagnostics_availability.plugin",
            label="P",
            action="maya.anim.set_key",
            visible_when="plugin.exists('definitelyMissingActionRailPlugin')",
        ),
    ),
)
availability_report = diagnose_spec(availability_spec, cmds_module=cmds)
availability_codes = [issue.code for issue in availability_report.warnings]
if availability_codes != ["missing_command", "missing_plugin"]:
    raise AssertionError(f"Missing availability diagnostics: {availability_report.as_dict()}")

broken_spec = StackSpec(
    id="diagnostics_broken",
    layout=RailLayout(anchor="viewport.left.center"),
    items=(
        StackItem(
            type="button",
            id="diagnostics_broken.action",
            label="X",
            action="maya.missing.action",
        ),
    ),
)
broken_report = diagnose_spec(broken_spec, cmds_module=cmds)
if [issue.code for issue in broken_report.errors] != ["missing_action"]:
    raise AssertionError(f"Missing action diagnostic failed: {broken_report.as_dict()}")

window_report_text = actionrail.show_last_report()
app.processEvents()
diagnostics_window = app.activeWindow()
if diagnostics_window is None or diagnostics_window.objectName() != WINDOW_OBJECT_NAME:
    diagnostics_window = next(
        (
            widget
            for widget in app.allWidgets()
            if widget.objectName() == WINDOW_OBJECT_NAME and widget.isVisible()
        ),
        None,
    )
if diagnostics_window is None:
    raise AssertionError("Diagnostics window did not open.")

issue_list = diagnostics_window.findChild(QtWidgets.QListWidget, ISSUE_LIST_OBJECT_NAME)
report_text = diagnostics_window.findChild(QtWidgets.QTextEdit, REPORT_TEXT_OBJECT_NAME)
summary_label = diagnostics_window.findChild(QtWidgets.QLabel, SUMMARY_OBJECT_NAME)
if issue_list is None or report_text is None or summary_label is None:
    raise AssertionError("Diagnostics window is missing expected child widgets.")
if issue_list.count() != 1 or "missing_action" not in issue_list.item(0).text():
    raise AssertionError(
        f"Diagnostics issue list did not show missing action: {issue_list.count()}"
    )
if "Status: errors" not in report_text.toPlainText():
    raise AssertionError(f"Diagnostics report text missing errors: {report_text.toPlainText()}")
if "1 errors" not in summary_label.text():
    raise AssertionError(f"Diagnostics summary missing error count: {summary_label.text()}")

window_pixmap = diagnostics_window.grab()
window_screenshot_saved = window_pixmap.save(str(output_path), "PNG")
if not window_screenshot_saved:
    raise AssertionError(f"Could not save diagnostics screenshot: {output_path}")

issue_list.setCurrentRow(0)
copy_buttons = {
    button.text(): button for button in diagnostics_window.findChildren(QtWidgets.QPushButton)
}
copy_buttons["Copy Selected"].click()
app.processEvents()
selected_clipboard_text = QtWidgets.QApplication.clipboard().text()
if "Code: missing_action" not in selected_clipboard_text:
    raise AssertionError(f"Copy Selected produced wrong text: {selected_clipboard_text}")

copy_buttons["Copy Full Report"].click()
app.processEvents()
full_clipboard_text = QtWidgets.QApplication.clipboard().text()
if full_clipboard_text != window_report_text:
    raise AssertionError("Copy Full Report did not copy the formatted report.")

copy_buttons["Clear"].click()
app.processEvents()
if actionrail.last_report() is not None:
    raise AssertionError("Diagnostics Clear button did not clear last_report().")
if "No ActionRail diagnostic report" not in report_text.toPlainText():
    raise AssertionError("Diagnostics Clear button did not clear visible report text.")

diagnostics_window.close()
app.processEvents()

missing_icon_spec = StackSpec(
    id="diagnostics_missing_icon",
    layout=RailLayout(anchor="viewport.left.center"),
    items=(
        StackItem(
            type="button",
            id="diagnostics_missing_icon.slot",
            label="I",
            action="maya.anim.set_key",
            icon="missing.icon",
        ),
    ),
)
missing_icon_report = diagnose_spec(missing_icon_spec, cmds_module=cmds)
if [issue.code for issue in missing_icon_report.warnings] != ["missing_icon"]:
    raise AssertionError(f"Missing icon diagnostic failed: {missing_icon_report.as_dict()}")

start_report = actionrail.safe_start("transform_stack")
app.processEvents()
cmds.refresh(force=True)
if start_report.has_errors or not start_report.overlay_started:
    raise AssertionError(f"Safe start did not show transform_stack: {start_report.as_dict()}")
last_report = actionrail.last_report()
if last_report != start_report:
    raise AssertionError(f"Last report did not track safe_start: {last_report!r}")
last_report_text = actionrail.format_report()
if "Status: ok" not in last_report_text or "Overlay id: transform_stack" not in last_report_text:
    raise AssertionError(f"Last report text missing safe_start state: {last_report_text}")
if active_overlay_ids() != ("transform_stack",):
    raise AssertionError(f"Unexpected active overlays after safe start: {active_overlay_ids()}")

widget = _OVERLAYS.get("transform_stack")
widget_size = []
if widget is not None and getattr(widget, "widget", None) is not None:
    widget_size = [widget.widget.width(), widget.widget.height()]

result = {
    "availability_warning_codes": availability_codes,
    "broken_error_codes": [issue.code for issue in broken_report.errors],
    "builtin_issue_count": len(builtin_report.issues),
    "missing_icon_warning_codes": [issue.code for issue in missing_icon_report.warnings],
    "safe_start_active_ids": active_overlay_ids(),
    "safe_start_overlay_started": start_report.overlay_started,
    "last_report_text": last_report_text,
    "diagnostics_window_copied_selected": "Code: missing_action" in selected_clipboard_text,
    "diagnostics_window_copied_full": full_clipboard_text == window_report_text,
    "diagnostics_window_screenshot": str(output_path),
    "diagnostics_window_screenshot_size": [
        window_pixmap.width(),
        window_pixmap.height(),
    ],
    "widget_size": widget_size,
}

actionrail.hide_all()
app.processEvents()

print(json.dumps(result, sort_keys=True))
