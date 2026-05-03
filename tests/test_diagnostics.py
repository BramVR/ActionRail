from __future__ import annotations

import sys
import types

import pytest

import actionrail.diagnostics as diagnostics
from actionrail.actions import Action, ActionRegistry, create_default_registry
from actionrail.diagnostics import (
    DiagnosticIssue,
    DiagnosticOverlayState,
    DiagnosticReport,
    clear_last_report,
    collect_diagnostics,
    diagnose_icon_import,
    diagnose_spec,
    format_report,
    last_report,
    safe_start,
    show_last_report,
)
from actionrail.hotkeys import publish_action, publish_slot
from actionrail.spec import RailLayout, StackItem, StackSpec, builtin_preset_ids


class AvailabilityCmds:
    def commandInfo(self, command_name: str, *, exists: bool = False) -> bool:  # noqa: N802
        return command_name == "availableCommand" and exists

    def pluginInfo(self, plugin_name: str, *, query: bool = False, loaded: bool = False) -> bool:  # noqa: N802
        return plugin_name == "loadedPlugin" and query and loaded


class RuntimeCmds(AvailabilityCmds):
    def __init__(self) -> None:
        self.runtime_commands: dict[str, dict[str, object]] = {}
        self.name_commands: dict[str, dict[str, object]] = {}

    def runTimeCommand(self, name: str = "", **kwargs: object) -> object:  # noqa: N802
        if kwargs.get("userCommandArray"):
            return tuple(self.runtime_commands)
        if kwargs.get("exists"):
            return name in self.runtime_commands
        if kwargs.get("query") and kwargs.get("command"):
            return self.runtime_commands[name].get("command")
        if kwargs.get("delete"):
            self.runtime_commands.pop(name, None)
            return None
        payload = dict(kwargs)
        payload.pop("edit", None)
        self.runtime_commands[name] = payload
        return name

    def nameCommand(self, name: str, **kwargs: object) -> str:  # noqa: N802
        self.name_commands[name] = dict(kwargs)
        return name


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


def test_diagnose_spec_skips_availability_checks_without_cmds() -> None:
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
        ),
    )

    report = diagnose_spec(spec, registry=create_default_registry(AvailabilityCmds()))

    assert report.issues == ()


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


def test_diagnose_spec_accepts_manifest_icon() -> None:
    spec = StackSpec(
        id="with_icon",
        layout=RailLayout(anchor="viewport.left.center"),
        items=(
            StackItem(
                type="button",
                id="with_icon.move",
                label="M",
                action="maya.tool.move",
                icon="actionrail.move",
            ),
        ),
    )

    report = diagnose_spec(
        spec,
        registry=create_default_registry(AvailabilityCmds()),
        cmds_module=AvailabilityCmds(),
    )

    assert report.has_errors is False
    assert report.warnings == ()


def test_collect_diagnostics_reports_unknown_builtin_preset() -> None:
    report = collect_diagnostics(("missing_preset",), cmds_module=AvailabilityCmds())

    assert report.has_errors is True
    assert report.errors[0].code == "broken_preset"
    assert report.errors[0].preset_id == "missing_preset"
    assert last_report() == report


def test_last_report_can_be_cleared_and_formatted() -> None:
    clear_last_report()

    assert last_report() is None
    assert format_report() == "No ActionRail diagnostic report has been recorded."

    report = diagnose_spec(
        StackSpec(
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
        ),
        registry=create_default_registry(AvailabilityCmds()),
    )

    text = format_report()

    assert last_report() == report
    assert "Status: errors" in text
    assert "missing_action [broken_actions.missing]" in text


def test_diagnostic_report_dict_and_runtime_helpers() -> None:
    base = DiagnosticReport()
    issue = DiagnosticIssue("warning_code", "warning", "Warned.")
    state = DiagnosticOverlayState(
        preset_id="transform_stack",
        filter_target_count=2,
        predicate_timer_active=True,
    )

    report = base.with_issues((issue,)).with_runtime(
        overlay_started=True,
        overlay_id="transform_stack",
        active_overlay_ids=("transform_stack",),
        active_overlay_states=(state,),
    )

    assert report.warnings == (issue,)
    assert report.as_dict() == {
        "has_errors": False,
        "overlay_started": True,
        "overlay_id": "transform_stack",
        "active_overlay_ids": ("transform_stack",),
        "published_runtime_commands": (),
        "active_overlay_states": (state.as_dict(),),
        "issues": (issue.as_dict(),),
    }


def test_format_report_for_clean_report_lists_no_issues() -> None:
    text = format_report(DiagnosticReport())

    assert "Status: ok" in text
    assert "Issues: none" in text


def test_format_report_includes_overlay_id() -> None:
    text = format_report(DiagnosticReport(overlay_started=True, overlay_id="transform_stack"))

    assert "Overlay id: transform_stack" in text


def test_format_report_includes_structured_issue_details() -> None:
    report = DiagnosticReport(
        (
            DiagnosticIssue(
                code="invalid_icon_import_metadata",
                severity="error",
                message="Icon id must use letters, numbers, dots, underscores, or hyphens.",
                target="bad id",
                path="icons/custom/arrow.svg",
                field="icon_id",
                hint="Use a valid icon id.",
            ),
        )
    )

    text = format_report(report)

    assert "invalid_icon_import_metadata" in text
    assert "target: bad id" in text
    assert "path: icons/custom/arrow.svg" in text
    assert "field: icon_id" in text
    assert "hint: Use a valid icon id." in text


def test_collect_diagnostics_includes_published_runtime_commands() -> None:
    cmds = RuntimeCmds()
    publish_action("maya.tool.move", label="Move", cmds_module=cmds)

    report = collect_diagnostics(("transform_stack",), cmds_module=cmds)
    text = format_report(report)

    assert report.published_runtime_commands == ("ActionRail_action_maya_tool_move",)
    assert "Published runtime commands: ActionRail_action_maya_tool_move" in text


def test_collect_diagnostics_includes_active_overlay_support_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(diagnostics, "_safe_active_overlay_ids", lambda: ("transform_stack",))
    monkeypatch.setattr(
        diagnostics,
        "_safe_active_overlay_states",
        lambda: (
            DiagnosticOverlayState(
                preset_id="transform_stack",
                panel="modelPanel4",
                widget_visible=True,
                widget_valid=True,
                filter_target_count=2,
                predicate_timer_active=True,
            ),
        ),
    )

    report = collect_diagnostics(("transform_stack",), cmds_module=AvailabilityCmds())
    text = format_report(report)

    assert report.active_overlay_states[0].as_dict() == {
        "preset_id": "transform_stack",
        "panel": "modelPanel4",
        "widget_visible": True,
        "widget_valid": True,
        "filter_target_count": 2,
        "predicate_timer_active": True,
    }
    assert "Active overlay details:" in text
    assert (
        "- transform_stack: panel=modelPanel4, widget_visible=True, "
        "widget_valid=True, filter_targets=2, predicate_timer_active=True"
    ) in text


def test_diagnostic_overlay_state_as_dict_preserves_false_booleans() -> None:
    state = DiagnosticOverlayState(preset_id="transform_stack")

    assert state.as_dict() == {
        "preset_id": "transform_stack",
        "widget_visible": False,
        "widget_valid": False,
        "predicate_timer_active": False,
    }


def test_collect_diagnostics_reports_orphaned_runtime_commands() -> None:
    cmds = RuntimeCmds()
    stale_action = publish_action("maya.tool.removed", label="Removed", cmds_module=cmds)
    stale_slot = publish_slot(
        "transform_stack",
        "removed_slot",
        label="Removed",
        cmds_module=cmds,
    )

    report = collect_diagnostics(("transform_stack",), cmds_module=cmds)

    orphaned = [
        issue for issue in report.warnings if issue.code == "orphaned_runtime_command"
    ]
    assert [(issue.action_id, issue.slot_id, issue.target) for issue in orphaned] == [
        ("maya.tool.removed", "", stale_action.runtime_command),
        ("", "removed_slot", stale_slot.runtime_command),
    ]
    assert all(issue.hint for issue in orphaned)


def test_collect_diagnostics_reports_unknown_slot_runtime_commands() -> None:
    cmds = RuntimeCmds()
    unknown = publish_slot("unknown", "slot", label="Unknown", cmds_module=cmds)

    report = collect_diagnostics(("transform_stack",), cmds_module=cmds)

    orphaned = [
        issue for issue in report.warnings if issue.code == "orphaned_runtime_command"
    ]
    assert [(issue.preset_id, issue.slot_id, issue.target) for issue in orphaned] == [
        ("unknown", "slot", unknown.runtime_command),
    ]


def test_collect_diagnostics_hides_published_command_query_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(diagnostics, "_safe_published_commands", lambda _cmds: ())

    report = collect_diagnostics(("transform_stack",), cmds_module=object())

    assert report.published_runtime_commands == ()


def test_runtime_command_diagnostics_ignore_missing_cmds() -> None:
    registry = create_default_registry(AvailabilityCmds())

    assert diagnostics._runtime_command_diagnostics(registry, None) == ()


def test_runtime_command_diagnostics_reports_malformed_slot_target(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    command = types.SimpleNamespace(
        target_kind="slot",
        target_id="malformed",
        runtime_command="ActionRail_slot_malformed",
    )
    monkeypatch.setattr(diagnostics, "_safe_published_commands", lambda _cmds: (command,))
    registry = create_default_registry(AvailabilityCmds())

    issues = diagnostics._runtime_command_diagnostics(registry, object())

    assert [(issue.preset_id, issue.slot_id, issue.target) for issue in issues] == [
        ("", "", "ActionRail_slot_malformed")
    ]


def test_split_runtime_slot_target_handles_malformed_target() -> None:
    assert diagnostics._split_runtime_slot_target("malformed") == ("", "")


def test_diagnostic_issue_preserves_positional_exception_type_order() -> None:
    issue = DiagnosticIssue(
        "overlay_startup_failed",
        "error",
        "ActionRail overlay startup failed.",
        "transform_stack",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "RuntimeError",
    )

    assert issue.exception_type == "RuntimeError"
    assert issue.hint == ""
    assert issue.as_dict()["exception_type"] == "RuntimeError"
    assert "hint" not in issue.as_dict()


def test_show_last_report_opens_qt_window_with_formatted_report(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    shown: list[tuple[object, str]] = []
    collect_diagnostics(("missing_preset",), cmds_module=AvailabilityCmds())
    monkeypatch.setattr(
        diagnostics,
        "_show_report_window",
        lambda report, message: shown.append((report, message)),
    )

    text = show_last_report(cmds_module=object())

    assert "broken_preset [missing_preset]" in text
    assert shown == [(last_report(), text)]


def test_diagnose_icon_import_records_copyable_report(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    icon_dir = tmp_path / "icons"
    manifest_path = icon_dir / "manifest.json"
    source_path = tmp_path / "source.txt"
    icon_dir.mkdir()
    manifest_path.write_text('{"icons": []}\n', encoding="utf-8")
    source_path.write_text("not svg", encoding="utf-8")
    monkeypatch.setattr(diagnostics, "_safe_active_overlay_ids", lambda: ("existing",))

    import actionrail.icons as icons

    monkeypatch.setattr(icons, "_PACKAGE_ROOT", tmp_path)
    monkeypatch.setattr(icons, "_ICON_DIR", icon_dir)
    monkeypatch.setattr(icons, "_MANIFEST_PATH", manifest_path)

    report = diagnose_icon_import(
        str(source_path),
        "bad id",
        source="Local",
        license_name="Apache-2.0",
        url="local://source.txt",
    )

    assert report.has_errors is True
    assert report.active_overlay_ids == ("existing",)
    assert [issue.code for issue in report.errors] == [
        "invalid_icon_import_source",
        "invalid_icon_import_metadata",
    ]
    assert report.errors[1].field == "icon_id"
    assert report.errors[1].hint
    assert last_report() == report
    assert "invalid_icon_import_source" in format_report(report)
    assert "hint:" in format_report(report)


def test_diagnose_icon_import_reports_fallback_target_details(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    icon_dir = tmp_path / "icons"
    manifest_path = icon_dir / "manifest.json"
    source_path = tmp_path / "source.svg"
    fallback_path = icon_dir / "custom" / "arrow@3x.png"
    fallback_path.parent.mkdir(parents=True)
    fallback_path.write_bytes(b"\x89PNG\r\n\x1a\n")
    manifest_path.write_text('{"icons": []}\n', encoding="utf-8")
    source_path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        '<path d="M4 12h16"/></svg>',
        encoding="utf-8",
    )

    import actionrail.icons as icons

    monkeypatch.setattr(icons, "_PACKAGE_ROOT", tmp_path)
    monkeypatch.setattr(icons, "_ICON_DIR", icon_dir)
    monkeypatch.setattr(icons, "_MANIFEST_PATH", manifest_path)

    report = diagnose_icon_import(
        str(source_path),
        "custom.arrow",
        source="Local",
        license_name="Apache-2.0",
        url="local://source.svg",
        target_path="icons/custom/arrow.svg",
    )
    text = format_report(report)

    assert [issue.code for issue in report.errors] == ["icon_fallback_target_exists"]
    assert report.errors[0].path == "icons/custom/arrow@3x.png"
    assert report.errors[0].field == "fallbacks.3x"
    assert "path: icons/custom/arrow@3x.png" in text
    assert "field: fallbacks.3x" in text
    assert "hint:" in text


def test_diagnose_icon_import_honors_disabled_fallback_generation(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    icon_dir = tmp_path / "icons"
    manifest_path = icon_dir / "manifest.json"
    source_path = tmp_path / "source.svg"
    fallback_path = icon_dir / "custom" / "arrow@3x.png"
    fallback_path.parent.mkdir(parents=True)
    fallback_path.write_bytes(b"\x89PNG\r\n\x1a\n")
    manifest_path.write_text('{"icons": []}\n', encoding="utf-8")
    source_path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        '<path d="M4 12h16"/></svg>',
        encoding="utf-8",
    )

    import actionrail.icons as icons

    monkeypatch.setattr(icons, "_PACKAGE_ROOT", tmp_path)
    monkeypatch.setattr(icons, "_ICON_DIR", icon_dir)
    monkeypatch.setattr(icons, "_MANIFEST_PATH", manifest_path)

    report = diagnose_icon_import(
        str(source_path),
        "custom.arrow",
        source="Local",
        license_name="Apache-2.0",
        url="local://source.svg",
        target_path="icons/custom/arrow.svg",
        generate_fallbacks=False,
    )

    assert report.issues == ()


def test_icon_manifest_and_import_issue_fallback_fields() -> None:
    manifest_issue = diagnostics._icon_manifest_issue(object())
    import_issue = diagnostics._icon_import_issue(object())

    assert manifest_issue.code == "invalid_icon_manifest"
    assert manifest_issue.severity == "warning"
    assert import_issue.code == "invalid_icon_import"
    assert import_issue.severity == "error"


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
    assert last_report() == report


def test_safe_start_can_recover_to_fallback_preset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    started: list[str] = []
    monkeypatch.setattr(
        diagnostics,
        "_show_overlay",
        lambda preset_id, *, panel, registry: started.append(preset_id),
    )
    monkeypatch.setattr(diagnostics, "_safe_active_overlay_ids", lambda: ("transform_stack",))

    report = safe_start(
        "missing_preset",
        registry=create_default_registry(AvailabilityCmds()),
        cmds_module=AvailabilityCmds(),
        fallback_preset_id="transform_stack",
    )

    assert report.overlay_started is True
    assert report.overlay_id == "transform_stack"
    assert report.has_errors is True
    assert started == ["transform_stack"]
    assert [issue.code for issue in report.issues] == [
        "broken_preset",
        "preset_recovered",
    ]
    assert last_report() == report


def test_safe_start_reports_failed_recovery_when_fallback_has_errors() -> None:
    registry = ActionRegistry()
    registry.register(Action("only.custom.action", "Custom", lambda: None))

    report = safe_start(
        "missing_preset",
        registry=registry,
        cmds_module=AvailabilityCmds(),
        fallback_preset_id="transform_stack",
    )

    assert report.overlay_started is False
    assert [issue.code for issue in report.errors] == [
        "broken_preset",
        "missing_action",
        "missing_action",
        "missing_action",
        "missing_action",
        "preset_recovery_failed",
    ]


def test_safe_start_reports_failed_recovery_when_fallback_start_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    hidden: list[str] = []

    def fail_to_start(
        _preset_id: str,
        *,
        panel: str | None,
        registry: ActionRegistry | None,
    ) -> object:
        raise RuntimeError("fallback failed")

    monkeypatch.setattr(diagnostics, "_show_overlay", fail_to_start)
    monkeypatch.setattr(
        diagnostics,
        "_safe_hide_overlay",
        lambda preset_id: hidden.append(preset_id),
    )

    report = safe_start(
        "missing_preset",
        registry=create_default_registry(AvailabilityCmds()),
        cmds_module=AvailabilityCmds(),
        fallback_preset_id="transform_stack",
    )

    assert report.overlay_started is False
    assert report.errors[-1].code == "preset_recovery_failed"
    assert report.errors[-1].exception_type == "RuntimeError"
    assert hidden == ["transform_stack"]


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


def test_diagnostics_private_runtime_boundaries_are_defensive(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_maya = types.ModuleType("maya")
    fake_maya.__path__ = []
    fake_cmds = types.ModuleType("maya.cmds")
    fake_maya.cmds = fake_cmds
    monkeypatch.setitem(sys.modules, "maya", fake_maya)
    monkeypatch.setitem(sys.modules, "maya.cmds", fake_cmds)

    assert diagnostics._resolve_cmds_module(None) is fake_cmds
    assert diagnostics._require_cmds_module(fake_cmds) is fake_cmds

    monkeypatch.delitem(sys.modules, "maya.cmds")
    monkeypatch.delitem(sys.modules, "maya")
    with pytest.raises(RuntimeError, match="requires maya.cmds"):
        diagnostics._require_cmds_module(None)


def test_diagnostics_show_window_and_overlay_wrappers_import_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    diagnostics_ui_module = types.ModuleType("actionrail.diagnostics_ui")
    runtime_module = types.ModuleType("actionrail.runtime")
    calls: list[tuple[str, object]] = []

    def show_report_window(report, message, *, on_clear, on_hide_overlays):
        calls.append(("window", (report, message, on_clear, on_hide_overlays)))
        return "window"

    def show_example(preset_id, *, panel, registry):
        calls.append(("show", (preset_id, panel, registry)))
        return "host"

    def active_overlay_ids():
        return ("transform_stack",)

    def hide_example(preset_id):
        calls.append(("hide_example", preset_id))

    diagnostics_ui_module.show_report_window = show_report_window
    runtime_module.show_example = show_example
    runtime_module.active_overlay_ids = active_overlay_ids
    runtime_module.hide_example = hide_example
    monkeypatch.setitem(sys.modules, "actionrail.diagnostics_ui", diagnostics_ui_module)
    monkeypatch.setitem(sys.modules, "actionrail.runtime", runtime_module)

    report = DiagnosticReport()

    assert diagnostics._show_report_window(report, "message") == "window"
    assert calls[0][0] == "window"
    calls[0][1][3]()
    assert (
        diagnostics._show_overlay("transform_stack", panel="modelPanel4", registry=None)
        == "host"
    )
    assert calls[1] == ("hide_example", "transform_stack")
    assert calls[2] == ("show", ("transform_stack", "modelPanel4", None))


def test_diagnostics_hide_all_overlays_continues_after_close_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime_module = types.ModuleType("actionrail.runtime")
    hidden: list[str] = []

    def active_overlay_ids():
        return ("broken", "remaining")

    def hide_example(preset_id):
        hidden.append(preset_id)
        if preset_id == "broken":
            raise RuntimeError("deleted Qt host")

    runtime_module.active_overlay_ids = active_overlay_ids
    runtime_module.hide_example = hide_example
    monkeypatch.setitem(sys.modules, "actionrail.runtime", runtime_module)

    diagnostics._safe_hide_all_overlays()

    assert hidden == ["broken", "remaining"]


def test_diagnostics_safe_runtime_helpers_hide_exceptions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime_module = types.ModuleType("actionrail.runtime")

    def raise_error(*_args: object, **_kwargs: object) -> object:
        raise RuntimeError("runtime unavailable")

    runtime_module.hide_example = raise_error
    runtime_module.hide_all = raise_error
    runtime_module.active_overlay_ids = raise_error
    runtime_module.active_overlay_states = raise_error
    monkeypatch.setitem(sys.modules, "actionrail.runtime", runtime_module)

    diagnostics._safe_hide_overlay("transform_stack")
    diagnostics._safe_hide_all_overlays()

    assert diagnostics._safe_active_overlay_ids() == ()
    assert diagnostics._safe_active_overlay_states() == ()


def test_diagnostic_overlay_state_conversion_is_defensive() -> None:
    assert diagnostics._diagnostic_overlay_state(object()) == DiagnosticOverlayState(preset_id="")
    assert diagnostics._diagnostic_overlay_state(
        {
            "preset_id": "transform_stack",
            "panel": "modelPanel4",
            "widget_visible": 1,
            "widget_valid": 1,
            "filter_target_count": "bad",
            "predicate_timer_active": 1,
        }
    ) == DiagnosticOverlayState(
        preset_id="transform_stack",
        panel="modelPanel4",
        widget_visible=True,
        widget_valid=True,
        filter_target_count=0,
        predicate_timer_active=True,
    )
