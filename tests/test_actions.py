from __future__ import annotations

import sys
from types import ModuleType

import pytest

from actionrail.actions import (
    MOVE_CONTEXT,
    ROTATE_CONTEXT,
    SCALE_CONTEXT,
    SELECT_CONTEXT,
    Action,
    ActionRegistry,
    clear_selection,
    create_default_registry,
    frame_selection,
    set_tool_context,
    toggle_grid,
    validate_action_ids,
)
from actionrail.authoring import DraftRail, DraftSlot, save_user_preset
from actionrail.runtime import run_action, run_slot


class FakeCmds:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []
        self.grid_visible = True
        self.selection: list[str] = ["cube"]

    def setToolTo(self, context: str) -> None:
        self.calls.append(("setToolTo", context))

    def setKeyframe(self) -> None:
        self.calls.append(("setKeyframe", None))

    def grid(self, query: bool = False, toggle: bool | None = None) -> bool | None:
        if query and toggle:
            return self.grid_visible
        if toggle is not None:
            self.grid_visible = bool(toggle)
            self.calls.append(("grid", self.grid_visible))
        return None

    def select(self, clear: bool = False) -> None:
        if clear:
            self.selection = []
        self.calls.append(("select", "clear" if clear else ""))

    def viewFit(self) -> None:  # noqa: N802
        self.calls.append(("viewFit", None))


class FakeSelectionCmds(FakeCmds):
    def __init__(self, selection: list[str]) -> None:
        super().__init__()
        self.selection = selection

    def ls(self, selection: bool = False) -> list[str]:
        if selection:
            return self.selection
        return []


def test_default_registry_contains_phase_zero_actions() -> None:
    registry = create_default_registry(FakeCmds())

    assert registry.ids() == (
        "maya.tool.select",
        "maya.tool.move",
        "maya.tool.translate",
        "maya.tool.rotate",
        "maya.tool.scale",
        "maya.anim.set_key",
        "maya.selection.clear",
        "maya.view.frame_selection",
        "maya.display.toggle_grid",
    )


@pytest.mark.parametrize(
    ("action_id", "expected_call"),
    [
        ("maya.tool.select", ("setToolTo", SELECT_CONTEXT)),
        ("maya.tool.move", ("setToolTo", MOVE_CONTEXT)),
        ("maya.tool.translate", ("setToolTo", MOVE_CONTEXT)),
        ("maya.tool.rotate", ("setToolTo", ROTATE_CONTEXT)),
        ("maya.tool.scale", ("setToolTo", SCALE_CONTEXT)),
        ("maya.anim.set_key", ("setKeyframe", None)),
        ("maya.selection.clear", ("select", "clear")),
        ("maya.view.frame_selection", ("viewFit", None)),
        ("maya.display.toggle_grid", ("grid", False)),
    ],
)
def test_default_actions_call_maya_cmds(
    action_id: str,
    expected_call: tuple[str, object],
) -> None:
    cmds = FakeCmds()
    registry = create_default_registry(cmds)

    registry.run(action_id)

    assert cmds.calls == [expected_call]


def test_toggle_grid_toggles_maya_grid_state() -> None:
    cmds = FakeCmds()

    assert toggle_grid(cmds) == "grid:off"
    assert toggle_grid(cmds) == "grid:on"

    assert cmds.calls == [("grid", False), ("grid", True)]


def test_selection_actions_use_maya_selection_commands() -> None:
    cmds = FakeCmds()

    assert clear_selection(cmds) == "selection:cleared"
    assert cmds.selection == []
    assert frame_selection(cmds) == "viewFit"

    assert cmds.calls == [("select", "clear"), ("viewFit", None)]


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


def test_runtime_run_slot_resolves_saved_user_preset(tmp_path) -> None:
    save_user_preset(
        DraftRail(
            id="artist_tools",
            slots=(DraftSlot(id="key", label="K", action="maya.anim.set_key"),),
        ),
        preset_dir=tmp_path,
    )
    cmds = FakeCmds()
    registry = create_default_registry(cmds)

    result = run_slot("artist_tools", "key", registry=registry, user_preset_dir=tmp_path)

    assert result == "setKeyframe"
    assert cmds.calls == [("setKeyframe", None)]


def test_set_keyframe_skips_empty_selection_without_throwing() -> None:
    cmds = FakeSelectionCmds([])
    registry = create_default_registry(cmds)

    result = registry.run("maya.anim.set_key")

    assert result == "setKeyframeSkipped:noSelection"
    assert cmds.calls == []


def test_set_keyframe_runs_for_selected_targets() -> None:
    cmds = FakeSelectionCmds(["pCube1"])
    registry = create_default_registry(cmds)

    result = registry.run("maya.anim.set_key")

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


def test_maya_action_requires_cmds_when_not_in_maya() -> None:
    with pytest.raises(RuntimeError, match="require maya.cmds"):
        set_tool_context(MOVE_CONTEXT)


def test_maya_action_imports_cmds_when_available(monkeypatch) -> None:
    cmds = FakeCmds()
    maya_module = ModuleType("maya")
    monkeypatch.setitem(sys.modules, "maya", maya_module)
    monkeypatch.setitem(sys.modules, "maya.cmds", cmds)

    assert set_tool_context(ROTATE_CONTEXT) == ROTATE_CONTEXT
    assert cmds.calls == [("setToolTo", ROTATE_CONTEXT)]


def test_validate_action_ids_reports_missing_ids() -> None:
    registry = ActionRegistry()
    registry.register(Action("known.action", "Known", lambda: None))

    with pytest.raises(ValueError, match="missing.action"):
        validate_action_ids(["known.action", "missing.action"], registry=registry)
