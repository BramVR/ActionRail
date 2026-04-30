"""Icon manifest lookup and validation helpers for ActionRail presets."""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_PACKAGE_ROOT = Path(__file__).resolve().parents[2]
_ICON_DIR = _PACKAGE_ROOT / "icons"
_MANIFEST_PATH = _ICON_DIR / "manifest.json"
_REQUIRED_FIELDS = ("id", "source", "license", "url", "imported_at", "path")
_EXTERNAL_REF_RE = re.compile(r"^\s*(?:https?:|file:|//|data:)", re.IGNORECASE)
_EXTERNAL_STYLE_RE = re.compile(
    r"(?:@import|url\(\s*['\"]?(?:https?:|file:|//|data:))",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class IconManifestIssue:
    """One manifest or asset problem found while validating icon metadata."""

    code: str
    message: str
    icon_id: str = ""
    path: str = ""
    field: str = ""


@dataclass(frozen=True)
class IconStatus:
    """Resolved state for one icon id."""

    icon_id: str
    path: Path | None = None
    issue: IconManifestIssue | None = None

    @property
    def ok(self) -> bool:
        return self.path is not None and self.issue is None


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


def validate_icon_manifest() -> tuple[IconManifestIssue, ...]:
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


def _resolve_manifest_path(raw_path: str) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path

    if path.parts and path.parts[0] == "icons":
        return _PACKAGE_ROOT / path

    return _ICON_DIR / path
