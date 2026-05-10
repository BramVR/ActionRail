"""Provider catalog and read-only icon lookup.

Purpose: own picker-facing icon descriptors and runtime icon id resolution
without importing SVG write/import or mayapy fallback code.
Used by: Quick Create, widget render-state resolution, project map, and the
public ``actionrail.icons`` facade.
Tests: ``tests/test_icons.py``.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import Path
from weakref import WeakKeyDictionary

from . import icon_manifest, icon_paths
from .icon_types import IconDescriptor, IconManifestIssue, IconStatus


def _maya_icon_descriptor(
    icon_id: str,
    label: str,
    category: str,
    qt_name: str,
    *keywords: str,
) -> IconDescriptor:
    return IconDescriptor(
        id=icon_id,
        provider="maya",
        label=label,
        category=category,
        keywords=keywords,
        qt_name=qt_name,
        source="Autodesk Maya",
        license="Autodesk Maya",
        url=f"maya-resource://{qt_name}",
    )


MAYA_ICON_DESCRIPTORS: tuple[IconDescriptor, ...] = (
    _maya_icon_descriptor(
        "maya.set_key",
        "Set Key",
        "Animation",
        "setKeyframe.png",
        "key",
        "keyframe",
        "animation",
        "set key",
    ),
    _maya_icon_descriptor("maya.camera", "Camera", "Camera", "camera.svg", "camera"),
    _maya_icon_descriptor(
        "maya.camera_lock",
        "Camera Lock",
        "Camera",
        "CameraLock.png",
        "camera",
        "lock",
    ),
    _maya_icon_descriptor(
        "maya.depth_of_field",
        "Depth Of Field",
        "Camera",
        "DepthOfField.png",
        "camera",
        "focus",
    ),
    _maya_icon_descriptor(
        "maya.film_gate",
        "Film Gate",
        "Camera",
        "FilmGate.png",
        "camera",
        "gate",
    ),
    _maya_icon_descriptor(
        "maya.image_plane",
        "Image Plane",
        "Camera",
        "imagePlane.svg",
        "camera",
        "image",
    ),
    _maya_icon_descriptor("maya.area_light", "Area Light", "Lighting", "LM_areaLight.png", "light"),
    _maya_icon_descriptor(
        "maya.directional_light",
        "Directional Light",
        "Lighting",
        "LM_directionalLight.png",
        "light",
    ),
    _maya_icon_descriptor("maya.light", "Light", "Lighting", "Light.png", "light"),
    _maya_icon_descriptor(
        "maya.point_light",
        "Point Light",
        "Lighting",
        "LM_pointLight.png",
        "light",
    ),
    _maya_icon_descriptor("maya.spot_light", "Spot Light", "Lighting", "LM_spotLight.png", "light"),
    _maya_icon_descriptor(
        "maya.volume_light",
        "Volume Light",
        "Lighting",
        "LM_volumeLight.png",
        "light",
    ),
    _maya_icon_descriptor(
        "maya.auto_weld",
        "Auto Weld",
        "Modeling",
        "NEX_autoWeld.png",
        "weld",
        "modeling",
    ),
    _maya_icon_descriptor("maya.bevel", "Bevel", "Modeling", "bevel.png", "bevel", "modeling"),
    _maya_icon_descriptor(
        "maya.center_pivot",
        "Center Pivot",
        "Modeling",
        "CenterPivot.png",
        "pivot",
        "modeling",
    ),
    _maya_icon_descriptor("maya.cut", "Cut", "Modeling", "NEX_cut.png", "cut", "modeling"),
    _maya_icon_descriptor(
        "maya.cut_edge",
        "Cut Edge",
        "Modeling",
        "NEX_cutEdge.png",
        "cut",
        "edge",
        "modeling",
    ),
    _maya_icon_descriptor(
        "maya.extrude",
        "Extrude",
        "Modeling",
        "polyExtrudeFacet.png",
        "extrude",
        "modeling",
    ),
    _maya_icon_descriptor(
        "maya.freeze_transform",
        "Freeze Transform",
        "Modeling",
        "FreezeTransform.png",
        "freeze",
        "transform",
    ),
    _maya_icon_descriptor("maya.knife", "Knife", "Modeling", "Knife.png", "knife", "modeling"),
    _maya_icon_descriptor(
        "maya.quad_draw",
        "Quad Draw",
        "Modeling",
        "NEX_quadDraw.png",
        "quad",
        "draw",
        "modeling",
    ),
    _maya_icon_descriptor(
        "maya.smooth_brush",
        "Smooth Brush",
        "Modeling",
        "NEX_QD_SmoothBrush.png",
        "smooth",
        "brush",
    ),
    _maya_icon_descriptor(
        "maya.move",
        "Move Tool",
        "Transform",
        "move_M.png",
        "move",
        "translate",
        "transform",
        "tool",
    ),
    _maya_icon_descriptor(
        "maya.rotate",
        "Rotate Tool",
        "Transform",
        "rotate_M.png",
        "rotate",
        "transform",
        "tool",
    ),
    _maya_icon_descriptor(
        "maya.scale",
        "Scale Tool",
        "Transform",
        "scale_M.png",
        "scale",
        "transform",
        "tool",
    ),
    _maya_icon_descriptor(
        "maya.translate",
        "Translate Tool",
        "Transform",
        "HIKCustomRigToolTranslate.png",
        "translate",
        "transform",
        "tool",
    ),
    _maya_icon_descriptor("maya.grid", "Grid", "Viewport", "grid.svg", "grid", "viewport"),
    _maya_icon_descriptor(
        "maya.high_quality",
        "High Quality",
        "Viewport",
        "HighQuality.png",
        "viewport",
        "quality",
    ),
    _maya_icon_descriptor(
        "maya.isolate_selected",
        "Isolate Selected",
        "Viewport",
        "IsolateSelected.png",
        "isolate",
        "selection",
        "viewport",
    ),
    _maya_icon_descriptor("maya.lock", "Lock", "Viewport", "Lock_ON.png", "lock", "viewport"),
    _maya_icon_descriptor(
        "maya.low_quality",
        "Low Quality",
        "Viewport",
        "LowQuality.png",
        "viewport",
        "quality",
    ),
    _maya_icon_descriptor(
        "maya.objects",
        "Objects",
        "Viewport",
        "Objects.png",
        "objects",
        "viewport",
    ),
    _maya_icon_descriptor(
        "maya.pan_zoom",
        "Pan Zoom",
        "Viewport",
        "PanZoom.png",
        "pan",
        "zoom",
        "viewport",
    ),
    _maya_icon_descriptor(
        "maya.reflection",
        "Reflection",
        "Viewport",
        "Reflection.png",
        "viewport",
        "reflection",
    ),
    _maya_icon_descriptor(
        "maya.regular_viewport",
        "Regular Viewport",
        "Viewport",
        "RegularViewport.png",
        "viewport",
    ),
    _maya_icon_descriptor(
        "maya.resolution_gate",
        "Resolution Gate",
        "Viewport",
        "ResolutionGate.png",
        "viewport",
        "gate",
    ),
)
MAYA_ICON_BY_ID = {descriptor.id: descriptor for descriptor in MAYA_ICON_DESCRIPTORS}
_MAYA_RESOURCE_EXISTS_CACHE: WeakKeyDictionary[object, dict[str, bool]] = WeakKeyDictionary()
_MAYA_RESOURCE_EXISTS_ID_CACHE: dict[int, dict[str, bool]] = {}


def resolve_icon_path(icon_id: str) -> Path | None:
    """Return a safe local path for a manifest icon id if it exists on disk."""

    return icon_status(icon_id).path


def resolve_icon_name(icon_id: str) -> str:
    """Return a Qt resource name for an icon id if it is not file-backed."""

    return icon_status(icon_id).qt_name


def icon_status(icon_id: str, *, cmds_module: object | None = None) -> IconStatus:
    """Return the resolved path or first diagnostic issue for one icon id."""

    if not icon_id:
        return IconStatus(icon_id)

    maya_status = maya_icon_status(icon_id, cmds_module=cmds_module)
    if maya_status is not None:
        return maya_status

    entries = icon_manifest.manifest_icons()
    for issue in icon_manifest.manifest_shape_issues(entries):
        return IconStatus(icon_id, issue=issue)

    for entry in entries:
        if entry.get("id") != icon_id:
            continue

        issue = icon_manifest.entry_issue(entry)
        if issue is not None:
            return IconStatus(icon_id, issue=issue)

        raw_path = entry["path"]
        icon_path = icon_paths.resolve_manifest_path(raw_path)
        issue = icon_manifest.asset_issue(icon_id, raw_path, icon_path)
        if issue is not None:
            return IconStatus(icon_id, issue=issue)
        return IconStatus(icon_id, path=icon_path, provider="manifest")

    return IconStatus(
        icon_id,
        issue=IconManifestIssue(
            code="missing_icon",
            message=f"Icon '{icon_id}' is not listed in the ActionRail icon manifest.",
            icon_id=icon_id,
            hint="Add the icon to icons/manifest.json or remove the slot icon reference.",
        ),
    )


def list_icon_descriptors(*, provider: str = "") -> tuple[IconDescriptor, ...]:
    """Return icon metadata for picker UIs."""

    descriptors = (*manifest_icon_descriptors(), *MAYA_ICON_DESCRIPTORS)
    if not provider:
        return tuple(sorted(descriptors, key=icon_descriptor_sort_key))
    return tuple(
        descriptor
        for descriptor in sorted(descriptors, key=icon_descriptor_sort_key)
        if descriptor.provider == provider
    )


def maya_icon_status(icon_id: str, *, cmds_module: object | None) -> IconStatus | None:
    descriptor = MAYA_ICON_BY_ID.get(icon_id)
    if descriptor is None:
        return None

    if cmds_module is not None and not maya_resource_exists(descriptor.qt_name, cmds_module):
        return IconStatus(
            icon_id,
            provider="maya",
            issue=IconManifestIssue(
                code="missing_maya_icon_resource",
                message=(
                    f"Maya icon resource '{descriptor.qt_name}' for icon "
                    f"'{icon_id}' is unavailable in this Maya session."
                ),
                icon_id=icon_id,
                path=descriptor.qt_name,
                hint=(
                    "Choose another Maya icon id or update the ActionRail Maya "
                    "resource mapping for this Maya version."
                ),
            ),
        )

    return IconStatus(icon_id, qt_name=descriptor.qt_name, provider="maya")


def maya_resource_exists(resource_name: str, cmds_module: object) -> bool:
    cache = _maya_resource_cache(cmds_module)
    if resource_name in cache:
        return cache[resource_name]

    resource_manager = getattr(cmds_module, "resourceManager", None)
    if not callable(resource_manager):
        cache[resource_name] = False
        return False

    try:
        resources = resource_manager(nameFilter=resource_name) or ()
    except Exception:
        cache[resource_name] = False
        return False
    exists = resource_name in set(string_values(resources))
    cache[resource_name] = exists
    return exists


def _maya_resource_cache(cmds_module: object) -> dict[str, bool]:
    try:
        cache = _MAYA_RESOURCE_EXISTS_CACHE.get(cmds_module)
    except TypeError:
        cache = _MAYA_RESOURCE_EXISTS_ID_CACHE.setdefault(id(cmds_module), {})
    else:
        if cache is None:
            cache = {}
            _MAYA_RESOURCE_EXISTS_CACHE[cmds_module] = cache
    return cache


def string_values(values: Iterable[object]) -> tuple[str, ...]:
    return tuple(value for value in values if isinstance(value, str))


def manifest_icon_descriptors() -> tuple[IconDescriptor, ...]:
    entries = icon_manifest.manifest_icons()
    if icon_manifest.manifest_shape_issues(entries):
        return ()

    descriptors: list[IconDescriptor] = []
    for entry in entries:
        if icon_manifest.entry_issue(entry) is not None:
            continue
        raw_path = entry["path"]
        icon_path = icon_paths.resolve_manifest_path(raw_path)
        if icon_manifest.asset_issue(entry["id"], raw_path, icon_path) is not None:
            continue
        descriptors.append(
            IconDescriptor(
                id=entry["id"],
                provider="manifest",
                label=label_from_icon_id(entry["id"]),
                category=str(entry.get("category") or "Custom"),
                keywords=keywords_from_icon_id(entry["id"]),
                path=icon_path,
                source=entry["source"],
                license=entry["license"],
                url=entry["url"],
            )
        )
    return tuple(descriptors)


def label_from_icon_id(icon_id: str) -> str:
    label = icon_id.rsplit(".", 1)[-1].replace("_", " ").replace("-", " ")
    return " ".join(word.capitalize() for word in label.split()) or icon_id


def keywords_from_icon_id(icon_id: str) -> tuple[str, ...]:
    words = re.split(r"[._-]+", icon_id)
    return tuple(word for word in words if word)


def icon_descriptor_sort_key(descriptor: IconDescriptor) -> tuple[str, str, str]:
    return (descriptor.provider, descriptor.category, descriptor.label)
