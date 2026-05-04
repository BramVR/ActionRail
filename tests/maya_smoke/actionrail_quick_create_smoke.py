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
        "actionrail_quick_create_panel.png",
    )
)
output_path.parent.mkdir(parents=True, exist_ok=True)

from maya import cmds  # noqa: E402
from PySide6 import QtWidgets  # noqa: E402

import actionrail  # noqa: E402
from actionrail import maya_ui  # noqa: E402
from actionrail.quick_create_ui import (  # noqa: E402
    PANEL_OBJECT_NAME,
    STATUS_OBJECT_NAME,
    TABS_OBJECT_NAME,
    TEMPLATE_COMBO_OBJECT_NAME,
)

app = QtWidgets.QApplication.instance()
if app is None:
    raise RuntimeError("Maya QApplication is not available.")

if cmds.workspaceControl(maya_ui.QUICK_CREATE_WORKSPACE_CONTROL, exists=True):
    cmds.deleteUI(maya_ui.QUICK_CREATE_WORKSPACE_CONTROL, control=True)

panel = actionrail.show_quick_create_panel()
app.processEvents()
cmds.refresh(force=True)
app.processEvents()

if panel is None or panel.objectName() != PANEL_OBJECT_NAME:
    raise AssertionError(f"Quick Create returned the wrong panel: {panel}")

visible_panel = next(
    (
        widget
        for widget in app.allWidgets()
        if widget.objectName() == PANEL_OBJECT_NAME and widget.isVisible()
    ),
    None,
)
if visible_panel is None:
    raise AssertionError("Quick Create panel did not become visible.")

status_label = visible_panel.findChild(QtWidgets.QLabel, STATUS_OBJECT_NAME)
template_combo = visible_panel.findChild(QtWidgets.QComboBox, TEMPLATE_COMBO_OBJECT_NAME)
tabs = visible_panel.findChild(QtWidgets.QTabWidget, TABS_OBJECT_NAME)
if status_label is None or template_combo is None or tabs is None:
    raise AssertionError("Quick Create panel is missing expected child widgets.")

if template_combo.count() != 3:
    raise AssertionError(f"Unexpected template count: {template_combo.count()}")
if "Valid draft:" not in status_label.text():
    raise AssertionError(f"Quick Create status did not validate the draft: {status_label.text()}")

current_draft = visible_panel._actionrail_current_draft()
if current_draft.id != "quick-vertical-stack":
    raise AssertionError(f"Unexpected default draft id: {current_draft.id}")
if len(current_draft.slots) != 4:
    raise AssertionError(f"Unexpected default slot count: {len(current_draft.slots)}")

template_combo.setCurrentIndex(1)
app.processEvents()
horizontal_draft = visible_panel._actionrail_current_draft()
if horizontal_draft.layout.orientation != "horizontal":
    raise AssertionError(f"Template switch did not update orientation: {horizontal_draft}")

tab_screenshots = {}
for index in range(tabs.count()):
    tabs.setCurrentIndex(index)
    app.processEvents()
    tab_name = tabs.tabText(index).lower().replace(" ", "_")
    tab_path = output_path.with_name(f"actionrail_quick_create_{tab_name}.png")
    tab_pixmap = visible_panel.grab()
    tab_saved = tab_pixmap.save(str(tab_path), "PNG")
    if not tab_saved or tab_pixmap.width() <= 0 or tab_pixmap.height() <= 0:
        raise AssertionError(f"Failed to save Quick Create {tab_name} screenshot: {tab_path}")
    tab_screenshots[tab_name] = {
        "path": str(tab_path),
        "saved": bool(tab_saved),
        "size": [tab_pixmap.width(), tab_pixmap.height()],
    }

pixmap = visible_panel.grab()
screenshot_saved = pixmap.save(str(output_path), "PNG")
if not screenshot_saved or pixmap.width() <= 0 or pixmap.height() <= 0:
    raise AssertionError(f"Failed to save Quick Create screenshot: {output_path}")

result = {
    "current_template": template_combo.currentText(),
    "default_slot_count": len(current_draft.slots),
    "horizontal_orientation": horizontal_draft.layout.orientation,
    "panel_visible": bool(visible_panel.isVisible()),
    "quick_create_menu_command": maya_ui.show_quick_create_panel_command(),
    "screenshot": str(output_path),
    "screenshot_saved": bool(screenshot_saved),
    "screenshot_size": [pixmap.width(), pixmap.height()],
    "status_text": status_label.text(),
    "tab_screenshots": tab_screenshots,
    "template_count": template_combo.count(),
}

visible_panel.close()
app.processEvents()
if cmds.workspaceControl(maya_ui.QUICK_CREATE_WORKSPACE_CONTROL, exists=True):
    cmds.deleteUI(maya_ui.QUICK_CREATE_WORKSPACE_CONTROL, control=True)

print(json.dumps(result, sort_keys=True))
