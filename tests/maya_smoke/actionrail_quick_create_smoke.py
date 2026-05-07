from __future__ import annotations

import json
import os
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
user_preset_dir = output_path.parent / "quick_create_user_presets"
user_preset_dir.mkdir(parents=True, exist_ok=True)
os.environ["ACTIONRAIL_USER_PRESET_DIR"] = str(user_preset_dir)
saved_path = user_preset_dir / "quick-horizontal-strip.json"
if saved_path.exists():
    saved_path.unlink()

from maya import cmds  # noqa: E402
from PySide6 import QtWidgets  # noqa: E402

import actionrail  # noqa: E402
import actionrail.runtime as actionrail_runtime  # noqa: E402
from actionrail import maya_ui  # noqa: E402
from actionrail.quick_create_ui import (  # noqa: E402
    BUTTON_COUNT_OBJECT_NAME,
    BUTTON_SIZE_OBJECT_NAME,
    BUTTONS_PER_ROW_OBJECT_NAME,
    EDIT_LAYOUT_BUTTON_OBJECT_NAME,
    PANEL_OBJECT_NAME,
    PUBLISH_BUTTON_OBJECT_NAME,
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
publish_button = visible_panel.findChild(QtWidgets.QPushButton, PUBLISH_BUTTON_OBJECT_NAME)
edit_layout_button = visible_panel.findChild(
    QtWidgets.QPushButton,
    EDIT_LAYOUT_BUTTON_OBJECT_NAME,
)
tabs = visible_panel.findChild(QtWidgets.QTabWidget, TABS_OBJECT_NAME)
preset_id_edit = visible_panel.findChild(QtWidgets.QLineEdit, "ActionRailQuickCreatePresetId")
button_count = visible_panel.findChild(QtWidgets.QSpinBox, BUTTON_COUNT_OBJECT_NAME)
buttons_per_row = visible_panel.findChild(QtWidgets.QSpinBox, BUTTONS_PER_ROW_OBJECT_NAME)
button_size = visible_panel.findChild(QtWidgets.QDoubleSpinBox, BUTTON_SIZE_OBJECT_NAME)
if (
    status_label is None
    or template_combo is None
    or publish_button is None
    or edit_layout_button is None
    or tabs is None
    or preset_id_edit is None
    or button_count is None
    or buttons_per_row is None
    or button_size is None
):
    raise AssertionError("Quick Create panel is missing expected child widgets.")

if template_combo.count() != 3:
    raise AssertionError(f"Unexpected template count: {template_combo.count()}")
if "Valid draft:" not in status_label.text():
    raise AssertionError(f"Quick Create status did not validate the draft: {status_label.text()}")

workspace_parent = visible_panel.parentWidget()
if workspace_parent is not None:
    workspace_parent.resize(1040, 760)
    app.processEvents()
    parent_rect = workspace_parent.rect()
    if (
        visible_panel.geometry().width() != parent_rect.width()
        or visible_panel.geometry().height() != parent_rect.height()
    ):
        raise AssertionError(
            "Quick Create panel did not resize with workspace parent: "
            f"panel={visible_panel.geometry().getRect()} "
            f"parent={parent_rect.getRect()}"
        )

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

visible_panel._actionrail_preview_draft()
app.processEvents()
cmds.refresh(force=True)
app.processEvents()
if "quick-horizontal-strip" not in actionrail.active_overlay_ids():
    raise AssertionError(
        f"Quick Create preview did not show overlay: {actionrail.active_overlay_ids()}"
    )

visible_panel._actionrail_edit_layout()
app.processEvents()
cmds.refresh(force=True)
app.processEvents()
edit_state = actionrail.edit_mode_state()
if not edit_state.enabled or edit_state.selected_preset_id != "quick-horizontal-strip":
    raise AssertionError(f"Quick Create Edit Layout did not select preview: {edit_state}")
edit_overlay = next(
    (
        widget
        for widget in app.allWidgets()
        if widget.objectName() == "ActionRailEditModeOverlay" and widget.isVisible()
    ),
    None,
)
if edit_overlay is None:
    raise AssertionError("Quick Create Edit Layout did not show Edit Mode overlay.")
edit_screenshot_path = output_path.with_name("actionrail_quick_create_edit_layout.png")
edit_pixmap = edit_overlay.grab()
edit_screenshot_saved = edit_pixmap.save(str(edit_screenshot_path), "PNG")
if not edit_screenshot_saved or edit_pixmap.width() <= 0 or edit_pixmap.height() <= 0:
    raise AssertionError(
        f"Failed to save Quick Create Edit Layout screenshot: {edit_screenshot_path}"
    )
actionrail.exit_edit_mode()
app.processEvents()
cmds.refresh(force=True)
app.processEvents()
if "Editing layout: quick-horizontal-strip" not in status_label.text():
    raise AssertionError(f"Quick Create Edit Layout did not report status: {status_label.text()}")

button_count.setValue(10)
buttons_per_row.setValue(5)
button_size.setValue(1.25)
app.processEvents()
cmds.refresh(force=True)
app.processEvents()
live_draft = visible_panel._actionrail_current_draft()
if len(live_draft.slots) != 10:
    raise AssertionError(f"Live Buttons slider did not create 10 slots: {live_draft.slots}")
if live_draft.layout.rows != 2 or live_draft.layout.columns != 5:
    raise AssertionError(f"Live Buttons Per Row did not wrap 10 slots as 2x5: {live_draft}")
if live_draft.layout.scale != 1.25:
    raise AssertionError(f"Live Button Size did not update draft scale: {live_draft.layout.scale}")
host = actionrail_runtime._OVERLAYS.get("quick-horizontal-strip")
if host is None:
    raise AssertionError("Live preview refresh removed the Quick Create overlay.")
if host.spec.layout.rows != 2 or host.spec.layout.columns != 5 or host.spec.layout.scale != 1.25:
    raise AssertionError(f"Live preview host did not receive updated layout: {host.spec.layout}")
preview_buttons = host.widget.findChildren(QtWidgets.QPushButton)
slot_buttons = [
    button for button in preview_buttons if button.property("actionRailSlotId")
]
if len(slot_buttons) != 10:
    raise AssertionError(f"Live preview did not render 10 slot buttons: {len(slot_buttons)}")
icons = [button.property("actionRailIcon") for button in slot_buttons]
if icons[:4] != ["maya.move", "maya.rotate", "maya.scale", "maya.set_key"] or any(icons[4:]):
    raise AssertionError(
        f"Generated Quick Create slots did not preserve icons then blanks: {icons}"
    )

visible_panel._actionrail_save_draft()
app.processEvents()
cmds.refresh(force=True)
app.processEvents()
if not saved_path.is_file():
    raise AssertionError(f"Quick Create save did not write preset: {saved_path}")
if actionrail.active_overlay_ids() != ("quick-horizontal-strip",):
    raise AssertionError(
        f"Quick Create save did not show saved preset: {actionrail.active_overlay_ids()}"
    )

visible_panel._actionrail_save_draft()
app.processEvents()
if "overwrite=True" not in status_label.text():
    raise AssertionError(
        f"Duplicate Quick Create save did not require explicit overwrite: {status_label.text()}"
    )

visible_panel._actionrail_save_draft(overwrite=True)
app.processEvents()
if "Saved and showing user preset: quick-horizontal-strip" not in status_label.text():
    raise AssertionError(f"Explicit overwrite did not save preset: {status_label.text()}")

template_combo.setCurrentIndex(0)
app.processEvents()
preset_id_edit.setText("quick-horizontal-strip")
app.processEvents()
visible_panel._actionrail_load_existing()
app.processEvents()
loaded_draft = visible_panel._actionrail_current_draft()
if loaded_draft.id != "quick-horizontal-strip" or loaded_draft.layout.orientation != "horizontal":
    raise AssertionError(f"Load Existing did not restore saved bar: {loaded_draft}")

visible_panel._actionrail_save_publish_draft()
app.processEvents()
cmds.refresh(force=True)
app.processEvents()
published_runtime = "ActionRail_slot_quick_horizontal_strip_move"
published_shelf = "ActionRailTogglePresetShelfButton_quick_horizontal_strip"
if not cmds.runTimeCommand(published_runtime, exists=True):
    raise AssertionError(f"Save + Publish did not create runtime command: {published_runtime}")
if not cmds.shelfButton(published_shelf, exists=True):
    raise AssertionError(f"Save + Publish did not create shelf button: {published_shelf}")
shelf_command = str(cmds.shelfButton(published_shelf, query=True, command=True))
escaped_user_preset_dir = str(user_preset_dir).replace("\\", "\\\\")
if escaped_user_preset_dir not in shelf_command:
    raise AssertionError(
        "Save + Publish shelf button did not preserve custom user preset dir: "
        f"{shelf_command}"
    )
if "Published" not in status_label.text():
    raise AssertionError(f"Save + Publish did not report publish status: {status_label.text()}")

actionrail.reload("quick-horizontal-strip")
app.processEvents()
cmds.refresh(force=True)
app.processEvents()
if actionrail.active_overlay_ids() != ("quick-horizontal-strip",):
    raise AssertionError(
        f"Saved Quick Create preset did not survive ActionRail reload: "
        f"{actionrail.active_overlay_ids()}"
    )

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
    "live_preview_icons": icons,
    "live_preview_layout": [live_draft.layout.rows, live_draft.layout.columns],
    "live_preview_scale": live_draft.layout.scale,
    "live_preview_slot_count": len(live_draft.slots),
    "loaded_orientation": loaded_draft.layout.orientation,
    "panel_visible": bool(visible_panel.isVisible()),
    "parent_resize_synced": workspace_parent is not None,
    "edit_layout_selected": edit_state.selected_preset_id,
    "edit_layout_screenshot": str(edit_screenshot_path),
    "edit_layout_screenshot_saved": bool(edit_screenshot_saved),
    "quick_create_menu_command": maya_ui.show_quick_create_panel_command(),
    "published_runtime_exists": cmds.runTimeCommand(published_runtime, exists=True),
    "published_shelf_command": shelf_command,
    "published_shelf_exists": cmds.shelfButton(published_shelf, exists=True),
    "saved_preset": str(saved_path),
    "saved_preset_exists": saved_path.is_file(),
    "screenshot": str(output_path),
    "screenshot_saved": bool(screenshot_saved),
    "screenshot_size": [pixmap.width(), pixmap.height()],
    "status_text": status_label.text(),
    "tab_screenshots": tab_screenshots,
    "template_count": template_combo.count(),
}

visible_panel.close()
actionrail.hide_all()
app.processEvents()
if cmds.workspaceControl(maya_ui.QUICK_CREATE_WORKSPACE_CONTROL, exists=True):
    cmds.deleteUI(maya_ui.QUICK_CREATE_WORKSPACE_CONTROL, control=True)
if cmds.shelfButton(published_shelf, exists=True):
    cmds.deleteUI(published_shelf, control=True)

print(json.dumps(result, sort_keys=True))
