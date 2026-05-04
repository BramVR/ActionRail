"""PNG fallback validation and rendering for SVG icons.

Purpose: keep mayapy/Qt rendering and fallback asset bookkeeping outside the
picker-facing catalog and import preflight UI.
Used by: icon manifest validation, SVG import pipeline, and the public facade.
Tests: ``tests/test_icons.py``.
"""

from __future__ import annotations

import shutil
import subprocess
from contextlib import suppress
from pathlib import Path
from typing import Any

from . import icon_paths
from .icon_types import IconFallbackResult, IconManifestIssue, PngRenderer

FALLBACK_SCALES = (1, 2, 3)
FALLBACK_BASE_SIZE = 24
FALLBACKS_FIELD = "fallbacks"
FALLBACK_HASH_FIELD = "fallback_source_sha256"
FALLBACK_SIZE_FIELD = "fallback_base_size"


def generate_png_fallbacks(
    icon_id: str,
    *,
    png_renderer: PngRenderer | None = None,
) -> IconFallbackResult:
    """Generate 1x/2x/3x PNG fallbacks for an existing manifest SVG icon."""

    from . import icon_manifest

    payload = icon_manifest.manifest_payload_for_update()
    entries = payload["icons"]
    entry = next((entry for entry in entries if entry.get("id") == icon_id), None)
    if entry is None:
        msg = f"Icon id '{icon_id}' is not listed in the ActionRail icon manifest."
        raise ValueError(msg)

    entry_issue = icon_manifest.entry_issue(entry)
    if entry_issue is not None:
        raise ValueError(entry_issue.message)

    raw_path = entry["path"]
    icon_path = icon_paths.resolve_manifest_path(raw_path)
    asset_issue = icon_manifest.asset_issue(icon_id, raw_path, icon_path)
    if asset_issue is not None:
        raise ValueError(asset_issue.message)
    if icon_path.suffix.lower() != ".svg":
        msg = f"Icon '{icon_id}' must point to an SVG source to generate PNG fallbacks."
        raise ValueError(msg)

    manifest_entry = dict(entry)
    snapshots = snapshot_files(fallback_paths_for_manifest_entry(manifest_entry))
    try:
        fallback_paths = generate_png_fallbacks_for_entry(
            manifest_entry,
            icon_path,
            png_renderer=png_renderer,
        )
    except Exception:
        restore_file_snapshots(snapshots)
        raise
    icon_manifest.upsert_manifest_entry(entries, manifest_entry)
    icon_manifest.write_manifest_payload(payload)
    return IconFallbackResult(
        icon_id=icon_id,
        source_path=icon_path,
        fallback_paths=fallback_paths,
        manifest_path=icon_paths.MANIFEST_PATH,
        manifest_entry=manifest_entry,
    )


def fallback_issues(
    entry: dict[str, Any],
    *,
    require_fallbacks: bool,
) -> tuple[IconManifestIssue, ...]:
    raw_path = entry.get("path")
    icon_id = entry.get("id") if isinstance(entry.get("id"), str) else ""
    if (
        not isinstance(raw_path, str)
        or icon_paths.resolve_manifest_path(raw_path).suffix.lower() != ".svg"
    ):
        return ()

    fallbacks = entry.get(FALLBACKS_FIELD)
    if fallbacks is None:
        if not require_fallbacks:
            return ()
        return (
            IconManifestIssue(
                code="missing_icon_fallbacks",
                message=f"Icon '{icon_id}' does not list generated PNG fallbacks.",
                icon_id=icon_id,
                path=raw_path,
                field=FALLBACKS_FIELD,
                hint=fallback_regeneration_hint(icon_id),
            ),
        )

    if not isinstance(fallbacks, dict):
        return (
            IconManifestIssue(
                code="invalid_icon_fallbacks",
                message=f"Icon '{icon_id}' fallback metadata must be an object.",
                icon_id=icon_id,
                path=raw_path,
                field=FALLBACKS_FIELD,
                hint="Replace fallback metadata with 1x, 2x, and 3x PNG paths.",
            ),
        )

    issues: list[IconManifestIssue] = []
    for scale in FALLBACK_SCALES:
        label = f"{scale}x"
        fallback_path = fallbacks.get(label)
        if not isinstance(fallback_path, str) or not fallback_path:
            issues.append(
                IconManifestIssue(
                    code="missing_icon_fallback",
                    message=f"Icon '{icon_id}' is missing its {label} PNG fallback path.",
                    icon_id=icon_id,
                    path=raw_path,
                    field=f"{FALLBACKS_FIELD}.{label}",
                    hint=fallback_regeneration_hint(icon_id),
                )
            )
            continue

        fallback_issue = fallback_path_issue(icon_id, fallback_path)
        if fallback_issue is not None:
            issues.append(fallback_issue)

    recorded_hash = entry.get(FALLBACK_HASH_FIELD)
    current_hash = icon_paths.file_sha256(icon_paths.resolve_manifest_path(raw_path))
    if not isinstance(recorded_hash, str) or not recorded_hash:
        issues.append(
            IconManifestIssue(
                code="missing_icon_fallback_hash",
                message=f"Icon '{icon_id}' does not record a fallback source hash.",
                icon_id=icon_id,
                path=raw_path,
                field=FALLBACK_HASH_FIELD,
                hint=fallback_regeneration_hint(icon_id),
            )
        )
    elif recorded_hash != current_hash:
        issues.append(
            IconManifestIssue(
                code="stale_icon_fallback",
                message=f"Icon '{icon_id}' PNG fallbacks are stale for source SVG: {raw_path}.",
                icon_id=icon_id,
                path=raw_path,
                field=FALLBACK_HASH_FIELD,
                hint=fallback_regeneration_hint(icon_id),
            )
        )

    recorded_size = entry.get(FALLBACK_SIZE_FIELD)
    if not isinstance(recorded_size, int) or recorded_size <= 0:
        issues.append(
            IconManifestIssue(
                code="invalid_icon_fallback_size",
                message=f"Icon '{icon_id}' fallback base size must be a positive integer.",
                icon_id=icon_id,
                path=raw_path,
                field=FALLBACK_SIZE_FIELD,
                hint=fallback_regeneration_hint(icon_id),
            )
        )

    return tuple(issues)


def fallback_path_issue(icon_id: str, raw_path: str) -> IconManifestIssue | None:
    manifest_path = Path(raw_path)
    if manifest_path.is_absolute() or ".." in manifest_path.parts:
        return IconManifestIssue(
            code="invalid_icon_fallback_path",
            message=(
                f"Icon '{icon_id}' fallback path must stay inside the "
                "ActionRail icons directory."
            ),
            icon_id=icon_id,
            path=raw_path,
            hint="Use a relative PNG fallback path inside icons/.",
        )
    if manifest_path.suffix.lower() != ".png":
        return IconManifestIssue(
            code="invalid_icon_fallback_path",
            message=f"Icon '{icon_id}' fallback path must use the .png extension.",
            icon_id=icon_id,
            path=raw_path,
            hint="Regenerate PNG fallbacks or update the fallback path to a .png file.",
        )

    fallback_path = icon_paths.resolve_manifest_path(raw_path)
    if not fallback_path.is_file():
        return IconManifestIssue(
            code="missing_icon_fallback_file",
            message=f"Icon '{icon_id}' points to a missing PNG fallback: {raw_path}.",
            icon_id=icon_id,
            path=raw_path,
            hint=fallback_regeneration_hint(icon_id),
        )
    return None


def fallback_import_target_issues(
    icon_id: str,
    icon_path: Path,
    entries: list[dict[str, Any]],
    *,
    overwrite: bool,
) -> tuple[IconManifestIssue, ...]:
    manifest_svg_path = icon_paths.manifest_path_for_icon_path(icon_path)
    issues: list[IconManifestIssue] = []
    for scale in FALLBACK_SCALES:
        label = f"{scale}x"
        fallback_manifest_path = fallback_manifest_path_for_svg(manifest_svg_path, scale)
        conflicting_id = fallback_manifest_path_owner(
            fallback_manifest_path,
            entries,
            icon_id=icon_id,
        )
        if conflicting_id:
            issues.append(
                IconManifestIssue(
                    code="icon_fallback_path_conflict",
                    message=(
                        f"Generated PNG fallback path '{fallback_manifest_path}' "
                        f"is already used by icon '{conflicting_id}'."
                    ),
                    icon_id=icon_id,
                    path=fallback_manifest_path,
                    field=f"{FALLBACKS_FIELD}.{label}",
                    hint=(
                        "Choose a target path whose generated fallback paths "
                        "are not used by another icon."
                    ),
                )
            )
            continue

        fallback_path = icon_paths.resolve_manifest_path(fallback_manifest_path)
        if fallback_path.exists() and not overwrite:
            issues.append(
                IconManifestIssue(
                    code="icon_fallback_target_exists",
                    message=f"Generated PNG fallback target already exists: {fallback_path}",
                    icon_id=icon_id,
                    path=fallback_manifest_path,
                    field=f"{FALLBACKS_FIELD}.{label}",
                    hint=(
                        "Use overwrite=True to replace generated fallback assets, "
                        "choose another target path, or remove the orphaned PNG."
                    ),
                )
            )
    return tuple(issues)


def fallback_manifest_path_owner(
    fallback_manifest_path: str,
    entries: list[dict[str, Any]],
    *,
    icon_id: str,
) -> str:
    fallback_path = icon_paths.resolve_manifest_path(fallback_manifest_path).resolve(strict=False)
    for entry in entries:
        if entry.get("id") == icon_id:
            continue
        fallbacks = entry.get(FALLBACKS_FIELD)
        if not isinstance(fallbacks, dict):
            continue
        for raw_path in fallbacks.values():
            if not isinstance(raw_path, str):
                continue
            if icon_paths.resolve_manifest_path(raw_path).resolve(strict=False) == fallback_path:
                return str(entry.get("id") or "<unknown>")
    return ""


def fallback_regeneration_hint(icon_id: str) -> str:
    return f"Regenerate fallbacks with actionrail.icons.generate_png_fallbacks({icon_id!r})."


def generate_png_fallbacks_for_entry(
    manifest_entry: dict[str, Any],
    icon_path: Path,
    *,
    png_renderer: PngRenderer | None,
) -> tuple[Path, ...]:
    fallback_paths: list[Path] = []
    fallback_manifest_paths: dict[str, str] = {}
    for scale in FALLBACK_SCALES:
        fallback_manifest_path = fallback_manifest_path_for_svg(manifest_entry["path"], scale)
        fallback_path = icon_paths.resolve_manifest_path(fallback_manifest_path)
        fallback_path.parent.mkdir(parents=True, exist_ok=True)
        render_png(icon_path, fallback_path, FALLBACK_BASE_SIZE * scale, png_renderer)
        fallback_paths.append(fallback_path)
        fallback_manifest_paths[f"{scale}x"] = fallback_manifest_path

    manifest_entry[FALLBACKS_FIELD] = fallback_manifest_paths
    manifest_entry[FALLBACK_HASH_FIELD] = icon_paths.file_sha256(icon_path)
    manifest_entry[FALLBACK_SIZE_FIELD] = FALLBACK_BASE_SIZE
    return tuple(fallback_paths)


def fallback_paths_for_manifest_entry(manifest_entry: dict[str, Any]) -> tuple[Path, ...]:
    return tuple(
        icon_paths.resolve_manifest_path(
            fallback_manifest_path_for_svg(manifest_entry["path"], scale)
        )
        for scale in FALLBACK_SCALES
    )


def snapshot_files(paths: list[Path] | tuple[Path, ...]) -> dict[Path, bytes | None]:
    snapshots: dict[Path, bytes | None] = {}
    for path in paths:
        key = path.resolve(strict=False)
        if key in snapshots:
            continue
        snapshots[key] = key.read_bytes() if key.is_file() else None
    return snapshots


def restore_file_snapshots(snapshots: dict[Path, bytes | None]) -> None:
    for path, contents in snapshots.items():
        if contents is None:
            with suppress(FileNotFoundError):
                path.unlink()
            continue

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(contents)


def fallback_manifest_path_for_svg(raw_svg_path: str, scale: int) -> str:
    source_path = Path(raw_svg_path)
    suffix = f"@{scale}x.png"
    if source_path.suffix:
        return source_path.with_name(f"{source_path.stem}{suffix}").as_posix()
    return source_path.with_name(f"{source_path.name}{suffix}").as_posix()


def render_png(
    svg_path: Path,
    png_path: Path,
    size_px: int,
    png_renderer: PngRenderer | None,
) -> None:
    if png_renderer is not None:
        png_renderer(svg_path, png_path, size_px)
        return

    try:
        render_png_with_mayapy(svg_path, png_path, size_px)
    except Exception as exc:
        msg = f"Unable to generate PNG fallback assets with mayapy: {exc}"
        raise RuntimeError(msg) from exc


def render_png_with_mayapy(svg_path: Path, png_path: Path, size_px: int) -> None:
    mayapy = next(iter(mayapy_candidates()), "")
    if not mayapy:
        raise RuntimeError("Autodesk Maya 'mayapy' executable is unavailable")

    script = """
import sys
from PySide6 import QtCore, QtGui, QtSvg

svg_path, png_path, size_text = sys.argv[1:4]
size_px = int(size_text)
renderer = QtSvg.QSvgRenderer(svg_path)
if not renderer.isValid():
    raise SystemExit(f"Qt could not load SVG icon: {svg_path}")
image = QtGui.QImage(size_px, size_px, QtGui.QImage.Format_ARGB32)
image.fill(QtCore.Qt.transparent)
painter = QtGui.QPainter(image)
try:
    renderer.render(painter)
finally:
    painter.end()
if not image.save(png_path, "PNG"):
    raise SystemExit(f"Qt could not write PNG fallback: {png_path}")
"""
    completed = subprocess.run(
        [mayapy, "-c", script, str(svg_path), str(png_path), str(size_px)],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode:
        message = completed.stderr.strip() or completed.stdout.strip() or "unknown error"
        raise RuntimeError(message)


def mayapy_candidates() -> tuple[str, ...]:
    candidates: list[str] = []
    path_candidate = shutil.which("mayapy")
    if path_candidate:
        candidates.append(path_candidate)

    autodesk_root = Path("C:/Program Files/Autodesk")
    if autodesk_root.is_dir():
        candidates.extend(
            str(path)
            for path in sorted(
                autodesk_root.glob("Maya*/bin/mayapy.exe"),
                key=lambda candidate: candidate.as_posix(),
                reverse=True,
            )
        )

    seen: set[str] = set()
    unique_candidates: list[str] = []
    for candidate in candidates:
        normalized = str(Path(candidate).resolve(strict=False)).lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        unique_candidates.append(candidate)
    return tuple(unique_candidates)
