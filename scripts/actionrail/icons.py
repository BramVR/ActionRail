"""Icon manifest lookup and validation helpers for ActionRail presets.

Purpose: keep icon ids, source metadata, local paths, and SVG safety checks in
one pure-Python place.
Owns: `icons/manifest.json`, local SVG import, manifest diagnostics.
Used by: preset diagnostics and widget render-state resolution.
Tests: `tests/test_icons.py`.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from datetime import date
from hashlib import sha256
from pathlib import Path
from typing import Any

_PACKAGE_ROOT = Path(__file__).resolve().parents[2]
_ICON_DIR = _PACKAGE_ROOT / "icons"
_MANIFEST_PATH = _ICON_DIR / "manifest.json"
_REQUIRED_FIELDS = ("id", "source", "license", "url", "imported_at", "path")
_ICON_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
_SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9_-]+")
_EXTERNAL_REF_RE = re.compile(r"^\s*(?:https?:|file:|//|data:)", re.IGNORECASE)
_EXTERNAL_STYLE_RE = re.compile(
    r"(?:@import|url\(\s*['\"]?(?:https?:|file:|//|data:))",
    re.IGNORECASE,
)
_FALLBACK_SCALES = (1, 2, 3)
_FALLBACK_BASE_SIZE = 24
_FALLBACKS_FIELD = "fallbacks"
_FALLBACK_HASH_FIELD = "fallback_source_sha256"
_FALLBACK_SIZE_FIELD = "fallback_base_size"
_PngRenderer = Callable[[Path, Path, int], None]

__all__ = [
    "IconFallbackResult",
    "IconImportResult",
    "IconManifestIssue",
    "IconStatus",
    "generate_png_fallbacks",
    "icon_status",
    "import_svg_icon",
    "resolve_icon_path",
    "validate_svg_icon_import",
    "validate_icon_manifest",
]


@dataclass(frozen=True)
class IconManifestIssue:
    """One manifest or asset problem found while validating icon metadata."""

    code: str
    message: str
    icon_id: str = ""
    path: str = ""
    field: str = ""

    def as_dict(self) -> dict[str, str]:
        payload = {
            "code": self.code,
            "message": self.message,
            "icon_id": self.icon_id,
            "path": self.path,
            "field": self.field,
        }
        return {key: value for key, value in payload.items() if value}


@dataclass(frozen=True)
class IconStatus:
    """Resolved state for one icon id."""

    icon_id: str
    path: Path | None = None
    issue: IconManifestIssue | None = None

    @property
    def ok(self) -> bool:
        return self.path is not None and self.issue is None


@dataclass(frozen=True)
class IconImportResult:
    """Result from importing a local SVG into the ActionRail icon manifest."""

    icon_id: str
    path: Path
    manifest_path: Path
    manifest_entry: dict[str, Any]
    replaced_existing: bool = False
    fallback_paths: tuple[Path, ...] = ()


@dataclass(frozen=True)
class IconFallbackResult:
    """Result from generating PNG fallback assets for a manifest icon."""

    icon_id: str
    source_path: Path
    fallback_paths: tuple[Path, ...]
    manifest_path: Path
    manifest_entry: dict[str, Any]


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
    png_renderer: _PngRenderer | None = None,
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
    )
    if import_issues:
        raise ValueError(import_issues[0].message)

    source_file = Path(source_path)
    payload = _manifest_payload_for_update()
    entries = payload["icons"]
    existing = [entry for entry in entries if entry.get("id") == icon_id]

    raw_manifest_path = (
        target_path
        or _existing_icon_path(existing)
        or _default_import_manifest_path(icon_id)
    )
    icon_path = _resolve_import_target(raw_manifest_path)
    manifest_path = _manifest_path_for_icon_path(icon_path)

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
        rollback_paths.extend(_fallback_paths_for_manifest_entry(manifest_entry))
    snapshots = _snapshot_files(rollback_paths)

    try:
        _upsert_manifest_entry(entries, manifest_entry)
        icon_path.parent.mkdir(parents=True, exist_ok=True)
        icon_path.write_text(source_file.read_text(encoding="utf-8"), encoding="utf-8")
        if generate_fallbacks:
            fallback_paths = _generate_png_fallbacks_for_entry(
                manifest_entry,
                icon_path,
                png_renderer=png_renderer,
            )
    except Exception:
        _restore_file_snapshots(snapshots)
        raise

    _write_manifest_payload(payload)

    return IconImportResult(
        icon_id=icon_id,
        path=icon_path,
        manifest_path=_MANIFEST_PATH,
        manifest_entry=manifest_entry,
        replaced_existing=bool(existing),
        fallback_paths=fallback_paths,
    )


def generate_png_fallbacks(
    icon_id: str,
    *,
    png_renderer: _PngRenderer | None = None,
) -> IconFallbackResult:
    """Generate 1x/2x/3x PNG fallbacks for an existing manifest SVG icon."""

    payload = _manifest_payload_for_update()
    entries = payload["icons"]
    entry = next((entry for entry in entries if entry.get("id") == icon_id), None)
    if entry is None:
        msg = f"Icon id '{icon_id}' is not listed in the ActionRail icon manifest."
        raise ValueError(msg)

    entry_issue = _entry_issue(entry)
    if entry_issue is not None:
        raise ValueError(entry_issue.message)

    raw_path = entry["path"]
    icon_path = _resolve_manifest_path(raw_path)
    asset_issue = _asset_issue(icon_id, raw_path, icon_path)
    if asset_issue is not None:
        raise ValueError(asset_issue.message)
    if icon_path.suffix.lower() != ".svg":
        msg = f"Icon '{icon_id}' must point to an SVG source to generate PNG fallbacks."
        raise ValueError(msg)

    manifest_entry = dict(entry)
    snapshots = _snapshot_files(_fallback_paths_for_manifest_entry(manifest_entry))
    try:
        fallback_paths = _generate_png_fallbacks_for_entry(
            manifest_entry,
            icon_path,
            png_renderer=png_renderer,
        )
    except Exception:
        _restore_file_snapshots(snapshots)
        raise
    _upsert_manifest_entry(entries, manifest_entry)
    _write_manifest_payload(payload)
    return IconFallbackResult(
        icon_id=icon_id,
        source_path=icon_path,
        fallback_paths=fallback_paths,
        manifest_path=_MANIFEST_PATH,
        manifest_entry=manifest_entry,
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
            )
        )
    elif source_file.suffix.lower() != ".svg":
        issues.append(
            IconManifestIssue(
                code="invalid_icon_import_source",
                message="ActionRail only imports SVG icon sources.",
                icon_id=icon_id,
                path=str(source_file),
            )
        )

    metadata_issue = _import_metadata_issue(
        icon_id=icon_id,
        source=source,
        license_name=license_name,
        url=url,
        imported_at=imported_at,
    )
    if metadata_issue is not None:
        issues.append(metadata_issue)

    if source_file.is_file() and source_file.suffix.lower() == ".svg":
        svg_issue = _svg_issue(icon_id, str(source_file), source_file)
        if svg_issue is not None:
            issues.append(svg_issue)

    try:
        payload = _manifest_payload_for_update()
    except ValueError as exc:
        issues.append(
            IconManifestIssue(
                code="invalid_icon_manifest",
                message=str(exc),
                icon_id=icon_id,
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
            )
        )

    raw_manifest_path = (
        target_path
        or _existing_icon_path(existing)
        or _default_import_manifest_path(icon_id)
    )
    try:
        icon_path = _resolve_import_target(raw_manifest_path)
    except ValueError as exc:
        issues.append(
            IconManifestIssue(
                code="invalid_icon_import_target",
                message=str(exc),
                icon_id=icon_id,
                path=raw_manifest_path,
            )
        )
        return tuple(issues)

    conflicting_path = [
        entry
        for entry in entries
        if entry.get("id") != icon_id
        and _manifest_entry_icon_path(entry) == icon_path.resolve(strict=False)
    ]
    if conflicting_path:
        other_id = conflicting_path[0].get("id", "<unknown>")
        manifest_path = _manifest_path_for_icon_path(icon_path)
        issues.append(
            IconManifestIssue(
                code="icon_path_conflict",
                message=(
                    f"Icon path '{manifest_path}' is already used by icon "
                    f"'{other_id}'."
                ),
                icon_id=icon_id,
                path=manifest_path,
            )
        )
    if icon_path.exists() and not overwrite and not existing:
        issues.append(
            IconManifestIssue(
                code="icon_target_exists",
                message=f"Icon target already exists: {icon_path}",
                icon_id=icon_id,
                path=_manifest_path_for_icon_path(icon_path),
            )
        )

    return tuple(issues)


def resolve_icon_path(icon_id: str) -> Path | None:
    """Return a safe local path for a manifest icon id if it exists on disk."""

    return icon_status(icon_id).path


def icon_status(icon_id: str) -> IconStatus:
    """Return the resolved path or first diagnostic issue for one icon id."""

    if not icon_id:
        return IconStatus(icon_id)

    entries = _manifest_icons()
    for issue in _manifest_shape_issues(entries):
        return IconStatus(icon_id, issue=issue)

    for entry in entries:
        if entry.get("id") != icon_id:
            continue

        entry_issue = _entry_issue(entry)
        if entry_issue is not None:
            return IconStatus(icon_id, issue=entry_issue)

        raw_path = entry["path"]
        icon_path = _resolve_manifest_path(raw_path)
        asset_issue = _asset_issue(icon_id, raw_path, icon_path)
        if asset_issue is not None:
            return IconStatus(icon_id, issue=asset_issue)
        return IconStatus(icon_id, path=icon_path)

    return IconStatus(
        icon_id,
        issue=IconManifestIssue(
            code="missing_icon",
            message=f"Icon '{icon_id}' is not listed in the ActionRail icon manifest.",
            icon_id=icon_id,
        ),
    )


def validate_icon_manifest(*, require_fallbacks: bool = True) -> tuple[IconManifestIssue, ...]:
    """Validate icon manifest metadata and local assets."""

    entries = _manifest_icons()
    issues = list(_manifest_shape_issues(entries))
    if issues:
        return tuple(issues)

    seen: set[str] = set()
    for entry in entries:
        entry_issue = _entry_issue(entry)
        if entry_issue is not None:
            issues.append(entry_issue)
            continue

        icon_id = entry["id"]
        if icon_id in seen:
            issues.append(
                IconManifestIssue(
                    code="duplicate_icon",
                    message=f"Icon id '{icon_id}' is listed more than once.",
                    icon_id=icon_id,
                )
            )
            continue
        seen.add(icon_id)

        raw_path = entry["path"]
        asset_issue = _asset_issue(icon_id, raw_path, _resolve_manifest_path(raw_path))
        if asset_issue is not None:
            issues.append(asset_issue)
            continue

        issues.extend(_fallback_issues(entry, require_fallbacks=require_fallbacks))

    return tuple(issues)


def _manifest_icons() -> tuple[dict[str, Any], ...]:
    try:
        with _MANIFEST_PATH.open("r", encoding="utf-8") as stream:
            payload = json.load(stream)
    except FileNotFoundError:
        return ({"__manifest_error__": "missing"},)
    except Exception as exc:
        return ({"__manifest_error__": type(exc).__name__},)

    icons = payload.get("icons") if isinstance(payload, dict) else None
    if not isinstance(icons, list):
        return ({"__manifest_error__": "invalid_shape"},)

    return tuple(
        entry if isinstance(entry, dict) else {"__manifest_error__": "invalid_entry"}
        for entry in icons
    )


def _manifest_payload_for_update() -> dict[str, Any]:
    if not _MANIFEST_PATH.exists():
        return {"icons": []}

    try:
        with _MANIFEST_PATH.open("r", encoding="utf-8") as stream:
            payload = json.load(stream)
    except json.JSONDecodeError as exc:
        msg = f"ActionRail icon manifest is invalid JSON: {_MANIFEST_PATH}"
        raise ValueError(msg) from exc

    icons = payload.get("icons") if isinstance(payload, dict) else None
    if not isinstance(icons, list) or not all(isinstance(entry, dict) for entry in icons):
        msg = "ActionRail icon manifest must be an object with an icons list before importing."
        raise ValueError(msg)
    return payload


def _write_manifest_payload(payload: dict[str, Any]) -> None:
    _MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    _MANIFEST_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _upsert_manifest_entry(entries: list[dict[str, Any]], manifest_entry: dict[str, str]) -> None:
    insert_index: int | None = None
    icon_id = manifest_entry["id"]
    retained: list[dict[str, Any]] = []
    for entry in entries:
        if entry.get("id") == icon_id:
            if insert_index is None:
                insert_index = len(retained)
            continue
        retained.append(entry)

    if insert_index is None:
        retained.append(manifest_entry)
    else:
        retained.insert(insert_index, manifest_entry)
    entries[:] = retained


def _existing_icon_path(entries: list[dict[str, Any]]) -> str:
    if not entries:
        return ""
    path = entries[0].get("path")
    return path if isinstance(path, str) else ""


def _manifest_entry_icon_path(entry: dict[str, Any]) -> Path | None:
    raw_path = entry.get("path")
    if not isinstance(raw_path, str) or not raw_path:
        return None

    manifest_path = Path(raw_path)
    if manifest_path.is_absolute() or ".." in manifest_path.parts:
        return None
    return _resolve_manifest_path(raw_path).resolve(strict=False)


def _manifest_shape_issues(entries: tuple[dict[str, Any], ...]) -> tuple[IconManifestIssue, ...]:
    issues: list[IconManifestIssue] = []
    for entry in entries:
        error = entry.get("__manifest_error__")
        if not error:
            continue

        code = "invalid_icon_manifest"
        message = "ActionRail icon manifest is invalid."
        if error == "missing":
            code = "missing_icon_manifest"
            message = "ActionRail icon manifest is missing."
        elif error == "invalid_entry":
            message = "ActionRail icon manifest entries must be objects."
        else:
            message = f"ActionRail icon manifest is invalid: {error}."
        issues.append(IconManifestIssue(code=code, message=message))
    return tuple(issues)


def _entry_issue(entry: dict[str, Any]) -> IconManifestIssue | None:
    icon_id = entry.get("id") if isinstance(entry.get("id"), str) else ""
    for field in _REQUIRED_FIELDS:
        value = entry.get(field)
        if not isinstance(value, str) or not value:
            return IconManifestIssue(
                code="invalid_icon_manifest",
                message=f"Icon manifest entry field '{field}' must be a non-empty string.",
                icon_id=icon_id,
                field=field,
            )
    return None


def _asset_issue(icon_id: str, raw_path: str, icon_path: Path) -> IconManifestIssue | None:
    manifest_path = Path(raw_path)
    if manifest_path.is_absolute() or ".." in manifest_path.parts:
        return IconManifestIssue(
            code="invalid_icon_path",
            message=f"Icon '{icon_id}' path must stay inside the ActionRail icons directory.",
            icon_id=icon_id,
            path=raw_path,
        )

    if not icon_path.is_file():
        return IconManifestIssue(
            code="missing_icon_file",
            message=f"Icon '{icon_id}' points to a missing file: {raw_path}.",
            icon_id=icon_id,
            path=raw_path,
        )

    if icon_path.suffix.lower() == ".svg":
        return _svg_issue(icon_id, raw_path, icon_path)
    return None


def _fallback_issues(
    entry: dict[str, Any],
    *,
    require_fallbacks: bool,
) -> tuple[IconManifestIssue, ...]:
    raw_path = entry.get("path")
    icon_id = entry.get("id") if isinstance(entry.get("id"), str) else ""
    if not isinstance(raw_path, str) or _resolve_manifest_path(raw_path).suffix.lower() != ".svg":
        return ()

    fallbacks = entry.get(_FALLBACKS_FIELD)
    if fallbacks is None:
        if not require_fallbacks:
            return ()
        return (
            IconManifestIssue(
                code="missing_icon_fallbacks",
                message=f"Icon '{icon_id}' does not list generated PNG fallbacks.",
                icon_id=icon_id,
                path=raw_path,
                field=_FALLBACKS_FIELD,
            ),
        )

    if not isinstance(fallbacks, dict):
        return (
            IconManifestIssue(
                code="invalid_icon_fallbacks",
                message=f"Icon '{icon_id}' fallback metadata must be an object.",
                icon_id=icon_id,
                path=raw_path,
                field=_FALLBACKS_FIELD,
            ),
        )

    issues: list[IconManifestIssue] = []
    for scale in _FALLBACK_SCALES:
        label = f"{scale}x"
        fallback_path = fallbacks.get(label)
        if not isinstance(fallback_path, str) or not fallback_path:
            issues.append(
                IconManifestIssue(
                    code="missing_icon_fallback",
                    message=f"Icon '{icon_id}' is missing its {label} PNG fallback path.",
                    icon_id=icon_id,
                    path=raw_path,
                    field=f"{_FALLBACKS_FIELD}.{label}",
                )
            )
            continue

        fallback_issue = _fallback_path_issue(icon_id, fallback_path)
        if fallback_issue is not None:
            issues.append(fallback_issue)

    recorded_hash = entry.get(_FALLBACK_HASH_FIELD)
    current_hash = _file_sha256(_resolve_manifest_path(raw_path))
    if not isinstance(recorded_hash, str) or not recorded_hash:
        issues.append(
            IconManifestIssue(
                code="missing_icon_fallback_hash",
                message=f"Icon '{icon_id}' does not record a fallback source hash.",
                icon_id=icon_id,
                path=raw_path,
                field=_FALLBACK_HASH_FIELD,
            )
        )
    elif recorded_hash != current_hash:
        issues.append(
            IconManifestIssue(
                code="stale_icon_fallback",
                message=f"Icon '{icon_id}' PNG fallbacks are stale for source SVG: {raw_path}.",
                icon_id=icon_id,
                path=raw_path,
                field=_FALLBACK_HASH_FIELD,
            )
        )

    recorded_size = entry.get(_FALLBACK_SIZE_FIELD)
    if not isinstance(recorded_size, int) or recorded_size <= 0:
        issues.append(
            IconManifestIssue(
                code="invalid_icon_fallback_size",
                message=f"Icon '{icon_id}' fallback base size must be a positive integer.",
                icon_id=icon_id,
                path=raw_path,
                field=_FALLBACK_SIZE_FIELD,
            )
        )

    return tuple(issues)


def _fallback_path_issue(icon_id: str, raw_path: str) -> IconManifestIssue | None:
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
        )
    if manifest_path.suffix.lower() != ".png":
        return IconManifestIssue(
            code="invalid_icon_fallback_path",
            message=f"Icon '{icon_id}' fallback path must use the .png extension.",
            icon_id=icon_id,
            path=raw_path,
        )

    fallback_path = _resolve_manifest_path(raw_path)
    if not fallback_path.is_file():
        return IconManifestIssue(
            code="missing_icon_fallback_file",
            message=f"Icon '{icon_id}' points to a missing PNG fallback: {raw_path}.",
            icon_id=icon_id,
            path=raw_path,
        )
    return None


def _svg_issue(icon_id: str, raw_path: str, icon_path: Path) -> IconManifestIssue | None:
    try:
        root = ET.fromstring(icon_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return IconManifestIssue(
            code="invalid_icon_svg",
            message=f"Icon '{icon_id}' SVG could not be parsed: {exc}.",
            icon_id=icon_id,
            path=raw_path,
        )

    if _local_name(root.tag) != "svg" or not root.attrib.get("viewBox"):
        return IconManifestIssue(
            code="invalid_icon_svg",
            message=f"Icon '{icon_id}' SVG must have an <svg> root and viewBox.",
            icon_id=icon_id,
            path=raw_path,
        )

    for element in root.iter():
        name = _local_name(element.tag)
        if name in {"script", "foreignObject"}:
            return _unsafe_svg_issue(icon_id, raw_path, f"disallowed <{name}> element")
        if name == "style" and _EXTERNAL_STYLE_RE.search("".join(element.itertext())):
            return _unsafe_svg_issue(icon_id, raw_path, "external stylesheet reference")
        for attr_name, attr_value in element.attrib.items():
            attr = _local_name(attr_name)
            if attr.lower().startswith("on"):
                return _unsafe_svg_issue(icon_id, raw_path, f"event handler '{attr}'")
            if attr in {"href", "src"} and _EXTERNAL_REF_RE.search(attr_value):
                return _unsafe_svg_issue(icon_id, raw_path, f"external reference '{attr_value}'")
            if isinstance(attr_value, str) and _EXTERNAL_STYLE_RE.search(attr_value):
                return _unsafe_svg_issue(icon_id, raw_path, "external stylesheet reference")
    return None


def _unsafe_svg_issue(icon_id: str, raw_path: str, reason: str) -> IconManifestIssue:
    return IconManifestIssue(
        code="unsafe_icon_svg",
        message=f"Icon '{icon_id}' SVG is unsafe: {reason}.",
        icon_id=icon_id,
        path=raw_path,
    )


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _validate_import_metadata(
    *,
    icon_id: str,
    source: str,
    license_name: str,
    url: str,
    imported_at: str | None,
) -> None:
    issue = _import_metadata_issue(
        icon_id=icon_id,
        source=source,
        license_name=license_name,
        url=url,
        imported_at=imported_at,
    )
    if issue is not None:
        raise ValueError(issue.message)


def _import_metadata_issue(
    *,
    icon_id: str,
    source: str,
    license_name: str,
    url: str,
    imported_at: str | None,
) -> IconManifestIssue | None:
    if not isinstance(icon_id, str) or not _ICON_ID_RE.fullmatch(icon_id):
        return IconManifestIssue(
            code="invalid_icon_import_metadata",
            message="Icon id must use letters, numbers, dots, underscores, or hyphens.",
            icon_id=icon_id if isinstance(icon_id, str) else "",
            field="icon_id",
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
            )
    if imported_at is not None and (not isinstance(imported_at, str) or not imported_at):
        return IconManifestIssue(
            code="invalid_icon_import_metadata",
            message="Icon import field 'imported_at' must be a non-empty string when provided.",
            icon_id=icon_id,
            field="imported_at",
        )
    return None


def _default_import_manifest_path(icon_id: str) -> str:
    parts = icon_id.split(".")
    namespace = _safe_filename(parts[0] if len(parts) > 1 else "custom")
    filename = _safe_filename("-".join(parts[1:]) if len(parts) > 1 else parts[0])
    return f"icons/{namespace}/{filename}.svg"


def _safe_filename(value: str) -> str:
    safe = _SAFE_FILENAME_RE.sub("-", value).strip("-")
    return safe or "icon"


def _resolve_import_target(raw_path: str) -> Path:
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

    icon_path = _resolve_manifest_path(raw_path)
    try:
        icon_path.resolve(strict=False).relative_to(_ICON_DIR.resolve(strict=False))
    except ValueError as exc:
        msg = "Icon import target path must resolve inside the ActionRail icons directory."
        raise ValueError(msg) from exc
    return icon_path


def _manifest_path_for_icon_path(icon_path: Path) -> str:
    relative_path = icon_path.resolve(strict=False).relative_to(_ICON_DIR.resolve(strict=False))
    return Path("icons", relative_path).as_posix()


def _resolve_manifest_path(raw_path: str) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path

    if path.parts and path.parts[0] == "icons":
        return _PACKAGE_ROOT / path

    return _ICON_DIR / path


def _generate_png_fallbacks_for_entry(
    manifest_entry: dict[str, Any],
    icon_path: Path,
    *,
    png_renderer: _PngRenderer | None,
) -> tuple[Path, ...]:
    fallback_paths: list[Path] = []
    fallback_manifest_paths: dict[str, str] = {}
    for scale in _FALLBACK_SCALES:
        fallback_manifest_path = _fallback_manifest_path(manifest_entry["path"], scale)
        fallback_path = _resolve_manifest_path(fallback_manifest_path)
        fallback_path.parent.mkdir(parents=True, exist_ok=True)
        _render_png(icon_path, fallback_path, _FALLBACK_BASE_SIZE * scale, png_renderer)
        fallback_paths.append(fallback_path)
        fallback_manifest_paths[f"{scale}x"] = fallback_manifest_path

    manifest_entry[_FALLBACKS_FIELD] = fallback_manifest_paths
    manifest_entry[_FALLBACK_HASH_FIELD] = _file_sha256(icon_path)
    manifest_entry[_FALLBACK_SIZE_FIELD] = _FALLBACK_BASE_SIZE
    return tuple(fallback_paths)


def _fallback_paths_for_manifest_entry(manifest_entry: dict[str, Any]) -> tuple[Path, ...]:
    return tuple(
        _resolve_manifest_path(_fallback_manifest_path(manifest_entry["path"], scale))
        for scale in _FALLBACK_SCALES
    )


def _snapshot_files(paths: list[Path] | tuple[Path, ...]) -> dict[Path, bytes | None]:
    snapshots: dict[Path, bytes | None] = {}
    for path in paths:
        key = path.resolve(strict=False)
        if key in snapshots:
            continue
        snapshots[key] = key.read_bytes() if key.is_file() else None
    return snapshots


def _restore_file_snapshots(snapshots: dict[Path, bytes | None]) -> None:
    for path, contents in snapshots.items():
        if contents is None:
            with suppress(FileNotFoundError):
                path.unlink()
            continue

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(contents)


def _fallback_manifest_path(raw_svg_path: str, scale: int) -> str:
    source_path = Path(raw_svg_path)
    suffix = f"@{scale}x.png"
    if source_path.suffix:
        return source_path.with_name(f"{source_path.stem}{suffix}").as_posix()
    return source_path.with_name(f"{source_path.name}{suffix}").as_posix()


def _render_png(
    svg_path: Path,
    png_path: Path,
    size_px: int,
    png_renderer: _PngRenderer | None,
) -> None:
    if png_renderer is not None:
        png_renderer(svg_path, png_path, size_px)
        return

    try:
        _render_png_with_mayapy(svg_path, png_path, size_px)
    except Exception as exc:
        msg = f"Unable to generate PNG fallback assets with mayapy: {exc}"
        raise RuntimeError(msg) from exc


def _render_png_with_mayapy(svg_path: Path, png_path: Path, size_px: int) -> None:
    mayapy = next(iter(_mayapy_candidates()), "")
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


def _mayapy_candidates() -> tuple[str, ...]:
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

def _file_sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()
