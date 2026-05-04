"""SVG safety and shape validation for ActionRail icons.

Purpose: keep SVG parsing and safety checks separate from manifest storage and
import writes.
Used by: icon manifest validation and SVG import preflight.
Tests: ``tests/test_icons.py``.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

from .icon_types import IconManifestIssue

_EXTERNAL_REF_RE = re.compile(r"^\s*(?:https?:|file:|//|data:)", re.IGNORECASE)
_EXTERNAL_STYLE_RE = re.compile(
    r"(?:@import|url\(\s*['\"]?(?:https?:|file:|//|data:))",
    re.IGNORECASE,
)


def svg_issue(icon_id: str, raw_path: str, icon_path: Path) -> IconManifestIssue | None:
    try:
        root = ET.fromstring(icon_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return IconManifestIssue(
            code="invalid_icon_svg",
            message=f"Icon '{icon_id}' SVG could not be parsed: {exc}.",
            icon_id=icon_id,
            path=raw_path,
            hint="Use a valid SVG file with an <svg> root and viewBox.",
        )

    if local_name(root.tag) != "svg" or not root.attrib.get("viewBox"):
        return IconManifestIssue(
            code="invalid_icon_svg",
            message=f"Icon '{icon_id}' SVG must have an <svg> root and viewBox.",
            icon_id=icon_id,
            path=raw_path,
            hint="Use a valid SVG file with an <svg> root and viewBox.",
        )

    for element in root.iter():
        name = local_name(element.tag)
        if name in {"script", "foreignObject"}:
            return unsafe_svg_issue(icon_id, raw_path, f"disallowed <{name}> element")
        if name == "style" and _EXTERNAL_STYLE_RE.search("".join(element.itertext())):
            return unsafe_svg_issue(icon_id, raw_path, "external stylesheet reference")
        for attr_name, attr_value in element.attrib.items():
            attr = local_name(attr_name)
            if attr.lower().startswith("on"):
                return unsafe_svg_issue(icon_id, raw_path, f"event handler '{attr}'")
            if attr in {"href", "src"} and _EXTERNAL_REF_RE.search(attr_value):
                return unsafe_svg_issue(icon_id, raw_path, f"external reference '{attr_value}'")
            if isinstance(attr_value, str) and _EXTERNAL_STYLE_RE.search(attr_value):
                return unsafe_svg_issue(icon_id, raw_path, "external stylesheet reference")
    return None


def unsafe_svg_issue(icon_id: str, raw_path: str, reason: str) -> IconManifestIssue:
    return IconManifestIssue(
        code="unsafe_icon_svg",
        message=f"Icon '{icon_id}' SVG is unsafe: {reason}.",
        icon_id=icon_id,
        path=raw_path,
        hint="Use a cleaned local SVG without scripts, event handlers, or external resources.",
    )


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]
