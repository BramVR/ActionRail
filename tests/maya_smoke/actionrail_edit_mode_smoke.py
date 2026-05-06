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
            key_label="1",
        ),
        actionrail.StackItem(
            type="button",
            id="edit_mode_custom.rotate",
            label="Rot",
            action="maya.tool.rotate",
            key_label="2",
        ),
        actionrail.StackItem(
            type="button",
            id="edit_mode_custom.key",
            label="Key",
            action="maya.anim.set_key",
            key_label="3",
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
            key_label="4",
        ),
        actionrail.StackItem(
            type="button",
            id="edit_mode_target.two",
            label="Two",
            action="maya.tool.rotate",
            key_label="5",
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

grid_check = next(
    (checkbox for checkbox in panel.findChildren(QtWidgets.QCheckBox) if checkbox.text() == "Grid"),
    None,
)
grid_size_spin = panel.findChild(QtWidgets.QSpinBox)
lock_button = panel.findChild(QtWidgets.QPushButton)
if grid_check is None or grid_size_spin is None or lock_button is None:
    raise AssertionError("Edit Mode panel is missing expected grid or lock controls.")
if lock_button.text() != "No selection":
    raise AssertionError(f"Expected neutral lock text before selection, got {lock_button.text()!r}")
grid_check.setChecked(False)
app.processEvents()
if grid_size_spin.isEnabled():
    raise AssertionError("Grid Size remained enabled while Grid was unchecked.")
grid_check.setChecked(True)
app.processEvents()

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

slot_drag_start = QtCore.QPoint(
    custom_frame.x + custom_frame.width // 2,
    custom_frame.y + custom_frame.height // 2,
)
slot_drag_end = QtCore.QPoint(slot_drag_start.x() + 48, slot_drag_start.y())
QtTest.QTest.mousePress(
    edit_widget,
    QtCore.Qt.LeftButton,
    QtCore.Qt.NoModifier,
    slot_drag_start,
)
QtTest.QTest.mouseMove(edit_widget, slot_drag_end)
QtTest.QTest.mouseRelease(
    edit_widget,
    QtCore.Qt.LeftButton,
    QtCore.Qt.NoModifier,
    slot_drag_end,
)
app.processEvents()
cmds.refresh(force=True)
app.processEvents()
custom_frame_after_slot_drag = next(
    frame for frame in host.frames if frame.preset_id == "edit_mode_custom"
)
state_after_slot_drag = actionrail.edit_mode_state()
if state_after_slot_drag.selected_preset_id != "edit_mode_custom":
    raise AssertionError(f"Frame drag did not select the dragged rail: {state_after_slot_drag}")
if custom_frame_after_slot_drag.x == custom_frame.x:
    raise AssertionError(
        "Dragging inside an unlocked rail frame did not move the whole rail."
    )
custom_frame = custom_frame_after_slot_drag

click_point = QtCore.QPoint(custom_frame.x + custom_frame.width // 2, custom_frame.y + 8)
state_after_left_click = actionrail.edit_mode_state()
for _attempt in range(3):
    QtTest.QTest.mouseClick(edit_widget, QtCore.Qt.LeftButton, QtCore.Qt.NoModifier, click_point)
    app.processEvents()
    cmds.refresh(force=True)
    app.processEvents()
    state_after_left_click = actionrail.edit_mode_state()
    if state_after_left_click.selected_preset_id == "edit_mode_custom":
        break
if state_after_left_click.selected_preset_id != "edit_mode_custom":
    raise AssertionError(f"Left click did not select custom rail: {state_after_left_click}")

popover = edit_widget.findChild(QtWidgets.QFrame, edit_mode.POSITION_POPOVER_OBJECT_NAME)
if popover is None or not popover.isVisible():
    raise AssertionError("Selected rail position popover did not open.")

removed_options = edit_widget.findChild(QtWidgets.QFrame, "ActionRailEditModeFrameOptionsPopover")
if removed_options is not None:
    raise AssertionError("Removed Edit Mode frame options popover was still created.")
if edit_widget.findChild(QtWidgets.QListWidget) is not None:
    raise AssertionError("Edit Mode still exposes the removed action palette.")

spinboxes = popover.findChildren(QtWidgets.QSpinBox)
if len(spinboxes) < 2:
    raise AssertionError("Position popover is missing X/Y spin boxes.")

old_x = custom_frame.x
old_y = custom_frame.y
actionrail.set_edit_mode_options(snap_to_grid=True, sticky_frames=False)
app.processEvents()
spinboxes[0].setValue(old_x + 5)
app.processEvents()
cmds.refresh(force=True)
app.processEvents()

custom_frame_after_nudge = next(
    frame for frame in host.frames if frame.preset_id == "edit_mode_custom"
)
expected_snap_x = edit_mode._snap_value_to_grid(old_x + 5, 64)
if custom_frame_after_nudge.x != expected_snap_x:
    raise AssertionError(
        "X coordinate control did not honor Snap to Grid: "
        f"{old_x} -> {custom_frame_after_nudge.x}, expected {expected_snap_x}"
    )
if custom_frame_after_nudge.y != old_y:
    raise AssertionError(
        "X coordinate control changed Y while Snap to Grid was enabled: "
        f"{old_y} -> {custom_frame_after_nudge.y}"
    )

right_button = next(
    (button for button in popover.findChildren(QtWidgets.QToolButton) if button.text() == ">"),
    None,
)
if right_button is None:
    raise AssertionError("Position popover is missing right nudge button.")
QtTest.QTest.mouseClick(right_button, QtCore.Qt.LeftButton)
app.processEvents()
cmds.refresh(force=True)
app.processEvents()
custom_frame_after_arrow = next(
    frame for frame in host.frames if frame.preset_id == "edit_mode_custom"
)
if custom_frame_after_arrow.x != expected_snap_x + 64:
    raise AssertionError(
        "Right-arrow nudge did not move by one grid cell with Snap to Grid enabled: "
        f"{custom_frame_after_arrow.x} != {expected_snap_x + 64}"
    )
if custom_frame_after_arrow.y != old_y:
    raise AssertionError(
        "Right-arrow nudge changed Y while Snap to Grid was enabled: "
        f"{old_y} -> {custom_frame_after_arrow.y}"
    )

actionrail.set_edit_mode_options(snap_to_grid=False, sticky_frames=True)
app.processEvents()
host.set_selected_position(
    target_frame.x - custom_frame_after_arrow.width + 5,
    custom_frame_after_arrow.y,
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

actionrail.set_edit_mode_options(snap_to_grid=True, sticky_frames=True)
app.processEvents()
host.set_selected_position(
    target_frame.x - custom_frame_after_sticky.width + 5,
    custom_frame_after_sticky.y + 5,
    apply_snapping=True,
)
app.processEvents()
custom_frame_after_snap_sticky = next(
    frame for frame in host.frames if frame.preset_id == "edit_mode_custom"
)
if custom_frame_after_snap_sticky.x % 64 or custom_frame_after_snap_sticky.y % 64:
    raise AssertionError(
        "Sticky Frames left the rail off-grid while Snap to Grid was enabled: "
        f"{custom_frame_after_snap_sticky.x}, {custom_frame_after_snap_sticky.y}"
    )

save_dir = output_path.parent.parent / "user_presets"
saved_path = actionrail.save_edit_mode_layout(user_preset_dir=save_dir)
saved_spec = actionrail.load_user_preset("edit_mode_custom", preset_dir=save_dir)
if saved_spec.layout.offset != custom_frame_after_snap_sticky.offset:
    raise AssertionError(
        "Edit Mode layout save did not persist the adjusted offset: "
        f"{saved_spec.layout.offset} != {custom_frame_after_snap_sticky.offset}"
    )

custom_runtime_host = edit_mode._runtime_hosts().get("edit_mode_custom")
if custom_runtime_host is None:
    raise AssertionError("Custom runtime host disappeared before collapse verification.")
if not host.toggle_selected_edge_tab():
    raise AssertionError("Edit Mode failed to collapse the selected edge-tab rail.")
app.processEvents()
cmds.refresh(force=True)
app.processEvents()
if not getattr(custom_runtime_host, "_collapsed", False):
    raise AssertionError("Runtime host did not enter collapsed state.")
if not custom_runtime_host.spec.collapse.default_collapsed:
    raise AssertionError("Collapsed state was not written to the runtime spec default.")
collapsed_widget = custom_runtime_host.widget
collapsed_handle_size = sorted((collapsed_widget.width(), collapsed_widget.height()))
if collapsed_handle_size[0] > 28 or collapsed_handle_size[1] > 56:
    raise AssertionError(
        "Collapsed edge handle is too large: "
        f"{collapsed_widget.width()}x{collapsed_widget.height()}"
    )
collapsed_save_path = actionrail.save_edit_mode_layout(user_preset_dir=save_dir)
collapsed_saved_spec = actionrail.load_user_preset("edit_mode_custom", preset_dir=save_dir)
if not collapsed_saved_spec.collapse.default_collapsed:
    raise AssertionError("Edit Mode save did not persist collapsed edge-tab state.")
actionrail.run_slot("edit_mode_custom", "move", user_preset_dir=save_dir)
if cmds.currentCtx() != "moveSuperContext":
    raise AssertionError("Collapsed rail slot action did not remain executable.")
handle = collapsed_widget.findChild(QtWidgets.QPushButton)
if handle is None or handle.property("actionRailCollapsedPresetId") != "edit_mode_custom":
    raise AssertionError("Collapsed edge handle button was not rendered.")
QtTest.QTest.mouseClick(handle, QtCore.Qt.LeftButton)
app.processEvents()
cmds.refresh(force=True)
app.processEvents()
if getattr(custom_runtime_host, "_collapsed", True):
    raise AssertionError("Clicking the collapsed edge handle did not expand the rail.")

pixmap = edit_widget.grab()
screenshot_saved = pixmap.save(str(output_path), "PNG")
if not screenshot_saved or pixmap.width() <= 0 or pixmap.height() <= 0:
    raise AssertionError(f"Failed to save Edit Mode screenshot: {output_path}")

result = {
    "edit_mode_enabled": actionrail.edit_mode_state().enabled,
    "grid_size": actionrail.edit_mode_state().settings.grid_size,
    "rail_count": len(host.frames),
    "saved_layout_offset": list(saved_spec.layout.offset),
    "saved_layout_path": str(saved_path),
    "collapsed_layout_path": str(collapsed_save_path),
    "collapsed_saved": bool(collapsed_saved_spec.collapse.default_collapsed),
    "screenshot": str(output_path),
    "screenshot_saved": bool(screenshot_saved),
    "screenshot_size": [pixmap.width(), pixmap.height()],
    "selected_preset_id": actionrail.edit_mode_state().selected_preset_id,
    "snap_to_grid": actionrail.edit_mode_state().settings.snap_to_grid,
    "sticky_aligned_right_edge": custom_frame_after_sticky.right,
    "sticky_grid_position": [
        custom_frame_after_snap_sticky.x,
        custom_frame_after_snap_sticky.y,
    ],
    "sticky_target_left_edge": target_frame.x,
    "sticky_frames": actionrail.edit_mode_state().settings.sticky_frames,
}

actionrail.exit_edit_mode()
actionrail.hide_all()
app.processEvents()

print(json.dumps(result, sort_keys=True))
