"""Icon manifest store and validation.

Purpose: own ``icons/manifest.json`` loading, writing, path normalization, and
metadata/asset validation.
Used by: icon catalog, SVG import pipeline, diagnostics, and the public facade.
Tests: ``tests/test_icons.py``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import icon_fallbacks, icon_paths, icon_svg
from .icon_types import IconManifestIssue

REQUIRED_FIELDS = ("id", "source", "license", "url", "imported_at", "path")


def validate_icon_manifest(*, require_fallbacks: bool = True) -> tuple[IconManifestIssue, ...]:
    """Validate icon manifest metadata and local assets."""

    entries = manifest_icons()
    issues = list(manifest_shape_issues(entries))
    if issues:
        return tuple(issues)

    seen: set[str] = set()
    for entry in entries:
        issue = entry_issue(entry)
        if issue is not None:
            issues.append(issue)
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
        issue = asset_issue(icon_id, raw_path, icon_paths.resolve_manifest_path(raw_path))
        if issue is not None:
            issues.append(issue)
            continue

        issues.extend(icon_fallbacks.fallback_issues(entry, require_fallbacks=require_fallbacks))

    return tuple(issues)


def manifest_icons() -> tuple[dict[str, Any], ...]:
    try:
        with icon_paths.MANIFEST_PATH.open("r", encoding="utf-8") as stream:
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


def manifest_payload_for_update() -> dict[str, Any]:
    if not icon_paths.MANIFEST_PATH.exists():
        return {"icons": []}

    try:
        with icon_paths.MANIFEST_PATH.open("r", encoding="utf-8") as stream:
            payload = json.load(stream)
    except json.JSONDecodeError as exc:
        msg = f"ActionRail icon manifest is invalid JSON: {icon_paths.MANIFEST_PATH}"
        raise ValueError(msg) from exc

    icons = payload.get("icons") if isinstance(payload, dict) else None
    if not isinstance(icons, list) or not all(isinstance(entry, dict) for entry in icons):
        msg = "ActionRail icon manifest must be an object with an icons list before importing."
        raise ValueError(msg)
    return payload


def write_manifest_payload(payload: dict[str, Any]) -> None:
    icon_paths.MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    icon_paths.MANIFEST_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def upsert_manifest_entry(entries: list[dict[str, Any]], manifest_entry: dict[str, str]) -> None:
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


def existing_icon_path(entries: list[dict[str, Any]]) -> str:
    if not entries:
        return ""
    path = entries[0].get("path")
    return path if isinstance(path, str) else ""


def manifest_entry_icon_path(entry: dict[str, Any]) -> Path | None:
    raw_path = entry.get("path")
    if not isinstance(raw_path, str) or not raw_path:
        return None

    manifest_path = Path(raw_path)
    if manifest_path.is_absolute() or ".." in manifest_path.parts:
        return None
    return icon_paths.resolve_manifest_path(raw_path).resolve(strict=False)


def manifest_shape_issues(entries: tuple[dict[str, Any], ...]) -> tuple[IconManifestIssue, ...]:
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
        issues.append(
            IconManifestIssue(
                code=code,
                message=message,
                hint="Restore icons/manifest.json to a valid object with an icons list.",
            )
        )
    return tuple(issues)


def entry_issue(entry: dict[str, Any]) -> IconManifestIssue | None:
    icon_id = entry.get("id") if isinstance(entry.get("id"), str) else ""
    for field in REQUIRED_FIELDS:
        value = entry.get(field)
        if not isinstance(value, str) or not value:
            return IconManifestIssue(
                code="invalid_icon_manifest",
                message=f"Icon manifest entry field '{field}' must be a non-empty string.",
                icon_id=icon_id,
                field=field,
                hint="Fill in the required icon manifest metadata field.",
            )
    return None


def asset_issue(icon_id: str, raw_path: str, icon_path: Path) -> IconManifestIssue | None:
    manifest_path = Path(raw_path)
    if manifest_path.is_absolute() or ".." in manifest_path.parts:
        return IconManifestIssue(
            code="invalid_icon_path",
            message=f"Icon '{icon_id}' path must stay inside the ActionRail icons directory.",
            icon_id=icon_id,
            path=raw_path,
            hint="Use a relative path inside icons/ for this manifest entry.",
        )

    if not icon_path.is_file():
        return IconManifestIssue(
            code="missing_icon_file",
            message=f"Icon '{icon_id}' points to a missing file: {raw_path}.",
            icon_id=icon_id,
            path=raw_path,
            hint="Restore the referenced asset or update the manifest path.",
        )

    if icon_path.suffix.lower() == ".svg":
        return icon_svg.svg_issue(icon_id, raw_path, icon_path)
    return None
