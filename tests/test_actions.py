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
    center_pivot,
    clear_selection,
    create_default_registry,
    delete_history,
    frame_selection,
    freeze_transforms,
    run_mel_command,
    set_tool_context,
    toggle_grid,
    toggle_isolate_selected,
    validate_action_ids,
)
from actionrail.authoring import DraftRail, DraftSlot, save_user_preset
from actionrail.runtime import run_action, run_slot


class FakeCmds:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []
        self.grid_visible = True
        self.isolate_selected = False
        self.model_panel = "modelPanel4"
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

    def xform(self, centerPivots: bool = False) -> None:  # noqa: N803
        self.calls.append(("xform", {"centerPivots": centerPivots}))

    def makeIdentity(
        self,
        apply: bool = False,  # noqa: A002
        translate: bool = False,
        rotate: bool = False,
        scale: bool = False,
        normal: bool = False,
    ) -> None:
        self.calls.append(
            (
                "makeIdentity",
                {
                    "apply": apply,
                    "translate": translate,
                    "rotate": rotate,
                    "scale": scale,
                    "normal": normal,
                },
            )
        )

    def delete(self, constructionHistory: bool = False) -> None:  # noqa: N803
        self.calls.append(("delete", {"constructionHistory": constructionHistory}))

    def getPanel(
        self,
        withFocus: bool = False,  # noqa: N803
        visiblePanels: bool = False,  # noqa: N803
        typeOf: str = "",  # noqa: N803
    ) -> str | list[str]:
        if withFocus:
            return self.model_panel
        if visiblePanels:
            return [self.model_panel]
        if typeOf:
            return "modelPanel" if typeOf == self.model_panel else "window"
        return ""

    def isolateSelect(
        self,
        panel: str,
        query: bool = False,
        state: bool | None = None,
    ) -> bool | None:  # noqa: N802
        if query:
            return self.isolate_selected
        if state is not None:
            self.isolate_selected = bool(state)
            self.calls.append(("isolateSelect", {"panel": panel, "state": bool(state)}))
        return None


class FakeMel:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def eval(self, command: str) -> None:  # noqa: A003
        self.calls.append(command)


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

    expected_base_ids = (
        "maya.tool.select",
        "maya.tool.move",
        "maya.tool.translate",
        "maya.tool.rotate",
        "maya.tool.scale",
        "maya.anim.set_key",
        "maya.selection.clear",
        "maya.modeling.center_pivot",
        "maya.modeling.freeze_transforms",
        "maya.modeling.delete_history",
        "maya.view.frame_selection",
        "maya.display.toggle_grid",
        "maya.view.toggle_isolate_selected",
    )
    expected_modeling_ids = (
        "maya.modeling.poly_cube",
        "maya.modeling.poly_sphere",
        "maya.modeling.poly_cylinder",
        "maya.modeling.poly_cone",
        "maya.modeling.poly_torus",
        "maya.modeling.poly_plane",
        "maya.modeling.combine",
        "maya.modeling.mirror",
        "maya.modeling.smooth",
        "maya.modeling.reduce",
        "maya.modeling.remesh",
        "maya.modeling.retopologize",
        "maya.modeling.extrude",
        "maya.modeling.smart_extrude",
        "maya.modeling.bridge",
        "maya.modeling.bevel",
        "maya.modeling.merge",
        "maya.modeling.multi_cut",
        "maya.modeling.target_weld",
        "maya.modeling.quad_draw",
    )

    assert registry.ids() == (*expected_base_ids, *expected_modeling_ids)


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
        ("maya.modeling.center_pivot", ("xform", {"centerPivots": True})),
        (
            "maya.modeling.freeze_transforms",
            (
                "makeIdentity",
                {
                    "apply": True,
                    "translate": True,
                    "rotate": True,
                    "scale": True,
                    "normal": False,
                },
            ),
        ),
        ("maya.modeling.delete_history", ("delete", {"constructionHistory": True})),
        ("maya.view.frame_selection", ("viewFit", None)),
        ("maya.display.toggle_grid", ("grid", False)),
        (
            "maya.view.toggle_isolate_selected",
            ("isolateSelect", {"panel": "modelPanel4", "state": True}),
        ),
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


def test_modeling_actions_skip_empty_selection_without_throwing() -> None:
    cmds = FakeSelectionCmds([])

    assert center_pivot(cmds) == "centerPivotSkipped:noSelection"
    assert freeze_transforms(cmds) == "freezeTransformsSkipped:noSelection"
    assert delete_history(cmds) == "deleteHistorySkipped:noSelection"

    assert cmds.calls == []


def test_toggle_isolate_selected_uses_focused_model_panel() -> None:
    cmds = FakeCmds()

    assert toggle_isolate_selected(cmds) == "isolateSelected:on"
    assert toggle_isolate_selected(cmds) == "isolateSelected:off"

    assert cmds.calls == [
        ("isolateSelect", {"panel": "modelPanel4", "state": True}),
        ("isolateSelect", {"panel": "modelPanel4", "state": False}),
    ]


def test_toggle_isolate_selected_falls_back_to_visible_model_panel() -> None:
    cmds = FakeCmds()
    cmds.model_panel = "modelPanel7"

    def get_panel(
        withFocus: bool = False,  # noqa: N803
        visiblePanels: bool = False,  # noqa: N803
        typeOf: str = "",  # noqa: N803
    ) -> str | list[str]:
        if withFocus:
            return "scriptEditorPanel1"
        if visiblePanels:
            return ["scriptEditorPanel1", "modelPanel7"]
        if typeOf:
            return "modelPanel" if typeOf == "modelPanel7" else "window"
        return ""

    cmds.getPanel = get_panel  # type: ignore[method-assign]

    assert toggle_isolate_selected(cmds) == "isolateSelected:on"
    assert cmds.calls == [
        ("isolateSelect", {"panel": "modelPanel7", "state": True}),
    ]


@pytest.mark.parametrize(
    ("action_id", "command"),
    [
        ("maya.modeling.poly_cube", "CreatePolygonCube"),
        ("maya.modeling.poly_sphere", "CreatePolygonSphere"),
        ("maya.modeling.poly_cylinder", "CreatePolygonCylinder"),
        ("maya.modeling.poly_cone", "CreatePolygonCone"),
        ("maya.modeling.poly_torus", "CreatePolygonTorus"),
        ("maya.modeling.poly_plane", "CreatePolygonPlane"),
        ("maya.modeling.combine", "CombinePolygons"),
        ("maya.modeling.mirror", "MirrorPolygonGeometry"),
        ("maya.modeling.smooth", "SmoothPolygon"),
        ("maya.modeling.reduce", "ReducePolygon"),
        ("maya.modeling.remesh", "PolyRemesh"),
        ("maya.modeling.retopologize", "PolyRetopo"),
        ("maya.modeling.extrude", "PolyExtrude"),
        ("maya.modeling.smart_extrude", "SmartExtrude"),
        ("maya.modeling.bridge", "performBridgeOrFill"),
        ("maya.modeling.bevel", "performBevelOrChamfer"),
        ("maya.modeling.merge", "PolyMerge"),
        ("maya.modeling.multi_cut", "dR_multiCutTool"),
        ("maya.modeling.target_weld", "MergeVertexTool"),
        ("maya.modeling.quad_draw", "dR_quadDrawTool"),
    ],
)
def test_modeling_shelf_actions_run_mel_commands(action_id: str, command: str) -> None:
    mel = FakeMel()
    registry = create_default_registry(FakeCmds(), mel)

    assert registry.run(action_id) == command
    assert mel.calls == [command]


def test_run_mel_command_rejects_empty_commands() -> None:
    with pytest.raises(ValueError, match="cannot be empty"):
        run_mel_command("  ", FakeMel())


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
