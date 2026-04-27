from __future__ import annotations

from actionrail.state import selection_count, snapshot


class FakeCmds:
    def currentCtx(self) -> str:
        return "moveSuperContext"

    def ls(self, selection: bool = False) -> list[str]:
        if selection:
            return ["pCube1", "pSphere1"]
        return []


def test_state_snapshot_uses_injected_cmds() -> None:
    state = snapshot(FakeCmds())

    assert state.current_tool == "moveSuperContext"
    assert state.selection_count == 2


def test_selection_count_handles_empty_maya_result() -> None:
    class EmptyCmds:
        def ls(self, selection: bool = False) -> None:
            return None

    assert selection_count(EmptyCmds()) == 0
