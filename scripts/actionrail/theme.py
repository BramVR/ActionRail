"""Theme tokens and QSS generation for ActionRail widgets."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ToneStyle:
    """Button colors for a named ActionRail tone."""

    background: str
    border: str
    hover_background: str
    color: str | None = None


@dataclass(frozen=True)
class ActionRailTheme:
    """Resolved visual tokens used by the Qt widget builder."""

    button_size: int = 32
    frame_padding: int = 4
    frame_spacing: int = 2
    root_background: str = "transparent"
    cluster_background: str = (
        "qlineargradient(spread:repeat, x1:0, y1:0, x2:0.045, y2:0.045, "
        "stop:0 rgba(37, 45, 52, 102), "
        "stop:0.34 rgba(37, 45, 52, 102), "
        "stop:0.5 rgba(59, 70, 80, 102), "
        "stop:0.66 rgba(37, 45, 52, 102), "
        "stop:1 rgba(37, 45, 52, 102))"
    )
    cluster_border: str = "#030404"
    cluster_border_width: int = 2
    cluster_border_radius: int = 2
    button_border_width: int = 1
    button_border_radius: int = 1
    button_background: str = "#101315"
    button_border: str = "#020303"
    button_color: str = "#d7dde0"
    button_hover_background: str = "#1a2022"
    button_hover_border: str = "#2b3437"
    button_pressed_background: str = "#090b0c"
    button_active_border: str = "#8ccf3f"
    button_active_background: str = "#17301c"
    button_active_hover_background: str = "#214425"
    button_disabled_background: str = "#101315"
    button_disabled_border: str = "#20272a"
    button_disabled_color: str = "#6f7a80"
    button_font_size: int = 13
    button_font_weight: int = 700
    panel_background: str = "rgba(32, 34, 34, 230)"
    panel_surface_background: str = "rgba(14, 19, 20, 205)"
    panel_inset_background: str = "rgba(20, 25, 27, 195)"
    panel_raised_background: str = "rgba(27, 33, 35, 195)"
    panel_profile_background: str = (
        "qlineargradient(spread:repeat, x1:0, y1:0, x2:0.009, y2:0.009, "
        "stop:0 rgba(18, 23, 25, 102), "
        "stop:0.26 rgba(18, 23, 25, 102), "
        "stop:0.5 rgba(46, 55, 58, 102), "
        "stop:0.74 rgba(18, 23, 25, 102), "
        "stop:1 rgba(18, 23, 25, 102))"
    )
    text_muted: str = "#8c9aa1"
    accent: str = "#8ccf3f"
    accent_hover: str = "#a6e45b"
    accent_line: str = "#8ccf3f"
    success: str = "#2dff87"
    warning: str = "#ffb200"
    error: str = "#ff5a64"
    tones: tuple[tuple[str, ToneStyle], ...] = (
        ("pink", ToneStyle(background="#5a2439", border="#a6456b", hover_background="#71304a")),
        (
            "teal",
            ToneStyle(
                background="#121719",
                border="#2b3437",
                hover_background="#1a2022",
                color="#d7dde0",
            ),
        ),
        (
            "gold",
            ToneStyle(
                background="#6e4c0d",
                border="#ffb200",
                hover_background="#805b13",
                color="#fff1c7",
            ),
        ),
    )

    @property
    def button_outer_size(self) -> int:
        """Total rendered button size including the QSS border."""

        return self.button_size + (self.button_border_width * 2)

    @property
    def slot_extent(self) -> int:
        """Total extent of a single framed slot including borders and padding."""

        return self.button_outer_size + ((self.frame_padding + self.cluster_border_width) * 2)

    @property
    def rail_width(self) -> int:
        """Cross-axis extent of a single ActionRail column or row."""

        return self.slot_extent


DEFAULT_THEME = ActionRailTheme()


def generate_style_sheet(theme: ActionRailTheme = DEFAULT_THEME) -> str:
    """Generate Qt style sheet text from ActionRail theme tokens."""

    qss = f"""
QWidget#ActionRailRoot {{
    background: {theme.root_background};
}}
QFrame[actionRailRole="cluster"] {{
    background: {theme.cluster_background};
    border: {theme.cluster_border_width}px solid {theme.cluster_border};
    border-radius: {theme.cluster_border_radius}px;
}}
QPushButton[actionRailRole="button"] {{
    min-width: {theme.button_size}px;
    max-width: {theme.button_size}px;
    min-height: {theme.button_size}px;
    max-height: {theme.button_size}px;
    border: {theme.button_border_width}px solid {theme.button_border};
    border-radius: {theme.button_border_radius}px;
    background: {theme.button_background};
    color: {theme.button_color};
    font-size: {theme.button_font_size}px;
    font-weight: {theme.button_font_weight};
    letter-spacing: 0px;
    padding: 0px;
}}
QPushButton[actionRailRole="button"]:hover {{
    background: {theme.button_hover_background};
    border-color: {theme.button_hover_border};
}}
QPushButton[actionRailRole="button"]:pressed {{
    background: {theme.button_pressed_background};
}}
QPushButton[actionRailRole="button"]:disabled {{
    background: {theme.button_disabled_background};
    border-color: {theme.button_disabled_border};
    color: {theme.button_disabled_color};
}}
QPushButton[actionRailRole="button"][actionRailLocked="true"] {{
    background: #0d1011;
    border-color: #1c2326;
    color: {theme.text_muted};
}}
QPushButton[actionRailRole="button"][actionRailLocked="true"]:hover {{
    background: #121719;
    border-color: #2a3337;
}}
QPushButton[actionRailRole="button"][actionRailLocked="true"]:disabled {{
    background: #0d1011;
    border-color: #1c2326;
    color: {theme.text_muted};
}}
QPushButton[actionRailRole="collapsedHandle"] {{
    border: {theme.button_border_width}px solid {theme.button_hover_border};
    border-radius: {theme.button_border_radius}px;
    background: {theme.cluster_background};
    color: {theme.button_color};
    font-size: 11px;
    font-weight: {theme.button_font_weight};
    letter-spacing: 0px;
    padding: 0px;
}}
QPushButton[actionRailRole="collapsedHandle"]:hover {{
    background: {theme.button_hover_background};
    border-color: {theme.button_active_border};
}}
"""

    for tone_name, tone in theme.tones:
        color_rule = f"\n    color: {tone.color};" if tone.color else ""
        qss += f"""QPushButton[actionRailTone="{tone_name}"] {{
    background: {tone.background};
    border-color: {tone.border};{color_rule}
}}
QPushButton[actionRailTone="{tone_name}"]:hover {{
    background: {tone.hover_background};
}}
"""

    qss += f"""QPushButton[actionRailRole="button"][actionRailActive="true"] {{
    background: {theme.button_active_background};
    border-color: {theme.button_active_border};
}}
QPushButton[actionRailRole="button"][actionRailActive="true"]:hover {{
    background: {theme.button_active_hover_background};
}}
QPushButton[actionRailRole="button"][actionRailDiagnosticSeverity="warning"] {{
    border-color: {theme.warning};
}}
QPushButton[actionRailRole="button"][actionRailDiagnosticSeverity="error"] {{
    background: #4b171c;
    border-color: {theme.error};
    color: #fff1f2;
}}
"""

    return qss
