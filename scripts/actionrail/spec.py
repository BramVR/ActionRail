"""Built-in ActionRail example specifications."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass

TRANSFORM_STACK_ID = "transform_stack"


@dataclass(frozen=True)
class StackItem:
    type: str
    label: str = ""
    action: str = ""
    tone: str = "neutral"
    tooltip: str = ""
    size: int = 0


@dataclass(frozen=True)
class StackSpec:
    id: str
    anchor: str
    items: tuple[StackItem, ...]


_TRANSFORM_STACK = StackSpec(
    id=TRANSFORM_STACK_ID,
    anchor="viewport.left.center",
    items=(
        StackItem(
            type="toolButton",
            label="M",
            action="maya.tool.move",
            tooltip="Move tool",
        ),
        StackItem(
            type="toolButton",
            label="T",
            action="maya.tool.translate",
            tooltip="Translate tool",
        ),
        StackItem(
            type="toolButton",
            label="R",
            action="maya.tool.rotate",
            tooltip="Rotate tool",
        ),
        StackItem(
            type="toolButton",
            label="S",
            action="maya.tool.scale",
            tone="pink",
            tooltip="Scale tool",
        ),
        StackItem(type="spacer", size=14),
        StackItem(
            type="button",
            label="K",
            action="maya.anim.set_key",
            tone="teal",
            tooltip="Set keyframe",
        ),
    ),
)


def get_example_spec(example_id: str = TRANSFORM_STACK_ID) -> StackSpec:
    """Return a built-in example spec by id."""

    if example_id != TRANSFORM_STACK_ID:
        msg = f"Unknown ActionRail example: {example_id}"
        raise KeyError(msg)
    return deepcopy(_TRANSFORM_STACK)


def action_ids(spec: StackSpec) -> tuple[str, ...]:
    """Return all non-empty action ids referenced by a stack spec."""

    return tuple(item.action for item in spec.items if item.action)
