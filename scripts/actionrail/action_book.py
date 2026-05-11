"""Action Book catalog entries for placeable ActionRail actions."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from .actions import Action, ActionRegistry, create_default_registry

__all__ = [
    "ACTION_BOOK_MIME_TYPE",
    "ActionBookEntry",
    "action_book_action_id_from_mime_text",
    "action_book_entries",
    "action_book_entry_by_id",
    "action_book_choices",
    "action_book_search",
    "action_book_mime_text",
]

ACTION_BOOK_MIME_TYPE = "application/x-actionrail-action-id"


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
    "maya.modeling.poly_cube": {
        "category": "Modeling Primitives",
        "icon": "maya.poly_cube",
        "keywords": ("polygon", "poly", "cube", "primitive", "modeling", "shelf"),
    },
    "maya.modeling.poly_sphere": {
        "category": "Modeling Primitives",
        "icon": "maya.poly_sphere",
        "keywords": ("polygon", "poly", "sphere", "primitive", "modeling", "shelf"),
    },
    "maya.modeling.poly_cylinder": {
        "category": "Modeling Primitives",
        "icon": "maya.poly_cylinder",
        "keywords": ("polygon", "poly", "cylinder", "primitive", "modeling", "shelf"),
    },
    "maya.modeling.poly_cone": {
        "category": "Modeling Primitives",
        "icon": "maya.poly_cone",
        "keywords": ("polygon", "poly", "cone", "primitive", "modeling", "shelf"),
    },
    "maya.modeling.poly_torus": {
        "category": "Modeling Primitives",
        "icon": "maya.poly_torus",
        "keywords": ("polygon", "poly", "torus", "primitive", "modeling", "shelf"),
    },
    "maya.modeling.poly_plane": {
        "category": "Modeling Primitives",
        "icon": "maya.poly_plane",
        "keywords": ("polygon", "poly", "plane", "primitive", "modeling", "shelf"),
    },
    "maya.modeling.combine": {
        "category": "Modeling",
        "icon": "maya.poly_combine",
        "keywords": ("combine", "unite", "polygon", "modeling", "shelf"),
    },
    "maya.modeling.mirror": {
        "category": "Modeling",
        "icon": "maya.poly_mirror",
        "keywords": ("mirror", "symmetry", "polygon", "modeling", "shelf"),
    },
    "maya.modeling.smooth": {
        "category": "Modeling",
        "icon": "maya.poly_smooth",
        "keywords": ("smooth", "subdivision", "polygon", "modeling", "shelf"),
    },
    "maya.modeling.reduce": {
        "category": "Modeling",
        "icon": "maya.poly_reduce",
        "keywords": ("reduce", "decimate", "polygon", "modeling", "shelf"),
    },
    "maya.modeling.remesh": {
        "category": "Modeling",
        "icon": "maya.poly_remesh",
        "keywords": ("remesh", "triangulate", "topology", "modeling", "shelf"),
    },
    "maya.modeling.retopologize": {
        "category": "Modeling",
        "icon": "maya.poly_retopologize",
        "keywords": ("retopologize", "retopo", "quad", "topology", "modeling", "shelf"),
    },
    "maya.modeling.extrude": {
        "category": "Modeling",
        "icon": "maya.extrude",
        "keywords": ("extrude", "face", "edge", "polygon", "modeling", "shelf"),
    },
    "maya.modeling.smart_extrude": {
        "category": "Modeling",
        "icon": "maya.smart_extrude",
        "keywords": ("smart", "extrude", "face", "polygon", "modeling", "shelf"),
    },
    "maya.modeling.bridge": {
        "category": "Modeling",
        "icon": "maya.poly_bridge",
        "keywords": ("bridge", "edge", "face", "polygon", "modeling", "shelf"),
    },
    "maya.modeling.bevel": {
        "category": "Modeling",
        "icon": "maya.bevel",
        "keywords": ("bevel", "chamfer", "edge", "face", "modeling", "shelf"),
    },
    "maya.modeling.merge": {
        "category": "Modeling",
        "icon": "maya.poly_merge",
        "keywords": ("merge", "vertex", "edge", "polygon", "modeling", "shelf"),
    },
    "maya.modeling.multi_cut": {
        "category": "Modeling Tools",
        "icon": "maya.multi_cut",
        "keywords": ("multi-cut", "cut", "slice", "insert edge", "modeling", "shelf"),
    },
    "maya.modeling.target_weld": {
        "category": "Modeling Tools",
        "icon": "maya.target_weld",
        "keywords": ("target", "weld", "merge", "vertex", "edge", "modeling", "shelf"),
    },
    "maya.modeling.quad_draw": {
        "category": "Modeling Tools",
        "icon": "maya.quad_draw",
        "keywords": ("quad", "draw", "retopology", "topology", "modeling", "shelf"),
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


def action_book_search(
    query: str = "",
    *,
    registry: ActionRegistry | None = None,
) -> tuple[ActionBookEntry, ...]:
    """Return Action Book entries matching a label/category/keyword query."""

    entries = action_book_entries(registry)
    terms = tuple(term.casefold() for term in query.split() if term.strip())
    if not terms:
        return entries
    return tuple(entry for entry in entries if _entry_matches_terms(entry, terms))


def action_book_mime_text(action_id: str) -> str:
    """Return a stable drag/drop payload for one Action Book action."""

    if not action_id.strip():
        msg = "Action Book drag payload requires a non-empty action id."
        raise ValueError(msg)
    return action_id.strip()


def action_book_action_id_from_mime_text(text: str) -> str:
    """Return an action id from an Action Book drag/drop payload."""

    action_id = str(text).strip()
    if not action_id:
        msg = "Action Book drag payload is empty."
        raise ValueError(msg)
    return action_id


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


def _entry_matches_terms(entry: ActionBookEntry, terms: tuple[str, ...]) -> bool:
    haystack = " ".join(
        (
            entry.id,
            entry.label,
            entry.tooltip,
            entry.category,
            entry.source,
            entry.kind,
            *entry.keywords,
        )
    ).casefold()
    return all(term in haystack for term in terms)
