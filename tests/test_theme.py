from __future__ import annotations

from actionrail.theme import DEFAULT_THEME, ActionRailTheme, ToneStyle, generate_style_sheet
from actionrail.widgets import BUTTON_SIZE, FRAME_PADDING, FRAME_SPACING, RAIL_WIDTH, STYLE_SHEET


def test_default_theme_preserves_phase_zero_metrics() -> None:
    assert DEFAULT_THEME.button_size == 32
    assert DEFAULT_THEME.frame_padding == 4
    assert DEFAULT_THEME.frame_spacing == 2
    assert DEFAULT_THEME.rail_width == 40
    assert BUTTON_SIZE == 32
    assert FRAME_PADDING == 4
    assert FRAME_SPACING == 2
    assert RAIL_WIDTH == 40


def test_default_qss_preserves_reference_tones() -> None:
    qss = generate_style_sheet()

    assert "min-width: 32px;" in qss
    assert "background: #666670;" in qss
    assert 'QPushButton[actionRailTone="pink"]' in qss
    assert "background: #8b667f;" in qss
    assert 'QPushButton[actionRailTone="teal"]' in qss
    assert "color: #e9fffb;" in qss
    assert qss == STYLE_SHEET


def test_custom_theme_generates_metrics_and_tones() -> None:
    theme = ActionRailTheme(
        button_size=24,
        frame_padding=3,
        frame_spacing=1,
        button_background="#111111",
        tones=(
            (
                "gold",
                ToneStyle(
                    background="#aa8844",
                    border="#ccb066",
                    hover_background="#bb9955",
                    color="#fff6cc",
                ),
            ),
        ),
    )

    qss = generate_style_sheet(theme)

    assert theme.rail_width == 30
    assert "min-width: 24px;" in qss
    assert "background: #111111;" in qss
    assert 'QPushButton[actionRailTone="gold"]' in qss
    assert "border-color: #ccb066;" in qss
    assert "color: #fff6cc;" in qss
