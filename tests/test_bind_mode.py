from __future__ import annotations

import pytest

from actionrail.bind_mode import (
    assign_hovered_hotkey,
    bind_mode_state,
    clear_hovered_hotkey,
    enter_bind_mode,
    exit_bind_mode,
    select_bind_mode_slot,
    toggle_bind_mode,
)


class FakeCmds:
    def __init__(self) -> None:
        self.runtime_commands: dict[str, dict[str, object]] = {}
        self.name_commands: dict[str, dict[str, object]] = {}
        self.hotkeys: dict[tuple[str, bool, bool, bool, bool, bool], str] = {}

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
            return self.hotkeys.get(key)

        value = kwargs.get("releaseName", kwargs.get("name"))
        if value:
            self.hotkeys[key] = str(value)
        else:
            self.hotkeys.pop(key, None)
        return None


@pytest.fixture(autouse=True)
def reset_bind_mode() -> None:
    exit_bind_mode(save=False, cmds_module=FakeCmds())


def test_enter_select_assign_and_save_bind_mode_slot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cmds = FakeCmds()
    updates: list[tuple[str, str, str]] = []

    def update_slot_key_label(preset_id: str, slot_id: str, key_label: str) -> int:
        updates.append((preset_id, slot_id, key_label))
        return 1

    monkeypatch.setattr("actionrail.runtime.update_slot_key_label", update_slot_key_label)

    state = enter_bind_mode()
    assert state.enabled is True

    select_bind_mode_slot("transform_stack", "set_key")
    binding = assign_hovered_hotkey("F12", cmds_module=cmds)

    assert binding.name == "ActionRail_slot_transform_stack_set_key_NameCommand"
    assert cmds.hotkeys[("F12", False, False, False, False, False)] == binding.name
    assert updates == [("transform_stack", "set_key", "F12")]

    state = exit_bind_mode(save=True, cmds_module=cmds)
    assert state.enabled is False
    assert cmds.hotkeys[("F12", False, False, False, False, False)] == binding.name


def test_discard_bind_mode_restores_touched_hotkey_and_label(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cmds = FakeCmds()
    cmds.hotkeys[("F12", False, False, False, False, False)] = "ExistingCommand"
    updates: list[tuple[str, str, str]] = []

    def update_slot_key_label(preset_id: str, slot_id: str, key_label: str) -> int:
        updates.append((preset_id, slot_id, key_label))
        return 1

    monkeypatch.setattr("actionrail.runtime.update_slot_key_label", update_slot_key_label)

    enter_bind_mode()
    select_bind_mode_slot("transform_stack", "set_key")
    assign_hovered_hotkey("F12", overwrite=True, cmds_module=cmds)

    assert cmds.hotkeys[("F12", False, False, False, False, False)] == (
        "ActionRail_slot_transform_stack_set_key_NameCommand"
    )

    exit_bind_mode(save=False, cmds_module=cmds)

    assert cmds.hotkeys[("F12", False, False, False, False, False)] == "ExistingCommand"
    assert updates == [
        ("transform_stack", "set_key", "F12"),
        ("transform_stack", "set_key", "S"),
    ]


def test_clear_hovered_hotkey_removes_visible_slot_label(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cmds = FakeCmds()
    updates: list[tuple[str, str, str]] = []

    def update_slot_key_label(preset_id: str, slot_id: str, key_label: str) -> int:
        updates.append((preset_id, slot_id, key_label))
        return 1

    monkeypatch.setattr("actionrail.runtime.update_slot_key_label", update_slot_key_label)

    enter_bind_mode()
    select_bind_mode_slot("transform_stack", "set_key")

    assert clear_hovered_hotkey(cmds_module=cmds) is True
    assert updates == [("transform_stack", "set_key", "")]


def test_assign_requires_enabled_mode_and_selected_slot() -> None:
    with pytest.raises(RuntimeError, match="not active"):
        assign_hovered_hotkey("F12", cmds_module=FakeCmds())

    enter_bind_mode()
    with pytest.raises(RuntimeError, match="No ActionRail slot"):
        assign_hovered_hotkey("F12", cmds_module=FakeCmds())


def test_toggle_bind_mode_switches_state() -> None:
    assert bind_mode_state().enabled is False
    assert toggle_bind_mode().enabled is True
    assert toggle_bind_mode().enabled is False
