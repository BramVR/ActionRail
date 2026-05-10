"""Small Maya state helpers for ActionRail overlays."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class MayaStateSnapshot:
    current_tool: str
    selection_count: int
    active_panel: str = ""
    active_camera: str = ""
    playback_playing: bool = False


STATE_DEPENDENCIES = frozenset(
    {
        "maya.tool",
        "selection.count",
        "active.panel",
        "active.camera",
        "playback.playing",
    }
)


class MayaStateService:
    """Shared Maya state snapshot cache for predicate refresh schedulers."""

    def __init__(self, cmds_module: Any | None = None) -> None:
        self.cmds = _require_cmds(cmds_module)
        self.snapshot: MayaStateSnapshot | None = None
        self.changed_dependencies: frozenset[str] = STATE_DEPENDENCIES
        self._camera_by_panel: dict[str, str] = {}

    def refresh(
        self,
        *,
        active_panels: tuple[str, ...] = (),
        dependencies: frozenset[str] | None = None,
    ) -> MayaStateSnapshot:
        """Read Maya state once and cache per-panel camera lookups."""

        dependencies = STATE_DEPENDENCIES if dependencies is None else dependencies
        previous = self.snapshot
        panel = (
            _active_panel(self.cmds)
            if dependencies.intersection({"active.panel", "active.camera"})
            else previous.active_panel
            if previous is not None
            else ""
        )
        cameras = (
            {
                panel_id: _active_camera(self.cmds, panel_id)
                for panel_id in dict.fromkeys((panel, *active_panels))
                if panel_id
            }
            if "active.camera" in dependencies
            else dict(self._camera_by_panel)
        )
        base = MayaStateSnapshot(
            current_tool=(
                current_tool(self.cmds)
                if "maya.tool" in dependencies
                else previous.current_tool
                if previous is not None
                else ""
            ),
            selection_count=(
                selection_count(self.cmds)
                if "selection.count" in dependencies
                else previous.selection_count
                if previous is not None
                else 0
            ),
            active_panel=panel,
            active_camera=cameras.get(panel, ""),
            playback_playing=(
                _playback_playing(self.cmds)
                if "playback.playing" in dependencies
                else previous.playback_playing
                if previous is not None
                else False
            ),
        )
        self.snapshot = base
        self._camera_by_panel = cameras
        self.changed_dependencies = _changed_dependencies(previous, base)
        return base

    def snapshot_for_panel(self, panel: str | None = None) -> MayaStateSnapshot:
        """Return the cached snapshot, overriding panel fields for a host."""

        base = self.snapshot
        if base is None:
            base = self.refresh(active_panels=(panel,) if panel else ())
        if not panel:
            return base
        return MayaStateSnapshot(
            current_tool=base.current_tool,
            selection_count=base.selection_count,
            active_panel=panel,
            active_camera=self._camera_by_panel.get(panel, ""),
            playback_playing=base.playback_playing,
        )


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
    try:
        return str(cmds.currentCtx())
    except Exception:
        return ""


def selection_count(cmds_module: Any | None = None) -> int:
    cmds = _require_cmds(cmds_module)
    try:
        return len(cmds.ls(selection=True) or [])
    except Exception:
        return 0


def snapshot(cmds_module: Any | None = None, active_panel: str | None = None) -> MayaStateSnapshot:
    cmds = _require_cmds(cmds_module)
    panel = active_panel if active_panel is not None else _active_panel(cmds)
    return MayaStateSnapshot(
        current_tool=current_tool(cmds),
        selection_count=selection_count(cmds),
        active_panel=panel,
        active_camera=_active_camera(cmds, panel),
        playback_playing=_playback_playing(cmds),
    )


def _changed_dependencies(
    previous: MayaStateSnapshot | None,
    current: MayaStateSnapshot,
) -> frozenset[str]:
    if previous is None:
        return STATE_DEPENDENCIES

    changed: set[str] = set()
    if previous.current_tool != current.current_tool:
        changed.add("maya.tool")
    if previous.selection_count != current.selection_count:
        changed.add("selection.count")
    if previous.active_panel != current.active_panel:
        changed.add("active.panel")
    if previous.active_camera != current.active_camera:
        changed.add("active.camera")
    if previous.playback_playing != current.playback_playing:
        changed.add("playback.playing")
    return frozenset(changed)


def _active_panel(cmds: Any) -> str:
    try:
        panel = cmds.getPanel(withFocus=True)
    except Exception:
        return ""
    return panel if isinstance(panel, str) else ""


def _active_camera(cmds: Any, panel: str) -> str:
    if not panel:
        return ""
    try:
        camera = cmds.modelPanel(panel, query=True, camera=True)
    except Exception:
        return ""
    return camera if isinstance(camera, str) else ""


def _playback_playing(cmds: Any) -> bool:
    try:
        return bool(cmds.play(query=True, state=True))
    except Exception:
        return False
