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
        "actionrail_import_diagnostics_window.png",
    )
)
output_path.parent.mkdir(parents=True, exist_ok=True)

source_path = Path(
    __args__.get(
        "source_path",
        "C:/PROJECTS/GG/ScreenUI/.gg-maya-sessiond/tmp/not-an-svg.txt",
    )
)
source_path.parent.mkdir(parents=True, exist_ok=True)
source_path.write_text("not svg", encoding="utf-8")

from maya import cmds  # noqa: E402
from PySide6 import QtWidgets  # noqa: E402

import actionrail  # noqa: E402
from actionrail.diagnostics_ui import (  # noqa: E402
    ISSUE_LIST_OBJECT_NAME,
    REPORT_TEXT_OBJECT_NAME,
    SUMMARY_OBJECT_NAME,
    WINDOW_OBJECT_NAME,
)
from actionrail.runtime import active_overlay_ids  # noqa: E402

app = QtWidgets.QApplication.instance()
if app is None:
    raise RuntimeError("Maya QApplication is not available.")

cmds.file(new=True, force=True)

import_report = actionrail.diagnose_icon_import(
    str(source_path),
    "bad id",
    source="Local",
    license_name="Apache-2.0",
    url="local://not-an-svg.txt",
    target_path="icons/actionrail/move.svg",
)
import_codes = [issue.code for issue in import_report.errors]
expected_import_codes = [
    "invalid_icon_import_source",
    "invalid_icon_import_metadata",
    "icon_path_conflict",
    "icon_target_exists",
]
if import_codes != expected_import_codes:
    raise AssertionError(f"Unexpected import diagnostics: {import_report.as_dict()}")
if actionrail.last_report() != import_report:
    raise AssertionError("diagnose_icon_import did not record last_report().")

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
    raise AssertionError("Import diagnostics window did not open.")

issue_list = diagnostics_window.findChild(QtWidgets.QListWidget, ISSUE_LIST_OBJECT_NAME)
report_text = diagnostics_window.findChild(QtWidgets.QTextEdit, REPORT_TEXT_OBJECT_NAME)
summary_label = diagnostics_window.findChild(QtWidgets.QLabel, SUMMARY_OBJECT_NAME)
if issue_list is None or report_text is None or summary_label is None:
    raise AssertionError("Import diagnostics window is missing expected child widgets.")

if issue_list.count() != len(expected_import_codes):
    raise AssertionError(f"Wrong import issue count in UI: {issue_list.count()}")
ui_issue_text = "\n".join(issue_list.item(index).text() for index in range(issue_list.count()))
for code in expected_import_codes:
    if code not in ui_issue_text:
        raise AssertionError(f"Import diagnostics UI missing {code}: {ui_issue_text}")
if "4 errors" not in summary_label.text():
    raise AssertionError(f"Import diagnostics summary missing error count: {summary_label.text()}")
if (
    "Status: errors" not in report_text.toPlainText()
    or "icon_path_conflict" not in report_text.toPlainText()
    or "path: icons/actionrail/move.svg" not in report_text.toPlainText()
    or "field: icon_id" not in report_text.toPlainText()
    or "hint:" not in report_text.toPlainText()
):
    raise AssertionError(f"Import report text missing issue detail: {report_text.toPlainText()}")

issue_list.setCurrentRow(1)
copy_buttons = {
    button.text(): button for button in diagnostics_window.findChildren(QtWidgets.QPushButton)
}
copy_buttons["Copy Selected"].click()
app.processEvents()
selected_clipboard_text = QtWidgets.QApplication.clipboard().text()
if "Code: invalid_icon_import_metadata" not in selected_clipboard_text:
    raise AssertionError(f"Copy Selected produced wrong issue: {selected_clipboard_text}")
if "Hint:" not in selected_clipboard_text or "icon_id" not in selected_clipboard_text:
    raise AssertionError(f"Copy Selected missing import hint detail: {selected_clipboard_text}")

window_pixmap = diagnostics_window.grab()
if not window_pixmap.save(str(output_path), "PNG"):
    raise AssertionError(f"Could not save import diagnostics screenshot: {output_path}")
if window_pixmap.width() <= 0 or window_pixmap.height() <= 0:
    raise AssertionError(
        f"Import diagnostics screenshot has invalid size: {window_pixmap.size()}"
    )

diagnostics_window.close()
app.processEvents()

recovery_report = actionrail.safe_start(
    "missing_preset",
    fallback_preset_id="transform_stack",
)
app.processEvents()
cmds.refresh(force=True)
recovery_codes = [issue.code for issue in recovery_report.issues]
if recovery_codes != ["broken_preset", "preset_recovered"]:
    raise AssertionError(f"Unexpected recovery diagnostics: {recovery_report.as_dict()}")
if not recovery_report.overlay_started or recovery_report.overlay_id != "transform_stack":
    raise AssertionError(f"Fallback preset did not start: {recovery_report.as_dict()}")
if active_overlay_ids() != ("transform_stack",):
    raise AssertionError(f"Unexpected active overlays after recovery: {active_overlay_ids()}")
if actionrail.last_report() != recovery_report:
    raise AssertionError("safe_start fallback recovery did not record last_report().")

result = {
    "active_overlay_ids": active_overlay_ids(),
    "import_error_codes": import_codes,
    "import_report_text_has_conflict": "icon_path_conflict" in window_report_text,
    "import_selected_copy_has_hint": "Hint:" in selected_clipboard_text,
    "import_screenshot": str(output_path),
    "import_screenshot_size": [window_pixmap.width(), window_pixmap.height()],
    "recovery_codes": recovery_codes,
    "recovery_has_errors": recovery_report.has_errors,
    "recovery_overlay_id": recovery_report.overlay_id,
    "recovery_overlay_started": recovery_report.overlay_started,
}

actionrail.hide_all()
app.processEvents()

print(json.dumps(result, sort_keys=True))
