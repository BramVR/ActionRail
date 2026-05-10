from __future__ import annotations

import sys
from types import ModuleType

import pytest

from actionrail.state import MayaStateService, current_tool, selection_count, snapshot


class FakeCmds:
    def __init__(self) -> None:
        self.camera_panel = ""

    def currentCtx(self) -> str:
        return "moveSuperContext"

    def ls(self, selection: bool = False) -> list[str]:
        if selection:
            return ["pCube1", "pSphere1"]
        return []

    def getPanel(self, **kwargs: object) -> object:  # noqa: N802
        if kwargs.get("withFocus"):
            return "outlinerPanel1"
        return None

    def modelPanel(self, panel: str, **kwargs: object) -> str:  # noqa: N802
        if kwargs.get("query") and kwargs.get("camera"):
            self.camera_panel = panel
            return "persp"
        return ""

    def play(self, **kwargs: object) -> bool:
        return False


def test_state_snapshot_uses_injected_cmds() -> None:
    state = snapshot(FakeCmds())

    assert state.current_tool == "moveSuperContext"
    assert state.selection_count == 2


def test_state_snapshot_uses_supplied_active_panel_for_camera_context() -> None:
    cmds = FakeCmds()

    state = snapshot(cmds, active_panel="modelPanel4")

    assert state.active_panel == "modelPanel4"
    assert state.active_camera == "persp"
    assert cmds.camera_panel == "modelPanel4"


def test_selection_count_handles_empty_maya_result() -> None:
    class EmptyCmds:
        def ls(self, selection: bool = False) -> None:
            return None

    assert selection_count(EmptyCmds()) == 0


def test_state_requires_cmds_when_not_in_maya() -> None:
    with pytest.raises(RuntimeError, match="require maya.cmds"):
        current_tool()


def test_state_imports_cmds_when_available(monkeypatch) -> None:
    cmds = FakeCmds()
    maya_module = ModuleType("maya")
    monkeypatch.setitem(sys.modules, "maya", maya_module)
    monkeypatch.setitem(sys.modules, "maya.cmds", cmds)

    assert current_tool() == "moveSuperContext"


def test_state_snapshot_handles_panel_camera_and_playback_failures() -> None:
    class BrokenCmds(FakeCmds):
        def getPanel(self, **kwargs: object) -> object:  # noqa: N802
            raise RuntimeError("focus unavailable")

        def modelPanel(self, panel: str, **kwargs: object) -> str:  # noqa: N802
            raise RuntimeError("camera unavailable")

        def play(self, **kwargs: object) -> bool:
            raise RuntimeError("playback unavailable")

    state = snapshot(BrokenCmds())

    assert state.active_panel == ""
    assert state.active_camera == ""
    assert state.playback_playing is False


def test_state_snapshot_handles_camera_failure_with_supplied_panel() -> None:
    class BrokenCameraCmds(FakeCmds):
        def modelPanel(self, panel: str, **kwargs: object) -> str:  # noqa: N802
            raise RuntimeError("camera unavailable")

    state = snapshot(BrokenCameraCmds(), active_panel="modelPanel4")

    assert state.active_panel == "modelPanel4"
    assert state.active_camera == ""


def test_state_snapshot_ignores_non_string_panel_and_camera() -> None:
    class NonStringCmds(FakeCmds):
        def getPanel(self, **kwargs: object) -> object:  # noqa: N802
            return 123

        def modelPanel(self, panel: str, **kwargs: object) -> object:  # noqa: N802
            return 456

        def play(self, **kwargs: object) -> bool:
            return True

    state = snapshot(NonStringCmds(), active_panel="modelPanel4")
    unfocused_state = snapshot(NonStringCmds())

    assert state.active_camera == ""
    assert state.playback_playing is True
    assert unfocused_state.active_panel == ""


def test_state_service_reads_only_requested_dependencies() -> None:
    class CountingCmds(FakeCmds):
        def __init__(self) -> None:
            super().__init__()
            self.current_ctx_calls = 0
            self.selection_calls = 0
            self.panel_calls = 0
            self.camera_calls = 0
            self.play_calls = 0

        def currentCtx(self) -> str:  # noqa: N802
            self.current_ctx_calls += 1
            return "moveSuperContext"

        def ls(self, selection: bool = False) -> list[str]:
            self.selection_calls += 1
            return super().ls(selection=selection)

        def getPanel(self, **kwargs: object) -> object:  # noqa: N802
            self.panel_calls += 1
            return super().getPanel(**kwargs)

        def modelPanel(self, panel: str, **kwargs: object) -> str:  # noqa: N802
            self.camera_calls += 1
            return super().modelPanel(panel, **kwargs)

        def play(self, **kwargs: object) -> bool:
            self.play_calls += 1
            return super().play(**kwargs)

    cmds = CountingCmds()
    service = MayaStateService(cmds)

    state = service.refresh(
        active_panels=("modelPanel4",),
        dependencies=frozenset({"maya.tool"}),
    )

    assert state.current_tool == "moveSuperContext"
    assert state.selection_count == 0
    assert state.active_panel == ""
    assert state.active_camera == ""
    assert cmds.current_ctx_calls == 1
    assert cmds.selection_calls == 0
    assert cmds.panel_calls == 0
    assert cmds.camera_calls == 0
    assert cmds.play_calls == 0
