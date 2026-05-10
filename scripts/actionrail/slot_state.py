"""Pure render-state resolution for ActionRail slots.

Purpose: resolve validated slot specs into runtime state for widgets and tests.
Owns: predicate evaluation, action/icon diagnostics, tooltip fallback, visibility.
Used by: Qt widgets and diagnostic-focused tests; imports no Qt modules.
"""

from __future__ import annotations

from dataclasses import dataclass

from .actions import ActionRegistry
from .icon_catalog import icon_status
from .icon_types import IconStatus
from .predicates import PredicateContext, availability_blocking_targets, evaluate_predicate
from .spec import StackItem, StackSpec

__all__ = [
    "SlotRenderState",
    "button_secondary_text",
    "button_text",
    "is_item_active",
    "is_item_visible",
    "resolve_slot_render_state",
    "visible_action_items",
]


@dataclass(frozen=True)
class SlotRenderState:
    """Resolved, mutable-at-runtime state for one rendered action slot."""

    label: str
    key_label: str
    icon: str
    icon_path: str
    icon_name: str
    tone: str
    tooltip: str
    enabled: bool
    active: bool
    locked: bool = False
    diagnostic_code: str = ""
    diagnostic_severity: str = ""
    diagnostic_badge: str = ""

    @property
    def text(self) -> str:
        return button_text(self.label, self.key_label, self.diagnostic_badge)

    @property
    def active_property(self) -> str:
        return "true" if self.active else "false"


@dataclass(frozen=True)
class _SlotDiagnostic:
    code: str = ""
    severity: str = ""
    badge: str = ""
    message: str = ""

    @property
    def blocks_enabled(self) -> bool:
        return self.severity == "error" or self.code in {"missing_command", "missing_plugin"}

    @property
    def has_issue(self) -> bool:
        return bool(self.code)


_NO_SLOT_DIAGNOSTIC = _SlotDiagnostic()


def button_text(label: str, key_label: str, diagnostic_badge: str = "") -> str:
    secondary = button_secondary_text(key_label, diagnostic_badge)
    if not secondary:
        return label
    if not label:
        return secondary
    return f"{label}\n{secondary}"


def button_secondary_text(key_label: str, diagnostic_badge: str = "") -> str:
    if key_label and diagnostic_badge:
        return f"{key_label}{diagnostic_badge}"
    return key_label or diagnostic_badge


def resolve_slot_render_state(
    item: StackItem,
    registry: ActionRegistry,
    context: PredicateContext | None = None,
    *,
    key_label: str | None = None,
) -> SlotRenderState:
    """Resolve the public render-state contract for one action slot."""

    item_context = _item_context(item, registry, context)
    icon = _icon_status(item.icon, item_context) if item.icon else None
    diagnostic = _slot_diagnostic(item, registry, item_context, icon_status=icon)
    locked = not bool(item.action)
    return SlotRenderState(
        label=item.label,
        key_label=item.key_label if key_label is None else key_label,
        icon=item.icon,
        icon_path=str(icon.path or "") if icon is not None else "",
        icon_name=icon.qt_name if icon is not None else "",
        tone=item.tone,
        tooltip=_diagnostic_tooltip(_item_tooltip(item, registry), diagnostic),
        enabled=not locked
        and evaluate_predicate(item.enabled_when, item_context)
        and not diagnostic.blocks_enabled,
        active=not locked and is_item_active(item, item_context),
        locked=locked,
        diagnostic_code=diagnostic.code,
        diagnostic_severity=diagnostic.severity,
        diagnostic_badge=diagnostic.badge,
    )


def _item_tooltip(item: StackItem, registry: ActionRegistry | None = None) -> str:
    if item.tooltip:
        return item.tooltip

    get_action = getattr(registry, "get", None)
    if get_action is None:
        return ""

    try:
        action = get_action(item.action)
    except Exception:
        return ""

    tooltip = getattr(action, "tooltip", "")
    return tooltip if isinstance(tooltip, str) else ""


def _slot_diagnostic(
    item: StackItem,
    registry: ActionRegistry | None = None,
    context: PredicateContext | None = None,
    *,
    icon_status: IconStatus | None = None,
) -> _SlotDiagnostic:
    get_action = getattr(registry, "get", None)
    if item.action and get_action is not None:
        try:
            get_action(item.action)
        except Exception:
            return _SlotDiagnostic(
                code="missing_action",
                severity="error",
                badge="!",
                message=f"Missing ActionRail action: {item.action}",
            )

    availability_diagnostic = _availability_diagnostic(item, context)
    if availability_diagnostic.has_issue:
        return availability_diagnostic

    if item.icon:
        return _icon_diagnostic(item.icon, context, icon_status=icon_status)

    return _NO_SLOT_DIAGNOSTIC


def _icon_diagnostic(
    icon_id: str,
    context: PredicateContext | None = None,
    *,
    icon_status: IconStatus | None = None,
) -> _SlotDiagnostic:
    status = icon_status or _icon_status(icon_id, context)
    if status.ok:
        return _NO_SLOT_DIAGNOSTIC
    if status.issue is not None:
        return _SlotDiagnostic(
            code=status.issue.code,
            severity="warning",
            badge="?",
            message=status.issue.message,
        )
    return _SlotDiagnostic(
        code="missing_icon",
        severity="warning",
        badge="?",
        message=f"Missing ActionRail icon: {icon_id}",
    )


def _icon_status(icon_id: str, context: PredicateContext | None = None) -> IconStatus:
    if context is None or context.cmds_module is None:
        return icon_status(icon_id)
    return icon_status(icon_id, cmds_module=context.cmds_module)


def _availability_diagnostic(
    item: StackItem,
    context: PredicateContext | None,
) -> _SlotDiagnostic:
    if context is None:
        return _NO_SLOT_DIAGNOSTIC

    for field_name in ("enabled_when", "visible_when", "active_when"):
        predicate = getattr(item, field_name)
        if not predicate.strip():
            continue
        for kind, target in availability_blocking_targets(predicate, context):
            if kind == "command":
                return _SlotDiagnostic(
                    code="missing_command",
                    severity="warning",
                    badge="?",
                    message=f"Unavailable Maya command in {field_name}: {target}",
                )
            if kind == "plugin":
                return _SlotDiagnostic(
                    code="missing_plugin",
                    severity="warning",
                    badge="?",
                    message=f"Unavailable Maya plugin in {field_name}: {target}",
                )

    return _NO_SLOT_DIAGNOSTIC


def _diagnostic_tooltip(base_tooltip: str, diagnostic: _SlotDiagnostic) -> str:
    if not diagnostic.message:
        return base_tooltip
    if not base_tooltip:
        return diagnostic.message
    return f"{base_tooltip}\n{diagnostic.message}"


def is_item_visible(item: StackItem, context: PredicateContext | None = None) -> bool:
    item_context = _item_context(item, context=context)
    if evaluate_predicate(item.visible_when, item_context):
        return True
    return bool(availability_blocking_targets(item.visible_when, item_context))


def is_item_active(item: StackItem, context: PredicateContext | None = None) -> bool:
    return bool(item.active_when.strip()) and evaluate_predicate(
        item.active_when,
        _item_context(item, context=context),
    )


def _item_context(
    item: StackItem,
    registry: ActionRegistry | None = None,
    context: PredicateContext | None = None,
) -> PredicateContext:
    context = context or PredicateContext()
    return PredicateContext(
        state=context.state,
        registry=registry or context.registry,
        item=item,
        cmds_module=context.cmds_module,
    )


def visible_action_items(
    spec: StackSpec,
    context: PredicateContext | None = None,
) -> tuple[StackItem, ...]:
    return tuple(
        item
        for item in spec.items
        if item.type in {"button", "toolButton"} and is_item_visible(item, context)
    )
