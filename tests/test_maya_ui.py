from __future__ import annotations

from actionrail import maya_ui


class FakeCmds:
    def __init__(self) -> None:
        self.menus: dict[str, dict[str, object]] = {}
        self.menu_items: dict[str, dict[str, object]] = {}
        self.shelves: dict[str, dict[str, object]] = {}
        self.shelf_buttons: dict[str, dict[str, object]] = {}
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

    def deleteUI(self, name: str, **kwargs: object) -> None:  # noqa: N802
        self.deleted.append((name, dict(kwargs)))
        if kwargs.get("menuItem"):
            self.menu_items.pop(name, None)
        elif kwargs.get("menu"):
            self.menus.pop(name, None)
        elif kwargs.get("control"):
            self.shelf_buttons.pop(name, None)
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
    assert maya_ui.diagnose_icon_import_from_maya_command() == (
        "import actionrail; actionrail.diagnose_icon_import_from_maya()"
    )


def test_toggle_default_shows_when_hidden_and_hides_when_visible(
    monkeypatch,
) -> None:
    active_ids: set[str] = set()
    calls: list[tuple[str, str]] = []

    def active_overlay_ids() -> tuple[str, ...]:
        return tuple(active_ids)

    def show_example(preset_id: str, *, panel: str | None = None) -> None:
        calls.append(("show", f"{preset_id}:{panel}"))
        active_ids.add(preset_id)

    def hide_example(preset_id: str) -> None:
        calls.append(("hide", preset_id))
        active_ids.discard(preset_id)

    monkeypatch.setattr(maya_ui.runtime, "active_overlay_ids", active_overlay_ids)
    monkeypatch.setattr(maya_ui.runtime, "show_example", show_example)
    monkeypatch.setattr(maya_ui.runtime, "hide_example", hide_example)

    assert maya_ui.toggle_default(panel="modelPanel4") == "shown"
    assert maya_ui.toggle_default() == "hidden"
    assert calls == [
        ("show", "transform_stack:modelPanel4"),
        ("hide", "transform_stack"),
    ]


def test_install_menu_toggle_is_idempotent() -> None:
    cmds = FakeCmds()

    first = maya_ui.install_menu_toggle(cmds_module=cmds)
    second = maya_ui.install_menu_toggle(cmds_module=cmds)

    assert first == second == maya_ui.MENU_ITEM_NAME
    assert tuple(cmds.menus) == (maya_ui.MENU_NAME,)
    assert tuple(cmds.menu_items) == (
        maya_ui.MENU_ITEM_NAME,
        maya_ui.MENU_ICON_IMPORT_DIAGNOSTICS_ITEM_NAME,
        maya_ui.MENU_DIAGNOSTICS_ITEM_NAME,
    )
    assert cmds.menu_items[maya_ui.MENU_ITEM_NAME]["command"] == maya_ui.toggle_command()
    assert cmds.menu_items[maya_ui.MENU_ICON_IMPORT_DIAGNOSTICS_ITEM_NAME][
        "command"
    ] == maya_ui.diagnose_icon_import_from_maya_command()
    assert cmds.menu_items[maya_ui.MENU_DIAGNOSTICS_ITEM_NAME]["command"] == (
        "import actionrail; actionrail.show_last_report()"
    )
    assert cmds.deleted == [
        (maya_ui.MENU_ITEM_NAME, {"menuItem": True}),
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
    assert (maya_ui.MENU_DIAGNOSTICS_ITEM_NAME, {"menuItem": True}) in cmds.deleted
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
