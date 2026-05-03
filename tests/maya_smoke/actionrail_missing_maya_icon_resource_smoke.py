from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

__args__ = globals().get("__args__", {})

repo_scripts = __args__.get("repo_scripts")
if repo_scripts and repo_scripts not in sys.path:
    sys.path.insert(0, repo_scripts)

from maya import cmds  # noqa: E402
from PySide6 import QtWidgets  # noqa: E402

import actionrail  # noqa: E402
import actionrail.icons as icons  # noqa: E402

app = QtWidgets.QApplication.instance()
if app is None:
    raise RuntimeError("Maya QApplication is not available.")

output_path = Path(
    __args__.get(
        "output_path",
        "C:/PROJECTS/GG/ScreenUI/.gg-maya-sessiond/screenshots/"
        "actionrail_missing_maya_icon_resource.png",
    )
)
output_path.parent.mkdir(parents=True, exist_ok=True)

missing_qt_name = "actionrail_missing_maya_icon_resource_DO_NOT_CREATE.png"
original_descriptor = icons._MAYA_ICON_BY_ID["maya.move"]
icons._MAYA_ICON_BY_ID["maya.move"] = replace(
    original_descriptor,
    qt_name=missing_qt_name,
    url=f"maya-resource://{missing_qt_name}",
)

result = {}
try:
    cmds.file(new=True, force=True)
    cmds.polyCube(name="actionrailMissingMayaIconResourceCube")
    cmds.refresh(force=True)

    spec = actionrail.StackSpec(
        id="missing_maya_icon_resource_smoke",
        layout=actionrail.RailLayout(
            anchor="viewport.bottom.center",
            orientation="horizontal",
            offset=(0, -24),
        ),
        items=(
            actionrail.StackItem(
                type="toolButton",
                id="missing_maya_icon_resource.move",
                label="M",
                icon="maya.move",
                action="maya.tool.move",
            ),
        ),
    )

    diagnostics = actionrail.diagnose_spec(spec, cmds_module=cmds)
    warning_codes = [issue.code for issue in diagnostics.warnings]
    if warning_codes != ["missing_maya_icon_resource"] or diagnostics.errors:
        raise AssertionError(f"Unexpected diagnostics: {diagnostics.as_dict()}")

    host = actionrail.show_spec(spec)
    app.processEvents()
    cmds.refresh(force=True)
    app.processEvents()

    widget = host.widget
    buttons = widget.findChildren(QtWidgets.QPushButton)
    if len(buttons) != 1:
        raise AssertionError(f"Expected one rendered button, got {len(buttons)}")

    button = buttons[0]
    pixmap = widget.grab()
    screenshot_saved = pixmap.save(str(output_path), "PNG")

    result = {
        "button_count": len(buttons),
        "diagnostics": diagnostics.as_dict(),
        "icon_id": button.property("actionRailIcon"),
        "icon_name": button.property("actionRailIconName"),
        "icon_path": button.property("actionRailIconPath"),
        "icon_is_null": bool(button.icon().isNull()),
        "diagnostic_code": button.property("actionRailDiagnosticCode"),
        "diagnostic_severity": button.property("actionRailDiagnosticSeverity"),
        "panel": host.panel,
        "screenshot": str(output_path),
        "screenshot_saved": bool(screenshot_saved),
        "screenshot_size": [pixmap.width(), pixmap.height()],
        "text": button.text(),
        "visible": bool(widget.isVisible()),
        "widget_size": [widget.width(), widget.height()],
    }

    if result["diagnostic_code"] != "missing_maya_icon_resource":
        raise AssertionError(f"Rendered button missed Maya icon diagnostic: {result}")
    if result["diagnostic_severity"] != "warning":
        raise AssertionError(f"Rendered button diagnostic severity is wrong: {result}")
    if result["icon_name"] or result["icon_path"] or result["icon_is_null"] is not True:
        raise AssertionError(f"Rendered button still looks icon-healthy: {result}")
    if result["text"] != "M\n?":
        raise AssertionError(f"Rendered button did not show warning badge: {result}")
    if not screenshot_saved or pixmap.width() <= 0 or pixmap.height() <= 0:
        raise AssertionError(f"Failed to save missing Maya icon screenshot: {result}")
finally:
    icons._MAYA_ICON_BY_ID["maya.move"] = original_descriptor
    if __args__.get("cleanup", True):
        actionrail.hide_all()
        app.processEvents()

print(json.dumps(result, sort_keys=True))
