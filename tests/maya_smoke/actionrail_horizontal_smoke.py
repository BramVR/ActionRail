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
cmds.polyCube(name="actionrailHorizontalSmokeCube")
cmds.refresh(force=True)

host = actionrail.show_example("horizontal_tools")
app.processEvents()
cmds.refresh(force=True)

widget = host.widget
buttons = widget.findChildren(QtWidgets.QPushButton)

result = {
    "anchor": host.spec.anchor,
    "button_count": len(buttons),
    "button_labels": [button.text() for button in buttons],
    "orientation": host.spec.layout.orientation,
    "opacity": host.spec.layout.opacity,
    "panel": host.panel,
    "position": [widget.x(), widget.y()],
    "size": [widget.width(), widget.height()],
    "visible": bool(widget.isVisible()),
}

actionrail.hide_all()
app.processEvents()

print(json.dumps(result, sort_keys=True))
