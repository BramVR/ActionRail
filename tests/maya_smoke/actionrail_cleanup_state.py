from __future__ import annotations

import json
import sys

__args__ = globals().get("__args__", {})

repo_scripts = __args__.get("repo_scripts")
if repo_scripts and repo_scripts not in sys.path:
    sys.path.insert(0, repo_scripts)

from maya import cmds  # noqa: E402
from PySide6 import QtCore, QtWidgets  # noqa: E402
from shiboken6 import getCppPointer, isValid  # noqa: E402

import actionrail  # noqa: E402


def _close_smoke_hosts() -> int:
    closed = 0
    for name, value in list(vars(actionrail).items()):
        if not name.startswith("_") or not name.endswith("_smoke_host"):
            continue
        close = getattr(value, "close", None)
        if close is None:
            continue
        try:
            close()
            setattr(actionrail, name, None)
            closed += 1
        except Exception:
            pass
    return closed


def _delete_actionrail_widgets(app: QtWidgets.QApplication) -> int:
    seen: set[int] = set()
    deleted = 0
    for widget in app.allWidgets():
        if not isValid(widget):
            continue
        try:
            object_name = widget.objectName()
        except Exception:
            continue
        if not object_name.startswith("ActionRailViewportOverlay"):
            continue
        identifier = int(getCppPointer(widget)[0])
        if identifier in seen:
            continue
        seen.add(identifier)
        try:
            widget.hide()
            widget.setParent(None)
            widget.deleteLater()
            deleted += 1
        except Exception:
            pass

    if deleted:
        app.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)
        app.processEvents()
    return deleted


def _purge_actionrail_modules() -> int:
    module_names = [
        name for name in sys.modules if name == "actionrail" or name.startswith("actionrail.")
    ]
    for name in module_names:
        sys.modules.pop(name, None)
    return len(module_names)


app = QtWidgets.QApplication.instance()
if app is None:
    raise RuntimeError("Maya QApplication is not available.")

actionrail.hide_all()
closed_hosts = _close_smoke_hosts()
deleted_widgets = _delete_actionrail_widgets(app)
cmds.file(new=True, force=True)
cmds.select(clear=True)
app.processEvents()
purged_modules = _purge_actionrail_modules()

print(
    json.dumps(
        {
            "closed_smoke_hosts": closed_hosts,
            "deleted_widgets": deleted_widgets,
            "purged_modules": purged_modules,
            "scene": cmds.file(query=True, sceneName=True) or None,
        },
        sort_keys=True,
    )
)
