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
        "actionrail_hidden_visibility_widget.png",
    )
)
output_path.parent.mkdir(parents=True, exist_ok=True)

previous_host = getattr(actionrail, "_hidden_visibility_smoke_host", None)
if previous_host is not None:
    previous_host.close()
    actionrail._hidden_visibility_smoke_host = None

cmds.file(new=True, force=True)
cmds.polyCube(name="actionrailHiddenVisibilityCube")
cmds.refresh(force=True)

spec = parse_stack_spec(
    {
        "id": "hidden_visibility_smoke",
        "layout": {
            "anchor": "viewport.left.center",
            "orientation": "vertical",
            "offset": [48, 0],
        },
        "items": [
            {
                "type": "toolButton",
                "id": "hidden_visibility.hidden_move",
                "label": "HM",
                "action": "maya.tool.move",
                "visible_when": False,
            },
            {
                "type": "toolButton",
                "id": "hidden_visibility.hidden_rotate",
                "label": "HR",
                "action": "maya.tool.rotate",
                "visible_when": False,
            },
            {
                "type": "button",
                "id": "hidden_visibility.hidden_key",
                "label": "HK",
                "action": "maya.anim.set_key",
                "visible_when": False,
            },
            {
                "type": "button",
                "id": "hidden_visibility.visible_key",
                "label": "VK",
                "action": "maya.anim.set_key",
                "tone": "teal",
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
frames = [
    frame
    for frame in widget.findChildren(QtWidgets.QFrame)
    if frame.property("actionRailRole") == "cluster"
]
frame_button_counts = [len(frame.findChildren(QtWidgets.QPushButton)) for frame in frames]

result = {
    "button_labels": [button.text() for button in buttons],
    "empty_frame_count": frame_button_counts.count(0),
    "frame_button_counts": frame_button_counts,
    "frame_count": len(frames),
    "output_path": str(output_path),
    "panel": host.panel,
    "pixmap_size": [pixmap.width(), pixmap.height()],
    "position": [widget.x(), widget.y()],
    "saved": bool(saved),
    "size": [widget.width(), widget.height()],
    "visible": bool(widget.isVisible()),
}

if result["button_labels"] != ["VK"]:
    raise AssertionError(f"Unexpected visible buttons: {result['button_labels']}")
if result["empty_frame_count"] != 0:
    raise AssertionError(f"Hidden items left empty frames: {result}")
if result["frame_button_counts"] != [1]:
    raise AssertionError(f"Unexpected frame structure: {result}")
if not result["saved"]:
    raise AssertionError(f"Failed to save hidden visibility screenshot: {result}")

actionrail._hidden_visibility_smoke_host = host

if __args__.get("cleanup"):
    actionrail.hide_all()
    host.close()
    actionrail._hidden_visibility_smoke_host = None
    app.processEvents()

print(json.dumps(result, sort_keys=True))
