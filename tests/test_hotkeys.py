from __future__ import annotations

import pytest

from actionrail.hotkeys import (
    HotkeyConflictError,
    _clear_published_cache,
    assign_hotkey,
    assign_published_hotkey,
    assign_slot_hotkey,
    clear_visible_key_label,
    format_hotkey,
    name_command_name,
    publish_action,
    publish_default_actions,
    publish_preset_slots,
    publish_slot,
    query_hotkey_binding,
    runtime_command_name,
    slot_target_id,
    sync_default_actions,
    sync_preset_slots,
    unpublish,
)


@pytest.fixture(autouse=True)
def clear_published_cache() -> None:
    _clear_published_cache()


class FakeCmds:
    def __init__(self) -> None:
        self.runtime_commands: dict[str, dict[str, object]] = {}
        self.name_commands: dict[str, dict[str, object]] = {}
        self.hotkeys: dict[tuple[str, bool, bool, bool, bool, bool], str] = {}
        self.query_hotkeys = True
        self.reject_duplicate_name_commands = False

    def runTimeCommand(self, name: str = "", **kwargs: object) -> object:  # noqa: N802
        if kwargs.get("userCommandArray"):
            return tuple(self.runtime_commands)
        if kwargs.get("exists"):
            return name in self.runtime_commands
        if kwargs.get("query") and kwargs.get("command"):
            return self.runtime_commands[name].get("command")
        if kwargs.get("delete"):
            self.runtime_commands.pop(name, None)
            return None
        payload = dict(kwargs)
        payload.pop("edit", None)
        self.runtime_commands[name] = payload
        return name

    def nameCommand(self, name: str, **kwargs: object) -> str:  # noqa: N802
        if self.reject_duplicate_name_commands and name in self.name_commands:
            raise RuntimeError(f"nameCommand already exists: {name}")
        self.name_commands[name] = dict(kwargs)
        return name

    def hotkey(self, *args: object, **kwargs: object) -> object:
        key_shortcut = args[0] if args else kwargs["keyShortcut"]
        key = (
            str(key_shortcut),
            bool(kwargs.get("ctrlModifier", False)),
            bool(kwargs.get("altModifier", False)),
            bool(kwargs.get("shiftModifier", False)),
            bool(kwargs.get("commandModifier", False)),
            "releaseName" in kwargs,
        )
        if kwargs.get("query"):
            if not self.query_hotkeys:
                return None
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


def test_publish_action_ignores_existing_name_command() -> None:
    cmds = FakeCmds()
    cmds.reject_duplicate_name_commands = True

    first = publish_action("maya.tool.move", label="Move", cmds_module=cmds)
    second = publish_action("maya.tool.move", label="Move Updated", cmds_module=cmds)

    assert first.name_command == second.name_command
    assert cmds.runtime_commands[second.runtime_command]["label"] == "Move Updated"


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
        "transform_stack.rotate",
        "transform_stack.scale",
        "transform_stack.set_key",
    ]
    assert "gap" not in " ".join(cmds.runtime_commands)


def test_publish_slot_command_uses_normalized_slot_id() -> None:
    cmds = FakeCmds()

    published = publish_preset_slots("transform_stack", cmds_module=cmds)
    set_key = next(command for command in published if command.target_id.endswith(".set_key"))

    assert cmds.runtime_commands[set_key.runtime_command]["command"] == (
        "import actionrail; actionrail.run_slot('transform_stack', 'transform_stack.set_key')"
    )


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


def test_assign_published_hotkey_syncs_slot_label(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cmds = FakeCmds()
    published = publish_slot("transform_stack", "set_key", label="Set Key", cmds_module=cmds)
    updates: list[tuple[str, str, str]] = []

    def update_slot_key_label(preset_id: str, slot_id: str, key_label: str) -> int:
        updates.append((preset_id, slot_id, key_label))
        return 1

    monkeypatch.setattr("actionrail.runtime.update_slot_key_label", update_slot_key_label)

    binding = assign_published_hotkey(published, "K", ctrl=True, cmds_module=cmds)

    assert binding.name == published.name_command
    assert updates == [("transform_stack", "set_key", "Ctrl+K")]


def test_assign_published_hotkey_clears_overwritten_slot_label(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cmds = FakeCmds()
    move = publish_slot("transform_stack", "move", label="Move", cmds_module=cmds)
    set_key = publish_slot("transform_stack", "set_key", label="Set Key", cmds_module=cmds)
    updates: list[tuple[str, str, str]] = []

    def update_slot_key_label(preset_id: str, slot_id: str, key_label: str) -> int:
        updates.append((preset_id, slot_id, key_label))
        return 1

    monkeypatch.setattr("actionrail.runtime.update_slot_key_label", update_slot_key_label)

    assign_published_hotkey(move, "S", cmds_module=cmds)
    assign_published_hotkey(set_key, "S", overwrite=True, cmds_module=cmds)

    assert updates == [
        ("transform_stack", "move", "S"),
        ("transform_stack", "move", ""),
        ("transform_stack", "set_key", "S"),
    ]


def test_assign_published_hotkey_clears_cached_slot_when_query_misses(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cmds = FakeCmds()
    cmds.query_hotkeys = False
    move = publish_slot("transform_stack", "move", label="Move", cmds_module=cmds)
    set_key = publish_slot("transform_stack", "set_key", label="Set Key", cmds_module=cmds)
    updates: list[tuple[str, str, str]] = []

    def update_slot_key_label(preset_id: str, slot_id: str, key_label: str) -> int:
        updates.append((preset_id, slot_id, key_label))
        return 1

    monkeypatch.setattr("actionrail.runtime.update_slot_key_label", update_slot_key_label)

    assign_published_hotkey(move, "F12", cmds_module=cmds)
    assign_published_hotkey(set_key, "F12", overwrite=True, cmds_module=cmds)

    assert updates == [
        ("transform_stack", "move", "F12"),
        ("transform_stack", "move", ""),
        ("transform_stack", "set_key", "F12"),
    ]


def test_clear_visible_key_label_resolves_persisted_builtin_slot_name_command(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    updates: list[tuple[str, str, str]] = []

    def update_slot_key_label(preset_id: str, slot_id: str, key_label: str) -> int:
        updates.append((preset_id, slot_id, key_label))
        return 1

    monkeypatch.setattr("actionrail.runtime.update_slot_key_label", update_slot_key_label)

    cleared = clear_visible_key_label("ActionRail_slot_transform_stack_set_key_NameCommand")

    assert cleared == 1
    assert updates == [("transform_stack", "set_key", "")]


def test_assign_slot_hotkey_publishes_assigns_and_syncs_label(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cmds = FakeCmds()
    updates: list[tuple[str, str, str]] = []

    def update_slot_key_label(preset_id: str, slot_id: str, key_label: str) -> int:
        updates.append((preset_id, slot_id, key_label))
        return 1

    monkeypatch.setattr("actionrail.runtime.update_slot_key_label", update_slot_key_label)

    binding = assign_slot_hotkey(
        "transform_stack",
        "set_key",
        "S",
        release=True,
        cmds_module=cmds,
    )

    assert binding.name == "ActionRail_slot_transform_stack_set_key_NameCommand"
    assert "ActionRail_slot_transform_stack_set_key" in cmds.runtime_commands
    assert updates == [("transform_stack", "set_key", "S Up")]


def test_assign_published_hotkey_leaves_action_labels_alone(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cmds = FakeCmds()
    published = publish_action("maya.tool.rotate", label="Rotate", cmds_module=cmds)
    updates: list[tuple[str, str, str]] = []

    def update_slot_key_label(preset_id: str, slot_id: str, key_label: str) -> int:
        updates.append((preset_id, slot_id, key_label))
        return 1

    monkeypatch.setattr("actionrail.runtime.update_slot_key_label", update_slot_key_label)

    assign_published_hotkey(published, "R", cmds_module=cmds)

    assert updates == []


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


def test_sync_preset_slots_removes_stale_slot_command() -> None:
    cmds = FakeCmds()
    stale = publish_slot("transform_stack", "removed_slot", label="Removed", cmds_module=cmds)

    result = sync_preset_slots("transform_stack", cmds_module=cmds)

    assert stale not in result.published
    assert result.unpublished == (stale,)
    assert stale.runtime_command not in cmds.runtime_commands
    assert "ActionRail_slot_transform_stack_set_key" in cmds.runtime_commands


def test_sync_preset_slots_leaves_unparseable_prefixed_command_alone() -> None:
    cmds = FakeCmds()
    cmds.runtime_commands["ActionRail_slot_transform_stack_custom"] = {
        "command": "python(\"print('not generated by ActionRail')\")",
    }

    result = sync_preset_slots("transform_stack", cmds_module=cmds)

    assert result.unpublished == ()
    assert "ActionRail_slot_transform_stack_custom" in cmds.runtime_commands


def test_sync_default_actions_removes_stale_action_command() -> None:
    cmds = FakeCmds()
    stale = publish_action("maya.tool.removed", label="Removed", cmds_module=cmds)

    result = sync_default_actions(cmds_module=cmds)

    assert stale not in result.published
    assert result.unpublished == (stale,)
    assert stale.runtime_command not in cmds.runtime_commands
    assert "ActionRail_action_maya_tool_move" in cmds.runtime_commands


def test_unpublish_forgets_cached_slot_label() -> None:
    cmds = FakeCmds()
    published = publish_slot("transform_stack", "set_key", label="Set Key", cmds_module=cmds)

    unpublish(published, cmds_module=cmds)

    assert clear_visible_key_label(published.name_command) == 0


def test_format_hotkey_includes_modifiers_in_order() -> None:
    assert format_hotkey("K", ctrl=True, alt=True, shift=True, command=True) == (
        "Ctrl+Alt+Shift+Command+K"
    )
