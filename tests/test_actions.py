from __future__ import annotations

import pytest

from actionrail.actions import (
    MOVE_CONTEXT,
    ROTATE_CONTEXT,
    SCALE_CONTEXT,
    Action,
    ActionRegistry,
    create_default_registry,
)
from actionrail.runtime import run_action, run_slot


class FakeCmds:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str | None]] = []

    def setToolTo(self, context: str) -> None:
        self.calls.append(("setToolTo", context))

    def setKeyframe(self) -> None:
        self.calls.append(("setKeyframe", None))


def test_default_registry_contains_phase_zero_actions() -> None:
    registry = create_default_registry(FakeCmds())

    assert registry.ids() == (
        "maya.tool.move",
        "maya.tool.translate",
        "maya.tool.rotate",
        "maya.tool.scale",
        "maya.anim.set_key",
    )


@pytest.mark.parametrize(
    ("action_id", "expected_call"),
    [
        ("maya.tool.move", ("setToolTo", MOVE_CONTEXT)),
        ("maya.tool.translate", ("setToolTo", MOVE_CONTEXT)),
        ("maya.tool.rotate", ("setToolTo", ROTATE_CONTEXT)),
        ("maya.tool.scale", ("setToolTo", SCALE_CONTEXT)),
        ("maya.anim.set_key", ("setKeyframe", None)),
    ],
)
def test_default_actions_call_maya_cmds(
    action_id: str,
    expected_call: tuple[str, str | None],
) -> None:
    cmds = FakeCmds()
    registry = create_default_registry(cmds)

    registry.run(action_id)

    assert cmds.calls == [expected_call]


def test_registry_rejects_duplicate_action_ids() -> None:
    registry = ActionRegistry()
    registry.register(Action("same.id", "First", lambda: None))

    with pytest.raises(ValueError, match="same.id"):
        registry.register(Action("same.id", "Second", lambda: None))


def test_runtime_run_action_uses_registry_without_overlay() -> None:
    cmds = FakeCmds()
    registry = create_default_registry(cmds)

    assert run_action("maya.tool.rotate", registry=registry) == ROTATE_CONTEXT

    assert cmds.calls == [("setToolTo", ROTATE_CONTEXT)]


def test_runtime_run_slot_uses_preset_slot_action_without_overlay() -> None:
    cmds = FakeCmds()
    registry = create_default_registry(cmds)

    result = run_slot("transform_stack", "transform_stack.set_key", registry=registry)

    assert result == "setKeyframe"
    assert cmds.calls == [("setKeyframe", None)]


def test_runtime_run_slot_accepts_unqualified_slot_id() -> None:
    cmds = FakeCmds()
    registry = create_default_registry(cmds)

    result = run_slot("transform_stack", "set_key", registry=registry)

    assert result == "setKeyframe"
    assert cmds.calls == [("setKeyframe", None)]


def test_runtime_run_slot_rejects_slot_without_action() -> None:
    registry = create_default_registry(FakeCmds())

    with pytest.raises(ValueError, match="has no action"):
        run_slot("transform_stack", "transform_stack.gap", registry=registry)


def test_runtime_run_slot_rejects_unknown_slot() -> None:
    registry = create_default_registry(FakeCmds())

    with pytest.raises(KeyError, match="missing.slot"):
        run_slot("transform_stack", "missing.slot", registry=registry)
