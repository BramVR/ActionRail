"""WoW-style hover-to-bind workflow for ActionRail slots.

Purpose: keep the artist-facing binding flow centered on visible action slots
while reusing Maya runtime commands and nameCommands underneath.
Owns: bind-mode state, hovered slot target, session save/discard restoration.
Used by: future widget event filters, Maya menu commands, and tests.
Tests: `tests/test_bind_mode.py`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .hotkeys import (
    HotkeyBinding,
    _maya_key_shortcut,
    activate_hotkey_set,
    assign_hotkey,
    assign_slot_hotkey,
    current_hotkey_set,
    ensure_editable_hotkey_set,
    publish_slot,
    query_hotkey_binding,
    save_hotkey_preferences,
    slot_binding_targets,
)

__all__ = [
    "BindModeState",
    "HotkeyChord",
    "assign_hovered_hotkey",
    "bind_mode_state",
    "clear_hovered_hotkey",
    "enter_bind_mode",
    "exit_bind_mode",
    "select_bind_mode_slot",
    "toggle_bind_mode",
]


@dataclass(frozen=True)
class HotkeyChord:
    """A Maya hotkey chord captured from Bind Mode."""

    key: str
    ctrl: bool = False
    alt: bool = False
    shift: bool = False
    command: bool = False
    release: bool = False


@dataclass(frozen=True)
class BindModeState:
    """Public snapshot of the current Bind Mode state."""

    enabled: bool
    preset_id: str = ""
    slot_id: str = ""
    pending_change_count: int = 0


@dataclass
class _BindModeSession:
    enabled: bool = False
    preset_id: str = ""
    slot_id: str = ""
    user_preset_dir: str | Path | None = None
    original_hotkey_set: str = ""
    original_bindings: dict[HotkeyChord, HotkeyBinding | None] = field(default_factory=dict)
    original_slot_labels: dict[tuple[str, str], str] = field(default_factory=dict)


_SESSION = _BindModeSession()


def enter_bind_mode() -> BindModeState:
    """Start a slot-hover binding session."""

    _SESSION.enabled = True
    _refresh_bind_mode_visuals()
    return bind_mode_state()


def exit_bind_mode(
    *,
    save: bool = True,
    persist: bool = False,
    cmds_module: Any | None = None,
) -> BindModeState:
    """End Bind Mode, optionally discarding assignments made during the session."""

    if _SESSION.enabled and not save:
        _restore_session(cmds_module=cmds_module)
        _restore_original_hotkey_set(cmds_module=cmds_module)
    elif _SESSION.enabled and save and persist and _SESSION.original_bindings:
        save_hotkey_preferences(cmds_module=cmds_module)
    _SESSION.enabled = False
    _SESSION.preset_id = ""
    _SESSION.slot_id = ""
    _SESSION.user_preset_dir = None
    _SESSION.original_hotkey_set = ""
    _SESSION.original_bindings.clear()
    _SESSION.original_slot_labels.clear()
    _refresh_bind_mode_visuals()
    return bind_mode_state()


def toggle_bind_mode(*, cmds_module: Any | None = None) -> BindModeState:
    """Toggle Bind Mode on or off."""

    if _SESSION.enabled:
        return exit_bind_mode(save=True, cmds_module=cmds_module)
    return enter_bind_mode()


def bind_mode_state() -> BindModeState:
    """Return the current bind-mode state."""

    return BindModeState(
        enabled=_SESSION.enabled,
        preset_id=_SESSION.preset_id,
        slot_id=_SESSION.slot_id,
        pending_change_count=len(_SESSION.original_bindings),
    )


def select_bind_mode_slot(
    preset_id: str,
    slot_id: str,
    *,
    user_preset_dir: str | Path | None = None,
) -> BindModeState:
    """Set the visible slot that will receive the next captured hotkey."""

    _SESSION.preset_id = preset_id
    _SESSION.slot_id = _slot_suffix(preset_id, slot_id)
    _SESSION.user_preset_dir = user_preset_dir
    _refresh_bind_mode_visuals()
    return bind_mode_state()


def assign_hovered_hotkey(
    key: str,
    *,
    ctrl: bool = False,
    alt: bool = False,
    shift: bool = False,
    command: bool = False,
    release: bool = False,
    overwrite: bool = True,
    cmds_module: Any | None = None,
) -> HotkeyBinding:
    """Assign a captured hotkey chord to the currently selected Bind Mode slot."""

    _require_active_slot()
    _ensure_session_hotkey_set(cmds_module=cmds_module)
    chord = HotkeyChord(key, ctrl, alt, shift, command, release)
    _remember_chord(chord, cmds_module=cmds_module)
    _remember_slot_label(
        _SESSION.preset_id,
        _SESSION.slot_id,
        user_preset_dir=_SESSION.user_preset_dir,
    )
    binding = assign_slot_hotkey(
        _SESSION.preset_id,
        _SESSION.slot_id,
        key,
        ctrl=ctrl,
        alt=alt,
        shift=shift,
        command=command,
        release=release,
        overwrite=overwrite,
        sync_visible=True,
        user_preset_dir=_SESSION.user_preset_dir,
        cmds_module=cmds_module,
    )
    _refresh_bind_mode_visuals()
    return binding


def clear_hovered_hotkey(*, cmds_module: Any | None = None) -> bool:
    """Clear the visible key label for the currently selected Bind Mode slot."""

    _require_active_slot()
    preset_id = _SESSION.preset_id
    slot_id = _SESSION.slot_id
    _ensure_session_hotkey_set(cmds_module=cmds_module)
    _remember_slot_label(preset_id, slot_id, user_preset_dir=_SESSION.user_preset_dir)
    published = publish_slot(
        preset_id,
        slot_id,
        user_preset_dir=_SESSION.user_preset_dir,
        cmds_module=cmds_module,
    )
    target = _binding_target(preset_id, slot_id, user_preset_dir=_SESSION.user_preset_dir)
    chord = _parse_hotkey_label(target.key_label if target is not None else "")
    if chord is not None:
        _remember_chord(chord, cmds_module=cmds_module)
        existing = query_hotkey_binding(
            chord.key,
            ctrl=chord.ctrl,
            alt=chord.alt,
            shift=chord.shift,
            command=chord.command,
            release=chord.release,
            cmds_module=cmds_module,
        )
        if existing is not None and existing.name == published.name_command:
            _clear_hotkey(chord, cmds_module=cmds_module)

    from .runtime import update_slot_key_label

    update_slot_key_label(preset_id, slot_id, "")
    _refresh_bind_mode_visuals()
    return True


def _refresh_bind_mode_visuals() -> None:
    from .runtime import refresh_bind_mode_visuals

    refresh_bind_mode_visuals(
        enabled=_SESSION.enabled,
        preset_id=_SESSION.preset_id,
        slot_id=_SESSION.slot_id,
        pending_change_count=len(_SESSION.original_bindings),
    )


def _restore_session(*, cmds_module: Any | None = None) -> None:
    _ensure_session_hotkey_set(cmds_module=cmds_module)
    for chord, binding in _SESSION.original_bindings.items():
        if binding is None:
            _clear_hotkey(chord, cmds_module=cmds_module)
            continue
        assign_hotkey(
            binding.name,
            chord.key,
            ctrl=chord.ctrl,
            alt=chord.alt,
            shift=chord.shift,
            command=chord.command,
            release=chord.release,
            overwrite=True,
            cmds_module=cmds_module,
        )

    from .runtime import update_slot_key_label

    for (preset_id, slot_id), key_label in _SESSION.original_slot_labels.items():
        update_slot_key_label(preset_id, slot_id, key_label)


def _ensure_session_hotkey_set(*, cmds_module: Any | None = None) -> None:
    if not _SESSION.original_hotkey_set:
        try:
            _SESSION.original_hotkey_set = current_hotkey_set(cmds_module=cmds_module)
        except RuntimeError:
            _SESSION.original_hotkey_set = ""
    ensure_editable_hotkey_set(cmds_module=cmds_module)


def _restore_original_hotkey_set(*, cmds_module: Any | None = None) -> None:
    if not _SESSION.original_hotkey_set:
        return
    try:
        if current_hotkey_set(cmds_module=cmds_module) != _SESSION.original_hotkey_set:
            activate_hotkey_set(_SESSION.original_hotkey_set, cmds_module=cmds_module)
    except RuntimeError:
        return


def _remember_chord(
    chord: HotkeyChord,
    *,
    cmds_module: Any | None = None,
) -> None:
    if chord in _SESSION.original_bindings:
        return
    _SESSION.original_bindings[chord] = query_hotkey_binding(
        chord.key,
        ctrl=chord.ctrl,
        alt=chord.alt,
        shift=chord.shift,
        command=chord.command,
        release=chord.release,
        cmds_module=cmds_module,
    )


def _remember_slot_label(
    preset_id: str,
    slot_id: str,
    *,
    user_preset_dir: str | Path | None = None,
) -> None:
    key = (preset_id, slot_id)
    if key in _SESSION.original_slot_labels:
        return
    target = _binding_target(preset_id, slot_id, user_preset_dir=user_preset_dir)
    _SESSION.original_slot_labels[key] = target.key_label if target is not None else ""


def _binding_target(
    preset_id: str,
    slot_id: str,
    *,
    user_preset_dir: str | Path | None = None,
):
    target_id = f"{preset_id}.{_slot_suffix(preset_id, slot_id)}"
    try:
        targets = slot_binding_targets(
            preset_id,
            user_preset_dir=user_preset_dir,
            include_empty=True,
        )
    except Exception:
        targets = _active_overlay_binding_targets(preset_id, user_preset_dir=user_preset_dir)
    for target in targets:
        if target.target_id == target_id:
            return target
    return None


def _active_overlay_binding_targets(
    preset_id: str,
    *,
    user_preset_dir: str | Path | None = None,
):
    from . import runtime

    host = getattr(runtime, "_OVERLAYS", {}).get(preset_id)
    spec = getattr(host, "spec", None)
    if spec is None:
        return ()
    return slot_binding_targets(
        preset_id,
        spec=spec,
        user_preset_dir=user_preset_dir,
        include_empty=True,
    )


def _clear_hotkey(chord: HotkeyChord, *, cmds_module: Any | None = None) -> None:
    _ensure_session_hotkey_set(cmds_module=cmds_module)
    cmds = _require_cmds(cmds_module)
    flag = "releaseName" if chord.release else "name"
    cmds.hotkey(
        keyShortcut=_maya_key_shortcut(chord.key),
        ctrlModifier=chord.ctrl,
        altModifier=chord.alt,
        shiftModifier=chord.shift,
        commandModifier=chord.command,
        **{flag: ""},
    )


def _parse_hotkey_label(label: str) -> HotkeyChord | None:
    if not label.strip():
        return None
    parts = [part.strip() for part in label.split("+") if part.strip()]
    if not parts:
        return None
    release = False
    key = parts[-1]
    if key.endswith(" Up"):
        key = key.removesuffix(" Up").strip()
        release = True
    modifiers = {part.lower() for part in parts[:-1]}
    return HotkeyChord(
        key,
        ctrl="ctrl" in modifiers or "control" in modifiers,
        alt="alt" in modifiers,
        shift="shift" in modifiers,
        command="command" in modifiers or "cmd" in modifiers or "meta" in modifiers,
        release=release,
    )


def _slot_suffix(preset_id: str, slot_id: str) -> str:
    prefix = f"{preset_id}."
    if slot_id.startswith(prefix):
        return slot_id.removeprefix(prefix)
    return slot_id


def _require_active_slot() -> None:
    if not _SESSION.enabled:
        msg = "ActionRail Bind Mode is not active."
        raise RuntimeError(msg)
    if not _SESSION.preset_id or not _SESSION.slot_id:
        msg = "No ActionRail slot is selected for Bind Mode."
        raise RuntimeError(msg)


def _require_cmds(cmds_module: Any | None = None) -> Any:
    if cmds_module is not None:
        return cmds_module
    try:
        import maya.cmds as cmds  # type: ignore[import-not-found]
    except Exception as exc:  # pragma: no cover - Maya-only path.
        msg = "ActionRail Bind Mode hotkey capture requires maya.cmds inside Maya."
        raise RuntimeError(msg) from exc
    return cmds
