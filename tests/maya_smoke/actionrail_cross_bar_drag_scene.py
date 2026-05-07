from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from maya import cmds

args = globals().get("__args__", {}) or {}
repo_root_value = (
    args.get("repo_root") if isinstance(args, dict) else None
) or os.environ.get("ACTIONRAIL_REPO_ROOT")
repo_root = Path(repo_root_value or os.getcwd()).resolve()
scripts_dir = repo_root / "scripts"
if not (scripts_dir / "actionrail").exists():
    msg = (
        "Unable to resolve ActionRail repo root. Pass "
        "args={'repo_root': '<repo path>'} to script.execute or set "
        "ACTIONRAIL_REPO_ROOT."
    )
    raise RuntimeError(msg)
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

import actionrail  # noqa: E402

cmds.file(new=True, force=True)
actionrail.hide_all()

source_spec = actionrail.StackSpec(
    id="drag_source_bar",
    layout=actionrail.RailLayout(
        anchor="viewport.top.center",
        orientation="horizontal",
        rows=1,
        columns=3,
        offset=(0, 72),
        locked=False,
    ),
    items=(
        actionrail.StackItem(
            type="button",
            id="drag_source_bar.move",
            label="Move",
            action="maya.tool.move",
            icon="maya.move",
            key_label="1",
            active_when="maya.tool == move",
        ),
        actionrail.StackItem(
            type="button",
            id="drag_source_bar.rotate",
            label="Rotate",
            action="maya.tool.rotate",
            icon="maya.rotate",
            key_label="2",
            active_when="maya.tool == rotate",
        ),
        actionrail.StackItem(
            type="button",
            id="drag_source_bar.empty",
            label="New",
            key_label="3",
        ),
    ),
)

target_spec = actionrail.StackSpec(
    id="drag_target_bar",
    layout=actionrail.RailLayout(
        anchor="viewport.top.center",
        orientation="horizontal",
        rows=1,
        columns=3,
        offset=(0, 152),
        locked=False,
    ),
    items=(
        actionrail.StackItem(
            type="button",
            id="drag_target_bar.empty_a",
            label="New",
            key_label="8",
        ),
        actionrail.StackItem(
            type="button",
            id="drag_target_bar.scale",
            label="Scale",
            action="maya.tool.scale",
            icon="maya.scale",
            key_label="9",
            active_when="maya.tool == scale",
        ),
        actionrail.StackItem(
            type="button",
            id="drag_target_bar.empty_b",
            label="New",
            key_label="0",
        ),
    ),
)

source_host = actionrail.show_spec(source_spec)
target_host = actionrail.show_spec(target_spec)
actionrail.unlock_rail_slots("drag_source_bar")
actionrail.unlock_rail_slots("drag_target_bar")
actionrail.install_menu_toggle()

cmds.select(clear=True)
cmds.inViewMessage(
    amg=(
        "<hl>ActionRail drag test ready.</hl><br/>"
        "Both bars are unlocked. Hold Shift and drag Move/Rotate from SOURCE "
        "onto TARGET empty/Scale slots."
    ),
    pos="topCenter",
    fade=True,
)

scene_path = repo_root / ".gg-maya-sessiond" / "actionrail_cross_bar_drag_scene.ma"
cmds.file(rename=str(scene_path))
cmds.file(save=True, type="mayaAscii")

print(
    json.dumps(
        {
            "scene_path": str(scene_path),
            "source_bar": source_host.spec.id,
            "target_bar": target_host.spec.id,
            "source_unlocked": source_host.slot_edit_unlocked(),
            "target_unlocked": target_host.slot_edit_unlocked(),
        },
        sort_keys=True,
    )
)
