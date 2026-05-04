"""Public icon compatibility facade.

Purpose: preserve the historical ``actionrail.icons`` API while the icon
subsystem is split into picker catalog, manifest validation, import pipeline,
SVG safety, and fallback rendering modules.
Used by: public callers, diagnostics, slot render-state resolution, and tests.
Implementation owners:
- ``icon_catalog``: provider descriptors and read-only icon lookup.
- ``icon_manifest``: manifest store and validation.
- ``icon_import``: SVG import preflight and writes.
- ``icon_fallbacks``: PNG fallback generation and mayapy rendering.
- ``icon_svg``: SVG safety checks.
Tests: ``tests/test_icons.py``.
"""

from __future__ import annotations

from . import icon_catalog, icon_fallbacks, icon_import, icon_manifest, icon_paths, icon_svg
from .icon_catalog import icon_status, list_icon_descriptors, resolve_icon_name, resolve_icon_path
from .icon_fallbacks import generate_png_fallbacks
from .icon_import import import_svg_icon, validate_svg_icon_import
from .icon_manifest import validate_icon_manifest
from .icon_types import (
    IconDescriptor,
    IconFallbackResult,
    IconImportResult,
    IconManifestIssue,
    IconStatus,
)

__all__ = [
    "IconDescriptor",
    "IconFallbackResult",
    "IconImportResult",
    "IconManifestIssue",
    "IconStatus",
    "generate_png_fallbacks",
    "icon_status",
    "import_svg_icon",
    "list_icon_descriptors",
    "resolve_icon_name",
    "resolve_icon_path",
    "validate_svg_icon_import",
    "validate_icon_manifest",
]

# Private compatibility aliases for existing tests and developer scripts. New
# code should import from the narrower implementation modules directly.
_PACKAGE_ROOT = icon_paths.PACKAGE_ROOT
_ICON_DIR = icon_paths.ICON_DIR
_MANIFEST_PATH = icon_paths.MANIFEST_PATH
_REQUIRED_FIELDS = icon_manifest.REQUIRED_FIELDS
_ICON_ID_RE = icon_import.ICON_ID_RE
_SAFE_FILENAME_RE = icon_import.SAFE_FILENAME_RE
_EXTERNAL_REF_RE = icon_svg._EXTERNAL_REF_RE
_EXTERNAL_STYLE_RE = icon_svg._EXTERNAL_STYLE_RE
_FALLBACK_SCALES = icon_fallbacks.FALLBACK_SCALES
_FALLBACK_BASE_SIZE = icon_fallbacks.FALLBACK_BASE_SIZE
_FALLBACKS_FIELD = icon_fallbacks.FALLBACKS_FIELD
_FALLBACK_HASH_FIELD = icon_fallbacks.FALLBACK_HASH_FIELD
_FALLBACK_SIZE_FIELD = icon_fallbacks.FALLBACK_SIZE_FIELD

_maya_icon_descriptor = icon_catalog._maya_icon_descriptor
_MAYA_ICON_DESCRIPTORS = icon_catalog.MAYA_ICON_DESCRIPTORS
_MAYA_ICON_BY_ID = icon_catalog.MAYA_ICON_BY_ID
_maya_icon_status = icon_catalog.maya_icon_status
_maya_resource_exists = icon_catalog.maya_resource_exists
_string_values = icon_catalog.string_values
_manifest_icon_descriptors = icon_catalog.manifest_icon_descriptors
_label_from_icon_id = icon_catalog.label_from_icon_id
_keywords_from_icon_id = icon_catalog.keywords_from_icon_id
_icon_descriptor_sort_key = icon_catalog.icon_descriptor_sort_key

_manifest_icons = icon_manifest.manifest_icons
_manifest_payload_for_update = icon_manifest.manifest_payload_for_update
_write_manifest_payload = icon_manifest.write_manifest_payload
_upsert_manifest_entry = icon_manifest.upsert_manifest_entry
_existing_icon_path = icon_manifest.existing_icon_path
_manifest_entry_icon_path = icon_manifest.manifest_entry_icon_path
_manifest_shape_issues = icon_manifest.manifest_shape_issues
_entry_issue = icon_manifest.entry_issue
_asset_issue = icon_manifest.asset_issue

_fallback_issues = icon_fallbacks.fallback_issues
_fallback_path_issue = icon_fallbacks.fallback_path_issue
_fallback_import_target_issues = icon_fallbacks.fallback_import_target_issues
_fallback_manifest_path_owner = icon_fallbacks.fallback_manifest_path_owner
_fallback_regeneration_hint = icon_fallbacks.fallback_regeneration_hint
_generate_png_fallbacks_for_entry = icon_fallbacks.generate_png_fallbacks_for_entry
_fallback_paths_for_manifest_entry = icon_fallbacks.fallback_paths_for_manifest_entry
_snapshot_files = icon_fallbacks.snapshot_files
_restore_file_snapshots = icon_fallbacks.restore_file_snapshots
_fallback_manifest_path = icon_fallbacks.fallback_manifest_path_for_svg
_render_png = icon_fallbacks.render_png
_render_png_with_mayapy = icon_fallbacks.render_png_with_mayapy
_mayapy_candidates = icon_fallbacks.mayapy_candidates

_svg_issue = icon_svg.svg_issue
_unsafe_svg_issue = icon_svg.unsafe_svg_issue
_local_name = icon_svg.local_name

_validate_import_metadata = icon_import.validate_import_metadata
_import_metadata_issue = icon_import.import_metadata_issue
_default_import_manifest_path = icon_import.default_import_manifest_path
_safe_filename = icon_import.safe_filename
_resolve_import_target = icon_import.resolve_import_target

_manifest_path_for_icon_path = icon_paths.manifest_path_for_icon_path
_resolve_manifest_path = icon_paths.resolve_manifest_path
_file_sha256 = icon_paths.file_sha256

subprocess = icon_fallbacks.subprocess
shutil = icon_fallbacks.shutil
Path = icon_paths.Path
