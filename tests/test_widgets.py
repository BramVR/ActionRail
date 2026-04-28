from __future__ import annotations

import actionrail.widgets as widgets
from actionrail.predicates import PredicateContext
from actionrail.spec import RailLayout, StackItem, StackSpec
from actionrail.state import MayaStateSnapshot
from actionrail.widgets import (
    _button_text,
    _is_item_active,
    _is_item_visible,
    refresh_predicate_state,
)


class FakeStyle:
    def __init__(self) -> None:
        self.unpolished = 0
        self.polished = 0

    def unpolish(self, _button: object) -> None:
        self.unpolished += 1

    def polish(self, _button: object) -> None:
        self.polished += 1


class FakeButton:
    def __init__(self, slot_id: str, *, active: str = "false", enabled: bool = True) -> None:
        self.properties = {
            "actionRailSlotId": slot_id,
            "actionRailActive": active,
        }
        self.enabled = enabled
        self.style_object = FakeStyle()
        self.updated = 0

    def property(self, name: str) -> object:
        return self.properties.get(name)

    def setProperty(self, name: str, value: object) -> None:  # noqa: N802
        self.properties[name] = value

    def isEnabled(self) -> bool:  # noqa: N802
        return self.enabled

    def setEnabled(self, enabled: bool) -> None:  # noqa: N802
        self.enabled = enabled

    def style(self) -> FakeStyle:
        return self.style_object

    def update(self) -> None:
        self.updated += 1


class FakeRoot:
    def __init__(self, buttons: list[FakeButton]) -> None:
        self.buttons = buttons

    def findChildren(self, _widget_type: object) -> list[FakeButton]:  # noqa: N802
        return self.buttons


class FakeQt:
    class QtWidgets:
        QPushButton = FakeButton


def test_literal_false_visibility_skips_item_before_frame_building() -> None:
    assert _is_item_visible(StackItem(type="button", visible_when="")) is True
    assert _is_item_visible(StackItem(type="button", visible_when="true")) is True
    assert _is_item_visible(StackItem(type="button", visible_when="false")) is False


def test_state_visibility_skips_item_before_frame_building() -> None:
    item = StackItem(type="button", visible_when="selection.count > 0")

    assert _is_item_visible(item) is False
    assert (
        _is_item_visible(
            item,
            PredicateContext(state=MayaStateSnapshot(current_tool="", selection_count=1)),
        )
        is True
    )


def test_empty_active_predicate_is_inactive_by_default() -> None:
    assert _is_item_active(StackItem(type="button", active_when="")) is False
    assert _is_item_active(StackItem(type="button", active_when="true")) is True


def test_button_text_adds_key_label_on_second_line() -> None:
    assert _button_text("K", "") == "K"
    assert _button_text("K", "Ctrl+S") == "K\nCtrl+S"


def test_refresh_predicate_state_updates_enabled_and_active(
    monkeypatch,
) -> None:
    monkeypatch.setattr(widgets, "load", lambda: FakeQt)
    spec = StackSpec(
        id="refresh_test",
        layout=RailLayout(anchor="viewport.left.center"),
        items=(
            StackItem(
                type="button",
                id="refresh_test.scale",
                label="S",
                action="maya.tool.scale",
                enabled_when="selection.count > 0",
                active_when="maya.tool == scale",
            ),
        ),
    )
    button = FakeButton("refresh_test.scale", active="false", enabled=False)
    root = FakeRoot([button])

    result = refresh_predicate_state(
        root,
        spec,
        registry=object(),
        state_snapshot=MayaStateSnapshot(current_tool="scaleSuperContext", selection_count=1),
    )

    assert result.needs_rebuild is False
    assert result.refreshed == 2
    assert button.isEnabled() is True
    assert button.property("actionRailActive") == "true"
    assert button.style_object.polished == 1
    assert button.updated == 1


def test_refresh_predicate_state_requests_rebuild_when_visibility_changes(
    monkeypatch,
) -> None:
    monkeypatch.setattr(widgets, "load", lambda: FakeQt)
    spec = StackSpec(
        id="refresh_test",
        layout=RailLayout(anchor="viewport.left.center"),
        items=(
            StackItem(
                type="button",
                id="refresh_test.visible_after_select",
                label="V",
                action="maya.anim.set_key",
                visible_when="selection.count > 0",
            ),
        ),
    )
    root = FakeRoot([])

    result = refresh_predicate_state(
        root,
        spec,
        registry=object(),
        state_snapshot=MayaStateSnapshot(current_tool="", selection_count=1),
    )

    assert result.needs_rebuild is True
    assert result.visible_slot_ids == ("refresh_test.visible_after_select",)
    assert result.rendered_slot_ids == ()
