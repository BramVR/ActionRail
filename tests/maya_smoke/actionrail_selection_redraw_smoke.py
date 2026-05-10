from __future__ import annotations

import json
import sys
import time

__args__ = globals().get("__args__", {})

repo_scripts = __args__.get("repo_scripts")
if repo_scripts and repo_scripts not in sys.path:
    sys.path.insert(0, repo_scripts)

from maya import cmds  # noqa: E402
from maya import utils as maya_utils  # noqa: E402
from PySide6 import QtCore, QtWidgets  # noqa: E402

import actionrail  # noqa: E402

app = QtWidgets.QApplication.instance()
if app is None:
    raise RuntimeError("Maya QApplication is not available.")


def _active_model_panel() -> str:
    focused = cmds.getPanel(withFocus=True)
    if focused and cmds.getPanel(typeOf=focused) == "modelPanel":
        return focused
    for panel in cmds.getPanel(visiblePanels=True) or []:
        if cmds.getPanel(typeOf=panel) == "modelPanel":
            return panel
    panels = cmds.getPanel(type="modelPanel") or []
    if panels:
        return panels[0]
    raise RuntimeError("No Maya modelPanel is available.")


def _process_events(delay_ms: int = 0) -> None:
    app.processEvents()
    maya_utils.processIdleEvents()
    if delay_ms:
        QtCore.QThread.msleep(delay_ms)
        app.processEvents()
        maya_utils.processIdleEvents()


def _wait_for_refresh_call(calls: list[dict[str, object]], expected_count: int) -> bool:
    deadline = time.monotonic() + 2.0
    while time.monotonic() < deadline:
        _process_events(25)
        if len(calls) >= expected_count:
            return True
    _process_events()
    return len(calls) >= expected_count


def _make_scene() -> tuple[str, str]:
    cmds.file(new=True, force=True)
    cube_a = cmds.polyCube(name="ActionRailSelectionRedrawCubeA")[0]
    cmds.move(-0.85, 0.5, 0, cube_a)
    cube_b = cmds.polyCube(name="ActionRailSelectionRedrawCubeB")[0]
    cmds.move(0.85, 0.5, 0, cube_b)
    cmds.select(clear=True)
    return cube_a, cube_b


def _horizontal_smoke_spec() -> actionrail.StackSpec:
    return actionrail.StackSpec(
        id="selection_redraw_strip",
        layout=actionrail.RailLayout(
            anchor="viewport.bottom.center",
            orientation="horizontal",
            offset=(0, -24),
            locked=True,
        ),
        items=(
            actionrail.StackItem(
                type="toolButton",
                id="selection_redraw_strip.select",
                label="Q",
                action="maya.tool.select",
                icon="maya.objects",
            ),
            actionrail.StackItem(
                type="toolButton",
                id="selection_redraw_strip.move",
                label="W",
                action="maya.tool.move",
                icon="maya.move",
                active_when="maya.tool == move",
            ),
        ),
    )


cube_a, cube_b = _make_scene()
panel = _active_model_panel()
cmds.setToolTo("selectSuperContext")

hosts = (
    actionrail.show_preset("transform_stack", panel=panel),
    actionrail.show_spec(_horizontal_smoke_spec(), panel=panel),
)
_process_events(150)

schedulers = {
    getattr(host, "_viewport_selection_refresh_scheduler", None) for host in hosts
}
if None in schedulers or len(schedulers) != 1:
    raise AssertionError(f"Expected one shared selection refresh scheduler: {schedulers}")

scheduler = next(iter(schedulers))
job_id = getattr(scheduler, "job_id", None)
callback_id = getattr(scheduler, "callback_id", None)
if callback_id is None and (not isinstance(job_id, int) or job_id <= 0):
    raise AssertionError(
        "Selection refresh callback was not installed: "
        f"callback_id={callback_id!r}, job_id={job_id!r}"
    )

refresh_calls: list[dict[str, object]] = []
original_refresh = cmds.refresh


def _recording_refresh(*_args: object, **kwargs: object) -> object:
    refresh_calls.append(dict(kwargs))
    return original_refresh(*_args, **kwargs)


cmds.refresh = _recording_refresh
try:
    cmds.select(cube_a, replace=True)
    if not _wait_for_refresh_call(refresh_calls, 1):
        raise AssertionError("Selecting the first mesh did not schedule a viewport refresh.")
    cmds.select(cube_b, replace=True)
    if not _wait_for_refresh_call(refresh_calls, 2):
        raise AssertionError("Selecting the second mesh did not schedule a viewport refresh.")
finally:
    cmds.refresh = original_refresh

expected = {"currentView": True, "force": True}
if not all(call == expected for call in refresh_calls[:2]):
    raise AssertionError(f"Unexpected selection refresh calls: {refresh_calls}")

result = {
    "callback_id": repr(callback_id),
    "job_id": job_id,
    "panel": panel,
    "refresh_calls": refresh_calls[:2],
    "selected": cmds.ls(selection=True) or [],
}

actionrail.hide_all()
_process_events(100)

if getattr(scheduler, "callback_id", None) is not None or getattr(scheduler, "job_id", None):
    raise AssertionError("Selection refresh callback was not removed after hide_all().")

print(json.dumps(result, sort_keys=True))
