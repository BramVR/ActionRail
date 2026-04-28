"""Maya runtime-command and hotkey bridge for ActionRail actions and slots."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Literal

from .actions import ActionRegistry, create_default_registry
from .spec import StackSpec, get_example_spec

COMMAND_PREFIX = "ActionRail"
COMMAND_CATEGORY = "ActionRail"
NAME_COMMAND_SUFFIX = "_NameCommand"

TargetKind = Literal["action", "slot"]

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
