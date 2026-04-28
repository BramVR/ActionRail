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
from actionrail.overlay import ViewportOverlayHost  # noqa: E402
from actionrail.spec import parse_stack_spec  # noqa: E402

app = QtWidgets.QApplication.instance()
if app is None:
    raise RuntimeError("Maya QApplication is not available.")

output_path = Path(
    __args__.get(
        "output_path",
        "C:/PROJECTS/GG/ScreenUI/.gg-maya-sessiond/screenshots/"
        "actionrail_predicates_widget.png",
    )
)
output_path.parent.mkdir(parents=True, exist_ok=True)

previous_host = getattr(actionrail, "_predicates_smoke_host", None)
if previous_host is not None:
    previous_host.close()
    actionrail._predicates_smoke_host = None

cmds.file(new=True, force=True)
cube = cmds.polyCube(name="actionrailPredicatesCube")[0]
cmds.select(cube, replace=True)
cmds.setToolTo("scaleSuperContext")
cmds.refresh(force=True)

spec = parse_stack_spec(
    {
        "id": "predicates_smoke",
        "layout": {
            "anchor": "viewport.left.center",
            "orientation": "vertical",
            "offset": [96, 0],
        },
        "items": [
            {
                "type": "button",
                "id": "predicates.hidden_empty_selection",
                "label": "HE",
                "action": "maya.anim.set_key",
                "visible_when": "selection.count == 0",
            },
            {
                "type": "toolButton",
                "id": "predicates.visible_selected_active_scale",
                "label": "VS",
                "action": "maya.tool.scale",
                "visible_when": "selection.count > 0",
                "enabled_when": "action.exists",
                "active_when": "maya.tool == scale",
            },
            {
                "type": "button",
                "id": "predicates.disabled_missing_command",
                "label": "DK",
                "action": "maya.anim.set_key",
                "enabled_when": "command.exists('definitelyMissingActionRailCommand')",
            },
            {
                "type": "button",
                "id": "predicates.enabled_existing_command",
                "label": "CK",
                "action": "maya.anim.set_key",
                "enabled_when": "command.exists('setKeyframe')",
                "active_when": "current_tool == 'scaleSuperContext'",
            },
        ],
    }
)

host = ViewportOverlayHost(spec)
host.show()
app.processEvents()
cmds.refresh(force=True)

widget = host.widget
pixmap = widget.grab()
saved = pixmap.save(str(output_path), "PNG")
buttons = widget.findChildren(QtWidgets.QPushButton)
button_state = {
    str(button.property("actionRailSlotId")): {
        "active": button.property("actionRailActive"),
        "enabled": bool(button.isEnabled()),
        "text": button.text(),
    }
    for button in buttons
}

result = {
    "button_state": button_state,
    "button_text": [button.text() for button in buttons],
    "current_context": cmds.currentCtx(),
    "output_path": str(output_path),
    "panel": host.panel,
    "pixmap_size": [pixmap.width(), pixmap.height()],
    "saved": bool(saved),
    "selection": cmds.ls(selection=True),
    "size": [widget.width(), widget.height()],
    "visible": bool(widget.isVisible()),
}

if result["button_text"] != ["VS", "DK", "CK"]:
    raise AssertionError(f"Unexpected predicate-visible buttons: {result}")

visible_button = button_state["predicates.visible_selected_active_scale"]
disabled_button = button_state["predicates.disabled_missing_command"]
command_button = button_state["predicates.enabled_existing_command"]

if visible_button["active"] != "true" or visible_button["enabled"] is not True:
    raise AssertionError(f"Selected scale predicate did not activate: {result}")
if disabled_button["enabled"] is not False:
    raise AssertionError(f"Missing command predicate did not disable button: {result}")
if command_button["active"] != "true" or command_button["enabled"] is not True:
    raise AssertionError(f"Existing command/current tool predicates failed: {result}")
if not result["saved"]:
    raise AssertionError(f"Failed to save predicate screenshot: {result}")

actionrail._predicates_smoke_host = host

if __args__.get("cleanup"):
    actionrail.hide_all()
    host.close()
    actionrail._predicates_smoke_host = None
    app.processEvents()

print(json.dumps(result, sort_keys=True))
