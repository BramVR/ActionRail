from __future__ import annotations

import json
import sys
from pathlib import Path

__args__ = globals().get("__args__", {})

repo_scripts = __args__.get("repo_scripts")
if repo_scripts and repo_scripts not in sys.path:
    sys.path.insert(0, repo_scripts)

from maya import cmds  # noqa: E402
from PySide6 import QtWidgets  # noqa: E402

import actionrail  # noqa: E402

app = QtWidgets.QApplication.instance()
if app is None:
    raise RuntimeError("Maya QApplication is not available.")

output_path = Path(
    __args__.get(
        "output_path",
        "C:/PROJECTS/GG/ScreenUI/.gg-maya-sessiond/screenshots/"
        "actionrail_maya_icons_widget.png",
    )
)
output_path.parent.mkdir(parents=True, exist_ok=True)

cmds.file(new=True, force=True)
cmds.polyCube(name="actionrailMayaIconSmokeCube")
cmds.refresh(force=True)

spec = actionrail.StackSpec(
    id="maya_icon_smoke",
    layout=actionrail.RailLayout(
        anchor="viewport.bottom.center",
        orientation="horizontal",
        columns=4,
        offset=(0, -24),
    ),
    items=(
        actionrail.StackItem(
            type="toolButton",
            id="maya_icon_smoke.move",
            label="M",
            icon="maya.move",
            action="maya.tool.move",
        ),
        actionrail.StackItem(
            type="toolButton",
            id="maya_icon_smoke.rotate",
            label="R",
            icon="maya.rotate",
            action="maya.tool.rotate",
        ),
        actionrail.StackItem(
            type="toolButton",
            id="maya_icon_smoke.scale",
            label="S",
            icon="maya.scale",
            action="maya.tool.scale",
        ),
        actionrail.StackItem(
            type="button",
            id="maya_icon_smoke.set_key",
            label="K",
            icon="maya.set_key",
            action="maya.anim.set_key",
        ),
    ),
)

diagnostics = actionrail.diagnose_spec(spec, cmds_module=cmds)
if diagnostics.warnings or diagnostics.errors:
    raise AssertionError(f"Unexpected Maya icon diagnostics: {diagnostics.as_dict()}")

host = actionrail.show_spec(spec)
app.processEvents()
cmds.refresh(force=True)

buttons = host.widget.findChildren(QtWidgets.QPushButton)
icon_state = {}
for button in buttons:
    slot_id = button.property("actionRailSlotId")
    if not isinstance(slot_id, str) or not slot_id:
        continue
    render_size = button.iconSize()
    icon_pixmap = button.icon().pixmap(render_size)
    icon_state[slot_id] = {
        "icon_id": button.property("actionRailIcon"),
        "icon_name": button.property("actionRailIconName"),
        "icon_path": button.property("actionRailIconPath"),
        "icon_is_null": bool(button.icon().isNull()),
        "icon_render_size": [render_size.width(), render_size.height()],
        "icon_pixmap_is_null": bool(icon_pixmap.isNull()),
        "icon_pixmap_size": [icon_pixmap.width(), icon_pixmap.height()],
    }

pixmap = host.widget.grab()
screenshot_saved = pixmap.save(str(output_path), "PNG")

expected_names = {
    "maya_icon_smoke.move": "move_M.png",
    "maya_icon_smoke.rotate": "rotate_M.png",
    "maya_icon_smoke.scale": "scale_M.png",
    "maya_icon_smoke.set_key": "setKeyframe.png",
}
bad_slots = {
    slot_id: icon_state.get(slot_id)
    for slot_id, icon_name in expected_names.items()
    if icon_state.get(slot_id, {}).get("icon_name") != icon_name
    or icon_state.get(slot_id, {}).get("icon_path") != ""
    or icon_state.get(slot_id, {}).get("icon_is_null") is not False
    or icon_state.get(slot_id, {}).get("icon_render_size") != [32, 32]
    or icon_state.get(slot_id, {}).get("icon_pixmap_is_null") is not False
}
if bad_slots:
    raise AssertionError(f"Maya resource icon rendering failed: {bad_slots}")
if not screenshot_saved or pixmap.width() <= 0 or pixmap.height() <= 0:
    raise AssertionError(f"Failed to save Maya icon smoke screenshot: {output_path}")

result = {
    "button_count": len(buttons),
    "button_labels": [button.text() for button in buttons],
    "button_icons": icon_state,
    "screenshot": str(output_path),
    "screenshot_saved": bool(screenshot_saved),
    "screenshot_size": [pixmap.width(), pixmap.height()],
    "size": [host.widget.width(), host.widget.height()],
    "visible": bool(host.widget.isVisible()),
}

actionrail.hide_all()
app.processEvents()

print(json.dumps(result, sort_keys=True))
