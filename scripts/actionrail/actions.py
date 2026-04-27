"""Reusable ActionRail actions backed by Maya commands."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

ActionCallback = Callable[[], Any]

MOVE_CONTEXT = "moveSuperContext"
ROTATE_CONTEXT = "RotateSuperContext"
SCALE_CONTEXT = "scaleSuperContext"


@dataclass(frozen=True)
class Action:
    """Named command that can be attached to an ActionRail widget."""

    id: str
    label: str
    callback: ActionCallback
    tooltip: str = ""


class ActionRegistry:
    """Small action registry used by the overlay widgets."""

    def __init__(self) -> None:
        self._actions: dict[str, Action] = {}

    def register(self, action: Action) -> Action:
        if action.id in self._actions:
            msg = f"Action already registered: {action.id}"
            raise ValueError(msg)
        self._actions[action.id] = action
        return action

    def get(self, action_id: str) -> Action:
        try:
            return self._actions[action_id]
        except KeyError as exc:
            msg = f"Unknown ActionRail action: {action_id}"
            raise KeyError(msg) from exc

    def run(self, action_id: str) -> Any:
        return self.get(action_id).callback()

    def ids(self) -> tuple[str, ...]:
        return tuple(self._actions)

    def actions(self) -> tuple[Action, ...]:
        return tuple(self._actions.values())


def _require_cmds(cmds_module: Any | None = None) -> Any:
    if cmds_module is not None:
        return cmds_module

    try:
        import maya.cmds as cmds  # type: ignore[import-not-found]
    except Exception as exc:  # pragma: no cover - exercised only outside Maya.
        msg = "ActionRail Maya actions require maya.cmds inside Maya."
        raise RuntimeError(msg) from exc
    return cmds


def set_tool_context(context_name: str, cmds_module: Any | None = None) -> str:
    """Set Maya's active tool context and return the requested context."""

    cmds = _require_cmds(cmds_module)
    cmds.setToolTo(context_name)
    return context_name


def set_keyframe(cmds_module: Any | None = None) -> str:
    """Set a keyframe on the current Maya selection."""

    cmds = _require_cmds(cmds_module)
    cmds.setKeyframe()
    return "setKeyframe"


def create_default_registry(cmds_module: Any | None = None) -> ActionRegistry:
    """Create the default Maya action registry.

    ``cmds_module`` is injectable so unit tests can exercise command binding
    without importing Maya.
    """

    registry = ActionRegistry()
    registry.register(
        Action(
            id="maya.tool.move",
            label="Move",
            tooltip="Move tool",
            callback=lambda: set_tool_context(MOVE_CONTEXT, cmds_module),
        )
    )
    registry.register(
        Action(
            id="maya.tool.translate",
            label="Translate",
            tooltip="Translate tool",
            callback=lambda: set_tool_context(MOVE_CONTEXT, cmds_module),
        )
    )
    registry.register(
        Action(
            id="maya.tool.rotate",
            label="Rotate",
            tooltip="Rotate tool",
            callback=lambda: set_tool_context(ROTATE_CONTEXT, cmds_module),
        )
    )
    registry.register(
        Action(
            id="maya.tool.scale",
            label="Scale",
            tooltip="Scale tool",
            callback=lambda: set_tool_context(SCALE_CONTEXT, cmds_module),
        )
    )
    registry.register(
        Action(
            id="maya.anim.set_key",
            label="Set Key",
            tooltip="Set keyframe",
            callback=lambda: set_keyframe(cmds_module),
        )
    )
    return registry


def validate_action_ids(action_ids: Iterable[str], registry: ActionRegistry | None = None) -> None:
    """Raise if any action id is missing from the given registry."""

    action_registry = registry or create_default_registry()
    missing = [action_id for action_id in action_ids if action_id not in action_registry.ids()]
    if missing:
        msg = f"Unknown ActionRail action ids: {', '.join(missing)}"
        raise ValueError(msg)
