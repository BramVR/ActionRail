from __future__ import annotations

from actionrail.diagnostics import DiagnosticIssue, DiagnosticOverlayState, DiagnosticReport
from actionrail.diagnostics_ui import _issue_detail, _issue_title, _summary_text


def test_issue_detail_includes_import_path_and_field() -> None:
    issue = DiagnosticIssue(
        code="invalid_icon_import_metadata",
        severity="error",
        message="Icon id must use letters, numbers, dots, underscores, or hyphens.",
        target="bad id",
        path="icons/custom/arrow.svg",
        field="icon_id",
        hint="Use a valid icon id.",
    )

    detail = _issue_detail(issue)

    assert "Target: bad id" in detail
    assert "Path: icons/custom/arrow.svg" in detail
    assert "Field: icon_id" in detail
    assert "Hint: Use a valid icon id." in detail


def test_issue_title_uses_path_when_no_stronger_target_exists() -> None:
    issue = DiagnosticIssue(
        code="missing_icon_fallback_file",
        severity="warning",
        message="Icon points to a missing PNG fallback.",
        path="icons/custom/arrow@3x.png",
    )

    assert (
        _issue_title(issue)
        == "WARNING missing_icon_fallback_file - icons/custom/arrow@3x.png"
    )


def test_summary_text_includes_overlay_support_counts() -> None:
    report = DiagnosticReport(
        active_overlay_ids=("transform_stack",),
        published_runtime_commands=("ActionRail_action_maya_tool_move",),
        active_overlay_states=(
            DiagnosticOverlayState(
                preset_id="transform_stack",
                filter_target_count=2,
                predicate_timer_active=True,
            ),
        ),
    )

    summary = _summary_text(report)

    assert "Published commands: 1." in summary
    assert "Event filters: 2." in summary
    assert "Refresh timers: 1." in summary
