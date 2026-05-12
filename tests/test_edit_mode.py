from __future__ import annotations

import sys
from dataclasses import replace
from types import ModuleType

import actionrail.edit_mode as edit_mode
import actionrail.overlay as overlay
import actionrail.runtime as runtime
from actionrail.authoring import load_user_preset, save_user_preset
from actionrail.spec import RailCollapse, RailLayout, StackItem, StackSpec


def test_edit_mode_settings_clamp_grid_size() -> None:
    assert edit_mode.EditModeSettings().normalized().grid_size == 32
    assert edit_mode.EditModeSettings(grid_size=-1).normalized().grid_size == 16
    assert edit_mode.EditModeSettings(grid_size=999).normalized().grid_size == 512
    assert edit_mode.EditModeSettings(grid_size=32).normalized().grid_size == 32


def test_edit_mode_frame_options_popover_is_removed() -> None:
    assert not hasattr(edit_mode, "FRAME_OPTIONS_POPOVER_OBJECT_NAME")
    assert not hasattr(edit_mode.EditModeOverlayHost, "open_options")
    assert not hasattr(edit_mode.EditModeOverlayHost, "assign_slot_action_payload")


def test_rail_frame_contains_and_topmost_selection() -> None:
    back = edit_mode.RailFrameInfo(
        preset_id="back",
        label="Back",
        x=0,
        y=0,
        width=100,
        height=100,
        anchor="viewport.left.top",
        offset=(0, 0),
        orientation="vertical",
        rows=1,
        columns=1,
        scale=1.0,
        opacity=1.0,
        locked=False,
    )
    front = replace(back, preset_id="front", label="Front", x=20, y=20)

    assert back.contains(100, 100) is True
    assert back.contains(101, 100) is False
    assert edit_mode._topmost_frame_at((back, front), 25, 25) is front
    assert edit_mode._topmost_frame_at((back, front), 121, 121) is None


def test_rail_slot_contains_and_topmost_selection() -> None:
    back = edit_mode.RailSlotInfo(
        preset_id="bar",
        slot_id="bar.one",
        label="One",
        action="maya.tool.move",
        x=0,
        y=0,
        width=32,
        height=32,
        locked=False,
    )
    front = replace(back, slot_id="bar.two", label=edit_mode.EMPTY_SLOT_LABEL, action="", x=8)

    assert back.contains(32, 32) is True
    assert back.has_payload is True
    assert front.has_payload is False
    assert edit_mode._topmost_slot_at((back, front), 12, 12) is front
    assert edit_mode._topmost_slot_at((back, front), 60, 12) is None


def test_snap_to_grid_and_sticky_frame_alignment() -> None:
    moving = edit_mode.RailFrameInfo(
        preset_id="moving",
        label="Moving",
        x=10,
        y=10,
        width=40,
        height=40,
        anchor="viewport.left.top",
        offset=(0, 0),
        orientation="horizontal",
        rows=1,
        columns=1,
        scale=1.0,
        opacity=1.0,
        locked=False,
    )
    target = replace(moving, preset_id="target", x=100, y=200)

    assert edit_mode._snap_value_to_grid(30, 16) == 32
    assert edit_mode._snapped_position(
        moving,
        30,
        47,
        edit_mode.EditModeSettings(snap_to_grid=True, grid_size=16),
        (moving, target),
    ) == (32, 48)
    assert edit_mode._snapped_position(
        moving,
        61,
        161,
        edit_mode.EditModeSettings(sticky_frames=True),
        (moving, target),
    ) == (60, 160)
    assert edit_mode._snapped_position(
        moving,
        40,
        140,
        edit_mode.EditModeSettings(sticky_frames=True),
        (moving, target),
    ) == (40, 140)
    assert edit_mode._snapped_position(
        moving,
        61,
        161,
        edit_mode.EditModeSettings(snap_to_grid=True, sticky_frames=True, grid_size=16),
        (moving, target),
    ) == (64, 160)
    assert edit_mode._snapped_position(
        moving,
        61,
        163,
        edit_mode.EditModeSettings(snap_to_grid=True, sticky_frames=True, grid_size=16),
        (moving, target),
        snap_axes=("x",),
    ) == (64, 163)
    assert edit_mode._snap_axes_for_delta(1, 0) == ("x",)
    assert edit_mode._snap_axes_for_delta(0, -1) == ("y",)
    assert edit_mode._snap_axes_for_delta(0, 0) == ("x", "y")
    assert edit_mode._nudge_delta(1, 64) == 64
    assert edit_mode._nudge_delta(-1, 64) == -64
    assert edit_mode._nudge_delta(0, 64) == 0


def test_guide_segments_use_axis_aligned_sticky_guides() -> None:
    moving = edit_mode.RailFrameInfo(
        preset_id="moving",
        label="Moving",
        x=60,
        y=160,
        width=40,
        height=40,
        anchor="viewport.left.top",
        offset=(0, 0),
        orientation="horizontal",
        rows=1,
        columns=1,
        scale=1.0,
        opacity=1.0,
        locked=False,
    )
    target = replace(moving, preset_id="target", x=100, y=200)

    selected_only = edit_mode._guide_segments(
        moving,
        (moving, target),
        edit_mode.EditModeSettings(sticky_frames=False),
        640,
        480,
    )
    assert len(selected_only) == 6
    assert {segment.kind for segment in selected_only} == {"selected"}

    sticky_segments = edit_mode._guide_segments(
        moving,
        (moving, target),
        edit_mode.EditModeSettings(sticky_frames=True),
        640,
        480,
    )
    sticky_only = [segment for segment in sticky_segments if segment.kind == "sticky"]

    assert edit_mode._GuideSegment(100, 160, 100, 240, "sticky") in sticky_only
    assert edit_mode._GuideSegment(200, 60, 140, 200, "sticky") not in sticky_only
    assert all(
        segment.x1 == segment.x2 or segment.y1 == segment.y2
        for segment in sticky_only
    )


def test_snapped_position_clamps_to_safe_bounds() -> None:
    frame = edit_mode.RailFrameInfo(
        preset_id="moving",
        label="Moving",
        x=0,
        y=0,
        width=100,
        height=50,
        anchor="viewport.left.top",
        offset=(0, 0),
        orientation="horizontal",
        rows=1,
        columns=1,
        scale=1.0,
        opacity=1.0,
        locked=False,
    )
    settings = edit_mode.EditModeSettings(snap_to_grid=True, grid_size=64)

    assert edit_mode._snapped_position(frame, -100, -100, settings, ()) == (8, 8)
    assert edit_mode._snapped_position(
        frame,
        100000,
        100000,
        settings,
        (),
        bounds=(640, 480),
    ) == (532, 422)


def test_widget_position_prefers_parent_mapped_global_position() -> None:
    class Point:
        def __init__(self, x_pos: int, y_pos: int) -> None:
            self._x = x_pos
            self._y = y_pos

        def x(self) -> int:
            return self._x

        def y(self) -> int:
            return self._y

    class Qt:
        class QtCore:
            QPoint = Point

    class Widget:
        def mapToGlobal(self, _point: Point) -> Point:  # noqa: N802
            return Point(130, 240)

    class Parent:
        def mapFromGlobal(self, point: Point) -> Point:  # noqa: N802
            return Point(point.x() - 100, point.y() - 200)

    assert edit_mode._widget_position_in_parent(Qt, Parent(), Widget()) == (30, 40)


def test_widget_position_falls_back_to_geometry_and_origin() -> None:
    class Geometry:
        def x(self) -> int:
            return 7

        def y(self) -> int:
            return 9

    class GeometryWidget:
        def mapToGlobal(self, _point: object) -> object:  # noqa: N802
            raise RuntimeError("not mapped")

        def geometry(self) -> Geometry:
            return Geometry()

    class BrokenWidget:
        def geometry(self) -> object:
            raise RuntimeError("deleted")

    class Qt:
        class QtCore:
            class QPoint:
                def __init__(self, *_args: object) -> None:
                    pass

    assert edit_mode._widget_position_in_parent(Qt, object(), GeometryWidget()) == (7, 9)
    assert edit_mode._widget_position_in_parent(Qt, object(), BrokenWidget()) == (0, 0)


def test_rail_frame_info_extracts_runtime_host_geometry() -> None:
    class Point:
        def __init__(self, x_pos: int, y_pos: int) -> None:
            self._x = x_pos
            self._y = y_pos

        def x(self) -> int:
            return self._x

        def y(self) -> int:
            return self._y

    class Qt:
        class QtCore:
            QPoint = Point

    class Parent:
        def mapFromGlobal(self, point: Point) -> Point:  # noqa: N802
            return point

    class Widget:
        def isVisible(self) -> bool:  # noqa: N802
            return True

        def width(self) -> int:
            return 46

        def height(self) -> int:
            return 214

        def mapToGlobal(self, _point: Point) -> Point:  # noqa: N802
            return Point(12, 34)

    class Host:
        widget = Widget()
        spec = StackSpec(
            id="transform_stack",
            layout=RailLayout(
                anchor="viewport.left.center",
                offset=(3, 4),
                rows=5,
                columns=1,
                locked=True,
            ),
            items=(),
        )

    frame = edit_mode._rail_frame_info(Qt, Parent(), "transform_stack", Host())

    assert frame is not None
    assert frame.label == "Transform Stack"
    assert frame.x == 12
    assert frame.y == 34
    assert frame.width == 46
    assert frame.height == 214
    assert frame.offset == (3, 4)
    assert frame.locked is True


def test_rail_frame_infos_filters_missing_or_invalid_hosts(monkeypatch) -> None:
    class Widget:
        def __init__(self, *, visible: bool = True, width: int = 10, height: int = 20) -> None:
            self._visible = visible
            self._width = width
            self._height = height

        def isVisible(self) -> bool:  # noqa: N802
            return self._visible

        def width(self) -> int:
            return self._width

        def height(self) -> int:
            return self._height

        def geometry(self) -> object:
            return type("Geometry", (), {"x": lambda self: 1, "y": lambda self: 2})()

    valid_spec = StackSpec(
        id="valid",
        layout=RailLayout(anchor="viewport.left.top"),
        items=(),
    )
    hosts = {
        "none": type("Host", (), {"widget": None, "spec": valid_spec})(),
        "hidden": type("Host", (), {"widget": Widget(visible=False), "spec": valid_spec})(),
        "zero": type("Host", (), {"widget": Widget(width=0), "spec": valid_spec})(),
        "nospec": type("Host", (), {"widget": Widget(), "spec": None})(),
        "valid": type("Host", (), {"widget": Widget(), "spec": valid_spec})(),
    }
    monkeypatch.setattr(edit_mode, "_runtime_hosts", lambda: hosts)

    frames = edit_mode._rail_frame_infos(object(), object())

    assert [frame.preset_id for frame in frames] == ["valid"]


def test_safe_widget_helpers_handle_missing_and_raising_methods() -> None:
    class Raising:
        def isVisible(self) -> bool:  # noqa: N802
            raise RuntimeError("deleted")

        def width(self) -> int:
            raise RuntimeError("deleted")

    assert edit_mode._safe_widget_visible(object()) is False
    assert edit_mode._safe_widget_visible(Raising()) is False
    assert edit_mode._safe_widget_dimension(object(), "width") == 0
    assert edit_mode._safe_widget_dimension(Raising(), "width") == 0


def test_set_edit_mode_options_refreshes_active_host(monkeypatch) -> None:
    class Host:
        frames = ()

        def __init__(self) -> None:
            self.settings = None

        def set_settings(self, settings: edit_mode.EditModeSettings) -> None:
            self.settings = settings

    host = Host()
    monkeypatch.setattr(edit_mode, "_EDIT_HOST", host)

    state = edit_mode.set_edit_mode_options(
        show_grid=False,
        snap_to_grid=True,
        sticky_frames=True,
        grid_size=1000,
    )

    assert state.enabled is True
    assert state.settings.show_grid is False
    assert state.settings.snap_to_grid is True
    assert state.settings.sticky_frames is True
    assert state.settings.grid_size == 512
    assert host.settings == state.settings

    monkeypatch.setattr(edit_mode, "_EDIT_HOST", None)
    edit_mode.set_edit_mode_options(
        show_grid=True,
        snap_to_grid=False,
        sticky_frames=False,
        grid_size=edit_mode.DEFAULT_GRID_SIZE,
    )


def test_enter_exit_and_toggle_edit_mode_use_host(monkeypatch) -> None:
    events: list[tuple[str, object]] = []

    class FakeHost:
        def __init__(self, **kwargs: object) -> None:
            events.append(("init", kwargs))
            self.frames = ("frame",)

        def show(self) -> None:
            events.append(("show", None))

        def close(self) -> None:
            events.append(("close", None))

        def refresh(self) -> None:
            events.append(("refresh", None))

    monkeypatch.setattr(edit_mode, "EditModeOverlayHost", FakeHost)
    monkeypatch.setattr(edit_mode, "_EDIT_HOST", None)

    state = edit_mode.enter_edit_mode(
        panel="modelPanel4",
        settings=edit_mode.EditModeSettings(grid_size=10),
    )
    assert state.enabled is True
    assert state.rail_count == 1

    state = edit_mode.enter_edit_mode(panel="modelPanel2")
    assert state.enabled is True
    assert events.count(("close", None)) == 1

    assert edit_mode.toggle_edit_mode().enabled is False
    assert edit_mode.toggle_edit_mode(panel="modelPanel3").enabled is True
    assert edit_mode.refresh_edit_mode().enabled is True

    edit_mode.exit_edit_mode()
    edit_mode.set_edit_mode_options(grid_size=edit_mode.DEFAULT_GRID_SIZE)


def test_select_edit_mode_rail_forwards_to_active_host(monkeypatch) -> None:
    class Host:
        frames = ()

        def __init__(self) -> None:
            self.selected = ""

        def select_rail(self, preset_id: str) -> None:
            self.selected = preset_id

    host = Host()
    monkeypatch.setattr(edit_mode, "_EDIT_HOST", host)

    state = edit_mode.select_edit_mode_rail("transform_stack")

    assert state.selected_preset_id == "transform_stack"
    assert host.selected == "transform_stack"
    monkeypatch.setattr(edit_mode, "_EDIT_HOST", None)
    edit_mode.select_edit_mode_rail("")


def test_refresh_clears_stale_selected_id(monkeypatch) -> None:
    frame = edit_mode.RailFrameInfo(
        preset_id="visible",
        label="Visible",
        x=50,
        y=60,
        width=40,
        height=80,
        anchor="viewport.left.top",
        offset=(10, 20),
        orientation="vertical",
        rows=1,
        columns=1,
        scale=1.0,
        opacity=1.0,
        locked=False,
    )
    host = object.__new__(edit_mode.EditModeOverlayHost)
    host.qt = object()
    host.parent = object()
    host._original_offsets = {}
    host.widget = type("Widget", (), {"refresh_from_host": lambda self: None})()
    monkeypatch.setattr(edit_mode, "_SELECTED_PRESET_ID", "missing")
    monkeypatch.setattr(edit_mode, "_rail_frame_infos", lambda *_args: (frame,))

    host.refresh()

    assert edit_mode._SELECTED_PRESET_ID == ""


def test_select_and_nudge_unlocked_frame_updates_host(monkeypatch) -> None:
    frame = edit_mode.RailFrameInfo(
        preset_id="custom",
        label="Custom",
        x=50,
        y=60,
        width=40,
        height=80,
        anchor="viewport.left.top",
        offset=(10, 20),
        orientation="vertical",
        rows=1,
        columns=1,
        scale=1.0,
        opacity=1.0,
        locked=False,
    )
    updates = []

    class RuntimeHost:
        def update_layout_offset(self, offset: tuple[int, int]) -> None:
            updates.append(offset)

    host = object.__new__(edit_mode.EditModeOverlayHost)
    host.frames = (frame,)
    host._original_offsets = {"custom": (10, 20)}
    host.widget = type("Widget", (), {"refresh_from_host": lambda self: None})()
    host.select_rail("custom")
    host.refresh = lambda: None
    monkeypatch.setattr(edit_mode, "_runtime_hosts", lambda: {"custom": RuntimeHost()})

    host.nudge_selected(5, -2)
    host.reset_selected_position()

    assert updates == [(15, 18), (10, 20)]


def test_set_host_offset_falls_back_to_spec_replacement() -> None:
    positioned = []

    class RuntimeHost:
        def __init__(self) -> None:
            self.spec = StackSpec(
                id="fallback",
                layout=RailLayout(anchor="viewport.left.top", offset=(0, 0)),
                items=(),
            )

        def position(self) -> None:
            positioned.append(True)

    host = RuntimeHost()

    edit_mode._set_host_offset(host, (3, 4))
    edit_mode._set_host_offset(object(), (5, 6))

    assert host.spec.layout.offset == (3, 4)
    assert positioned == [True]


def test_save_edit_mode_layout_writes_selected_runtime_spec_to_user_preset(
    monkeypatch,
    tmp_path,
) -> None:
    frame = edit_mode.RailFrameInfo(
        preset_id="custom_layout",
        label="Custom Layout",
        x=50,
        y=60,
        width=40,
        height=80,
        anchor="viewport.left.top",
        offset=(12, 24),
        orientation="vertical",
        rows=1,
        columns=1,
        scale=1.0,
        opacity=1.0,
        locked=False,
        source_layer="runtime",
    )
    spec = StackSpec(
        id="custom_layout",
        layout=RailLayout(anchor="viewport.left.top", offset=(12, 24)),
        items=(
            StackItem(
                type="button",
                id="custom_layout.move",
                label="Move",
                action="maya.tool.move",
            ),
        ),
    )
    runtime_host = type("RuntimeHost", (), {"spec": spec})()
    host = object.__new__(edit_mode.EditModeOverlayHost)
    host.frames = (frame,)
    monkeypatch.setattr(edit_mode, "_EDIT_HOST", host)
    monkeypatch.setattr(edit_mode, "_SELECTED_PRESET_ID", "custom_layout")
    monkeypatch.setattr(edit_mode, "_runtime_hosts", lambda: {"custom_layout": runtime_host})

    path = edit_mode.save_edit_mode_layout(user_preset_dir=tmp_path)

    saved = load_user_preset("custom_layout", preset_dir=tmp_path)
    assert path == tmp_path / "custom_layout.json"
    assert saved.layout.offset == (12, 24)
    assert saved.items[0].id == "custom_layout.move"


def test_save_edit_mode_layout_uses_runtime_host_user_preset_dir(
    monkeypatch,
    tmp_path,
) -> None:
    frame = edit_mode.RailFrameInfo(
        preset_id="custom_store_layout",
        label="Custom Store Layout",
        x=50,
        y=60,
        width=40,
        height=80,
        anchor="viewport.left.top",
        offset=(12, 24),
        orientation="vertical",
        rows=1,
        columns=1,
        scale=1.0,
        opacity=1.0,
        locked=False,
        source_layer="user",
    )
    spec = StackSpec(
        id="custom_store_layout",
        layout=RailLayout(anchor="viewport.left.top", offset=(12, 24)),
        items=(
            StackItem(
                type="button",
                id="custom_store_layout.move",
                label="Move",
                action="maya.tool.move",
            ),
        ),
    )
    runtime_host = type(
        "RuntimeHost",
        (),
        {"spec": spec, "user_preset_dir": tmp_path},
    )()
    host = object.__new__(edit_mode.EditModeOverlayHost)
    host.frames = (frame,)
    monkeypatch.setattr(edit_mode, "_EDIT_HOST", host)
    monkeypatch.setattr(edit_mode, "_SELECTED_PRESET_ID", "custom_store_layout")
    monkeypatch.setattr(
        edit_mode,
        "_runtime_hosts",
        lambda: {"custom_store_layout": runtime_host},
    )

    path = edit_mode.save_edit_mode_layout()

    assert path == tmp_path / "custom_store_layout.json"
    assert load_user_preset("custom_store_layout", preset_dir=tmp_path).layout.offset == (
        12,
        24,
    )


def test_preset_source_layer_uses_custom_user_preset_dir(tmp_path) -> None:
    save_user_preset(
        StackSpec(
            id="custom_source",
            layout=RailLayout(anchor="viewport.left.top"),
            items=(
                StackItem(
                    type="button",
                    id="custom_source.move",
                    label="Move",
                    action="maya.tool.move",
                ),
            ),
        ),
        preset_dir=tmp_path,
    )

    assert (
        edit_mode._preset_source_layer("custom_source", user_preset_dir=tmp_path)
        == "user"
    )


def test_preset_source_layer_detects_studio_runtime_host(
    monkeypatch,
    tmp_path,
) -> None:
    studio_dir = tmp_path / "studio"
    save_user_preset(
        StackSpec(
            id="studio.tools",
            layout=RailLayout(anchor="viewport.right.center", locked=True),
            items=(
                StackItem(
                    type="button",
                    id="studio.tools.move",
                    label="Move",
                    action="maya.tool.move",
                ),
            ),
        ),
        preset_dir=studio_dir,
    )
    runtime_host = type("RuntimeHost", (), {"studio_preset_dir": studio_dir})()
    monkeypatch.setattr(
        edit_mode,
        "_runtime_hosts",
        lambda: {"studio.tools": runtime_host},
    )

    assert edit_mode._preset_source_layer("studio.tools") == "studio"


def test_save_edit_mode_layout_writes_builtin_user_override(
    monkeypatch,
    tmp_path,
) -> None:
    frame = edit_mode.RailFrameInfo(
        preset_id="transform_stack",
        label="Transform Stack",
        x=50,
        y=60,
        width=40,
        height=80,
        anchor="viewport.left.top",
        offset=(12, 24),
        orientation="vertical",
        rows=1,
        columns=1,
        scale=1.0,
        opacity=1.0,
        locked=False,
        source_layer="builtin",
    )
    runtime_host = type(
        "RuntimeHost",
        (),
        {
            "spec": StackSpec(
                id="transform_stack",
                layout=RailLayout(anchor="viewport.left.top", offset=(12, 24)),
                items=(
                    StackItem(
                        type="button",
                        id="transform_stack.move",
                        label="Move",
                        action="maya.tool.move",
                    ),
                ),
            )
        },
    )()
    host = object.__new__(edit_mode.EditModeOverlayHost)
    host.frames = (frame,)
    monkeypatch.setattr(edit_mode, "_EDIT_HOST", host)
    monkeypatch.setattr(edit_mode, "_SELECTED_PRESET_ID", "transform_stack")
    monkeypatch.setattr(edit_mode, "_runtime_hosts", lambda: {"transform_stack": runtime_host})

    path = edit_mode.save_edit_mode_layout(user_preset_dir=tmp_path)
    saved = load_user_preset("transform_stack_user_override", preset_dir=tmp_path)

    assert path == tmp_path / "transform_stack_user_override.json"
    assert saved.id == "transform_stack_user_override"
    assert saved.layout.offset == (12, 24)
    assert saved.layout.locked is False
    assert saved.items[0].id == "transform_stack_user_override.move"


def test_save_edit_mode_layout_writes_studio_user_override(
    monkeypatch,
    tmp_path,
) -> None:
    frame = edit_mode.RailFrameInfo(
        preset_id="studio.tools",
        label="Studio Tools",
        x=50,
        y=60,
        width=40,
        height=80,
        anchor="viewport.right.center",
        offset=(12, 24),
        orientation="vertical",
        rows=1,
        columns=1,
        scale=1.0,
        opacity=1.0,
        locked=False,
        source_layer="studio",
    )
    runtime_host = type(
        "RuntimeHost",
        (),
        {
            "spec": StackSpec(
                id="studio.tools",
                layout=RailLayout(
                    anchor="viewport.right.center",
                    offset=(12, 24),
                    locked=True,
                ),
                items=(
                    StackItem(
                        type="button",
                        id="studio.tools.move",
                        label="Move",
                        action="maya.tool.move",
                    ),
                ),
            )
        },
    )()
    host = object.__new__(edit_mode.EditModeOverlayHost)
    host.frames = (frame,)
    monkeypatch.setattr(edit_mode, "_EDIT_HOST", host)
    monkeypatch.setattr(edit_mode, "_SELECTED_PRESET_ID", "studio.tools")
    monkeypatch.setattr(
        edit_mode,
        "_runtime_hosts",
        lambda: {"studio.tools": runtime_host},
    )

    path = edit_mode.save_edit_mode_layout(user_preset_dir=tmp_path)
    saved = load_user_preset("studio.tools_user_override", preset_dir=tmp_path)

    assert path == tmp_path / "studio.tools_user_override.json"
    assert saved.id == "studio.tools_user_override"
    assert saved.layout.offset == (12, 24)
    assert saved.layout.locked is False
    assert saved.items[0].id == "studio.tools_user_override.move"


def test_save_edit_mode_layout_refuses_locked_frames(monkeypatch) -> None:
    frame = edit_mode.RailFrameInfo(
        preset_id="locked",
        label="Locked",
        x=50,
        y=60,
        width=40,
        height=80,
        anchor="viewport.left.top",
        offset=(12, 24),
        orientation="vertical",
        rows=1,
        columns=1,
        scale=1.0,
        opacity=1.0,
        locked=True,
        source_layer="builtin",
    )
    runtime_host = type("RuntimeHost", (), {"spec": object()})()
    host = object.__new__(edit_mode.EditModeOverlayHost)
    host.frames = (frame,)
    monkeypatch.setattr(edit_mode, "_EDIT_HOST", host)
    monkeypatch.setattr(edit_mode, "_SELECTED_PRESET_ID", "locked")
    monkeypatch.setattr(edit_mode, "_runtime_hosts", lambda: {"locked": runtime_host})

    try:
        edit_mode.save_edit_mode_layout()
    except ValueError as exc:
        assert "locked" in str(exc)
    else:
        raise AssertionError("Locked Edit Mode layout save unexpectedly succeeded.")


def test_edit_mode_options_toggle_edge_tab_collapsed_state(monkeypatch) -> None:
    frame = edit_mode.RailFrameInfo(
        preset_id="edge_tab",
        label="Edge Tab",
        x=50,
        y=60,
        width=40,
        height=80,
        anchor="viewport.left.center",
        offset=(12, 24),
        orientation="vertical",
        rows=1,
        columns=1,
        scale=1.0,
        opacity=0.92,
        locked=False,
        source_layer="runtime",
    )
    runtime_host = type(
        "RuntimeHost",
        (),
        {},
    )()
    runtime_host.spec = StackSpec(
        id="edge_tab",
        layout=RailLayout(anchor="viewport.left.center", opacity=0.92),
        items=(StackItem(type="button", id="edge_tab.a", label="A"),),
    )
    runtime_host._collapsed = False
    collapsed_updates = []

    def set_collapsed(value: bool, *, persist_default: bool = False) -> bool:
        runtime_host._collapsed = value
        collapsed_updates.append((value, persist_default))
        return True

    runtime_host.set_collapsed = set_collapsed
    host = object.__new__(edit_mode.EditModeOverlayHost)
    host.frames = (frame,)
    host.widget = type("Widget", (), {"refresh_from_host": lambda self: None})()
    host.refresh = lambda: None
    monkeypatch.setattr(edit_mode, "_runtime_hosts", lambda: {"edge_tab": runtime_host})
    host.select_rail("edge_tab")

    assert host.toggle_selected_edge_tab() is True
    assert runtime_host.spec.layout.opacity == 0.92
    assert runtime_host.spec.collapse == RailCollapse(
        enabled=True,
        edge="left",
        default_collapsed=True,
    )
    assert collapsed_updates == [(True, True)]
    assert host.toggle_selected_edge_tab() is True
    assert runtime_host.spec.collapse.default_collapsed is False
    assert collapsed_updates == [(True, True), (False, True)]


def test_edit_mode_options_toggle_configured_collapse_for_center_anchor(monkeypatch) -> None:
    frame = edit_mode.RailFrameInfo(
        preset_id="center_tab",
        label="Center Tab",
        x=50,
        y=60,
        width=40,
        height=80,
        anchor="viewport.center",
        offset=(12, 24),
        orientation="vertical",
        rows=1,
        columns=1,
        scale=1.0,
        opacity=0.92,
        locked=False,
        collapse_enabled=True,
        collapse_edge="bottom",
        source_layer="runtime",
    )
    runtime_host = type("RuntimeHost", (), {})()
    runtime_host.spec = StackSpec(
        id="center_tab",
        layout=RailLayout(anchor="viewport.center", opacity=0.92),
        items=(StackItem(type="button", id="center_tab.a", label="A"),),
        collapse=RailCollapse(enabled=True, edge="bottom"),
    )
    runtime_host._collapsed = False
    collapsed_updates = []

    def set_collapsed(value: bool, *, persist_default: bool = False) -> bool:
        runtime_host._collapsed = value
        collapsed_updates.append((value, persist_default))
        return True

    runtime_host.set_collapsed = set_collapsed
    host = object.__new__(edit_mode.EditModeOverlayHost)
    host.frames = (frame,)
    host.widget = type("Widget", (), {"refresh_from_host": lambda self: None})()
    host.refresh = lambda: None
    monkeypatch.setattr(edit_mode, "_runtime_hosts", lambda: {"center_tab": runtime_host})
    host.select_rail("center_tab")

    assert host.toggle_selected_edge_tab() is True
    assert runtime_host.spec.collapse.edge == "bottom"
    assert runtime_host.spec.collapse.default_collapsed is True
    assert collapsed_updates == [(True, True)]


def test_locked_frame_does_not_nudge(monkeypatch) -> None:
    frame = edit_mode.RailFrameInfo(
        preset_id="locked",
        label="Locked",
        x=50,
        y=60,
        width=40,
        height=80,
        anchor="viewport.left.top",
        offset=(10, 20),
        orientation="vertical",
        rows=1,
        columns=1,
        scale=1.0,
        opacity=1.0,
        locked=True,
    )
    host = object.__new__(edit_mode.EditModeOverlayHost)
    host.frames = (frame,)
    host._original_offsets = {"locked": (10, 20)}
    host.widget = type("Widget", (), {"refresh_from_host": lambda self: None})()
    host.select_rail("locked")
    monkeypatch.setattr(
        edit_mode,
        "_runtime_hosts",
        lambda: {"locked": object()},
    )

    host.nudge_selected(5, -2)

    assert frame.offset == (10, 20)


def test_toggle_selected_lock_updates_runtime_spec(monkeypatch) -> None:
    frame = edit_mode.RailFrameInfo(
        preset_id="locked",
        label="Locked",
        x=50,
        y=60,
        width=40,
        height=80,
        anchor="viewport.left.top",
        offset=(10, 20),
        orientation="vertical",
        rows=1,
        columns=1,
        scale=1.0,
        opacity=1.0,
        locked=True,
    )
    runtime_host = type("RuntimeHost", (), {})()
    runtime_host.spec = StackSpec(
        id="locked",
        layout=RailLayout(anchor="viewport.left.top", locked=True),
        items=(StackItem(type="button", id="locked.a", label="A"),),
    )
    runtime_host._rebuild_widget = lambda _state: None

    class Widget:
        def __init__(self) -> None:
            self.raised = 0

        def refresh_from_host(self) -> None:
            pass

        def raise_(self) -> None:
            self.raised += 1

    widget = Widget()
    host = object.__new__(edit_mode.EditModeOverlayHost)
    host.qt = object()
    host.parent = object()
    host.frames = (frame,)
    host._original_offsets = {}
    host._qt_widget_is_valid = lambda _widget: True
    host.widget = widget
    monkeypatch.setattr(edit_mode, "_runtime_hosts", lambda: {"locked": runtime_host})
    monkeypatch.setattr(
        edit_mode,
        "_rail_frame_infos",
        lambda _qt, _parent: (replace(frame, locked=False),),
    )
    host.select_rail("locked")

    assert host.toggle_selected_lock() is True
    assert runtime_host.spec.layout.locked is False
    assert widget.raised == 1


def test_runtime_hosts_uses_runtime_registry(monkeypatch) -> None:
    monkeypatch.setattr(
        runtime,
        "_active_overlay_hosts",
        lambda: (("one", object()),),
    )

    assert tuple(edit_mode._runtime_hosts()) == ("one",)


def test_runtime_refresh_edit_mode_ignores_refresh_errors(monkeypatch) -> None:
    refreshed = []
    monkeypatch.setattr(edit_mode, "refresh_edit_mode", lambda: refreshed.append(True))

    runtime._refresh_edit_mode()
    assert refreshed == [True]

    monkeypatch.setattr(
        edit_mode,
        "refresh_edit_mode",
        lambda: (_ for _ in ()).throw(RuntimeError("closed")),
    )
    runtime._refresh_edit_mode()


def test_runtime_active_overlay_hosts_returns_current_registry(monkeypatch) -> None:
    host = object()
    monkeypatch.setattr(runtime, "_OVERLAYS", {"preset": host})

    assert runtime._active_overlay_hosts() == (("preset", host),)


def test_popover_position_and_panel_style() -> None:
    class Qt:
        class QtCore:
            class QPoint:
                def __init__(self, x_pos: int, y_pos: int) -> None:
                    self.value = (x_pos, y_pos)

                def x(self) -> int:
                    return self.value[0]

                def y(self) -> int:
                    return self.value[1]

    class Canvas:
        _host = type("Host", (), {"qt": Qt})()

        def width(self) -> int:
            return 180

        def height(self) -> int:
            return 140

    class Panel:
        def width(self) -> int:
            return 80

        def height(self) -> int:
            return 60

    frame = edit_mode.RailFrameInfo(
        preset_id="frame",
        label="Frame",
        x=150,
        y=120,
        width=40,
        height=30,
        anchor="viewport.left.top",
        offset=(0, 0),
        orientation="vertical",
        rows=1,
        columns=1,
        scale=1.0,
        opacity=1.0,
        locked=False,
    )

    assert edit_mode._popover_position(Canvas(), frame, 80, 60).value == (92, 72)
    assert (
        edit_mode._clamped_panel_position(
            Canvas(),
            Panel(),
            Qt.QtCore.QPoint(-20, 200),
        ).value
        == (8, 72)
    )
    assert edit_mode._panel_width(0, 540) == 540
    assert edit_mode._panel_width(500, 540) == 484
    assert "Sticky" not in edit_mode._panel_style_sheet()
    assert f"color: {edit_mode.DEFAULT_THEME.accent_line};" in edit_mode._panel_style_sheet()
    assert edit_mode._frame_label_font_size(frame) == 10
    assert edit_mode._frame_label_font_size(replace(frame, label="Very Long Label", width=20)) == 6


def test_panel_summary_and_lock_state_helpers_are_readable_without_selection() -> None:
    frame = edit_mode.RailFrameInfo(
        preset_id="frame",
        label="Frame",
        x=150,
        y=120,
        width=40,
        height=30,
        anchor="viewport.left.top",
        offset=(0, 0),
        orientation="vertical",
        rows=1,
        columns=1,
        scale=1.0,
        opacity=1.0,
        locked=False,
    )

    assert edit_mode._panel_summary_text(None, 1) == "1 rail frame(s) | no frame selected"
    assert edit_mode._lock_button_accessible_name(None) == "No rail selected"
    assert edit_mode._lock_button_accessible_name(frame) == "Unlocked rail"
    assert edit_mode._lock_button_accessible_name(replace(frame, locked=True)) == "Locked rail"
    assert "Select a rail" in edit_mode._lock_button_tooltip(None)
    assert "Click to lock" in edit_mode._lock_button_tooltip(frame)
    assert "Click to unlock" in edit_mode._lock_button_tooltip(replace(frame, locked=True))
    assert (
        edit_mode._panel_summary_text(frame, 1)
        == "Frame\nruntime | viewport.left.top | x 150, y 120"
    )


def test_edit_mode_paint_colors_use_green_accent_and_black_grid() -> None:
    events: list[tuple[str, object]] = []

    class Color:
        def __init__(self, red: int, green: int, blue: int, alpha: int = 255) -> None:
            self.value = (red, green, blue, alpha)

    class Pen:
        def __init__(self, color: Color, width: int = 1) -> None:
            self.color = color
            self.width = width

    class Rect:
        def __init__(self, x: int = 0, y: int = 0, width: int = 96, height: int = 64) -> None:
            self.value = (x, y, width, height)

        def x(self) -> int:
            return self.value[0]

        def y(self) -> int:
            return self.value[1]

        def width(self) -> int:
            return self.value[2]

        def height(self) -> int:
            return self.value[3]

        def adjusted(self, left: int, top: int, right: int, bottom: int) -> Rect:
            return Rect(left, top, right, bottom)

    class Font:
        def setBold(self, _enabled: bool) -> None:  # noqa: N802
            pass

        def setPointSize(self, _size: int) -> None:  # noqa: N802
            pass

    class Painter:
        def setPen(self, pen: Pen | Color) -> None:  # noqa: N802
            if isinstance(pen, Pen):
                events.append(("pen", (pen.color.value, pen.width)))
            else:
                events.append(("color", pen.value))

        def drawLine(self, *args: int) -> None:  # noqa: N802
            events.append(("line", args))

        def fillRect(self, _rect: Rect, color: Color) -> None:  # noqa: N802
            events.append(("fill", color.value))

        def drawRect(self, _rect: Rect) -> None:  # noqa: N802
            events.append(("rect", None))

        def font(self) -> Font:
            return Font()

        def setFont(self, _font: Font) -> None:  # noqa: N802
            pass

        def drawText(self, *_args: object) -> None:  # noqa: N802
            events.append(("text", _args[-1]))

    class Qt:
        class QtCore:
            QRect = Rect

            class Qt:
                AlignCenter = 1
                TextWordWrap = 2

        class QtGui:
            QColor = Color
            QPen = Pen

    frame = edit_mode.RailFrameInfo(
        preset_id="frame",
        label="Frame",
        x=4,
        y=6,
        width=40,
        height=30,
        anchor="viewport.left.top",
        offset=(0, 0),
        orientation="horizontal",
        rows=1,
        columns=4,
        scale=1.0,
        opacity=1.0,
        locked=False,
    )

    edit_mode._paint_grid(Qt, Painter(), Rect(), 32)
    edit_mode._paint_frame(Qt, Painter(), frame, selected=True)
    edit_mode._paint_guides(
        Qt,
        Painter(),
        Rect(),
        frame,
        (frame,),
        edit_mode.EditModeSettings(sticky_frames=True),
    )

    assert ("pen", ((0, 0, 0, 125), 1)) in events
    assert ("pen", ((0, 0, 0, 70), 1)) in events
    assert ("pen", ((140, 207, 63, 255), 2)) in events
    assert ("pen", ((140, 207, 63, 115), 1)) in events
    assert ("color", (140, 207, 63, 255)) in events
    assert not any(
        event[0] == "text" and "Locked" in str(event[1])
        for event in events
    )


def test_require_cmds_uses_supplied_module() -> None:
    cmds = object()

    assert edit_mode._require_cmds(cmds) is cmds


def test_require_cmds_imports_maya_cmds(monkeypatch) -> None:
    maya_module = ModuleType("maya")
    cmds = object()
    monkeypatch.setitem(sys.modules, "maya", maya_module)
    monkeypatch.setitem(sys.modules, "maya.cmds", cmds)

    assert edit_mode._require_cmds() is cmds


def test_overlay_host_update_layout_offset_repositions() -> None:
    host = object.__new__(overlay.ViewportOverlayHost)
    host.spec = StackSpec(
        id="offset",
        layout=RailLayout(anchor="viewport.left.top", offset=(0, 0)),
        items=(),
    )
    positioned = []
    host.position = lambda: positioned.append(True)

    assert host.update_layout_offset((8, 9)) == (8, 9)
    assert host.spec.layout.offset == (8, 9)
    assert positioned == [True]
