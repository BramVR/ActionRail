"""Icon manifest lookup helpers for ActionRail presets."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_PACKAGE_ROOT = Path(__file__).resolve().parents[2]
_ICON_DIR = _PACKAGE_ROOT / "icons"
_MANIFEST_PATH = _ICON_DIR / "manifest.json"


def resolve_icon_path(icon_id: str) -> Path | None:
    """Return the local path for a manifest icon id if it exists on disk."""

    if not icon_id:
        return None

    for entry in _manifest_icons():
        if entry.get("id") != icon_id:
            continue

        raw_path = entry.get("path")
        if not isinstance(raw_path, str) or not raw_path:
            return None

        icon_path = _resolve_manifest_path(raw_path)
        return icon_path if icon_path.is_file() else None

    return None


def _manifest_icons() -> tuple[dict[str, Any], ...]:
    try:
        with _MANIFEST_PATH.open("r", encoding="utf-8") as stream:
            payload = json.load(stream)
    except Exception:
        return ()

    icons = payload.get("icons") if isinstance(payload, dict) else None
    if not isinstance(icons, list):
        return ()

    return tuple(entry for entry in icons if isinstance(entry, dict))


def _resolve_manifest_path(raw_path: str) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path

    if path.parts and path.parts[0] == "icons":
        return _PACKAGE_ROOT / path

    return _ICON_DIR / path
