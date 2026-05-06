"""Helpers for editing action payloads on stable rail slot containers."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import replace as dataclass_replace
from typing import Any

EMPTY_SLOT_LABEL = "New"
ACTION_ICON_DEFAULTS = {
    "maya.tool.move": "maya.move",
    "maya.tool.translate": "maya.move",
    "maya.tool.rotate": "maya.rotate",
    "maya.tool.scale": "maya.scale",
    "maya.anim.set_key": "maya.set_key",
}
PERSISTENT_ACTION_PREDICATES = {
    "maya.tool.move": "maya.tool == move",
    "maya.tool.translate": "maya.tool == move",
    "maya.tool.rotate": "maya.tool == rotate",
    "maya.tool.scale": "maya.tool == scale",
}

__all__ = [
    "EMPTY_SLOT_LABEL",
    "item_has_payload",
    "payload_from_action",
    "spec_with_empty_slot_payload",
    "spec_with_moved_slot_payload",
    "spec_with_slot_action_payload",
]


@dataclass(frozen=True)
class SlotPayload:
    """Action data that can be assigned to a stable slot container."""

    label: str = EMPTY_SLOT_LABEL
    action: str = ""
    tone: str = "neutral"
    tooltip: str = ""
    icon: str = ""
    enabled_when: str = ""
    active_when: str = ""


def spec_with_slot_action_payload(spec: Any, slot_id: str, action_id: str) -> Any:
    """Return a spec copy with one slot assigned to a registry action."""

    index = _slot_item_index(spec.items, slot_id)
    if index is None:
        msg = f"Unknown ActionRail slot: {slot_id}"
        raise KeyError(msg)
    return _spec_with_item(
        spec,
        index,
        _item_with_payload(spec.items[index], payload_from_action(action_id)),
    )


def spec_with_empty_slot_payload(spec: Any, slot_id: str) -> Any:
    """Return a spec copy with one slot payload cleared."""

    index = _slot_item_index(spec.items, slot_id)
    if index is None:
        msg = f"Unknown ActionRail slot: {slot_id}"
        raise KeyError(msg)
    return _spec_with_item(spec, index, _item_with_payload(spec.items[index], SlotPayload()))


def spec_with_moved_slot_payload(spec: Any, source_slot_id: str, target_slot_id: str) -> Any:
    """Return a spec copy with a slot payload moved or swapped between slots."""

    source_index = _slot_item_index(spec.items, source_slot_id)
    target_index = _slot_item_index(spec.items, target_slot_id)
    if source_index is None:
        msg = f"Unknown ActionRail slot: {source_slot_id}"
        raise KeyError(msg)
    if target_index is None:
        msg = f"Unknown ActionRail slot: {target_slot_id}"
        raise KeyError(msg)
    if source_index == target_index:
        return spec
    if not item_has_payload(spec.items[source_index]):
        msg = f"ActionRail slot has no payload: {source_slot_id}"
        raise ValueError(msg)

    source_payload = _payload_from_item(spec.items[source_index])
    items = list(spec.items)
    if item_has_payload(items[target_index]):
        target_payload = _payload_from_item(items[target_index])
        items[source_index] = _item_with_payload(items[source_index], target_payload)
    else:
        items[source_index] = _item_with_payload(items[source_index], SlotPayload())
    items[target_index] = _item_with_payload(items[target_index], source_payload)
    return dataclass_replace(spec, items=tuple(items))


def payload_from_action(action_id: str) -> SlotPayload:
    """Resolve default slot payload fields from a registered action id."""

    from .actions import create_default_registry

    action = create_default_registry().get(action_id)
    return SlotPayload(
        label=action.label,
        action=action.id,
        tooltip=action.tooltip or action.id,
        icon=ACTION_ICON_DEFAULTS.get(action.id, ""),
        active_when=PERSISTENT_ACTION_PREDICATES.get(action.id, ""),
    )


def item_has_payload(item: Any) -> bool:
    """Return whether a slot carries an editable action payload."""

    label = str(getattr(item, "label", "")).strip()
    return bool(
        getattr(item, "action", "")
        or getattr(item, "icon", "")
        or (label and label != EMPTY_SLOT_LABEL)
    )


def _slot_item_index(items: tuple[Any, ...], slot_id: str) -> int | None:
    for index, item in enumerate(items):
        if getattr(item, "type", "") == "spacer":
            continue
        if getattr(item, "id", "") == slot_id:
            return index
    return None


def _spec_with_item(spec: Any, index: int, item: Any) -> Any:
    items = list(spec.items)
    items[index] = item
    return dataclass_replace(spec, items=tuple(items))


def _payload_from_item(item: Any) -> SlotPayload:
    return SlotPayload(
        label=getattr(item, "label", EMPTY_SLOT_LABEL),
        action=getattr(item, "action", ""),
        tone=getattr(item, "tone", "neutral"),
        tooltip=getattr(item, "tooltip", ""),
        icon=getattr(item, "icon", ""),
        enabled_when=getattr(item, "enabled_when", ""),
        active_when=getattr(item, "active_when", ""),
    )


def _item_with_payload(item: Any, payload: SlotPayload) -> Any:
    return dataclass_replace(
        item,
        label=payload.label,
        action=payload.action,
        tone=payload.tone,
        tooltip=payload.tooltip,
        icon=payload.icon,
        enabled_when=payload.enabled_when,
        active_when=payload.active_when,
    )
