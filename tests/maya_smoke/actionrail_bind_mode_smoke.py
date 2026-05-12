from __future__ import annotations

import json
import sys

__args__ = globals().get("__args__", {})

repo_scripts = __args__.get("repo_scripts")
if repo_scripts and repo_scripts not in sys.path:
    sys.path.insert(0, repo_scripts)

from maya import cmds  # noqa: E402
from PySide6 import QtCore, QtGui, QtWidgets  # noqa: E402

import actionrail  # noqa: E402


def _button(host, slot_id: str):
    for button in host.widget.findChildren(QtWidgets.QPushButton):
        if button.property("actionRailSlotId") == slot_id:
            return button
    raise RuntimeError(f"Missing ActionRail slot button: {slot_id}")


def _snapshot(button) -> dict[str, object]:
    return {
        "key_label": button.property("actionRailKeyLabel"),
        "text": button.text(),
        "conflict": button.property("actionRailBindConflict"),
    }


def _send_bind_key(button, key: int, modifiers=QtCore.Qt.KeyboardModifier.NoModifier) -> None:
    enter = QtCore.QEvent(QtCore.QEvent.Type.Enter)
    QtWidgets.QApplication.sendEvent(button, enter)
    event = QtGui.QKeyEvent(
        QtCore.QEvent.Type.KeyRelease,
        key,
        modifiers,
    )
    QtWidgets.QApplication.sendEvent(button, event)


cmds.file(new=True, force=True)
cmds.hotkey(
    keyShortcut="F12",
    ctrlModifier=True,
    altModifier=True,
    shiftModifier=True,
    name="",
)
actionrail.hide_all()
host = actionrail.show_example("transform_stack")
app = QtWidgets.QApplication.instance()
if app is None:
    raise RuntimeError("Maya QApplication is not available.")
app.processEvents()

set_key_slot_id = "transform_stack.set_key"
set_key_button = _button(host, set_key_slot_id)
before = _snapshot(set_key_button)

actionrail.enter_bind_mode()
state_after_enter = actionrail.bind_mode_state()
_send_bind_key(
    set_key_button,
    QtCore.Qt.Key.Key_F12,
    QtCore.Qt.KeyboardModifier.ControlModifier
    | QtCore.Qt.KeyboardModifier.AltModifier
    | QtCore.Qt.KeyboardModifier.ShiftModifier,
)
app.processEvents()
after_bind = _snapshot(set_key_button)
state_after_bind = actionrail.bind_mode_state()

if after_bind["key_label"] != "Ctrl+Alt+Shift+F12" or after_bind["text"] != (
    "K\nCtrl+Alt+Shift+F12"
):
    raise RuntimeError(f"Bind Mode did not update visible set-key label: {after_bind}")
if state_after_bind.slot_id != "set_key":
    raise RuntimeError(f"Bind Mode did not select hovered slot: {state_after_bind}")

actionrail.exit_bind_mode(save=False)
app.processEvents()
after_discard = _snapshot(set_key_button)

if after_discard["key_label"] != "S" or after_discard["text"] != "K\nS":
    raise RuntimeError(f"Bind Mode discard did not restore original label: {after_discard}")

actionrail.enter_bind_mode()
_send_bind_key(set_key_button, QtCore.Qt.Key.Key_Escape)
app.processEvents()
after_clear = _snapshot(set_key_button)
actionrail.exit_bind_mode(save=True)

if after_clear["key_label"] != "" or after_clear["text"] != "K":
    raise RuntimeError(f"Bind Mode escape did not clear visible label: {after_clear}")

result = {
    "after_bind": after_bind,
    "after_clear": after_clear,
    "after_discard": after_discard,
    "before": before,
    "state_after_bind": state_after_bind.__dict__,
    "state_after_enter": state_after_enter.__dict__,
}

actionrail.hide_all()
app.processEvents()

print(json.dumps(result, sort_keys=True))
