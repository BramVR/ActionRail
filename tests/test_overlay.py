from __future__ import annotations

from actionrail.overlay import _anchored_position


def test_anchored_position_supports_common_viewport_anchors() -> None:
    assert _anchored_position("viewport.left.center", 800, 600, 40, 196, 12) == (12, 202)
    assert _anchored_position("viewport.right.top", 800, 600, 40, 196, 12) == (748, 12)
    assert _anchored_position("viewport.bottom.center", 800, 600, 200, 40, 12) == (300, 548)
