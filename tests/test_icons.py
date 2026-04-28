from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_icon_manifest_has_expected_shape() -> None:
    manifest_path = REPO_ROOT / "icons" / "manifest.json"

    payload = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert set(payload) == {"icons"}
    assert isinstance(payload["icons"], list)


def test_icon_manifest_entries_include_required_metadata() -> None:
    manifest_path = REPO_ROOT / "icons" / "manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))

    for icon in payload["icons"]:
        assert isinstance(icon, dict)
        assert {"id", "source", "license", "url", "imported_at", "path"} <= set(icon)
