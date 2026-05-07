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
        "actionrail_spell_book_panel.png",
    )
)
output_path.parent.mkdir(parents=True, exist_ok=True)

from maya import cmds  # noqa: E402
from PySide6 import QtCore, QtGui, QtWidgets  # noqa: E402

import actionrail  # noqa: E402
import actionrail.runtime as actionrail_runtime  # noqa: E402
from actionrail import maya_ui  # noqa: E402
from actionrail.action_book import (  # noqa: E402
    ACTION_BOOK_MIME_TYPE,
    action_book_entries,
    action_book_mime_text,
)
from actionrail.action_book_ui import (  # noqa: E402
    ENTRY_BUTTON_OBJECT_NAME_PREFIX,
    PANEL_OBJECT_NAME,
    SEARCH_OBJECT_NAME,
    STATUS_OBJECT_NAME,
)
from actionrail.quick_create import build_quick_create_draft, make_default_input  # noqa: E402

app = QtWidgets.QApplication.instance()
if app is None:
    raise RuntimeError("Maya QApplication is not available.")

cmds.file(new=True, force=True)
if cmds.workspaceControl(maya_ui.ACTION_BOOK_WORKSPACE_CONTROL, exists=True):
    cmds.deleteUI(maya_ui.ACTION_BOOK_WORKSPACE_CONTROL, control=True)

panel = actionrail.show_action_book_panel()
app.processEvents()
cmds.refresh(force=True)
app.processEvents()

if panel is None or panel.objectName() != PANEL_OBJECT_NAME:
    raise AssertionError(f"Spell Book returned the wrong panel: {panel}")

visible_panel = next(
    (
        widget
        for widget in app.allWidgets()
        if widget.objectName() == PANEL_OBJECT_NAME and widget.isVisible()
    ),
    None,
)
if visible_panel is None:
    raise AssertionError("Spell Book panel did not become visible.")

search = visible_panel.findChild(QtWidgets.QLineEdit, SEARCH_OBJECT_NAME)
status_label = visible_panel.findChild(QtWidgets.QLabel, STATUS_OBJECT_NAME)
if search is None or status_label is None:
    raise AssertionError("Spell Book panel is missing search or status widgets.")


def entry_buttons() -> list[QtWidgets.QToolButton]:
    return [
        button
        for button in visible_panel.findChildren(QtWidgets.QToolButton)
        if button.objectName().startswith(ENTRY_BUTTON_OBJECT_NAME_PREFIX)
    ]


def entry_button(action_id: str) -> QtWidgets.QToolButton:
    for button in entry_buttons():
        if button.property("actionRailActionBookActionId") == action_id:
            return button
    raise AssertionError(f"Spell Book entry button was not visible: {action_id}")


initial_entries = action_book_entries()
initial_buttons = entry_buttons()
if len(initial_entries) < 13 or len(initial_buttons) != len(initial_entries):
    raise AssertionError(
        "Spell Book did not render the current Action Book catalog: "
        f"entries={len(initial_entries)} buttons={len(initial_buttons)}"
    )

scale_button = entry_button("maya.tool.scale")
if scale_button.property("actionRailIcon") != "maya.scale":
    raise AssertionError(f"Scale entry does not use the Action Book icon: {scale_button.icon()}")
if "Scale" not in scale_button.text() or "scale" not in scale_button.toolTip().lower():
    raise AssertionError(f"Scale entry is missing label/description: {scale_button.text()!r}")
if scale_button.icon().isNull():
    raise AssertionError("Scale entry rendered with a null icon.")

pixmap = visible_panel.grab()
screenshot_saved = pixmap.save(str(output_path), "PNG")
if not screenshot_saved or pixmap.width() <= 0 or pixmap.height() <= 0:
    raise AssertionError(f"Failed to save Spell Book screenshot: {output_path}")

search.setText("scale")
app.processEvents()
cmds.refresh(force=True)
app.processEvents()
search_buttons = entry_buttons()
search_action_ids = [
    str(button.property("actionRailActionBookActionId")) for button in search_buttons
]
if "maya.tool.scale" not in search_action_ids or any(
    "scale" not in button.text().lower() and "scale" not in button.toolTip().lower()
    for button in search_buttons
):
    raise AssertionError(f"Spell Book search did not filter to scale matches: {search_action_ids}")

search_path = output_path.with_name("actionrail_spell_book_search_scale.png")
search_pixmap = visible_panel.grab()
search_screenshot_saved = search_pixmap.save(str(search_path), "PNG")
if not search_screenshot_saved or search_pixmap.width() <= 0 or search_pixmap.height() <= 0:
    raise AssertionError(f"Failed to save Spell Book search screenshot: {search_path}")

search.clear()
app.processEvents()
select_button = entry_button("maya.tool.select")
cmds.setToolTo("moveSuperContext")
select_button.click()
app.processEvents()
context_after_click = cmds.currentCtx()
if context_after_click != "selectSuperContext":
    raise AssertionError(f"Clicking Select did not run its Maya action: {context_after_click}")

draft = build_quick_create_draft(make_default_input())
host = actionrail.edit_quick_create_slots(draft)
app.processEvents()
cmds.refresh(force=True)
app.processEvents()
if host is None or not host.slot_edit_unlocked():
    raise AssertionError("Quick Create blank bar was not unlocked for Spell Book drop.")

slot_button = next(
    (
        button
        for button in host.widget.findChildren(QtWidgets.QPushButton)
        if button.property("actionRailSlotId") == "quick-blank-bar.slot_1"
    ),
    None,
)
if slot_button is None:
    raise AssertionError("Unlocked blank bar did not render slot_1.")

mime = QtCore.QMimeData()
payload = action_book_mime_text("maya.tool.scale")
mime.setData(ACTION_BOOK_MIME_TYPE, payload.encode("utf-8"))
mime.setText(payload)
point = slot_button.rect().center()
drag_event = QtGui.QDragEnterEvent(
    point,
    QtCore.Qt.CopyAction,
    mime,
    QtCore.Qt.LeftButton,
    QtCore.Qt.NoModifier,
)
QtWidgets.QApplication.sendEvent(slot_button, drag_event)
slot_button.dragEnterEvent(drag_event)
drop_event = QtGui.QDropEvent(
    QtCore.QPointF(point),
    QtCore.Qt.CopyAction,
    mime,
    QtCore.Qt.LeftButton,
    QtCore.Qt.NoModifier,
)
QtWidgets.QApplication.sendEvent(slot_button, drop_event)
slot_button.dropEvent(drop_event)
app.processEvents()
cmds.refresh(force=True)
app.processEvents()

updated_host = actionrail_runtime._OVERLAYS.get("quick-blank-bar")
if updated_host is None:
    raise AssertionError("Spell Book drop removed the Quick Create bar.")
assigned_item = updated_host.spec.items[0]
if assigned_item.action != "maya.tool.scale" or assigned_item.icon != "maya.scale":
    raise AssertionError(
        "Spell Book drop did not assign the scale payload with the catalog icon: "
        f"action={assigned_item.action} icon={assigned_item.icon}"
    )
updated_slot = next(
    (
        button
        for button in updated_host.widget.findChildren(QtWidgets.QPushButton)
        if button.property("actionRailSlotId") == "quick-blank-bar.slot_1"
    ),
    None,
)
if updated_slot is None or updated_slot.property("actionRailIcon") != "maya.scale":
    raise AssertionError("Assigned bar slot did not render the same scale icon.")

drop_path = output_path.with_name("actionrail_spell_book_drop_bar.png")
drop_pixmap = updated_host.widget.grab()
drop_screenshot_saved = drop_pixmap.save(str(drop_path), "PNG")
if not drop_screenshot_saved or drop_pixmap.width() <= 0 or drop_pixmap.height() <= 0:
    raise AssertionError(f"Failed to save Spell Book drop screenshot: {drop_path}")

result = {
    "action_count": len(initial_entries),
    "context_after_click": context_after_click,
    "drop_assigned_action": assigned_item.action,
    "drop_assigned_icon": assigned_item.icon,
    "drop_screenshot": str(drop_path),
    "drop_screenshot_saved": bool(drop_screenshot_saved),
    "initial_button_count": len(initial_buttons),
    "menu_command": maya_ui.show_action_book_panel_command(),
    "panel_visible": bool(visible_panel.isVisible()),
    "scale_entry_icon": scale_button.property("actionRailIcon"),
    "screenshot": str(output_path),
    "screenshot_saved": bool(screenshot_saved),
    "screenshot_size": [pixmap.width(), pixmap.height()],
    "search_action_ids": search_action_ids,
    "search_screenshot": str(search_path),
    "search_screenshot_saved": bool(search_screenshot_saved),
    "status_text": status_label.text(),
}

visible_panel.close()
actionrail.hide_all()
app.processEvents()
if cmds.workspaceControl(maya_ui.ACTION_BOOK_WORKSPACE_CONTROL, exists=True):
    cmds.deleteUI(maya_ui.ACTION_BOOK_WORKSPACE_CONTROL, control=True)

print(json.dumps(result, sort_keys=True))
