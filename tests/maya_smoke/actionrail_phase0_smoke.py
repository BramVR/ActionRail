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
from actionrail.runtime import active_overlay_ids  # noqa: E402

app = QtWidgets.QApplication.instance()
if app is None:
    raise RuntimeError("Maya QApplication is not available.")

cmds.file(new=True, force=True)
cube = cmds.polyCube(name="actionrailSmokeCube")[0]
cmds.select(cube, replace=True)
cmds.currentTime(1)

host = actionrail.show_example("transform_stack")
app.processEvents()
cmds.refresh(force=True)

widget = host.widget
buttons = widget.findChildren(QtWidgets.QPushButton)
button_labels = [button.text() for button in buttons]

buttons_by_label = {button.text(): button for button in buttons}
for label in ("M", "R", "S", "K"):
    buttons_by_label[label].click()
    app.processEvents()

keyframe_count = cmds.keyframe(cube, query=True, keyframeCount=True) or 0
visible_before_hide = bool(widget.isVisible())
object_name = widget.objectName()
size = [widget.width(), widget.height()]
panel = host.panel

actionrail.hide_all()
app.processEvents()
ids_after_hide = active_overlay_ids()

host_after_reload = actionrail.reload(panel=panel)
app.processEvents()
cmds.refresh(force=True)

reload_widget = host_after_reload.widget
reload_buttons = reload_widget.findChildren(QtWidgets.QPushButton)

result = {
    "active_ids_after_reload": active_overlay_ids(),
    "button_labels": button_labels,
    "current_context_after_clicks": cmds.currentCtx(),
    "ids_after_hide": ids_after_hide,
    "import_version": actionrail.__version__,
    "keyframe_count": keyframe_count,
    "panel": panel,
    "reload_button_count": len(reload_buttons),
    "reload_visible": bool(reload_widget.isVisible()),
    "size": size,
    "visible_before_hide": visible_before_hide,
    "widget_object_name": object_name,
}

if not __args__.get("leave_visible"):
    actionrail.hide_all()
    app.processEvents()

print(json.dumps(result, sort_keys=True))
