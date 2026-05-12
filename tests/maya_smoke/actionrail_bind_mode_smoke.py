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


def _bind_mode_hud(preset_id: str):
    object_name = f"ActionRailBindModeHud_{preset_id}"
    return next(
        (
            widget
            for widget in QtWidgets.QApplication.allWidgets()
            if widget.objectName() == object_name and widget.isVisible()
        ),
        None,
    )


def _send_bind_key(button, key: int, modifiers=QtCore.Qt.KeyboardModifier.NoModifier) -> None:
    enter = QtCore.QEvent(QtCore.QEvent.Type.Enter)
    QtWidgets.QApplication.sendEvent(button, enter)
    event = QtGui.QKeyEvent(
        QtCore.QEvent.Type.KeyRelease,
        key,
        modifiers,
    )
    QtWidgets.QApplication.sendEvent(button, event)


def _query_hotkey_name(key: str):
    query_key = key.lower() if len(key) == 1 and key.isalpha() else key
    return cmds.hotkey(query_key, query=True, name=True)


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
app.processEvents()
state_after_enter = actionrail.bind_mode_state()
bind_mode_property_after_enter = set_key_button.property("actionRailBindMode")
bind_hud_after_enter = _bind_mode_hud("transform_stack")
if bind_mode_property_after_enter != "true":
    raise RuntimeError(
        "Bind Mode did not mark visible slots as bindable: "
        f"{bind_mode_property_after_enter}"
    )
if bind_hud_after_enter is None or "BIND MODE" not in bind_hud_after_enter.text():
    raise RuntimeError("Bind Mode did not show the floating HUD.")
bind_hud_text_after_enter = bind_hud_after_enter.text()
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
bind_hover_property_after_bind = set_key_button.property("actionRailBindHovered")

if after_bind["key_label"] != "Ctrl+Alt+Shift+F12" or after_bind["text"] != (
    "K\nCtrl+Alt+Shift+F12"
):
    raise RuntimeError(f"Bind Mode did not update visible set-key label: {after_bind}")
if state_after_bind.slot_id != "set_key":
    raise RuntimeError(f"Bind Mode did not select hovered slot: {state_after_bind}")
if bind_hover_property_after_bind != "true":
    raise RuntimeError(
        "Bind Mode did not mark the hovered slot: "
        f"{bind_hover_property_after_bind}"
    )

actionrail.exit_bind_mode(save=False)
app.processEvents()
after_discard = _snapshot(set_key_button)
bind_mode_property_after_exit = set_key_button.property("actionRailBindMode")
bind_hud_visible_after_exit = _bind_mode_hud("transform_stack") is not None

if after_discard["key_label"] != "S" or after_discard["text"] != "K\nS":
    raise RuntimeError(f"Bind Mode discard did not restore original label: {after_discard}")
if bind_mode_property_after_exit != "false":
    raise RuntimeError(
        "Bind Mode visual state did not turn off after discard: "
        f"{bind_mode_property_after_exit}"
    )
if bind_hud_visible_after_exit:
    raise RuntimeError("Bind Mode HUD stayed visible after discard.")

previous_w_binding = _query_hotkey_name("W")
actionrail.enter_bind_mode()
_send_bind_key(set_key_button, QtCore.Qt.Key.Key_W)
app.processEvents()
after_w_bind = _snapshot(set_key_button)
w_binding_during_bind = _query_hotkey_name("W")
actionrail.exit_bind_mode(save=False)
app.processEvents()
after_w_discard = _snapshot(set_key_button)
w_binding_after_discard = _query_hotkey_name("W")
if after_w_bind["key_label"] != "W" or w_binding_during_bind != (
    "ActionRail_slot_transform_stack_set_key_NameCommand"
):
    raise RuntimeError(
        "Bind Mode did not overwrite and show the plain W hotkey: "
        f"label={after_w_bind} binding={w_binding_during_bind}"
    )
if after_w_discard["key_label"] != "S" or w_binding_after_discard != previous_w_binding:
    raise RuntimeError(
        "Bind Mode discard did not restore the previous W hotkey: "
        f"label={after_w_discard} before={previous_w_binding} after={w_binding_after_discard}"
    )

previous_1_binding = _query_hotkey_name("1")
actionrail.enter_bind_mode()
_send_bind_key(set_key_button, QtCore.Qt.Key.Key_1)
app.processEvents()
after_1_bind = _snapshot(set_key_button)
one_binding_during_bind = _query_hotkey_name("1")
actionrail.exit_bind_mode(save=False)
app.processEvents()
after_1_discard = _snapshot(set_key_button)
one_binding_after_discard = _query_hotkey_name("1")
if after_1_bind["key_label"] != "1" or one_binding_during_bind != (
    "ActionRail_slot_transform_stack_set_key_NameCommand"
):
    raise RuntimeError(
        "Bind Mode did not overwrite and show the plain 1 hotkey: "
        f"label={after_1_bind} binding={one_binding_during_bind}"
    )
if after_1_discard["key_label"] != "S" or one_binding_after_discard != previous_1_binding:
    raise RuntimeError(
        "Bind Mode discard did not restore the previous 1 hotkey: "
        f"label={after_1_discard} before={previous_1_binding} after={one_binding_after_discard}"
    )

actionrail.enter_bind_mode()
_send_bind_key(set_key_button, QtCore.Qt.Key.Key_Escape)
app.processEvents()
after_clear = _snapshot(set_key_button)
actionrail.exit_bind_mode(save=True)

if after_clear["key_label"] != "" or after_clear["text"] != "K":
    raise RuntimeError(f"Bind Mode escape did not clear visible label: {after_clear}")

result = {
    "after_bind": after_bind,
    "after_1_bind": after_1_bind,
    "after_1_discard": after_1_discard,
    "after_clear": after_clear,
    "after_discard": after_discard,
    "after_w_bind": after_w_bind,
    "after_w_discard": after_w_discard,
    "before": before,
    "bind_hover_property_after_bind": bind_hover_property_after_bind,
    "bind_hud_text_after_enter": bind_hud_text_after_enter,
    "bind_mode_property_after_enter": bind_mode_property_after_enter,
    "bind_mode_property_after_exit": bind_mode_property_after_exit,
    "bind_hud_visible_after_exit": bind_hud_visible_after_exit,
    "one_binding_restored": one_binding_after_discard == previous_1_binding,
    "state_after_bind": state_after_bind.__dict__,
    "state_after_enter": state_after_enter.__dict__,
    "w_binding_restored": w_binding_after_discard == previous_w_binding,
}

actionrail.hide_all()
app.processEvents()

print(json.dumps(result, sort_keys=True))
