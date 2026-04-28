"""Public entry points for the ActionRail Maya viewport overlay."""

from __future__ import annotations

from .runtime import hide_all, reload, run_action, run_slot, show_example, update_slot_key_label

__all__ = [
    "__version__",
    "hide_all",
    "reload",
    "run_action",
    "run_slot",
    "show_example",
    "update_slot_key_label",
]

__version__ = "0.1.0"
