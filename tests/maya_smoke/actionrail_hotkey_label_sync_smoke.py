from __future__ import annotations

import json
import sys

__args__ = globals().get("__args__", {})

repo_scripts = __args__.get("repo_scripts")
if repo_scripts and repo_scripts not in sys.path:
    sys.path.insert(0, repo_scripts)

from maya import cmds  # noqa: E402

import actionrail  # noqa: E402
from actionrail.hotkeys import assign_slot_hotkey  # noqa: E402
from actionrail.qt import load  # noqa: E402


def _button_snapshot(host, slot_id: str) -> dict[str, object]:
    qt = load()
    for button in host.widget.findChildren(qt.QtWidgets.QPushButton):
        if button.property("actionRailSlotId") == slot_id:
            return {
                "height": button.height(),
                "key_label": button.property("actionRailKeyLabel"),
                "text": button.text(),
                "width": button.width(),
            }
    raise RuntimeError(f"Missing ActionRail slot button: {slot_id}")


cmds.file(new=True, force=True)
host = actionrail.show_example("transform_stack")
qt = load()
app = qt.QtWidgets.QApplication.instance()
if app is not None:
    app.processEvents()

move_slot_id = "transform_stack.move"
set_key_slot_id = "transform_stack.set_key"
before = _button_snapshot(host, set_key_slot_id)
move_binding = assign_slot_hotkey("transform_stack", "move", "F12", overwrite=True)
if app is not None:
    app.processEvents()
move_after_first_bind = _button_snapshot(host, move_slot_id)

binding = assign_slot_hotkey("transform_stack", "set_key", "F12", overwrite=True)
if app is not None:
    app.processEvents()
move_after_overwrite = _button_snapshot(host, move_slot_id)
after = _button_snapshot(host, set_key_slot_id)

result = {
    "after": after,
    "before": before,
    "binding_name": binding.name,
    "binding_key": binding.key,
    "move_after_first_bind": move_after_first_bind,
    "move_after_overwrite": move_after_overwrite,
    "move_binding_name": move_binding.name,
    "same_fixed_size": before["width"] == after["width"] and before["height"] == after["height"],
}

if move_after_first_bind["key_label"] != "F12" or move_after_first_bind["text"] != "M\nF12":
    raise RuntimeError(f"Move slot did not receive first key label: {move_after_first_bind}")
if move_after_overwrite["key_label"] != "" or move_after_overwrite["text"] != "M":
    raise RuntimeError(f"Move slot kept stale overwritten key label: {move_after_overwrite}")
if after["key_label"] != "F12" or after["text"] != "K\nF12":
    raise RuntimeError(f"Set-key slot did not receive overwritten key label: {after}")
if not result["same_fixed_size"]:
    raise RuntimeError(f"Set-key slot changed fixed size: {result}")

actionrail.hide_all()

print(json.dumps(result, sort_keys=True))
