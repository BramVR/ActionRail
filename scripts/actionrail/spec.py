"""ActionRail stack specifications and JSON preset loading."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

TRANSFORM_STACK_ID = "transform_stack"
MAX_LAYOUT_COLUMNS = 99
MAX_LAYOUT_OFFSET = 5000
MAX_LAYOUT_ROWS = 99
MAX_LAYOUT_SCALE = 10.0
_PACKAGE_ROOT = Path(__file__).resolve().parents[2]
_PRESET_DIR = _PACKAGE_ROOT / "presets"

__all__ = [
    "MAX_LAYOUT_COLUMNS",
    "MAX_LAYOUT_OFFSET",
    "MAX_LAYOUT_ROWS",
    "MAX_LAYOUT_SCALE",
    "TRANSFORM_STACK_ID",
    "RailCollapse",
    "RailLayout",
    "StackItem",
    "StackSpec",
    "action_ids",
    "builtin_preset_ids",
    "get_example_spec",
    "load_builtin_preset",
    "load_preset",
    "parse_stack_spec",
]


@dataclass(frozen=True)
class StackItem:
    type: str
    id: str = ""
    label: str = ""
    action: str = ""
    tone: str = "neutral"
    tooltip: str = ""
    size: int = 0
    key_label: str = ""
    visible_when: str = ""
    enabled_when: str = ""
    active_when: str = ""
    icon: str = ""


@dataclass(frozen=True)
class RailCollapse:
    enabled: bool = False
    edge: str = "left"
    handle_icon: str = ""
    reveal_trigger: str = "click"
    default_collapsed: bool = False


@dataclass(frozen=True)
class RailLayout:
    anchor: str
    orientation: str = "vertical"
    rows: int = 1
    columns: int = 1
    offset: tuple[int, int] = (0, 0)
    scale: float = 1.0
    opacity: float = 1.0
    locked: bool = False


@dataclass(frozen=True)
class StackSpec:
    id: str
    layout: RailLayout
    items: tuple[StackItem, ...]
    collapse: RailCollapse = field(default_factory=RailCollapse)

    @property
    def anchor(self) -> str:
        """Return the rail anchor for compatibility with Phase 0 callers."""

        return self.layout.anchor


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


def builtin_preset_ids() -> tuple[str, ...]:
    """Return bundled preset ids discovered from the preset directory."""

    return tuple(sorted(path.stem for path in _PRESET_DIR.glob("*.json") if path.is_file()))


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
    layout = _parse_layout(payload, source)
    collapse = _parse_collapse(payload, layout, source)
    raw_items = payload.get("items")
    if not isinstance(raw_items, list) or not raw_items:
        msg = f"ActionRail preset items must be a non-empty list: {source}"
        raise ValueError(msg)

    items = tuple(_parse_item(item, index, source, spec_id) for index, item in enumerate(raw_items))
    _validate_unique_item_ids(items, source)
    return StackSpec(id=spec_id, layout=layout, items=items, collapse=collapse)


def action_ids(spec: StackSpec) -> tuple[str, ...]:
    """Return all non-empty action ids referenced by a stack spec."""

    return tuple(item.action for item in spec.items if item.action)


def _parse_layout(payload: dict[str, Any], source: str) -> RailLayout:
    raw_layout = payload.get("layout", {})
    if raw_layout is None:
        raw_layout = {}
    if not isinstance(raw_layout, dict):
        msg = f"ActionRail preset layout must be an object: {source}"
        raise ValueError(msg)

    anchor_value = raw_layout.get("anchor", payload.get("anchor"))
    if not isinstance(anchor_value, str) or not anchor_value:
        msg = f"ActionRail preset requires non-empty string 'anchor': {source}"
        raise ValueError(msg)

    orientation = _optional_string(
        raw_layout,
        "orientation",
        "vertical",
        source,
        location=" layout",
    )
    if orientation not in {"vertical", "horizontal"}:
        msg = f"ActionRail preset layout orientation must be 'vertical' or 'horizontal': {source}"
        raise ValueError(msg)

    rows = _optional_positive_int(raw_layout, "rows", 1, source, maximum=MAX_LAYOUT_ROWS)
    columns = _optional_positive_int(
        raw_layout,
        "columns",
        1,
        source,
        maximum=MAX_LAYOUT_COLUMNS,
    )
    offset = _optional_offset(raw_layout, source)
    scale = _optional_number(
        raw_layout,
        "scale",
        1.0,
        source,
        minimum=0.1,
        maximum=MAX_LAYOUT_SCALE,
    )
    opacity = _optional_number(raw_layout, "opacity", 1.0, source, minimum=0.0, maximum=1.0)
    locked = raw_layout.get("locked", False)
    if not isinstance(locked, bool):
        msg = f"ActionRail preset layout field 'locked' must be a boolean: {source}"
        raise ValueError(msg)

    return RailLayout(
        anchor=anchor_value,
        orientation=orientation,
        rows=rows,
        columns=columns,
        offset=offset,
        scale=scale,
        opacity=opacity,
        locked=locked,
    )


def _parse_collapse(payload: dict[str, Any], layout: RailLayout, source: str) -> RailCollapse:
    raw_collapse = payload.get("collapse", {})
    if raw_collapse is None:
        raw_collapse = {}
    if not isinstance(raw_collapse, dict):
        msg = f"ActionRail preset collapse must be an object: {source}"
        raise ValueError(msg)

    enabled = raw_collapse.get("enabled", False)
    if not isinstance(enabled, bool):
        msg = f"ActionRail preset collapse field 'enabled' must be a boolean: {source}"
        raise ValueError(msg)

    edge = _optional_string(
        raw_collapse,
        "edge",
        _edge_from_anchor(layout.anchor),
        source,
        location=" collapse",
    )
    if edge not in {"left", "right", "top", "bottom"}:
        msg = (
            "ActionRail preset collapse field 'edge' must be one of "
            f"'left', 'right', 'top', or 'bottom': {source}"
        )
        raise ValueError(msg)

    handle_icon = _optional_string(
        raw_collapse,
        "handle_icon",
        "",
        source,
        location=" collapse",
    )
    reveal_trigger = _optional_string(
        raw_collapse,
        "reveal_trigger",
        "click",
        source,
        location=" collapse",
    )
    if reveal_trigger not in {"click", "hover"}:
        msg = (
            "ActionRail preset collapse field 'reveal_trigger' must be "
            f"'click' or 'hover': {source}"
        )
        raise ValueError(msg)

    default_collapsed = raw_collapse.get("default_collapsed", False)
    if not isinstance(default_collapsed, bool):
        msg = (
            "ActionRail preset collapse field 'default_collapsed' must be a "
            f"boolean: {source}"
        )
        raise ValueError(msg)

    return RailCollapse(
        enabled=enabled,
        edge=edge,
        handle_icon=handle_icon,
        reveal_trigger=reveal_trigger,
        default_collapsed=default_collapsed,
    )


def _parse_item(payload: Any, index: int, source: str, spec_id: str) -> StackItem:
    if not isinstance(payload, dict):
        msg = f"ActionRail preset item {index} must be an object: {source}"
        raise ValueError(msg)

    item_type = _required_string(payload, "type", source, index=index)
    item_id = _optional_string(
        payload,
        "id",
        _default_item_id(spec_id, index, payload),
        source,
        index=index,
    )
    if item_type == "spacer":
        size = payload.get("size")
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            msg = f"ActionRail spacer item {index} requires a non-negative integer size: {source}"
            raise ValueError(msg)
        return StackItem(type=item_type, id=item_id, size=size)

    if item_type not in {"button", "toolButton"}:
        msg = f"Unsupported ActionRail item type '{item_type}' at item {index}: {source}"
        raise ValueError(msg)

    label = _optional_string(payload, "label", "", source, index=index)
    action = _optional_string(payload, "action", "", source, index=index)
    icon = _optional_string(payload, "icon", "", source, index=index)
    tone = _optional_string(payload, "tone", "neutral", source, index=index)
    tooltip = _optional_string(payload, "tooltip", "", source, index=index)
    key_label = _optional_string(payload, "key_label", "", source, index=index)
    visible_when = _optional_predicate(payload, "visible_when", source, index)
    enabled_when = _optional_predicate(payload, "enabled_when", source, index)
    active_when = _optional_predicate(payload, "active_when", source, index)
    return StackItem(
        type=item_type,
        id=item_id,
        label=label,
        action=action,
        icon=icon,
        tone=tone,
        tooltip=tooltip,
        key_label=key_label,
        visible_when=visible_when,
        enabled_when=enabled_when,
        active_when=active_when,
    )


def _default_item_id(spec_id: str, index: int, payload: dict[str, Any]) -> str:
    item_type = payload.get("type")
    action = payload.get("action")
    if isinstance(action, str) and action:
        suffix = action.replace(".", "_")
    elif isinstance(item_type, str) and item_type:
        suffix = item_type
    else:
        suffix = "item"
    return f"{spec_id}.{index}.{suffix}"


def _validate_unique_item_ids(items: tuple[StackItem, ...], source: str) -> None:
    seen: set[str] = set()
    for item in items:
        if item.id in seen:
            msg = f"ActionRail preset item ids must be unique; duplicate id '{item.id}': {source}"
            raise ValueError(msg)
        seen.add(item.id)


def _edge_from_anchor(anchor: str) -> str:
    parts = anchor.split(".")
    for edge in ("left", "right", "top", "bottom"):
        if edge in parts:
            return edge
    return "left"


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
    index: int | None = None,
    location: str = "",
) -> str:
    value = payload.get(key, default)
    if isinstance(value, str):
        return value

    if index is not None:
        location = f" item {index}"
    msg = f"ActionRail preset{location} field '{key}' must be a string: {source}"
    raise ValueError(msg)


def _optional_predicate(payload: dict[str, Any], key: str, source: str, index: int) -> str:
    value = payload.get(key, "")
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return value

    msg = f"ActionRail preset item {index} field '{key}' must be a string or boolean: {source}"
    raise ValueError(msg)


def _optional_positive_int(
    payload: dict[str, Any],
    key: str,
    default: int,
    source: str,
    *,
    maximum: int | None = None,
) -> int:
    value = payload.get(key, default)
    if (
        isinstance(value, int)
        and not isinstance(value, bool)
        and value >= 1
        and (maximum is None or value <= maximum)
    ):
        return value

    range_text = "a positive integer"
    if maximum is not None:
        range_text = f"an integer between 1 and {maximum}"
    msg = f"ActionRail preset layout field '{key}' must be {range_text}: {source}"
    raise ValueError(msg)


def _optional_number(
    payload: dict[str, Any],
    key: str,
    default: float,
    source: str,
    *,
    minimum: float,
    maximum: float | None = None,
) -> float:
    value = payload.get(key, default)
    if isinstance(value, int | float) and not isinstance(value, bool):
        number = float(value)
        if number >= minimum and (maximum is None or number <= maximum):
            return number

    range_text = f" between {minimum} and {maximum}" if maximum is not None else f" >= {minimum}"
    msg = f"ActionRail preset layout field '{key}' must be a number{range_text}: {source}"
    raise ValueError(msg)


def _optional_offset(payload: dict[str, Any], source: str) -> tuple[int, int]:
    value = payload.get("offset", (0, 0))
    if (
        isinstance(value, list | tuple)
        and len(value) == 2
        and all(
            isinstance(component, int) and not isinstance(component, bool)
            for component in value
        )
        and all(abs(component) <= MAX_LAYOUT_OFFSET for component in value)
    ):
        return (value[0], value[1])

    msg = (
        "ActionRail preset layout field 'offset' must be a two-integer array "
        f"with values between -{MAX_LAYOUT_OFFSET} and {MAX_LAYOUT_OFFSET}: {source}"
    )
    raise ValueError(msg)
