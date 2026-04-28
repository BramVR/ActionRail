"""ActionRail stack specifications and JSON preset loading."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

TRANSFORM_STACK_ID = "transform_stack"
_PACKAGE_ROOT = Path(__file__).resolve().parents[2]
_PRESET_DIR = _PACKAGE_ROOT / "presets"


@dataclass(frozen=True)
class StackItem:
    type: str
    label: str = ""
    action: str = ""
    tone: str = "neutral"
    tooltip: str = ""
    size: int = 0


@dataclass(frozen=True)
class StackSpec:
    id: str
    anchor: str
    items: tuple[StackItem, ...]


def get_example_spec(example_id: str = TRANSFORM_STACK_ID) -> StackSpec:
    """Return a built-in example spec by id."""

    return load_builtin_preset(example_id)


def load_builtin_preset(preset_id: str) -> StackSpec:
    """Load a bundled JSON preset by id."""

    preset_path = _PRESET_DIR / f"{preset_id}.json"
    if not preset_path.is_file():
        msg = f"Unknown ActionRail example: {preset_id}"
        raise KeyError(msg)
    return load_preset(preset_path)


def load_preset(path: str | Path) -> StackSpec:
    """Load and validate an ActionRail stack spec from a JSON preset file."""

    preset_path = Path(path)
    try:
        with preset_path.open("r", encoding="utf-8") as stream:
            payload = json.load(stream)
    except json.JSONDecodeError as exc:
        msg = f"Invalid ActionRail preset JSON: {preset_path}"
        raise ValueError(msg) from exc

    return parse_stack_spec(payload, source=str(preset_path))


def parse_stack_spec(payload: Any, *, source: str = "<memory>") -> StackSpec:
    """Parse a JSON-like mapping into a validated stack spec."""

    if not isinstance(payload, dict):
        msg = f"ActionRail preset must be an object: {source}"
        raise ValueError(msg)

    spec_id = _required_string(payload, "id", source)
    anchor = _required_string(payload, "anchor", source)
    raw_items = payload.get("items")
    if not isinstance(raw_items, list) or not raw_items:
        msg = f"ActionRail preset items must be a non-empty list: {source}"
        raise ValueError(msg)

    items = tuple(_parse_item(item, index, source) for index, item in enumerate(raw_items))
    return StackSpec(id=spec_id, anchor=anchor, items=items)


def action_ids(spec: StackSpec) -> tuple[str, ...]:
    """Return all non-empty action ids referenced by a stack spec."""

    return tuple(item.action for item in spec.items if item.action)


def _parse_item(payload: Any, index: int, source: str) -> StackItem:
    if not isinstance(payload, dict):
        msg = f"ActionRail preset item {index} must be an object: {source}"
        raise ValueError(msg)

    item_type = _required_string(payload, "type", source, index=index)
    if item_type == "spacer":
        size = payload.get("size")
        if not isinstance(size, int) or size < 0:
            msg = f"ActionRail spacer item {index} requires a non-negative integer size: {source}"
            raise ValueError(msg)
        return StackItem(type=item_type, size=size)

    if item_type not in {"button", "toolButton"}:
        msg = f"Unsupported ActionRail item type '{item_type}' at item {index}: {source}"
        raise ValueError(msg)

    label = _required_string(payload, "label", source, index=index)
    action = _required_string(payload, "action", source, index=index)
    tone = _optional_string(payload, "tone", "neutral", source, index=index)
    tooltip = _optional_string(payload, "tooltip", "", source, index=index)
    return StackItem(
        type=item_type,
        label=label,
        action=action,
        tone=tone,
        tooltip=tooltip,
    )


def _required_string(
    payload: dict[str, Any],
    key: str,
    source: str,
    *,
    index: int | None = None,
) -> str:
    value = payload.get(key)
    if isinstance(value, str) and value:
        return value

    location = f" item {index}" if index is not None else ""
    msg = f"ActionRail preset{location} requires non-empty string '{key}': {source}"
    raise ValueError(msg)


def _optional_string(
    payload: dict[str, Any],
    key: str,
    default: str,
    source: str,
    *,
    index: int,
) -> str:
    value = payload.get(key, default)
    if isinstance(value, str):
        return value

    msg = f"ActionRail preset item {index} field '{key}' must be a string: {source}"
    raise ValueError(msg)
