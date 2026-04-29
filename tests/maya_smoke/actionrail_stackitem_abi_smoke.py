from __future__ import annotations

import json
import sys

__args__ = globals().get("__args__", {})

repo_scripts = __args__.get("repo_scripts")
if repo_scripts and repo_scripts not in sys.path:
    sys.path.insert(0, repo_scripts)

from PySide6 import QtWidgets  # noqa: E402

from actionrail.actions import create_default_registry  # noqa: E402
from actionrail.spec import RailLayout, StackItem, StackSpec  # noqa: E402
from actionrail.widgets import build_transform_stack  # noqa: E402

app = QtWidgets.QApplication.instance()
if app is None:
    raise RuntimeError("Maya QApplication is not available.")

item = StackItem("button", "abi.slot", "K", "maya.anim.set_key", "teal")
if item.tone != "teal" or item.icon != "":
    raise AssertionError(f"StackItem positional ABI changed: {item!r}")

spec = StackSpec(
    id="stackitem_abi",
    layout=RailLayout(anchor="viewport.left.center"),
    items=(item,),
)
widget = build_transform_stack(spec, create_default_registry())
app.processEvents()

buttons = widget.findChildren(QtWidgets.QPushButton)
if len(buttons) != 1:
    raise AssertionError(f"Expected one rendered button, got {len(buttons)}")

button = buttons[0]
result = {
    "button_text": button.text(),
    "icon": item.icon,
    "rendered_icon": button.property("actionRailIcon"),
    "rendered_tone": button.property("actionRailTone"),
    "slot_id": button.property("actionRailSlotId"),
    "tone": item.tone,
}

if result["rendered_tone"] != "teal":
    raise AssertionError(f"Legacy tone did not render as tone: {result}")
if result["rendered_icon"] != "":
    raise AssertionError(f"Legacy tone was treated as icon: {result}")

widget.close()
app.processEvents()

print(json.dumps(result, sort_keys=True))
