from __future__ import annotations

import sys
from types import ModuleType

from actionrail import maya_ui


class FakeCmds:
    def __init__(self) -> None:
        self.menus: dict[str, dict[str, object]] = {}
        self.menu_items: dict[str, dict[str, object]] = {}
        self.shelves: dict[str, dict[str, object]] = {}
        self.shelf_buttons: dict[str, dict[str, object]] = {}
        self.workspace_controls: dict[str, dict[str, object]] = {}
        self.deleted: list[tuple[str, dict[str, object]]] = []
        self.file_dialog_selection: list[str] = []
        self.prompt_result = "Diagnose"
        self.prompt_default_text = ""
        self.prompt_text = ""

    def menu(self, name: str, **kwargs: object) -> object:
        if kwargs.get("exists"):
            return name in self.menus
        if kwargs.get("query") and kwargs.get("itemArray"):
            return [
                item_name
                for item_name, item in self.menu_items.items()
                if item.get("parent") == name
            ]
        self.menus[name] = dict(kwargs)
        return name

    def menuItem(self, name: str, **kwargs: object) -> object:  # noqa: N802
        if kwargs.get("exists"):
            return name in self.menu_items
        self.menu_items[name] = dict(kwargs)
        return name

    def shelfLayout(self, name: str, **kwargs: object) -> object:  # noqa: N802
        if kwargs.get("exists"):
            return name in self.shelves
        if kwargs.get("query") and kwargs.get("childArray"):
            return [
                button_name
                for button_name, button in self.shelf_buttons.items()
                if button.get("parent") == name
            ]
        self.shelves[name] = dict(kwargs)
        return name

    def shelfButton(self, name: str, **kwargs: object) -> object:  # noqa: N802
        if kwargs.get("exists"):
            return name in self.shelf_buttons
        self.shelf_buttons[name] = dict(kwargs)
        return name

    def workspaceControl(self, name: str, **kwargs: object) -> object:  # noqa: N802
        if kwargs.get("exists"):
            return name in self.workspace_controls
        if kwargs.get("edit"):
            self.workspace_controls.setdefault(name, {}).update(kwargs)
            return name
        self.workspace_controls[name] = dict(kwargs)
        return name

    def deleteUI(self, name: str, **kwargs: object) -> None:  # noqa: N802
        self.deleted.append((name, dict(kwargs)))
        if kwargs.get("menuItem"):
            self.menu_items.pop(name, None)
        elif kwargs.get("menu"):
            self.menus.pop(name, None)
        elif kwargs.get("control"):
            self.shelf_buttons.pop(name, None)
            self.workspace_controls.pop(name, None)
        elif kwargs.get("layout"):
            self.shelves.pop(name, None)

    def fileDialog2(self, **kwargs: object) -> list[str]:  # noqa: N802
        return self.file_dialog_selection

    def promptDialog(self, **kwargs: object) -> str:  # noqa: N802
        if kwargs.get("query") and kwargs.get("text"):
            return self.prompt_text
        self.prompt_default_text = str(kwargs.get("text", ""))
        return self.prompt_result


class FakeMel:
    def eval(self, expression: str) -> str:
        assert "$gShelfTopLevel" in expression
        return "ShelfLayout"


def test_toggle_command_uses_public_actionrail_api() -> None:
    assert maya_ui.toggle_command() == "import actionrail; actionrail.toggle_default()"
    assert maya_ui.toggle_command("horizontal_tools") == (
        "import actionrail; actionrail.toggle_default('horizontal_tools')"
    )
    assert maya_ui.toggle_command("artist_tools", user_preset_dir="C:/custom/presets") == (
        "import actionrail; actionrail.toggle_default('artist_tools', "
        "user_preset_dir='C:/custom/presets')"
    )
    assert maya_ui.diagnose_icon_import_from_maya_command() == (
        "import actionrail; actionrail.diagnose_icon_import_from_maya()"
    )
    assert maya_ui.toggle_edit_mode_command() == (
        "import actionrail; actionrail.toggle_edit_mode()"
    )
    assert maya_ui.toggle_bind_mode_command() == (
        "import actionrail; actionrail.toggle_bind_mode()"
    )
    assert maya_ui.save_bind_mode_command() == (
        "import actionrail; actionrail.exit_bind_mode(save=True)"
    )
    assert maya_ui.discard_bind_mode_command() == (
        "import actionrail; actionrail.exit_bind_mode(save=False)"
    )
    assert maya_ui.clear_bind_mode_hovered_command() == (
        "import actionrail; actionrail.clear_hovered_hotkey()"
    )
    assert maya_ui.run_diagnostics_from_maya_command() == (
        "import actionrail; actionrail.run_diagnostics_from_maya()"
    )
    assert maya_ui.show_quick_create_panel_command() == (
        "import actionrail; actionrail.show_quick_create_panel()"
    )
    assert maya_ui.show_action_book_panel_command() == (
        "import actionrail; actionrail.show_action_book_panel()"
    )
    assert maya_ui.restore_quick_create_panel_command() == (
        "import actionrail; actionrail.restore_quick_create_panel()"
    )
    assert maya_ui.restore_action_book_panel_command() == (
        "import actionrail; actionrail.restore_action_book_panel()"
    )
    assert maya_ui._toggle_label("horizontal_tools") == "Toggle Horizontal Tools"


def test_toggle_default_shows_when_hidden_and_hides_when_visible(
    monkeypatch,
) -> None:
    active_ids: set[str] = set()
    calls: list[tuple[str, str]] = []

    def active_overlay_ids() -> tuple[str, ...]:
        return tuple(active_ids)

    def show_preset(preset_id: str, *, panel: str | None = None) -> None:
        calls.append(("show", f"{preset_id}:{panel}"))
        active_ids.add(preset_id)

    def hide_example(preset_id: str) -> None:
        calls.append(("hide", preset_id))
        active_ids.discard(preset_id)

    monkeypatch.setattr(maya_ui.runtime, "active_overlay_ids", active_overlay_ids)
    monkeypatch.setattr(maya_ui.runtime, "show_preset", show_preset)
    monkeypatch.setattr(maya_ui.runtime, "hide_example", hide_example)

    assert maya_ui.toggle_default(panel="modelPanel4") == "shown"
    assert maya_ui.toggle_default() == "hidden"
    assert calls == [
        ("show", "transform_stack:modelPanel4"),
        ("hide", "transform_stack"),
    ]


def test_toggle_default_forwards_custom_preset_dirs(monkeypatch, tmp_path) -> None:
    calls: list[dict[str, object]] = []

    monkeypatch.setattr(maya_ui.runtime, "active_overlay_ids", lambda: ())
    monkeypatch.setattr(
        maya_ui.runtime,
        "show_preset",
        lambda preset_id, **kwargs: calls.append({"preset_id": preset_id, **kwargs}),
    )

    assert (
        maya_ui.toggle_default(
            "artist_tools",
            user_preset_dir=tmp_path / "user",
            studio_preset_dir=tmp_path / "studio",
        )
        == "shown"
    )
    assert calls == [
        {
            "preset_id": "artist_tools",
            "panel": None,
            "user_preset_dir": tmp_path / "user",
            "studio_preset_dir": tmp_path / "studio",
        }
    ]


def test_install_menu_toggle_is_idempotent() -> None:
    cmds = FakeCmds()

    first = maya_ui.install_menu_toggle(cmds_module=cmds)
    second = maya_ui.install_menu_toggle(cmds_module=cmds)

    assert first == second == maya_ui.MENU_ITEM_NAME
    assert tuple(cmds.menus) == (maya_ui.MENU_NAME,)
    assert tuple(cmds.menu_items) == (
        maya_ui.MENU_ITEM_NAME,
        maya_ui.MENU_EDIT_MODE_ITEM_NAME,
        maya_ui.MENU_BIND_MODE_ITEM_NAME,
        maya_ui.MENU_BIND_MODE_SAVE_ITEM_NAME,
        maya_ui.MENU_BIND_MODE_DISCARD_ITEM_NAME,
        maya_ui.MENU_BIND_MODE_CLEAR_ITEM_NAME,
        maya_ui.MENU_QUICK_CREATE_ITEM_NAME,
        maya_ui.MENU_ACTION_BOOK_ITEM_NAME,
        maya_ui.MENU_RUN_DIAGNOSTICS_ITEM_NAME,
        maya_ui.MENU_ICON_IMPORT_DIAGNOSTICS_ITEM_NAME,
        maya_ui.MENU_DIAGNOSTICS_ITEM_NAME,
    )
    assert cmds.menu_items[maya_ui.MENU_ITEM_NAME]["command"] == maya_ui.toggle_command()
    assert cmds.menu_items[maya_ui.MENU_EDIT_MODE_ITEM_NAME][
        "command"
    ] == maya_ui.toggle_edit_mode_command()
    assert cmds.menu_items[maya_ui.MENU_BIND_MODE_ITEM_NAME][
        "command"
    ] == maya_ui.toggle_bind_mode_command()
    assert cmds.menu_items[maya_ui.MENU_BIND_MODE_SAVE_ITEM_NAME][
        "command"
    ] == maya_ui.save_bind_mode_command()
    assert cmds.menu_items[maya_ui.MENU_BIND_MODE_DISCARD_ITEM_NAME][
        "command"
    ] == maya_ui.discard_bind_mode_command()
    assert cmds.menu_items[maya_ui.MENU_BIND_MODE_CLEAR_ITEM_NAME][
        "command"
    ] == maya_ui.clear_bind_mode_hovered_command()
    assert cmds.menu_items[maya_ui.MENU_QUICK_CREATE_ITEM_NAME][
        "command"
    ] == maya_ui.show_quick_create_panel_command()
    assert cmds.menu_items[maya_ui.MENU_ACTION_BOOK_ITEM_NAME][
        "command"
    ] == maya_ui.show_action_book_panel_command()
    assert cmds.menu_items[maya_ui.MENU_RUN_DIAGNOSTICS_ITEM_NAME][
        "command"
    ] == maya_ui.run_diagnostics_from_maya_command()
    assert cmds.menu_items[maya_ui.MENU_ICON_IMPORT_DIAGNOSTICS_ITEM_NAME][
        "command"
    ] == maya_ui.diagnose_icon_import_from_maya_command()
    assert cmds.menu_items[maya_ui.MENU_DIAGNOSTICS_ITEM_NAME]["command"] == (
        "import actionrail; actionrail.show_last_report()"
    )
    assert cmds.deleted == [
        (maya_ui.MENU_ITEM_NAME, {"menuItem": True}),
        (maya_ui.MENU_EDIT_MODE_ITEM_NAME, {"menuItem": True}),
        (maya_ui.MENU_BIND_MODE_ITEM_NAME, {"menuItem": True}),
        (maya_ui.MENU_BIND_MODE_SAVE_ITEM_NAME, {"menuItem": True}),
        (maya_ui.MENU_BIND_MODE_DISCARD_ITEM_NAME, {"menuItem": True}),
        (maya_ui.MENU_BIND_MODE_CLEAR_ITEM_NAME, {"menuItem": True}),
        (maya_ui.MENU_QUICK_CREATE_ITEM_NAME, {"menuItem": True}),
        (maya_ui.MENU_ACTION_BOOK_ITEM_NAME, {"menuItem": True}),
        (maya_ui.MENU_RUN_DIAGNOSTICS_ITEM_NAME, {"menuItem": True}),
        (maya_ui.MENU_DIAGNOSTICS_ITEM_NAME, {"menuItem": True}),
        (maya_ui.MENU_ICON_IMPORT_DIAGNOSTICS_ITEM_NAME, {"menuItem": True}),
    ]


def test_uninstall_menu_toggle_removes_empty_actionrail_menu_only() -> None:
    cmds = FakeCmds()
    maya_ui.install_menu_toggle(cmds_module=cmds)

    maya_ui.uninstall_menu_toggle(cmds_module=cmds)

    assert cmds.menu_items == {}
    assert cmds.menus == {}
    assert (maya_ui.MENU_ITEM_NAME, {"menuItem": True}) in cmds.deleted
    assert (maya_ui.MENU_EDIT_MODE_ITEM_NAME, {"menuItem": True}) in cmds.deleted
    assert (maya_ui.MENU_BIND_MODE_ITEM_NAME, {"menuItem": True}) in cmds.deleted
    assert (maya_ui.MENU_BIND_MODE_SAVE_ITEM_NAME, {"menuItem": True}) in cmds.deleted
    assert (maya_ui.MENU_BIND_MODE_DISCARD_ITEM_NAME, {"menuItem": True}) in cmds.deleted
    assert (maya_ui.MENU_BIND_MODE_CLEAR_ITEM_NAME, {"menuItem": True}) in cmds.deleted
    assert (maya_ui.MENU_QUICK_CREATE_ITEM_NAME, {"menuItem": True}) in cmds.deleted
    assert (maya_ui.MENU_ACTION_BOOK_ITEM_NAME, {"menuItem": True}) in cmds.deleted
    assert (maya_ui.MENU_DIAGNOSTICS_ITEM_NAME, {"menuItem": True}) in cmds.deleted
    assert (maya_ui.MENU_RUN_DIAGNOSTICS_ITEM_NAME, {"menuItem": True}) in cmds.deleted
    assert (
        maya_ui.MENU_ICON_IMPORT_DIAGNOSTICS_ITEM_NAME,
        {"menuItem": True},
    ) in cmds.deleted
    assert (maya_ui.MENU_NAME, {"menu": True}) in cmds.deleted


def test_uninstall_menu_toggle_leaves_nonempty_menu() -> None:
    cmds = FakeCmds()
    maya_ui.install_menu_toggle(cmds_module=cmds)
    cmds.menuItem("OtherItem", parent=maya_ui.MENU_NAME)

    maya_ui.uninstall_menu_toggle(cmds_module=cmds)

    assert maya_ui.MENU_NAME in cmds.menus
    assert "OtherItem" in cmds.menu_items


def test_uninstall_menu_toggle_handles_menu_query_failure() -> None:
    class BrokenMenuCmds(FakeCmds):
        def menu(self, name: str, **kwargs: object) -> object:
            if kwargs.get("query") and kwargs.get("itemArray"):
                raise RuntimeError("menu deleted")
            return super().menu(name, **kwargs)

    cmds = BrokenMenuCmds()
    maya_ui.install_menu_toggle(cmds_module=cmds)

    maya_ui.uninstall_menu_toggle(cmds_module=cmds)

    assert cmds.menus == {}


def test_diagnose_icon_import_from_maya_uses_dialog_values(monkeypatch) -> None:
    cmds = FakeCmds()
    cmds.file_dialog_selection = ["C:/icons/Example Icon.svg"]
    cmds.prompt_text = "custom.example-icon"
    calls: dict[str, object] = {}

    def diagnose_icon_import(
        source_path: str,
        icon_id: str,
        **kwargs: object,
    ) -> object:
        calls["diagnose"] = (source_path, icon_id, kwargs)
        return "report"

    def show_last_report() -> str:
        calls["shown"] = True
        return "formatted"

    monkeypatch.setattr(
        maya_ui.diagnostics,
        "diagnose_icon_import",
        diagnose_icon_import,
    )
    monkeypatch.setattr(maya_ui.diagnostics, "show_last_report", show_last_report)

    result = maya_ui.diagnose_icon_import_from_maya(cmds_module=cmds)

    assert result == "report"
    assert calls["shown"] is True
    assert calls["diagnose"] == (
        "C:/icons/Example Icon.svg",
        "custom.example-icon",
        {
            "source": "Example Icon",
            "license_name": "Unknown",
            "url": "C:/icons/Example Icon.svg",
            "target_path": "",
            "overwrite": False,
            "generate_fallbacks": True,
        },
    )


def test_diagnose_icon_import_from_maya_reports_empty_prompt_text(monkeypatch) -> None:
    cmds = FakeCmds()
    cmds.file_dialog_selection = ["C:/icons/Empty Id.svg"]
    cmds.prompt_text = ""
    calls: dict[str, object] = {}

    def diagnose_icon_import(
        source_path: str,
        icon_id: str,
        **kwargs: object,
    ) -> object:
        calls["diagnose"] = (source_path, icon_id, kwargs)
        return "report"

    def show_last_report() -> str:
        calls["shown"] = True
        return "formatted"

    monkeypatch.setattr(
        maya_ui.diagnostics,
        "diagnose_icon_import",
        diagnose_icon_import,
    )
    monkeypatch.setattr(maya_ui.diagnostics, "show_last_report", show_last_report)

    result = maya_ui.diagnose_icon_import_from_maya(cmds_module=cmds)

    assert result == "report"
    assert calls["shown"] is True
    assert calls["diagnose"] == (
        "C:/icons/Empty Id.svg",
        "",
        {
            "source": "Empty Id",
            "license_name": "Unknown",
            "url": "C:/icons/Empty Id.svg",
            "target_path": "",
            "overwrite": False,
            "generate_fallbacks": True,
        },
    )


def test_diagnose_icon_import_from_maya_forwards_fallback_generation_option(
    monkeypatch,
) -> None:
    cmds = FakeCmds()
    calls: dict[str, object] = {}

    def diagnose_icon_import(
        source_path: str,
        icon_id: str,
        **kwargs: object,
    ) -> object:
        calls["diagnose"] = (source_path, icon_id, kwargs)
        return "report"

    def show_last_report() -> str:
        calls["shown"] = True
        return "formatted"

    monkeypatch.setattr(
        maya_ui.diagnostics,
        "diagnose_icon_import",
        diagnose_icon_import,
    )
    monkeypatch.setattr(maya_ui.diagnostics, "show_last_report", show_last_report)

    result = maya_ui.diagnose_icon_import_from_maya(
        source_path="C:/icons/No Fallbacks.svg",
        icon_id="custom.no-fallbacks",
        generate_fallbacks=False,
        cmds_module=cmds,
    )

    assert result == "report"
    assert calls["shown"] is True
    assert calls["diagnose"] == (
        "C:/icons/No Fallbacks.svg",
        "custom.no-fallbacks",
        {
            "source": "No Fallbacks",
            "license_name": "Unknown",
            "url": "C:/icons/No Fallbacks.svg",
            "target_path": "",
            "overwrite": False,
            "generate_fallbacks": False,
        },
    )


def test_diagnose_icon_import_from_maya_prompt_cancel_returns_none(monkeypatch) -> None:
    cmds = FakeCmds()
    cmds.file_dialog_selection = ["C:/icons/Cancel.svg"]
    cmds.prompt_result = "Cancel"
    shown = False

    def show_last_report() -> str:
        nonlocal shown
        shown = True
        return "formatted"

    monkeypatch.setattr(maya_ui.diagnostics, "show_last_report", show_last_report)

    assert maya_ui.diagnose_icon_import_from_maya(cmds_module=cmds) is None
    assert shown is False


def test_diagnose_icon_import_from_maya_cancel_returns_none(monkeypatch) -> None:
    cmds = FakeCmds()
    cmds.file_dialog_selection = []
    shown = False

    def show_last_report() -> str:
        nonlocal shown
        shown = True
        return "formatted"

    monkeypatch.setattr(maya_ui.diagnostics, "show_last_report", show_last_report)

    assert maya_ui.diagnose_icon_import_from_maya(cmds_module=cmds) is None
    assert shown is False


def test_run_diagnostics_from_maya_collects_and_shows_report(monkeypatch) -> None:
    cmds = FakeCmds()
    calls: dict[str, object] = {}

    def collect_diagnostics(**kwargs: object) -> object:
        calls["collect"] = kwargs
        return "report"

    def show_last_report() -> str:
        calls["shown"] = True
        return "formatted"

    monkeypatch.setattr(maya_ui.diagnostics, "collect_diagnostics", collect_diagnostics)
    monkeypatch.setattr(maya_ui.diagnostics, "show_last_report", show_last_report)

    result = maya_ui.run_diagnostics_from_maya(cmds_module=cmds)

    assert result == "report"
    assert calls["shown"] is True
    assert calls["collect"] == {"cmds_module": cmds}


def test_toggle_edit_mode_forwards_panel(monkeypatch) -> None:
    calls: dict[str, object] = {}

    def toggle_edit_mode(**kwargs: object) -> str:
        calls["toggle"] = kwargs
        return "state"

    monkeypatch.setattr(maya_ui.edit_mode, "toggle_edit_mode", toggle_edit_mode)

    assert maya_ui.toggle_edit_mode(panel="modelPanel4") == "state"
    assert calls["toggle"] == {"panel": "modelPanel4"}


def test_toggle_bind_mode_forwards_to_bind_mode(monkeypatch) -> None:
    calls = []

    def toggle_bind_mode() -> str:
        calls.append("toggle")
        return "state"

    monkeypatch.setattr(maya_ui.bind_mode, "toggle_bind_mode", toggle_bind_mode)

    assert maya_ui.toggle_bind_mode() == "state"
    assert calls == ["toggle"]


def test_show_quick_create_panel_creates_workspace_control(monkeypatch) -> None:
    cmds = FakeCmds()
    calls: list[str] = []

    def restore_quick_create_panel(**kwargs: object) -> str:
        calls.append(str(kwargs))
        return "panel"

    monkeypatch.setattr(maya_ui, "restore_quick_create_panel", restore_quick_create_panel)

    assert maya_ui.show_quick_create_panel(cmds_module=cmds) == "panel"

    assert calls == ["{'user_preset_dir': None}"]
    assert cmds.workspace_controls[maya_ui.QUICK_CREATE_WORKSPACE_CONTROL] == {
        "label": "ActionRail Quick Create",
        "retain": False,
        "floating": True,
        "initialWidth": 900,
        "initialHeight": 680,
        "uiScript": maya_ui.restore_quick_create_panel_command(),
    }


def test_show_quick_create_panel_reopens_existing_workspace_control(monkeypatch) -> None:
    cmds = FakeCmds()
    cmds.workspace_controls[maya_ui.QUICK_CREATE_WORKSPACE_CONTROL] = {"label": "Existing"}
    monkeypatch.setattr(maya_ui, "restore_quick_create_panel", lambda **_kwargs: "panel")

    assert maya_ui.show_quick_create_panel(cmds_module=cmds) == "panel"

    assert cmds.workspace_controls[maya_ui.QUICK_CREATE_WORKSPACE_CONTROL]["edit"] is True
    assert cmds.workspace_controls[maya_ui.QUICK_CREATE_WORKSPACE_CONTROL]["visible"] is True


def test_restore_quick_create_panel_uses_workspace_parent(monkeypatch) -> None:
    calls: dict[str, object] = {}

    def show_quick_create_panel(**kwargs: object) -> str:
        calls["show"] = kwargs
        return "panel"

    monkeypatch.setattr(maya_ui, "_workspace_control_parent", lambda name: f"parent:{name}")
    monkeypatch.setattr(
        maya_ui.quick_create_ui,
        "show_quick_create_panel",
        show_quick_create_panel,
    )

    assert maya_ui.restore_quick_create_panel() == "panel"
    assert calls["show"] == {
        "parent": f"parent:{maya_ui.QUICK_CREATE_WORKSPACE_CONTROL}",
        "user_preset_dir": None,
    }


def test_restore_quick_create_panel_forwards_custom_user_preset_dir(
    monkeypatch,
    tmp_path,
) -> None:
    calls: dict[str, object] = {}

    def show_quick_create_panel(**kwargs: object) -> str:
        calls["show"] = kwargs
        return "panel"

    monkeypatch.setattr(maya_ui, "_workspace_control_parent", lambda name: f"parent:{name}")
    monkeypatch.setattr(
        maya_ui.quick_create_ui,
        "show_quick_create_panel",
        show_quick_create_panel,
    )

    assert maya_ui.restore_quick_create_panel(user_preset_dir=tmp_path) == "panel"
    assert calls["show"] == {
        "parent": f"parent:{maya_ui.QUICK_CREATE_WORKSPACE_CONTROL}",
        "user_preset_dir": tmp_path,
    }


def test_show_action_book_panel_creates_workspace_control(monkeypatch) -> None:
    cmds = FakeCmds()
    calls: list[str] = []

    def restore_action_book_panel() -> str:
        calls.append("restore")
        return "panel"

    monkeypatch.setattr(maya_ui, "restore_action_book_panel", restore_action_book_panel)

    assert maya_ui.show_action_book_panel(cmds_module=cmds) == "panel"

    assert calls == ["restore"]
    assert cmds.workspace_controls[maya_ui.ACTION_BOOK_WORKSPACE_CONTROL] == {
        "label": "ActionRail Action Book",
        "retain": False,
        "floating": True,
        "initialWidth": 720,
        "initialHeight": 680,
        "uiScript": maya_ui.restore_action_book_panel_command(),
    }


def test_show_action_book_panel_reopens_existing_workspace_control(monkeypatch) -> None:
    cmds = FakeCmds()
    cmds.workspace_controls[maya_ui.ACTION_BOOK_WORKSPACE_CONTROL] = {"label": "Existing"}
    monkeypatch.setattr(maya_ui, "restore_action_book_panel", lambda: "panel")

    assert maya_ui.show_action_book_panel(cmds_module=cmds) == "panel"

    assert cmds.workspace_controls[maya_ui.ACTION_BOOK_WORKSPACE_CONTROL]["edit"] is True
    assert cmds.workspace_controls[maya_ui.ACTION_BOOK_WORKSPACE_CONTROL]["visible"] is True


def test_restore_action_book_panel_uses_workspace_parent(monkeypatch) -> None:
    calls: dict[str, object] = {}

    def show_action_book_panel(**kwargs: object) -> str:
        calls["show"] = kwargs
        return "panel"

    monkeypatch.setattr(maya_ui, "_workspace_control_parent", lambda name: f"parent:{name}")
    monkeypatch.setattr(
        maya_ui.action_book_ui,
        "show_action_book_panel",
        show_action_book_panel,
    )

    assert maya_ui.restore_action_book_panel() == "panel"
    assert calls["show"] == {
        "parent": f"parent:{maya_ui.ACTION_BOOK_WORKSPACE_CONTROL}",
    }


def test_workspace_control_parent_handles_missing_maya_ui(monkeypatch) -> None:
    monkeypatch.setattr(maya_ui, "load", lambda: object())
    sys.modules.pop("maya.OpenMayaUI", None)
    sys.modules.pop("maya", None)

    assert maya_ui._workspace_control_parent("Missing") is None


def test_workspace_control_parent_wraps_found_control(monkeypatch) -> None:
    class FakeQtWidgets:
        QWidget = object

    class FakeQt:
        QtWidgets = FakeQtWidgets

        @staticmethod
        def wrap_instance(pointer: int, base: object) -> str:
            return f"{pointer}:{base}"

    class FakeMQtUtil:
        @staticmethod
        def findControl(name: str) -> int:  # noqa: N802
            assert name == "Workspace"
            return 123

    maya_module = ModuleType("maya")
    omui_module = ModuleType("maya.OpenMayaUI")
    omui_module.MQtUtil = FakeMQtUtil
    monkeypatch.setitem(sys.modules, "maya", maya_module)
    monkeypatch.setitem(sys.modules, "maya.OpenMayaUI", omui_module)
    monkeypatch.setattr(maya_ui, "load", lambda: FakeQt)

    assert maya_ui._workspace_control_parent("Workspace") == f"123:{object}"


def test_workspace_control_parent_handles_missing_pointer(monkeypatch) -> None:
    class FakeMQtUtil:
        @staticmethod
        def findControl(name: str) -> None:  # noqa: N802
            assert name == "Workspace"
            return None

    maya_module = ModuleType("maya")
    omui_module = ModuleType("maya.OpenMayaUI")
    omui_module.MQtUtil = FakeMQtUtil
    monkeypatch.setitem(sys.modules, "maya", maya_module)
    monkeypatch.setitem(sys.modules, "maya.OpenMayaUI", omui_module)
    monkeypatch.setattr(maya_ui, "load", lambda: object())

    assert maya_ui._workspace_control_parent("Workspace") is None


def test_workspace_control_parent_handles_find_control_error(monkeypatch) -> None:
    class FakeMQtUtil:
        @staticmethod
        def findControl(name: str) -> None:  # noqa: N802
            assert name == "Workspace"
            raise RuntimeError("deleted")

    maya_module = ModuleType("maya")
    omui_module = ModuleType("maya.OpenMayaUI")
    omui_module.MQtUtil = FakeMQtUtil
    monkeypatch.setitem(sys.modules, "maya", maya_module)
    monkeypatch.setitem(sys.modules, "maya.OpenMayaUI", omui_module)
    monkeypatch.setattr(maya_ui, "load", lambda: object())

    assert maya_ui._workspace_control_parent("Workspace") is None


def test_install_shelf_toggle_is_idempotent() -> None:
    cmds = FakeCmds()

    first = maya_ui.install_shelf_toggle(cmds_module=cmds, mel_module=FakeMel())
    second = maya_ui.install_shelf_toggle(cmds_module=cmds, mel_module=FakeMel())

    assert first == second == maya_ui.SHELF_BUTTON_NAME
    assert tuple(cmds.shelves) == (maya_ui.SHELF_NAME,)
    assert tuple(cmds.shelf_buttons) == (maya_ui.SHELF_BUTTON_NAME,)
    assert cmds.shelves[maya_ui.SHELF_NAME]["parent"] == "ShelfLayout"
    assert cmds.shelf_buttons[maya_ui.SHELF_BUTTON_NAME]["command"] == maya_ui.toggle_command()
    assert cmds.deleted == [(maya_ui.SHELF_BUTTON_NAME, {"control": True})]


def test_install_preset_shelf_toggle_uses_unique_button_name() -> None:
    cmds = FakeCmds()

    button = maya_ui.install_preset_shelf_toggle(
        "artist-tools.main",
        parent="ShelfLayout",
        cmds_module=cmds,
    )

    assert button == "ActionRailTogglePresetShelfButton_artist_tools_main"
    assert cmds.shelf_buttons[button]["command"] == (
        "import actionrail; actionrail.toggle_default('artist-tools.main')"
    )
    assert cmds.shelf_buttons[button]["imageOverlayLabel"] == "AT"


def test_install_preset_shelf_toggle_preserves_custom_user_preset_dir(tmp_path) -> None:
    cmds = FakeCmds()

    button = maya_ui.install_preset_shelf_toggle(
        "artist_tools",
        parent="ShelfLayout",
        user_preset_dir=tmp_path,
        cmds_module=cmds,
    )

    assert cmds.shelf_buttons[button]["command"] == (
        "import actionrail; actionrail.toggle_default('artist_tools', "
        f"user_preset_dir={str(tmp_path)!r})"
    )


def test_uninstall_shelf_toggle_removes_empty_actionrail_shelf_only() -> None:
    cmds = FakeCmds()
    maya_ui.install_shelf_toggle(parent="ShelfLayout", cmds_module=cmds)

    maya_ui.uninstall_shelf_toggle(cmds_module=cmds)

    assert cmds.shelf_buttons == {}
    assert cmds.shelves == {}
    assert (maya_ui.SHELF_BUTTON_NAME, {"control": True}) in cmds.deleted
    assert (maya_ui.SHELF_NAME, {"layout": True}) in cmds.deleted


def test_uninstall_shelf_toggle_leaves_nonempty_shelf() -> None:
    cmds = FakeCmds()
    maya_ui.install_shelf_toggle(parent="ShelfLayout", cmds_module=cmds)
    cmds.shelfButton("OtherButton", parent=maya_ui.SHELF_NAME)

    maya_ui.uninstall_shelf_toggle(cmds_module=cmds)

    assert maya_ui.SHELF_NAME in cmds.shelves
    assert "OtherButton" in cmds.shelf_buttons


def test_uninstall_shelf_toggle_handles_child_query_failure() -> None:
    class BrokenShelfCmds(FakeCmds):
        def shelfLayout(self, name: str, **kwargs: object) -> object:  # noqa: N802
            if kwargs.get("query") and kwargs.get("childArray"):
                raise RuntimeError("shelf deleted")
            return super().shelfLayout(name, **kwargs)

    cmds = BrokenShelfCmds()
    maya_ui.install_shelf_toggle(parent="ShelfLayout", cmds_module=cmds)

    maya_ui.uninstall_shelf_toggle(cmds_module=cmds)

    assert cmds.shelves == {}


def test_default_shelf_parent_requires_mel_when_not_in_maya() -> None:
    try:
        sys.modules.pop("maya.mel", None)
        sys.modules.pop("maya", None)
        try:
            maya_ui._default_shelf_parent()
        except RuntimeError as exc:
            assert "requires maya.mel" in str(exc)
        else:
            raise AssertionError("Expected missing maya.mel to raise")
    finally:
        sys.modules.pop("maya.mel", None)
        sys.modules.pop("maya", None)


def test_maya_ui_imports_cmds_when_available(monkeypatch) -> None:
    cmds = FakeCmds()
    maya_module = ModuleType("maya")
    monkeypatch.setitem(sys.modules, "maya", maya_module)
    monkeypatch.setitem(sys.modules, "maya.cmds", cmds)

    assert maya_ui._require_cmds() is cmds
