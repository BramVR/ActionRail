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

app = QtWidgets.QApplication.instance()
if app is None:
    raise RuntimeError("Maya QApplication is not available.")

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
    icon_state[slot_id] = {
        "icon_id": button.property("actionRailIcon"),
        "icon_name": button.property("actionRailIconName"),
        "icon_path": button.property("actionRailIconPath"),
        "icon_is_null": bool(button.icon().isNull()),
    }

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
}
if bad_slots:
    raise AssertionError(f"Maya resource icon rendering failed: {bad_slots}")

result = {
    "button_count": len(buttons),
    "button_labels": [button.text() for button in buttons],
    "button_icons": icon_state,
    "size": [host.widget.width(), host.widget.height()],
    "visible": bool(host.widget.isVisible()),
}

actionrail.hide_all()
app.processEvents()

print(json.dumps(result, sort_keys=True))
