from __future__ import annotations

from actionrail.spec import StackItem
from actionrail.widgets import _is_item_visible


def test_literal_false_visibility_skips_item_before_frame_building() -> None:
    assert _is_item_visible(StackItem(type="button", visible_when="")) is True
    assert _is_item_visible(StackItem(type="button", visible_when="true")) is True
    assert _is_item_visible(StackItem(type="button", visible_when="false")) is False
