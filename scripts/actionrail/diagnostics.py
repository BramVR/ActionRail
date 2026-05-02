"""Safe-mode diagnostics for ActionRail presets and overlay startup.

Purpose: validate presets and dependencies before showing user-facing UI.
Owns: report data classes, latest-report state, safe startup, report formatting.
Used by: public package helpers, Maya menu diagnostics, diagnostics Qt window.
Tests: `tests/test_diagnostics.py` and `actionrail_diagnostics_smoke.py`.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, replace
from typing import Any, Literal

from .actions import ActionRegistry, create_default_registry
from .icons import icon_status, validate_icon_manifest, validate_svg_icon_import
from .predicates import (
    PredicateContext,
    evaluate_predicate,
    missing_availability_targets,
)
from .spec import StackItem, StackSpec, builtin_preset_ids, load_builtin_preset

DiagnosticSeverity = Literal["info", "warning", "error"]

__all__ = [
    "DiagnosticIssue",
    "DiagnosticOverlayState",
    "DiagnosticReport",
    "DiagnosticSeverity",
    "clear_last_report",
    "collect_diagnostics",
    "diagnose_icon_import",
    "diagnose_spec",
    "format_report",
    "last_report",
    "safe_start",
    "show_last_report",
]


@dataclass(frozen=True)
class DiagnosticIssue:
    """One actionable diagnostic discovered before or during safe startup."""

    code: str
    severity: DiagnosticSeverity
    message: str
    preset_id: str = ""
    slot_id: str = ""
    action_id: str = ""
    predicate_field: str = ""
    predicate: str = ""
    target: str = ""
    path: str = ""
    field: str = ""
    exception_type: str = ""
    hint: str = ""

    def as_dict(self) -> dict[str, str]:
        """Return a compact serializable shape for scripts and future UI."""

        payload = {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "preset_id": self.preset_id,
            "slot_id": self.slot_id,
            "action_id": self.action_id,
            "predicate_field": self.predicate_field,
            "predicate": self.predicate,
            "target": self.target,
            "path": self.path,
            "field": self.field,
            "hint": self.hint,
            "exception_type": self.exception_type,
        }
        return {key: value for key, value in payload.items() if value}


@dataclass(frozen=True)
class DiagnosticOverlayState:
    """Support state for one active overlay host."""

    preset_id: str
    panel: str = ""
    widget_visible: bool = False
    widget_valid: bool = False
    filter_target_count: int = 0
    predicate_timer_active: bool = False

    def as_dict(self) -> dict[str, object]:
        """Return a compact serializable shape for diagnostics consumers."""

        payload: dict[str, object] = {
            "preset_id": self.preset_id,
            "panel": self.panel,
            "widget_visible": self.widget_visible,
            "widget_valid": self.widget_valid,
            "filter_target_count": self.filter_target_count,
            "predicate_timer_active": self.predicate_timer_active,
        }
        return {
            key: value
            for key, value in payload.items()
            if value != "" and not (type(value) is int and value == 0)
        }


@dataclass(frozen=True)
class DiagnosticReport:
    """Diagnostics plus safe-start runtime state."""

    issues: tuple[DiagnosticIssue, ...] = ()
    overlay_started: bool = False
    overlay_id: str = ""
    active_overlay_ids: tuple[str, ...] = ()
    published_runtime_commands: tuple[str, ...] = ()
    active_overlay_states: tuple[DiagnosticOverlayState, ...] = ()

    @property
    def has_errors(self) -> bool:
        return any(issue.severity == "error" for issue in self.issues)

    @property
    def errors(self) -> tuple[DiagnosticIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity == "error")

    @property
    def warnings(self) -> tuple[DiagnosticIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity == "warning")

    def as_dict(self) -> dict[str, object]:
        """Return a compact serializable shape for Maya scripts and tests."""

        return {
            "has_errors": self.has_errors,
            "overlay_started": self.overlay_started,
            "overlay_id": self.overlay_id,
            "active_overlay_ids": self.active_overlay_ids,
            "published_runtime_commands": self.published_runtime_commands,
            "active_overlay_states": tuple(
                state.as_dict() for state in self.active_overlay_states
            ),
            "issues": tuple(issue.as_dict() for issue in self.issues),
        }

    def with_issues(self, issues: Iterable[DiagnosticIssue]) -> DiagnosticReport:
        return replace(self, issues=(*self.issues, *tuple(issues)))

    def with_runtime(
        self,
        *,
        overlay_started: bool,
        overlay_id: str = "",
        active_overlay_ids: tuple[str, ...] = (),
        active_overlay_states: tuple[DiagnosticOverlayState, ...] = (),
    ) -> DiagnosticReport:
        return replace(
            self,
            overlay_started=overlay_started,
            overlay_id=overlay_id,
            active_overlay_ids=active_overlay_ids,
            active_overlay_states=active_overlay_states,
        )


_LAST_REPORT: DiagnosticReport | None = None


def last_report() -> DiagnosticReport | None:
    """Return the most recently recorded ActionRail diagnostic report."""

    return _LAST_REPORT


def clear_last_report() -> None:
    """Clear the most recently recorded diagnostic report."""

    global _LAST_REPORT
    _LAST_REPORT = None


def format_report(report: DiagnosticReport | None = None) -> str:
    """Return a compact plain-text report for Maya dialogs and logs."""

    diagnostic_report = report if report is not None else last_report()
    if diagnostic_report is None:
        return "No ActionRail diagnostic report has been recorded."

    status = "errors" if diagnostic_report.has_errors else "ok"
    lines = [
        f"Status: {status}",
        f"Overlay started: {diagnostic_report.overlay_started}",
    ]
    if diagnostic_report.overlay_id:
        lines.append(f"Overlay id: {diagnostic_report.overlay_id}")
    if diagnostic_report.active_overlay_ids:
        lines.append(
            "Active overlays: " + ", ".join(diagnostic_report.active_overlay_ids)
        )
    if diagnostic_report.published_runtime_commands:
        lines.append(
            "Published runtime commands: "
            + ", ".join(diagnostic_report.published_runtime_commands)
        )
    if diagnostic_report.active_overlay_states:
        lines.append("Active overlay details:")
        lines.extend(
            f"- {state.preset_id}: {_format_overlay_state(state)}"
            for state in diagnostic_report.active_overlay_states
        )

    if not diagnostic_report.issues:
        lines.append("Issues: none")
        return "\n".join(lines)

    lines.append("Issues:")
    for issue in diagnostic_report.issues:
        label = issue.code
        if issue.slot_id:
            label = f"{label} [{issue.slot_id}]"
        elif issue.preset_id:
            label = f"{label} [{issue.preset_id}]"
        lines.append(f"- {issue.severity}: {label}: {issue.message}")
        lines.extend(f"  {key}: {value}" for key, value in _issue_detail_fields(issue))
    return "\n".join(lines)


def show_last_report(*, cmds_module: Any | None = None) -> str:
    """Show the latest diagnostic report in the ActionRail Qt diagnostics window."""

    _ = cmds_module
    report = last_report()
    message = format_report()
    _show_report_window(report, message)
    return message


def collect_diagnostics(
    preset_ids: Iterable[str] | None = None,
    *,
    registry: ActionRegistry | None = None,
    cmds_module: Any | None = None,
) -> DiagnosticReport:
    """Collect diagnostics for bundled presets without showing an overlay."""

    resolved_cmds = _resolve_cmds_module(cmds_module)
    action_registry = registry or create_default_registry(resolved_cmds)
    issues: list[DiagnosticIssue] = [
        _icon_manifest_issue(issue) for issue in validate_icon_manifest()
    ]
    for preset_id in tuple(preset_ids) if preset_ids is not None else builtin_preset_ids():
        try:
            spec = load_builtin_preset(preset_id)
        except Exception as exc:
            issues.append(
                DiagnosticIssue(
                    code="broken_preset",
                    severity="error",
                    message=f"Unable to load ActionRail preset '{preset_id}': {exc}",
                    preset_id=preset_id,
                    exception_type=type(exc).__name__,
                )
            )
            continue

        issues.extend(
            diagnose_spec(
                spec,
                registry=action_registry,
                cmds_module=resolved_cmds,
                record=False,
            ).issues
        )
    issues.extend(_runtime_command_diagnostics(action_registry, resolved_cmds))
    return _record_report(
        DiagnosticReport(
            tuple(issues),
            active_overlay_ids=_safe_active_overlay_ids(),
            published_runtime_commands=_safe_published_runtime_commands(resolved_cmds),
            active_overlay_states=_safe_active_overlay_states(),
        )
    )


def diagnose_spec(
    spec: StackSpec,
    *,
    registry: ActionRegistry | None = None,
    cmds_module: Any | None = None,
    record: bool = True,
) -> DiagnosticReport:
    """Collect diagnostics for an already parsed preset spec."""

    resolved_cmds = _resolve_cmds_module(cmds_module)
    action_registry = registry or create_default_registry(resolved_cmds)
    issues: list[DiagnosticIssue] = []
    action_ids = set(action_registry.ids())
    for item in spec.items:
        if item.action and item.action not in action_ids:
            issues.append(
                DiagnosticIssue(
                    code="missing_action",
                    severity="error",
                    message=(
                        f"Preset '{spec.id}' slot '{item.id}' references unknown "
                        f"ActionRail action '{item.action}'."
                    ),
                    preset_id=spec.id,
                    slot_id=item.id,
                    action_id=item.action,
                )
            )
        if item.icon:
            icon_issue = _icon_issue(spec.id, item)
            if icon_issue is not None:
                issues.append(icon_issue)

        issues.extend(
            _predicate_diagnostics(
                spec.id,
                item,
                registry=action_registry,
                cmds_module=resolved_cmds,
            )
        )
    report = DiagnosticReport(
        tuple(issues),
        active_overlay_ids=_safe_active_overlay_ids(),
        published_runtime_commands=_safe_published_runtime_commands(resolved_cmds),
        active_overlay_states=_safe_active_overlay_states(),
    )
    if not record:
        return report
    return _record_report(report)


def diagnose_icon_import(
    source_path: str,
    icon_id: str,
    *,
    source: str,
    license_name: str,
    url: str,
    imported_at: str | None = None,
    target_path: str = "",
    overwrite: bool = False,
) -> DiagnosticReport:
    """Collect report-backed diagnostics for a local SVG icon import."""

    issues = tuple(
        _icon_import_issue(issue)
        for issue in validate_svg_icon_import(
            source_path,
            icon_id,
            source=source,
            license_name=license_name,
            url=url,
            imported_at=imported_at,
            target_path=target_path,
            overwrite=overwrite,
        )
    )
    return _record_report(
        DiagnosticReport(
            issues,
            active_overlay_ids=_safe_active_overlay_ids(),
            published_runtime_commands=_safe_published_runtime_commands(
                _resolve_cmds_module(None)
            ),
            active_overlay_states=_safe_active_overlay_states(),
        )
    )


def safe_start(
    preset_id: str = "transform_stack",
    *,
    panel: str | None = None,
    registry: ActionRegistry | None = None,
    cmds_module: Any | None = None,
    fallback_preset_id: str = "",
) -> DiagnosticReport:
    """Validate a preset, start it if safe, and report recoverable failures."""

    report = collect_diagnostics(
        (preset_id,),
        registry=registry,
        cmds_module=cmds_module,
    )
    if report.has_errors:
        if fallback_preset_id and fallback_preset_id != preset_id:
            return _recover_with_fallback_preset(
                report,
                preset_id,
                fallback_preset_id,
                panel=panel,
                registry=registry,
                cmds_module=cmds_module,
            )
        return _record_report(
            report.with_runtime(
                overlay_started=False,
                active_overlay_ids=_safe_active_overlay_ids(),
                active_overlay_states=_safe_active_overlay_states(),
            )
        )

    try:
        _show_overlay(preset_id, panel=panel, registry=registry)
    except Exception as exc:
        _safe_hide_overlay(preset_id)
        issue = DiagnosticIssue(
            code="overlay_startup_failed",
            severity="error",
            message=f"ActionRail overlay startup failed for preset '{preset_id}': {exc}",
            preset_id=preset_id,
            exception_type=type(exc).__name__,
        )
        return _record_report(
            report.with_issues((issue,)).with_runtime(
                overlay_started=False,
                active_overlay_ids=_safe_active_overlay_ids(),
                active_overlay_states=_safe_active_overlay_states(),
            )
        )

    return _record_report(
        report.with_runtime(
            overlay_started=True,
            overlay_id=preset_id,
            active_overlay_ids=_safe_active_overlay_ids(),
            active_overlay_states=_safe_active_overlay_states(),
        )
    )


def _predicate_diagnostics(
    preset_id: str,
    item: StackItem,
    *,
    registry: ActionRegistry,
    cmds_module: Any | None,
) -> tuple[DiagnosticIssue, ...]:
    issues: list[DiagnosticIssue] = []
    for field_name in ("visible_when", "enabled_when", "active_when"):
        predicate = getattr(item, field_name)
        if not predicate.strip():
            continue

        context = PredicateContext(registry=registry, item=item, cmds_module=cmds_module)
        try:
            evaluate_predicate(predicate, context)
        except Exception as exc:
            issues.append(
                DiagnosticIssue(
                    code="invalid_predicate",
                    severity="error",
                    message=(
                        f"Preset '{preset_id}' slot '{item.id}' has an invalid "
                        f"{field_name} predicate: {exc}"
                    ),
                    preset_id=preset_id,
                    slot_id=item.id,
                    predicate_field=field_name,
                    predicate=predicate,
                    exception_type=type(exc).__name__,
                )
            )
            continue

        if cmds_module is None:
            continue

        for kind, target in missing_availability_targets(predicate, cmds_module):
            if kind == "command":
                issues.append(
                    _availability_issue(
                        "missing_command",
                        f"Maya command '{target}' is unavailable.",
                        preset_id,
                        item,
                        field_name,
                        predicate,
                        target,
                    )
                )
            elif kind == "plugin":
                issues.append(
                    _availability_issue(
                        "missing_plugin",
                        f"Maya plugin '{target}' is not loaded.",
                        preset_id,
                        item,
                        field_name,
                        predicate,
                        target,
                    )
                )

    return tuple(issues)


def _availability_issue(
    code: str,
    message: str,
    preset_id: str,
    item: StackItem,
    predicate_field: str,
    predicate: str,
    target: str,
) -> DiagnosticIssue:
    return DiagnosticIssue(
        code=code,
        severity="warning",
        message=f"Preset '{preset_id}' slot '{item.id}': {message}",
        preset_id=preset_id,
        slot_id=item.id,
        predicate_field=predicate_field,
        predicate=predicate,
        target=target,
    )


def _icon_issue(preset_id: str, item: StackItem) -> DiagnosticIssue | None:
    status = icon_status(item.icon)
    if status.ok or status.issue is None:
        return None

    issue = status.issue
    return DiagnosticIssue(
        code=issue.code,
        severity="warning",
        message=f"Preset '{preset_id}' slot '{item.id}': {issue.message}",
        preset_id=preset_id,
        slot_id=item.id,
        target=issue.icon_id or item.icon,
        path=issue.path,
        field=issue.field,
        hint=issue.hint,
    )


def _icon_manifest_issue(issue: object) -> DiagnosticIssue:
    code = getattr(issue, "code", "invalid_icon_manifest")
    message = getattr(issue, "message", "ActionRail icon manifest is invalid.")
    icon_id = getattr(issue, "icon_id", "")
    return DiagnosticIssue(
        code=code,
        severity="warning",
        message=message,
        target=icon_id,
        path=getattr(issue, "path", ""),
        field=getattr(issue, "field", ""),
        hint=getattr(issue, "hint", ""),
    )


def _icon_import_issue(issue: object) -> DiagnosticIssue:
    code = getattr(issue, "code", "invalid_icon_import")
    message = getattr(issue, "message", "ActionRail icon import is invalid.")
    icon_id = getattr(issue, "icon_id", "")
    return DiagnosticIssue(
        code=code,
        severity="error",
        message=message,
        target=icon_id,
        path=getattr(issue, "path", ""),
        field=getattr(issue, "field", ""),
        hint=getattr(issue, "hint", ""),
    )


def _recover_with_fallback_preset(
    report: DiagnosticReport,
    preset_id: str,
    fallback_preset_id: str,
    *,
    panel: str | None,
    registry: ActionRegistry | None,
    cmds_module: Any | None,
) -> DiagnosticReport:
    fallback_report = collect_diagnostics(
        (fallback_preset_id,),
        registry=registry,
        cmds_module=cmds_module,
    )
    issues = list(report.issues)
    issues.extend(fallback_report.issues)
    if fallback_report.has_errors:
        issues.append(
            DiagnosticIssue(
                code="preset_recovery_failed",
                severity="error",
                message=(
                    f"Preset '{preset_id}' failed diagnostics and fallback preset "
                    f"'{fallback_preset_id}' is not safe to start."
                ),
                preset_id=preset_id,
                target=fallback_preset_id,
            )
        )
        return _record_report(
            DiagnosticReport(
                tuple(issues),
                overlay_started=False,
                active_overlay_ids=_safe_active_overlay_ids(),
                published_runtime_commands=report.published_runtime_commands,
                active_overlay_states=_safe_active_overlay_states(),
            )
        )

    try:
        _show_overlay(fallback_preset_id, panel=panel, registry=registry)
    except Exception as exc:
        _safe_hide_overlay(fallback_preset_id)
        issues.append(
            DiagnosticIssue(
                code="preset_recovery_failed",
                severity="error",
                message=(
                    f"Fallback preset '{fallback_preset_id}' failed to start "
                    f"after preset '{preset_id}' failed diagnostics: {exc}"
                ),
                preset_id=preset_id,
                target=fallback_preset_id,
                exception_type=type(exc).__name__,
            )
        )
        return _record_report(
            DiagnosticReport(
                tuple(issues),
                overlay_started=False,
                active_overlay_ids=_safe_active_overlay_ids(),
                published_runtime_commands=report.published_runtime_commands,
                active_overlay_states=_safe_active_overlay_states(),
            )
        )

    issues.append(
        DiagnosticIssue(
            code="preset_recovered",
            severity="warning",
            message=(
                f"Preset '{preset_id}' failed diagnostics; started fallback "
                f"preset '{fallback_preset_id}'."
            ),
            preset_id=preset_id,
            target=fallback_preset_id,
        )
    )
    return _record_report(
        DiagnosticReport(
            tuple(issues),
            overlay_started=True,
            overlay_id=fallback_preset_id,
            active_overlay_ids=_safe_active_overlay_ids(),
            published_runtime_commands=report.published_runtime_commands,
            active_overlay_states=_safe_active_overlay_states(),
        )
    )


def _record_report(report: DiagnosticReport) -> DiagnosticReport:
    global _LAST_REPORT
    _LAST_REPORT = report
    return report


def _issue_detail_fields(issue: DiagnosticIssue) -> tuple[tuple[str, str], ...]:
    """Return optional copyable issue fields in stable report order."""

    fields = (
        ("preset", issue.preset_id),
        ("slot", issue.slot_id),
        ("action", issue.action_id),
        ("predicate_field", issue.predicate_field),
        ("predicate", issue.predicate),
        ("target", issue.target),
        ("path", issue.path),
        ("field", issue.field),
        ("hint", issue.hint),
        ("exception", issue.exception_type),
    )
    return tuple((key, value) for key, value in fields if value)


def _format_overlay_state(state: DiagnosticOverlayState) -> str:
    details = [
        f"panel={state.panel or 'unknown'}",
        f"widget_visible={state.widget_visible}",
        f"widget_valid={state.widget_valid}",
        f"filter_targets={state.filter_target_count}",
        f"predicate_timer_active={state.predicate_timer_active}",
    ]
    return ", ".join(details)


def _runtime_command_diagnostics(
    registry: ActionRegistry,
    cmds_module: Any | None,
) -> tuple[DiagnosticIssue, ...]:
    if cmds_module is None:
        return ()

    issues: list[DiagnosticIssue] = []
    action_ids = set(registry.ids())
    for command in _safe_published_commands(cmds_module):
        if command.target_kind == "action":
            if command.target_id not in action_ids:
                issues.append(
                    DiagnosticIssue(
                        code="orphaned_runtime_command",
                        severity="warning",
                        message=(
                            f"Published ActionRail runtime command "
                            f"'{command.runtime_command}' targets missing action "
                            f"'{command.target_id}'."
                        ),
                        action_id=command.target_id,
                        target=command.runtime_command,
                        hint=(
                            "Run actionrail.hotkeys.sync_default_actions() to remove "
                            "stale generated action commands."
                        ),
                    )
                )
            continue

        preset_id, slot_id = _split_runtime_slot_target(command.target_id)
        if not preset_id or not slot_id:
            issues.append(_orphaned_slot_command_issue(command, "", ""))
            continue

        try:
            spec = load_builtin_preset(preset_id)
        except Exception:
            issues.append(_orphaned_slot_command_issue(command, preset_id, slot_id))
            continue

        if not any(item.id == command.target_id and item.action for item in spec.items):
            issues.append(_orphaned_slot_command_issue(command, preset_id, slot_id))

    return tuple(issues)


def _orphaned_slot_command_issue(
    command: Any,
    preset_id: str,
    slot_id: str,
) -> DiagnosticIssue:
    return DiagnosticIssue(
        code="orphaned_runtime_command",
        severity="warning",
        message=(
            f"Published ActionRail runtime command '{command.runtime_command}' "
            f"targets missing or unassigned slot '{command.target_id}'."
        ),
        preset_id=preset_id,
        slot_id=slot_id,
        target=command.runtime_command,
        hint=(
            "Run actionrail.hotkeys.sync_preset_slots() for the affected preset "
            "or unpublish the stale generated command."
        ),
    )


def _split_runtime_slot_target(target_id: str) -> tuple[str, str]:
    preset_id, separator, slot_id = target_id.partition(".")
    if not separator:
        return "", ""
    return preset_id, slot_id


def _safe_published_runtime_commands(cmds_module: Any | None) -> tuple[str, ...]:
    return tuple(command.runtime_command for command in _safe_published_commands(cmds_module))


def _safe_published_commands(cmds_module: Any | None) -> tuple[Any, ...]:
    if cmds_module is None:
        return ()
    try:
        from .hotkeys import list_published_commands

        return tuple(list_published_commands(cmds_module=cmds_module))
    except Exception:
        return ()


def _show_report_window(report: DiagnosticReport | None, message: str) -> Any:
    from .diagnostics_ui import show_report_window

    return show_report_window(report, message, on_clear=clear_last_report)


def _resolve_cmds_module(cmds_module: Any | None) -> Any | None:
    if cmds_module is not None:
        return cmds_module

    try:
        import maya.cmds as cmds  # type: ignore[import-not-found]
    except Exception:
        return None
    return cmds


def _require_cmds_module(cmds_module: Any | None) -> Any:
    cmds = _resolve_cmds_module(cmds_module)
    if cmds is None:
        msg = "ActionRail diagnostic UI requires maya.cmds inside Maya."
        raise RuntimeError(msg)
    return cmds


def _show_overlay(
    preset_id: str,
    *,
    panel: str | None,
    registry: ActionRegistry | None,
) -> Any:
    from .runtime import show_example

    return show_example(preset_id, panel=panel, registry=registry)


def _safe_hide_overlay(preset_id: str) -> None:
    try:
        from .runtime import hide_example

        hide_example(preset_id)
    except Exception:
        return


def _safe_active_overlay_ids() -> tuple[str, ...]:
    try:
        from .runtime import active_overlay_ids

        return active_overlay_ids()
    except Exception:
        return ()


def _safe_active_overlay_states() -> tuple[DiagnosticOverlayState, ...]:
    try:
        from .runtime import active_overlay_states

        return tuple(_diagnostic_overlay_state(state) for state in active_overlay_states())
    except Exception:
        return ()


def _diagnostic_overlay_state(state: object) -> DiagnosticOverlayState:
    if not isinstance(state, dict):
        return DiagnosticOverlayState(preset_id="")
    return DiagnosticOverlayState(
        preset_id=str(state.get("preset_id") or ""),
        panel=str(state.get("panel") or ""),
        widget_visible=bool(state.get("widget_visible")),
        widget_valid=bool(state.get("widget_valid")),
        filter_target_count=_safe_int(state.get("filter_target_count")),
        predicate_timer_active=bool(state.get("predicate_timer_active")),
    )


def _safe_int(value: object) -> int:
    try:
        return int(value)  # type: ignore[arg-type]
    except Exception:
        return 0
