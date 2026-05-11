from __future__ import annotations

import json
import sys

__args__ = globals().get("__args__", {})

repo_scripts = __args__.get("repo_scripts")
if repo_scripts and repo_scripts not in sys.path:
    sys.path.insert(0, repo_scripts)

from maya import cmds  # noqa: E402
from maya import utils as maya_utils  # noqa: E402
from PySide6 import QtCore, QtWidgets  # noqa: E402

import actionrail  # noqa: E402
from actionrail import overlay  # noqa: E402

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

if hasattr(overlay, "ViewportSelectionRefreshScheduler"):
    raise AssertionError("Selection redraw scheduler still exists in actionrail.overlay.")

host_schedulers = [
    getattr(host, "_viewport_selection_refresh_scheduler", None) for host in hosts
]
if any(scheduler is not None for scheduler in host_schedulers):
    raise AssertionError(f"Unexpected selection refresh scheduler on hosts: {host_schedulers}")

refresh_calls: list[dict[str, object]] = []
original_refresh = cmds.refresh


def _recording_refresh(*_args: object, **kwargs: object) -> object:
    refresh_calls.append(dict(kwargs))
    return original_refresh(*_args, **kwargs)


cmds.refresh = _recording_refresh
try:
    cmds.select(cube_a, replace=True)
    _process_events(150)
    selected_after_a = cmds.ls(selection=True) or []
    cmds.select(cube_b, replace=True)
    _process_events(150)
    selected_after_b = cmds.ls(selection=True) or []
    cmds.delete(cube_b)
    _process_events(150)
    cube_b_exists_after_delete = bool(cmds.objExists(cube_b))
finally:
    cmds.refresh = original_refresh

if selected_after_a != [cube_a]:
    raise AssertionError(f"First mesh was not selected natively: {selected_after_a}")
if selected_after_b != [cube_b]:
    raise AssertionError(f"Second mesh was not selected natively: {selected_after_b}")
if cube_b_exists_after_delete:
    raise AssertionError("Selected mesh delete did not complete while overlays were visible.")
if refresh_calls:
    raise AssertionError(f"ActionRail scheduled forced selection refresh calls: {refresh_calls}")

result = {
    "forced_refresh_calls": refresh_calls,
    "host_selection_schedulers": [repr(scheduler) for scheduler in host_schedulers],
    "panel": panel,
    "selected_after_a": selected_after_a,
    "selected_after_b": selected_after_b,
    "cube_b_exists_after_delete": cube_b_exists_after_delete,
}

actionrail.hide_all()
_process_events(100)

print(json.dumps(result, sort_keys=True))
