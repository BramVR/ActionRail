"""Icon manifest lookup and validation helpers for ActionRail presets."""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date
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


@dataclass(frozen=True)
class IconImportResult:
    """Result from importing a local SVG into the ActionRail icon manifest."""

    icon_id: str
    path: Path
    manifest_path: Path
    manifest_entry: dict[str, str]
    replaced_existing: bool = False


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
) -> IconImportResult:
    """Import a safe local SVG and record its source metadata in the manifest."""

    source_file = Path(source_path)
    if not source_file.is_file():
        msg = f"SVG icon source does not exist: {source_file}"
        raise ValueError(msg)
    if source_file.suffix.lower() != ".svg":
        msg = "ActionRail only imports SVG icon sources."
        raise ValueError(msg)

    _validate_import_metadata(
        icon_id=icon_id,
        source=source,
        license_name=license_name,
        url=url,
        imported_at=imported_at,
    )
    svg_issue = _svg_issue(icon_id, str(source_file), source_file)
    if svg_issue is not None:
        raise ValueError(svg_issue.message)

    payload = _manifest_payload_for_update()
    entries = payload["icons"]
    existing = [entry for entry in entries if entry.get("id") == icon_id]
    if existing and not overwrite:
        msg = f"Icon id '{icon_id}' already exists in the ActionRail icon manifest."
        raise ValueError(msg)

    raw_manifest_path = (
        target_path
        or _existing_icon_path(existing)
        or _default_import_manifest_path(icon_id)
    )
    icon_path = _resolve_import_target(raw_manifest_path)
    manifest_path = _manifest_path_for_icon_path(icon_path)
    conflicting_path = [
        entry
        for entry in entries
        if entry.get("path") == manifest_path and entry.get("id") != icon_id
    ]
    if conflicting_path:
        other_id = conflicting_path[0].get("id", "<unknown>")
        msg = f"Icon path '{manifest_path}' is already used by icon '{other_id}'."
        raise ValueError(msg)
    if icon_path.exists() and not overwrite and not existing:
        msg = f"Icon target already exists: {icon_path}"
        raise ValueError(msg)

    manifest_entry = {
        "id": icon_id,
        "source": source,
        "license": license_name,
        "url": url,
        "imported_at": imported_at or date.today().isoformat(),
        "path": manifest_path,
    }
    _upsert_manifest_entry(entries, manifest_entry)

    icon_path.parent.mkdir(parents=True, exist_ok=True)
    icon_path.write_text(source_file.read_text(encoding="utf-8"), encoding="utf-8")
    _write_manifest_payload(payload)

    return IconImportResult(
        icon_id=icon_id,
        path=icon_path,
        manifest_path=_MANIFEST_PATH,
        manifest_entry=manifest_entry,
        replaced_existing=bool(existing),
    )


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


def _validate_import_metadata(
    *,
    icon_id: str,
    source: str,
    license_name: str,
    url: str,
    imported_at: str | None,
) -> None:
    if not isinstance(icon_id, str) or not _ICON_ID_RE.fullmatch(icon_id):
        msg = "Icon id must use letters, numbers, dots, underscores, or hyphens."
        raise ValueError(msg)
    for field, value in (
        ("source", source),
        ("license_name", license_name),
        ("url", url),
    ):
        if not isinstance(value, str) or not value:
            msg = f"Icon import field '{field}' must be a non-empty string."
            raise ValueError(msg)
    if imported_at is not None and (not isinstance(imported_at, str) or not imported_at):
        msg = "Icon import field 'imported_at' must be a non-empty string when provided."
        raise ValueError(msg)


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
