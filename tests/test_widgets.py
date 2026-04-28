from __future__ import annotations

from actionrail.spec import StackItem
from actionrail.widgets import _button_text, _is_item_visible


def test_literal_false_visibility_skips_item_before_frame_building() -> None:
    assert _is_item_visible(StackItem(type="button", visible_when="")) is True
    assert _is_item_visible(StackItem(type="button", visible_when="true")) is True
    assert _is_item_visible(StackItem(type="button", visible_when="false")) is False


def test_button_text_adds_key_label_on_second_line() -> None:
    assert _button_text("K", "") == "K"
    assert _button_text("K", "Ctrl+S") == "K\nCtrl+S"
