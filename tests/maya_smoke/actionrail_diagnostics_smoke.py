from __future__ import annotations

import json
import sys

__args__ = globals().get("__args__", {})

repo_scripts = __args__.get("repo_scripts")
if repo_scripts and repo_scripts not in sys.path:
    sys.path.insert(0, repo_scripts)

from maya import cmds  # noqa: E402
from PySide6 import QtWidgets  # noqa: E402

import actionrail  # noqa: E402
from actionrail.diagnostics import diagnose_spec  # noqa: E402
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
    "widget_size": widget_size,
}

actionrail.hide_all()
app.processEvents()

print(json.dumps(result, sort_keys=True))
