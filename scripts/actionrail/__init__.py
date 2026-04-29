"""Public entry points for the ActionRail Maya viewport overlay."""

from __future__ import annotations

from .diagnostics import (
    DiagnosticIssue,
    DiagnosticReport,
    collect_diagnostics,
    diagnose_spec,
    safe_start,
)
from .maya_ui import (
    install_menu_toggle,
    install_shelf_toggle,
    toggle_default,
    uninstall_menu_toggle,
    uninstall_shelf_toggle,
)
from .runtime import hide_all, reload, run_action, run_slot, show_example, update_slot_key_label

__all__ = [
    "DiagnosticIssue",
    "DiagnosticReport",
    "__version__",
    "collect_diagnostics",
    "diagnose_spec",
    "hide_all",
    "install_menu_toggle",
    "install_shelf_toggle",
    "reload",
    "run_action",
    "run_slot",
    "safe_start",
    "show_example",
    "toggle_default",
    "update_slot_key_label",
    "uninstall_menu_toggle",
    "uninstall_shelf_toggle",
]

__version__ = "0.1.0"
