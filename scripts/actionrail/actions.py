"""Reusable ActionRail actions backed by Maya commands."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

ActionCallback = Callable[[], Any]

MOVE_CONTEXT = "moveSuperContext"
ROTATE_CONTEXT = "RotateSuperContext"
SCALE_CONTEXT = "scaleSuperContext"
SELECT_CONTEXT = "selectSuperContext"

__all__ = [
    "MOVE_CONTEXT",
    "ROTATE_CONTEXT",
    "SCALE_CONTEXT",
    "SELECT_CONTEXT",
    "Action",
    "ActionCallback",
    "ActionRegistry",
    "center_pivot",
    "clear_selection",
    "create_default_registry",
    "delete_history",
    "frame_selection",
    "freeze_transforms",
    "run_mel_command",
    "set_keyframe",
    "set_tool_context",
    "toggle_grid",
    "toggle_isolate_selected",
    "validate_action_ids",
]


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


def _require_mel(mel_module: Any | None = None) -> Any:
    if mel_module is not None:
        return mel_module

    try:
        import maya.mel as mel  # type: ignore[import-not-found]
    except Exception as exc:  # pragma: no cover - exercised only outside Maya.
        msg = "ActionRail Maya shelf actions require maya.mel inside Maya."
        raise RuntimeError(msg) from exc
    return mel


def set_tool_context(context_name: str, cmds_module: Any | None = None) -> str:
    """Set Maya's active tool context and return the requested context."""

    cmds = _require_cmds(cmds_module)
    cmds.setToolTo(context_name)
    return context_name


def run_mel_command(command: str, mel_module: Any | None = None) -> str:
    """Run a Maya MEL command/procedure and return the command name."""

    clean_command = command.strip()
    if not clean_command:
        msg = "Maya MEL action command cannot be empty."
        raise ValueError(msg)
    mel = _require_mel(mel_module)
    mel.eval(clean_command)
    return clean_command


def set_keyframe(cmds_module: Any | None = None) -> str:
    """Set a keyframe on the current Maya selection."""

    cmds = _require_cmds(cmds_module)
    if not _current_selection(cmds):
        return "setKeyframeSkipped:noSelection"
    cmds.setKeyframe()
    return "setKeyframe"


def clear_selection(cmds_module: Any | None = None) -> str:
    """Clear Maya's current selection."""

    cmds = _require_cmds(cmds_module)
    cmds.select(clear=True)
    return "selection:cleared"


def frame_selection(cmds_module: Any | None = None) -> str:
    """Frame the current selection in Maya's active viewport."""

    cmds = _require_cmds(cmds_module)
    cmds.viewFit()
    return "viewFit"


def center_pivot(cmds_module: Any | None = None) -> str:
    """Center pivots for the current Maya selection."""

    cmds = _require_cmds(cmds_module)
    if not _current_selection(cmds):
        return "centerPivotSkipped:noSelection"
    cmds.xform(centerPivots=True)
    return "centerPivot"


def freeze_transforms(cmds_module: Any | None = None) -> str:
    """Freeze transforms for the current Maya selection."""

    cmds = _require_cmds(cmds_module)
    if not _current_selection(cmds):
        return "freezeTransformsSkipped:noSelection"
    cmds.makeIdentity(apply=True, translate=True, rotate=True, scale=True, normal=False)
    return "freezeTransforms"


def delete_history(cmds_module: Any | None = None) -> str:
    """Delete construction history for the current Maya selection."""

    cmds = _require_cmds(cmds_module)
    if not _current_selection(cmds):
        return "deleteHistorySkipped:noSelection"
    cmds.delete(constructionHistory=True)
    return "deleteHistory"


def toggle_grid(cmds_module: Any | None = None) -> str:
    """Toggle Maya viewport grid visibility and return the new state."""

    cmds = _require_cmds(cmds_module)
    is_visible = bool(cmds.grid(query=True, toggle=True))
    next_state = not is_visible
    cmds.grid(toggle=next_state)
    return f"grid:{'on' if next_state else 'off'}"


def toggle_isolate_selected(cmds_module: Any | None = None) -> str:
    """Toggle isolate selected in the active Maya model panel."""

    cmds = _require_cmds(cmds_module)
    panel = _active_model_panel(cmds)
    if not panel:
        return "isolateSelectedSkipped:noModelPanel"
    current_state = bool(cmds.isolateSelect(panel, query=True, state=True))
    next_state = not current_state
    cmds.isolateSelect(panel, state=next_state)
    return f"isolateSelected:{'on' if next_state else 'off'}"


_MAYA_SHELF_ACTIONS: tuple[tuple[str, str, str, str], ...] = (
    (
        "maya.modeling.poly_cube",
        "Polygon Cube",
        "Create a polygon cube",
        "CreatePolygonCube",
    ),
    (
        "maya.modeling.poly_sphere",
        "Polygon Sphere",
        "Create a polygon sphere",
        "CreatePolygonSphere",
    ),
    (
        "maya.modeling.poly_cylinder",
        "Polygon Cylinder",
        "Create a polygon cylinder",
        "CreatePolygonCylinder",
    ),
    (
        "maya.modeling.poly_cone",
        "Polygon Cone",
        "Create a polygon cone",
        "CreatePolygonCone",
    ),
    (
        "maya.modeling.poly_torus",
        "Polygon Torus",
        "Create a polygon torus",
        "CreatePolygonTorus",
    ),
    (
        "maya.modeling.poly_plane",
        "Polygon Plane",
        "Create a polygon plane",
        "CreatePolygonPlane",
    ),
    (
        "maya.modeling.combine",
        "Combine",
        "Combine selected polygon objects",
        "CombinePolygons",
    ),
    (
        "maya.modeling.mirror",
        "Mirror",
        "Mirror selected polygon geometry",
        "MirrorPolygonGeometry",
    ),
    (
        "maya.modeling.smooth",
        "Smooth",
        "Smooth selected polygon objects",
        "SmoothPolygon",
    ),
    (
        "maya.modeling.reduce",
        "Reduce",
        "Reduce selected polygon objects",
        "ReducePolygon",
    ),
    (
        "maya.modeling.remesh",
        "Remesh",
        "Remesh selected polygon objects",
        "PolyRemesh",
    ),
    (
        "maya.modeling.retopologize",
        "Retopologize",
        "Retopologize selected polygon objects",
        "PolyRetopo",
    ),
    (
        "maya.modeling.extrude",
        "Extrude",
        "Extrude selected polygon components",
        "PolyExtrude",
    ),
    (
        "maya.modeling.smart_extrude",
        "Smart Extrude",
        "Interactively smart extrude selected mesh faces",
        "SmartExtrude",
    ),
    (
        "maya.modeling.bridge",
        "Bridge",
        "Bridge selected polygon edges or faces",
        "performBridgeOrFill",
    ),
    (
        "maya.modeling.bevel",
        "Bevel Components",
        "Bevel selected polygon edges or faces",
        "performBevelOrChamfer",
    ),
    (
        "maya.modeling.merge",
        "Merge",
        "Merge selected polygon vertices or border edges",
        "PolyMerge",
    ),
    (
        "maya.modeling.multi_cut",
        "Multi-Cut Tool",
        "Cut, slice, and insert edges on polygons",
        "dR_multiCutTool",
    ),
    (
        "maya.modeling.target_weld",
        "Target Weld Tool",
        "Merge one edge or vertex into another",
        "MergeVertexTool",
    ),
    (
        "maya.modeling.quad_draw",
        "Quad Draw Tool",
        "Draw quad topology on live objects",
        "dR_quadDrawTool",
    ),
)


def _current_selection(cmds: Any) -> tuple[str, ...]:
    list_selection = getattr(cmds, "ls", None)
    if not callable(list_selection):
        return ("__unknown_selection__",)
    return tuple(str(item) for item in (list_selection(selection=True) or ()))


def _active_model_panel(cmds: Any) -> str:
    panel = _model_panel_from_focus(cmds)
    if panel:
        return panel

    get_panel = getattr(cmds, "getPanel", None)
    if not callable(get_panel):
        return ""
    visible_panels = get_panel(visiblePanels=True) or ()
    for candidate in visible_panels:
        if _is_model_panel(cmds, str(candidate)):
            return str(candidate)
    return ""


def _model_panel_from_focus(cmds: Any) -> str:
    get_panel = getattr(cmds, "getPanel", None)
    if not callable(get_panel):
        return ""
    focused = get_panel(withFocus=True) or ""
    if focused and _is_model_panel(cmds, str(focused)):
        return str(focused)
    return ""


def _is_model_panel(cmds: Any, panel: str) -> bool:
    get_panel = getattr(cmds, "getPanel", None)
    if not callable(get_panel):
        return False
    try:
        return get_panel(typeOf=panel) == "modelPanel"
    except Exception:
        return False


def create_default_registry(
    cmds_module: Any | None = None,
    mel_module: Any | None = None,
) -> ActionRegistry:
    """Create the default Maya action registry.

    ``cmds_module`` is injectable so unit tests can exercise command binding
    without importing Maya.
    """

    registry = ActionRegistry()
    registry.register(
        Action(
            id="maya.tool.select",
            label="Select",
            tooltip="Select tool",
            callback=lambda: set_tool_context(SELECT_CONTEXT, cmds_module),
        )
    )
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
    registry.register(
        Action(
            id="maya.selection.clear",
            label="Clear Selection",
            tooltip="Clear current selection",
            callback=lambda: clear_selection(cmds_module),
        )
    )
    registry.register(
        Action(
            id="maya.modeling.center_pivot",
            label="Center Pivot",
            tooltip="Center pivot on current selection",
            callback=lambda: center_pivot(cmds_module),
        )
    )
    registry.register(
        Action(
            id="maya.modeling.freeze_transforms",
            label="Freeze Transforms",
            tooltip="Freeze transforms on current selection",
            callback=lambda: freeze_transforms(cmds_module),
        )
    )
    registry.register(
        Action(
            id="maya.modeling.delete_history",
            label="Delete History",
            tooltip="Delete construction history on current selection",
            callback=lambda: delete_history(cmds_module),
        )
    )
    registry.register(
        Action(
            id="maya.view.frame_selection",
            label="Frame Selection",
            tooltip="Frame current selection",
            callback=lambda: frame_selection(cmds_module),
        )
    )
    registry.register(
        Action(
            id="maya.display.toggle_grid",
            label="Toggle Grid",
            tooltip="Toggle viewport grid",
            callback=lambda: toggle_grid(cmds_module),
        )
    )
    registry.register(
        Action(
            id="maya.view.toggle_isolate_selected",
            label="Toggle Isolate Selected",
            tooltip="Toggle isolate selected in the active viewport",
            callback=lambda: toggle_isolate_selected(cmds_module),
        )
    )
    for action_id, label, tooltip, command in _MAYA_SHELF_ACTIONS:
        registry.register(
            Action(
                id=action_id,
                label=label,
                tooltip=tooltip,
                callback=lambda command=command: run_mel_command(command, mel_module),
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
