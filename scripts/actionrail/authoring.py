"""Draft authoring model and safe user-preset storage for ActionRail."""

from __future__ import annotations

import json
import os
import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .spec import (
    RailAppearance,
    RailBackground,
    RailBorder,
    RailCollapse,
    RailLayout,
    RailSlotAppearance,
    StackItem,
    StackSpec,
    builtin_preset_ids,
    load_preset,
    parse_stack_spec,
)

_USER_PRESET_DIR_ENV = "ACTIONRAIL_USER_PRESET_DIR"
_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")

__all__ = [
    "DraftRail",
    "DraftSlot",
    "build_draft_spec",
    "load_user_preset",
    "save_user_preset",
    "spec_to_payload",
    "user_preset_dir",
    "user_preset_files",
    "user_preset_ids",
    "validate_preset_id",
]


@dataclass(frozen=True)
class DraftSlot:
    """Authoring-time slot data that maps to one persisted StackItem."""

    id: str
    label: str = ""
    action: str = ""
    type: str = "button"
    tone: str = "neutral"
    tooltip: str = ""
    key_label: str = ""
    visible_when: str = ""
    enabled_when: str = ""
    active_when: str = ""
    icon: str = ""
    size: int = 0


@dataclass(frozen=True)
class DraftRail:
    """Authoring-time rail data used before Quick Create gains a full UI."""

    id: str
    slots: tuple[DraftSlot, ...]
    layout: RailLayout = field(
        default_factory=lambda: RailLayout(anchor="viewport.left.center")
    )
    collapse: RailCollapse = field(default_factory=RailCollapse)
    appearance: RailAppearance = field(default_factory=RailAppearance)


def build_draft_spec(draft: DraftRail) -> StackSpec:
    """Convert a draft rail into a validated runtime spec."""

    return parse_stack_spec(draft_to_payload(draft), source=f"<draft:{draft.id}>")


def save_user_preset(
    draft_or_spec: DraftRail | StackSpec,
    *,
    preset_dir: str | Path | None = None,
    overwrite: bool = False,
) -> Path:
    """Validate and save a draft or spec into the user preset location."""

    spec = _as_valid_spec(draft_or_spec)
    validate_preset_id(spec.id)
    if spec.id in builtin_preset_ids():
        msg = f"User preset '{spec.id}' would overwrite a locked built-in preset."
        raise ValueError(msg)

    directory = user_preset_dir(preset_dir)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{spec.id}.json"
    if path.exists() and not overwrite:
        msg = (
            f"User preset '{spec.id}' already exists. "
            "Pass overwrite=True to replace it."
        )
        raise FileExistsError(msg)
    payload = spec_to_payload(spec)
    parse_stack_spec(payload, source=f"<save:{spec.id}>")
    temp_path = path.with_name(f"{path.name}.tmp")
    temp_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temp_path.replace(path)
    return path


def load_user_preset(
    preset_id: str,
    *,
    preset_dir: str | Path | None = None,
) -> StackSpec:
    """Load a user preset by id from the user preset location."""

    validate_preset_id(preset_id)
    if preset_id in builtin_preset_ids():
        msg = f"User preset '{preset_id}' would shadow a locked built-in preset."
        raise ValueError(msg)
    path = user_preset_dir(preset_dir) / f"{preset_id}.json"
    if not path.is_file():
        msg = f"Unknown ActionRail user preset: {preset_id}"
        raise KeyError(msg)
    spec = load_preset(path)
    if spec.id != preset_id:
        msg = (
            f"ActionRail user preset file '{path.name}' declares id '{spec.id}' "
            f"but was requested as '{preset_id}'."
        )
        raise ValueError(msg)
    return spec


def user_preset_ids(*, preset_dir: str | Path | None = None) -> tuple[str, ...]:
    """Return user preset ids discovered from JSON files in the user store."""

    return tuple(sorted(path.stem for path in user_preset_files(preset_dir=preset_dir)))


def user_preset_files(*, preset_dir: str | Path | None = None) -> tuple[Path, ...]:
    """Return JSON user preset files from the user preset location."""

    directory = user_preset_dir(preset_dir)
    if not directory.is_dir():
        return ()
    return tuple(sorted(path for path in directory.glob("*.json") if path.is_file()))


def user_preset_dir(preset_dir: str | Path | None = None) -> Path:
    """Return the ActionRail user preset directory."""

    if preset_dir is not None:
        return Path(preset_dir)
    env_path = os.environ.get(_USER_PRESET_DIR_ENV)
    if env_path:
        return Path(env_path)
    base = Path(os.environ.get("APPDATA") or Path.home())
    return base / "ActionRail" / "presets"


def validate_preset_id(preset_id: str) -> str:
    """Validate a preset or slot id fragment for file-safe storage."""

    if isinstance(preset_id, str) and _IDENTIFIER_PATTERN.fullmatch(preset_id):
        return preset_id
    msg = (
        "ActionRail preset ids must start with a letter or number and contain "
        "only letters, numbers, dots, underscores, or hyphens."
    )
    raise ValueError(msg)


def spec_to_payload(spec: StackSpec) -> dict[str, Any]:
    """Return the canonical JSON payload for a runtime spec."""

    return {
        "id": spec.id,
        "layout": _layout_to_payload(spec.layout),
        **_collapse_payload_entry(spec.collapse),
        **_appearance_payload_entry(spec.appearance),
        "items": [_item_to_payload(item) for item in spec.items],
    }


def draft_to_payload(draft: DraftRail) -> dict[str, Any]:
    """Return a JSON-like preset payload for an authoring draft."""

    validate_preset_id(draft.id)
    return {
        "id": draft.id,
        "layout": _layout_to_payload(draft.layout),
        **_collapse_payload_entry(draft.collapse),
        **_appearance_payload_entry(draft.appearance),
        "items": [_draft_slot_to_payload(draft.id, slot) for slot in draft.slots],
    }


def _as_valid_spec(draft_or_spec: DraftRail | StackSpec) -> StackSpec:
    if isinstance(draft_or_spec, DraftRail):
        return build_draft_spec(draft_or_spec)
    if isinstance(draft_or_spec, StackSpec):
        return parse_stack_spec(spec_to_payload(draft_or_spec), source=f"<spec:{draft_or_spec.id}>")
    msg = "ActionRail user presets can only be saved from DraftRail or StackSpec data."
    raise TypeError(msg)


def _layout_to_payload(layout: RailLayout) -> dict[str, object]:
    return {
        "anchor": layout.anchor,
        "orientation": layout.orientation,
        "rows": layout.rows,
        "columns": layout.columns,
        "offset": [layout.offset[0], layout.offset[1]],
        "scale": layout.scale,
        "opacity": layout.opacity,
        "locked": layout.locked,
    }


def _collapse_payload_entry(collapse: RailCollapse) -> dict[str, object]:
    if not _should_write_collapse(collapse):
        return {}
    payload: dict[str, object] = {"enabled": collapse.enabled}
    if collapse.edge != "left" or collapse.enabled:
        payload["edge"] = collapse.edge
    if collapse.handle_icon:
        payload["handle_icon"] = collapse.handle_icon
    if collapse.reveal_trigger != "click":
        payload["reveal_trigger"] = collapse.reveal_trigger
    if collapse.default_collapsed:
        payload["default_collapsed"] = collapse.default_collapsed
    return {"collapse": payload}


def _should_write_collapse(collapse: RailCollapse) -> bool:
    return (
        collapse.enabled
        or collapse.edge != "left"
        or bool(collapse.handle_icon)
        or collapse.reveal_trigger != "click"
        or collapse.default_collapsed
    )


def _appearance_payload_entry(appearance: RailAppearance) -> dict[str, object]:
    if not _should_write_appearance(appearance):
        return {}

    payload: dict[str, object] = {}
    if appearance.theme != "default":
        payload["theme"] = appearance.theme
    if not appearance.inherit_global:
        payload["inherit_global"] = appearance.inherit_global
    _add_optional_fields(
        payload,
        (
            ("accent", appearance.accent),
            ("secondary", appearance.secondary),
            ("text", appearance.text),
            ("muted_text", appearance.muted_text),
        ),
    )
    background = _background_to_payload(appearance.background)
    if background:
        payload["background"] = background
    border = _border_to_payload(appearance.border)
    if border:
        payload["border"] = border
    slots = _slots_to_payload(appearance.slots)
    if slots:
        payload["slots"] = slots
    return {"appearance": payload}


def _should_write_appearance(appearance: RailAppearance) -> bool:
    return appearance != RailAppearance()


def _background_to_payload(background: RailBackground) -> dict[str, object]:
    defaults = RailBackground()
    payload: dict[str, object] = {}
    if background.enabled != defaults.enabled:
        payload["enabled"] = background.enabled
    if background.color:
        payload["color"] = background.color
    if background.pattern != defaults.pattern:
        payload["pattern"] = background.pattern
    if background.pattern_color:
        payload["pattern_color"] = background.pattern_color
    if background.pattern_opacity != defaults.pattern_opacity:
        payload["pattern_opacity"] = background.pattern_opacity
    if background.pattern_scale != defaults.pattern_scale:
        payload["pattern_scale"] = background.pattern_scale
    return payload


def _border_to_payload(border: RailBorder) -> dict[str, object]:
    defaults = RailBorder()
    payload: dict[str, object] = {}
    if border.enabled != defaults.enabled:
        payload["enabled"] = border.enabled
    if border.color:
        payload["color"] = border.color
    if border.width is not None:
        payload["width"] = border.width
    return payload


def _slots_to_payload(slots: RailSlotAppearance) -> dict[str, object]:
    payload: dict[str, object] = {}
    _add_optional_fields(
        payload,
        (
            ("empty_background", slots.empty_background),
            ("empty_border", slots.empty_border),
            ("icon_backplate", slots.icon_backplate),
            ("icon_border", slots.icon_border),
            ("active", slots.active),
            ("text", slots.text),
        ),
    )
    return payload


def _draft_slot_to_payload(preset_id: str, slot: DraftSlot) -> dict[str, object]:
    validate_preset_id(slot.id)
    slot_id = _slot_item_id(preset_id, slot.id)
    if slot.type == "spacer":
        return {"type": "spacer", "id": slot_id, "size": slot.size}
    payload: dict[str, object] = {
        "type": slot.type,
        "id": slot_id,
        "label": slot.label,
    }
    _add_optional_fields(
        payload,
        (
            ("action", slot.action),
            ("tone", slot.tone),
            ("tooltip", slot.tooltip),
            ("key_label", slot.key_label),
            ("visible_when", slot.visible_when),
            ("enabled_when", slot.enabled_when),
            ("active_when", slot.active_when),
            ("icon", slot.icon),
        ),
    )
    return payload


def _item_to_payload(item: StackItem) -> dict[str, object]:
    if item.type == "spacer":
        return {"type": "spacer", "id": item.id, "size": item.size}
    payload: dict[str, object] = {
        "type": item.type,
        "id": item.id,
        "label": item.label,
    }
    _add_optional_fields(
        payload,
        (
            ("action", item.action),
            ("tone", item.tone),
            ("tooltip", item.tooltip),
            ("key_label", item.key_label),
            ("visible_when", item.visible_when),
            ("enabled_when", item.enabled_when),
            ("active_when", item.active_when),
            ("icon", item.icon),
        ),
    )
    return payload


def _add_optional_fields(
    payload: dict[str, object],
    fields: Iterable[tuple[str, str]],
) -> None:
    for key, value in fields:
        if value:
            payload[key] = value


def _slot_item_id(preset_id: str, slot_id: str) -> str:
    prefix = f"{preset_id}."
    return slot_id if slot_id.startswith(prefix) else f"{prefix}{slot_id}"
