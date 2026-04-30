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

cmds.file(new=True, force=True)
cmds.polyCube(name="actionrailHorizontalSmokeCube")
cmds.refresh(force=True)

host = actionrail.show_example("horizontal_tools")
app.processEvents()
cmds.refresh(force=True)

widget = host.widget
buttons = widget.findChildren(QtWidgets.QPushButton)
output_path = (
    Path("C:/PROJECTS/GG/ScreenUI/.gg-maya-sessiond/screenshots/")
    / "actionrail_horizontal_tools_widget.png"
)
output_path.parent.mkdir(parents=True, exist_ok=True)
pixmap = widget.grab()
screenshot_saved = pixmap.save(str(output_path), "PNG")

icon_state = {}
for button in buttons:
    slot_id = button.property("actionRailSlotId")
    if not isinstance(slot_id, str) or not slot_id:
        continue
    icon_path = button.property("actionRailIconPath")
    icon_state[slot_id] = {
        "icon_id": button.property("actionRailIcon"),
        "icon_path": icon_path,
        "icon_is_null": bool(button.icon().isNull()),
    }

result = {
    "anchor": host.spec.anchor,
    "button_count": len(buttons),
    "button_labels": [button.text() for button in buttons],
    "button_icons": icon_state,
    "orientation": host.spec.layout.orientation,
    "opacity": host.spec.layout.opacity,
    "panel": host.panel,
    "position": [widget.x(), widget.y()],
    "screenshot": str(output_path),
    "screenshot_saved": screenshot_saved,
    "screenshot_size": [pixmap.width(), pixmap.height()],
    "size": [widget.width(), widget.height()],
    "visible": bool(widget.isVisible()),
}

expected_icon_slots = {
    "horizontal_tools.move",
    "horizontal_tools.rotate",
    "horizontal_tools.scale",
    "horizontal_tools.set_key",
}
missing_icon_slots = []
null_icon_slots = []
for slot_id in expected_icon_slots:
    state = icon_state.get(slot_id)
    if not state or not state["icon_path"]:
        missing_icon_slots.append(slot_id)
    elif state["icon_is_null"]:
        null_icon_slots.append(slot_id)

if missing_icon_slots or null_icon_slots:
    raise AssertionError(f"Horizontal icon rendering failed: {result}")

if not screenshot_saved or pixmap.width() <= 0 or pixmap.height() <= 0:
    raise AssertionError(f"Failed to save horizontal rail screenshot: {result}")

actionrail.hide_all()
app.processEvents()

print(json.dumps(result, sort_keys=True))
