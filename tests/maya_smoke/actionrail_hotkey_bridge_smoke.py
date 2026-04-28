from __future__ import annotations

import json
import sys

__args__ = globals().get("__args__", {})

repo_scripts = __args__.get("repo_scripts")
if repo_scripts and repo_scripts not in sys.path:
    sys.path.insert(0, repo_scripts)

from maya import cmds, mel  # noqa: E402

import actionrail  # noqa: E402
from actionrail.hotkeys import (  # noqa: E402
    publish_action,
    publish_preset_slots,
    publish_slot,
    sync_preset_slots,
)
from actionrail.runtime import active_overlay_ids  # noqa: E402

cmds.file(new=True, force=True)
cube = cmds.polyCube(name="actionrailHotkeyBridgeSmokeCube")[0]
cmds.select(cube, replace=True)
cmds.currentTime(1)

action_command = publish_action("maya.tool.rotate", label="Rotate")
action_command_after_republish = publish_action("maya.tool.rotate", label="Rotate")
slot_commands = publish_preset_slots("transform_stack")
set_key_command = next(
    command for command in slot_commands if command.target_id.endswith(".set_key")
)
unqualified_set_key_command = publish_slot("transform_stack", "set_key", label="Set Key")
stale_slot_command = publish_slot("transform_stack", "removed_slot", label="Removed")
sync_result = sync_preset_slots("transform_stack")

mel.eval(f"{action_command.runtime_command};")
context_after_runtime_command = cmds.currentCtx()

mel.eval(f"{set_key_command.runtime_command};")
keyframe_count = cmds.keyframe(cube, query=True, keyframeCount=True) or 0
cmds.cutKey(cube, clear=True)

mel.eval(f"{unqualified_set_key_command.runtime_command};")
unqualified_keyframe_count = cmds.keyframe(cube, query=True, keyframeCount=True) or 0

result = {
    "active_overlay_ids": active_overlay_ids(),
    "action_republish_same_name": action_command.runtime_command
    == action_command_after_republish.runtime_command,
    "action_runtime_exists": cmds.runTimeCommand(action_command.runtime_command, exists=True),
    "context_after_runtime_command": context_after_runtime_command,
    "keyframe_count": keyframe_count,
    "slot_count": len(slot_commands),
    "slot_runtime_exists": cmds.runTimeCommand(set_key_command.runtime_command, exists=True),
    "stale_slot_removed": not cmds.runTimeCommand(
        stale_slot_command.runtime_command,
        exists=True,
    ),
    "sync_published_count": len(sync_result.published),
    "sync_unpublished_count": len(sync_result.unpublished),
    "unqualified_keyframe_count": unqualified_keyframe_count,
    "unqualified_slot_runtime_exists": cmds.runTimeCommand(
        unqualified_set_key_command.runtime_command,
        exists=True,
    ),
}

actionrail.hide_all()

print(json.dumps(result, sort_keys=True))
