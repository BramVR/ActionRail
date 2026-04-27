"""Runtime registry and public overlay lifecycle operations."""

from __future__ import annotations

from typing import Any

from .spec import TRANSFORM_STACK_ID, get_example_spec

_OVERLAYS: dict[str, Any] = {}


def show_example(example_id: str = TRANSFORM_STACK_ID, *, panel: str | None = None) -> Any:
    """Show a built-in ActionRail example overlay."""

    spec = get_example_spec(example_id)
    hide_example(example_id)

    from .overlay import ViewportOverlayHost

    host = ViewportOverlayHost(spec, panel=panel)
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
