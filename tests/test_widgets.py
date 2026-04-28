from __future__ import annotations

from actionrail.predicates import PredicateContext
from actionrail.spec import StackItem
from actionrail.state import MayaStateSnapshot
from actionrail.widgets import _button_text, _is_item_active, _is_item_visible


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
