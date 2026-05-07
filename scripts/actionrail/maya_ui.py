"""Maya-native UI entry points for ActionRail."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from . import action_book_ui, diagnostics, edit_mode, quick_create_ui, runtime
from .qt import load
from .spec import TRANSFORM_STACK_ID

MENU_NAME = "ActionRailMenu"
MENU_ITEM_NAME = "ActionRailToggleTransformStackMenuItem"
MENU_EDIT_MODE_ITEM_NAME = "ActionRailEditModeMenuItem"
MENU_QUICK_CREATE_ITEM_NAME = "ActionRailQuickCreateMenuItem"
MENU_ACTION_BOOK_ITEM_NAME = "ActionRailActionBookMenuItem"
MENU_RUN_DIAGNOSTICS_ITEM_NAME = "ActionRailRunDiagnosticsMenuItem"
MENU_DIAGNOSTICS_ITEM_NAME = "ActionRailShowLastDiagnosticReportMenuItem"
MENU_ICON_IMPORT_DIAGNOSTICS_ITEM_NAME = "ActionRailDiagnoseIconImportMenuItem"
SHELF_NAME = "ActionRail"
SHELF_BUTTON_NAME = "ActionRailToggleTransformStackShelfButton"
SHELF_BUTTON_PREFIX = "ActionRailTogglePresetShelfButton"
QUICK_CREATE_WORKSPACE_CONTROL = "ActionRailQuickCreateWorkspaceControl"
ACTION_BOOK_WORKSPACE_CONTROL = "ActionRailActionBookWorkspaceControl"
_QUICK_CREATE_USER_PRESET_DIR: str | Path | None = None

ToggleResult = Literal["shown", "hidden"]


def toggle_default(
    preset_id: str = TRANSFORM_STACK_ID,
    *,
    panel: str | None = None,
    user_preset_dir: str | Path | None = None,
    studio_preset_dir: str | Path | None = None,
) -> ToggleResult:
    """Show the default preset when hidden, or hide it when visible."""

    if preset_id in runtime.active_overlay_ids():
        runtime.hide_example(preset_id)
        return "hidden"

    kwargs: dict[str, Any] = {"panel": panel}
    if user_preset_dir is not None:
        kwargs["user_preset_dir"] = user_preset_dir
    if studio_preset_dir is not None:
        kwargs["studio_preset_dir"] = studio_preset_dir
    runtime.show_preset(preset_id, **kwargs)
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
    if cmds.menuItem(MENU_EDIT_MODE_ITEM_NAME, exists=True):
        cmds.deleteUI(MENU_EDIT_MODE_ITEM_NAME, menuItem=True)
    if cmds.menuItem(MENU_QUICK_CREATE_ITEM_NAME, exists=True):
        cmds.deleteUI(MENU_QUICK_CREATE_ITEM_NAME, menuItem=True)
    if cmds.menuItem(MENU_ACTION_BOOK_ITEM_NAME, exists=True):
        cmds.deleteUI(MENU_ACTION_BOOK_ITEM_NAME, menuItem=True)
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
        MENU_EDIT_MODE_ITEM_NAME,
        label="Toggle Edit Mode",
        annotation="Show or hide ActionRail Edit Mode layout-map controls.",
        command=toggle_edit_mode_command(),
        parent=MENU_NAME,
        sourceType="python",
    )
    cmds.menuItem(
        MENU_QUICK_CREATE_ITEM_NAME,
        label="Quick Create...",
        annotation="Open the dockable ActionRail Quick Create panel.",
        command=show_quick_create_panel_command(),
        parent=MENU_NAME,
        sourceType="python",
    )
    cmds.menuItem(
        MENU_ACTION_BOOK_ITEM_NAME,
        label="Action Book...",
        annotation="Open the searchable ActionRail Action Book.",
        command=show_action_book_panel_command(),
        parent=MENU_NAME,
        sourceType="python",
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
    if cmds.menuItem(MENU_ACTION_BOOK_ITEM_NAME, exists=True):
        cmds.deleteUI(MENU_ACTION_BOOK_ITEM_NAME, menuItem=True)
    if cmds.menuItem(MENU_QUICK_CREATE_ITEM_NAME, exists=True):
        cmds.deleteUI(MENU_QUICK_CREATE_ITEM_NAME, menuItem=True)
    if cmds.menuItem(MENU_EDIT_MODE_ITEM_NAME, exists=True):
        cmds.deleteUI(MENU_EDIT_MODE_ITEM_NAME, menuItem=True)
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


def install_preset_shelf_toggle(
    preset_id: str,
    *,
    parent: str | None = None,
    label: str = "",
    user_preset_dir: str | Path | None = None,
    studio_preset_dir: str | Path | None = None,
    cmds_module: Any | None = None,
    mel_module: Any | None = None,
) -> str:
    """Install an idempotent shelf button for a saved or bundled preset."""

    cmds = _require_cmds(cmds_module)
    shelf_parent = parent or _default_shelf_parent(mel_module)
    if not cmds.shelfLayout(SHELF_NAME, exists=True):
        cmds.shelfLayout(SHELF_NAME, parent=shelf_parent)

    button_name = _preset_shelf_button_name(preset_id)
    if cmds.shelfButton(button_name, exists=True):
        cmds.deleteUI(button_name, control=True)

    button_label = label or _preset_shelf_label(preset_id)
    return str(
        cmds.shelfButton(
            button_name,
            label=button_label,
            annotation=f"Show or hide ActionRail preset '{preset_id}'.",
            command=toggle_command(
                preset_id,
                user_preset_dir=user_preset_dir,
                studio_preset_dir=studio_preset_dir,
            ),
            parent=SHELF_NAME,
            sourceType="python",
            imageOverlayLabel=_shelf_overlay_label(button_label),
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


def toggle_command(
    preset_id: str = TRANSFORM_STACK_ID,
    *,
    user_preset_dir: str | Path | None = None,
    studio_preset_dir: str | Path | None = None,
) -> str:
    """Return the Python command string used by Maya menu and shelf entries."""

    kwargs = _toggle_command_kwargs(
        user_preset_dir=user_preset_dir,
        studio_preset_dir=studio_preset_dir,
    )
    if preset_id == TRANSFORM_STACK_ID and not kwargs:
        return "import actionrail; actionrail.toggle_default()"
    args = [] if preset_id == TRANSFORM_STACK_ID else [repr(preset_id)]
    args.extend(kwargs)
    return f"import actionrail; actionrail.toggle_default({', '.join(args)})"


def toggle_edit_mode_command() -> str:
    """Return the Python command string for the Maya Edit Mode toggle."""

    return "import actionrail; actionrail.toggle_edit_mode()"


def toggle_edit_mode(
    *,
    panel: str | None = None,
) -> edit_mode.EditModeState:
    """Toggle the edit-only layout-map overlay from Maya UI."""

    return edit_mode.toggle_edit_mode(panel=panel)


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


def show_quick_create_panel(
    *,
    cmds_module: Any | None = None,
    user_preset_dir: str | Path | None = None,
) -> Any:
    """Open the dockable Maya workspace-control Quick Create panel."""

    global _QUICK_CREATE_USER_PRESET_DIR
    _QUICK_CREATE_USER_PRESET_DIR = user_preset_dir

    cmds = _require_cmds(cmds_module)
    if not cmds.workspaceControl(QUICK_CREATE_WORKSPACE_CONTROL, exists=True):
        cmds.workspaceControl(
            QUICK_CREATE_WORKSPACE_CONTROL,
            label="ActionRail Quick Create",
            retain=False,
            floating=True,
            initialWidth=900,
            initialHeight=680,
            uiScript=restore_quick_create_panel_command(),
        )
    else:
        cmds.workspaceControl(QUICK_CREATE_WORKSPACE_CONTROL, edit=True, visible=True)
    return restore_quick_create_panel(user_preset_dir=user_preset_dir)


def show_action_book_panel(
    *,
    cmds_module: Any | None = None,
) -> Any:
    """Open the dockable Maya workspace-control Action Book panel."""

    cmds = _require_cmds(cmds_module)
    if not cmds.workspaceControl(ACTION_BOOK_WORKSPACE_CONTROL, exists=True):
        cmds.workspaceControl(
            ACTION_BOOK_WORKSPACE_CONTROL,
            label="ActionRail Action Book",
            retain=False,
            floating=True,
            initialWidth=720,
            initialHeight=680,
            uiScript=restore_action_book_panel_command(),
        )
    else:
        cmds.workspaceControl(ACTION_BOOK_WORKSPACE_CONTROL, edit=True, visible=True)
    return restore_action_book_panel()


def restore_quick_create_panel(
    *,
    user_preset_dir: str | Path | None = None,
) -> Any:
    """Restore the Quick Create Qt contents inside Maya's workspace control."""

    preset_dir = user_preset_dir
    if preset_dir is None:
        preset_dir = _QUICK_CREATE_USER_PRESET_DIR
    return quick_create_ui.show_quick_create_panel(
        parent=_workspace_control_parent(QUICK_CREATE_WORKSPACE_CONTROL),
        user_preset_dir=preset_dir,
    )


def restore_action_book_panel() -> Any:
    """Restore the Action Book Qt contents inside Maya's workspace control."""

    return action_book_ui.show_action_book_panel(
        parent=_workspace_control_parent(ACTION_BOOK_WORKSPACE_CONTROL),
    )


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


def show_quick_create_panel_command() -> str:
    """Return the Python command string for the Maya Quick Create menu item."""

    return "import actionrail; actionrail.show_quick_create_panel()"


def show_action_book_panel_command() -> str:
    """Return the Python command string for the Maya Action Book menu item."""

    return "import actionrail; actionrail.show_action_book_panel()"


def restore_quick_create_panel_command() -> str:
    """Return the Python command string used by Maya workspace-control restore."""

    return "import actionrail; actionrail.restore_quick_create_panel()"


def restore_action_book_panel_command() -> str:
    """Return the Python command string used by Maya workspace-control restore."""

    return "import actionrail; actionrail.restore_action_book_panel()"


def _toggle_label(preset_id: str) -> str:
    if preset_id == TRANSFORM_STACK_ID:
        return "Toggle Transform Stack"
    return f"Toggle {preset_id.replace('_', ' ').title()}"


def _toggle_command_kwargs(
    *,
    user_preset_dir: str | Path | None = None,
    studio_preset_dir: str | Path | None = None,
) -> list[str]:
    kwargs: list[str] = []
    if user_preset_dir is not None:
        kwargs.append(f"user_preset_dir={str(user_preset_dir)!r}")
    if studio_preset_dir is not None:
        kwargs.append(f"studio_preset_dir={str(studio_preset_dir)!r}")
    return kwargs


def _preset_shelf_button_name(preset_id: str) -> str:
    safe = "".join(char if char.isalnum() else "_" for char in preset_id).strip("_")
    return f"{SHELF_BUTTON_PREFIX}_{safe or 'preset'}"


def _preset_shelf_label(preset_id: str) -> str:
    return preset_id.replace("_", " ").replace("-", " ").title()


def _shelf_overlay_label(label: str) -> str:
    initials = "".join(word[0] for word in label.split() if word[:1].isalnum())
    return (initials or "AR")[:3].upper()


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


def _workspace_control_parent(control_name: str) -> Any | None:
    qt = load()
    try:
        from maya import OpenMayaUI as omui  # type: ignore[import-not-found]
    except Exception:
        return None

    try:
        pointer = omui.MQtUtil.findControl(control_name)
    except Exception:
        pointer = None
    if not pointer:
        return None
    return qt.wrap_instance(int(pointer), qt.QtWidgets.QWidget)


def _require_cmds(cmds_module: Any | None = None) -> Any:
    if cmds_module is not None:
        return cmds_module

    try:
        import maya.cmds as cmds  # type: ignore[import-not-found]
    except Exception as exc:  # pragma: no cover - exercised only inside Maya.
        msg = "ActionRail Maya UI install requires maya.cmds inside Maya."
        raise RuntimeError(msg) from exc
    return cmds
