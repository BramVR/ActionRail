from __future__ import annotations

import json
import sys

__args__ = globals().get("__args__", {})

repo_scripts = __args__.get("repo_scripts")
if repo_scripts and repo_scripts not in sys.path:
    sys.path.insert(0, repo_scripts)

from maya import cmds  # noqa: E402

import actionrail  # noqa: E402

cmds.file(new=True, force=True)

entry = actionrail.action_book_entry_by_id("maya.display.toggle_grid")
choices = actionrail.action_book_entries()

before = bool(cmds.grid(query=True, toggle=True))
first_result = actionrail.run_action("maya.display.toggle_grid")
after_first = bool(cmds.grid(query=True, toggle=True))
second_result = actionrail.run_action("maya.display.toggle_grid")
after_second = bool(cmds.grid(query=True, toggle=True))

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

result = {
    "action_count": len(choices),
    "grid_after_first": after_first,
    "grid_after_second": after_second,
    "grid_before": before,
    "grid_entry_category": entry.category,
    "grid_entry_icon": entry.icon,
    "grid_entry_keywords": entry.keywords,
    "grid_entry_label": entry.label,
    "grid_result_first": first_result,
    "grid_result_second": second_result,
    "has_toggle_grid_choice": any(
        choice.id == "maya.display.toggle_grid" for choice in choices
    ),
}

actionrail.hide_all()

print(json.dumps(result, sort_keys=True))
