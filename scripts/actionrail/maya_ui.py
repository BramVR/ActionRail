"""Maya-native UI entry points for ActionRail."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from . import diagnostics, runtime
from .spec import TRANSFORM_STACK_ID

MENU_NAME = "ActionRailMenu"
MENU_ITEM_NAME = "ActionRailToggleTransformStackMenuItem"
MENU_RUN_DIAGNOSTICS_ITEM_NAME = "ActionRailRunDiagnosticsMenuItem"
MENU_DIAGNOSTICS_ITEM_NAME = "ActionRailShowLastDiagnosticReportMenuItem"
MENU_ICON_IMPORT_DIAGNOSTICS_ITEM_NAME = "ActionRailDiagnoseIconImportMenuItem"
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
    if cmds.menuItem(MENU_RUN_DIAGNOSTICS_ITEM_NAME, exists=True):
        cmds.deleteUI(MENU_RUN_DIAGNOSTICS_ITEM_NAME, menuItem=True)
    if cmds.menuItem(MENU_DIAGNOSTICS_ITEM_NAME, exists=True):
        cmds.deleteUI(MENU_DIAGNOSTICS_ITEM_NAME, menuItem=True)
    if cmds.menuItem(MENU_ICON_IMPORT_DIAGNOSTICS_ITEM_NAME, exists=True):
        cmds.deleteUI(MENU_ICON_IMPORT_DIAGNOSTICS_ITEM_NAME, menuItem=True)

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
        MENU_RUN_DIAGNOSTICS_ITEM_NAME,
        label="Run Diagnostics",
        annotation="Collect current ActionRail diagnostics and show the report.",
        command=run_diagnostics_from_maya_command(),
        parent=MENU_NAME,
        sourceType="python",
    )
    cmds.menuItem(
        MENU_ICON_IMPORT_DIAGNOSTICS_ITEM_NAME,
        label="Diagnose SVG Icon Import...",
        annotation="Preflight a local SVG icon import and show the diagnostics report.",
        command=diagnose_icon_import_from_maya_command(),
        parent=MENU_NAME,
        sourceType="python",
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
    if cmds.menuItem(MENU_ICON_IMPORT_DIAGNOSTICS_ITEM_NAME, exists=True):
        cmds.deleteUI(MENU_ICON_IMPORT_DIAGNOSTICS_ITEM_NAME, menuItem=True)
    if cmds.menuItem(MENU_DIAGNOSTICS_ITEM_NAME, exists=True):
        cmds.deleteUI(MENU_DIAGNOSTICS_ITEM_NAME, menuItem=True)
    if cmds.menuItem(MENU_RUN_DIAGNOSTICS_ITEM_NAME, exists=True):
        cmds.deleteUI(MENU_RUN_DIAGNOSTICS_ITEM_NAME, menuItem=True)
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


def diagnose_icon_import_from_maya(
    *,
    source_path: str = "",
    icon_id: str = "",
    source: str = "",
    license_name: str = "Unknown",
    url: str = "",
    target_path: str = "",
    overwrite: bool = False,
    generate_fallbacks: bool = True,
    cmds_module: Any | None = None,
) -> diagnostics.DiagnosticReport | None:
    """Run icon import preflight from Maya dialogs and show the report window."""

    cmds = _require_cmds(cmds_module)
    resolved_source_path = source_path or _choose_svg_source_path(cmds)
    if not resolved_source_path:
        return None

    resolved_icon_id = icon_id
    if not resolved_icon_id:
        prompted_icon_id = _prompt_icon_id(
            cmds,
            _default_import_icon_id(resolved_source_path),
        )
        if prompted_icon_id is None:
            return None
        resolved_icon_id = prompted_icon_id

    source_file = Path(resolved_source_path)
    report = diagnostics.diagnose_icon_import(
        resolved_source_path,
        resolved_icon_id,
        source=source or source_file.stem or "Maya file dialog",
        license_name=license_name,
        url=url or resolved_source_path,
        target_path=target_path,
        overwrite=overwrite,
        generate_fallbacks=generate_fallbacks,
    )
    diagnostics.show_last_report()
    return report


def run_diagnostics_from_maya(
    *,
    cmds_module: Any | None = None,
) -> diagnostics.DiagnosticReport:
    """Collect current ActionRail diagnostics from Maya and show the report window."""

    cmds = _require_cmds(cmds_module)
    report = diagnostics.collect_diagnostics(cmds_module=cmds)
    diagnostics.show_last_report()
    return report


def run_diagnostics_from_maya_command() -> str:
    """Return the Python command string for the Maya diagnostics collection item."""

    return "import actionrail; actionrail.run_diagnostics_from_maya()"


def diagnose_icon_import_from_maya_command() -> str:
    """Return the Python command string for the Maya icon import diagnostics item."""

    return "import actionrail; actionrail.diagnose_icon_import_from_maya()"


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


def _choose_svg_source_path(cmds: Any) -> str:
    selection = cmds.fileDialog2(
        caption="Diagnose ActionRail SVG Icon Import",
        fileFilter="SVG Icons (*.svg);;All Files (*.*)",
        fileMode=1,
    )
    if not selection:
        return ""
    return str(selection[0])


def _prompt_icon_id(cmds: Any, default_icon_id: str) -> str | None:
    result = cmds.promptDialog(
        title="ActionRail Icon Import Diagnostics",
        message="Icon id",
        text=default_icon_id,
        button=("Diagnose", "Cancel"),
        defaultButton="Diagnose",
        cancelButton="Cancel",
        dismissString="Cancel",
    )
    if result != "Diagnose":
        return None
    return str(cmds.promptDialog(query=True, text=True)).strip()


def _default_import_icon_id(source_path: str) -> str:
    stem = Path(source_path).stem.lower()
    safe = "".join(char if char.isalnum() else "-" for char in stem).strip("-")
    return f"custom.{safe or 'icon'}"


def _require_cmds(cmds_module: Any | None = None) -> Any:
    if cmds_module is not None:
        return cmds_module

    try:
        import maya.cmds as cmds  # type: ignore[import-not-found]
    except Exception as exc:  # pragma: no cover - exercised only inside Maya.
        msg = "ActionRail Maya UI install requires maya.cmds inside Maya."
        raise RuntimeError(msg) from exc
    return cmds
