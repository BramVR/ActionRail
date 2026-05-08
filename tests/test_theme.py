from __future__ import annotations

from actionrail.spec import RailAppearance, RailBackground, RailBorder, RailSlotAppearance
from actionrail.theme import (
    DEFAULT_THEME,
    ActionRailTheme,
    ToneStyle,
    apply_appearance_overrides,
    generate_style_sheet,
)
from actionrail.widgets import (
    BUTTON_OUTER_SIZE,
    BUTTON_SIZE,
    FRAME_PADDING,
    FRAME_SPACING,
    RAIL_WIDTH,
    STYLE_SHEET,
)


def test_default_theme_accounts_for_styled_borders() -> None:
    assert DEFAULT_THEME.button_size == 32
    assert DEFAULT_THEME.button_outer_size == 34
    assert DEFAULT_THEME.frame_padding == 4
    assert DEFAULT_THEME.frame_spacing == 2
    assert DEFAULT_THEME.rail_width == 46
    assert BUTTON_SIZE == 32
    assert BUTTON_OUTER_SIZE == 34
    assert FRAME_PADDING == 4
    assert FRAME_SPACING == 2
    assert RAIL_WIDTH == 46


def test_default_qss_preserves_reference_tones() -> None:
    qss = generate_style_sheet()

    assert "min-width: 32px;" in qss
    assert 'QFrame[actionRailRole="cluster"]' in qss
    assert "background: transparent;" in qss
    assert "border: none;" in qss
    assert DEFAULT_THEME.cluster_base_rgb == (29, 32, 42)
    assert DEFAULT_THEME.cluster_stripe_rgb == (45, 47, 60)
    assert "stop:0 rgb(29, 32, 42)" in DEFAULT_THEME.cluster_background
    assert "stop:0.35 rgb(45, 47, 60)" in DEFAULT_THEME.cluster_background
    assert "stop:0.65 rgb(45, 47, 60)" in DEFAULT_THEME.cluster_background
    assert (
        "qlineargradient(spread:repeat, x1:0, y1:0, x2:0.009, y2:0.009"
        in DEFAULT_THEME.panel_profile_background
    )
    assert "stop:0.26 rgba(18, 23, 25, 102)" in DEFAULT_THEME.panel_profile_background
    assert "stop:0.5 rgba(46, 55, 58, 102)" in DEFAULT_THEME.panel_profile_background
    assert "stop:0.74 rgba(18, 23, 25, 102)" in DEFAULT_THEME.panel_profile_background
    assert DEFAULT_THEME.spell_icon_background == "#444341"
    assert DEFAULT_THEME.spell_icon_border == "#171716"
    assert DEFAULT_THEME.spell_icon_inset == 3
    assert "border-top-color: #8ccf3f;" not in qss
    assert "background: #101315;" in qss
    assert 'QPushButton[actionRailRole="button"][actionRailActive="true"]' in qss
    assert 'QPushButton[actionRailRole="button"]:disabled' in qss
    assert 'QPushButton[actionRailRole="button"][actionRailLocked="true"]' in qss
    assert "background: #0d1011;" in qss
    assert qss.index('[actionRailTone="pink"]') < qss.index('[actionRailActive="true"]')
    assert 'QPushButton[actionRailTone="pink"]' in qss
    assert "background: #5a2439;" in qss
    assert "background: #71304a;" in qss
    assert "color: #8c9aa1;" in qss
    assert 'QPushButton[actionRailTone="teal"]' in qss
    assert "color: #d7dde0;" in qss
    assert 'QPushButton[actionRailTone="gold"]' in qss
    assert "border-color: #ffb200;" in qss
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

    assert theme.button_outer_size == 26
    assert theme.rail_width == 36
    assert "min-width: 24px;" in qss
    assert "background: #111111;" in qss
    assert 'QPushButton[actionRailTone="gold"]' in qss
    assert "border-color: #ccb066;" in qss
    assert "color: #fff6cc;" in qss


def test_appearance_overrides_resolve_to_theme_tokens() -> None:
    theme = apply_appearance_overrides(
        DEFAULT_THEME,
        RailAppearance(
            accent="#33dd88",
            text="#eeeeee",
            muted_text="#888888",
            background=RailBackground(
                color="#111722",
                pattern="none",
                pattern_color="#263044",
                pattern_opacity=0.5,
                pattern_scale=1.5,
            ),
            border=RailBorder(color="#020304", width=3),
            slots=RailSlotAppearance(
                empty_background="#101315",
                empty_border="#020303",
                icon_backplate="#444341",
                icon_border="#171716",
                active="#44ffaa",
                text="#f8f8f8",
            ),
        ),
    )

    assert theme.accent == "#33dd88"
    assert theme.button_color == "#f8f8f8"
    assert theme.text_muted == "#888888"
    assert theme.cluster_base_rgb == (17, 23, 34)
    assert theme.cluster_pattern == "none"
    assert theme.cluster_stripe_rgb == (38, 48, 68)
    assert theme.cluster_stripe_opacity == 0.5
    assert theme.cluster_pattern_scale == 1.5
    assert theme.cluster_background == "rgb(17, 23, 34)"
    assert theme.cluster_border == "#020304"
    assert theme.cluster_border_width == 3
    assert theme.button_background == "#101315"
    assert theme.button_border == "#020303"
    assert theme.spell_icon_background == "#444341"
    assert theme.spell_icon_border == "#171716"
    assert theme.button_active_border == "#44ffaa"
    assert theme.button_active_background == "#134730"


def test_appearance_can_disable_background_and_border() -> None:
    theme = apply_appearance_overrides(
        DEFAULT_THEME,
        RailAppearance(
            background=RailBackground(enabled=False),
            border=RailBorder(enabled=False),
        ),
    )

    assert theme.cluster_background_enabled is False
    assert theme.cluster_background == "transparent"
    assert theme.cluster_border_width == 0
