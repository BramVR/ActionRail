"""Theme tokens and QSS generation for ActionRail widgets."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any


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
    cluster_background_enabled: bool = True
    cluster_base_rgb: tuple[int, int, int] = (29, 32, 42)
    cluster_base_opacity: float = 1.0
    cluster_pattern: str = "diagonal_stripes"
    cluster_stripe_rgb: tuple[int, int, int] = (45, 47, 60)
    cluster_stripe_opacity: float = 1.0
    cluster_pattern_scale: float = 1.0
    cluster_background: str = (
        "qlineargradient(spread:repeat, x1:0, y1:0, x2:0.045, y2:0.045, "
        "stop:0 rgb(29, 32, 42), "
        "stop:0.35 rgb(29, 32, 42), "
        "stop:0.35 rgb(45, 47, 60), "
        "stop:0.65 rgb(45, 47, 60), "
        "stop:0.65 rgb(29, 32, 42), "
        "stop:1 rgb(29, 32, 42))"
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
    spell_icon_background: str = "#444341"
    spell_icon_border: str = "#171716"
    spell_icon_inset: int = 3
    text_muted: str = "#8c9aa1"
    accent: str = "#8ccf3f"
    accent_hover: str = "#a6e45b"
    accent_line: str = "#8ccf3f"
    bind_mode_border: str = "#8ccf3f"
    bind_mode_background: str = "#1f3118"
    bind_mode_hover_border: str = "#a6e45b"
    bind_mode_hover_background: str = "#29401f"
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


def apply_appearance_overrides(
    theme: ActionRailTheme,
    appearance: Any | None,
) -> ActionRailTheme:
    """Resolve persisted bar appearance overrides onto theme tokens."""

    if appearance is None:
        return theme

    updates: dict[str, object] = {}
    accent = _string_attr(appearance, "accent")
    text = _string_attr(appearance, "text")
    muted_text = _string_attr(appearance, "muted_text")
    background = getattr(appearance, "background", None)
    border = getattr(appearance, "border", None)
    slots = getattr(appearance, "slots", None)

    if accent:
        updates.update(
            {
                "accent": accent,
                "accent_line": accent,
                "button_active_border": accent,
                "button_active_background": _mix_hex(accent, "#000000", 0.28),
                "button_active_hover_background": _mix_hex(accent, "#000000", 0.40),
                "bind_mode_border": accent,
                "bind_mode_background": _mix_hex(accent, "#000000", 0.20),
                "bind_mode_hover_border": _mix_hex(accent, "#ffffff", 0.78),
                "bind_mode_hover_background": _mix_hex(accent, "#000000", 0.32),
            }
        )
    if text:
        updates["button_color"] = text
    if muted_text:
        updates["text_muted"] = muted_text

    if background is not None:
        updates["cluster_background_enabled"] = bool(
            getattr(background, "enabled", theme.cluster_background_enabled)
        )
        base_rgb = _rgb_from_color(_string_attr(background, "color"))
        if base_rgb is not None:
            updates["cluster_base_rgb"] = base_rgb
        updates["cluster_pattern"] = getattr(background, "pattern", theme.cluster_pattern)
        stripe_rgb = _rgb_from_color(_string_attr(background, "pattern_color"))
        if stripe_rgb is not None:
            updates["cluster_stripe_rgb"] = stripe_rgb
        updates["cluster_stripe_opacity"] = float(
            getattr(background, "pattern_opacity", theme.cluster_stripe_opacity)
        )
        updates["cluster_pattern_scale"] = float(
            getattr(background, "pattern_scale", theme.cluster_pattern_scale)
        )

    if border is not None:
        if not bool(getattr(border, "enabled", True)):
            updates["cluster_border_width"] = 0
        elif border.width is not None:
            updates["cluster_border_width"] = int(border.width)
        border_color = _string_attr(border, "color")
        if border_color:
            updates["cluster_border"] = border_color

    if slots is not None:
        slot_text = _string_attr(slots, "text")
        if slot_text:
            updates["button_color"] = slot_text
        slot_active = _string_attr(slots, "active")
        if slot_active:
            updates.update(
                {
                    "button_active_border": slot_active,
                    "button_active_background": _mix_hex(slot_active, "#000000", 0.28),
                    "button_active_hover_background": _mix_hex(slot_active, "#000000", 0.40),
                }
            )
        _copy_string_attr(updates, slots, "empty_background", "button_background")
        _copy_string_attr(updates, slots, "empty_border", "button_border")
        _copy_string_attr(updates, slots, "icon_backplate", "spell_icon_background")
        _copy_string_attr(updates, slots, "icon_border", "spell_icon_border")

    if not updates:
        return theme
    resolved = replace(theme, **updates)
    return replace(resolved, cluster_background=_cluster_background_qss(resolved))


def generate_style_sheet(theme: ActionRailTheme = DEFAULT_THEME) -> str:
    """Generate Qt style sheet text from ActionRail theme tokens."""

    qss = f"""
QWidget#ActionRailRoot {{
    background: {theme.root_background};
}}
QFrame[actionRailRole="cluster"] {{
    background: transparent;
    border: none;
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
QPushButton[actionRailRole="button"][actionRailBindMode="true"] {{
    background: {theme.bind_mode_background};
    border-color: {theme.bind_mode_border};
}}
QPushButton[actionRailRole="button"][actionRailBindMode="true"]:hover {{
    background: {theme.bind_mode_hover_background};
    border-color: {theme.bind_mode_hover_border};
}}
QPushButton[actionRailRole="button"][actionRailBindMode="true"]:disabled {{
    background: {theme.bind_mode_background};
    border-color: {theme.bind_mode_border};
    color: {theme.button_color};
}}
QPushButton[actionRailRole="button"][actionRailBindHovered="true"] {{
    background: {theme.bind_mode_hover_background};
    border-color: {theme.bind_mode_hover_border};
}}
QPushButton[actionRailRole="button"][actionRailBindHovered="true"]:disabled {{
    background: {theme.bind_mode_hover_background};
    border-color: {theme.bind_mode_hover_border};
    color: {theme.button_color};
}}
"""

    return qss


def _copy_string_attr(
    updates: dict[str, object],
    source: object,
    source_name: str,
    target_name: str,
) -> None:
    value = _string_attr(source, source_name)
    if value:
        updates[target_name] = value


def _string_attr(source: object, name: str) -> str:
    value = getattr(source, name, "")
    return value if isinstance(value, str) else ""


def _cluster_background_qss(theme: ActionRailTheme) -> str:
    base = _rgb_qss(theme.cluster_base_rgb, theme.cluster_base_opacity)
    if not theme.cluster_background_enabled:
        return "transparent"
    if theme.cluster_pattern != "diagonal_stripes":
        return base
    stripe = _rgb_qss(theme.cluster_stripe_rgb, theme.cluster_stripe_opacity)
    return (
        "qlineargradient(spread:repeat, x1:0, y1:0, x2:0.045, y2:0.045, "
        f"stop:0 {base}, "
        f"stop:0.35 {base}, "
        f"stop:0.35 {stripe}, "
        f"stop:0.65 {stripe}, "
        f"stop:0.65 {base}, "
        f"stop:1 {base})"
    )


def _rgb_qss(rgb: tuple[int, int, int], opacity: float = 1.0) -> str:
    red, green, blue = rgb
    if opacity >= 1.0:
        return f"rgb({red}, {green}, {blue})"
    alpha = max(0, min(255, round(opacity * 255)))
    return f"rgba({red}, {green}, {blue}, {alpha})"


def _rgb_from_color(color: str) -> tuple[int, int, int] | None:
    color = color.strip()
    if len(color) == 7 and color.startswith("#"):
        try:
            return (
                int(color[1:3], 16),
                int(color[3:5], 16),
                int(color[5:7], 16),
            )
        except ValueError:
            return None
    if color.startswith("rgb(") and color.endswith(")"):
        parts = [part.strip() for part in color[4:-1].split(",")]
        if len(parts) != 3:
            return None
        try:
            values = tuple(int(part) for part in parts)
        except ValueError:
            return None
        if all(0 <= value <= 255 for value in values):
            return values
    return None


def _mix_hex(color: str, other: str, weight: float) -> str:
    first = _rgb_from_color(color)
    second = _rgb_from_color(other)
    if first is None or second is None:
        return color
    weight = max(0.0, min(1.0, weight))
    mixed = tuple(
        round((component * weight) + (other_component * (1.0 - weight)))
        for component, other_component in zip(first, second, strict=True)
    )
    return "#{:02x}{:02x}{:02x}".format(*mixed)
