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
        "actionrail_edit_mode_layout_map.png",
    )
)
output_path.parent.mkdir(parents=True, exist_ok=True)

from maya import cmds  # noqa: E402
from PySide6 import QtCore, QtTest, QtWidgets  # noqa: E402

import actionrail  # noqa: E402
from actionrail import edit_mode  # noqa: E402

app = QtWidgets.QApplication.instance()
if app is None:
    raise RuntimeError("Maya QApplication is not available.")

actionrail.hide_all()
actionrail.exit_edit_mode()
app.processEvents()

custom_spec = actionrail.StackSpec(
    id="edit_mode_custom",
    layout=actionrail.RailLayout(
        anchor="viewport.bottom.center",
        orientation="horizontal",
        rows=1,
        columns=3,
        offset=(0, -120),
        locked=False,
    ),
    items=(
        actionrail.StackItem(
            type="button",
            id="edit_mode_custom.move",
            label="Move",
            action="maya.tool.move",
        ),
        actionrail.StackItem(
            type="button",
            id="edit_mode_custom.rotate",
            label="Rot",
            action="maya.tool.rotate",
        ),
        actionrail.StackItem(
            type="button",
            id="edit_mode_custom.key",
            label="Key",
            action="maya.anim.set_key",
        ),
    ),
)
target_spec = actionrail.StackSpec(
    id="edit_mode_target",
    layout=actionrail.RailLayout(
        anchor="viewport.bottom.center",
        orientation="horizontal",
        rows=1,
        columns=2,
        offset=(180, -120),
        locked=False,
    ),
    items=(
        actionrail.StackItem(
            type="button",
            id="edit_mode_target.one",
            label="One",
            action="maya.tool.move",
        ),
        actionrail.StackItem(
            type="button",
            id="edit_mode_target.two",
            label="Two",
            action="maya.tool.rotate",
        ),
    ),
)

actionrail.show_preset("transform_stack")
actionrail.show_spec(custom_spec)
actionrail.show_spec(target_spec)
app.processEvents()
cmds.refresh(force=True)
app.processEvents()

state = actionrail.enter_edit_mode(
    settings=actionrail.EditModeSettings(
        show_grid=True,
        snap_to_grid=True,
        sticky_frames=True,
        grid_size=64,
    )
)
app.processEvents()
cmds.refresh(force=True)
app.processEvents()

if not state.enabled or state.rail_count < 3:
    raise AssertionError(f"Edit Mode did not see active rails: {state}")

edit_widget = next(
    (
        widget
        for widget in app.allWidgets()
        if widget.objectName() == edit_mode.EDIT_OVERLAY_OBJECT_NAME and widget.isVisible()
    ),
    None,
)
if edit_widget is None:
    raise AssertionError("Edit Mode overlay widget is not visible.")

panel = edit_widget.findChild(QtWidgets.QFrame, edit_mode.EDIT_PANEL_OBJECT_NAME)
if panel is None or not panel.isVisible():
    raise AssertionError("Edit Mode control panel is not visible.")

host = edit_mode._EDIT_HOST
if host is None:
    raise AssertionError("Edit Mode host was not created.")

custom_frame = next(
    (frame for frame in host.frames if frame.preset_id == "edit_mode_custom"),
    None,
)
if custom_frame is None:
    raise AssertionError(f"Custom rail frame was not present: {host.frames}")
target_frame = next(
    (frame for frame in host.frames if frame.preset_id == "edit_mode_target"),
    None,
)
if target_frame is None:
    raise AssertionError(f"Target rail frame was not present: {host.frames}")

click_point = QtCore.QPoint(custom_frame.x + 4, custom_frame.y + 4)
QtTest.QTest.mouseClick(edit_widget, QtCore.Qt.LeftButton, QtCore.Qt.NoModifier, click_point)
app.processEvents()

state_after_left_click = actionrail.edit_mode_state()
if state_after_left_click.selected_preset_id != "edit_mode_custom":
    raise AssertionError(f"Left click did not select custom rail: {state_after_left_click}")

popover = edit_widget.findChild(QtWidgets.QFrame, edit_mode.POSITION_POPOVER_OBJECT_NAME)
if popover is None or not popover.isVisible():
    raise AssertionError("Selected rail position popover did not open.")

spinboxes = popover.findChildren(QtWidgets.QSpinBox)
if len(spinboxes) < 2:
    raise AssertionError("Position popover is missing X/Y spin boxes.")

old_x = custom_frame.x
spinboxes[0].setValue(old_x + 5)
app.processEvents()
cmds.refresh(force=True)
app.processEvents()

custom_frame_after_nudge = next(
    frame for frame in host.frames if frame.preset_id == "edit_mode_custom"
)
if custom_frame_after_nudge.x != old_x + 5:
    raise AssertionError(
        f"X coordinate control did not move frame: {old_x} -> {custom_frame_after_nudge.x}"
    )

actionrail.set_edit_mode_options(snap_to_grid=False, sticky_frames=True)
app.processEvents()
host.set_selected_position(
    target_frame.x - custom_frame_after_nudge.width + 5,
    custom_frame_after_nudge.y,
    apply_snapping=True,
)
app.processEvents()
custom_frame_after_sticky = next(
    frame for frame in host.frames if frame.preset_id == "edit_mode_custom"
)
if custom_frame_after_sticky.right != target_frame.x:
    raise AssertionError(
        "Sticky Frames did not align the moved rail to the target rail: "
        f"{custom_frame_after_sticky.right} != {target_frame.x}"
    )

right_click_point = QtCore.QPoint(
    custom_frame_after_sticky.x + 4,
    custom_frame_after_sticky.y + 4,
)
QtTest.QTest.mouseClick(
    edit_widget,
    QtCore.Qt.RightButton,
    QtCore.Qt.NoModifier,
    right_click_point,
)
app.processEvents()

state_after_right_click = actionrail.edit_mode_state()
if state_after_right_click.options_preset_id != "edit_mode_custom":
    raise AssertionError(
        f"Right click did not route to frame options: {state_after_right_click}"
    )

pixmap = edit_widget.grab()
screenshot_saved = pixmap.save(str(output_path), "PNG")
if not screenshot_saved or pixmap.width() <= 0 or pixmap.height() <= 0:
    raise AssertionError(f"Failed to save Edit Mode screenshot: {output_path}")

result = {
    "edit_mode_enabled": actionrail.edit_mode_state().enabled,
    "grid_size": actionrail.edit_mode_state().settings.grid_size,
    "options_preset_id": actionrail.edit_mode_state().options_preset_id,
    "rail_count": len(host.frames),
    "screenshot": str(output_path),
    "screenshot_saved": bool(screenshot_saved),
    "screenshot_size": [pixmap.width(), pixmap.height()],
    "selected_preset_id": actionrail.edit_mode_state().selected_preset_id,
    "snap_to_grid": actionrail.edit_mode_state().settings.snap_to_grid,
    "sticky_aligned_right_edge": custom_frame_after_sticky.right,
    "sticky_target_left_edge": target_frame.x,
    "sticky_frames": actionrail.edit_mode_state().settings.sticky_frames,
}

actionrail.exit_edit_mode()
actionrail.hide_all()
app.processEvents()

print(json.dumps(result, sort_keys=True))
