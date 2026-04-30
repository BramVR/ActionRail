from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import actionrail
from actionrail.project import about


def test_about_returns_json_safe_agent_map() -> None:
    project = about()

    json.dumps(project)
    assert project["product"] == "ActionRail"
    assert "about" in project["public_api"]
    assert "transform_stack" in project["builtins"]["preset_ids"]
    assert "maya.tool.rotate" in project["builtins"]["action_ids"]
    assert any(entry["path"] == "docs/00_start_here.md" for entry in project["docs"])
    assert any(module["path"] == "scripts/actionrail/icons.py" for module in project["modules"])


def test_package_exposes_about() -> None:
    assert callable(actionrail.about)
    assert actionrail.about()["package"] == "actionrail"


def test_module_cli_prints_json_project_map() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root / "scripts")
    result = subprocess.run(
        [sys.executable, "-m", "actionrail", "--json"],
        cwd=repo_root,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)
    assert payload["package"] == "actionrail"
    assert payload["verification"]["workflow_doc"] == "docs/03_maya_sessiond_workflow.md"
