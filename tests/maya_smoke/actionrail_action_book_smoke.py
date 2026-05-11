from __future__ import annotations

import json
import sys
from pathlib import Path

__args__ = globals().get("__args__", {})

repo_scripts = __args__.get("repo_scripts")
if repo_scripts and repo_scripts not in sys.path:
    sys.path.insert(0, repo_scripts)

catalog_path = Path(
    __args__.get(
        "catalog_path",
        "C:/PROJECTS/GG/ScreenUI/.gg-maya-sessiond/screenshots/"
        "actionrail_action_book_catalog.json",
    )
)
catalog_path.parent.mkdir(parents=True, exist_ok=True)

from maya import cmds, mel  # noqa: E402

import actionrail  # noqa: E402
import actionrail.icons as actionrail_icons  # noqa: E402

cmds.file(new=True, force=True)

grid_entry = actionrail.action_book_entry_by_id("maya.display.toggle_grid")
select_entry = actionrail.action_book_entry_by_id("maya.tool.select")
clear_entry = actionrail.action_book_entry_by_id("maya.selection.clear")
frame_entry = actionrail.action_book_entry_by_id("maya.view.frame_selection")
center_pivot_entry = actionrail.action_book_entry_by_id("maya.modeling.center_pivot")
freeze_entry = actionrail.action_book_entry_by_id("maya.modeling.freeze_transforms")
history_entry = actionrail.action_book_entry_by_id("maya.modeling.delete_history")
isolate_entry = actionrail.action_book_entry_by_id("maya.view.toggle_isolate_selected")
modeling_shelf_commands = {
    "maya.modeling.poly_cube": "CreatePolygonCube",
    "maya.modeling.poly_sphere": "CreatePolygonSphere",
    "maya.modeling.poly_cylinder": "CreatePolygonCylinder",
    "maya.modeling.poly_cone": "CreatePolygonCone",
    "maya.modeling.poly_torus": "CreatePolygonTorus",
    "maya.modeling.poly_plane": "CreatePolygonPlane",
    "maya.modeling.combine": "CombinePolygons",
    "maya.modeling.mirror": "MirrorPolygonGeometry",
    "maya.modeling.smooth": "SmoothPolygon",
    "maya.modeling.reduce": "ReducePolygon",
    "maya.modeling.remesh": "PolyRemesh",
    "maya.modeling.retopologize": "PolyRetopo",
    "maya.modeling.extrude": "PolyExtrude",
    "maya.modeling.smart_extrude": "SmartExtrude",
    "maya.modeling.bridge": "performBridgeOrFill",
    "maya.modeling.bevel": "performBevelOrChamfer",
    "maya.modeling.merge": "PolyMerge",
    "maya.modeling.multi_cut": "dR_multiCutTool",
    "maya.modeling.target_weld": "MergeVertexTool",
    "maya.modeling.quad_draw": "dR_quadDrawTool",
}
modeling_shelf_entries = {
    action_id: actionrail.action_book_entry_by_id(action_id)
    for action_id in modeling_shelf_commands
}
choices = actionrail.action_book_entries()

before = bool(cmds.grid(query=True, toggle=True))
first_result = actionrail.run_action("maya.display.toggle_grid")
after_first = bool(cmds.grid(query=True, toggle=True))
second_result = actionrail.run_action("maya.display.toggle_grid")
after_second = bool(cmds.grid(query=True, toggle=True))

cube = cmds.polyCube(name="actionrailActionBookCube")[0]
cmds.select(cube, replace=True)
select_result = actionrail.run_action("maya.tool.select")
context_after_select = cmds.currentCtx()
center_pivot_result = actionrail.run_action("maya.modeling.center_pivot")
cmds.setAttr(f"{cube}.translateX", 3)
cmds.setAttr(f"{cube}.rotateY", 20)
cmds.setAttr(f"{cube}.scaleZ", 2)
freeze_result = actionrail.run_action("maya.modeling.freeze_transforms")
translate_x_after_freeze = cmds.getAttr(f"{cube}.translateX")
rotate_y_after_freeze = cmds.getAttr(f"{cube}.rotateY")
scale_z_after_freeze = cmds.getAttr(f"{cube}.scaleZ")
cmds.polyBevel(cube, segments=1, offset=0.1)
history_before_delete = cmds.listHistory(cube) or []
history_result = actionrail.run_action("maya.modeling.delete_history")
history_after_delete = cmds.listHistory(cube) or []
panel = cmds.getPanel(withFocus=True) or ""
if not panel or cmds.getPanel(typeOf=panel) != "modelPanel":
    panel = next(
        (
            candidate
            for candidate in (cmds.getPanel(visiblePanels=True) or [])
            if cmds.getPanel(typeOf=candidate) == "modelPanel"
        ),
        "",
    )
isolate_before = bool(cmds.isolateSelect(panel, query=True, state=True)) if panel else False
isolate_result = actionrail.run_action("maya.view.toggle_isolate_selected")
isolate_after = bool(cmds.isolateSelect(panel, query=True, state=True)) if panel else False
actionrail.run_action("maya.view.toggle_isolate_selected")
cmds.select(cube, replace=True)
frame_result = actionrail.run_action("maya.view.frame_selection")
selection_before_clear = cmds.ls(selection=True) or []
clear_result = actionrail.run_action("maya.selection.clear")
selection_after_clear = cmds.ls(selection=True) or []
poly_cube_result = actionrail.run_action("maya.modeling.poly_cube")
created_cube_selection = cmds.ls(selection=True, type="transform") or []
poly_sphere_result = actionrail.run_action("maya.modeling.poly_sphere")
created_sphere_selection = cmds.ls(selection=True, type="transform") or []

missing_modeling_entries = [
    action_id for action_id in modeling_shelf_commands if action_id not in modeling_shelf_entries
]
missing_mel_commands = [
    command for command in modeling_shelf_commands.values() if not mel.eval(f'exists "{command}"')
]
icon_issues = {
    action_id: actionrail_icons.icon_status(entry.icon, cmds_module=cmds).issue.as_dict()
    for action_id, entry in modeling_shelf_entries.items()
    if not actionrail_icons.icon_status(entry.icon, cmds_module=cmds).ok
}

if after_first == before:
    raise AssertionError(
        "Toggle Grid action did not flip Maya grid visibility: "
        f"before={before} after={after_first}"
    )
if after_second != before:
    raise AssertionError(
        "Toggle Grid action did not restore Maya grid visibility: "
        f"before={before} after_second={after_second}"
    )
if context_after_select != "selectSuperContext":
    raise AssertionError(f"Select action did not enter select tool: {context_after_select}")
if center_pivot_result != "centerPivot":
    raise AssertionError(f"Center Pivot returned unexpected result: {center_pivot_result}")
if (
    abs(translate_x_after_freeze) > 0.001
    or abs(rotate_y_after_freeze) > 0.001
    or abs(scale_z_after_freeze - 1.0) > 0.001
):
    raise AssertionError(
        "Freeze Transforms did not reset transform channels: "
        f"tx={translate_x_after_freeze} ry={rotate_y_after_freeze} sz={scale_z_after_freeze}"
    )
if not any("polyBevel" in item for item in history_before_delete):
    raise AssertionError(
        "Delete History setup did not create bevel history: "
        f"{history_before_delete}"
    )
if any("polyBevel" in item for item in history_after_delete):
    raise AssertionError(f"Delete History left bevel history behind: {history_after_delete}")
if panel and isolate_after == isolate_before:
    raise AssertionError(
        "Toggle Isolate Selected did not flip isolate state: "
        f"panel={panel} before={isolate_before} after={isolate_after}"
    )
if cube not in selection_before_clear:
    raise AssertionError(f"Frame Selection setup lost cube selection: {selection_before_clear}")
if selection_after_clear:
    raise AssertionError(f"Clear Selection did not clear Maya selection: {selection_after_clear}")
if len(choices) < 33:
    raise AssertionError(
        "Action Book catalog did not include the 20-action shelf pack: "
        f"{len(choices)}"
    )
if missing_modeling_entries:
    raise AssertionError(f"Missing modeling shelf entries: {missing_modeling_entries}")
if missing_mel_commands:
    raise AssertionError(f"Missing Maya MEL shelf commands: {missing_mel_commands}")
if icon_issues:
    raise AssertionError(f"Missing Maya shelf icon resources: {icon_issues}")
if poly_cube_result != "CreatePolygonCube" or not any(
    name.startswith("pCube") for name in created_cube_selection
):
    raise AssertionError(
        "Polygon Cube shelf action did not create/select a cube: "
        f"result={poly_cube_result} selection={created_cube_selection}"
    )
if poly_sphere_result != "CreatePolygonSphere" or not any(
    name.startswith("pSphere") for name in created_sphere_selection
):
    raise AssertionError(
        "Polygon Sphere shelf action did not create/select a sphere: "
        f"result={poly_sphere_result} selection={created_sphere_selection}"
    )

catalog_payload = [
    {
        "id": choice.id,
        "label": choice.label,
        "tooltip": choice.tooltip,
        "category": choice.category,
        "icon": choice.icon,
        "kind": choice.kind,
        "source": choice.source,
        "keywords": list(choice.keywords),
    }
    for choice in choices
]
catalog_path.write_text(
    json.dumps(catalog_payload, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)

result = {
    "action_count": len(choices),
    "catalog_path": str(catalog_path),
    "catalog_saved": catalog_path.is_file(),
    "center_pivot_entry_category": center_pivot_entry.category,
    "center_pivot_result": center_pivot_result,
    "clear_entry_category": clear_entry.category,
    "clear_result": clear_result,
    "context_after_select": context_after_select,
    "freeze_entry_category": freeze_entry.category,
    "freeze_result": freeze_result,
    "frame_entry_category": frame_entry.category,
    "frame_result": frame_result,
    "grid_after_first": after_first,
    "grid_after_second": after_second,
    "grid_before": before,
    "grid_entry_category": grid_entry.category,
    "grid_entry_icon": grid_entry.icon,
    "grid_entry_keywords": grid_entry.keywords,
    "grid_entry_label": grid_entry.label,
    "grid_result_first": first_result,
    "grid_result_second": second_result,
    "has_center_pivot_choice": any(
        choice.id == "maya.modeling.center_pivot" for choice in choices
    ),
    "has_clear_selection_choice": any(
        choice.id == "maya.selection.clear" for choice in choices
    ),
    "has_delete_history_choice": any(
        choice.id == "maya.modeling.delete_history" for choice in choices
    ),
    "has_freeze_transforms_choice": any(
        choice.id == "maya.modeling.freeze_transforms" for choice in choices
    ),
    "has_frame_selection_choice": any(
        choice.id == "maya.view.frame_selection" for choice in choices
    ),
    "has_select_choice": any(choice.id == "maya.tool.select" for choice in choices),
    "has_toggle_isolate_selected_choice": any(
        choice.id == "maya.view.toggle_isolate_selected" for choice in choices
    ),
    "has_toggle_grid_choice": any(
        choice.id == "maya.display.toggle_grid" for choice in choices
    ),
    "history_after_delete": history_after_delete,
    "history_before_delete": history_before_delete,
    "history_entry_category": history_entry.category,
    "isolate_after": isolate_after,
    "isolate_before": isolate_before,
    "isolate_entry_category": isolate_entry.category,
    "isolate_result": isolate_result,
    "modeling_shelf_action_count": len(modeling_shelf_entries),
    "modeling_shelf_icons": {
        action_id: entry.icon for action_id, entry in modeling_shelf_entries.items()
    },
    "poly_cube_result": poly_cube_result,
    "poly_sphere_result": poly_sphere_result,
    "select_entry_category": select_entry.category,
    "select_entry_icon": select_entry.icon,
    "select_result": select_result,
    "selection_after_clear": selection_after_clear,
}

actionrail.hide_all()

print(json.dumps(result, sort_keys=True))
