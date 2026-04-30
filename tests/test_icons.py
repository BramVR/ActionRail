from __future__ import annotations

import json
from pathlib import Path

import pytest

import actionrail.icons as icons
from actionrail.icons import (
    icon_status,
    import_svg_icon,
    resolve_icon_path,
    validate_icon_manifest,
)

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


def test_import_svg_icon_copies_asset_and_updates_manifest(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    package_root = tmp_path
    icon_dir = package_root / "icons"
    manifest_path = icon_dir / "manifest.json"
    source_path = tmp_path / "source.svg"
    icon_dir.mkdir()
    manifest_path.write_text('{"icons": []}\n', encoding="utf-8")
    source_path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        '<path d="M4 12h16"/></svg>',
        encoding="utf-8",
    )
    monkeypatch.setattr(icons, "_PACKAGE_ROOT", package_root)
    monkeypatch.setattr(icons, "_ICON_DIR", icon_dir)
    monkeypatch.setattr(icons, "_MANIFEST_PATH", manifest_path)

    result = import_svg_icon(
        source_path,
        "test.arrow",
        source="Lucide",
        license_name="ISC",
        url="https://example.test/arrow",
        imported_at="2026-04-30",
    )

    assert result.path == icon_dir / "test" / "arrow.svg"
    assert result.path.read_text(encoding="utf-8") == source_path.read_text(
        encoding="utf-8"
    )
    assert result.replaced_existing is False
    assert result.manifest_entry == {
        "id": "test.arrow",
        "source": "Lucide",
        "license": "ISC",
        "url": "https://example.test/arrow",
        "imported_at": "2026-04-30",
        "path": "icons/test/arrow.svg",
    }
    assert icon_status("test.arrow").path == result.path
    assert validate_icon_manifest() == ()


def test_import_svg_icon_rejects_unsafe_svg_without_manifest_change(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    package_root = tmp_path
    icon_dir = package_root / "icons"
    manifest_path = icon_dir / "manifest.json"
    source_path = tmp_path / "unsafe.svg"
    icon_dir.mkdir()
    manifest_path.write_text('{"icons": []}\n', encoding="utf-8")
    source_path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        "<script>alert(1)</script></svg>",
        encoding="utf-8",
    )
    monkeypatch.setattr(icons, "_PACKAGE_ROOT", package_root)
    monkeypatch.setattr(icons, "_ICON_DIR", icon_dir)
    monkeypatch.setattr(icons, "_MANIFEST_PATH", manifest_path)

    with pytest.raises(ValueError, match="unsafe"):
        import_svg_icon(
            source_path,
            "test.unsafe",
            source="Local",
            license_name="Apache-2.0",
            url="local://unsafe.svg",
            imported_at="2026-04-30",
        )

    assert json.loads(manifest_path.read_text(encoding="utf-8")) == {"icons": []}
    assert not (icon_dir / "test" / "unsafe.svg").exists()


def test_import_svg_icon_refuses_duplicate_without_overwrite(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    package_root = tmp_path
    icon_dir = package_root / "icons"
    manifest_path = icon_dir / "manifest.json"
    source_path = tmp_path / "source.svg"
    icon_dir.mkdir()
    manifest_path.write_text(
        json.dumps(
            {
                "icons": [
                    {
                        "id": "test.arrow",
                        "source": "Existing",
                        "license": "MIT",
                        "url": "local://existing.svg",
                        "imported_at": "2026-04-29",
                        "path": "icons/test/arrow.svg",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    source_path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"></svg>',
        encoding="utf-8",
    )
    monkeypatch.setattr(icons, "_PACKAGE_ROOT", package_root)
    monkeypatch.setattr(icons, "_ICON_DIR", icon_dir)
    monkeypatch.setattr(icons, "_MANIFEST_PATH", manifest_path)

    with pytest.raises(ValueError, match="already exists"):
        import_svg_icon(
            source_path,
            "test.arrow",
            source="Local",
            license_name="Apache-2.0",
            url="local://source.svg",
        )


def test_import_svg_icon_overwrites_existing_entry(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    package_root = tmp_path
    icon_dir = package_root / "icons"
    manifest_path = icon_dir / "manifest.json"
    source_path = tmp_path / "source.svg"
    target_path = icon_dir / "custom" / "arrow.svg"
    target_path.parent.mkdir(parents=True)
    target_path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 8 8"></svg>',
        encoding="utf-8",
    )
    manifest_path.write_text(
        json.dumps(
            {
                "icons": [
                    {
                        "id": "test.arrow",
                        "source": "Existing",
                        "license": "MIT",
                        "url": "local://existing.svg",
                        "imported_at": "2026-04-29",
                        "path": "icons/custom/arrow.svg",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    source_path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        '<path d="M12 4v16"/></svg>',
        encoding="utf-8",
    )
    monkeypatch.setattr(icons, "_PACKAGE_ROOT", package_root)
    monkeypatch.setattr(icons, "_ICON_DIR", icon_dir)
    monkeypatch.setattr(icons, "_MANIFEST_PATH", manifest_path)

    result = import_svg_icon(
        source_path,
        "test.arrow",
        source="Local",
        license_name="Apache-2.0",
        url="local://source.svg",
        imported_at="2026-04-30",
        overwrite=True,
    )

    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert result.replaced_existing is True
    assert payload["icons"] == [result.manifest_entry]
    assert target_path.read_text(encoding="utf-8") == source_path.read_text(
        encoding="utf-8"
    )


def test_import_svg_icon_rejects_target_outside_icon_dir(
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "source.svg"
    source_path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"></svg>',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="inside the ActionRail icons directory"):
        import_svg_icon(
            source_path,
            "test.escape",
            source="Local",
            license_name="Apache-2.0",
            url="local://source.svg",
            target_path="../escape.svg",
        )
