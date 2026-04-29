"""Maya-native UI entry points for ActionRail."""

from __future__ import annotations

from typing import Any, Literal

from . import runtime
from .spec import TRANSFORM_STACK_ID

MENU_NAME = "ActionRailMenu"
MENU_ITEM_NAME = "ActionRailToggleTransformStackMenuItem"
MENU_DIAGNOSTICS_ITEM_NAME = "ActionRailShowLastDiagnosticReportMenuItem"
SHELF_NAME = "ActionRail"
SHELF_BUTTON_NAME = "ActionRailToggleTransformStackShelfButton"

ToggleResult = Literal["shown", "hidden"]


def toggle_default(
    preset_id: str = TRANSFORM_STACK_ID,
    *,
    panel: str | None = None,
) -> ToggleResult:
    """Show the default preset when hidden, or hide it when visible."""

    if preset_id in runtime.active_overlay_ids():
        runtime.hide_example(preset_id)
        return "hidden"

    runtime.show_example(preset_id, panel=panel)
    return "shown"


def install_menu_toggle(
    *,
    parent: str = "MayaWindow",
    preset_id: str = TRANSFORM_STACK_ID,
    cmds_module: Any | None = None,
) -> str:
    """Install an idempotent Maya menu item that toggles the default rail."""

    cmds = _require_cmds(cmds_module)
    if not cmds.menu(MENU_NAME, exists=True):
        cmds.menu(MENU_NAME, label="ActionRail", parent=parent, tearOff=True)

    if cmds.menuItem(MENU_ITEM_NAME, exists=True):
        cmds.deleteUI(MENU_ITEM_NAME, menuItem=True)
    if cmds.menuItem(MENU_DIAGNOSTICS_ITEM_NAME, exists=True):
        cmds.deleteUI(MENU_DIAGNOSTICS_ITEM_NAME, menuItem=True)

    toggle_item = str(
        cmds.menuItem(
            MENU_ITEM_NAME,
            label=_toggle_label(preset_id),
            annotation="Show or hide the ActionRail viewport rail.",
            command=toggle_command(preset_id),
            parent=MENU_NAME,
            sourceType="python",
        )
    )
    cmds.menuItem(
        MENU_DIAGNOSTICS_ITEM_NAME,
        label="Show Last Diagnostic Report",
        annotation="Show the latest ActionRail diagnostic report.",
        command="import actionrail; actionrail.show_last_report()",
        parent=MENU_NAME,
        sourceType="python",
    )
    return toggle_item


def uninstall_menu_toggle(*, cmds_module: Any | None = None) -> None:
    """Remove the ActionRail menu toggle created by :func:`install_menu_toggle`."""

    cmds = _require_cmds(cmds_module)
    if cmds.menuItem(MENU_DIAGNOSTICS_ITEM_NAME, exists=True):
        cmds.deleteUI(MENU_DIAGNOSTICS_ITEM_NAME, menuItem=True)
    if cmds.menuItem(MENU_ITEM_NAME, exists=True):
        cmds.deleteUI(MENU_ITEM_NAME, menuItem=True)

    if cmds.menu(MENU_NAME, exists=True):
        try:
            remaining_items = cmds.menu(MENU_NAME, query=True, itemArray=True) or []
        except Exception:
            remaining_items = []
        if not remaining_items:
            cmds.deleteUI(MENU_NAME, menu=True)


def install_shelf_toggle(
    *,
    parent: str | None = None,
    preset_id: str = TRANSFORM_STACK_ID,
    cmds_module: Any | None = None,
    mel_module: Any | None = None,
) -> str:
    """Install an idempotent Maya shelf button that toggles the default rail."""

    cmds = _require_cmds(cmds_module)
    shelf_parent = parent or _default_shelf_parent(mel_module)
    if not cmds.shelfLayout(SHELF_NAME, exists=True):
        cmds.shelfLayout(SHELF_NAME, parent=shelf_parent)

    if cmds.shelfButton(SHELF_BUTTON_NAME, exists=True):
        cmds.deleteUI(SHELF_BUTTON_NAME, control=True)

    return str(
        cmds.shelfButton(
            SHELF_BUTTON_NAME,
            label="ActionRail",
            annotation="Show or hide the ActionRail viewport rail.",
            command=toggle_command(preset_id),
            parent=SHELF_NAME,
            sourceType="python",
            imageOverlayLabel="AR",
            width=34,
            height=34,
        )
    )


def uninstall_shelf_toggle(*, cmds_module: Any | None = None) -> None:
    """Remove the ActionRail shelf button created by :func:`install_shelf_toggle`."""

    cmds = _require_cmds(cmds_module)
    if cmds.shelfButton(SHELF_BUTTON_NAME, exists=True):
        cmds.deleteUI(SHELF_BUTTON_NAME, control=True)

    if cmds.shelfLayout(SHELF_NAME, exists=True):
        try:
            children = cmds.shelfLayout(SHELF_NAME, query=True, childArray=True) or []
        except Exception:
            children = []
        if not children:
            cmds.deleteUI(SHELF_NAME, layout=True)


def toggle_command(preset_id: str = TRANSFORM_STACK_ID) -> str:
    """Return the Python command string used by Maya menu and shelf entries."""

    if preset_id == TRANSFORM_STACK_ID:
        return "import actionrail; actionrail.toggle_default()"
    return f"import actionrail; actionrail.toggle_default({preset_id!r})"


def _toggle_label(preset_id: str) -> str:
    if preset_id == TRANSFORM_STACK_ID:
        return "Toggle Transform Stack"
    return f"Toggle {preset_id.replace('_', ' ').title()}"


def _default_shelf_parent(mel_module: Any | None = None) -> str:
    mel = mel_module
    if mel is None:
        try:
            import maya.mel as mel  # type: ignore[import-not-found,no-redef]
        except Exception as exc:  # pragma: no cover - exercised only inside Maya.
            msg = "ActionRail shelf install requires maya.mel inside Maya."
            raise RuntimeError(msg) from exc

    return str(mel.eval("$tmp = $gShelfTopLevel"))


def _require_cmds(cmds_module: Any | None = None) -> Any:
    if cmds_module is not None:
        return cmds_module

    try:
        import maya.cmds as cmds  # type: ignore[import-not-found]
    except Exception as exc:  # pragma: no cover - exercised only inside Maya.
        msg = "ActionRail Maya UI install requires maya.cmds inside Maya."
        raise RuntimeError(msg) from exc
    return cmds
