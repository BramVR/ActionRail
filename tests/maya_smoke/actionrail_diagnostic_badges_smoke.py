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
from actionrail.overlay import ViewportOverlayHost  # noqa: E402
from actionrail.spec import parse_stack_spec  # noqa: E402

app = QtWidgets.QApplication.instance()
if app is None:
    raise RuntimeError("Maya QApplication is not available.")

cmds.file(new=True, force=True)

previous_host = getattr(actionrail, "_diagnostic_badges_smoke_host", None)
if previous_host is not None:
    previous_host.close()
    actionrail._diagnostic_badges_smoke_host = None

spec = parse_stack_spec(
    {
        "id": "diagnostic_badges_smoke",
        "layout": {
            "anchor": "viewport.left.center",
            "orientation": "vertical",
            "offset": [128, 0],
        },
        "items": [
            {
                "type": "button",
                "id": "diagnostic_badges.missing_action",
                "label": "X",
                "action": "maya.missing.action",
            },
            {
                "type": "button",
                "id": "diagnostic_badges.missing_icon",
                "label": "I",
                "action": "maya.anim.set_key",
                "icon": "missing.icon",
            },
        ],
    }
)

host = ViewportOverlayHost(spec)
host.show()
app.processEvents()
cmds.refresh(force=True)

widget = host.widget
buttons = widget.findChildren(QtWidgets.QPushButton)
button_state = {
    str(button.property("actionRailSlotId")): {
        "diagnostic_code": button.property("actionRailDiagnosticCode"),
        "diagnostic_severity": button.property("actionRailDiagnosticSeverity"),
        "enabled": bool(button.isEnabled()),
        "text": button.text(),
    }
    for button in buttons
}

missing_action = button_state["diagnostic_badges.missing_action"]
missing_icon = button_state["diagnostic_badges.missing_icon"]

if missing_action != {
    "diagnostic_code": "missing_action",
    "diagnostic_severity": "error",
    "enabled": False,
    "text": "X\n!",
}:
    raise AssertionError(f"Missing action badge failed: {button_state}")

if missing_icon != {
    "diagnostic_code": "missing_icon",
    "diagnostic_severity": "warning",
    "enabled": True,
    "text": "I\n?",
}:
    raise AssertionError(f"Missing icon badge failed: {button_state}")

result = {
    "button_state": button_state,
    "size": [widget.width(), widget.height()],
    "visible": bool(widget.isVisible()),
}

actionrail._diagnostic_badges_smoke_host = host

if __args__.get("cleanup", True):
    host.close()
    actionrail._diagnostic_badges_smoke_host = None
    app.processEvents()

print(json.dumps(result, sort_keys=True))
