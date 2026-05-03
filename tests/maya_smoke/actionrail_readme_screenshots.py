from __future__ import annotations

import json
import math
import sys
from contextlib import suppress
from pathlib import Path

__args__ = globals().get("__args__", {})

repo_scripts = __args__.get("repo_scripts")
if repo_scripts and repo_scripts not in sys.path:
    sys.path.insert(0, repo_scripts)

from maya import cmds  # noqa: E402
from PySide6 import QtCore, QtGui, QtWidgets  # noqa: E402

import actionrail  # noqa: E402

if __args__.get("repo_root"):
    REPO_ROOT = Path(__args__["repo_root"])
elif repo_scripts:
    REPO_ROOT = Path(repo_scripts).resolve().parent
else:
    REPO_ROOT = Path("C:/PROJECTS/GG/ScreenUI")
ASSET_DIR = REPO_ROOT / "docs" / "assets"
SCRATCH_DIR = REPO_ROOT / ".gg-maya-sessiond" / "readme_screenshots"


def _material(name: str, color: tuple[float, float, float]) -> str:
    shader = cmds.shadingNode("lambert", asShader=True, name=name)
    cmds.setAttr(f"{shader}.color", color[0], color[1], color[2], type="double3")
    cmds.setAttr(f"{shader}.diffuse", 0.85)
    shading_group = cmds.sets(
        renderable=True,
        noSurfaceShader=True,
        empty=True,
        name=f"{name}SG",
    )
    cmds.connectAttr(f"{shader}.outColor", f"{shading_group}.surfaceShader", force=True)
    return shading_group


def _assign(node: str, shading_group: str) -> None:
    cmds.sets(node, edit=True, forceElement=shading_group)


def _set_override_color(node: str, color_index: int) -> None:
    cmds.setAttr(f"{node}.overrideEnabled", 1)
    cmds.setAttr(f"{node}.overrideColor", color_index)


def _soften(node: str) -> None:
    with suppress(Exception):
        cmds.polySoftEdge(node, angle=45)


def _bevel(node: str, offset: float = 0.035, segments: int = 2) -> None:
    with suppress(Exception):
        cmds.polyBevel(node, offset=offset, segments=segments, autoFit=True)
        _soften(node)


def _create_scene() -> str:
    cmds.file(new=True, force=True)
    cmds.currentUnit(linear="cm")
    cmds.currentTime(12)

    blue = _material("ar_blue_mat", (0.16, 0.42, 0.72))
    teal = _material("ar_teal_mat", (0.08, 0.7, 0.64))
    gold = _material("ar_gold_mat", (0.95, 0.68, 0.24))
    graphite = _material("ar_graphite_mat", (0.12, 0.13, 0.145))

    ground = cmds.polyPlane(name="ActionRailStage", width=7.2, height=4.8)[0]
    cmds.move(0, -0.04, 0, ground)
    _assign(ground, graphite)

    hero = cmds.polyCube(name="ActionRailSelectedControl", width=1.25, height=1.25, depth=1.25)[0]
    cmds.move(-0.15, 0.64, 0, hero)
    cmds.rotate(0, 32, 0, hero)
    _assign(hero, blue)
    _bevel(hero)

    handle = cmds.polySphere(name="ActionRailHandle", radius=0.28)[0]
    cmds.move(0.98, 1.08, -0.18, handle)
    _assign(handle, teal)
    _soften(handle)

    marker = cmds.polyCylinder(name="ActionRailKeyMarker", radius=0.18, height=0.55)[0]
    cmds.move(-1.45, 0.24, 0.9, marker)
    cmds.rotate(0, 0, 90, marker)
    _assign(marker, gold)
    _soften(marker)

    rotate_control = cmds.circle(name="ActionRailRotateGuide", normal=(0, 1, 0), radius=1.55)[0]
    cmds.move(-0.15, 0.66, 0, rotate_control)
    _set_override_color(rotate_control, 13)

    scale_control = cmds.circle(name="ActionRailScaleGuide", normal=(1, 0, 0), radius=1.3)[0]
    cmds.move(-0.15, 0.66, 0, scale_control)
    _set_override_color(scale_control, 18)

    cmds.directionalLight(name="ActionRailKeyLight", intensity=0.95)
    cmds.rotate(-38, 35, -22, "ActionRailKeyLight")
    cmds.ambientLight(name="ActionRailFillLight", intensity=0.28)

    cmds.select(hero, replace=True)
    cmds.setToolTo("RotateSuperContext")
    return hero


def _active_model_panel() -> str:
    focused = cmds.getPanel(withFocus=True)
    if focused and cmds.getPanel(typeOf=focused) == "modelPanel":
        return focused
    for panel in cmds.getPanel(visiblePanels=True) or []:
        if cmds.getPanel(typeOf=panel) == "modelPanel":
            return panel
    panels = cmds.getPanel(type="modelPanel") or []
    if not panels:
        raise RuntimeError("No Maya modelPanel is available for README screenshots.")
    return panels[0]


def _look_at_camera(panel: str) -> str:
    camera, shape = cmds.camera(name="ActionRailReadmeCamera")
    cmds.setAttr(f"{shape}.focalLength", 55)
    cmds.setAttr(f"{shape}.nearClipPlane", 0.1)
    cmds.setAttr(f"{shape}.farClipPlane", 1000)
    cmds.xform(camera, translation=(4.35, 2.7, 4.55))

    target = cmds.spaceLocator(name="ActionRailReadmeCameraTarget")[0]
    cmds.xform(target, translation=(-0.1, 0.7, 0.05))
    constraint = cmds.aimConstraint(
        target,
        camera,
        aimVector=(0, 0, -1),
        upVector=(0, 1, 0),
        worldUpType="scene",
    )[0]
    cmds.delete(constraint, target)

    cmds.modelPanel(panel, edit=True, camera=camera)
    return camera


def _set_viewport_style(panel: str) -> None:
    editor = cmds.modelPanel(panel, query=True, modelEditor=True)
    flags = {
        "displayAppearance": "smoothShaded",
        "displayLights": "default",
        "grid": False,
        "headsUpDisplay": False,
        "selectionHiliteDisplay": True,
        "textures": False,
        "useDefaultMaterial": False,
        "wireframeOnShaded": False,
    }
    for flag, value in flags.items():
        with suppress(Exception):
            cmds.modelEditor(editor, edit=True, **{flag: value})

    for name, color in {
        "background": (0.075, 0.082, 0.095),
        "backgroundTop": (0.105, 0.115, 0.13),
        "backgroundBottom": (0.055, 0.06, 0.07),
    }.items():
        with suppress(Exception):
            cmds.displayRGBColor(name, color[0], color[1], color[2])


ACTION_CYCLE = (
    ("move", "M", "maya.tool.move"),
    ("rotate", "R", "maya.tool.rotate"),
    ("scale", "S", "maya.tool.scale"),
    ("key", "K", "maya.anim.set_key"),
)
SHOWCASE_ICON_IDS = (
    "maya.move",
    "maya.rotate",
    "maya.scale",
    "maya.set_key",
    "maya.camera",
    "maya.light",
    "maya.grid",
    "maya.isolate_selected",
    "maya.center_pivot",
    "maya.freeze_transform",
    "maya.knife",
    "maya.quad_draw",
    "maya.area_light",
    "maya.directional_light",
    "maya.point_light",
    "maya.spot_light",
    "maya.volume_light",
    "maya.image_plane",
    "maya.depth_of_field",
    "maya.film_gate",
    "maya.cut",
    "maya.cut_edge",
    "maya.smooth_brush",
    "maya.auto_weld",
    "maya.bevel",
    "maya.extrude",
    "maya.pan_zoom",
    "maya.reflection",
    "maya.resolution_gate",
    "maya.high_quality",
    "maya.low_quality",
    "maya.objects",
    "maya.lock",
    "maya.regular_viewport",
    "maya.camera_lock",
    "maya.translate",
)


def _action_item(
    spec_id: str,
    index: int,
    icon_id: str,
    *,
    label_override: str | None = None,
    key_label: str = "",
    icon_only: bool = False,
    active: bool = False,
) -> actionrail.StackItem:
    action_name, label, action_id = ACTION_CYCLE[index % len(ACTION_CYCLE)]
    active_when = ""
    if active and action_id == "maya.tool.rotate":
        active_when = "maya.tool == rotate"
    elif active and action_id == "maya.tool.move":
        active_when = "maya.tool == move"
    elif active and action_id == "maya.tool.scale":
        active_when = "maya.tool == scale"

    return actionrail.StackItem(
        type="toolButton",
        id=f"{spec_id}.{action_name}_{index + 1}",
        label="" if icon_only else (label_override if label_override is not None else label),
        action=action_id,
        icon=icon_id,
        key_label=key_label,
        tooltip=f"{label_override or label} action",
        active_when=active_when,
    )


def _number_bar_spec() -> actionrail.StackSpec:
    spec_id = "readme_number_actionbar"
    key_labels = ("1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "-", "=")
    icon_ids = SHOWCASE_ICON_IDS[: len(key_labels)]
    return actionrail.StackSpec(
        id=spec_id,
        layout=actionrail.RailLayout(
            anchor="viewport.bottom.center",
            orientation="horizontal",
            offset=(0, -22),
            opacity=0.95,
        ),
        items=tuple(
            _action_item(
                spec_id,
                index,
                icon_id,
                key_label=key,
                icon_only=True,
                active=index == 1,
            )
            for index, (key, icon_id) in enumerate(zip(key_labels, icon_ids, strict=True))
        ),
    )


def _icon_strip_spec() -> actionrail.StackSpec:
    spec_id = "readme_icon_strip"
    icon_ids = SHOWCASE_ICON_IDS[12:20]
    return actionrail.StackSpec(
        id=spec_id,
        layout=actionrail.RailLayout(
            anchor="viewport.bottom.center",
            orientation="horizontal",
            offset=(0, -76),
            opacity=0.92,
        ),
        items=tuple(
            _action_item(spec_id, index, icon_id, icon_only=True)
            for index, icon_id in enumerate(icon_ids)
        ),
    )


def _left_label_column_spec() -> actionrail.StackSpec:
    spec_id = "readme_left_label_column"
    labels = tuple("ABCDEFGHI")
    return actionrail.StackSpec(
        id=spec_id,
        layout=actionrail.RailLayout(
            anchor="viewport.left.center",
            orientation="vertical",
            offset=(6, -62),
            opacity=0.94,
        ),
        items=tuple(
            _action_item(spec_id, index, "", label_override=label)
            for index, label in enumerate(labels)
        ),
    )


def _right_number_column_spec() -> actionrail.StackSpec:
    spec_id = "readme_right_number_column"
    icon_ids = SHOWCASE_ICON_IDS[20:27]
    return actionrail.StackSpec(
        id=spec_id,
        layout=actionrail.RailLayout(
            anchor="viewport.right.center",
            orientation="vertical",
            offset=(-8, -42),
            opacity=0.94,
        ),
        items=tuple(
            _action_item(
                spec_id,
                index,
                icon_id,
                key_label=str(index + 1),
                icon_only=True,
                active=index == 1,
            )
            for index, icon_id in enumerate(icon_ids)
        ),
    )


def _show_bars(panel: str) -> tuple[object, ...]:
    specs = (
        _number_bar_spec(),
        _icon_strip_spec(),
        _left_label_column_spec(),
        _right_number_column_spec(),
    )
    _assert_unique_icons(specs)
    hosts = (
        actionrail.show_spec(specs[0], panel=panel),
        actionrail.show_spec(specs[1], panel=panel),
        actionrail.show_spec(specs[2], panel=panel),
        actionrail.show_spec(specs[3], panel=panel),
    )
    _process_events(350)
    for host in hosts:
        try:
            host.refresh_state()
            host.position()
            host.widget.raise_()
        except Exception:
            pass
    _process_events(150)
    return hosts


def _assert_unique_icons(specs: tuple[actionrail.StackSpec, ...]) -> None:
    icon_ids = [item.icon for spec in specs for item in spec.items if item.icon]
    duplicates = sorted({icon_id for icon_id in icon_ids if icon_ids.count(icon_id) > 1})
    if duplicates:
        raise AssertionError(f"README showcase icon ids must be unique: {duplicates}")


def _process_events(delay_ms: int = 0) -> None:
    app = QtWidgets.QApplication.instance()
    if app is None:
        raise RuntimeError("Maya QApplication is not available.")
    app.processEvents()
    if delay_ms:
        QtCore.QThread.msleep(delay_ms)
        app.processEvents()


def _playblast(path: Path, size: tuple[int, int]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    cmds.refresh(force=True)
    result = cmds.playblast(
        completeFilename=str(path),
        compression="png",
        endTime=12,
        forceOverwrite=True,
        format="image",
        frame=12,
        percent=100,
        showOrnaments=False,
        startTime=12,
        viewer=False,
        widthHeight=(size[0], size[1]),
    )
    output = Path(result or path)
    if output.is_file():
        return output
    if path.is_file():
        return path

    candidates = sorted(path.parent.glob(f"{path.stem}*.png"))
    if candidates:
        return candidates[-1]
    raise RuntimeError(f"Playblast did not produce an image: {path}")


def _anchor_position(
    anchor: str,
    image_size: tuple[int, int],
    rail_size: tuple[int, int],
    offset: tuple[int, int],
    margin: int = 18,
) -> tuple[int, int]:
    image_width, image_height = image_size
    rail_width, rail_height = rail_size
    parts = anchor.split(".")

    if "left" in parts:
        x_pos = margin
    elif "right" in parts:
        x_pos = image_width - rail_width - margin
    else:
        x_pos = math.floor((image_width - rail_width) / 2)

    if "top" in parts:
        y_pos = margin
    elif "bottom" in parts:
        y_pos = image_height - rail_height - margin
    else:
        y_pos = math.floor((image_height - rail_height) / 2)

    x_pos += offset[0]
    y_pos += offset[1]
    return (max(8, x_pos), max(8, y_pos))


def _save_composite(
    hosts: tuple[object, ...],
    output_path: Path,
    *,
    viewport_size: tuple[int, int],
    blast_name: str,
    rail_margin: int = 18,
) -> dict[str, object]:
    blast_path = _playblast(SCRATCH_DIR / blast_name, viewport_size)
    base = QtGui.QPixmap(str(blast_path))
    if base.isNull():
        raise RuntimeError(f"Unable to read viewport playblast: {blast_path}")

    painter = QtGui.QPainter(base)
    placements = []
    for host in hosts:
        widget = host.widget
        rail = widget.grab()
        spec = host.spec
        x_pos, y_pos = _anchor_position(
            spec.anchor,
            (base.width(), base.height()),
            (rail.width(), rail.height()),
            spec.layout.offset,
            margin=rail_margin,
        )
        painter.drawPixmap(x_pos, y_pos, rail)
        placements.append(
            {
                "id": spec.id,
                "position": [x_pos, y_pos],
                "size": [rail.width(), rail.height()],
            }
        )
    painter.end()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not base.save(str(output_path), "PNG"):
        raise RuntimeError(f"Unable to save composite screenshot: {output_path}")

    return {
        "output_path": str(output_path),
        "playblast_path": str(blast_path),
        "placements": placements,
        "size": [base.width(), base.height()],
    }


def main() -> None:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    SCRATCH_DIR.mkdir(parents=True, exist_ok=True)

    hero_object = _create_scene()
    panel = _active_model_panel()
    _look_at_camera(panel)
    _set_viewport_style(panel)
    cmds.select(hero_object, replace=True)
    cmds.setToolTo("RotateSuperContext")

    hosts = _show_bars(panel)
    try:
        captures = [
            _save_composite(
                hosts,
                ASSET_DIR / "actionrail_readme_maya_icons_showcase.png",
                viewport_size=(1600, 900),
                blast_name="actionrail_readme_maya_scene_base.png",
            )
        ]
    finally:
        actionrail.hide_all()
        _process_events(100)

    result = {
        "captures": captures,
        "panel": panel,
        "selected": hero_object,
    }
    print(json.dumps(result, sort_keys=True))


main()
