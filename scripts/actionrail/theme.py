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
    cluster_background: str = "#4a4a4f"
    cluster_border: str = "#323238"
    cluster_border_width: int = 2
    cluster_border_radius: int = 2
    button_border_width: int = 1
    button_border_radius: int = 1
    button_background: str = "#666670"
    button_border: str = "#696972"
    button_color: str = "#d9d9de"
    button_hover_background: str = "#74747e"
    button_hover_border: str = "#888894"
    button_pressed_background: str = "#555560"
    button_active_border: str = "#a9839e"
    button_active_background: str = "#8b667f"
    button_active_hover_background: str = "#9c7390"
    button_disabled_background: str = "#54545b"
    button_disabled_border: str = "#5d5d65"
    button_disabled_color: str = "#8e8e98"
    button_font_size: int = 13
    button_font_weight: int = 700
    tones: tuple[tuple[str, ToneStyle], ...] = (
        ("pink", ToneStyle(background="#8b667f", border="#a9839e", hover_background="#9c7390")),
        (
            "teal",
            ToneStyle(
                background="#22a79b",
                border="#45c6bb",
                hover_background="#29b9ad",
                color="#e9fffb",
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
    border-color: #f0c45c;
}}
QPushButton[actionRailRole="button"][actionRailDiagnosticSeverity="error"] {{
    background: #724c52;
    border-color: #f06f78;
    color: #fff1f2;
}}
"""

    return qss
