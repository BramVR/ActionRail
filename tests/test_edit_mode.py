from __future__ import annotations

import sys
from dataclasses import replace
from types import ModuleType

import actionrail.edit_mode as edit_mode
import actionrail.overlay as overlay
import actionrail.runtime as runtime
from actionrail.authoring import load_user_preset, save_user_preset
from actionrail.spec import RailLayout, StackItem, StackSpec


def test_edit_mode_settings_clamp_grid_size() -> None:
    assert edit_mode.EditModeSettings().normalized().grid_size == 32
    assert edit_mode.EditModeSettings(grid_size=-1).normalized().grid_size == 16
    assert edit_mode.EditModeSettings(grid_size=999).normalized().grid_size == 512
    assert edit_mode.EditModeSettings(grid_size=32).normalized().grid_size == 32


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


def test_refresh_clears_stale_selected_and_options_ids(monkeypatch) -> None:
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
    monkeypatch.setattr(edit_mode, "_OPTIONS_PRESET_ID", "missing")
    monkeypatch.setattr(edit_mode, "_rail_frame_infos", lambda *_args: (frame,))

    host.refresh()

    assert edit_mode._SELECTED_PRESET_ID == ""
    assert edit_mode._OPTIONS_PRESET_ID == ""


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


def test_edit_mode_options_can_add_remove_and_reorder_slots(monkeypatch) -> None:
    frame = edit_mode.RailFrameInfo(
        preset_id="custom_slots",
        label="Custom Slots",
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
        opacity=1.0,
        locked=False,
        source_layer="runtime",
    )

    class RuntimeHost:
        def __init__(self) -> None:
            self.spec = StackSpec(
                id="custom_slots",
                layout=RailLayout(anchor="viewport.left.center", offset=(12, 24)),
                items=(
                    StackItem(type="button", id="custom_slots.a", label="A"),
                    StackItem(type="button", id="custom_slots.b", label="B"),
                    StackItem(type="spacer", id="custom_slots.gap", size=8),
                ),
            )
            self.rebuilds = 0

        def _rebuild_widget(self, _state: object) -> None:
            self.rebuilds += 1

    runtime_host = RuntimeHost()
    host = object.__new__(edit_mode.EditModeOverlayHost)
    host.frames = (frame,)
    host.widget = type("Widget", (), {"refresh_from_host": lambda self: None})()
    host.refresh = lambda: None
    monkeypatch.setattr(edit_mode, "_runtime_hosts", lambda: {"custom_slots": runtime_host})
    host.select_rail("custom_slots")

    assert host.reorder_selected_slot(-1) is True
    assert [item.id for item in runtime_host.spec.items] == [
        "custom_slots.b",
        "custom_slots.a",
        "custom_slots.gap",
    ]
    assert host.add_slot_to_selected() is True
    assert runtime_host.spec.items[-1].id == "custom_slots.slot_1"
    assert host.remove_slot_from_selected() is True
    assert [item.id for item in runtime_host.spec.items] == [
        "custom_slots.b",
        "custom_slots.a",
        "custom_slots.gap",
    ]
    assert runtime_host.rebuilds == 3


def test_edit_mode_options_toggle_edge_tab_opacity(monkeypatch) -> None:
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
        {
            "spec": StackSpec(
                id="edge_tab",
                layout=RailLayout(anchor="viewport.left.center", opacity=0.92),
                items=(StackItem(type="button", id="edge_tab.a", label="A"),),
            )
        },
    )()
    host = object.__new__(edit_mode.EditModeOverlayHost)
    host.frames = (frame,)
    host.widget = type("Widget", (), {"refresh_from_host": lambda self: None})()
    host.refresh = lambda: None
    monkeypatch.setattr(edit_mode, "_runtime_hosts", lambda: {"edge_tab": runtime_host})
    host.select_rail("edge_tab")

    assert host.toggle_selected_edge_tab() is True
    assert runtime_host.spec.layout.opacity == 0.35
    assert host.toggle_selected_edge_tab() is True
    assert runtime_host.spec.layout.opacity == 0.92


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

    class Canvas:
        _host = type("Host", (), {"qt": Qt})()

        def width(self) -> int:
            return 180

        def height(self) -> int:
            return 140

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
    assert edit_mode._panel_width(0, 540) == 540
    assert edit_mode._panel_width(500, 540) == 484
    assert edit_mode._options_popover_position(Canvas(), frame, 80, 60).value == (92, 72)
    assert "Sticky" not in edit_mode._panel_style_sheet()
    assert edit_mode._frame_label_font_size(frame) == 10
    assert edit_mode._frame_label_font_size(replace(frame, label="Very Long Label", width=20)) == 6


def test_panel_summary_and_lock_text_are_readable_without_selection() -> None:
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

    assert edit_mode._panel_summary_text(None, 1, "") == "1 rail frame(s) | no frame selected"
    assert edit_mode._lock_button_text(None) == "No selection"
    assert edit_mode._lock_button_text(frame) == "Unlocked"
    assert (
        edit_mode._panel_summary_text(frame, 1, "frame")
        == "Frame\nruntime | viewport.left.top | x 150, y 120\noptions: frame"
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
