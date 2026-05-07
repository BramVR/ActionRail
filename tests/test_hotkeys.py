from __future__ import annotations

import sys
from collections.abc import Iterator
from types import ModuleType

import pytest

import actionrail
import actionrail.hotkeys as hotkeys
from actionrail.authoring import DraftRail, DraftSlot, save_user_preset
from actionrail.hotkeys import (
    HotkeyConflictError,
    PublishedCommand,
    SlotBindingTarget,
    assign_hotkey,
    assign_published_hotkey,
    assign_slot_hotkey,
    clear_visible_key_label,
    clear_visible_published_key_label,
    format_hotkey,
    list_published_commands,
    name_command_name,
    publish_action,
    publish_default_actions,
    publish_preset_slots,
    publish_slot,
    query_hotkey_binding,
    runtime_command_name,
    slot_binding_targets,
    slot_target_id,
    sync_default_actions,
    sync_preset_slots,
    sync_visible_key_label,
    unpublish,
)


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


class StringCommandArrayCmds(FakeCmds):
    def runTimeCommand(self, name: str = "", **kwargs: object) -> object:  # noqa: N802
        if kwargs.get("userCommandArray"):
            return "ActionRail_action_maya_tool_move"
        return super().runTimeCommand(name, **kwargs)


class BrokenQueryCmds(FakeCmds):
    def runTimeCommand(self, name: str = "", **kwargs: object) -> object:  # noqa: N802
        if kwargs.get("query") and kwargs.get("command"):
            raise RuntimeError("command deleted")
        return super().runTimeCommand(name, **kwargs)


class FailingNameCommandCmds(FakeCmds):
    def nameCommand(self, name: str, **kwargs: object) -> str:  # noqa: N802
        raise RuntimeError("permission denied")


class RaisingExistsCmds(FakeCmds):
    def runTimeCommand(self, name: str = "", **kwargs: object) -> object:  # noqa: N802
        if kwargs.get("exists"):
            raise RuntimeError("runtime command query failed")
        return super().runTimeCommand(name, **kwargs)


@pytest.fixture(autouse=True)
def forget_cached_published_commands() -> Iterator[None]:
    _forget_known_published_commands()
    yield
    _forget_known_published_commands()


def _forget_known_published_commands() -> None:
    cmds = FakeCmds()
    for command in _known_published_commands():
        unpublish(command, cmds_module=cmds)


def _known_published_commands() -> tuple[PublishedCommand, ...]:
    action_ids = (
        "maya.tool.move",
        "maya.tool.translate",
        "maya.tool.rotate",
        "maya.tool.scale",
        "maya.anim.set_key",
        "maya.tool.removed",
    )
    slot_ids = (
        ("transform_stack", "move"),
        ("transform_stack", "rotate"),
        ("transform_stack", "scale"),
        ("transform_stack", "set_key"),
        ("transform_stack", "removed_slot"),
        ("horizontal_tools", "rotate"),
        ("unknown", "slot"),
    )
    actions = tuple(
        PublishedCommand(
            "action",
            action_id,
            runtime_command_name("action", action_id),
            name_command_name(runtime_command_name("action", action_id)),
        )
        for action_id in action_ids
    )
    slots = tuple(
        PublishedCommand(
            "slot",
            slot_target_id(preset_id, slot_id),
            runtime_command_name("slot", slot_target_id(preset_id, slot_id)),
            name_command_name(runtime_command_name("slot", slot_target_id(preset_id, slot_id))),
        )
        for preset_id, slot_id in slot_ids
    )
    return (*actions, *slots)


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


def test_publish_action_reraises_unexpected_name_command_errors() -> None:
    with pytest.raises(RuntimeError, match="permission denied"):
        publish_action("maya.tool.move", label="Move", cmds_module=FailingNameCommandCmds())


def test_publish_default_actions_creates_one_command_per_registered_action() -> None:
    cmds = FakeCmds()

    published = publish_default_actions(cmds_module=cmds)

    assert [command.runtime_command for command in published] == [
        "ActionRail_action_maya_tool_move",
        "ActionRail_action_maya_tool_translate",
        "ActionRail_action_maya_tool_rotate",
        "ActionRail_action_maya_tool_scale",
        "ActionRail_action_maya_anim_set_key",
        "ActionRail_action_maya_display_toggle_grid",
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


def test_slot_binding_targets_describe_action_bearing_slots() -> None:
    targets = slot_binding_targets("transform_stack")

    assert targets == (
        SlotBindingTarget(
            preset_id="transform_stack",
            slot_id="move",
            target_id="transform_stack.move",
            label="M",
            action="maya.tool.move",
            key_label="",
            runtime_command="ActionRail_slot_transform_stack_move",
            name_command="ActionRail_slot_transform_stack_move_NameCommand",
        ),
        SlotBindingTarget(
            preset_id="transform_stack",
            slot_id="rotate",
            target_id="transform_stack.rotate",
            label="R",
            action="maya.tool.rotate",
            key_label="",
            runtime_command="ActionRail_slot_transform_stack_rotate",
            name_command="ActionRail_slot_transform_stack_rotate_NameCommand",
        ),
        SlotBindingTarget(
            preset_id="transform_stack",
            slot_id="scale",
            target_id="transform_stack.scale",
            label="S",
            action="maya.tool.scale",
            key_label="",
            runtime_command="ActionRail_slot_transform_stack_scale",
            name_command="ActionRail_slot_transform_stack_scale_NameCommand",
        ),
        SlotBindingTarget(
            preset_id="transform_stack",
            slot_id="set_key",
            target_id="transform_stack.set_key",
            label="K",
            action="maya.anim.set_key",
            key_label="S",
            runtime_command="ActionRail_slot_transform_stack_set_key",
            name_command="ActionRail_slot_transform_stack_set_key_NameCommand",
        ),
    )


def test_slot_binding_targets_can_include_empty_slots(tmp_path) -> None:
    save_user_preset(
        DraftRail(
            id="blank_tools",
            slots=(
                DraftSlot(id="move", label="M", action="maya.tool.move"),
                DraftSlot(id="empty", label="2"),
            ),
        ),
        preset_dir=tmp_path,
    )

    targets = slot_binding_targets(
        "blank_tools",
        user_preset_dir=tmp_path,
        include_empty=True,
    )

    assert [target.slot_id for target in targets] == ["move", "empty"]
    assert targets[1].action == ""
    assert targets[1].runtime_command == "ActionRail_slot_blank_tools_empty"
    assert targets[1].user_preset_dir == str(tmp_path)


def test_slot_binding_targets_can_publish_exact_maya_commands(tmp_path) -> None:
    save_user_preset(
        DraftRail(
            id="artist_tools",
            slots=(DraftSlot(id="move", label="M", action="maya.tool.move"),),
        ),
        preset_dir=tmp_path,
    )
    cmds = FakeCmds()

    targets = slot_binding_targets(
        "artist_tools",
        user_preset_dir=tmp_path,
        publish=True,
        cmds_module=cmds,
    )

    assert targets == (
        SlotBindingTarget(
            preset_id="artist_tools",
            slot_id="move",
            target_id="artist_tools.move",
            label="M",
            action="maya.tool.move",
            key_label="",
            runtime_command="ActionRail_slot_artist_tools_move",
            name_command="ActionRail_slot_artist_tools_move_NameCommand",
            published=True,
            user_preset_dir=str(tmp_path),
        ),
    )
    assert cmds.runtime_commands["ActionRail_slot_artist_tools_move"]["command"] == (
        "import actionrail; actionrail.run_slot("
        f"'artist_tools', 'artist_tools.move', user_preset_dir={str(tmp_path)!r})"
    )


def test_public_api_exposes_slot_binding_helpers() -> None:
    assert actionrail.SlotBindingTarget is SlotBindingTarget
    assert actionrail.slot_binding_targets("transform_stack")[0].target_id == (
        "transform_stack.move"
    )
    assert actionrail.format_hotkey("K", ctrl=True) == "Ctrl+K"


def test_publish_preset_slots_resolves_saved_user_preset(tmp_path) -> None:
    save_user_preset(
        DraftRail(
            id="artist_tools",
            slots=(
                DraftSlot(id="move", label="M", action="maya.tool.move"),
                DraftSlot(id="gap", type="spacer", size=8),
                DraftSlot(id="empty", label="E"),
            ),
        ),
        preset_dir=tmp_path,
    )
    cmds = FakeCmds()

    published = publish_preset_slots(
        "artist_tools",
        user_preset_dir=tmp_path,
        cmds_module=cmds,
    )

    assert [command.target_id for command in published] == ["artist_tools.move"]
    assert cmds.runtime_commands["ActionRail_slot_artist_tools_move"]["command"] == (
        "import actionrail; actionrail.run_slot("
        f"'artist_tools', 'artist_tools.move', user_preset_dir={str(tmp_path)!r})"
    )


def test_publish_preset_slots_disambiguates_sanitized_name_collisions(tmp_path) -> None:
    save_user_preset(
        DraftRail(
            id="foo.bar",
            slots=(DraftSlot(id="baz", label="A", action="maya.tool.move"),),
        ),
        preset_dir=tmp_path,
    )
    save_user_preset(
        DraftRail(
            id="foo",
            slots=(DraftSlot(id="bar_baz", label="B", action="maya.tool.rotate"),),
        ),
        preset_dir=tmp_path,
    )
    cmds = FakeCmds()

    first = publish_preset_slots("foo.bar", user_preset_dir=tmp_path, cmds_module=cmds)[0]
    second = publish_preset_slots("foo", user_preset_dir=tmp_path, cmds_module=cmds)[0]

    assert first.runtime_command == "ActionRail_slot_foo_bar_baz"
    assert second.runtime_command.startswith("ActionRail_slot_foo_bar_baz_h")
    assert first.runtime_command != second.runtime_command
    assert list_published_commands(cmds_module=cmds) == (first, second)
    assert cmds.runtime_commands[first.runtime_command]["command"] == (
        "import actionrail; actionrail.run_slot("
        f"'foo.bar', 'foo.bar.baz', user_preset_dir={str(tmp_path)!r})"
    )
    assert cmds.runtime_commands[second.runtime_command]["command"] == (
        "import actionrail; actionrail.run_slot("
        f"'foo', 'foo.bar_baz', user_preset_dir={str(tmp_path)!r})"
    )


def test_publish_slot_reuses_existing_hashed_command_for_same_target() -> None:
    cmds = FakeCmds()

    publish_slot("foo.bar", "baz", cmds_module=cmds)
    hashed = publish_slot("foo", "bar_baz", cmds_module=cmds)
    republished = publish_slot("foo", "bar_baz", cmds_module=cmds)

    assert republished.runtime_command == hashed.runtime_command


def test_publish_slot_reports_unresolvable_runtime_name_collision(monkeypatch) -> None:
    cmds = FakeCmds()
    monkeypatch.setattr(
        hotkeys,
        "_hashed_runtime_command_name",
        lambda _kind, _target_id: "ActionRail_slot_shared_hash",
    )

    publish_slot("foo.bar", "baz", cmds_module=cmds)
    publish_slot("foo", "bar_baz", cmds_module=cmds)

    with pytest.raises(RuntimeError, match="collision could not be resolved"):
        publish_slot("foo", "bar-baz", cmds_module=cmds)


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


def test_assign_published_hotkey_clears_uncached_existing_slot_label(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cmds = FakeCmds()
    cmds.hotkeys[("S", False, False, False, False, False)] = (
        "ActionRail_slot_transform_stack_set_key_NameCommand"
    )
    move = publish_slot("transform_stack", "move", label="Move", cmds_module=cmds)
    updates: list[tuple[str, str, str]] = []

    def update_slot_key_label(preset_id: str, slot_id: str, key_label: str) -> int:
        updates.append((preset_id, slot_id, key_label))
        return 1

    monkeypatch.setattr("actionrail.runtime.update_slot_key_label", update_slot_key_label)

    assign_published_hotkey(move, "S", overwrite=True, cmds_module=cmds)

    assert updates == [
        ("transform_stack", "set_key", ""),
        ("transform_stack", "move", "S"),
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


def test_clear_visible_key_label_resolves_persisted_user_slot_name_command(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    save_user_preset(
        DraftRail(
            id="artist_tools",
            slots=(DraftSlot(id="move", label="M", action="maya.tool.move"),),
        ),
        preset_dir=tmp_path,
    )
    monkeypatch.setenv("ACTIONRAIL_USER_PRESET_DIR", str(tmp_path))
    updates: list[tuple[str, str, str]] = []

    def update_slot_key_label(preset_id: str, slot_id: str, key_label: str) -> int:
        updates.append((preset_id, slot_id, key_label))
        return 1

    monkeypatch.setattr("actionrail.runtime.update_slot_key_label", update_slot_key_label)

    cleared = clear_visible_key_label("ActionRail_slot_artist_tools_move_NameCommand")

    assert cleared == 1
    assert updates == [("artist_tools", "move", "")]


def test_clear_visible_key_label_reads_persisted_runtime_payload_for_dotted_user_ids(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    save_user_preset(
        DraftRail(
            id="studio.tools",
            slots=(DraftSlot(id="move", label="M", action="maya.tool.move"),),
        ),
        preset_dir=tmp_path,
    )
    cmds = FakeCmds()
    published = publish_preset_slots(
        "studio.tools",
        user_preset_dir=tmp_path,
        cmds_module=cmds,
    )[0]
    unpublish(published, cmds_module=FakeCmds())
    updates: list[tuple[str, str, str]] = []

    def update_slot_key_label(preset_id: str, slot_id: str, key_label: str) -> int:
        updates.append((preset_id, slot_id, key_label))
        return 1

    monkeypatch.setattr("actionrail.runtime.update_slot_key_label", update_slot_key_label)

    cleared = clear_visible_key_label(published.name_command, cmds_module=cmds)

    assert cleared == 1
    assert updates == [("studio.tools", "move", "")]


def test_clear_visible_key_label_uses_published_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cmds = FakeCmds()
    published = publish_slot("transform_stack", "set_key", label="Set Key", cmds_module=cmds)
    updates: list[tuple[str, str, str]] = []

    def update_slot_key_label(preset_id: str, slot_id: str, key_label: str) -> int:
        updates.append((preset_id, slot_id, key_label))
        return 1

    monkeypatch.setattr("actionrail.runtime.update_slot_key_label", update_slot_key_label)

    assert clear_visible_key_label(published.name_command) == 1
    assert updates == [("transform_stack", "set_key", "")]


def test_clear_visible_published_key_label_splits_legacy_slot_targets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    updates: list[tuple[str, str, str]] = []

    def update_slot_key_label(preset_id: str, slot_id: str, key_label: str) -> int:
        updates.append((preset_id, slot_id, key_label))
        return 1

    monkeypatch.setattr("actionrail.runtime.update_slot_key_label", update_slot_key_label)

    assert (
        clear_visible_published_key_label(
            PublishedCommand(
                "slot",
                "transform_stack.set_key",
                "ActionRail_slot_transform_stack_set_key",
                "ActionRail_slot_transform_stack_set_key_NameCommand",
            )
        )
        == 1
    )
    assert (
        clear_visible_published_key_label(
            PublishedCommand(
                "slot",
                "custom.move",
                "ActionRail_slot_custom_move",
                "ActionRail_slot_custom_move_NameCommand",
            )
        )
        == 1
    )
    assert updates == [
        ("transform_stack", "set_key", ""),
        ("custom", "move", ""),
    ]


def test_clear_visible_key_label_ignores_runtime_command_exists_errors() -> None:
    assert (
        clear_visible_key_label(
            "ActionRail_slot_custom_move_NameCommand",
            cmds_module=RaisingExistsCmds(),
        )
        == 0
    )


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


def test_assign_slot_hotkey_binds_saved_user_slot_by_id(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    save_user_preset(
        DraftRail(
            id="artist_tools",
            slots=(DraftSlot(id="move", label="M", action="maya.tool.move"),),
        ),
        preset_dir=tmp_path,
    )
    cmds = FakeCmds()
    updates: list[tuple[str, str, str]] = []

    def update_slot_key_label(preset_id: str, slot_id: str, key_label: str) -> int:
        updates.append((preset_id, slot_id, key_label))
        return 1

    monkeypatch.setattr("actionrail.runtime.update_slot_key_label", update_slot_key_label)

    binding = assign_slot_hotkey("artist_tools", "move", "M", cmds_module=cmds)

    assert binding.name == "ActionRail_slot_artist_tools_move_NameCommand"
    assert cmds.runtime_commands["ActionRail_slot_artist_tools_move"]["command"] == (
        "import actionrail; actionrail.run_slot('artist_tools', 'artist_tools.move')"
    )
    assert updates == [("artist_tools", "move", "M")]


def test_assign_slot_hotkey_can_publish_saved_user_slot_with_custom_store(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    save_user_preset(
        DraftRail(
            id="artist_tools",
            slots=(DraftSlot(id="move", label="M", action="maya.tool.move"),),
        ),
        preset_dir=tmp_path,
    )
    cmds = FakeCmds()
    updates: list[tuple[str, str, str]] = []

    def update_slot_key_label(preset_id: str, slot_id: str, key_label: str) -> int:
        updates.append((preset_id, slot_id, key_label))
        return 1

    monkeypatch.setattr("actionrail.runtime.update_slot_key_label", update_slot_key_label)

    binding = assign_slot_hotkey(
        "artist_tools",
        "move",
        "M",
        user_preset_dir=tmp_path,
        cmds_module=cmds,
    )

    assert binding.name == "ActionRail_slot_artist_tools_move_NameCommand"
    assert cmds.runtime_commands["ActionRail_slot_artist_tools_move"]["command"] == (
        "import actionrail; actionrail.run_slot("
        f"'artist_tools', 'artist_tools.move', user_preset_dir={str(tmp_path)!r})"
    )
    assert updates == [("artist_tools", "move", "M")]


def test_assign_published_hotkey_clears_persisted_dotted_user_slot_label(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    save_user_preset(
        DraftRail(
            id="studio.tools",
            slots=(DraftSlot(id="move", label="M", action="maya.tool.move"),),
        ),
        preset_dir=tmp_path,
    )
    cmds = FakeCmds()
    previous = publish_preset_slots(
        "studio.tools",
        user_preset_dir=tmp_path,
        cmds_module=cmds,
    )[0]
    unpublish(previous, cmds_module=FakeCmds())
    cmds.hotkeys[("S", False, False, False, False, False)] = previous.name_command
    replacement = publish_slot("transform_stack", "set_key", label="Set Key", cmds_module=cmds)
    updates: list[tuple[str, str, str]] = []

    def update_slot_key_label(preset_id: str, slot_id: str, key_label: str) -> int:
        updates.append((preset_id, slot_id, key_label))
        return 1

    monkeypatch.setattr("actionrail.runtime.update_slot_key_label", update_slot_key_label)

    assign_published_hotkey(replacement, "S", overwrite=True, cmds_module=cmds)

    assert updates == [
        ("studio.tools", "move", ""),
        ("transform_stack", "set_key", "S"),
    ]


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


def test_visible_key_label_helpers_ignore_non_slot_targets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    updates: list[tuple[str, str, str]] = []

    def update_slot_key_label(preset_id: str, slot_id: str, key_label: str) -> int:
        updates.append((preset_id, slot_id, key_label))
        return 1

    monkeypatch.setattr("actionrail.runtime.update_slot_key_label", update_slot_key_label)
    action = PublishedCommand(
        "action",
        "maya.tool.move",
        "ActionRail_action_maya_tool_move",
        "ActionRail_action_maya_tool_move_NameCommand",
    )
    malformed_slot = PublishedCommand(
        "slot",
        "malformed",
        "ActionRail_slot_malformed",
        "ActionRail_slot_malformed_NameCommand",
    )

    action_binding = assign_hotkey(action.name_command, "M", cmds_module=FakeCmds())
    malformed_binding = assign_hotkey(malformed_slot.name_command, "M", cmds_module=FakeCmds())

    assert sync_visible_key_label(action, action_binding) == 0
    assert sync_visible_key_label(malformed_slot, malformed_binding) == 0
    assert clear_visible_published_key_label(action) == 0
    assert clear_visible_published_key_label(malformed_slot) == 0
    assert clear_visible_key_label("NotAnActionRailNameCommand") == 0
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


def test_sync_preset_slots_removes_stale_user_slot_command(tmp_path) -> None:
    save_user_preset(
        DraftRail(
            id="artist_tools",
            slots=(DraftSlot(id="move", label="M", action="maya.tool.move"),),
        ),
        preset_dir=tmp_path,
    )
    cmds = FakeCmds()
    stale = publish_slot("artist_tools", "removed", label="Removed", cmds_module=cmds)

    result = sync_preset_slots(
        "artist_tools",
        user_preset_dir=tmp_path,
        cmds_module=cmds,
    )

    assert stale not in result.published
    assert result.unpublished == (stale,)
    assert "ActionRail_slot_artist_tools_move" in cmds.runtime_commands
    assert stale.runtime_command not in cmds.runtime_commands


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


def test_unpublish_forgets_cached_hotkey_binding() -> None:
    cmds = FakeCmds()
    published = publish_slot("transform_stack", "set_key", label="Set Key", cmds_module=cmds)
    assign_published_hotkey(published, "S", cmds_module=cmds, sync_visible=False)

    unpublish(published, cmds_module=cmds)

    replacement = publish_slot("transform_stack", "move", label="Move", cmds_module=cmds)
    assign_published_hotkey(replacement, "S", overwrite=True, cmds_module=cmds, sync_visible=False)


def test_list_published_commands_filters_kind_and_preset() -> None:
    cmds = FakeCmds()
    action = publish_action("maya.tool.move", label="Move", cmds_module=cmds)
    set_key = publish_slot("transform_stack", "set_key", label="Set Key", cmds_module=cmds)
    rotate = publish_slot("horizontal_tools", "rotate", label="Rotate", cmds_module=cmds)
    cmds.runtime_commands["OtherTool"] = {"command": "print('external')"}

    assert list_published_commands(cmds_module=cmds) == (action, set_key, rotate)
    assert list_published_commands(target_kind="action", cmds_module=cmds) == (action,)
    assert list_published_commands(
        target_kind="slot",
        preset_id="transform_stack",
        cmds_module=cmds,
    ) == (set_key,)


def test_list_published_commands_handles_string_command_arrays() -> None:
    cmds = StringCommandArrayCmds()
    published = publish_action("maya.tool.move", label="Move", cmds_module=cmds)

    assert list_published_commands(cmds_module=cmds) == (published,)


def test_list_published_commands_skips_unreadable_or_unparseable_commands() -> None:
    broken = BrokenQueryCmds()
    broken.runtime_commands["ActionRail_action_maya_tool_move"] = {
        "command": "import actionrail; actionrail.run_action('maya.tool.move')",
    }

    empty = FakeCmds()
    empty.runtime_commands["ActionRail_action_maya_tool_move"] = {"command": ""}

    syntax = FakeCmds()
    syntax.runtime_commands["ActionRail_action_maya_tool_move"] = {"command": "not python("}

    non_actionrail = FakeCmds()
    non_actionrail.runtime_commands["ActionRail_action_maya_tool_move"] = {
        "command": "other.run_action('maya.tool.move')",
    }

    dynamic_arg = FakeCmds()
    dynamic_arg.runtime_commands["ActionRail_action_maya_tool_move"] = {
        "command": "import actionrail; actionrail.run_action(action_id)",
    }

    wrong_name = FakeCmds()
    wrong_name.runtime_commands["ActionRail_action_wrong"] = {
        "command": "import actionrail; actionrail.run_action('maya.tool.move')",
    }

    for cmds in (broken, empty, syntax, non_actionrail, dynamic_arg, wrong_name):
        assert list_published_commands(cmds_module=cmds) == ()


def test_clear_visible_key_label_ignores_unknown_persisted_names() -> None:
    assert clear_visible_key_label("ActionRail_action_maya_tool_move_NameCommand") == 0
    assert clear_visible_key_label("ActionRail_slot_missing_slot_NameCommand") == 0


def test_hotkeys_require_cmds_when_not_in_maya() -> None:
    with pytest.raises(RuntimeError, match="requires maya.cmds"):
        list_published_commands()


def test_hotkeys_import_cmds_when_available(monkeypatch) -> None:
    cmds = FakeCmds()
    published = publish_action("maya.tool.move", label="Move", cmds_module=cmds)
    maya_module = ModuleType("maya")
    monkeypatch.setitem(sys.modules, "maya", maya_module)
    monkeypatch.setitem(sys.modules, "maya.cmds", cmds)

    assert list_published_commands() == (published,)


def test_format_hotkey_includes_modifiers_in_order() -> None:
    assert format_hotkey("K", ctrl=True, alt=True, shift=True, command=True) == (
        "Ctrl+Alt+Shift+Command+K"
    )
