from __future__ import annotations

import json
import sys
import time

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


def process_until(predicate, *, timeout: float = 2.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.processEvents()
        cmds.refresh(force=True)
        if predicate():
            return True
        time.sleep(0.05)
    app.processEvents()
    cmds.refresh(force=True)
    return bool(predicate())


def button_label(button):
    return button.text().splitlines()[0]


def buttons_by_label(widget):
    return {
        button_label(button): button
        for button in widget.findChildren(QtWidgets.QPushButton)
    }


def button_state(widget):
    return {
        button_label(button): {
            "active": button.property("actionRailActive"),
            "enabled": bool(button.isEnabled()),
            "locked": button.property("actionRailLocked"),
            "slot_id": button.property("actionRailSlotId"),
            "text": button.text(),
        }
        for button in widget.findChildren(QtWidgets.QPushButton)
    }


def active_labels(widget):
    state = button_state(widget)
    return sorted(label for label, values in state.items() if values["active"] == "true")


def assert_transform_state(widget, *, active: str) -> None:
    state = button_state(widget)
    expected_active = [active]
    if active_labels(widget) != expected_active:
        raise AssertionError(
            f"Expected only {expected_active} active, got {active_labels(widget)}: {state}"
        )

    if state["T"]["enabled"] is not False:
        raise AssertionError(f"Unassigned T slot should be disabled: {state}")
    if state["T"]["locked"] != "true":
        raise AssertionError(f"Unassigned T slot should be locked: {state}")
    if state["T"]["active"] != "false":
        raise AssertionError(f"Unassigned T slot should not be active: {state}")
    if state["K"]["active"] != "false":
        raise AssertionError(f"One-shot K slot should not be active: {state}")


cmds.file(new=True, force=True)
cube = cmds.polyCube(name="actionrailTransformStateCube")[0]
cmds.select(cube, replace=True)
cmds.currentTime(1)
cmds.setToolTo("selectSuperContext")

host = actionrail.show_example("transform_stack")
app.processEvents()
cmds.refresh(force=True)

widget = host.widget
buttons = buttons_by_label(widget)
state_after_show = button_state(widget)

expected_labels = ["M", "T", "R", "S", "K"]
if list(buttons) != expected_labels:
    raise AssertionError(f"Unexpected transform-stack buttons: {state_after_show}")

if state_after_show["T"]["enabled"] is not False:
    raise AssertionError(f"Unassigned T slot should start disabled: {state_after_show}")
if state_after_show["T"]["locked"] != "true":
    raise AssertionError(f"Unassigned T slot should start locked: {state_after_show}")
if state_after_show["T"]["active"] != "false":
    raise AssertionError(f"Unassigned T slot should not start active: {state_after_show}")

transition_states = {}
for label in ("M", "R", "S"):
    buttons[label].click()
    if not process_until(lambda expected=label: active_labels(widget) == [expected]):
        raise AssertionError(
            f"Clicking {label} did not make it the only active slot: {button_state(widget)}"
        )
    assert_transform_state(widget, active=label)
    transition_states[label] = {
        "button_state": button_state(widget),
        "current_context": cmds.currentCtx(),
    }

context_before_t = cmds.currentCtx()
buttons["T"].click()
app.processEvents()
cmds.refresh(force=True)
if cmds.currentCtx() != context_before_t:
    raise AssertionError(
        f"Disabled T slot changed the Maya context from {context_before_t} to {cmds.currentCtx()}"
    )
assert_transform_state(widget, active="S")

keyframes_before = cmds.keyframe(cube, query=True, keyframeCount=True) or 0
buttons["K"].click()
app.processEvents()
cmds.refresh(force=True)
keyframes_after = cmds.keyframe(cube, query=True, keyframeCount=True) or 0
if keyframes_after <= keyframes_before:
    raise AssertionError(
        "One-shot K slot did not set a keyframe: "
        f"before={keyframes_before}, after={keyframes_after}"
    )
assert_transform_state(widget, active="S")

result = {
    "active_ids": active_overlay_ids(),
    "button_labels": list(buttons),
    "context_after_disabled_t": cmds.currentCtx(),
    "initial_state": state_after_show,
    "keyframes_after": keyframes_after,
    "keyframes_before": keyframes_before,
    "panel": host.panel,
    "size": [widget.width(), widget.height()],
    "state_after_key": button_state(widget),
    "transition_states": transition_states,
    "visible": bool(widget.isVisible()),
}

if __args__.get("cleanup", True):
    actionrail.hide_all()
    app.processEvents()

print(json.dumps(result, sort_keys=True))
