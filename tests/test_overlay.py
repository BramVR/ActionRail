from __future__ import annotations

import pytest

from actionrail.overlay import _anchored_position, active_model_panel


class FakeCmds:
    def __init__(
        self,
        *,
        focused: str | None = None,
        visible_panels: list[str] | None = None,
        model_panels: list[str] | None = None,
    ) -> None:
        self.focused = focused
        self.visible_panels = visible_panels or []
        self.model_panels = model_panels or []

    def getPanel(self, **kwargs: object) -> object:  # noqa: N802
        if kwargs.get("withFocus"):
            return self.focused
        if "typeOf" in kwargs:
            panel = kwargs["typeOf"]
            return "modelPanel" if panel in self.model_panels else "scriptedPanel"
        if kwargs.get("visiblePanels"):
            return self.visible_panels
        if kwargs.get("type") == "modelPanel":
            return self.model_panels
        return None


def test_anchored_position_supports_common_viewport_anchors() -> None:
    assert _anchored_position("viewport.left.center", 800, 600, 40, 196, 12) == (12, 202)
    assert _anchored_position("viewport.right.top", 800, 600, 40, 196, 12) == (748, 12)
    assert _anchored_position("viewport.bottom.center", 800, 600, 200, 40, 12) == (300, 548)


def test_active_model_panel_prefers_focused_model_panel() -> None:
    cmds = FakeCmds(
        focused="modelPanel4",
        visible_panels=["modelPanel1"],
        model_panels=["modelPanel1", "modelPanel4"],
    )

    assert active_model_panel(cmds) == "modelPanel4"


def test_active_model_panel_falls_back_to_visible_model_panel() -> None:
    cmds = FakeCmds(
        focused="outlinerPanel1",
        visible_panels=["scriptEditorPanel1", "modelPanel2"],
        model_panels=["modelPanel2", "modelPanel3"],
    )

    assert active_model_panel(cmds) == "modelPanel2"


def test_active_model_panel_falls_back_to_any_model_panel() -> None:
    cmds = FakeCmds(
        focused="outlinerPanel1",
        visible_panels=["scriptEditorPanel1"],
        model_panels=["modelPanel3"],
    )

    assert active_model_panel(cmds) == "modelPanel3"


def test_active_model_panel_raises_when_no_model_panel_exists() -> None:
    cmds = FakeCmds(focused="outlinerPanel1", visible_panels=["scriptEditorPanel1"])

    with pytest.raises(RuntimeError, match="No Maya modelPanel"):
        active_model_panel(cmds)
