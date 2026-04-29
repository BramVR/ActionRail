from __future__ import annotations

import sys
import types

import pytest

import actionrail.diagnostics as diagnostics
from actionrail.actions import Action, ActionRegistry, create_default_registry
from actionrail.diagnostics import collect_diagnostics, diagnose_spec, safe_start
from actionrail.spec import RailLayout, StackItem, StackSpec, builtin_preset_ids


class AvailabilityCmds:
    def commandInfo(self, command_name: str, *, exists: bool = False) -> bool:  # noqa: N802
        return command_name == "availableCommand" and exists

    def pluginInfo(self, plugin_name: str, *, query: bool = False, loaded: bool = False) -> bool:  # noqa: N802
        return plugin_name == "loadedPlugin" and query and loaded


def test_builtin_preset_ids_are_discovered_from_presets_directory() -> None:
    assert builtin_preset_ids() == ("horizontal_tools", "transform_stack")


def test_diagnose_spec_reports_missing_action() -> None:
    spec = StackSpec(
        id="broken_actions",
        layout=RailLayout(anchor="viewport.left.center"),
        items=(
            StackItem(
                type="button",
                id="broken_actions.missing",
                label="X",
                action="maya.missing.action",
            ),
        ),
    )

    report = diagnose_spec(spec, registry=create_default_registry(AvailabilityCmds()))

    assert report.has_errors is True
    assert [issue.code for issue in report.errors] == ["missing_action"]
    assert report.errors[0].action_id == "maya.missing.action"


def test_diagnose_spec_reports_invalid_predicate() -> None:
    spec = StackSpec(
        id="broken_predicate",
        layout=RailLayout(anchor="viewport.left.center"),
        items=(
            StackItem(
                type="button",
                id="broken_predicate.slot",
                label="X",
                action="maya.anim.set_key",
                visible_when="__import__('os').system('echo nope')",
            ),
        ),
    )

    report = diagnose_spec(spec, registry=create_default_registry(AvailabilityCmds()))

    assert report.has_errors is True
    assert report.errors[0].code == "invalid_predicate"
    assert report.errors[0].predicate_field == "visible_when"


def test_diagnose_spec_reports_missing_command_and_plugin_predicates() -> None:
    spec = StackSpec(
        id="availability",
        layout=RailLayout(anchor="viewport.left.center"),
        items=(
            StackItem(
                type="button",
                id="availability.command",
                label="C",
                action="maya.anim.set_key",
                enabled_when="command.exists('missingCommand')",
            ),
            StackItem(
                type="button",
                id="availability.plugin",
                label="P",
                action="maya.anim.set_key",
                visible_when="plugin.exists('missingPlugin')",
            ),
            StackItem(
                type="button",
                id="availability.available",
                label="A",
                action="maya.anim.set_key",
                active_when=(
                    "command.exists('availableCommand') and plugin.exists('loadedPlugin')"
                ),
            ),
        ),
    )

    report = diagnose_spec(
        spec,
        registry=create_default_registry(AvailabilityCmds()),
        cmds_module=AvailabilityCmds(),
    )

    assert report.has_errors is False
    assert [(issue.code, issue.target) for issue in report.warnings] == [
        ("missing_command", "missingCommand"),
        ("missing_plugin", "missingPlugin"),
    ]


def test_diagnose_spec_reports_missing_icon_warning() -> None:
    spec = StackSpec(
        id="missing_icon",
        layout=RailLayout(anchor="viewport.left.center"),
        items=(
            StackItem(
                type="button",
                id="missing_icon.slot",
                label="I",
                action="maya.anim.set_key",
                icon="missing.icon",
            ),
        ),
    )

    report = diagnose_spec(
        spec,
        registry=create_default_registry(AvailabilityCmds()),
        cmds_module=AvailabilityCmds(),
    )

    assert report.has_errors is False
    assert [(issue.code, issue.target) for issue in report.warnings] == [
        ("missing_icon", "missing.icon")
    ]


def test_collect_diagnostics_reports_unknown_builtin_preset() -> None:
    report = collect_diagnostics(("missing_preset",), cmds_module=AvailabilityCmds())

    assert report.has_errors is True
    assert report.errors[0].code == "broken_preset"
    assert report.errors[0].preset_id == "missing_preset"


def test_safe_start_uses_importable_maya_cmds_for_availability_diagnostics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_maya = types.ModuleType("maya")
    fake_maya.__path__ = []
    fake_cmds = types.ModuleType("maya.cmds")
    fake_cmds.commandInfo = AvailabilityCmds().commandInfo
    fake_cmds.pluginInfo = AvailabilityCmds().pluginInfo
    fake_maya.cmds = fake_cmds
    monkeypatch.setitem(sys.modules, "maya", fake_maya)
    monkeypatch.setitem(sys.modules, "maya.cmds", fake_cmds)

    spec = StackSpec(
        id="availability",
        layout=RailLayout(anchor="viewport.left.center"),
        items=(
            StackItem(
                type="button",
                id="availability.command",
                label="C",
                action="maya.anim.set_key",
                enabled_when="command.exists('missingCommand')",
            ),
            StackItem(
                type="button",
                id="availability.plugin",
                label="P",
                action="maya.anim.set_key",
                visible_when="plugin.exists('missingPlugin')",
            ),
        ),
    )
    started: list[str] = []
    monkeypatch.setattr(diagnostics, "load_builtin_preset", lambda _preset_id: spec)
    monkeypatch.setattr(
        diagnostics,
        "_show_overlay",
        lambda preset_id, *, panel, registry: started.append(preset_id),
    )

    report = safe_start("availability")

    assert report.has_errors is False
    assert report.overlay_started is True
    assert started == ["availability"]
    assert [(issue.code, issue.target) for issue in report.warnings] == [
        ("missing_command", "missingCommand"),
        ("missing_plugin", "missingPlugin"),
    ]


def test_safe_start_skips_overlay_when_diagnostics_have_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry = ActionRegistry()
    registry.register(Action("only.custom.action", "Custom", lambda: None))
    started: list[str] = []
    monkeypatch.setattr(
        diagnostics,
        "_show_overlay",
        lambda preset_id, *, panel, registry: started.append(preset_id),
    )

    report = safe_start(
        "transform_stack",
        registry=registry,
        cmds_module=AvailabilityCmds(),
    )

    assert report.overlay_started is False
    assert report.has_errors is True
    assert started == []
    assert {issue.code for issue in report.errors} == {"missing_action"}


def test_safe_start_reports_recoverable_overlay_startup_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    hidden: list[str] = []

    def fail_to_start(
        _preset_id: str,
        *,
        panel: str | None,
        registry: ActionRegistry | None,
    ) -> object:
        raise RuntimeError("no model panel")

    monkeypatch.setattr(diagnostics, "_show_overlay", fail_to_start)
    monkeypatch.setattr(
        diagnostics,
        "_safe_hide_overlay",
        lambda preset_id: hidden.append(preset_id),
    )

    report = safe_start(
        "transform_stack",
        registry=create_default_registry(AvailabilityCmds()),
        cmds_module=AvailabilityCmds(),
    )

    assert report.overlay_started is False
    assert report.has_errors is True
    assert report.errors[0].code == "overlay_startup_failed"
    assert report.errors[0].exception_type == "RuntimeError"
    assert hidden == ["transform_stack"]


def test_safe_start_reports_started_overlay(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        diagnostics,
        "_show_overlay",
        lambda _preset_id, *, panel, registry: object(),
    )
    monkeypatch.setattr(diagnostics, "_safe_active_overlay_ids", lambda: ("transform_stack",))

    report = safe_start(
        "transform_stack",
        registry=create_default_registry(AvailabilityCmds()),
        cmds_module=AvailabilityCmds(),
    )

    assert report.has_errors is False
    assert report.overlay_started is True
    assert report.overlay_id == "transform_stack"
    assert report.active_overlay_ids == ("transform_stack",)
