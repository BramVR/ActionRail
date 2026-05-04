"""Shared icon value objects.

Purpose: keep icon subsystem data contracts independent from catalog,
manifest, import, and fallback implementation details.
Used by: icon catalog, manifest validation, import pipeline, diagnostics,
and the public ``actionrail.icons`` compatibility facade.
Tests: ``tests/test_icons.py``.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PngRenderer = Callable[[Path, Path, int], None]


@dataclass(frozen=True)
class IconDescriptor:
    """Picker-facing metadata for an available icon choice."""

    id: str
    provider: str
    label: str
    category: str = ""
    keywords: tuple[str, ...] = ()
    path: Path | None = None
    qt_name: str = ""
    source: str = ""
    license: str = ""
    url: str = ""

    def as_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "id": self.id,
            "provider": self.provider,
            "label": self.label,
            "category": self.category,
            "keywords": self.keywords,
            "path": str(self.path) if self.path is not None else "",
            "qt_name": self.qt_name,
            "source": self.source,
            "license": self.license,
            "url": self.url,
        }
        return {key: value for key, value in payload.items() if value}


@dataclass(frozen=True)
class IconManifestIssue:
    """One manifest or asset problem found while validating icon metadata."""

    code: str
    message: str
    icon_id: str = ""
    path: str = ""
    field: str = ""
    hint: str = ""

    def as_dict(self) -> dict[str, str]:
        payload = {
            "code": self.code,
            "message": self.message,
            "icon_id": self.icon_id,
            "path": self.path,
            "field": self.field,
            "hint": self.hint,
        }
        return {key: value for key, value in payload.items() if value}


@dataclass(frozen=True)
class IconStatus:
    """Resolved state for one icon id."""

    icon_id: str
    path: Path | None = None
    qt_name: str = ""
    provider: str = ""
    issue: IconManifestIssue | None = None

    @property
    def ok(self) -> bool:
        return (self.path is not None or bool(self.qt_name)) and self.issue is None


@dataclass(frozen=True)
class IconImportResult:
    """Result from importing a local SVG into an ActionRail icon manifest."""

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
