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
    list_icon_descriptors,
    resolve_icon_name,
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
    assert status.provider == "manifest"
    assert status.path == REPO_ROOT / "icons" / "actionrail" / "move.svg"
    assert status.qt_name == ""
    assert resolve_icon_path("actionrail.move") == status.path


def test_icon_status_resolves_known_maya_resource_icon() -> None:
    status = icon_status("maya.move")

    assert status.ok is True
    assert status.provider == "maya"
    assert status.path is None
    assert status.qt_name == "move_M.png"
    assert resolve_icon_path("maya.move") is None
    assert resolve_icon_name("maya.move") == "move_M.png"


def test_icon_status_reports_missing_maya_resource_when_cmds_can_verify() -> None:
    class MissingResourceCmds:
        def resourceManager(self, *, nameFilter: str):  # noqa: N802
            assert nameFilter == "move_M.png"
            return []

    status = icon_status("maya.move", cmds_module=MissingResourceCmds())

    assert status.ok is False
    assert status.provider == "maya"
    assert status.issue is not None
    assert status.issue.code == "missing_maya_icon_resource"
    assert status.issue.path == "move_M.png"


def test_icon_status_verifies_existing_maya_resource_with_cmds() -> None:
    class ResourceCmds:
        def resourceManager(self, *, nameFilter: str):  # noqa: N802
            return [nameFilter]

    status = icon_status("maya.set_key", cmds_module=ResourceCmds())

    assert status.ok is True
    assert status.qt_name == "setKeyframe.png"


def test_icon_status_reports_unknown_icon() -> None:
    status = icon_status("missing.icon")

    assert status.ok is False
    assert status.path is None
    assert status.issue is not None
    assert status.issue.code == "missing_icon"


def test_icon_descriptors_include_manifest_and_maya_picker_metadata() -> None:
    descriptors = list_icon_descriptors()
    ids = {descriptor.id for descriptor in descriptors}

    assert {"actionrail.move", "maya.move", "maya.set_key"} <= ids
    maya_move = next(descriptor for descriptor in descriptors if descriptor.id == "maya.move")
    actionrail_move = next(
        descriptor for descriptor in descriptors if descriptor.id == "actionrail.move"
    )
    assert maya_move.provider == "maya"
    assert maya_move.category == "Transform"
    assert maya_move.qt_name == "move_M.png"
    assert "translate" in maya_move.keywords
    assert actionrail_move.provider == "manifest"
    assert actionrail_move.path == REPO_ROOT / "icons" / "actionrail" / "move.svg"
    assert [descriptor.id for descriptor in list_icon_descriptors(provider="maya")] == [
        "maya.set_key",
        "maya.move",
        "maya.rotate",
        "maya.scale",
    ]


def test_icon_descriptor_as_dict_is_compact() -> None:
    descriptor = icons.IconDescriptor(
        id="maya.move",
        provider="maya",
        label="Move",
        keywords=("move",),
        qt_name="move_M.png",
    )

    assert descriptor.as_dict() == {
        "id": "maya.move",
        "provider": "maya",
        "label": "Move",
        "keywords": ("move",),
        "qt_name": "move_M.png",
    }


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
    assert issues[1].hint
    assert issues[2].path == "icons/custom/arrow.svg"
    assert "overwrite=True" in issues[2].hint


def test_validate_svg_icon_import_reports_existing_fallback_targets(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    package_root = tmp_path
    icon_dir = package_root / "icons"
    manifest_path = icon_dir / "manifest.json"
    source_path = tmp_path / "source.svg"
    fallback_path = icon_dir / "custom" / "arrow@2x.png"
    fallback_path.parent.mkdir(parents=True)
    fallback_path.write_bytes(PNG_BYTES)
    manifest_path.write_text('{"icons": []}\n', encoding="utf-8")
    source_path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        '<path d="M4 12h16"/></svg>',
        encoding="utf-8",
    )
    monkeypatch.setattr(icons, "_PACKAGE_ROOT", package_root)
    monkeypatch.setattr(icons, "_ICON_DIR", icon_dir)
    monkeypatch.setattr(icons, "_MANIFEST_PATH", manifest_path)

    issues = validate_svg_icon_import(
        source_path,
        "custom.arrow",
        source="Local",
        license_name="Apache-2.0",
        url="local://source.svg",
        target_path="icons/custom/arrow.svg",
    )

    assert [(issue.code, issue.path, issue.field) for issue in issues] == [
        (
            "icon_fallback_target_exists",
            "icons/custom/arrow@2x.png",
            "fallbacks.2x",
        )
    ]
    assert "overwrite=True" in issues[0].hint


def test_validate_svg_icon_import_ignores_fallback_targets_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    package_root = tmp_path
    icon_dir = package_root / "icons"
    manifest_path = icon_dir / "manifest.json"
    source_path = tmp_path / "source.svg"
    fallback_path = icon_dir / "custom" / "arrow@2x.png"
    fallback_path.parent.mkdir(parents=True)
    fallback_path.write_bytes(PNG_BYTES)
    manifest_path.write_text('{"icons": []}\n', encoding="utf-8")
    source_path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        '<path d="M4 12h16"/></svg>',
        encoding="utf-8",
    )
    monkeypatch.setattr(icons, "_PACKAGE_ROOT", package_root)
    monkeypatch.setattr(icons, "_ICON_DIR", icon_dir)
    monkeypatch.setattr(icons, "_MANIFEST_PATH", manifest_path)

    issues = validate_svg_icon_import(
        source_path,
        "custom.arrow",
        source="Local",
        license_name="Apache-2.0",
        url="local://source.svg",
        target_path="icons/custom/arrow.svg",
        generate_fallbacks=False,
    )

    assert issues == ()


def test_validate_svg_icon_import_reports_fallback_manifest_path_conflict(
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
                        "id": "other.arrow",
                        "source": "Existing",
                        "license": "MIT",
                        "url": "local://existing.svg",
                        "imported_at": "2026-05-01",
                        "path": "icons/other/arrow.svg",
                        "fallbacks": {
                            "1x": "icons/custom/arrow@1x.png",
                            "2x": "icons/other/arrow@2x.png",
                            "3x": "icons/other/arrow@3x.png",
                        },
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    source_path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        '<path d="M4 12h16"/></svg>',
        encoding="utf-8",
    )
    monkeypatch.setattr(icons, "_PACKAGE_ROOT", package_root)
    monkeypatch.setattr(icons, "_ICON_DIR", icon_dir)
    monkeypatch.setattr(icons, "_MANIFEST_PATH", manifest_path)

    issues = validate_svg_icon_import(
        source_path,
        "custom.arrow",
        source="Local",
        license_name="Apache-2.0",
        url="local://source.svg",
        target_path="icons/custom/arrow.svg",
        overwrite=True,
    )

    assert [(issue.code, issue.path, issue.field) for issue in issues] == [
        (
            "icon_fallback_path_conflict",
            "icons/custom/arrow@1x.png",
            "fallbacks.1x",
        )
    ]
    assert "other.arrow" in issues[0].message


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
    assert all("generate_png_fallbacks" in issue.hint for issue in issues)


def test_icon_dataclasses_report_compact_status() -> None:
    issue = icons.IconManifestIssue(
        "missing_icon",
        "Missing.",
        icon_id="missing.icon",
        hint="Add it.",
    )

    assert issue.as_dict() == {
        "code": "missing_icon",
        "message": "Missing.",
        "icon_id": "missing.icon",
        "hint": "Add it.",
    }
    assert icons.IconStatus("").ok is False


def test_manifest_shape_errors_cover_missing_invalid_and_bad_entries(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest_path = tmp_path / "icons" / "manifest.json"
    monkeypatch.setattr(icons, "_MANIFEST_PATH", manifest_path)

    assert validate_icon_manifest()[0].code == "missing_icon_manifest"

    manifest_path.parent.mkdir()
    manifest_path.write_text("{not json", encoding="utf-8")
    assert validate_icon_manifest()[0].message.endswith("JSONDecodeError.")

    manifest_path.write_text('{"icons": "bad"}', encoding="utf-8")
    assert validate_icon_manifest()[0].code == "invalid_icon_manifest"

    manifest_path.write_text('{"icons": ["bad"]}', encoding="utf-8")
    assert "entries must be objects" in validate_icon_manifest()[0].message


def test_icon_status_reports_manifest_shape_and_asset_issues(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest_path = tmp_path / "icons" / "manifest.json"
    manifest_path.parent.mkdir()
    manifest_path.write_text(
        json.dumps(
            {
                "icons": [
                    {
                        "id": "broken.path",
                        "source": "Local",
                        "license": "Apache-2.0",
                        "url": "local://broken.svg",
                        "imported_at": "2026-04-30",
                        "path": "../broken.svg",
                    },
                    {
                        "id": "missing.file",
                        "source": "Local",
                        "license": "Apache-2.0",
                        "url": "local://missing.svg",
                        "imported_at": "2026-04-30",
                        "path": "missing.svg",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(icons, "_PACKAGE_ROOT", tmp_path)
    monkeypatch.setattr(icons, "_ICON_DIR", tmp_path / "icons")
    monkeypatch.setattr(icons, "_MANIFEST_PATH", manifest_path)

    assert icon_status("").issue is None
    assert icon_status("broken.path").issue.code == "invalid_icon_path"
    assert icon_status("missing.file").issue.code == "missing_icon_file"


def test_validate_svg_icon_import_reports_invalid_manifest_and_duplicate(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    icon_dir = tmp_path / "icons"
    manifest_path = icon_dir / "manifest.json"
    source_path = tmp_path / "source.svg"
    icon_dir.mkdir()
    source_path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"></svg>',
        encoding="utf-8",
    )
    monkeypatch.setattr(icons, "_PACKAGE_ROOT", tmp_path)
    monkeypatch.setattr(icons, "_ICON_DIR", icon_dir)
    monkeypatch.setattr(icons, "_MANIFEST_PATH", manifest_path)

    manifest_path.write_text("{not json", encoding="utf-8")
    assert validate_svg_icon_import(
        source_path,
        "custom.arrow",
        source="Local",
        license_name="Apache-2.0",
        url="local://source.svg",
    )[0].code == "invalid_icon_manifest"

    manifest_path.write_text(
        json.dumps(
            {
                "icons": [
                    {
                        "id": "custom.arrow",
                        "source": "Local",
                        "license": "Apache-2.0",
                        "url": "local://old.svg",
                        "imported_at": "2026-04-30",
                        "path": "icons/custom/arrow.svg",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    assert validate_svg_icon_import(
        source_path,
        "custom.arrow",
        source="Local",
        license_name="Apache-2.0",
        url="local://source.svg",
    )[0].code == "duplicate_icon"


def test_validate_svg_icon_import_reports_invalid_sources_and_targets(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    icon_dir = tmp_path / "icons"
    manifest_path = icon_dir / "manifest.json"
    icon_dir.mkdir()
    manifest_path.write_text('{"icons": []}', encoding="utf-8")
    source_path = tmp_path / "source.svg"
    source_path.write_text("<svg></svg>", encoding="utf-8")
    monkeypatch.setattr(icons, "_PACKAGE_ROOT", tmp_path)
    monkeypatch.setattr(icons, "_ICON_DIR", icon_dir)
    monkeypatch.setattr(icons, "_MANIFEST_PATH", manifest_path)

    assert validate_svg_icon_import(
        tmp_path / "missing.svg",
        "custom.arrow",
        source="Local",
        license_name="Apache-2.0",
        url="local://missing.svg",
    )[0].code == "missing_icon_import_source"
    assert validate_svg_icon_import(
        source_path,
        "custom.arrow",
        source="Local",
        license_name="Apache-2.0",
        url="local://source.svg",
        target_path="icons/custom/arrow.png",
    )[-1].code == "invalid_icon_import_target"
    assert validate_svg_icon_import(
        source_path,
        "custom.arrow",
        source="Local",
        license_name="Apache-2.0",
        url="local://source.svg",
        imported_at="",
    )[0].field == "imported_at"


def test_validate_icon_manifest_reports_fallback_metadata_shapes(
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
        "fallbacks": {"1x": "../escape.png", "2x": "bad.txt", "3x": ""},
        "fallback_source_sha256": "",
        "fallback_base_size": 0,
    }
    monkeypatch.setattr(icons, "_manifest_icons", lambda: (entry,))
    monkeypatch.setattr(icons, "_resolve_manifest_path", lambda path: tmp_path / path)

    issues = validate_icon_manifest()

    assert [issue.code for issue in issues] == [
        "invalid_icon_fallback_path",
        "invalid_icon_fallback_path",
        "missing_icon_fallback",
        "missing_icon_fallback_hash",
        "invalid_icon_fallback_size",
    ]

    entry["fallbacks"] = "bad"
    assert validate_icon_manifest()[0].code == "invalid_icon_fallbacks"


def test_svg_validation_rejects_bad_roots_and_unsafe_references(tmp_path: Path) -> None:
    cases = [
        ("bad.xml", "<not-svg></not-svg>", "invalid_icon_svg"),
        (
            "foreign.svg",
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"><foreignObject /></svg>',
            "unsafe_icon_svg",
        ),
        (
            "event.svg",
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1" onclick="x"></svg>',
            "unsafe_icon_svg",
        ),
        (
            "href.svg",
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"><image href="https://example.test/x.png"/></svg>',
            "unsafe_icon_svg",
        ),
        (
            "style-attr.svg",
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1" style="background:url(https://example.test/x.png)"></svg>',
            "unsafe_icon_svg",
        ),
    ]

    for filename, contents, expected_code in cases:
        svg_path = tmp_path / filename
        svg_path.write_text(contents, encoding="utf-8")
        assert icons._svg_issue("test.svg", filename, svg_path).code == expected_code

    invalid_xml = tmp_path / "invalid.svg"
    invalid_xml.write_text("<svg", encoding="utf-8")
    assert icons._svg_issue("test.svg", "invalid.svg", invalid_xml).code == "invalid_icon_svg"


def test_generate_png_fallbacks_rejects_invalid_manifest_entries(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    icon_dir = tmp_path / "icons"
    manifest_path = icon_dir / "manifest.json"
    icon_dir.mkdir()
    monkeypatch.setattr(icons, "_PACKAGE_ROOT", tmp_path)
    monkeypatch.setattr(icons, "_ICON_DIR", icon_dir)
    monkeypatch.setattr(icons, "_MANIFEST_PATH", manifest_path)

    manifest_path.write_text('{"icons": []}', encoding="utf-8")
    with pytest.raises(ValueError, match="not listed"):
        generate_png_fallbacks("missing.icon")

    manifest_path.write_text('{"icons": [{"id": "bad"}]}', encoding="utf-8")
    with pytest.raises(ValueError, match="field 'source'"):
        generate_png_fallbacks("bad")

    manifest_path.write_text(
        json.dumps(
            {
                "icons": [
                    {
                        "id": "missing.file",
                        "source": "Local",
                        "license": "Apache-2.0",
                        "url": "local://missing.svg",
                        "imported_at": "2026-04-30",
                        "path": "icons/missing.svg",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="missing file"):
        generate_png_fallbacks("missing.file")

    png_path = icon_dir / "source.png"
    png_path.write_bytes(PNG_BYTES)
    manifest_path.write_text(
        json.dumps(
            {
                "icons": [
                    {
                        "id": "png.source",
                        "source": "Local",
                        "license": "Apache-2.0",
                        "url": "local://source.png",
                        "imported_at": "2026-04-30",
                        "path": "icons/source.png",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="must point to an SVG"):
        generate_png_fallbacks("png.source")


def test_generate_png_fallbacks_restores_existing_files_on_renderer_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    icon_dir = tmp_path / "icons"
    manifest_path = icon_dir / "manifest.json"
    svg_path = icon_dir / "source.svg"
    fallback_path = icon_dir / "source@1x.png"
    icon_dir.mkdir()
    svg_path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"></svg>',
        encoding="utf-8",
    )
    fallback_path.write_bytes(OLD_PNG_BYTES)
    manifest_path.write_text(
        json.dumps(
            {
                "icons": [
                    {
                        "id": "test.source",
                        "source": "Local",
                        "license": "Apache-2.0",
                        "url": "local://source.svg",
                        "imported_at": "2026-04-30",
                        "path": "icons/source.svg",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(icons, "_PACKAGE_ROOT", tmp_path)
    monkeypatch.setattr(icons, "_ICON_DIR", icon_dir)
    monkeypatch.setattr(icons, "_MANIFEST_PATH", manifest_path)

    with pytest.raises(RuntimeError, match="renderer failed"):
        generate_png_fallbacks("test.source", png_renderer=failing_png_renderer)

    assert fallback_path.read_bytes() == OLD_PNG_BYTES
    assert not (icon_dir / "source@2x.png").exists()
    assert not (icon_dir / "source@3x.png").exists()


def test_render_png_reports_missing_or_failing_mayapy(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    svg_path = tmp_path / "source.svg"
    png_path = tmp_path / "source.png"
    monkeypatch.setattr(icons, "_mayapy_candidates", lambda: ())

    with pytest.raises(RuntimeError, match="mayapy"):
        icons._render_png_with_mayapy(svg_path, png_path, 24)
    with pytest.raises(RuntimeError, match="Unable to generate PNG"):
        icons._render_png(svg_path, png_path, 24, None)

    monkeypatch.setattr(icons, "_mayapy_candidates", lambda: ("mayapy",))
    monkeypatch.setattr(
        icons.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 1, "out", "err"),
    )
    with pytest.raises(RuntimeError, match="err"):
        icons._render_png_with_mayapy(svg_path, png_path, 24)


def test_mayapy_candidates_are_unique_and_sorted(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeAutodeskRoot:
        def is_dir(self) -> bool:
            return True

        def glob(self, pattern: str) -> list[Path]:
            assert pattern == "Maya*/bin/mayapy.exe"
            return [
                Path("C:/Program Files/Autodesk/Maya2026/bin/mayapy.exe"),
                Path("C:/Program Files/Autodesk/Maya2025/bin/mayapy.exe"),
            ]

    def fake_path(value: str) -> object:
        if value == "C:/Program Files/Autodesk":
            return FakeAutodeskRoot()
        return Path(value)

    monkeypatch.setattr(icons.shutil, "which", lambda _name: "C:/mayapy.exe")
    monkeypatch.setattr(icons, "Path", fake_path)

    candidates = icons._mayapy_candidates()

    assert candidates[0] == "C:/mayapy.exe"
    assert len(candidates) == len(set(candidates))


def test_icon_status_reports_manifest_shape_and_entry_issues(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(icons, "_manifest_icons", lambda: ({"__manifest_error__": "missing"},))
    assert icon_status("anything").issue.code == "missing_icon_manifest"

    monkeypatch.setattr(icons, "_manifest_icons", lambda: ({"id": "bad.entry"},))
    assert icon_status("bad.entry").issue.field == "source"


def test_validate_icon_manifest_records_invalid_entries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(icons, "_manifest_icons", lambda: ({"id": "bad.entry"},))

    issues = validate_icon_manifest()

    assert issues[0].field == "source"


def test_manifest_payload_for_update_handles_missing_and_bad_shapes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest_path = tmp_path / "icons" / "manifest.json"
    monkeypatch.setattr(icons, "_MANIFEST_PATH", manifest_path)

    assert icons._manifest_payload_for_update() == {"icons": []}

    manifest_path.parent.mkdir()
    manifest_path.write_text('{"icons": ["bad"]}', encoding="utf-8")
    with pytest.raises(ValueError, match="icons list"):
        icons._manifest_payload_for_update()


def test_manifest_entry_icon_path_rejects_invalid_paths() -> None:
    assert icons._manifest_entry_icon_path({"path": ""}) is None
    assert icons._manifest_entry_icon_path({"path": "../escape.svg"}) is None


def test_upsert_manifest_entry_appends_new_entries() -> None:
    entries = [{"id": "existing"}]
    icons._upsert_manifest_entry(entries, {"id": "new"})

    assert entries == [{"id": "existing"}, {"id": "new"}]


def test_fallback_helpers_ignore_non_svg_and_non_string_owner_paths(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(icons, "_PACKAGE_ROOT", tmp_path)
    monkeypatch.setattr(icons, "_ICON_DIR", tmp_path / "icons")
    entry = {
        "id": "png.icon",
        "source": "Local",
        "license": "Apache-2.0",
        "url": "local://icon.png",
        "imported_at": "2026-04-30",
        "path": "icon.png",
    }

    assert icons._fallback_issues(entry, require_fallbacks=True) == ()
    assert icons._fallback_manifest_path_owner(
        "icons/custom/arrow@1x.png",
        [{"id": "other", "fallbacks": {"1x": 123}}],
        icon_id="current",
    ) == ""


def test_import_metadata_and_target_helpers_reject_bad_values(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(icons, "_PACKAGE_ROOT", tmp_path)
    monkeypatch.setattr(icons, "_ICON_DIR", tmp_path / "icons")

    with pytest.raises(ValueError, match="must be a non-empty string"):
        icons._validate_import_metadata(
            icon_id="custom.arrow",
            source="",
            license_name="Apache-2.0",
            url="local://arrow.svg",
            imported_at=None,
        )
    assert icons._import_metadata_issue(
        icon_id="custom.arrow",
        source="",
        license_name="Apache-2.0",
        url="local://arrow.svg",
        imported_at=None,
    ).field == "source"

    with pytest.raises(ValueError, match="non-empty string"):
        icons._resolve_import_target("")
    monkeypatch.setattr(icons, "_PACKAGE_ROOT", tmp_path / "package")
    with pytest.raises(ValueError, match="inside the ActionRail icons directory"):
        icons._resolve_import_target("icons/arrow.svg")


def test_path_and_snapshot_helpers_cover_absolute_duplicate_and_suffixless_paths(
    tmp_path: Path,
) -> None:
    existing = tmp_path / "existing.txt"
    missing = tmp_path / "missing.txt"
    existing.write_text("old", encoding="utf-8")

    snapshots = icons._snapshot_files((existing, existing, missing))
    existing.write_text("new", encoding="utf-8")
    missing.write_text("created", encoding="utf-8")
    icons._restore_file_snapshots(snapshots)

    assert existing.read_text(encoding="utf-8") == "old"
    assert not missing.exists()
    assert icons._fallback_manifest_path("icons/custom/icon", 2) == "icons/custom/icon@2x.png"
    assert icons._resolve_manifest_path(str(existing)) == existing


def test_mayapy_candidates_deduplicates_equivalent_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeAutodeskRoot:
        def is_dir(self) -> bool:
            return True

        def glob(self, _pattern: str) -> list[Path]:
            return [Path("C:/mayapy.exe")]

    def fake_path(value: str) -> object:
        if value == "C:/Program Files/Autodesk":
            return FakeAutodeskRoot()
        return Path(value)

    monkeypatch.setattr(icons.shutil, "which", lambda _name: "C:/mayapy.exe")
    monkeypatch.setattr(icons, "Path", fake_path)

    assert icons._mayapy_candidates() == ("C:/mayapy.exe",)
