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
    try:
        cmds.polyBevel(node, offset=offset, segments=segments, autoFit=True)
        _soften(node)
    except Exception:
        pass


def _create_scene() -> str:
    cmds.file(new=True, force=True)
    cmds.currentUnit(linear="cm")
    cmds.currentTime(12)

    slate = _material("ar_slate_mat", (0.18, 0.2, 0.23))
    blue = _material("ar_blue_mat", (0.18, 0.48, 0.76))
    teal = _material("ar_teal_mat", (0.08, 0.7, 0.64))
    pink = _material("ar_pink_mat", (0.72, 0.34, 0.58))
    gold = _material("ar_gold_mat", (0.95, 0.68, 0.24))
    graphite = _material("ar_graphite_mat", (0.11, 0.12, 0.14))

    ground = cmds.polyPlane(name="ActionRailStage", width=9.0, height=6.2)[0]
    cmds.move(0, -0.04, 0, ground)
    _assign(ground, graphite)

    hero = cmds.polyCube(name="ActionRailHeroControl", width=1.25, height=1.25, depth=1.25)[0]
    cmds.move(-0.5, 0.64, 0, hero)
    cmds.rotate(0, 34, 0, hero)
    _assign(hero, blue)
    _bevel(hero)

    knob = cmds.polySphere(name="ActionRailSelectedHandle", radius=0.42)[0]
    cmds.move(0.75, 1.25, -0.2, knob)
    _assign(knob, teal)
    _soften(knob)

    key = cmds.polyCylinder(
        name="ActionRailKeyShape",
        radius=0.42,
        height=1.15,
        subdivisionsX=32,
    )[0]
    cmds.move(1.9, 0.58, 0.75, key)
    cmds.rotate(0, 0, 90, key)
    _assign(key, gold)
    _soften(key)

    torus = cmds.polyTorus(name="ActionRailMotionRing", radius=0.82, sectionRadius=0.035)[0]
    cmds.move(-1.95, 0.9, 0.8, torus)
    cmds.rotate(90, 0, 20, torus)
    _assign(torus, pink)
    _soften(torus)

    for index, x_pos in enumerate((-2.8, -2.15, -1.5, -0.85)):
        dot = cmds.polySphere(name=f"ActionRailTimelineDot{index + 1}", radius=0.09)[0]
        cmds.move(x_pos, 0.08, -1.55 + (index * 0.12), dot)
        _assign(dot, gold if index == 3 else slate)
        _soften(dot)

    rotate_control = cmds.circle(name="ActionRailRotateControl", normal=(0, 1, 0), radius=1.72)[0]
    cmds.move(-0.5, 0.66, 0, rotate_control)
    _set_override_color(rotate_control, 13)

    scale_control = cmds.circle(name="ActionRailScaleControl", normal=(1, 0, 0), radius=1.45)[0]
    cmds.move(-0.5, 0.66, 0, scale_control)
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
    cmds.setAttr(f"{shape}.focalLength", 48)
    cmds.setAttr(f"{shape}.nearClipPlane", 0.1)
    cmds.setAttr(f"{shape}.farClipPlane", 1000)
    cmds.xform(camera, translation=(5.2, 3.35, 5.3))

    target = cmds.spaceLocator(name="ActionRailReadmeCameraTarget")[0]
    cmds.xform(target, translation=(-0.25, 0.78, 0.05))
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
        "wireframeOnShaded": True,
    }
    for flag, value in flags.items():
        with suppress(Exception):
            cmds.modelEditor(editor, edit=True, **{flag: value})

    for name, color in {
        "background": (0.095, 0.105, 0.12),
        "backgroundTop": (0.16, 0.18, 0.2),
        "backgroundBottom": (0.075, 0.08, 0.09),
    }.items():
        with suppress(Exception):
            cmds.displayRGBColor(name, color[0], color[1], color[2])


def _quick_spec() -> actionrail.StackSpec:
    return actionrail.StackSpec(
        id="readme_context_rail",
        layout=actionrail.RailLayout(
            anchor="viewport.right.center",
            orientation="vertical",
            offset=(-8, -18),
            opacity=0.94,
        ),
        items=(
            actionrail.StackItem(
                type="toolButton",
                id="readme_context_rail.move",
                label="W",
                action="maya.tool.move",
                icon="actionrail.move",
                tooltip="Move tool",
                key_label="W",
                active_when="maya.tool == move",
            ),
            actionrail.StackItem(
                type="toolButton",
                id="readme_context_rail.rotate",
                label="E",
                action="maya.tool.rotate",
                icon="actionrail.rotate",
                tooltip="Rotate tool",
                key_label="E",
                active_when="maya.tool == rotate",
            ),
            actionrail.StackItem(
                type="toolButton",
                id="readme_context_rail.scale",
                label="R",
                action="maya.tool.scale",
                icon="actionrail.scale",
                tooltip="Scale tool",
                key_label="R",
                active_when="maya.tool == scale",
            ),
            actionrail.StackItem(type="spacer", id="readme_context_rail.gap", size=10),
            actionrail.StackItem(
                type="button",
                id="readme_context_rail.key",
                label="K",
                action="maya.anim.set_key",
                icon="actionrail.key",
                tone="teal",
                tooltip="Set keyframe",
                key_label="S",
            ),
        ),
    )


def _show_bars(panel: str) -> tuple[object, ...]:
    hosts = (
        actionrail.show_example("transform_stack", panel=panel),
        actionrail.show_example("horizontal_tools", panel=panel),
        actionrail.show_spec(_quick_spec(), panel=panel),
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
                ASSET_DIR / "actionrail_readme_maya_scene.png",
                viewport_size=(1600, 900),
                blast_name="actionrail_readme_maya_scene_base.png",
            ),
            _save_composite(
                hosts,
                ASSET_DIR / "actionrail_readme_maya_detail.png",
                viewport_size=(1200, 760),
                blast_name="actionrail_readme_maya_detail_base.png",
                rail_margin=16,
            ),
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
