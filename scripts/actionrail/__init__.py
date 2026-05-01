"""Public entry points for the ActionRail Maya viewport overlay."""

from __future__ import annotations

from .diagnostics import (
    DiagnosticIssue,
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
from .maya_ui import (
    diagnose_icon_import_from_maya,
    install_menu_toggle,
    install_shelf_toggle,
    run_diagnostics_from_maya,
    toggle_default,
    uninstall_menu_toggle,
    uninstall_shelf_toggle,
)
from .project import about
from .runtime import hide_all, reload, run_action, run_slot, show_example, update_slot_key_label

__all__ = [
    "DiagnosticIssue",
    "DiagnosticReport",
    "__version__",
    "about",
    "clear_last_report",
    "collect_diagnostics",
    "diagnose_icon_import",
    "diagnose_icon_import_from_maya",
    "diagnose_spec",
    "format_report",
    "hide_all",
    "install_menu_toggle",
    "install_shelf_toggle",
    "last_report",
    "reload",
    "run_action",
    "run_diagnostics_from_maya",
    "run_slot",
    "safe_start",
    "show_example",
    "show_last_report",
    "toggle_default",
    "update_slot_key_label",
    "uninstall_menu_toggle",
    "uninstall_shelf_toggle",
]

__version__ = "0.1.0"
