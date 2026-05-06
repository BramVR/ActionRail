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

right_click_point = QtCore.QPoint(
    custom_frame_after_snap_sticky.x + 4,
    custom_frame_after_snap_sticky.y + 4,
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

options_popover = edit_widget.findChild(
    QtWidgets.QFrame,
    edit_mode.FRAME_OPTIONS_POPOVER_OBJECT_NAME,
)
if options_popover is None or not options_popover.isVisible():
    raise AssertionError("Right click did not open the frame options popover.")

action_list = options_popover.findChild(QtWidgets.QListWidget)
if action_list is None or action_list.count() <= 0:
    raise AssertionError("Frame options popover did not expose the action palette.")
if not action_list.isEnabled():
    raise AssertionError("Action palette was disabled for an unlocked rail.")

retired_slot_controls = {"Add Slot", "Remove Slot", "Move Up", "Move Down"}
visible_button_texts = {
    button.text()
    for button in options_popover.findChildren(QtWidgets.QPushButton)
    if button.isVisible()
}
if retired_slot_controls & visible_button_texts:
    raise AssertionError(
        "Frame options popover still exposes retired slot reorder controls: "
        f"{sorted(retired_slot_controls & visible_button_texts)}"
    )

custom_key_slot_id = "edit_mode_custom.key"
custom_rotate_slot_id = "edit_mode_custom.rotate"
target_one_slot_id = "edit_mode_target.one"

host.open_options("edit_mode_custom", custom_key_slot_id)
app.processEvents()
state_after_slot_select = actionrail.edit_mode_state()
if state_after_slot_select.selected_slot_id != custom_key_slot_id:
    raise AssertionError(f"Slot selection did not track the chosen slot: {state_after_slot_select}")
slot_status_texts = {
    label.text()
    for label in options_popover.findChildren(QtWidgets.QLabel)
    if label.isVisible()
}
if "Selected slot: Key (key)." not in slot_status_texts:
    raise AssertionError(f"Selected slot status was not rendered: {slot_status_texts}")


def _runtime_item(preset_id: str, slot_id: str) -> actionrail.StackItem:
    runtime_host = edit_mode._runtime_hosts().get(preset_id)
    if runtime_host is None:
        raise AssertionError(f"Runtime host is missing: {preset_id}")
    for item in runtime_host.spec.items:
        if item.id == slot_id:
            return item
    raise AssertionError(f"Runtime slot is missing: {preset_id}/{slot_id}")


def _assert_slot_payload(
    preset_id: str,
    slot_id: str,
    *,
    label: str,
    action: str,
    key_label: str,
) -> None:
    item = _runtime_item(preset_id, slot_id)
    if item.id != slot_id:
        raise AssertionError(f"Slot id changed: {item.id} != {slot_id}")
    if item.key_label != key_label:
        raise AssertionError(
            f"Slot key label changed for {slot_id}: {item.key_label!r} != {key_label!r}"
        )
    if item.label != label or item.action != action:
        raise AssertionError(
            f"Unexpected slot payload for {slot_id}: "
            f"{item.label!r}/{item.action!r} != {label!r}/{action!r}"
        )


if not host.assign_slot_action_payload(
    "edit_mode_custom",
    custom_key_slot_id,
    "maya.tool.rotate",
):
    raise AssertionError("Could not assign an action payload to a selected slot.")
_assert_slot_payload(
    "edit_mode_custom",
    custom_key_slot_id,
    label="Rotate",
    action="maya.tool.rotate",
    key_label="3",
)
if not host.clear_slot_payload("edit_mode_custom", custom_key_slot_id):
    raise AssertionError("Could not clear a slot payload.")
_assert_slot_payload(
    "edit_mode_custom",
    custom_key_slot_id,
    label=edit_mode.EMPTY_SLOT_LABEL,
    action="",
    key_label="3",
)
if not host.move_slot_payload(
    "edit_mode_target",
    target_one_slot_id,
    "edit_mode_custom",
    custom_key_slot_id,
):
    raise AssertionError("Could not move a payload between rails.")
_assert_slot_payload(
    "edit_mode_target",
    target_one_slot_id,
    label=edit_mode.EMPTY_SLOT_LABEL,
    action="",
    key_label="4",
)
_assert_slot_payload(
    "edit_mode_custom",
    custom_key_slot_id,
    label="One",
    action="maya.tool.move",
    key_label="3",
)
if not host.move_slot_payload(
    "edit_mode_custom",
    custom_key_slot_id,
    "edit_mode_custom",
    custom_rotate_slot_id,
):
    raise AssertionError("Could not swap payloads within a rail.")
_assert_slot_payload(
    "edit_mode_custom",
    custom_key_slot_id,
    label="Rot",
    action="maya.tool.rotate",
    key_label="3",
)
_assert_slot_payload(
    "edit_mode_custom",
    custom_rotate_slot_id,
    label="One",
    action="maya.tool.move",
    key_label="2",
)
if not host.clear_slot_payload("edit_mode_custom", custom_key_slot_id):
    raise AssertionError("Could not clear a payload after a swap.")
_assert_slot_payload(
    "edit_mode_custom",
    custom_key_slot_id,
    label=edit_mode.EMPTY_SLOT_LABEL,
    action="",
    key_label="3",
)
_assert_slot_payload(
    "edit_mode_custom",
    "edit_mode_custom.move",
    label="Move",
    action="maya.tool.move",
    key_label="1",
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
    "options_preset_id": actionrail.edit_mode_state().options_preset_id,
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
