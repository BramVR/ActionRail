from __future__ import annotations

import json
import sys

__args__ = globals().get("__args__", {})

repo_scripts = __args__.get("repo_scripts")
if repo_scripts and repo_scripts not in sys.path:
    sys.path.insert(0, repo_scripts)

from maya import cmds, mel  # noqa: E402

import actionrail  # noqa: E402
from actionrail.hotkeys import publish_action, publish_preset_slots  # noqa: E402
from actionrail.runtime import active_overlay_ids  # noqa: E402

cmds.file(new=True, force=True)
cube = cmds.polyCube(name="actionrailHotkeyBridgeSmokeCube")[0]
cmds.select(cube, replace=True)
cmds.currentTime(1)

action_command = publish_action("maya.tool.rotate", label="Rotate")
slot_commands = publish_preset_slots("transform_stack")
set_key_command = next(
    command for command in slot_commands if command.target_id.endswith(".set_key")
)

mel.eval(f"{action_command.runtime_command};")
context_after_runtime_command = cmds.currentCtx()

mel.eval(f"{set_key_command.runtime_command};")
keyframe_count = cmds.keyframe(cube, query=True, keyframeCount=True) or 0

result = {
    "active_overlay_ids": active_overlay_ids(),
    "action_runtime_exists": cmds.runTimeCommand(action_command.runtime_command, exists=True),
    "context_after_runtime_command": context_after_runtime_command,
    "keyframe_count": keyframe_count,
    "slot_count": len(slot_commands),
    "slot_runtime_exists": cmds.runTimeCommand(set_key_command.runtime_command, exists=True),
}

actionrail.hide_all()

print(json.dumps(result, sort_keys=True))
