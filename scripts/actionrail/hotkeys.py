"""Maya runtime-command and hotkey bridge for ActionRail actions and slots."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Literal

from .actions import ActionRegistry, create_default_registry
from .spec import StackSpec, get_example_spec

COMMAND_PREFIX = "ActionRail"
COMMAND_CATEGORY = "ActionRail"

TargetKind = Literal["action", "slot"]


@dataclass(frozen=True)
class PublishedCommand:
    """Maya command names published for one ActionRail target."""

    target_kind: TargetKind
    target_id: str
    runtime_command: str
    name_command: str


@dataclass(frozen=True)
class HotkeyBinding:
    """Existing Maya hotkey assignment for one key chord."""

    key: str
    name: str
    ctrl: bool = False
    alt: bool = False
    shift: bool = False
    command: bool = False
    release: bool = False


class HotkeyConflictError(RuntimeError):
    """Raised when a hotkey chord already has a different command."""


def publish_default_actions(
    *,
    registry: ActionRegistry | None = None,
    cmds_module: Any | None = None,
) -> tuple[PublishedCommand, ...]:
    """Publish every default registry action as a Maya runtime command."""

    action_registry = registry or create_default_registry()
    return tuple(
        publish_action(action.id, label=action.label, cmds_module=cmds_module)
        for action in action_registry.actions()
    )


def publish_action(
    action_id: str,
    *,
    label: str = "",
    cmds_module: Any | None = None,
) -> PublishedCommand:
    """Publish one ActionRail action as a Maya runtime command and nameCommand."""

    runtime_name = runtime_command_name("action", action_id)
    name_command = name_command_name(runtime_name)
    annotation = label or f"Run ActionRail action {action_id}"
    command = f"import actionrail; actionrail.run_action({action_id!r})"
    _publish_runtime_command(
        runtime_name,
        command=command,
        annotation=annotation,
        label=label or action_id,
        cmds_module=cmds_module,
    )
    _publish_name_command(
        name_command,
        command=runtime_name,
        annotation=annotation,
        cmds_module=cmds_module,
    )
    return PublishedCommand("action", action_id, runtime_name, name_command)


def publish_preset_slots(
    preset_id: str,
    *,
    spec: StackSpec | None = None,
    cmds_module: Any | None = None,
) -> tuple[PublishedCommand, ...]:
    """Publish action-bearing slots from a built-in preset as Maya commands."""

    stack_spec = spec or get_example_spec(preset_id)
    return tuple(
        publish_slot(preset_id, item.id, label=item.label, cmds_module=cmds_module)
        for item in stack_spec.items
        if item.action
    )


def publish_slot(
    preset_id: str,
    slot_id: str,
    *,
    label: str = "",
    cmds_module: Any | None = None,
) -> PublishedCommand:
    """Publish one preset slot as a Maya runtime command and nameCommand."""

    target_id = slot_target_id(preset_id, slot_id)
    runtime_name = runtime_command_name("slot", target_id)
    name_command = name_command_name(runtime_name)
    annotation = label or f"Run ActionRail slot {preset_id}/{slot_id}"
    command = f"import actionrail; actionrail.run_slot({preset_id!r}, {slot_id!r})"
    _publish_runtime_command(
        runtime_name,
        command=command,
        annotation=annotation,
        label=label or slot_id,
        cmds_module=cmds_module,
    )
    _publish_name_command(
        name_command,
        command=runtime_name,
        annotation=annotation,
        cmds_module=cmds_module,
    )
    return PublishedCommand("slot", target_id, runtime_name, name_command)


def unpublish(command: PublishedCommand | str, *, cmds_module: Any | None = None) -> None:
    """Remove an ActionRail runtime command when possible."""

    runtime_name = command.runtime_command if isinstance(command, PublishedCommand) else command
    cmds = _require_cmds(cmds_module)
    if _runtime_command_exists(runtime_name, cmds):
        cmds.runTimeCommand(runtime_name, edit=True, delete=True)


def query_hotkey_binding(
    key: str,
    *,
    ctrl: bool = False,
    alt: bool = False,
    shift: bool = False,
    command: bool = False,
    release: bool = False,
    cmds_module: Any | None = None,
) -> HotkeyBinding | None:
    """Return the Maya nameCommand currently assigned to a key chord, if any."""

    cmds = _require_cmds(cmds_module)
    flag = "releaseName" if release else "name"
    name = cmds.hotkey(
        keyShortcut=key,
        query=True,
        ctrlModifier=ctrl,
        altModifier=alt,
        shiftModifier=shift,
        commandModifier=command,
        **{flag: True},
    )
    if not name:
        return None
    return HotkeyBinding(key, str(name), ctrl, alt, shift, command, release)


def assign_hotkey(
    name_command: str,
    key: str,
    *,
    ctrl: bool = False,
    alt: bool = False,
    shift: bool = False,
    command: bool = False,
    release: bool = False,
    overwrite: bool = False,
    cmds_module: Any | None = None,
) -> HotkeyBinding:
    """Assign a Maya hotkey after checking for an existing binding."""

    existing = query_hotkey_binding(
        key,
        ctrl=ctrl,
        alt=alt,
        shift=shift,
        command=command,
        release=release,
        cmds_module=cmds_module,
    )
    if existing is not None and existing.name != name_command and not overwrite:
        hotkey_text = format_hotkey(key, ctrl=ctrl, alt=alt, shift=shift, command=command)
        msg = f"Hotkey {hotkey_text} already uses {existing.name}"
        raise HotkeyConflictError(msg)

    cmds = _require_cmds(cmds_module)
    flag = "releaseName" if release else "name"
    cmds.hotkey(
        keyShortcut=key,
        ctrlModifier=ctrl,
        altModifier=alt,
        shiftModifier=shift,
        commandModifier=command,
        **{flag: name_command},
    )
    return HotkeyBinding(key, name_command, ctrl, alt, shift, command, release)


def runtime_command_name(kind: TargetKind, target_id: str) -> str:
    """Return the stable Maya runtime command name for an ActionRail target."""

    safe_target = re.sub(r"[^0-9A-Za-z_]+", "_", target_id).strip("_")
    return f"{COMMAND_PREFIX}_{kind}_{safe_target}"


def name_command_name(runtime_name: str) -> str:
    """Return the paired Maya nameCommand used for direct hotkey assignment."""

    return f"{runtime_name}_NameCommand"


def slot_target_id(preset_id: str, slot_id: str) -> str:
    """Return the stable command target id for a preset slot."""

    prefix = f"{preset_id}."
    if slot_id.startswith(prefix):
        return slot_id
    return f"{preset_id}.{slot_id}"


def format_hotkey(
    key: str,
    *,
    ctrl: bool = False,
    alt: bool = False,
    shift: bool = False,
    command: bool = False,
) -> str:
    """Format a key chord for human-readable conflict messages."""

    parts = []
    if ctrl:
        parts.append("Ctrl")
    if alt:
        parts.append("Alt")
    if shift:
        parts.append("Shift")
    if command:
        parts.append("Command")
    parts.append(key)
    return "+".join(parts)


def _publish_runtime_command(
    name: str,
    *,
    command: str,
    annotation: str,
    label: str,
    cmds_module: Any | None,
) -> None:
    cmds = _require_cmds(cmds_module)
    kwargs = {
        "annotation": annotation,
        "category": COMMAND_CATEGORY,
        "commandLanguage": "python",
        "command": command,
        "label": label,
        "showInHotkeyEditor": True,
    }
    if _runtime_command_exists(name, cmds):
        cmds.runTimeCommand(name, edit=True, **kwargs)
    else:
        cmds.runTimeCommand(name, **kwargs)


def _publish_name_command(
    name: str,
    *,
    command: str,
    annotation: str,
    cmds_module: Any | None,
) -> None:
    cmds = _require_cmds(cmds_module)
    cmds.nameCommand(name, annotation=annotation, command=command, sourceType="mel")


def _runtime_command_exists(name: str, cmds: Any) -> bool:
    return bool(cmds.runTimeCommand(name, exists=True))


def _require_cmds(cmds_module: Any | None = None) -> Any:
    if cmds_module is not None:
        return cmds_module

    try:
        import maya.cmds as cmds  # type: ignore[import-not-found]
    except Exception as exc:  # pragma: no cover - exercised only inside Maya.
        msg = "ActionRail hotkey publishing requires maya.cmds inside Maya."
        raise RuntimeError(msg) from exc
    return cmds
