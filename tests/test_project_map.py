from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import actionrail
import actionrail.project as project_map
from actionrail.__main__ import main
from actionrail.project import about


def test_about_returns_json_safe_agent_map() -> None:
    project = about()

    json.dumps(project)
    assert project["product"] == "ActionRail"
    assert "about" in project["public_api"]
    assert "transform_stack" in project["builtins"]["preset_ids"]
    assert "maya.tool.rotate" in project["builtins"]["action_ids"]
    assert "directory" in project["user_presets"]
    assert {"id": "maya", "icon_count": 36} in project["icons"]["providers"]
    assert any(entry["path"] == "docs/00_start_here.md" for entry in project["docs"])
    assert any(module["path"] == "scripts/actionrail/icons.py" for module in project["modules"])
    assert any(module["path"] == "scripts/actionrail/authoring.py" for module in project["modules"])


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


def test_module_cli_prints_human_project_map(capsys) -> None:
    assert main([]) == 0

    output = capsys.readouterr().out
    assert "ActionRail" in output
    assert "Status: Phase 2 step 2.1 complete" in output
    assert "Use --json" in output


def test_module_cli_prints_json_project_map_in_process(capsys) -> None:
    assert main(["--json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["package"] == "actionrail"


def test_doc_entries_skip_missing_docs_and_handle_plain_markdown(tmp_path, monkeypatch) -> None:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    plain_doc = docs_dir / "plain.md"
    front_matter_doc = docs_dir / "front.md"
    plain_doc.write_text("# Plain\n", encoding="utf-8")
    front_matter_doc.write_text(
        "---\nsummary: Front matter\nread_when:\n  - Testing docs\n---\n# Front\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(project_map, "_PACKAGE_ROOT", tmp_path)
    monkeypatch.setattr(
        project_map,
        "DOC_PRIORITY",
        ("docs/missing.md", "docs/plain.md", "docs/front.md"),
    )

    entries = project_map._doc_entries()

    assert entries == (
        {"path": "docs/plain.md", "summary": "", "read_when": ()},
        {"path": "docs/front.md", "summary": "Front matter", "read_when": ("Testing docs",)},
    )
