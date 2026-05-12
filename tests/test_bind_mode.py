from __future__ import annotations

from types import SimpleNamespace

import pytest

import actionrail.runtime as runtime
from actionrail.bind_mode import (
    assign_hovered_hotkey,
    bind_mode_state,
    clear_hovered_hotkey,
    enter_bind_mode,
    exit_bind_mode,
    select_bind_mode_slot,
    toggle_bind_mode,
)
from actionrail.spec import RailLayout, StackItem, StackSpec


class FakeCmds:
    def __init__(self) -> None:
        self.runtime_commands: dict[str, dict[str, object]] = {}
        self.name_commands: dict[str, dict[str, object]] = {}
        self.hotkeys: dict[tuple[str, bool, bool, bool, bool, bool], str] = {}
        self.hotkey_sets: set[str] = {"Maya_Default"}
        self.current_hotkey_set = "Maya_Default"
        self.saved_hotkeys = 0

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

    def hotkeySet(self, name: str = "", **kwargs: object) -> object:  # noqa: N802
        if kwargs.get("query") and kwargs.get("current"):
            return self.current_hotkey_set
        if kwargs.get("query") and kwargs.get("hotkeySetArray"):
            return tuple(sorted(self.hotkey_sets))
        if kwargs.get("delete"):
            self.hotkey_sets.discard(name)
            if self.current_hotkey_set == name:
                self.current_hotkey_set = "Maya_Default"
            return None
        if kwargs.get("source") is not None:
            self.hotkey_sets.add(name)
            return name
        if kwargs.get("current"):
            self.hotkey_sets.add(name)
            self.current_hotkey_set = name
            return name
        return name

    def savePrefs(self, **kwargs: object) -> None:  # noqa: N802
        if kwargs.get("hotkeys"):
            self.saved_hotkeys += 1


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
    assert cmds.current_hotkey_set == "ActionRail"
    assert cmds.hotkeys[("F12", False, False, False, False, False)] == binding.name
    assert updates == [("transform_stack", "set_key", "F12")]

    state = exit_bind_mode(save=True, persist=True, cmds_module=cmds)
    assert state.enabled is False
    assert cmds.saved_hotkeys == 1
    assert cmds.hotkeys[("F12", False, False, False, False, False)] == binding.name


def test_bind_mode_state_refreshes_visible_overlay_affordances(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[dict[str, object]] = []

    monkeypatch.setattr(
        "actionrail.runtime.refresh_bind_mode_visuals",
        lambda **kwargs: events.append(kwargs) or 1,
    )

    enter_bind_mode()
    select_bind_mode_slot("transform_stack", "set_key")
    exit_bind_mode(save=True, cmds_module=FakeCmds())

    assert events == [
        {
            "enabled": True,
            "preset_id": "",
            "slot_id": "",
            "pending_change_count": 0,
        },
        {
            "enabled": True,
            "preset_id": "transform_stack",
            "slot_id": "set_key",
            "pending_change_count": 0,
        },
        {
            "enabled": False,
            "preset_id": "",
            "slot_id": "",
            "pending_change_count": 0,
        },
    ]


def test_assign_bind_mode_hotkey_uses_active_unsaved_preview_spec(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cmds = FakeCmds()
    updates: list[tuple[str, str, str]] = []
    spec = StackSpec(
        id="quick-blank-bar",
        layout=RailLayout(anchor="viewport.bottom.center", orientation="horizontal"),
        items=(StackItem(type="button", id="quick-blank-bar.slot_1", key_label="1"),),
    )

    monkeypatch.setitem(runtime._OVERLAYS, "quick-blank-bar", SimpleNamespace(spec=spec))
    monkeypatch.setattr(
        "actionrail.runtime.update_slot_key_label",
        lambda preset_id, slot_id, key_label: updates.append(
            (preset_id, slot_id, key_label)
        )
        or 1,
    )

    enter_bind_mode()
    select_bind_mode_slot("quick-blank-bar", "slot_1")
    binding = assign_hovered_hotkey("F11", cmds_module=cmds)

    assert binding.name == "ActionRail_slot_quick_blank_bar_slot_1_NameCommand"
    assert cmds.hotkeys[("F11", False, False, False, False, False)] == binding.name
    assert updates == [("quick-blank-bar", "slot_1", "F11")]


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

    assert cmds.current_hotkey_set == "Maya_Default"
    assert cmds.hotkeys[("F12", False, False, False, False, False)] == "ExistingCommand"
    assert updates == [
        ("transform_stack", "set_key", "F12"),
        ("transform_stack", "set_key", "S"),
    ]


def test_bind_mode_default_can_overwrite_existing_maya_chord_and_restore(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cmds = FakeCmds()
    cmds.hotkeys[("W", False, False, False, False, False)] = "MoveNameCommand"
    updates: list[tuple[str, str, str]] = []

    monkeypatch.setattr(
        "actionrail.runtime.update_slot_key_label",
        lambda preset_id, slot_id, key_label: updates.append(
            (preset_id, slot_id, key_label)
        )
        or 1,
    )

    enter_bind_mode()
    select_bind_mode_slot("transform_stack", "set_key")
    binding = assign_hovered_hotkey("W", cmds_module=cmds)

    assert binding.name == "ActionRail_slot_transform_stack_set_key_NameCommand"
    assert cmds.hotkeys[("w", False, False, False, False, False)] == binding.name
    assert updates == [("transform_stack", "set_key", "W")]

    exit_bind_mode(save=False, cmds_module=cmds)

    assert cmds.current_hotkey_set == "Maya_Default"
    assert cmds.hotkeys[("w", False, False, False, False, False)] == "MoveNameCommand"
    assert updates[-1] == ("transform_stack", "set_key", "S")


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
