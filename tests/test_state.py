from __future__ import annotations

from actionrail.state import selection_count, snapshot


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
