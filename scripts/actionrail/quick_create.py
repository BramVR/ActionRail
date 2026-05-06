"""Quick Create draft templates and picker data."""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil
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
from .spec import RailCollapse, RailLayout, builtin_preset_ids

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

_PERSISTENT_TOOL_ACTIVE_PREDICATES = {
    "maya.tool.move": "maya.tool == move",
    "maya.tool.translate": "maya.tool == move",
    "maya.tool.rotate": "maya.tool == rotate",
    "maya.tool.scale": "maya.tool == scale",
}


@dataclass(frozen=True)
class QuickCreateSlotInput:
    """One editable Quick Create slot row."""

    id: str
    label: str
    action: str = ""
    key_label: str = ""
    icon: str = ""
    type: str = "button"
    tone: str = "neutral"
    tooltip: str = ""
    visible_when: str = ""
    enabled_when: str = ""
    active_when: str = ""
    size: int = 0


@dataclass(frozen=True)
class QuickCreateTemplate:
    """A starter rail shape for the dockable Quick Create panel."""

    id: str
    label: str
    layout: RailLayout
    slots: tuple[QuickCreateSlotInput, ...]
    collapse: RailCollapse = RailCollapse()
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
    collapse_enabled: bool = False
    collapse_edge: str = "left"
    collapse_handle_icon: str = ""
    collapse_reveal_trigger: str = "click"
    collapse_default_collapsed: bool = False


@dataclass(frozen=True)
class QuickCreateSaveResult:
    """Result from saving and optionally showing a Quick Create preset."""

    preset_id: str
    path: Path
    host: Any | None = None
    diagnostics: Any | None = None
    published: tuple[Any, ...] = ()
    unpublished: tuple[Any, ...] = ()
    shelf_button: str = ""


_PREVIEW_IDS: set[str] = set()

_TEMPLATES = (
    QuickCreateTemplate(
        id="vertical_stack",
        label="Vertical Stack",
        description="Compact vertical action rail.",
        layout=RailLayout(
            anchor="viewport.left.center",
            orientation="vertical",
            rows=4,
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
        collapse=RailCollapse(enabled=True, edge="left", handle_icon="chevron-right"),
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
        collapse_enabled=template.collapse.enabled,
        collapse_edge=_template_collapse_edge(template),
        collapse_handle_icon=template.collapse.handle_icon,
        collapse_reveal_trigger=template.collapse.reveal_trigger,
        collapse_default_collapsed=template.collapse.default_collapsed,
    )


def build_quick_create_draft(values: QuickCreateDraftInput) -> DraftRail:
    """Convert editable Quick Create values to the authoring draft model."""

    template_by_id(values.template_id)
    if not values.slots:
        msg = "ActionRail Quick Create requires at least one slot."
        raise ValueError(msg)

    action_slot_count = sum(1 for slot in values.slots if slot.type != "spacer")
    rows = values.rows
    columns = values.columns
    if rows * columns < action_slot_count:
        if values.orientation == "horizontal":
            columns = ceil(action_slot_count / rows)
        else:
            rows = ceil(action_slot_count / columns)

    layout = RailLayout(
        anchor=values.anchor,
        orientation=values.orientation,
        rows=rows,
        columns=columns,
        offset=values.offset,
        scale=values.scale,
        opacity=values.opacity,
        locked=values.locked,
    )
    draft = DraftRail(
        id=values.preset_id,
        layout=layout,
        collapse=RailCollapse(
            enabled=values.collapse_enabled,
            edge=values.collapse_edge,
            handle_icon=values.collapse_handle_icon,
            reveal_trigger=values.collapse_reveal_trigger,
            default_collapsed=values.collapse_default_collapsed,
        ),
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
    publish: bool = False,
    install_shelf: bool = False,
    panel: str | None = None,
    cmds_module: Any | None = None,
    mel_module: Any | None = None,
) -> QuickCreateSaveResult:
    """Save a Quick Create draft as a user preset and optionally show it."""

    spec = build_draft_spec(draft)
    _validate_quick_create_id(spec.id)

    from . import diagnostics

    report = diagnostics.diagnose_publish_spec(spec, cmds_module=cmds_module)
    if report.has_errors:
        detail = _diagnostic_blocking_detail(report)
        msg = (
            "ActionRail Quick Create save has diagnostic errors; "
            f"{detail} Run actionrail.show_last_report() for details."
        )
        raise ValueError(msg)

    path = save_user_preset(spec, preset_dir=preset_dir, overwrite=overwrite)
    effective_preset_dir = path.parent.resolve()
    clear_quick_create_previews(spec.id)

    host = None
    if show:
        from . import runtime

        host = runtime.show_preset(
            spec.id,
            panel=panel,
            user_preset_dir=effective_preset_dir,
        )

    published: tuple[Any, ...] = ()
    unpublished: tuple[Any, ...] = ()
    if publish:
        from . import hotkeys

        sync_result = hotkeys.sync_preset_slots(
            spec.id,
            spec=spec,
            user_preset_dir=effective_preset_dir,
            cmds_module=cmds_module,
        )
        published = sync_result.published
        unpublished = sync_result.unpublished

    shelf_button = ""
    if install_shelf:
        from . import maya_ui

        shelf_button = maya_ui.install_preset_shelf_toggle(
            spec.id,
            user_preset_dir=effective_preset_dir,
            cmds_module=cmds_module,
            mel_module=mel_module,
        )

    return QuickCreateSaveResult(
        spec.id,
        path,
        host,
        report,
        published,
        unpublished,
        shelf_button,
    )


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
        template_id=_template_id_for_spec(spec),
        slots=tuple(_slot_input_from_item(spec.id, item) for item in spec.items),
        anchor=spec.layout.anchor,
        orientation=spec.layout.orientation,
        rows=spec.layout.rows,
        columns=spec.layout.columns,
        offset=spec.layout.offset,
        scale=spec.layout.scale,
        opacity=spec.layout.opacity,
        locked=spec.layout.locked,
        collapse_enabled=spec.collapse.enabled,
        collapse_edge=spec.collapse.edge,
        collapse_handle_icon=spec.collapse.handle_icon,
        collapse_reveal_trigger=spec.collapse.reveal_trigger,
        collapse_default_collapsed=spec.collapse.default_collapsed,
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
        type=slot.type,
        tone=slot.tone,
        key_label=slot.key_label,
        icon=slot.icon,
        tooltip=_slot_tooltip(slot),
        visible_when=slot.visible_when,
        enabled_when=slot.enabled_when,
        active_when=_slot_active_when(slot),
        size=slot.size,
    )


def _slot_active_when(slot: QuickCreateSlotInput) -> str:
    if slot.active_when.strip():
        return slot.active_when
    return _PERSISTENT_TOOL_ACTIVE_PREDICATES.get(slot.action, "")


def _slot_tooltip(slot: QuickCreateSlotInput) -> str:
    if slot.tooltip:
        return slot.tooltip
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
        type=item.type,
        tone=item.tone,
        tooltip=item.tooltip,
        visible_when=item.visible_when,
        enabled_when=item.enabled_when,
        active_when=item.active_when,
        size=item.size,
    )


def _unqualified_slot_id(preset_id: str, slot_id: str) -> str:
    prefix = f"{preset_id}."
    if slot_id.startswith(prefix):
        return slot_id.removeprefix(prefix)
    return slot_id


def _template_id_for_spec(spec: Any) -> str:
    if getattr(spec.collapse, "enabled", False):
        return "edge_tab_rail"
    if spec.layout.orientation == "horizontal":
        return "horizontal_strip"
    if len(spec.items) == 1 and spec.layout.opacity < 1.0:
        return "edge_tab_rail"
    return "vertical_stack"


def _template_collapse_edge(template: QuickCreateTemplate) -> str:
    if template.collapse.enabled:
        return template.collapse.edge
    return _edge_from_anchor(template.layout.anchor)


def _edge_from_anchor(anchor: str) -> str:
    for edge in ("left", "right", "top", "bottom"):
        if f".{edge}." in anchor:
            return edge
    return "left"


def _default_preset_id(template_id: str) -> str:
    suffix = template_id.replace("_", "-")
    return f"quick-{suffix}"


def _validate_quick_create_id(preset_id: str) -> str:
    validate_preset_id(preset_id)
    if preset_id in builtin_preset_ids():
        msg = f"Quick Create preset id '{preset_id}' would overwrite a locked built-in preset."
        raise ValueError(msg)
    return preset_id


def _diagnostic_blocking_detail(report: Any) -> str:
    errors = tuple(getattr(report, "errors", ()))
    if not errors:
        return ""
    first = errors[0]
    slot_id = getattr(first, "slot_id", "")
    target = slot_id or getattr(first, "preset_id", "") or getattr(first, "target", "")
    target_text = f" [{target}]" if target else ""
    remaining = len(errors) - 1
    suffix = f" and {remaining} more" if remaining else ""
    return f"{getattr(first, 'code', 'diagnostic_error')}{target_text}{suffix}."
