"""Quick Create draft templates and picker data."""

from __future__ import annotations

from dataclasses import dataclass

from .actions import ActionRegistry, create_default_registry
from .authoring import DraftRail, DraftSlot
from .icon_catalog import list_icon_descriptors
from .icon_types import IconDescriptor
from .spec import RailLayout

__all__ = [
    "ANCHOR_CHOICES",
    "QuickCreateDraftInput",
    "QuickCreateSlotInput",
    "QuickCreateTemplate",
    "TEMPLATE_IDS",
    "action_choices",
    "build_quick_create_draft",
    "icon_choices",
    "make_default_input",
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


def _default_preset_id(template_id: str) -> str:
    suffix = template_id.replace("_", "-")
    return f"quick-{suffix}"
