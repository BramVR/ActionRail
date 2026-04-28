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
from actionrail import maya_ui  # noqa: E402
from actionrail.runtime import _OVERLAYS, active_overlay_ids  # noqa: E402

app = QtWidgets.QApplication.instance()
if app is None:
    raise RuntimeError("Maya QApplication is not available.")


def _exists(name: str, query) -> bool:
    try:
        return bool(query(name, exists=True))
    except Exception:
        return False


actionrail.hide_all()
app.processEvents()

maya_ui.uninstall_menu_toggle()
maya_ui.uninstall_shelf_toggle()

menu_first = actionrail.install_menu_toggle()
menu_second = actionrail.install_menu_toggle()
shelf_first = actionrail.install_shelf_toggle()
shelf_second = actionrail.install_shelf_toggle()

menu_exists_after_install = _exists(maya_ui.MENU_ITEM_NAME, cmds.menuItem)
shelf_exists_after_install = _exists(maya_ui.SHELF_BUTTON_NAME, cmds.shelfButton)
menu_command = cmds.menuItem(maya_ui.MENU_ITEM_NAME, query=True, command=True)
shelf_command = cmds.shelfButton(maya_ui.SHELF_BUTTON_NAME, query=True, command=True)

toggle_show = actionrail.toggle_default()
app.processEvents()
cmds.refresh(force=True)

ids_after_show = active_overlay_ids()
host = _OVERLAYS["transform_stack"]
visible_after_show = bool(host.widget.isVisible())
size_after_show = [host.widget.width(), host.widget.height()]

toggle_hide = actionrail.toggle_default()
app.processEvents()
ids_after_hide = active_overlay_ids()

maya_ui.uninstall_menu_toggle()
maya_ui.uninstall_shelf_toggle()

result = {
    "ids_after_hide": ids_after_hide,
    "ids_after_show": ids_after_show,
    "menu_command": menu_command,
    "menu_exists_after_install": menu_exists_after_install,
    "menu_exists_after_uninstall": _exists(maya_ui.MENU_ITEM_NAME, cmds.menuItem),
    "menu_first": menu_first,
    "menu_second": menu_second,
    "shelf_command": shelf_command,
    "shelf_exists_after_install": shelf_exists_after_install,
    "shelf_exists_after_uninstall": _exists(maya_ui.SHELF_BUTTON_NAME, cmds.shelfButton),
    "shelf_first": shelf_first,
    "shelf_second": shelf_second,
    "size_after_show": size_after_show,
    "toggle_hide": toggle_hide,
    "toggle_show": toggle_show,
    "visible_after_show": visible_after_show,
}

actionrail.hide_all()
app.processEvents()

print(json.dumps(result, sort_keys=True))
