from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

import actionrail.icons as icons
from actionrail.icons import (
    generate_png_fallbacks,
    icon_status,
    import_svg_icon,
    resolve_icon_path,
    validate_icon_manifest,
    validate_svg_icon_import,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
PNG_BYTES = b"\x89PNG\r\n\x1a\n"
OLD_PNG_BYTES = b"\x89PNG\r\n\x1a\nold"


def fake_png_renderer(_svg_path: Path, png_path: Path, _size_px: int) -> None:
    png_path.write_bytes(PNG_BYTES)


def failing_png_renderer(_svg_path: Path, png_path: Path, _size_px: int) -> None:
    png_path.write_bytes(PNG_BYTES)
    raise RuntimeError("renderer failed")


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
    monkeypatch.setattr(icons, "_fallback_issues", lambda *_args, **_kwargs: ())

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
        generate_fallbacks=False,
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
    assert validate_icon_manifest(require_fallbacks=False) == ()


def test_import_svg_icon_generates_png_fallbacks_and_updates_manifest(
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
        png_renderer=fake_png_renderer,
    )

    assert result.fallback_paths == (
        icon_dir / "test" / "arrow@1x.png",
        icon_dir / "test" / "arrow@2x.png",
        icon_dir / "test" / "arrow@3x.png",
    )
    assert all(path.read_bytes() == PNG_BYTES for path in result.fallback_paths)
    assert result.manifest_entry["fallbacks"] == {
        "1x": "icons/test/arrow@1x.png",
        "2x": "icons/test/arrow@2x.png",
        "3x": "icons/test/arrow@3x.png",
    }
    assert isinstance(result.manifest_entry["fallback_source_sha256"], str)
    assert result.manifest_entry["fallback_base_size"] == 24
    assert validate_icon_manifest() == ()


def test_validate_svg_icon_import_reports_multiple_preflight_issues(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    package_root = tmp_path
    icon_dir = package_root / "icons"
    manifest_path = icon_dir / "manifest.json"
    source_path = tmp_path / "source.txt"
    target_path = icon_dir / "custom" / "arrow.svg"
    icon_dir.mkdir()
    target_path.parent.mkdir(parents=True)
    target_path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 8 8"></svg>',
        encoding="utf-8",
    )
    manifest_path.write_text('{"icons": []}\n', encoding="utf-8")
    source_path.write_text("not svg", encoding="utf-8")
    monkeypatch.setattr(icons, "_PACKAGE_ROOT", package_root)
    monkeypatch.setattr(icons, "_ICON_DIR", icon_dir)
    monkeypatch.setattr(icons, "_MANIFEST_PATH", manifest_path)

    issues = validate_svg_icon_import(
        source_path,
        "bad id",
        source="",
        license_name="Apache-2.0",
        url="local://source.txt",
        target_path="icons/custom/arrow.svg",
    )

    assert [issue.code for issue in issues] == [
        "invalid_icon_import_source",
        "invalid_icon_import_metadata",
        "icon_target_exists",
    ]
    assert issues[1].field == "icon_id"
    assert issues[2].path == "icons/custom/arrow.svg"


def test_import_svg_icon_rolls_back_new_asset_when_fallback_generation_fails(
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

    with pytest.raises(RuntimeError, match="renderer failed"):
        import_svg_icon(
            source_path,
            "test.arrow",
            source="Lucide",
            license_name="ISC",
            url="https://example.test/arrow",
            imported_at="2026-04-30",
            png_renderer=failing_png_renderer,
        )

    assert json.loads(manifest_path.read_text(encoding="utf-8")) == {"icons": []}
    assert not (icon_dir / "test" / "arrow.svg").exists()
    assert not (icon_dir / "test" / "arrow@1x.png").exists()
    assert not (icon_dir / "test" / "arrow@2x.png").exists()
    assert not (icon_dir / "test" / "arrow@3x.png").exists()


def test_generate_png_fallbacks_updates_existing_manifest_entry(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    package_root = tmp_path
    icon_dir = package_root / "icons"
    manifest_path = icon_dir / "manifest.json"
    svg_path = icon_dir / "test" / "arrow.svg"
    svg_path.parent.mkdir(parents=True)
    svg_path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"></svg>',
        encoding="utf-8",
    )
    manifest_path.write_text(
        json.dumps(
            {
                "icons": [
                    {
                        "id": "test.arrow",
                        "source": "Local",
                        "license": "Apache-2.0",
                        "url": "local://arrow.svg",
                        "imported_at": "2026-04-30",
                        "path": "icons/test/arrow.svg",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(icons, "_PACKAGE_ROOT", package_root)
    monkeypatch.setattr(icons, "_ICON_DIR", icon_dir)
    monkeypatch.setattr(icons, "_MANIFEST_PATH", manifest_path)

    result = generate_png_fallbacks("test.arrow", png_renderer=fake_png_renderer)

    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert result.fallback_paths == (
        icon_dir / "test" / "arrow@1x.png",
        icon_dir / "test" / "arrow@2x.png",
        icon_dir / "test" / "arrow@3x.png",
    )
    assert payload["icons"][0] == result.manifest_entry
    assert validate_icon_manifest() == ()


def test_render_png_uses_mayapy_renderer(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    svg_path = tmp_path / "source.svg"
    png_path = tmp_path / "source.png"
    svg_path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"></svg>',
        encoding="utf-8",
    )
    monkeypatch.setattr(icons, "_render_png_with_mayapy", fake_png_renderer)

    icons._render_png(svg_path, png_path, 24, None)

    assert png_path.read_bytes() == PNG_BYTES


def test_render_png_with_mayapy_invokes_discovered_executable(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    svg_path = tmp_path / "source.svg"
    png_path = tmp_path / "source.png"
    commands: list[list[str]] = []
    monkeypatch.setattr(icons, "_mayapy_candidates", lambda: ("C:/Maya/bin/mayapy.exe",))

    def fake_run(
        command: list[str],
        *,
        capture_output: bool,
        text: bool,
        check: bool,
    ) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(icons.subprocess, "run", fake_run)

    icons._render_png_with_mayapy(svg_path, png_path, 48)

    assert commands
    command = commands[0]
    assert command[0] == "C:/Maya/bin/mayapy.exe"
    assert command[1] == "-c"
    assert command[-3:] == [str(svg_path), str(png_path), "48"]


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


def test_import_svg_icon_rejects_external_style_block_without_manifest_change(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    package_root = tmp_path
    icon_dir = package_root / "icons"
    manifest_path = icon_dir / "manifest.json"
    source_path = tmp_path / "unsafe-style.svg"
    icon_dir.mkdir()
    manifest_path.write_text('{"icons": []}\n', encoding="utf-8")
    source_path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        "<style>@import url(https://example.test/icon.css);</style>"
        '<path d="M4 12h16"/></svg>',
        encoding="utf-8",
    )
    monkeypatch.setattr(icons, "_PACKAGE_ROOT", package_root)
    monkeypatch.setattr(icons, "_ICON_DIR", icon_dir)
    monkeypatch.setattr(icons, "_MANIFEST_PATH", manifest_path)

    with pytest.raises(ValueError, match="external stylesheet reference"):
        import_svg_icon(
            source_path,
            "test.unsafe_style",
            source="Local",
            license_name="Apache-2.0",
            url="local://unsafe-style.svg",
            imported_at="2026-04-30",
        )

    assert json.loads(manifest_path.read_text(encoding="utf-8")) == {"icons": []}
    assert not (icon_dir / "test" / "unsafe-style.svg").exists()


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
        generate_fallbacks=False,
    )

    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert result.replaced_existing is True
    assert payload["icons"] == [result.manifest_entry]
    assert target_path.read_text(encoding="utf-8") == source_path.read_text(
        encoding="utf-8"
    )


def test_import_svg_icon_restores_overwritten_asset_when_fallback_generation_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    package_root = tmp_path
    icon_dir = package_root / "icons"
    manifest_path = icon_dir / "manifest.json"
    source_path = tmp_path / "source.svg"
    target_path = icon_dir / "custom" / "arrow.svg"
    fallback_path = icon_dir / "custom" / "arrow@1x.png"
    target_path.parent.mkdir(parents=True)
    original_svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 8 8"></svg>'
    target_path.write_text(original_svg, encoding="utf-8")
    fallback_path.write_bytes(OLD_PNG_BYTES)
    manifest_payload = {
        "icons": [
            {
                "id": "test.arrow",
                "source": "Existing",
                "license": "MIT",
                "url": "local://existing.svg",
                "imported_at": "2026-04-29",
                "path": "icons/custom/arrow.svg",
                "fallbacks": {
                    "1x": "icons/custom/arrow@1x.png",
                    "2x": "icons/custom/arrow@2x.png",
                    "3x": "icons/custom/arrow@3x.png",
                },
                "fallback_source_sha256": "old-hash",
                "fallback_base_size": 24,
            }
        ]
    }
    manifest_path.write_text(json.dumps(manifest_payload), encoding="utf-8")
    source_path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        '<path d="M12 4v16"/></svg>',
        encoding="utf-8",
    )
    monkeypatch.setattr(icons, "_PACKAGE_ROOT", package_root)
    monkeypatch.setattr(icons, "_ICON_DIR", icon_dir)
    monkeypatch.setattr(icons, "_MANIFEST_PATH", manifest_path)

    with pytest.raises(RuntimeError, match="renderer failed"):
        import_svg_icon(
            source_path,
            "test.arrow",
            source="Local",
            license_name="Apache-2.0",
            url="local://source.svg",
            imported_at="2026-04-30",
            overwrite=True,
            png_renderer=failing_png_renderer,
        )

    assert json.loads(manifest_path.read_text(encoding="utf-8")) == manifest_payload
    assert target_path.read_text(encoding="utf-8") == original_svg
    assert fallback_path.read_bytes() == OLD_PNG_BYTES
    assert not (icon_dir / "custom" / "arrow@2x.png").exists()
    assert not (icon_dir / "custom" / "arrow@3x.png").exists()


def test_import_svg_icon_rejects_equivalent_manifest_path_conflict(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    package_root = tmp_path
    icon_dir = package_root / "icons"
    manifest_path = icon_dir / "manifest.json"
    source_path = tmp_path / "source.svg"
    target_path = icon_dir / "custom" / "arrow.svg"
    target_path.parent.mkdir(parents=True)
    original_svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 8 8"></svg>'
    target_path.write_text(original_svg, encoding="utf-8")
    manifest_payload = {
        "icons": [
            {
                "id": "other.arrow",
                "source": "Existing",
                "license": "MIT",
                "url": "local://existing.svg",
                "imported_at": "2026-04-29",
                "path": "custom/arrow.svg",
            }
        ]
    }
    manifest_path.write_text(json.dumps(manifest_payload), encoding="utf-8")
    source_path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        '<path d="M12 4v16"/></svg>',
        encoding="utf-8",
    )
    monkeypatch.setattr(icons, "_PACKAGE_ROOT", package_root)
    monkeypatch.setattr(icons, "_ICON_DIR", icon_dir)
    monkeypatch.setattr(icons, "_MANIFEST_PATH", manifest_path)

    with pytest.raises(ValueError, match="already used by icon 'other.arrow'"):
        import_svg_icon(
            source_path,
            "test.arrow",
            source="Local",
            license_name="Apache-2.0",
            url="local://source.svg",
            target_path="icons/custom/arrow.svg",
            overwrite=True,
        )

    assert json.loads(manifest_path.read_text(encoding="utf-8")) == manifest_payload
    assert target_path.read_text(encoding="utf-8") == original_svg


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


def test_validate_icon_manifest_reports_missing_fallback_metadata(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    svg_path = tmp_path / "source.svg"
    svg_path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"></svg>',
        encoding="utf-8",
    )
    entry = {
        "id": "test.source",
        "source": "Local",
        "license": "Apache-2.0",
        "url": "local://source.svg",
        "imported_at": "2026-04-30",
        "path": "source.svg",
    }
    monkeypatch.setattr(icons, "_manifest_icons", lambda: (entry,))
    monkeypatch.setattr(icons, "_resolve_manifest_path", lambda _path: svg_path)

    issues = validate_icon_manifest()

    assert [(issue.code, issue.icon_id) for issue in issues] == [
        ("missing_icon_fallbacks", "test.source")
    ]


def test_validate_icon_manifest_reports_missing_and_stale_fallbacks(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    svg_path = tmp_path / "source.svg"
    fallback_1x = tmp_path / "source@1x.png"
    fallback_2x = tmp_path / "source@2x.png"
    svg_path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"></svg>',
        encoding="utf-8",
    )
    fallback_1x.write_bytes(PNG_BYTES)
    fallback_2x.write_bytes(PNG_BYTES)
    entry = {
        "id": "test.source",
        "source": "Local",
        "license": "Apache-2.0",
        "url": "local://source.svg",
        "imported_at": "2026-04-30",
        "path": "source.svg",
        "fallbacks": {
            "1x": "source@1x.png",
            "2x": "source@2x.png",
            "3x": "source@3x.png",
        },
        "fallback_source_sha256": "outdated",
        "fallback_base_size": 24,
    }
    paths = {
        "source.svg": svg_path,
        "source@1x.png": fallback_1x,
        "source@2x.png": fallback_2x,
        "source@3x.png": tmp_path / "source@3x.png",
    }
    monkeypatch.setattr(icons, "_manifest_icons", lambda: (entry,))
    monkeypatch.setattr(icons, "_resolve_manifest_path", lambda path: paths[path])

    issues = validate_icon_manifest()

    assert [(issue.code, issue.path) for issue in issues] == [
        ("missing_icon_fallback_file", "source@3x.png"),
        ("stale_icon_fallback", "source.svg"),
    ]
