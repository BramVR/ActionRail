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
    "RailAppearance",
    "RailBackground",
    "RailBorder",
    "RailLayout",
    "RailSlotAppearance",
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
class RailBackground:
    enabled: bool = True
    color: str = ""
    pattern: str = "diagonal_stripes"
    pattern_color: str = ""
    pattern_opacity: float = 1.0
    pattern_scale: float = 1.0


@dataclass(frozen=True)
class RailBorder:
    enabled: bool = True
    color: str = ""
    width: int | None = None


@dataclass(frozen=True)
class RailSlotAppearance:
    empty_background: str = ""
    empty_border: str = ""
    icon_backplate: str = ""
    icon_border: str = ""
    active: str = ""
    text: str = ""


@dataclass(frozen=True)
class RailAppearance:
    theme: str = "default"
    inherit_global: bool = True
    accent: str = ""
    secondary: str = ""
    text: str = ""
    muted_text: str = ""
    background: RailBackground = field(default_factory=RailBackground)
    border: RailBorder = field(default_factory=RailBorder)
    slots: RailSlotAppearance = field(default_factory=RailSlotAppearance)


@dataclass(frozen=True)
class StackSpec:
    id: str
    layout: RailLayout
    items: tuple[StackItem, ...]
    collapse: RailCollapse = field(default_factory=RailCollapse)
    appearance: RailAppearance = field(default_factory=RailAppearance)

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
    appearance = _parse_appearance(payload, source)
    raw_items = payload.get("items")
    if not isinstance(raw_items, list) or not raw_items:
        msg = f"ActionRail preset items must be a non-empty list: {source}"
        raise ValueError(msg)

    items = tuple(_parse_item(item, index, source, spec_id) for index, item in enumerate(raw_items))
    _validate_unique_item_ids(items, source)
    return StackSpec(
        id=spec_id,
        layout=layout,
        items=items,
        collapse=collapse,
        appearance=appearance,
    )


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


def _parse_appearance(payload: dict[str, Any], source: str) -> RailAppearance:
    raw_appearance = payload.get("appearance", {})
    if raw_appearance is None:
        raw_appearance = {}
    if not isinstance(raw_appearance, dict):
        msg = f"ActionRail preset appearance must be an object: {source}"
        raise ValueError(msg)

    theme = _optional_string(raw_appearance, "theme", "default", source, location=" appearance")
    inherit_global = raw_appearance.get("inherit_global", True)
    if not isinstance(inherit_global, bool):
        msg = f"ActionRail preset appearance field 'inherit_global' must be a boolean: {source}"
        raise ValueError(msg)

    background = _parse_background_appearance(raw_appearance, source)
    border = _parse_border_appearance(raw_appearance, source)
    slots = _parse_slot_appearance(raw_appearance, source)
    return RailAppearance(
        theme=theme,
        inherit_global=inherit_global,
        accent=_optional_string(raw_appearance, "accent", "", source, location=" appearance"),
        secondary=_optional_string(
            raw_appearance,
            "secondary",
            "",
            source,
            location=" appearance",
        ),
        text=_optional_string(raw_appearance, "text", "", source, location=" appearance"),
        muted_text=_optional_string(
            raw_appearance,
            "muted_text",
            "",
            source,
            location=" appearance",
        ),
        background=background,
        border=border,
        slots=slots,
    )


def _parse_background_appearance(
    raw_appearance: dict[str, Any],
    source: str,
) -> RailBackground:
    raw_background = raw_appearance.get("background", {})
    if raw_background is None:
        raw_background = {}
    if not isinstance(raw_background, dict):
        msg = f"ActionRail preset appearance background must be an object: {source}"
        raise ValueError(msg)

    enabled = raw_background.get("enabled", True)
    if not isinstance(enabled, bool):
        msg = (
            "ActionRail preset appearance background field 'enabled' "
            f"must be a boolean: {source}"
        )
        raise ValueError(msg)

    pattern = _optional_string(
        raw_background,
        "pattern",
        "diagonal_stripes",
        source,
        location=" appearance background",
    )
    if pattern not in {"diagonal_stripes", "none"}:
        msg = (
            "ActionRail preset appearance background field 'pattern' must be "
            f"'diagonal_stripes' or 'none': {source}"
        )
        raise ValueError(msg)

    return RailBackground(
        enabled=enabled,
        color=_optional_string(
            raw_background,
            "color",
            "",
            source,
            location=" appearance background",
        ),
        pattern=pattern,
        pattern_color=_optional_string(
            raw_background,
            "pattern_color",
            "",
            source,
            location=" appearance background",
        ),
        pattern_opacity=_optional_number(
            raw_background,
            "pattern_opacity",
            1.0,
            source,
            minimum=0.0,
            maximum=1.0,
            location=" appearance background",
        ),
        pattern_scale=_optional_number(
            raw_background,
            "pattern_scale",
            1.0,
            source,
            minimum=0.25,
            maximum=4.0,
            location=" appearance background",
        ),
    )


def _parse_border_appearance(raw_appearance: dict[str, Any], source: str) -> RailBorder:
    raw_border = raw_appearance.get("border", {})
    if raw_border is None:
        raw_border = {}
    if not isinstance(raw_border, dict):
        msg = f"ActionRail preset appearance border must be an object: {source}"
        raise ValueError(msg)

    enabled = raw_border.get("enabled", True)
    if not isinstance(enabled, bool):
        msg = (
            "ActionRail preset appearance border field 'enabled' "
            f"must be a boolean: {source}"
        )
        raise ValueError(msg)

    width = raw_border.get("width")
    if width is not None and (
        not isinstance(width, int) or isinstance(width, bool) or width < 0 or width > 12
    ):
        msg = (
            "ActionRail preset appearance border field 'width' must be "
            f"an integer between 0 and 12: {source}"
        )
        raise ValueError(msg)

    return RailBorder(
        enabled=enabled,
        color=_optional_string(raw_border, "color", "", source, location=" appearance border"),
        width=width,
    )


def _parse_slot_appearance(
    raw_appearance: dict[str, Any],
    source: str,
) -> RailSlotAppearance:
    raw_slots = raw_appearance.get("slots", {})
    if raw_slots is None:
        raw_slots = {}
    if not isinstance(raw_slots, dict):
        msg = f"ActionRail preset appearance slots must be an object: {source}"
        raise ValueError(msg)

    return RailSlotAppearance(
        empty_background=_optional_string(
            raw_slots,
            "empty_background",
            "",
            source,
            location=" appearance slots",
        ),
        empty_border=_optional_string(
            raw_slots,
            "empty_border",
            "",
            source,
            location=" appearance slots",
        ),
        icon_backplate=_optional_string(
            raw_slots,
            "icon_backplate",
            "",
            source,
            location=" appearance slots",
        ),
        icon_border=_optional_string(
            raw_slots,
            "icon_border",
            "",
            source,
            location=" appearance slots",
        ),
        active=_optional_string(raw_slots, "active", "", source, location=" appearance slots"),
        text=_optional_string(raw_slots, "text", "", source, location=" appearance slots"),
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
    location: str = " layout",
) -> float:
    value = payload.get(key, default)
    if isinstance(value, int | float) and not isinstance(value, bool):
        number = float(value)
        if number >= minimum and (maximum is None or number <= maximum):
            return number

    range_text = f" between {minimum} and {maximum}" if maximum is not None else f" >= {minimum}"
    msg = f"ActionRail preset{location} field '{key}' must be a number{range_text}: {source}"
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
