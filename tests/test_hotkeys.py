from __future__ import annotations

import pytest

from actionrail.hotkeys import (
    HotkeyConflictError,
    assign_hotkey,
    format_hotkey,
    name_command_name,
    publish_action,
    publish_default_actions,
    publish_preset_slots,
    query_hotkey_binding,
    runtime_command_name,
    slot_target_id,
    unpublish,
)


class FakeCmds:
    def __init__(self) -> None:
        self.runtime_commands: dict[str, dict[str, object]] = {}
        self.name_commands: dict[str, dict[str, object]] = {}
        self.hotkeys: dict[tuple[str, bool, bool, bool, bool, bool], str] = {}

    def runTimeCommand(self, name: str, **kwargs: object) -> object:  # noqa: N802
        if kwargs.get("exists"):
            return name in self.runtime_commands
        if kwargs.get("delete"):
            self.runtime_commands.pop(name, None)
            return None
        payload = dict(kwargs)
        payload.pop("edit", None)
        self.runtime_commands[name] = payload
        return name

    def nameCommand(self, name: str, **kwargs: object) -> str:  # noqa: N802
        self.name_commands[name] = dict(kwargs)
        return name

    def hotkey(self, **kwargs: object) -> object:
        key = (
            str(kwargs["keyShortcut"]),
            bool(kwargs.get("ctrlModifier", False)),
            bool(kwargs.get("altModifier", False)),
            bool(kwargs.get("shiftModifier", False)),
            bool(kwargs.get("commandModifier", False)),
            "releaseName" in kwargs,
        )
        if kwargs.get("query"):
            return self.hotkeys.get(key)

        value = kwargs.get("releaseName", kwargs.get("name"))
        if value:
            self.hotkeys[key] = str(value)
        return None


def test_runtime_command_names_are_stable_maya_identifiers() -> None:
    assert runtime_command_name("action", "maya.tool.move") == "ActionRail_action_maya_tool_move"
    assert runtime_command_name("slot", "transform_stack.set_key") == (
        "ActionRail_slot_transform_stack_set_key"
    )


def test_slot_target_id_does_not_duplicate_preset_prefix() -> None:
    assert slot_target_id("transform_stack", "set_key") == "transform_stack.set_key"
    assert slot_target_id("transform_stack", "transform_stack.set_key") == (
        "transform_stack.set_key"
    )


def test_publish_action_creates_runtime_and_name_command() -> None:
    cmds = FakeCmds()

    published = publish_action("maya.tool.move", label="Move", cmds_module=cmds)

    assert published.runtime_command == "ActionRail_action_maya_tool_move"
    assert published.name_command == "ActionRail_action_maya_tool_move_NameCommand"
    assert cmds.runtime_commands[published.runtime_command]["command"] == (
        "import actionrail; actionrail.run_action('maya.tool.move')"
    )
    assert cmds.runtime_commands[published.runtime_command]["commandLanguage"] == "python"
    assert cmds.runtime_commands[published.runtime_command]["showInHotkeyEditor"] is True
    assert cmds.name_commands[published.name_command]["command"] == published.runtime_command


def test_publish_action_updates_existing_runtime_command() -> None:
    cmds = FakeCmds()

    publish_action("maya.tool.move", label="Move", cmds_module=cmds)
    publish_action("maya.tool.move", label="Move Updated", cmds_module=cmds)

    command = cmds.runtime_commands["ActionRail_action_maya_tool_move"]
    assert command["label"] == "Move Updated"
    assert command["annotation"] == "Move Updated"


def test_publish_default_actions_creates_one_command_per_registered_action() -> None:
    cmds = FakeCmds()

    published = publish_default_actions(cmds_module=cmds)

    assert [command.runtime_command for command in published] == [
        "ActionRail_action_maya_tool_move",
        "ActionRail_action_maya_tool_translate",
        "ActionRail_action_maya_tool_rotate",
        "ActionRail_action_maya_tool_scale",
        "ActionRail_action_maya_anim_set_key",
    ]


def test_publish_preset_slots_skips_spacers() -> None:
    cmds = FakeCmds()

    published = publish_preset_slots("transform_stack", cmds_module=cmds)

    assert [command.target_id for command in published] == [
        "transform_stack.move",
        "transform_stack.translate",
        "transform_stack.rotate",
        "transform_stack.scale",
        "transform_stack.set_key",
    ]
    assert "gap" not in " ".join(cmds.runtime_commands)


def test_assign_hotkey_rejects_existing_binding_without_overwrite() -> None:
    cmds = FakeCmds()
    cmds.hotkeys[("S", False, False, False, False, False)] = "ExistingCommand"

    with pytest.raises(HotkeyConflictError, match="ExistingCommand"):
        assign_hotkey("ActionRail_slot_transform_stack_set_key_NameCommand", "S", cmds_module=cmds)


def test_assign_hotkey_allows_same_binding_without_overwrite() -> None:
    cmds = FakeCmds()
    name = name_command_name("ActionRail_action_maya_anim_set_key")
    cmds.hotkeys[("S", False, False, False, False, False)] = name

    binding = assign_hotkey(name, "S", cmds_module=cmds)

    assert binding.name == name
    assert query_hotkey_binding("S", cmds_module=cmds).name == name


def test_assign_hotkey_allows_overwrite_and_reports_binding() -> None:
    cmds = FakeCmds()
    name = name_command_name("ActionRail_action_maya_anim_set_key")
    cmds.hotkeys[("S", False, False, False, False, False)] = "ExistingCommand"

    binding = assign_hotkey(name, "S", overwrite=True, cmds_module=cmds)

    assert binding.name == name
    assert query_hotkey_binding("S", cmds_module=cmds).name == name


def test_assign_hotkey_supports_release_and_command_modifiers() -> None:
    cmds = FakeCmds()
    name = name_command_name("ActionRail_action_maya_tool_rotate")

    binding = assign_hotkey(
        name,
        "R",
        ctrl=True,
        alt=True,
        shift=True,
        command=True,
        release=True,
        cmds_module=cmds,
    )

    assert binding.name == name
    assert binding.ctrl is True
    assert binding.alt is True
    assert binding.shift is True
    assert binding.command is True
    assert binding.release is True
    assert query_hotkey_binding(
        "R",
        ctrl=True,
        alt=True,
        shift=True,
        command=True,
        release=True,
        cmds_module=cmds,
    ).name == name


def test_conflict_message_includes_all_pressed_modifiers() -> None:
    cmds = FakeCmds()
    cmds.hotkeys[("K", True, True, True, True, False)] = "ExistingCommand"

    with pytest.raises(HotkeyConflictError, match=r"Ctrl\+Alt\+Shift\+Command\+K"):
        assign_hotkey(
            "ActionRail_slot_transform_stack_set_key_NameCommand",
            "K",
            ctrl=True,
            alt=True,
            shift=True,
            command=True,
            cmds_module=cmds,
        )


def test_unpublish_removes_existing_runtime_command() -> None:
    cmds = FakeCmds()
    published = publish_action("maya.tool.move", label="Move", cmds_module=cmds)

    unpublish(published, cmds_module=cmds)

    assert published.runtime_command not in cmds.runtime_commands


def test_unpublish_ignores_missing_runtime_command() -> None:
    cmds = FakeCmds()

    unpublish("ActionRail_missing", cmds_module=cmds)

    assert cmds.runtime_commands == {}


def test_format_hotkey_includes_modifiers_in_order() -> None:
    assert format_hotkey("K", ctrl=True, alt=True, shift=True, command=True) == (
        "Ctrl+Alt+Shift+Command+K"
    )
