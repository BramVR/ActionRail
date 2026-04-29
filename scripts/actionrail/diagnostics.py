"""Safe-mode diagnostics for ActionRail presets and overlay startup."""

from __future__ import annotations

import ast
from collections.abc import Iterable
from dataclasses import dataclass, replace
from typing import Any, Literal

from .actions import ActionRegistry, create_default_registry
from .predicates import (
    PredicateContext,
    _command_exists,
    _dotted_name,
    _plugin_exists,
    evaluate_predicate,
)
from .spec import StackItem, StackSpec, builtin_preset_ids, load_builtin_preset

DiagnosticSeverity = Literal["info", "warning", "error"]


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
    exception_type: str = ""

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
            "exception_type": self.exception_type,
        }
        return {key: value for key, value in payload.items() if value}


@dataclass(frozen=True)
class DiagnosticReport:
    """Diagnostics plus safe-start runtime state."""

    issues: tuple[DiagnosticIssue, ...] = ()
    overlay_started: bool = False
    overlay_id: str = ""
    active_overlay_ids: tuple[str, ...] = ()

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
    ) -> DiagnosticReport:
        return replace(
            self,
            overlay_started=overlay_started,
            overlay_id=overlay_id,
            active_overlay_ids=active_overlay_ids,
        )


def collect_diagnostics(
    preset_ids: Iterable[str] | None = None,
    *,
    registry: ActionRegistry | None = None,
    cmds_module: Any | None = None,
) -> DiagnosticReport:
    """Collect diagnostics for bundled presets without showing an overlay."""

    resolved_cmds = _resolve_cmds_module(cmds_module)
    action_registry = registry or create_default_registry(resolved_cmds)
    issues: list[DiagnosticIssue] = []
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
            ).issues
        )
    return DiagnosticReport(tuple(issues), active_overlay_ids=_safe_active_overlay_ids())


def diagnose_spec(
    spec: StackSpec,
    *,
    registry: ActionRegistry | None = None,
    cmds_module: Any | None = None,
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

        issues.extend(
            _predicate_diagnostics(
                spec.id,
                item,
                registry=action_registry,
                cmds_module=resolved_cmds,
            )
        )
    return DiagnosticReport(tuple(issues), active_overlay_ids=_safe_active_overlay_ids())


def safe_start(
    preset_id: str = "transform_stack",
    *,
    panel: str | None = None,
    registry: ActionRegistry | None = None,
    cmds_module: Any | None = None,
) -> DiagnosticReport:
    """Validate a preset, start it if safe, and report recoverable failures."""

    report = collect_diagnostics(
        (preset_id,),
        registry=registry,
        cmds_module=cmds_module,
    )
    if report.has_errors:
        return report.with_runtime(
            overlay_started=False,
            active_overlay_ids=_safe_active_overlay_ids(),
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
        return report.with_issues((issue,)).with_runtime(
            overlay_started=False,
            active_overlay_ids=_safe_active_overlay_ids(),
        )

    return report.with_runtime(
        overlay_started=True,
        overlay_id=preset_id,
        active_overlay_ids=_safe_active_overlay_ids(),
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

        for kind, target in _availability_targets(predicate):
            if kind == "command" and not _command_exists(cmds_module, target):
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
            elif kind == "plugin" and not _plugin_exists(cmds_module, target):
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


def _availability_targets(predicate: str) -> tuple[tuple[str, str], ...]:
    try:
        parsed = ast.parse(predicate, mode="eval")
    except SyntaxError:
        return ()

    targets: list[tuple[str, str]] = []
    for node in ast.walk(parsed):
        if not isinstance(node, ast.Call) or len(node.args) != 1:
            continue
        try:
            name = _dotted_name(node.func)
        except ValueError:
            continue
        if name not in {"command.exists", "plugin.exists"}:
            continue

        arg = node.args[0]
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            targets.append(("command" if name == "command.exists" else "plugin", arg.value))
    return tuple(targets)


def _resolve_cmds_module(cmds_module: Any | None) -> Any | None:
    if cmds_module is not None:
        return cmds_module

    try:
        import maya.cmds as cmds  # type: ignore[import-not-found]
    except Exception:
        return None
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
