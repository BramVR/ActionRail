from __future__ import annotations

import json
import sys
from pathlib import Path

__args__ = globals().get("__args__", {})

repo_scripts = __args__.get("repo_scripts")
if repo_scripts and repo_scripts not in sys.path:
    sys.path.insert(0, repo_scripts)

from maya import cmds  # noqa: E402
from PySide6 import QtWidgets  # noqa: E402

import actionrail  # noqa: E402
from actionrail import edit_mode  # noqa: E402

app = QtWidgets.QApplication.instance()
if app is None:
    raise RuntimeError("Maya QApplication is not available.")

store_dir = Path(
    __args__.get(
        "store_dir",
        "C:/PROJECTS/GG/ScreenUI/.gg-maya-sessiond/custom_store_presets",
    )
)
store_dir.mkdir(parents=True, exist_ok=True)

actionrail.hide_all()
actionrail.exit_edit_mode()
app.processEvents()

spec = actionrail.StackSpec(
    id="custom_store_smoke",
    layout=actionrail.RailLayout(
        anchor="viewport.bottom.center",
        orientation="horizontal",
        rows=1,
        columns=2,
        offset=(0, -96),
        locked=False,
    ),
    items=(
        actionrail.StackItem(
            type="button",
            id="custom_store_smoke.move",
            label="Move",
            action="maya.tool.move",
        ),
        actionrail.StackItem(
            type="button",
            id="custom_store_smoke.rotate",
            label="Rot",
            action="maya.tool.rotate",
        ),
    ),
)
actionrail.save_user_preset(spec, preset_dir=store_dir, overwrite=True)
host = actionrail.show_preset("custom_store_smoke", user_preset_dir=store_dir)
app.processEvents()
cmds.refresh(force=True)
app.processEvents()

if getattr(host, "user_preset_dir", None) != store_dir:
    raise AssertionError(
        f"Runtime host did not retain custom user preset dir: {host!r}"
    )

state = actionrail.enter_edit_mode()
app.processEvents()
cmds.refresh(force=True)
app.processEvents()

edit_host = edit_mode._EDIT_HOST
if edit_host is None:
    raise AssertionError("Edit Mode host was not created.")

frame = edit_host.frame_for_preset("custom_store_smoke")
if frame is None:
    raise AssertionError(f"Custom user preset frame was not present: {edit_host.frames}")
if frame.source_layer != "user":
    raise AssertionError(f"Custom store preset was not classified as user: {frame}")

edit_host.select_rail("custom_store_smoke")
edit_host.set_selected_position(frame.x + 19, frame.y + 0, apply_snapping=False)
app.processEvents()
cmds.refresh(force=True)
app.processEvents()

moved_frame = edit_host.frame_for_preset("custom_store_smoke")
if moved_frame is None:
    raise AssertionError("Moved frame disappeared from Edit Mode.")

saved_path = actionrail.save_edit_mode_layout()
saved_spec = actionrail.load_user_preset("custom_store_smoke", preset_dir=store_dir)

if saved_path.parent != store_dir:
    raise AssertionError(f"Save Position wrote to wrong directory: {saved_path}")
if saved_spec.layout.offset != moved_frame.offset:
    raise AssertionError(
        "Saved custom-store layout did not match the moved runtime frame: "
        f"{saved_spec.layout.offset} != {moved_frame.offset}"
    )

result = {
    "frame_source_layer": moved_frame.source_layer,
    "host_user_preset_dir": str(getattr(host, "user_preset_dir", "")),
    "saved_layout_offset": list(saved_spec.layout.offset),
    "saved_path": str(saved_path),
    "store_dir": str(store_dir),
}

actionrail.exit_edit_mode()
actionrail.hide_all()
app.processEvents()

print(json.dumps(result, sort_keys=True))
