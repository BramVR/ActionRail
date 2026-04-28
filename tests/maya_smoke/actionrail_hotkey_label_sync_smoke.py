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

slot_id = "transform_stack.set_key"
before = _button_snapshot(host, slot_id)
binding = assign_slot_hotkey("transform_stack", "set_key", "F12", overwrite=True)
if app is not None:
    app.processEvents()
after = _button_snapshot(host, slot_id)

result = {
    "after": after,
    "before": before,
    "binding_name": binding.name,
    "binding_key": binding.key,
    "same_fixed_size": before["width"] == after["width"] and before["height"] == after["height"],
}

actionrail.hide_all()

print(json.dumps(result, sort_keys=True))
