"""Maya runtime-command and hotkey bridge for ActionRail actions and slots.

Purpose: make ActionRail actions and preset slots visible to Maya's hotkey
system without requiring an overlay to be open.
Owns: runtime-command names, nameCommands, conflict checks, visible key labels.
Used by: future Bind Mode, user hotkey publishing, Maya smoke verification.
Tests: `tests/test_hotkeys.py` and hotkey smoke scripts.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from typing import Any, Literal

from .actions import ActionRegistry, create_default_registry
from .spec import StackSpec, get_example_spec

COMMAND_PREFIX = "ActionRail"
COMMAND_CATEGORY = "ActionRail"
NAME_COMMAND_SUFFIX = "_NameCommand"

TargetKind = Literal["action", "slot"]

__all__ = [
    "COMMAND_CATEGORY",
    "COMMAND_PREFIX",
    "NAME_COMMAND_SUFFIX",
    "CommandSyncResult",
    "HotkeyBinding",
    "HotkeyConflictError",
    "PublishedCommand",
    "TargetKind",
    "assign_hotkey",
    "assign_published_hotkey",
    "assign_slot_hotkey",
    "clear_visible_key_label",
    "clear_visible_published_key_label",
    "format_hotkey",
    "list_published_commands",
    "name_command_name",
    "publish_action",
    "publish_default_actions",
    "publish_preset_slots",
    "publish_slot",
    "query_hotkey_binding",
    "runtime_command_name",
    "slot_target_id",
    "sync_default_actions",
    "sync_preset_slots",
    "sync_visible_key_label",
    "unpublish",
]

_PUBLISHED_BY_NAME_COMMAND: dict[str, PublishedCommand] = {}
_PUBLISHED_BY_HOTKEY: dict[tuple[str, bool, bool, bool, bool, bool], PublishedCommand] = {}


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


@dataclass(frozen=True)
class CommandSyncResult:
    """Published and removed Maya commands from one ActionRail sync pass."""

    published: tuple[PublishedCommand, ...]
    unpublished: tuple[PublishedCommand, ...]


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


def sync_default_actions(
    *,
    registry: ActionRegistry | None = None,
    cmds_module: Any | None = None,
) -> CommandSyncResult:
    """Publish current actions and remove stale ActionRail action commands."""

    action_registry = registry or create_default_registry()
    published = publish_default_actions(registry=action_registry, cmds_module=cmds_module)
    expected_runtime_commands = {command.runtime_command for command in published}
    stale = tuple(
        command
        for command in list_published_commands(
            target_kind="action",
            cmds_module=cmds_module,
        )
        if command.runtime_command not in expected_runtime_commands
    )
    for command in stale:
        unpublish(command, cmds_module=cmds_module)
    return CommandSyncResult(published=published, unpublished=stale)


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
    return _remember_published(PublishedCommand("action", action_id, runtime_name, name_command))


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


def sync_preset_slots(
    preset_id: str,
    *,
    spec: StackSpec | None = None,
    cmds_module: Any | None = None,
) -> CommandSyncResult:
    """Publish current preset slots and remove stale slot runtime commands."""

    stack_spec = spec or get_example_spec(preset_id)
    published = publish_preset_slots(preset_id, spec=stack_spec, cmds_module=cmds_module)
    expected_runtime_commands = {command.runtime_command for command in published}
    stale = tuple(
        command
        for command in list_published_commands(
            target_kind="slot",
            preset_id=preset_id,
            cmds_module=cmds_module,
        )
        if command.runtime_command not in expected_runtime_commands
    )
    for command in stale:
        unpublish(command, cmds_module=cmds_module)
    return CommandSyncResult(published=published, unpublished=stale)


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
    command = f"import actionrail; actionrail.run_slot({preset_id!r}, {target_id!r})"
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
    return _remember_published(PublishedCommand("slot", target_id, runtime_name, name_command))


def unpublish(command: PublishedCommand | str, *, cmds_module: Any | None = None) -> None:
    """Remove an ActionRail runtime command when possible."""

    runtime_name = command.runtime_command if isinstance(command, PublishedCommand) else command
    cmds = _require_cmds(cmds_module)
    if _runtime_command_exists(runtime_name, cmds):
        cmds.runTimeCommand(runtime_name, edit=True, delete=True)
    if isinstance(command, PublishedCommand):
        _forget_published(command)


def list_published_commands(
    *,
    target_kind: TargetKind | None = None,
    preset_id: str = "",
    cmds_module: Any | None = None,
) -> tuple[PublishedCommand, ...]:
    """Return ActionRail runtime commands that can be safely identified."""

    cmds = _require_cmds(cmds_module)
    commands: list[PublishedCommand] = []
    for runtime_name in _runtime_command_names(cmds):
        if not runtime_name.startswith(f"{COMMAND_PREFIX}_"):
            continue
        published = _published_command_from_runtime(runtime_name, cmds)
        if published is None:
            continue
        if target_kind is not None and published.target_kind != target_kind:
            continue
        if preset_id and (
            published.target_kind != "slot"
            or _split_slot_target_id(published.target_id)[0] != preset_id
        ):
            continue
        commands.append(published)
    return tuple(commands)


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
        key,
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


def assign_published_hotkey(
    published: PublishedCommand,
    key: str,
    *,
    ctrl: bool = False,
    alt: bool = False,
    shift: bool = False,
    command: bool = False,
    release: bool = False,
    overwrite: bool = False,
    sync_visible: bool = True,
    cmds_module: Any | None = None,
) -> HotkeyBinding:
    """Assign a hotkey to a published command and refresh visible slot labels."""

    previous = query_hotkey_binding(
        key,
        ctrl=ctrl,
        alt=alt,
        shift=shift,
        command=command,
        release=release,
        cmds_module=cmds_module,
    )
    previous_published = _PUBLISHED_BY_HOTKEY.get(
        _hotkey_cache_key(
            key,
            ctrl=ctrl,
            alt=alt,
            shift=shift,
            command=command,
            release=release,
        )
    )
    binding = assign_hotkey(
        published.name_command,
        key,
        ctrl=ctrl,
        alt=alt,
        shift=shift,
        command=command,
        release=release,
        overwrite=overwrite,
        cmds_module=cmds_module,
    )
    _remember_hotkey_binding(published, binding)
    if sync_visible:
        if (
            previous_published is not None
            and previous_published.name_command != published.name_command
        ):
            clear_visible_published_key_label(previous_published)
        elif previous is not None and previous.name != published.name_command:
            clear_visible_key_label(previous.name)
        sync_visible_key_label(published, binding)
    return binding


def assign_slot_hotkey(
    preset_id: str,
    slot_id: str,
    key: str,
    *,
    ctrl: bool = False,
    alt: bool = False,
    shift: bool = False,
    command: bool = False,
    release: bool = False,
    overwrite: bool = False,
    label: str = "",
    sync_visible: bool = True,
    cmds_module: Any | None = None,
) -> HotkeyBinding:
    """Publish a preset slot, assign its hotkey, and refresh its visible key label."""

    published = publish_slot(preset_id, slot_id, label=label, cmds_module=cmds_module)
    return assign_published_hotkey(
        published,
        key,
        ctrl=ctrl,
        alt=alt,
        shift=shift,
        command=command,
        release=release,
        overwrite=overwrite,
        sync_visible=sync_visible,
        cmds_module=cmds_module,
    )


def sync_visible_key_label(
    published: PublishedCommand,
    binding: HotkeyBinding,
) -> int:
    """Refresh visible overlay key labels for a slot command assignment."""

    if published.target_kind != "slot":
        return 0

    preset_id, slot_id = _split_slot_target_id(published.target_id)
    if not preset_id or not slot_id:
        return 0

    from .runtime import update_slot_key_label

    return update_slot_key_label(preset_id, slot_id, _binding_label(binding))


def clear_visible_key_label(name_command: str) -> int:
    """Clear visible overlay key labels for a previously bound ActionRail slot."""

    published = _published_command_from_name_command(name_command)
    if published is None:
        return 0
    return clear_visible_published_key_label(published)


def clear_visible_published_key_label(published: PublishedCommand) -> int:
    """Clear visible overlay key labels for a published ActionRail slot."""

    if published is None or published.target_kind != "slot":
        return 0

    preset_id, slot_id = _split_slot_target_id(published.target_id)
    if not preset_id or not slot_id:
        return 0

    from .runtime import update_slot_key_label

    return update_slot_key_label(preset_id, slot_id, "")


def runtime_command_name(kind: TargetKind, target_id: str) -> str:
    """Return the stable Maya runtime command name for an ActionRail target."""

    safe_target = re.sub(r"[^0-9A-Za-z_]+", "_", target_id).strip("_")
    return f"{COMMAND_PREFIX}_{kind}_{safe_target}"


def name_command_name(runtime_name: str) -> str:
    """Return the paired Maya nameCommand used for direct hotkey assignment."""

    return f"{runtime_name}{NAME_COMMAND_SUFFIX}"


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


def _binding_label(binding: HotkeyBinding) -> str:
    label = format_hotkey(
        binding.key,
        ctrl=binding.ctrl,
        alt=binding.alt,
        shift=binding.shift,
        command=binding.command,
    )
    if binding.release:
        return f"{label} Up"
    return label


def _split_slot_target_id(target_id: str) -> tuple[str, str]:
    preset_id, separator, slot_suffix = target_id.partition(".")
    if not separator:
        return "", ""
    return preset_id, slot_suffix


def _remember_published(command: PublishedCommand) -> PublishedCommand:
    _PUBLISHED_BY_NAME_COMMAND[command.name_command] = command
    return command


def _forget_published(command: PublishedCommand) -> None:
    _PUBLISHED_BY_NAME_COMMAND.pop(command.name_command, None)
    for cache_key, cached_command in tuple(_PUBLISHED_BY_HOTKEY.items()):
        if cached_command.name_command == command.name_command:
            _PUBLISHED_BY_HOTKEY.pop(cache_key, None)


def _remember_hotkey_binding(command: PublishedCommand, binding: HotkeyBinding) -> None:
    _PUBLISHED_BY_HOTKEY[
        _hotkey_cache_key(
            binding.key,
            ctrl=binding.ctrl,
            alt=binding.alt,
            shift=binding.shift,
            command=binding.command,
            release=binding.release,
        )
    ] = command


def _hotkey_cache_key(
    key: str,
    *,
    ctrl: bool = False,
    alt: bool = False,
    shift: bool = False,
    command: bool = False,
    release: bool = False,
) -> tuple[str, bool, bool, bool, bool, bool]:
    return (key, ctrl, alt, shift, command, release)


def _published_command_from_name_command(name_command: str) -> PublishedCommand | None:
    if name_command in _PUBLISHED_BY_NAME_COMMAND:
        return _PUBLISHED_BY_NAME_COMMAND[name_command]

    if not name_command.endswith(NAME_COMMAND_SUFFIX):
        return None

    runtime_name = name_command[: -len(NAME_COMMAND_SUFFIX)]
    slot_prefix = f"{COMMAND_PREFIX}_slot_"
    if not runtime_name.startswith(slot_prefix):
        return None

    return _published_slot_from_runtime_fallback(runtime_name, name_command, slot_prefix)


def _published_slot_from_runtime_fallback(
    runtime_name: str,
    name_command: str,
    slot_prefix: str,
) -> PublishedCommand | None:
    # Fallback for persisted generated commands when the current Python session
    # did not publish them first. Try all underscore splits against built-in specs.
    target_parts = runtime_name.removeprefix(slot_prefix).split("_")
    for split_index in range(1, len(target_parts)):
        preset_id = "_".join(target_parts[:split_index])
        slot_id = "_".join(target_parts[split_index:])
        target_id = slot_target_id(preset_id, slot_id)
        try:
            spec = get_example_spec(preset_id)
        except KeyError:
            continue
        if any(item.id == target_id for item in spec.items):
            return PublishedCommand("slot", target_id, runtime_name, name_command)
    return None


def _clear_published_cache() -> None:
    """Clear published command memory for tests."""

    _PUBLISHED_BY_NAME_COMMAND.clear()
    _PUBLISHED_BY_HOTKEY.clear()


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
    try:
        cmds.nameCommand(name, annotation=annotation, command=command, sourceType="mel")
    except RuntimeError as exc:
        if _is_duplicate_name_command_error(exc):
            return
        raise


def _runtime_command_exists(name: str, cmds: Any) -> bool:
    return bool(cmds.runTimeCommand(name, exists=True))


def _runtime_command_names(cmds: Any) -> tuple[str, ...]:
    names = cmds.runTimeCommand(query=True, userCommandArray=True) or ()
    if isinstance(names, str):
        return (names,)
    return tuple(str(name) for name in names)


def _published_command_from_runtime(runtime_name: str, cmds: Any) -> PublishedCommand | None:
    try:
        command_text = cmds.runTimeCommand(runtime_name, query=True, command=True)
    except RuntimeError:
        return None
    if not command_text:
        return None

    parsed = _parse_published_command_text(str(command_text))
    if parsed is None:
        return None

    target_kind, target_id = parsed
    expected_name = runtime_command_name(target_kind, target_id)
    if runtime_name != expected_name:
        return None
    return PublishedCommand(
        target_kind,
        target_id,
        runtime_name,
        name_command_name(runtime_name),
    )


def _parse_published_command_text(command_text: str) -> tuple[TargetKind, str] | None:
    try:
        module = ast.parse(command_text)
    except SyntaxError:
        return None

    for node in ast.walk(module):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Attribute):
            continue
        if not isinstance(node.func.value, ast.Name) or node.func.value.id != "actionrail":
            continue
        if node.func.attr == "run_action" and len(node.args) == 1:
            action_id = _literal_string(node.args[0])
            if action_id:
                return "action", action_id
        if node.func.attr == "run_slot" and len(node.args) == 2:
            preset_id = _literal_string(node.args[0])
            slot_id = _literal_string(node.args[1])
            if preset_id and slot_id:
                return "slot", slot_target_id(preset_id, slot_id)
    return None


def _literal_string(node: ast.AST) -> str:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return ""


def _is_duplicate_name_command_error(exc: RuntimeError) -> bool:
    error_text = str(exc).lower()
    return "namecommand" in error_text and (
        "already" in error_text or "exists" in error_text or "duplicate" in error_text
    )


def _require_cmds(cmds_module: Any | None = None) -> Any:
    if cmds_module is not None:
        return cmds_module

    try:
        import maya.cmds as cmds  # type: ignore[import-not-found]
    except Exception as exc:  # pragma: no cover - exercised only inside Maya.
        msg = "ActionRail hotkey publishing requires maya.cmds inside Maya."
        raise RuntimeError(msg) from exc
    return cmds
