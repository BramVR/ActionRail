"""Quick Create draft templates and picker data."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .actions import ActionRegistry, create_default_registry
from .authoring import (
    DraftRail,
    DraftSlot,
    build_draft_spec,
    save_user_preset,
    validate_preset_id,
)
from .icon_catalog import list_icon_descriptors
from .icon_types import IconDescriptor
from .preset_store import resolve_preset
from .spec import RailLayout, builtin_preset_ids

__all__ = [
    "ANCHOR_CHOICES",
    "QuickCreateDraftInput",
    "QuickCreateSaveResult",
    "QuickCreateSlotInput",
    "QuickCreateTemplate",
    "TEMPLATE_IDS",
    "action_choices",
    "build_quick_create_draft",
    "clear_quick_create_previews",
    "icon_choices",
    "load_quick_create_preset",
    "make_default_input",
    "preview_quick_create_draft",
    "save_quick_create_preset",
    "template_by_id",
    "template_choices",
]

ANCHOR_CHOICES = (
    "viewport.left.center",
    "viewport.right.center",
    "viewport.top.center",
    "viewport.bottom.center",
    "viewport.center",
)


@dataclass(frozen=True)
class QuickCreateSlotInput:
    """One editable Quick Create slot row."""

    id: str
    label: str
    action: str = ""
    key_label: str = ""
    icon: str = ""


@dataclass(frozen=True)
class QuickCreateTemplate:
    """A starter rail shape for the dockable Quick Create panel."""

    id: str
    label: str
    layout: RailLayout
    slots: tuple[QuickCreateSlotInput, ...]
    description: str = ""


@dataclass(frozen=True)
class QuickCreateDraftInput:
    """Editable Quick Create values before conversion to ``DraftRail``."""

    preset_id: str
    template_id: str
    slots: tuple[QuickCreateSlotInput, ...]
    anchor: str
    orientation: str
    rows: int = 1
    columns: int = 1
    offset: tuple[int, int] = (0, 0)
    scale: float = 1.0
    opacity: float = 1.0
    locked: bool = False


@dataclass(frozen=True)
class QuickCreateSaveResult:
    """Result from saving and optionally showing a Quick Create preset."""

    preset_id: str
    path: Path
    host: Any | None = None


_PREVIEW_IDS: set[str] = set()

_TEMPLATES = (
    QuickCreateTemplate(
        id="vertical_stack",
        label="Vertical Stack",
        description="Compact vertical action rail.",
        layout=RailLayout(
            anchor="viewport.left.center",
            orientation="vertical",
            rows=1,
            columns=1,
            offset=(12, 0),
        ),
        slots=(
            QuickCreateSlotInput("move", "M", "maya.tool.move", "W", "maya.move"),
            QuickCreateSlotInput("rotate", "R", "maya.tool.rotate", "E", "maya.rotate"),
            QuickCreateSlotInput("scale", "S", "maya.tool.scale", "R", "maya.scale"),
            QuickCreateSlotInput("set_key", "K", "maya.anim.set_key", "S", "maya.set_key"),
        ),
    ),
    QuickCreateTemplate(
        id="horizontal_strip",
        label="Horizontal Strip",
        description="Bottom anchored action strip.",
        layout=RailLayout(
            anchor="viewport.bottom.center",
            orientation="horizontal",
            rows=1,
            columns=4,
            offset=(0, -36),
        ),
        slots=(
            QuickCreateSlotInput("move", "Move", "maya.tool.move", "W", "maya.move"),
            QuickCreateSlotInput("rotate", "Rotate", "maya.tool.rotate", "E", "maya.rotate"),
            QuickCreateSlotInput("scale", "Scale", "maya.tool.scale", "R", "maya.scale"),
            QuickCreateSlotInput("key", "Key", "maya.anim.set_key", "S", "maya.set_key"),
        ),
    ),
    QuickCreateTemplate(
        id="edge_tab_rail",
        label="Edge-Tab Rail",
        description="Edge anchored rail ready for later collapse settings.",
        layout=RailLayout(
            anchor="viewport.left.center",
            orientation="vertical",
            rows=1,
            columns=1,
            offset=(0, 0),
            opacity=0.92,
        ),
        slots=(
            QuickCreateSlotInput("primary", "Tool", "maya.tool.move", "", "maya.move"),
        ),
    ),
)

TEMPLATE_IDS = tuple(template.id for template in _TEMPLATES)


def template_choices() -> tuple[QuickCreateTemplate, ...]:
    """Return the supported Phase 2.2 rail templates."""

    return _TEMPLATES


def template_by_id(template_id: str) -> QuickCreateTemplate:
    """Return a Quick Create template by id."""

    for template in _TEMPLATES:
        if template.id == template_id:
            return template
    msg = f"Unknown ActionRail Quick Create template: {template_id}"
    raise KeyError(msg)


def make_default_input(template_id: str = "vertical_stack") -> QuickCreateDraftInput:
    """Return editable defaults for one template."""

    template = template_by_id(template_id)
    return QuickCreateDraftInput(
        preset_id=_default_preset_id(template_id),
        template_id=template.id,
        slots=template.slots,
        anchor=template.layout.anchor,
        orientation=template.layout.orientation,
        rows=template.layout.rows,
        columns=template.layout.columns,
        offset=template.layout.offset,
        scale=template.layout.scale,
        opacity=template.layout.opacity,
        locked=template.layout.locked,
    )


def build_quick_create_draft(values: QuickCreateDraftInput) -> DraftRail:
    """Convert editable Quick Create values to the authoring draft model."""

    template_by_id(values.template_id)
    if not values.slots:
        msg = "ActionRail Quick Create requires at least one slot."
        raise ValueError(msg)

    layout = RailLayout(
        anchor=values.anchor,
        orientation=values.orientation,
        rows=values.rows,
        columns=values.columns,
        offset=values.offset,
        scale=values.scale,
        opacity=values.opacity,
        locked=values.locked,
    )
    draft = DraftRail(
        id=values.preset_id,
        layout=layout,
        slots=tuple(_draft_slot_from_input(slot) for slot in values.slots),
    )
    return draft


def preview_quick_create_draft(
    draft: DraftRail,
    *,
    panel: str | None = None,
    registry: ActionRegistry | None = None,
) -> Any:
    """Preview a Quick Create draft through the normal overlay runtime."""

    spec = build_draft_spec(draft)
    _validate_quick_create_id(spec.id)

    from . import diagnostics, runtime

    report = diagnostics.diagnose_spec(spec, registry=registry)
    if report.has_errors:
        msg = (
            "ActionRail Quick Create preview has diagnostic errors; "
            "run actionrail.show_last_report() for details."
        )
        raise ValueError(msg)

    clear_quick_create_previews()
    host = runtime.show_spec(spec, panel=panel, registry=registry)
    _PREVIEW_IDS.add(spec.id)
    return host


def clear_quick_create_previews(preset_id: str = "") -> int:
    """Hide active Quick Create preview overlays tracked by this session."""

    from . import runtime

    preview_ids = (preset_id,) if preset_id else tuple(_PREVIEW_IDS)
    cleared = 0
    active_ids = set(runtime.active_overlay_ids())
    for preview_id in preview_ids:
        if preview_id in active_ids:
            cleared += 1
        runtime.hide_example(preview_id)
        _PREVIEW_IDS.discard(preview_id)
    return cleared


def save_quick_create_preset(
    draft: DraftRail,
    *,
    preset_dir: str | Path | None = None,
    overwrite: bool = False,
    show: bool = True,
    panel: str | None = None,
) -> QuickCreateSaveResult:
    """Save a Quick Create draft as a user preset and optionally show it."""

    spec = build_draft_spec(draft)
    _validate_quick_create_id(spec.id)
    path = save_user_preset(spec, preset_dir=preset_dir, overwrite=overwrite)
    clear_quick_create_previews(spec.id)

    host = None
    if show:
        from . import runtime

        host = runtime.show_preset(spec.id, panel=panel, user_preset_dir=preset_dir)
    return QuickCreateSaveResult(spec.id, path, host)


def load_quick_create_preset(
    preset_id: str,
    *,
    preset_dir: str | Path | None = None,
) -> QuickCreateDraftInput:
    """Return editable Quick Create values for an existing saved user preset."""

    spec = resolve_preset(preset_id, user_preset_dir=preset_dir)
    if spec.id in builtin_preset_ids():
        msg = f"Quick Create can only load saved user presets for editing: {spec.id}"
        raise ValueError(msg)

    return QuickCreateDraftInput(
        preset_id=spec.id,
        template_id=_template_id_for_layout(spec.layout, len(spec.items)),
        slots=tuple(
            _slot_input_from_item(spec.id, item)
            for item in spec.items
            if item.type != "spacer"
        ),
        anchor=spec.layout.anchor,
        orientation=spec.layout.orientation,
        rows=spec.layout.rows,
        columns=spec.layout.columns,
        offset=spec.layout.offset,
        scale=spec.layout.scale,
        opacity=spec.layout.opacity,
        locked=spec.layout.locked,
    )


def action_choices(
    registry: ActionRegistry | None = None,
) -> tuple[tuple[str, str, str], ...]:
    """Return registered action ids with picker labels and tooltips."""

    action_registry = registry or create_default_registry()
    return tuple(
        (action.id, action.label, action.tooltip)
        for action in sorted(action_registry.actions(), key=lambda item: item.label)
    )


def icon_choices(*, provider: str = "") -> tuple[IconDescriptor, ...]:
    """Return icon descriptors for the Quick Create icon picker."""

    return list_icon_descriptors(provider=provider)


def _draft_slot_from_input(slot: QuickCreateSlotInput) -> DraftSlot:
    return DraftSlot(
        id=slot.id,
        label=slot.label,
        action=slot.action,
        key_label=slot.key_label,
        icon=slot.icon,
        tooltip=_slot_tooltip(slot),
    )


def _slot_tooltip(slot: QuickCreateSlotInput) -> str:
    if slot.action:
        return slot.action
    return slot.label


def _slot_input_from_item(preset_id: str, item: Any) -> QuickCreateSlotInput:
    return QuickCreateSlotInput(
        id=_unqualified_slot_id(preset_id, item.id),
        label=item.label,
        action=item.action,
        key_label=item.key_label,
        icon=item.icon,
    )


def _unqualified_slot_id(preset_id: str, slot_id: str) -> str:
    prefix = f"{preset_id}."
    if slot_id.startswith(prefix):
        return slot_id.removeprefix(prefix)
    return slot_id


def _template_id_for_layout(layout: RailLayout, item_count: int) -> str:
    if layout.orientation == "horizontal":
        return "horizontal_strip"
    if item_count == 1 and layout.opacity < 1.0:
        return "edge_tab_rail"
    return "vertical_stack"


def _default_preset_id(template_id: str) -> str:
    suffix = template_id.replace("_", "-")
    return f"quick-{suffix}"


def _validate_quick_create_id(preset_id: str) -> str:
    validate_preset_id(preset_id)
    if preset_id in builtin_preset_ids():
        msg = f"Quick Create preset id '{preset_id}' would overwrite a locked built-in preset."
        raise ValueError(msg)
    return preset_id
