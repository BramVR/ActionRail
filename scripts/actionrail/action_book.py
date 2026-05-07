"""Action Book catalog entries for placeable ActionRail actions."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from .actions import Action, ActionRegistry, create_default_registry

__all__ = [
    "ActionBookEntry",
    "action_book_entries",
    "action_book_entry_by_id",
    "action_book_choices",
]


@dataclass(frozen=True)
class ActionBookEntry:
    """Picker-facing metadata for one placeable action."""

    id: str
    label: str
    tooltip: str = ""
    category: str = "Maya"
    icon: str = ""
    source: str = "actionrail"
    kind: str = "action"
    keywords: tuple[str, ...] = ()


_ACTION_METADATA: dict[str, dict[str, object]] = {
    "maya.tool.select": {
        "category": "Selection",
        "icon": "maya.objects",
        "keywords": ("select", "selection", "tool", "q"),
    },
    "maya.tool.move": {
        "category": "Transform",
        "icon": "maya.move",
        "keywords": ("move", "translate", "tool", "transform", "w"),
    },
    "maya.tool.translate": {
        "category": "Transform",
        "icon": "maya.move",
        "keywords": ("translate", "move", "tool", "transform", "w"),
    },
    "maya.tool.rotate": {
        "category": "Transform",
        "icon": "maya.rotate",
        "keywords": ("rotate", "tool", "transform", "e"),
    },
    "maya.tool.scale": {
        "category": "Transform",
        "icon": "maya.scale",
        "keywords": ("scale", "tool", "transform", "r"),
    },
    "maya.anim.set_key": {
        "category": "Animation",
        "icon": "maya.set_key",
        "keywords": ("key", "keyframe", "animation", "set key", "s"),
    },
    "maya.selection.clear": {
        "category": "Selection",
        "icon": "maya.objects",
        "keywords": ("clear", "deselect", "selection"),
    },
    "maya.modeling.center_pivot": {
        "category": "Modeling",
        "icon": "maya.center_pivot",
        "keywords": ("center", "pivot", "modeling", "transform"),
    },
    "maya.modeling.freeze_transforms": {
        "category": "Modeling",
        "icon": "maya.freeze_transform",
        "keywords": ("freeze", "transforms", "modeling", "zero", "apply"),
    },
    "maya.modeling.delete_history": {
        "category": "Modeling",
        "icon": "maya.objects",
        "keywords": ("delete", "history", "construction", "modeling", "cleanup"),
    },
    "maya.view.frame_selection": {
        "category": "Viewport",
        "icon": "maya.camera",
        "keywords": ("frame", "fit", "selection", "camera", "viewport", "f"),
    },
    "maya.display.toggle_grid": {
        "category": "Viewport",
        "icon": "maya.grid",
        "keywords": ("grid", "viewport", "display", "toggle"),
    },
    "maya.view.toggle_isolate_selected": {
        "category": "Viewport",
        "icon": "maya.isolate_selected",
        "keywords": ("isolate", "selection", "viewport", "display", "toggle"),
    },
}


def action_book_entries(
    registry: ActionRegistry | None = None,
) -> tuple[ActionBookEntry, ...]:
    """Return searchable Action Book entries for registered actions."""

    action_registry = registry or create_default_registry()
    entries = tuple(_entry_from_action(action) for action in action_registry.actions())
    return tuple(sorted(entries, key=_entry_sort_key))


def action_book_entry_by_id(
    action_id: str,
    registry: ActionRegistry | None = None,
) -> ActionBookEntry:
    """Return one Action Book entry by action id."""

    for entry in action_book_entries(registry):
        if entry.id == action_id:
            return entry
    msg = f"Unknown ActionRail Action Book entry: {action_id}"
    raise KeyError(msg)


def action_book_choices(
    registry: ActionRegistry | None = None,
) -> tuple[tuple[str, str, str], ...]:
    """Return compatibility picker choices as ``(id, label, tooltip)``."""

    return tuple(
        (entry.id, entry.label, entry.tooltip)
        for entry in action_book_entries(registry)
    )


def _entry_from_action(action: Action) -> ActionBookEntry:
    metadata = _ACTION_METADATA.get(action.id, {})
    return ActionBookEntry(
        id=action.id,
        label=action.label,
        tooltip=action.tooltip,
        category=str(metadata.get("category", "Custom")),
        icon=str(metadata.get("icon", "")),
        source=str(metadata.get("source", "actionrail")),
        kind=str(metadata.get("kind", "action")),
        keywords=_metadata_keywords(metadata.get("keywords", ())),
    )


def _metadata_keywords(value: object) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value,)
    if isinstance(value, Iterable):
        return tuple(str(item) for item in value)
    return ()


def _entry_sort_key(entry: ActionBookEntry) -> tuple[str, str, str]:
    return (entry.category.casefold(), entry.label.casefold(), entry.id)
