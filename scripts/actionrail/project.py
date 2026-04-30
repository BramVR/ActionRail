"""Machine-readable project map for agents and maintenance tools."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .actions import create_default_registry
from .icons import validate_icon_manifest
from .spec import builtin_preset_ids

_PACKAGE_ROOT = Path(__file__).resolve().parents[2]
_DOCS_DIR = _PACKAGE_ROOT / "docs"

MODULE_MAP: tuple[dict[str, object], ...] = (
    {
        "path": "scripts/actionrail/__init__.py",
        "owns": "public package API",
        "read_when": "Calling ActionRail from Maya or checking supported top-level helpers.",
    },
    {
        "path": "scripts/actionrail/runtime.py",
        "owns": "overlay lifecycle registry and action/slot execution",
        "tests": ("tests/test_package.py", "tests/maya_smoke/actionrail_phase0_smoke.py"),
    },
    {
        "path": "scripts/actionrail/spec.py",
        "owns": "JSON preset loading, schema validation, built-in preset discovery",
        "tests": ("tests/test_spec.py",),
    },
    {
        "path": "scripts/actionrail/widgets.py",
        "owns": "Qt rail/widget construction, slot render state, diagnostic badges",
        "tests": (
            "tests/test_widgets.py",
            "tests/maya_smoke/actionrail_diagnostic_badges_smoke.py",
        ),
    },
    {
        "path": "scripts/actionrail/overlay.py",
        "owns": "Maya model-panel anchoring, floating rail host, overlay cleanup",
        "tests": ("tests/test_overlay.py", "tests/maya_smoke/actionrail_overlay_cleanup_smoke.py"),
    },
    {
        "path": "scripts/actionrail/actions.py",
        "owns": "reusable Maya command registry",
        "tests": ("tests/test_actions.py",),
    },
    {
        "path": "scripts/actionrail/hotkeys.py",
        "owns": "Maya runtime-command publishing, nameCommands, hotkey labels",
        "tests": ("tests/test_hotkeys.py", "tests/maya_smoke/actionrail_hotkey_bridge_smoke.py"),
    },
    {
        "path": "scripts/actionrail/predicates.py",
        "owns": "safe predicate evaluator and availability target analysis",
        "tests": ("tests/test_predicates.py", "tests/maya_smoke/actionrail_predicates_smoke.py"),
    },
    {
        "path": "scripts/actionrail/icons.py",
        "owns": "icon manifest validation, SVG safety checks, local SVG import",
        "tests": ("tests/test_icons.py",),
    },
    {
        "path": "scripts/actionrail/diagnostics.py",
        "owns": "safe-mode reports, latest report state, safe overlay startup",
        "tests": ("tests/test_diagnostics.py", "tests/maya_smoke/actionrail_diagnostics_smoke.py"),
    },
    {
        "path": "scripts/actionrail/diagnostics_ui.py",
        "owns": "copyable themed Qt diagnostics report window",
        "tests": ("tests/maya_smoke/actionrail_diagnostics_smoke.py",),
    },
    {
        "path": "scripts/actionrail/maya_ui.py",
        "owns": "Maya menu and shelf toggle entry points",
        "tests": ("tests/test_maya_ui.py", "tests/maya_smoke/actionrail_maya_ui_smoke.py"),
    },
)

DOC_PRIORITY: tuple[str, ...] = (
    "docs/00_start_here.md",
    "docs/04_status.md",
    "docs/01_architecture.md",
    "docs/02_implementation_plan.md",
    "docs/03_maya_sessiond_workflow.md",
    "docs/05_tech_stack.md",
    "docs/06_wow_style_customization.md",
    "docs/07_missing_features_research.md",
    "docs/history/verification_log.md",
)


def about() -> dict[str, object]:
    """Return a JSON-safe map of the project for agents and local tooling."""

    package = _loaded_package()
    icon_issues = validate_icon_manifest()
    return {
        "product": "ActionRail",
        "package": "actionrail",
        "version": getattr(package, "__version__", "0.0.0"),
        "status": {
            "phase": "Phase 1 declarative MVP",
            "next_slice": "PNG fallback generation for imported SVG icons",
            "blockers_doc": "docs/04_status.md#blockers",
        },
        "public_api": tuple(
            name
            for name in getattr(package, "__all__", ())
            if isinstance(name, str) and not name.startswith("__")
        ),
        "builtins": {
            "preset_ids": builtin_preset_ids(),
            "action_ids": create_default_registry().ids(),
        },
        "icons": {
            "manifest": "icons/manifest.json",
            "issue_count": len(icon_issues),
            "issues": tuple(issue.as_dict() for issue in icon_issues[:10]),
        },
        "docs": _doc_entries(),
        "modules": MODULE_MAP,
        "verification": {
            "local": (
                ".\\.venv\\Scripts\\python.exe -m pytest",
                ".\\.venv\\Scripts\\python.exe -m ruff check .",
            ),
            "maya_smoke": ".\\scripts\\maya-smoke.ps1 -Script all",
            "workflow_doc": "docs/03_maya_sessiond_workflow.md",
        },
    }


def _loaded_package() -> object:
    import actionrail

    return actionrail


def _doc_entries() -> tuple[dict[str, object], ...]:
    entries = []
    for path_text in DOC_PRIORITY:
        path = _PACKAGE_ROOT / path_text
        if not path.is_file():
            continue
        front_matter = _front_matter(path)
        entries.append(
            {
                "path": path_text,
                "summary": front_matter.get("summary", ""),
                "read_when": tuple(front_matter.get("read_when", ())),
            }
        )
    return tuple(entries)


def _front_matter(path: Path) -> dict[str, Any]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].lstrip("\ufeff") != "---":
        return {}

    summary = ""
    read_when: list[str] = []
    active_key = ""
    for line in lines[1:]:
        if line == "---":
            break
        if line.startswith("summary:"):
            summary = line.split(":", 1)[1].strip()
            active_key = "summary"
            continue
        if line.startswith("read_when:"):
            active_key = "read_when"
            continue
        if active_key == "read_when" and line.strip().startswith("- "):
            read_when.append(line.strip()[2:].strip())

    result: dict[str, Any] = {}
    if summary:
        result["summary"] = summary
    if read_when:
        result["read_when"] = tuple(read_when)
    return result


__all__ = ["DOC_PRIORITY", "MODULE_MAP", "about"]
