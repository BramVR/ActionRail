"""Shared icon path and manifest-location helpers.

Purpose: centralize package-relative icon storage paths so catalog, manifest,
import, and fallback modules do not depend on each other for filesystem
normalization.
Used by: icon manifest, import pipeline, fallback generation, and catalog.
Tests: ``tests/test_icons.py``.
"""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[2]
ICON_DIR = PACKAGE_ROOT / "icons"
MANIFEST_PATH = ICON_DIR / "manifest.json"


def manifest_path_for_icon_path(icon_path: Path) -> str:
    relative_path = icon_path.resolve(strict=False).relative_to(ICON_DIR.resolve(strict=False))
    return Path("icons", relative_path).as_posix()


def resolve_manifest_path(raw_path: str) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path

    if path.parts and path.parts[0] == "icons":
        return PACKAGE_ROOT / path

    return ICON_DIR / path


def file_sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()
