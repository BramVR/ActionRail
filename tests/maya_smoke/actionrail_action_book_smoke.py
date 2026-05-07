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

from maya import cmds  # noqa: E402

import actionrail  # noqa: E402

cmds.file(new=True, force=True)

grid_entry = actionrail.action_book_entry_by_id("maya.display.toggle_grid")
select_entry = actionrail.action_book_entry_by_id("maya.tool.select")
clear_entry = actionrail.action_book_entry_by_id("maya.selection.clear")
frame_entry = actionrail.action_book_entry_by_id("maya.view.frame_selection")
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
cmds.select(cube, replace=True)
frame_result = actionrail.run_action("maya.view.frame_selection")
selection_before_clear = cmds.ls(selection=True) or []
clear_result = actionrail.run_action("maya.selection.clear")
selection_after_clear = cmds.ls(selection=True) or []

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
if cube not in selection_before_clear:
    raise AssertionError(f"Frame Selection setup lost cube selection: {selection_before_clear}")
if selection_after_clear:
    raise AssertionError(f"Clear Selection did not clear Maya selection: {selection_after_clear}")

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
    "clear_entry_category": clear_entry.category,
    "clear_result": clear_result,
    "context_after_select": context_after_select,
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
    "has_clear_selection_choice": any(
        choice.id == "maya.selection.clear" for choice in choices
    ),
    "has_frame_selection_choice": any(
        choice.id == "maya.view.frame_selection" for choice in choices
    ),
    "has_select_choice": any(choice.id == "maya.tool.select" for choice in choices),
    "has_toggle_grid_choice": any(
        choice.id == "maya.display.toggle_grid" for choice in choices
    ),
    "select_entry_category": select_entry.category,
    "select_entry_icon": select_entry.icon,
    "select_result": select_result,
    "selection_after_clear": selection_after_clear,
}

actionrail.hide_all()

print(json.dumps(result, sort_keys=True))
