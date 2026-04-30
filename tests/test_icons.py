from __future__ import annotations

import json
from pathlib import Path

import pytest

import actionrail.icons as icons
from actionrail.icons import icon_status, resolve_icon_path, validate_icon_manifest

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_icon_manifest_has_expected_shape() -> None:
    manifest_path = REPO_ROOT / "icons" / "manifest.json"

    payload = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert set(payload) == {"icons"}
    assert isinstance(payload["icons"], list)


def test_icon_manifest_entries_include_required_metadata() -> None:
    manifest_path = REPO_ROOT / "icons" / "manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))

    for icon in payload["icons"]:
        assert isinstance(icon, dict)
        assert {"id", "source", "license", "url", "imported_at", "path"} <= set(icon)


def test_icon_manifest_assets_validate_cleanly() -> None:
    assert validate_icon_manifest() == ()


def test_icon_status_resolves_safe_manifest_icon() -> None:
    status = icon_status("actionrail.move")

    assert status.ok is True
    assert status.path == REPO_ROOT / "icons" / "actionrail" / "move.svg"
    assert resolve_icon_path("actionrail.move") == status.path


def test_icon_status_reports_unknown_icon() -> None:
    status = icon_status("missing.icon")

    assert status.ok is False
    assert status.path is None
    assert status.issue is not None
    assert status.issue.code == "missing_icon"


def test_validate_icon_manifest_reports_duplicate_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    entry = {
        "id": "duplicate.icon",
        "source": "ActionRail",
        "license": "Apache-2.0",
        "url": "local://duplicate",
        "imported_at": "2026-04-30",
        "path": "duplicate.svg",
    }
    monkeypatch.setattr(icons, "_manifest_icons", lambda: (entry, entry))
    monkeypatch.setattr(icons, "_asset_issue", lambda *_args: None)

    issues = validate_icon_manifest()

    assert [issue.code for issue in issues] == ["duplicate_icon"]


def test_validate_icon_manifest_reports_unsafe_svg(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    svg_path = tmp_path / "unsafe.svg"
    svg_path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        "<script>alert(1)</script></svg>",
        encoding="utf-8",
    )
    entry = {
        "id": "unsafe.icon",
        "source": "ActionRail",
        "license": "Apache-2.0",
        "url": "local://unsafe",
        "imported_at": "2026-04-30",
        "path": "unsafe.svg",
    }
    monkeypatch.setattr(icons, "_manifest_icons", lambda: (entry,))
    monkeypatch.setattr(icons, "_resolve_manifest_path", lambda _path: svg_path)

    issues = validate_icon_manifest()

    assert [(issue.code, issue.icon_id) for issue in issues] == [
        ("unsafe_icon_svg", "unsafe.icon")
    ]
