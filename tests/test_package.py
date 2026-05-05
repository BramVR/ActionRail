from __future__ import annotations

import sys
from collections.abc import Iterator
from types import ModuleType

import pytest

import actionrail.runtime as runtime
from actionrail.authoring import DraftRail, DraftSlot, save_user_preset
from actionrail.spec import RailLayout, StackItem, StackSpec


@pytest.fixture(autouse=True)
def clear_runtime_overlays() -> Iterator[None]:
    runtime.hide_all()
    yield
    runtime.hide_all()


def _empty_spec(preset_id: str) -> StackSpec:
    return StackSpec(
        id=preset_id,
        layout=RailLayout(anchor="viewport.left.center"),
        items=(StackItem(type="button", id=f"{preset_id}.slot", label="S"),),
    )


def test_package_imports_without_maya_or_qt() -> None:
    import actionrail

    assert actionrail.__version__ == "0.1.0"
    assert callable(actionrail.about)
    assert callable(actionrail.show_example)
    assert callable(actionrail.show_preset)
    assert callable(actionrail.hide_all)
    assert callable(actionrail.reload)
    assert callable(actionrail.active_overlay_ids)
    assert callable(actionrail.active_overlay_states)
    assert callable(actionrail.show_spec)
    assert actionrail.StackItem is StackItem
    assert actionrail.StackSpec is StackSpec
    assert actionrail.RailLayout is RailLayout
    assert callable(actionrail.build_draft_spec)
    assert callable(actionrail.save_user_preset)
    assert callable(actionrail.load_user_preset)
    assert callable(actionrail.resolve_preset)
    assert callable(actionrail.preset_ids)
    assert callable(actionrail.parse_stack_spec)
    assert callable(actionrail.load_preset)
    assert callable(actionrail.collect_diagnostics)
    assert callable(actionrail.last_report)
    assert callable(actionrail.show_last_report)
    assert callable(actionrail.safe_start)
    assert callable(actionrail.preview_quick_create_draft)
    assert callable(actionrail.clear_quick_create_previews)
    assert callable(actionrail.save_quick_create_preset)
    assert callable(actionrail.load_quick_create_preset)
    assert callable(actionrail.diagnose_icon_import_from_maya)


def test_runtime_overlay_lifecycle_uses_overlay_host(monkeypatch) -> None:
    events: list[tuple[str, str]] = []

    class FakeHost:
        def __init__(self, spec, *, panel=None, registry=None) -> None:
            self.spec = spec
            self.panel = panel
            self.registry = registry
            self.widget = None
            self._filter_targets = ()
            self._predicate_refresh_timer = None

        def show(self) -> None:
            events.append(("show", self.spec.id))

        def close(self) -> None:
            events.append(("close", self.spec.id))

        def update_slot_key_label(self, slot_id: str, key_label: str) -> int:
            events.append((slot_id, key_label))
            return 1

    fake_overlay = ModuleType("actionrail.overlay")
    fake_overlay.ViewportOverlayHost = FakeHost
    fake_overlay._qt_widget_is_valid = lambda widget: True
    monkeypatch.setitem(sys.modules, "actionrail.overlay", fake_overlay)

    host = runtime.show_example("transform_stack", panel="modelPanel4")

    assert isinstance(host, FakeHost)
    assert runtime.active_overlay_ids() == ("transform_stack",)
    assert runtime.update_slot_key_label("transform_stack", "set_key", "K") == 1
    assert events == [
        ("show", "transform_stack"),
        ("transform_stack.set_key", "K"),
    ]

    replacement = runtime.reload("transform_stack", panel="modelPanel5")

    assert isinstance(replacement, FakeHost)
    assert replacement.panel == "modelPanel5"
    assert events[-2:] == [("close", "transform_stack"), ("show", "transform_stack")]

    runtime.hide_all()

    assert runtime.active_overlay_ids() == ()
    assert events[-1] == ("close", "transform_stack")


def test_runtime_show_spec_supports_user_authored_specs(monkeypatch) -> None:
    events: list[tuple[str, str]] = []

    class FakeHost:
        def __init__(self, spec, *, panel=None, registry=None) -> None:
            self.spec = spec
            self.panel = panel
            self.registry = registry
            self.widget = None
            self._filter_targets = ()
            self._predicate_refresh_timer = None

        def show(self) -> None:
            events.append(("show", f"{self.spec.id}:{self.panel}"))

        def close(self) -> None:
            events.append(("close", self.spec.id))

    fake_overlay = ModuleType("actionrail.overlay")
    fake_overlay.ViewportOverlayHost = FakeHost
    fake_overlay._qt_widget_is_valid = lambda widget: True
    monkeypatch.setitem(sys.modules, "actionrail.overlay", fake_overlay)

    spec = StackSpec(
        id="custom_tools",
        layout=RailLayout(anchor="viewport.bottom.center", orientation="horizontal"),
        items=(StackItem(type="button", id="custom_tools.key", label="K"),),
    )

    first = runtime.show_spec(spec, panel="modelPanel4")
    replacement = runtime.show_spec(spec, panel="modelPanel5")

    assert isinstance(first, FakeHost)
    assert isinstance(replacement, FakeHost)
    assert runtime.active_overlay_ids() == ("custom_tools",)
    assert events == [
        ("show", "custom_tools:modelPanel4"),
        ("close", "custom_tools"),
        ("show", "custom_tools:modelPanel5"),
    ]


def test_runtime_show_preset_and_reload_resolve_user_presets(tmp_path, monkeypatch) -> None:
    save_user_preset(
        DraftRail(
            id="artist_tools",
            slots=(DraftSlot(id="move", label="M", action="maya.tool.move"),),
        ),
        preset_dir=tmp_path,
    )
    events: list[tuple[str, str]] = []

    class FakeHost:
        def __init__(self, spec, *, panel=None, registry=None) -> None:
            self.spec = spec
            self.panel = panel
            self.registry = registry
            self.widget = None
            self._filter_targets = ()
            self._predicate_refresh_timer = None

        def show(self) -> None:
            events.append(("show", f"{self.spec.id}:{self.panel}"))

        def close(self) -> None:
            events.append(("close", self.spec.id))

    fake_overlay = ModuleType("actionrail.overlay")
    fake_overlay.ViewportOverlayHost = FakeHost
    fake_overlay._qt_widget_is_valid = lambda widget: True
    monkeypatch.setitem(sys.modules, "actionrail.overlay", fake_overlay)

    runtime.show_preset("artist_tools", panel="modelPanel4", user_preset_dir=tmp_path)
    assert runtime._OVERLAYS["artist_tools"].user_preset_dir == tmp_path
    runtime.reload("artist_tools", panel="modelPanel5", user_preset_dir=tmp_path)
    assert runtime._OVERLAYS["artist_tools"].user_preset_dir == tmp_path

    assert events == [
        ("show", "artist_tools:modelPanel4"),
        ("close", "artist_tools"),
        ("show", "artist_tools:modelPanel5"),
    ]


def test_runtime_update_slot_key_label_ignores_missing_overlay() -> None:
    assert runtime.update_slot_key_label("transform_stack", "set_key", "K") == 0


def test_runtime_active_overlay_states_are_defensive(monkeypatch) -> None:
    class RaisingWidget:
        def isVisible(self) -> bool:  # noqa: N802
            raise RuntimeError("deleted")

    class RaisingTimer:
        def isActive(self) -> bool:  # noqa: N802
            raise RuntimeError("deleted")

    class PassiveHost:
        panel = "modelPanel4"
        widget = object()
        _filter_targets = ("viewport", "window")
        _predicate_refresh_timer = object()

        def show(self) -> None:
            pass

        def close(self) -> None:
            pass

    class RaisingHost:
        panel = "modelPanel5"
        widget = RaisingWidget()
        _filter_targets = None
        _predicate_refresh_timer = RaisingTimer()

        def show(self) -> None:
            pass

        def close(self) -> None:
            pass

    fake_overlay = ModuleType("actionrail.overlay")
    hosts = [PassiveHost(), RaisingHost()]

    class FakeHost:
        def __new__(cls, *_args, **_kwargs):
            _ = cls
            return hosts.pop(0)

    fake_overlay._qt_widget_is_valid = lambda widget: widget is not PassiveHost.widget
    fake_overlay.ViewportOverlayHost = FakeHost
    monkeypatch.setitem(sys.modules, "actionrail.overlay", fake_overlay)

    runtime.show_spec(_empty_spec("passive"))
    runtime.show_spec(_empty_spec("raising"))

    assert runtime.active_overlay_states() == (
        {
            "preset_id": "passive",
            "panel": "modelPanel4",
            "widget_visible": False,
            "widget_valid": False,
            "filter_target_count": 2,
            "predicate_timer_active": True,
        },
        {
            "preset_id": "raising",
            "panel": "modelPanel5",
            "widget_visible": False,
            "widget_valid": True,
            "filter_target_count": 0,
            "predicate_timer_active": True,
        },
    )


def test_runtime_active_overlay_states_handle_missing_and_invalid_qt(monkeypatch) -> None:
    class HostWithoutWidget:
        panel = ""
        widget = None
        _filter_targets = ()
        _predicate_refresh_timer = None

        def show(self) -> None:
            pass

        def close(self) -> None:
            pass

    class HostWithInvalidWidget:
        panel = ""
        widget = object()
        _filter_targets = ()
        _predicate_refresh_timer = None

        def show(self) -> None:
            pass

        def close(self) -> None:
            pass

    def raise_invalid(widget) -> bool:
        raise RuntimeError("Qt wrapper deleted")

    fake_overlay = ModuleType("actionrail.overlay")
    hosts = [HostWithoutWidget(), HostWithInvalidWidget()]

    class FakeHost:
        def __new__(cls, *_args, **_kwargs):
            _ = cls
            return hosts.pop(0)

    fake_overlay._qt_widget_is_valid = raise_invalid
    fake_overlay.ViewportOverlayHost = FakeHost
    monkeypatch.setitem(sys.modules, "actionrail.overlay", fake_overlay)

    runtime.show_spec(_empty_spec("missing"))
    runtime.show_spec(_empty_spec("invalid"))

    assert runtime.active_overlay_states() == (
        {
            "preset_id": "missing",
            "panel": "",
            "widget_visible": False,
            "widget_valid": False,
            "filter_target_count": 0,
            "predicate_timer_active": False,
        },
        {
            "preset_id": "invalid",
            "panel": "",
            "widget_visible": False,
            "widget_valid": False,
            "filter_target_count": 0,
            "predicate_timer_active": False,
        },
    )
