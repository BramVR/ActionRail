"""Runtime registry and public overlay lifecycle operations."""

from __future__ import annotations

from typing import Any

from .actions import ActionRegistry, create_default_registry
from .spec import TRANSFORM_STACK_ID, get_example_spec

_OVERLAYS: dict[str, Any] = {}

__all__ = [
    "active_overlay_ids",
    "active_overlay_states",
    "hide_all",
    "hide_example",
    "reload",
    "run_action",
    "run_slot",
    "show_example",
    "update_slot_key_label",
]


def show_example(
    example_id: str = TRANSFORM_STACK_ID,
    *,
    panel: str | None = None,
    registry: ActionRegistry | None = None,
) -> Any:
    """Show a built-in ActionRail example overlay."""

    spec = get_example_spec(example_id)
    hide_example(example_id)

    from .overlay import ViewportOverlayHost

    host = ViewportOverlayHost(spec, panel=panel, registry=registry)
    host.show()
    _OVERLAYS[example_id] = host
    return host


def hide_example(example_id: str) -> None:
    host = _OVERLAYS.pop(example_id, None)
    if host is not None:
        host.close()


def hide_all() -> None:
    """Hide and delete all ActionRail overlays owned by this Python session."""

    for example_id in list(_OVERLAYS):
        hide_example(example_id)


def reload(example_id: str = TRANSFORM_STACK_ID, *, panel: str | None = None) -> Any:
    """Rebuild the default overlay after cleaning up existing widgets."""

    hide_all()
    return show_example(example_id, panel=panel)


def active_overlay_ids() -> tuple[str, ...]:
    """Return ids for overlays currently tracked by the runtime registry."""

    return tuple(_OVERLAYS)


def active_overlay_states() -> tuple[dict[str, object], ...]:
    """Return diagnostic support state for active overlay hosts."""

    return tuple(
        _overlay_state(preset_id, host) for preset_id, host in _OVERLAYS.items()
    )


def update_slot_key_label(preset_id: str, slot_id: str, key_label: str) -> int:
    """Update the rendered key label for an active preset slot, if visible."""

    host = _OVERLAYS.get(preset_id)
    if host is None:
        return 0
    return host.update_slot_key_label(_qualified_slot_id(preset_id, slot_id), key_label)


def run_action(action_id: str, *, registry: ActionRegistry | None = None) -> Any:
    """Run a registered ActionRail action without requiring an overlay widget."""

    action_registry = registry or create_default_registry()
    return action_registry.run(action_id)


def run_slot(
    preset_id: str,
    slot_id: str,
    *,
    registry: ActionRegistry | None = None,
) -> Any:
    """Run the action attached to a slot in a built-in preset."""

    spec = get_example_spec(preset_id)
    qualified_slot_id = _qualified_slot_id(preset_id, slot_id)
    for item in spec.items:
        if item.id == qualified_slot_id:
            if not item.action:
                msg = f"ActionRail slot has no action: {preset_id}/{qualified_slot_id}"
                raise ValueError(msg)
            return run_action(item.action, registry=registry)

    msg = f"Unknown ActionRail slot: {preset_id}/{qualified_slot_id}"
    raise KeyError(msg)


def _qualified_slot_id(preset_id: str, slot_id: str) -> str:
    prefix = f"{preset_id}."
    if slot_id.startswith(prefix):
        return slot_id
    return f"{preset_id}.{slot_id}"


def _overlay_state(preset_id: str, host: Any) -> dict[str, object]:
    widget = getattr(host, "widget", None)
    timer = getattr(host, "_predicate_refresh_timer", None)
    return {
        "preset_id": preset_id,
        "panel": getattr(host, "panel", ""),
        "widget_visible": _safe_widget_visible(widget),
        "widget_valid": _safe_widget_valid(widget),
        "filter_target_count": len(getattr(host, "_filter_targets", ()) or ()),
        "predicate_timer_active": _safe_timer_active(timer),
    }


def _safe_widget_visible(widget: Any) -> bool:
    is_visible = getattr(widget, "isVisible", None)
    if not callable(is_visible):
        return False
    try:
        return bool(is_visible())
    except Exception:
        return False


def _safe_widget_valid(widget: Any) -> bool:
    if widget is None:
        return False
    try:
        from .overlay import _qt_widget_is_valid

        return bool(_qt_widget_is_valid(widget))
    except Exception:
        return False


def _safe_timer_active(timer: Any) -> bool:
    if timer is None:
        return False
    is_active = getattr(timer, "isActive", None)
    if not callable(is_active):
        return True
    try:
        return bool(is_active())
    except Exception:
        return True
