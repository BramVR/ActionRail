from __future__ import annotations

import sys
from types import ModuleType

import actionrail.runtime as runtime


def test_package_imports_without_maya_or_qt() -> None:
    import actionrail

    assert actionrail.__version__ == "0.1.0"
    assert callable(actionrail.about)
    assert callable(actionrail.show_example)
    assert callable(actionrail.hide_all)
    assert callable(actionrail.reload)
    assert callable(actionrail.collect_diagnostics)
    assert callable(actionrail.last_report)
    assert callable(actionrail.show_last_report)
    assert callable(actionrail.safe_start)
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
    monkeypatch.setattr(runtime, "_OVERLAYS", {})

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


def test_runtime_update_slot_key_label_ignores_missing_overlay(monkeypatch) -> None:
    monkeypatch.setattr(runtime, "_OVERLAYS", {})

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

    class RaisingHost:
        panel = "modelPanel5"
        widget = RaisingWidget()
        _filter_targets = None
        _predicate_refresh_timer = RaisingTimer()

    fake_overlay = ModuleType("actionrail.overlay")
    fake_overlay._qt_widget_is_valid = lambda widget: widget is not PassiveHost.widget
    monkeypatch.setitem(sys.modules, "actionrail.overlay", fake_overlay)
    monkeypatch.setattr(
        runtime,
        "_OVERLAYS",
        {"passive": PassiveHost(), "raising": RaisingHost()},
    )

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

    class HostWithInvalidWidget:
        panel = ""
        widget = object()
        _filter_targets = ()
        _predicate_refresh_timer = None

    def raise_invalid(widget) -> bool:
        raise RuntimeError("Qt wrapper deleted")

    fake_overlay = ModuleType("actionrail.overlay")
    fake_overlay._qt_widget_is_valid = raise_invalid
    monkeypatch.setitem(sys.modules, "actionrail.overlay", fake_overlay)
    monkeypatch.setattr(
        runtime,
        "_OVERLAYS",
        {"missing": HostWithoutWidget(), "invalid": HostWithInvalidWidget()},
    )

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
