"""Small Maya state helpers for ActionRail overlays."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class MayaStateSnapshot:
    current_tool: str
    selection_count: int


def _require_cmds(cmds_module: Any | None = None) -> Any:
    if cmds_module is not None:
        return cmds_module

    try:
        import maya.cmds as cmds  # type: ignore[import-not-found]
    except Exception as exc:  # pragma: no cover - exercised only inside Maya.
        msg = "ActionRail state helpers require maya.cmds inside Maya."
        raise RuntimeError(msg) from exc
    return cmds


def current_tool(cmds_module: Any | None = None) -> str:
    cmds = _require_cmds(cmds_module)
    return cmds.currentCtx()


def selection_count(cmds_module: Any | None = None) -> int:
    cmds = _require_cmds(cmds_module)
    return len(cmds.ls(selection=True) or [])


def snapshot(cmds_module: Any | None = None) -> MayaStateSnapshot:
    cmds = _require_cmds(cmds_module)
    return MayaStateSnapshot(
        current_tool=current_tool(cmds),
        selection_count=selection_count(cmds),
    )
