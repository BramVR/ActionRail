"""SVG icon import pipeline.

Purpose: own local SVG import preflight, target conflict detection, manifest
mutation, asset copying, and rollback around generated fallback writes.
Used by: Maya import diagnostics/menu flow and the public facade.
Tests: ``tests/test_icons.py``.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from . import icon_fallbacks, icon_manifest, icon_paths, icon_svg
from .icon_types import IconImportResult, IconManifestIssue, PngRenderer

ICON_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9_-]+")


def import_svg_icon(
    source_path: str | Path,
    icon_id: str,
    *,
    source: str,
    license_name: str,
    url: str,
    imported_at: str | None = None,
    target_path: str = "",
    overwrite: bool = False,
    generate_fallbacks: bool = True,
    png_renderer: PngRenderer | None = None,
) -> IconImportResult:
    """Import a safe local SVG and record its source metadata in the manifest."""

    import_issues = validate_svg_icon_import(
        source_path,
        icon_id,
        source=source,
        license_name=license_name,
        url=url,
        imported_at=imported_at,
        target_path=target_path,
        overwrite=overwrite,
        generate_fallbacks=generate_fallbacks,
    )
    if import_issues:
        raise ValueError(import_issues[0].message)

    source_file = Path(source_path)
    payload = icon_manifest.manifest_payload_for_update()
    entries = payload["icons"]
    existing = [entry for entry in entries if entry.get("id") == icon_id]

    raw_manifest_path = (
        target_path
        or icon_manifest.existing_icon_path(existing)
        or default_import_manifest_path(icon_id)
    )
    icon_path = resolve_import_target(raw_manifest_path)
    manifest_path = icon_paths.manifest_path_for_icon_path(icon_path)

    manifest_entry = {
        "id": icon_id,
        "source": source,
        "license": license_name,
        "url": url,
        "imported_at": imported_at or date.today().isoformat(),
        "path": manifest_path,
    }

    fallback_paths: tuple[Path, ...] = ()
    rollback_paths = [icon_path]
    if generate_fallbacks:
        rollback_paths.extend(icon_fallbacks.fallback_paths_for_manifest_entry(manifest_entry))
    snapshots = icon_fallbacks.snapshot_files(rollback_paths)

    try:
        icon_manifest.upsert_manifest_entry(entries, manifest_entry)
        icon_path.parent.mkdir(parents=True, exist_ok=True)
        icon_path.write_text(source_file.read_text(encoding="utf-8"), encoding="utf-8")
        if generate_fallbacks:
            fallback_paths = icon_fallbacks.generate_png_fallbacks_for_entry(
                manifest_entry,
                icon_path,
                png_renderer=png_renderer,
            )
    except Exception:
        icon_fallbacks.restore_file_snapshots(snapshots)
        raise

    icon_manifest.write_manifest_payload(payload)

    return IconImportResult(
        icon_id=icon_id,
        path=icon_path,
        manifest_path=icon_paths.MANIFEST_PATH,
        manifest_entry=manifest_entry,
        replaced_existing=bool(existing),
        fallback_paths=fallback_paths,
    )


def validate_svg_icon_import(
    source_path: str | Path,
    icon_id: str,
    *,
    source: str,
    license_name: str,
    url: str,
    imported_at: str | None = None,
    target_path: str = "",
    overwrite: bool = False,
    generate_fallbacks: bool = True,
) -> tuple[IconManifestIssue, ...]:
    """Return structured diagnostics for a local SVG import without writing files."""

    issues: list[IconManifestIssue] = []
    source_file = Path(source_path)
    if not source_file.is_file():
        issues.append(
            IconManifestIssue(
                code="missing_icon_import_source",
                message=f"SVG icon source does not exist: {source_file}",
                icon_id=icon_id,
                path=str(source_file),
                hint="Choose an existing local .svg file before running the import preflight.",
            )
        )
    elif source_file.suffix.lower() != ".svg":
        issues.append(
            IconManifestIssue(
                code="invalid_icon_import_source",
                message="ActionRail only imports SVG icon sources.",
                icon_id=icon_id,
                path=str(source_file),
                hint="Choose an SVG file; other icon source formats are not imported.",
            )
        )

    metadata_issue = import_metadata_issue(
        icon_id=icon_id,
        source=source,
        license_name=license_name,
        url=url,
        imported_at=imported_at,
    )
    if metadata_issue is not None:
        issues.append(metadata_issue)

    if source_file.is_file() and source_file.suffix.lower() == ".svg":
        issue = icon_svg.svg_issue(icon_id, str(source_file), source_file)
        if issue is not None:
            issues.append(issue)

    try:
        payload = icon_manifest.manifest_payload_for_update()
    except ValueError as exc:
        issues.append(
            IconManifestIssue(
                code="invalid_icon_manifest",
                message=str(exc),
                icon_id=icon_id,
                hint="Fix icons/manifest.json so it is an object with an icons list.",
            )
        )
        return tuple(issues)

    entries = payload["icons"]
    existing = [entry for entry in entries if entry.get("id") == icon_id]
    if existing and not overwrite:
        issues.append(
            IconManifestIssue(
                code="duplicate_icon",
                message=f"Icon id '{icon_id}' already exists in the ActionRail icon manifest.",
                icon_id=icon_id,
                hint="Use overwrite=True to replace the existing icon, or choose a new icon id.",
            )
        )

    raw_manifest_path = (
        target_path
        or icon_manifest.existing_icon_path(existing)
        or default_import_manifest_path(icon_id)
    )
    try:
        icon_path = resolve_import_target(raw_manifest_path)
    except ValueError as exc:
        issues.append(
            IconManifestIssue(
                code="invalid_icon_import_target",
                message=str(exc),
                icon_id=icon_id,
                path=raw_manifest_path,
                hint="Use a relative target under icons/ with the .svg extension.",
            )
        )
        return tuple(issues)

    conflicting_path = [
        entry
        for entry in entries
        if entry.get("id") != icon_id
        and icon_manifest.manifest_entry_icon_path(entry) == icon_path.resolve(strict=False)
    ]
    if conflicting_path:
        other_id = conflicting_path[0].get("id", "<unknown>")
        manifest_path = icon_paths.manifest_path_for_icon_path(icon_path)
        issues.append(
            IconManifestIssue(
                code="icon_path_conflict",
                message=(
                    f"Icon path '{manifest_path}' is already used by icon "
                    f"'{other_id}'."
                ),
                icon_id=icon_id,
                path=manifest_path,
                hint="Choose a target path that is not already used by another icon id.",
            )
        )
    if icon_path.exists() and not overwrite and not existing:
        issues.append(
            IconManifestIssue(
                code="icon_target_exists",
                message=f"Icon target already exists: {icon_path}",
                icon_id=icon_id,
                path=icon_paths.manifest_path_for_icon_path(icon_path),
                hint=(
                    "Use overwrite=True to replace the existing asset, or choose "
                    "another target path."
                ),
            )
        )
    if generate_fallbacks:
        issues.extend(
            icon_fallbacks.fallback_import_target_issues(
                icon_id,
                icon_path,
                entries,
                overwrite=overwrite,
            )
        )

    return tuple(issues)


def validate_import_metadata(
    *,
    icon_id: str,
    source: str,
    license_name: str,
    url: str,
    imported_at: str | None,
) -> None:
    issue = import_metadata_issue(
        icon_id=icon_id,
        source=source,
        license_name=license_name,
        url=url,
        imported_at=imported_at,
    )
    if issue is not None:
        raise ValueError(issue.message)


def import_metadata_issue(
    *,
    icon_id: str,
    source: str,
    license_name: str,
    url: str,
    imported_at: str | None,
) -> IconManifestIssue | None:
    if not isinstance(icon_id, str) or not ICON_ID_RE.fullmatch(icon_id):
        return IconManifestIssue(
            code="invalid_icon_import_metadata",
            message="Icon id must use letters, numbers, dots, underscores, or hyphens.",
            icon_id=icon_id if isinstance(icon_id, str) else "",
            field="icon_id",
            hint=(
                "Use an id such as namespace.name with only letters, numbers, dots, "
                "underscores, or hyphens."
            ),
        )
    for field, value in (
        ("source", source),
        ("license_name", license_name),
        ("url", url),
    ):
        if not isinstance(value, str) or not value:
            return IconManifestIssue(
                code="invalid_icon_import_metadata",
                message=f"Icon import field '{field}' must be a non-empty string.",
                icon_id=icon_id,
                field=field,
                hint="Provide source, license_name, and url metadata before importing.",
            )
    if imported_at is not None and (not isinstance(imported_at, str) or not imported_at):
        return IconManifestIssue(
            code="invalid_icon_import_metadata",
            message="Icon import field 'imported_at' must be a non-empty string when provided.",
            icon_id=icon_id,
            field="imported_at",
            hint="Omit imported_at to use today's date, or pass a non-empty date string.",
        )
    return None


def default_import_manifest_path(icon_id: str) -> str:
    parts = icon_id.split(".")
    namespace = safe_filename(parts[0] if len(parts) > 1 else "custom")
    filename = safe_filename("-".join(parts[1:]) if len(parts) > 1 else parts[0])
    return f"icons/{namespace}/{filename}.svg"


def safe_filename(value: str) -> str:
    safe = SAFE_FILENAME_RE.sub("-", value).strip("-")
    return safe or "icon"


def resolve_import_target(raw_path: str) -> Path:
    if not isinstance(raw_path, str) or not raw_path:
        msg = "Icon import target path must be a non-empty string."
        raise ValueError(msg)

    manifest_path = Path(raw_path)
    if manifest_path.is_absolute() or ".." in manifest_path.parts:
        msg = "Icon import target path must stay inside the ActionRail icons directory."
        raise ValueError(msg)
    if manifest_path.suffix.lower() != ".svg":
        msg = "Icon import target path must use the .svg extension."
        raise ValueError(msg)

    icon_path = icon_paths.resolve_manifest_path(raw_path)
    try:
        icon_path.resolve(strict=False).relative_to(icon_paths.ICON_DIR.resolve(strict=False))
    except ValueError as exc:
        msg = "Icon import target path must resolve inside the ActionRail icons directory."
        raise ValueError(msg) from exc
    return icon_path
