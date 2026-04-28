from __future__ import annotations

import json
import sys
from pathlib import Path

__args__ = globals().get("__args__", {})

repo_scripts = __args__.get("repo_scripts")
if repo_scripts and repo_scripts not in sys.path:
    sys.path.insert(0, repo_scripts)

from maya import cmds  # noqa: E402
from PySide6 import QtCore, QtWidgets  # noqa: E402

import actionrail  # noqa: E402

output_path = Path(
    __args__.get(
        "output_path",
        "C:/PROJECTS/GG/ScreenUI/.gg-maya-sessiond/actionrail_phase0_overlay.png",
    )
)
output_path.parent.mkdir(parents=True, exist_ok=True)

app = QtWidgets.QApplication.instance()
if app is None:
    raise RuntimeError("Maya QApplication is not available.")

cmds.file(new=True, force=True)
cmds.polyCube(name="actionrailCaptureCube")
cmds.refresh(force=True)

host = actionrail.show_example("transform_stack")
app.processEvents()
cmds.refresh(force=True)
QtCore.QThread.msleep(250)
app.processEvents()

widget = host.widget
pixmap = widget.grab()
saved = pixmap.save(str(output_path), "PNG")

result = {
    "button_count": len(widget.findChildren(QtWidgets.QPushButton)),
    "output_path": str(output_path),
    "panel": host.panel,
    "pixmap_size": [pixmap.width(), pixmap.height()],
    "saved": bool(saved),
    "visible": bool(widget.isVisible()),
    "widget_size": [widget.width(), widget.height()],
}

actionrail.hide_all()
app.processEvents()

print(json.dumps(result, sort_keys=True))
