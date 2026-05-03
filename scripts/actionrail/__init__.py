"""Public entry points for the ActionRail Maya viewport overlay."""

from __future__ import annotations

from .authoring import (
    DraftRail,
    DraftSlot,
    build_draft_spec,
    load_user_preset,
    save_user_preset,
    spec_to_payload,
    user_preset_dir,
    user_preset_ids,
)
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
from .runtime import (
    hide_all,
    reload,
    run_action,
    run_slot,
    show_example,
    show_spec,
    update_slot_key_label,
)
from .spec import (
    RailLayout,
    StackItem,
    StackSpec,
    action_ids,
    builtin_preset_ids,
    load_builtin_preset,
    load_preset,
    parse_stack_spec,
)

__all__ = [
    "DiagnosticIssue",
    "DiagnosticReport",
    "DraftRail",
    "DraftSlot",
    "RailLayout",
    "StackItem",
    "StackSpec",
    "__version__",
    "about",
    "action_ids",
    "build_draft_spec",
    "builtin_preset_ids",
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
    "load_builtin_preset",
    "load_preset",
    "load_user_preset",
    "parse_stack_spec",
    "reload",
    "run_action",
    "run_diagnostics_from_maya",
    "run_slot",
    "safe_start",
    "save_user_preset",
    "show_example",
    "show_last_report",
    "show_spec",
    "spec_to_payload",
    "toggle_default",
    "update_slot_key_label",
    "uninstall_menu_toggle",
    "uninstall_shelf_toggle",
    "user_preset_dir",
    "user_preset_ids",
]

__version__ = "0.1.0"
