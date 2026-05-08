"""Dockable Quick Create Qt panel for ActionRail."""

from __future__ import annotations

from math import ceil
from pathlib import Path
from typing import Any

from .authoring import DraftRail, build_draft_spec
from .hotkeys import slot_binding_targets
from .overlay import maya_main_window
from .qt import QtBinding, load
from .quick_create import (
    ANCHOR_CHOICES,
    QuickCreateDraftInput,
    QuickCreateSlotInput,
    _slot_input_from_item,
    active_quick_create_preview_spec,
    build_quick_create_draft,
    clear_quick_create_previews,
    edit_quick_create_layout,
    load_quick_create_preset,
    make_default_input,
    save_quick_create_preset,
    set_quick_create_slots_unlocked,
    template_choices,
)
from .spec import (
    MAX_LAYOUT_COLUMNS,
    MAX_LAYOUT_OFFSET,
    MAX_LAYOUT_SCALE,
    RailAppearance,
    RailBackground,
    RailBorder,
    RailSlotAppearance,
)
from .theme import DEFAULT_THEME

PANEL_OBJECT_NAME = "ActionRailQuickCreatePanel"
STATUS_OBJECT_NAME = "ActionRailQuickCreateStatus"
TEMPLATE_COMBO_OBJECT_NAME = "ActionRailQuickCreateTemplateCombo"
TABS_OBJECT_NAME = "ActionRailQuickCreateTabs"
PREVIEW_BUTTON_OBJECT_NAME = "ActionRailQuickCreatePreviewButton"
CLEAR_PREVIEW_BUTTON_OBJECT_NAME = "ActionRailQuickCreateClearPreviewButton"
SAVE_BUTTON_OBJECT_NAME = "ActionRailQuickCreateSaveButton"
PUBLISH_BUTTON_OBJECT_NAME = "ActionRailQuickCreatePublishButton"
LOAD_BUTTON_OBJECT_NAME = "ActionRailQuickCreateLoadButton"
OVERWRITE_BUTTON_OBJECT_NAME = "ActionRailQuickCreateOverwriteButton"
EDIT_LAYOUT_BUTTON_OBJECT_NAME = "ActionRailQuickCreateEditLayoutButton"
EDIT_SLOTS_BUTTON_OBJECT_NAME = "ActionRailQuickCreateEditSlotsButton"
SLOT_LOCK_BUTTON_OBJECT_NAME = EDIT_SLOTS_BUTTON_OBJECT_NAME
BUTTON_COUNT_OBJECT_NAME = "ActionRailQuickCreateButtonCount"
BUTTONS_PER_ROW_OBJECT_NAME = "ActionRailQuickCreateButtonsPerRow"
BUTTON_SIZE_OBJECT_NAME = "ActionRailQuickCreateButtonSize"
BINDINGS_TABLE_OBJECT_NAME = "ActionRailQuickCreateBindingsTable"
APPEARANCE_ACCENT_OBJECT_NAME = "ActionRailQuickCreateAppearanceAccent"
APPEARANCE_BACKGROUND_COLOR_OBJECT_NAME = "ActionRailQuickCreateAppearanceBackgroundColor"
APPEARANCE_BORDER_WIDTH_OBJECT_NAME = "ActionRailQuickCreateAppearanceBorderWidth"
APPEARANCE_ACTIVE_COLOR_OBJECT_NAME = "ActionRailQuickCreateAppearanceActiveColor"

_PANEL: Any | None = None
_SLOT_COLUMNS = (
    ("Id", 96),
    ("Label", 160),
    ("Key", 64),
)
_BINDING_COLUMNS = (
    "Slot",
    "Key",
    "Maya Hotkey Name",
)

__all__ = [
    "PANEL_OBJECT_NAME",
    "CLEAR_PREVIEW_BUTTON_OBJECT_NAME",
    "EDIT_LAYOUT_BUTTON_OBJECT_NAME",
    "EDIT_SLOTS_BUTTON_OBJECT_NAME",
    "SLOT_LOCK_BUTTON_OBJECT_NAME",
    "LOAD_BUTTON_OBJECT_NAME",
    "OVERWRITE_BUTTON_OBJECT_NAME",
    "PREVIEW_BUTTON_OBJECT_NAME",
    "PUBLISH_BUTTON_OBJECT_NAME",
    "SAVE_BUTTON_OBJECT_NAME",
    "STATUS_OBJECT_NAME",
    "TABS_OBJECT_NAME",
    "TEMPLATE_COMBO_OBJECT_NAME",
    "BUTTON_COUNT_OBJECT_NAME",
    "BINDINGS_TABLE_OBJECT_NAME",
    "BUTTON_SIZE_OBJECT_NAME",
    "BUTTONS_PER_ROW_OBJECT_NAME",
    "APPEARANCE_ACCENT_OBJECT_NAME",
    "APPEARANCE_ACTIVE_COLOR_OBJECT_NAME",
    "APPEARANCE_BACKGROUND_COLOR_OBJECT_NAME",
    "APPEARANCE_BORDER_WIDTH_OBJECT_NAME",
    "show_quick_create_panel",
]


def show_quick_create_panel(  # pragma: no cover - Maya-hosted Qt panel.
    *,
    qt_binding: QtBinding | None = None,
    parent: Any | None = None,
    user_preset_dir: str | Path | None = None,
) -> Any:
    """Show the dockable Quick Create panel widget and return it."""

    global _PANEL

    qt = qt_binding or load()
    app = qt.QtWidgets.QApplication.instance()
    if app is None:
        msg = "ActionRail Quick Create requires a QApplication inside Maya."
        raise RuntimeError(msg)

    if _PANEL is not None:
        _close_existing_panel(qt)

    panel_parent = parent if parent is not None else maya_main_window(qt)
    panel = qt.QtWidgets.QWidget(panel_parent)
    panel.setObjectName(PANEL_OBJECT_NAME)
    panel.setWindowTitle("ActionRail Quick Create")
    panel.setMinimumSize(860, 640)
    panel.resize(900, 680)
    panel.setAttribute(qt.QtCore.Qt.WA_DeleteOnClose, True)
    if panel_parent is None:
        panel.setWindowFlags(qt.QtCore.Qt.Tool)
    else:
        _sync_to_parent_size(panel, panel_parent)
        _install_parent_resize_filter(qt, panel, panel_parent)

    panel._actionrail_user_preset_dir = user_preset_dir
    _build_panel(panel, qt, user_preset_dir=user_preset_dir)
    panel.destroyed.connect(_forget_panel)
    _PANEL = panel
    panel.show()
    panel.raise_()
    panel.activateWindow()
    return panel


def _install_parent_resize_filter(
    qt: QtBinding,
    panel: Any,
    panel_parent: Any,
) -> None:  # pragma: no cover - Maya-hosted Qt resize behavior.
    class ParentResizeFilter(qt.QtCore.QObject):  # type: ignore[misc, valid-type]
        def eventFilter(self, watched: Any, event: Any) -> bool:  # noqa: N802
            event_type = event.type()
            if event_type in (
                qt.QtCore.QEvent.Resize,
                qt.QtCore.QEvent.Show,
                qt.QtCore.QEvent.LayoutRequest,
            ):
                _sync_to_parent_size(panel, watched)
            return False

    resize_filter = ParentResizeFilter(panel)
    panel_parent.installEventFilter(resize_filter)
    panel._actionrail_parent_resize_filter = resize_filter


def _sync_to_parent_size(panel: Any, panel_parent: Any) -> None:
    rect = panel_parent.rect()
    panel.setGeometry(rect)


def _build_panel(
    panel: Any,
    qt: QtBinding,
    *,
    user_preset_dir: str | Path | None = None,
) -> None:  # pragma: no cover
    panel.setStyleSheet(_style_sheet())
    templates = template_choices()

    root = qt.QtWidgets.QVBoxLayout(panel)
    root.setContentsMargins(12, 10, 12, 12)
    root.setSpacing(8)

    title = qt.QtWidgets.QLabel("ActionRail")
    title.setObjectName("ActionRailQuickCreateTitle")
    root.addWidget(title)

    utility_row = qt.QtWidgets.QHBoxLayout()
    utility_row.setContentsMargins(0, 0, 0, 0)
    utility_row.setSpacing(6)
    root.addLayout(utility_row)
    reset_values = qt.QtWidgets.QPushButton("Reset Values")
    validate_top = qt.QtWidgets.QPushButton("Validate Draft")
    for button in (reset_values, validate_top):
        button.setProperty("actionRailRole", "utilityButton")
        utility_row.addWidget(button)
    utility_row.addStretch(1)

    body = qt.QtWidgets.QHBoxLayout()
    body.setContentsMargins(0, 0, 0, 0)
    body.setSpacing(10)
    root.addLayout(body, 1)

    nav = qt.QtWidgets.QFrame()
    nav.setObjectName("ActionRailQuickCreateSidebar")
    nav.setFixedWidth(180)
    nav_layout = qt.QtWidgets.QVBoxLayout(nav)
    nav_layout.setContentsMargins(10, 10, 10, 10)
    nav_layout.setSpacing(8)
    nav_title = qt.QtWidgets.QLabel("ActionBars")
    nav_title.setObjectName("ActionRailQuickCreateNavTitle")
    nav_layout.addWidget(nav_title)
    template_list = qt.QtWidgets.QListWidget()
    template_list.setObjectName("ActionRailQuickCreateTemplateList")
    for template in templates:
        template_list.addItem(template.label)
    nav_layout.addWidget(template_list, 1)
    body.addWidget(nav)

    content = qt.QtWidgets.QFrame()
    content.setObjectName("ActionRailQuickCreateContent")
    content_layout = qt.QtWidgets.QVBoxLayout(content)
    content_layout.setContentsMargins(10, 10, 10, 10)
    content_layout.setSpacing(8)
    body.addWidget(content, 1)

    preset_id = qt.QtWidgets.QLineEdit(make_default_input().preset_id)
    preset_id.setObjectName("ActionRailQuickCreatePresetId")
    template_combo = qt.QtWidgets.QComboBox()
    template_combo.setObjectName(TEMPLATE_COMBO_OBJECT_NAME)
    template_combo.addItems(tuple(template.label for template in templates))

    anchor_combo = qt.QtWidgets.QComboBox()
    anchor_combo.setObjectName("ActionRailQuickCreateAnchor")
    anchor_combo.addItems(ANCHOR_CHOICES)
    orientation_combo = qt.QtWidgets.QComboBox()
    orientation_combo.setObjectName("ActionRailQuickCreateOrientation")
    orientation_combo.addItems(("vertical", "horizontal"))
    button_count = _spin_box(qt, 1, MAX_LAYOUT_COLUMNS, 1)
    button_count.setObjectName(BUTTON_COUNT_OBJECT_NAME)
    buttons_per_row = _spin_box(qt, 1, MAX_LAYOUT_COLUMNS, 1)
    buttons_per_row.setObjectName(BUTTONS_PER_ROW_OBJECT_NAME)
    offset_x = _spin_box(qt, -MAX_LAYOUT_OFFSET, MAX_LAYOUT_OFFSET, 0)
    offset_y = _spin_box(qt, -MAX_LAYOUT_OFFSET, MAX_LAYOUT_OFFSET, 0)
    scale = _double_spin_box(qt, 0.1, MAX_LAYOUT_SCALE, 1.0, 0.05)
    scale.setObjectName(BUTTON_SIZE_OBJECT_NAME)
    opacity = _double_spin_box(qt, 0.0, 1.0, 1.0, 0.05)
    locked = qt.QtWidgets.QCheckBox()
    collapse_enabled = qt.QtWidgets.QCheckBox()
    collapse_edge = qt.QtWidgets.QComboBox()
    collapse_edge.addItems(("left", "right", "top", "bottom"))
    collapse_handle_icon = qt.QtWidgets.QLineEdit()
    collapse_trigger = qt.QtWidgets.QComboBox()
    collapse_trigger.addItems(("click", "hover"))
    collapse_default = qt.QtWidgets.QCheckBox()
    appearance_theme = qt.QtWidgets.QComboBox()
    appearance_theme.setEditable(True)
    appearance_theme.addItems(("default",))
    inherit_global = qt.QtWidgets.QCheckBox()
    accent_color = _color_line_edit(qt, "#8ccf3f")
    accent_color.setObjectName(APPEARANCE_ACCENT_OBJECT_NAME)
    text_color = _color_line_edit(qt, "")
    muted_text_color = _color_line_edit(qt, "")
    background_enabled = qt.QtWidgets.QCheckBox()
    background_color = _color_line_edit(qt, "#1d202a")
    background_color.setObjectName(APPEARANCE_BACKGROUND_COLOR_OBJECT_NAME)
    background_pattern = qt.QtWidgets.QComboBox()
    background_pattern.addItems(("diagonal_stripes", "none"))
    pattern_color = _color_line_edit(qt, "#2d2f3c")
    pattern_opacity = _double_spin_box(qt, 0.0, 1.0, 1.0, 0.05)
    pattern_scale = _double_spin_box(qt, 0.25, 4.0, 1.0, 0.05)
    border_enabled = qt.QtWidgets.QCheckBox()
    border_color = _color_line_edit(qt, "#030404")
    border_width = _spin_box(qt, 0, 12, 2)
    border_width.setObjectName(APPEARANCE_BORDER_WIDTH_OBJECT_NAME)
    empty_socket_background = _color_line_edit(qt, "#101315")
    empty_socket_border = _color_line_edit(qt, "#020303")
    icon_backplate = _color_line_edit(qt, "#444341")
    icon_border = _color_line_edit(qt, "#171716")
    active_color = _color_line_edit(qt, "#8ccf3f")
    active_color.setObjectName(APPEARANCE_ACTIVE_COLOR_OBJECT_NAME)
    for widget in (appearance_theme, background_pattern):
        widget.setMinimumWidth(150)
    for widget in (pattern_opacity, pattern_scale, border_width):
        widget.setMinimumWidth(104)

    tabs = qt.QtWidgets.QTabWidget()
    tabs.setObjectName(TABS_OBJECT_NAME)
    content_layout.addWidget(tabs, 1)

    general_tab = qt.QtWidgets.QWidget()
    general_layout = qt.QtWidgets.QVBoxLayout(general_tab)
    general_layout.setContentsMargins(10, 10, 10, 10)
    general_layout.setSpacing(10)
    tabs.addTab(general_tab, "General")

    general_grid = qt.QtWidgets.QGridLayout()
    general_grid.setHorizontalSpacing(14)
    general_grid.setVerticalSpacing(8)
    general_layout.addLayout(general_grid)
    _add_grid_field(qt, general_grid, 0, 0, "Locked", locked)
    _add_grid_field(qt, general_grid, 0, 2, "Template", template_combo)
    _add_grid_field(qt, general_grid, 1, 0, "Preset Id", preset_id)
    _add_grid_field(qt, general_grid, 1, 2, "Anchor Point", anchor_combo)
    _add_grid_field(qt, general_grid, 2, 0, "Direction", orientation_combo)
    _add_grid_field(qt, general_grid, 2, 2, "Collapse", collapse_enabled)
    _add_grid_field(qt, general_grid, 3, 0, "Collapse Edge", collapse_edge)
    _add_grid_field(qt, general_grid, 3, 2, "Handle Icon", collapse_handle_icon)
    _add_grid_field(qt, general_grid, 4, 0, "Reveal", collapse_trigger)
    _add_grid_field(qt, general_grid, 4, 2, "Starts Collapsed", collapse_default)
    general_grid.setColumnStretch(1, 1)
    general_grid.setColumnStretch(3, 1)
    general_layout.addStretch(1)

    layout_tab = qt.QtWidgets.QWidget()
    layout_layout = qt.QtWidgets.QVBoxLayout(layout_tab)
    layout_layout.setContentsMargins(10, 10, 10, 10)
    layout_layout.setSpacing(8)
    tabs.addTab(layout_tab, "Layout")

    control_grid = qt.QtWidgets.QGridLayout()
    control_grid.setHorizontalSpacing(18)
    control_grid.setVerticalSpacing(12)
    layout_layout.addLayout(control_grid)
    _add_slider_field(qt, control_grid, 0, 0, "Buttons", button_count, 1, MAX_LAYOUT_COLUMNS)
    _add_slider_field(
        qt,
        control_grid,
        0,
        2,
        "Buttons Per Row",
        buttons_per_row,
        1,
        MAX_LAYOUT_COLUMNS,
    )
    _add_slider_field(
        qt,
        control_grid,
        1,
        0,
        "Button Size",
        scale,
        10,
        round(MAX_LAYOUT_SCALE * 100),
        scale_factor=100,
    )
    _add_slider_field(qt, control_grid, 1, 2, "Alpha", opacity, 0, 100, scale_factor=100)
    _add_slider_field(
        qt,
        control_grid,
        2,
        0,
        "Offset X",
        offset_x,
        -MAX_LAYOUT_OFFSET,
        MAX_LAYOUT_OFFSET,
    )
    _add_slider_field(
        qt,
        control_grid,
        2,
        2,
        "Offset Y",
        offset_y,
        -MAX_LAYOUT_OFFSET,
        MAX_LAYOUT_OFFSET,
    )
    control_grid.setColumnStretch(0, 1)
    control_grid.setColumnStretch(2, 1)
    layout_layout.addStretch(1)

    appearance_tab = qt.QtWidgets.QWidget()
    appearance_layout = qt.QtWidgets.QVBoxLayout(appearance_tab)
    appearance_layout.setContentsMargins(10, 10, 10, 10)
    appearance_layout.setSpacing(10)
    tabs.addTab(appearance_tab, "Appearance")

    theme_group = _group_box(qt, "Theme")
    theme_grid = qt.QtWidgets.QGridLayout(theme_group)
    theme_grid.setHorizontalSpacing(14)
    theme_grid.setVerticalSpacing(8)
    _add_grid_field(qt, theme_grid, 0, 0, "Theme", appearance_theme)
    _add_grid_field(qt, theme_grid, 0, 2, "Inherit Global", inherit_global)
    _add_grid_field(qt, theme_grid, 1, 0, "Main Color", accent_color)
    _add_grid_field(qt, theme_grid, 1, 2, "Text", text_color)
    _add_grid_field(qt, theme_grid, 2, 0, "Muted Text", muted_text_color)
    theme_grid.setColumnStretch(1, 1)
    theme_grid.setColumnStretch(3, 1)
    appearance_layout.addWidget(theme_group)

    backdrop_group = _group_box(qt, "Backdrop Settings")
    backdrop_grid = qt.QtWidgets.QGridLayout(backdrop_group)
    backdrop_grid.setHorizontalSpacing(14)
    backdrop_grid.setVerticalSpacing(8)
    _add_grid_field(qt, backdrop_grid, 0, 0, "Backdrop", background_enabled)
    _add_grid_field(qt, backdrop_grid, 0, 2, "Color", background_color)
    _add_grid_field(qt, backdrop_grid, 1, 0, "Pattern", background_pattern)
    _add_grid_field(qt, backdrop_grid, 1, 2, "Pattern Color", pattern_color)
    _add_grid_field(qt, backdrop_grid, 2, 0, "Pattern Alpha", pattern_opacity)
    _add_grid_field(qt, backdrop_grid, 2, 2, "Pattern Scale", pattern_scale)
    backdrop_grid.setColumnStretch(1, 1)
    backdrop_grid.setColumnStretch(3, 1)
    appearance_layout.addWidget(backdrop_group)

    border_group = _group_box(qt, "Border Settings")
    border_grid = qt.QtWidgets.QGridLayout(border_group)
    border_grid.setHorizontalSpacing(14)
    border_grid.setVerticalSpacing(8)
    _add_grid_field(qt, border_grid, 0, 0, "Border", border_enabled)
    _add_grid_field(qt, border_grid, 0, 2, "Color", border_color)
    _add_grid_field(qt, border_grid, 1, 0, "Thickness", border_width)
    border_grid.setColumnStretch(1, 1)
    border_grid.setColumnStretch(3, 1)
    appearance_layout.addWidget(border_group)

    slot_group = _group_box(qt, "Slot Colors")
    slot_grid = qt.QtWidgets.QGridLayout(slot_group)
    slot_grid.setHorizontalSpacing(14)
    slot_grid.setVerticalSpacing(8)
    _add_grid_field(qt, slot_grid, 0, 0, "Empty Socket", empty_socket_background)
    _add_grid_field(qt, slot_grid, 0, 2, "Empty Border", empty_socket_border)
    _add_grid_field(qt, slot_grid, 1, 0, "Icon Backplate", icon_backplate)
    _add_grid_field(qt, slot_grid, 1, 2, "Icon Border", icon_border)
    _add_grid_field(qt, slot_grid, 2, 0, "Active", active_color)
    slot_grid.setColumnStretch(1, 1)
    slot_grid.setColumnStretch(3, 1)
    appearance_layout.addWidget(slot_group)
    appearance_layout.addStretch(1)

    slots_tab = qt.QtWidgets.QWidget()
    slots_tab_layout = qt.QtWidgets.QVBoxLayout(slots_tab)
    slots_tab_layout.setContentsMargins(10, 10, 10, 10)
    slots_tab_layout.setSpacing(6)
    tabs.addTab(slots_tab, "Slots")

    slots_header = qt.QtWidgets.QWidget()
    slots_header_layout = qt.QtWidgets.QHBoxLayout(slots_header)
    slots_header_layout.setContentsMargins(0, 0, 0, 0)
    slots_header_layout.setSpacing(6)
    for text, width in _SLOT_COLUMNS:
        header = qt.QtWidgets.QLabel(text)
        header.setObjectName("ActionRailQuickCreateHeader")
        header.setMinimumWidth(width)
        slots_header_layout.addWidget(header)
    slots_tab_layout.addWidget(slots_header)

    slots_scroll = qt.QtWidgets.QScrollArea()
    slots_scroll.setObjectName("ActionRailQuickCreateSlotScroll")
    slots_scroll.setWidgetResizable(True)
    slots_scroll.setMinimumHeight(250)
    slots_scroll.setFrameShape(qt.QtWidgets.QFrame.NoFrame)
    slots_scroll.setHorizontalScrollBarPolicy(qt.QtCore.Qt.ScrollBarAlwaysOff)
    slots_tab_layout.addWidget(slots_scroll, 1)
    slots_container = qt.QtWidgets.QWidget()
    slots_layout = qt.QtWidgets.QVBoxLayout(slots_container)
    slots_layout.setContentsMargins(0, 0, 0, 0)
    slots_layout.setSpacing(6)
    slots_layout.addStretch(1)
    slots_scroll.setWidget(slots_container)
    slot_rows: list[dict[str, Any]] = []

    bindings_tab = qt.QtWidgets.QWidget()
    bindings_layout = qt.QtWidgets.QVBoxLayout(bindings_tab)
    bindings_layout.setContentsMargins(10, 10, 10, 10)
    bindings_layout.setSpacing(6)
    tabs.addTab(bindings_tab, "Bindings")
    bindings_table = qt.QtWidgets.QTableWidget()
    bindings_table.setObjectName(BINDINGS_TABLE_OBJECT_NAME)
    bindings_table.setColumnCount(len(_BINDING_COLUMNS))
    bindings_table.setHorizontalHeaderLabels(_BINDING_COLUMNS)
    bindings_table.setEditTriggers(qt.QtWidgets.QAbstractItemView.NoEditTriggers)
    bindings_table.setSelectionMode(qt.QtWidgets.QAbstractItemView.NoSelection)
    bindings_table.setAlternatingRowColors(True)
    bindings_table.verticalHeader().setVisible(False)
    bindings_table.horizontalHeader().setStretchLastSection(False)
    bindings_table.horizontalHeader().setSectionResizeMode(
        qt.QtWidgets.QHeaderView.Interactive
    )
    bindings_table.setHorizontalScrollBarPolicy(qt.QtCore.Qt.ScrollBarAlwaysOff)
    bindings_table.setColumnWidth(0, 140)
    bindings_table.setColumnWidth(1, 64)
    bindings_table.horizontalHeader().setSectionResizeMode(
        2,
        qt.QtWidgets.QHeaderView.Stretch,
    )
    bindings_layout.addWidget(bindings_table, 1)

    status = qt.QtWidgets.QLabel("")
    status.setObjectName(STATUS_OBJECT_NAME)
    status.setWordWrap(True)
    state = {
        "applying": False,
        "preview_active": False,
        "slots_unlocked": True,
    }

    def set_template_selection(template_id: str) -> None:
        for index, template in enumerate(templates):
            if template.id != template_id:
                continue
            old_combo_blocked = template_combo.blockSignals(True)
            old_list_blocked = template_list.blockSignals(True)
            try:
                template_combo.setCurrentIndex(index)
                template_list.setCurrentRow(index)
            finally:
                template_combo.blockSignals(old_combo_blocked)
                template_list.blockSignals(old_list_blocked)
            return

    def apply_values(values: QuickCreateDraftInput) -> None:
        state["applying"] = True
        try:
            set_template_selection(values.template_id)
            preset_id.setText(values.preset_id)
            _set_combo_text(anchor_combo, values.anchor)
            _set_combo_text(orientation_combo, values.orientation)
            button_count.setValue(max(1, len(values.slots)))
            buttons_per_row.setValue(_buttons_per_row_from_values(values))
            offset_x.setValue(values.offset[0])
            offset_y.setValue(values.offset[1])
            scale.setValue(values.scale)
            opacity.setValue(values.opacity)
            locked.setChecked(values.locked)
            collapse_enabled.setChecked(values.collapse_enabled)
            _set_combo_text(collapse_edge, values.collapse_edge)
            collapse_handle_icon.setText(values.collapse_handle_icon)
            _set_combo_text(collapse_trigger, values.collapse_reveal_trigger)
            collapse_default.setChecked(values.collapse_default_collapsed)
            _apply_appearance_values(
                values.appearance,
                theme=appearance_theme,
                inherit_global=inherit_global,
                accent=accent_color,
                text=text_color,
                muted_text=muted_text_color,
                background_enabled=background_enabled,
                background_color=background_color,
                background_pattern=background_pattern,
                pattern_color=pattern_color,
                pattern_opacity=pattern_opacity,
                pattern_scale=pattern_scale,
                border_enabled=border_enabled,
                border_color=border_color,
                border_width=border_width,
                empty_socket_background=empty_socket_background,
                empty_socket_border=empty_socket_border,
                icon_backplate=icon_backplate,
                icon_border=icon_border,
                active_color=active_color,
            )
            _clear_slot_rows(slot_rows, slots_layout)
            for slot in values.slots:
                _add_slot_row(qt, slots_layout, slot_rows, slot)
        finally:
            state["applying"] = False

    def current_input() -> QuickCreateDraftInput:
        slot_count = max(1, len(slot_rows))
        columns = min(max(1, buttons_per_row.value()), slot_count)
        rows = _layout_rows_for_button_count(slot_count, columns)
        return QuickCreateDraftInput(
            preset_id=preset_id.text().strip(),
            template_id=templates[template_combo.currentIndex()].id,
            slots=tuple(_slot_input_from_row(row) for row in slot_rows),
            anchor=anchor_combo.currentText(),
            orientation=orientation_combo.currentText(),
            rows=rows,
            columns=columns,
            offset=(offset_x.value(), offset_y.value()),
            scale=scale.value(),
            opacity=opacity.value(),
            locked=locked.isChecked(),
            collapse_enabled=collapse_enabled.isChecked(),
            collapse_edge=collapse_edge.currentText(),
            collapse_handle_icon=collapse_handle_icon.text().strip(),
            collapse_reveal_trigger=collapse_trigger.currentText(),
            collapse_default_collapsed=collapse_default.isChecked(),
            appearance=_appearance_from_panel(
                theme=appearance_theme,
                inherit_global=inherit_global,
                accent=accent_color,
                text=text_color,
                muted_text=muted_text_color,
                background_enabled=background_enabled,
                background_color=background_color,
                background_pattern=background_pattern,
                pattern_color=pattern_color,
                pattern_opacity=pattern_opacity,
                pattern_scale=pattern_scale,
                border_enabled=border_enabled,
                border_color=border_color,
                border_width=border_width,
                empty_socket_background=empty_socket_background,
                empty_socket_border=empty_socket_border,
                icon_backplate=icon_backplate,
                icon_border=icon_border,
                active_color=active_color,
            ),
        )

    def current_draft() -> object:
        return build_quick_create_draft(current_input())

    def sync_slot_rows_from_preview() -> None:
        if not state["preview_active"]:
            return
        spec = active_quick_create_preview_spec(preset_id.text().strip())
        if spec is None:
            return
        slot_inputs = {
            slot.id: slot
            for slot in (_slot_input_from_item(spec.id, item) for item in spec.items)
        }
        for row in slot_rows:
            slot_id = row["id"].text().strip()
            slot = slot_inputs.get(slot_id)
            if slot is None:
                continue
            source = row.get("source")
            label_text = row["label"].text().strip()
            key_label_text = row["key_label"].text().strip()
            if label_text == getattr(source, "label", ""):
                row["label"].setText(slot.label)
            if key_label_text == getattr(source, "key_label", ""):
                row["key_label"].setText(slot.key_label)
            row["source"] = slot

    def validate_draft() -> None:
        try:
            sync_slot_rows_from_preview()
            draft = current_draft()
            text = _valid_draft_status_text(draft)
        except Exception as exc:
            _set_status(qt, status, "error", str(exc))
            return
        refresh_bindings()
        _set_status(qt, status, "ok", text)

    def _apply_slot_lock_button_text() -> None:
        slot_lock_button.setText("Lock Bar" if state["slots_unlocked"] else "Unlock Bar")

    def _preview_draft_with_slot_lock(draft: object) -> None:
        set_quick_create_slots_unlocked(
            draft,
            bool(state["slots_unlocked"]),
        )

    def _slot_lock_status_prefix() -> str:
        return "unlocked" if state["slots_unlocked"] else "locked"

    def preview_draft() -> None:
        try:
            sync_slot_rows_from_preview()
            draft = current_draft()
            _preview_draft_with_slot_lock(draft)
        except Exception as exc:
            _set_status(qt, status, "error", str(exc))
            return
        state["preview_active"] = True
        _set_status(
            qt,
            status,
            "ok",
            f"Previewing {_slot_lock_status_prefix()} draft: {draft.id}",
        )

    def edit_layout() -> None:
        try:
            draft = current_draft()
            edit_state = edit_quick_create_layout(draft)
        except Exception as exc:
            _set_status(qt, status, "error", str(exc))
            return
        state["preview_active"] = True
        _set_status(
            qt,
            status,
            "ok",
            f"Editing layout: {edit_state.selected_preset_id or draft.id}",
        )

    def toggle_slot_lock() -> None:
        state["slots_unlocked"] = not bool(state["slots_unlocked"])
        _apply_slot_lock_button_text()
        try:
            sync_slot_rows_from_preview()
            draft = current_draft()
            _preview_draft_with_slot_lock(draft)
        except Exception as exc:
            _set_status(qt, status, "error", str(exc))
            return
        state["preview_active"] = True
        _set_status(qt, status, "ok", f"Bar {_slot_lock_status_prefix()}: {draft.id}")

    def clear_preview() -> None:
        cleared = clear_quick_create_previews()
        state["preview_active"] = False
        _set_status(qt, status, "ok", f"Cleared Quick Create previews: {cleared}")

    def refresh_live_preview() -> None:
        if state["applying"] or not state["preview_active"]:
            return
        try:
            sync_slot_rows_from_preview()
            draft = current_draft()
            _preview_draft_with_slot_lock(draft)
        except Exception as exc:
            _set_status(qt, status, "error", str(exc))
            return
        _set_status(
            qt,
            status,
            "ok",
            f"Previewing {_slot_lock_status_prefix()} draft: {draft.id}",
        )

    def load_existing() -> None:
        preset_text = preset_id.text().strip()
        try:
            values = load_quick_create_preset(preset_text, preset_dir=user_preset_dir)
            apply_values(values)
            refresh_bindings()
        except Exception as exc:
            _set_status(qt, status, "error", str(exc))
            return
        _set_status(qt, status, "ok", f"Loaded user preset: {preset_text}")
        refresh_live_preview()

    def save_draft(*, overwrite: bool = False) -> None:
        try:
            sync_slot_rows_from_preview()
            result = save_quick_create_preset(
                current_draft(),
                overwrite=overwrite,
                preset_dir=user_preset_dir,
            )
        except Exception as exc:
            _set_status(qt, status, "error", str(exc))
            return
        _set_status(
            qt,
            status,
            "ok",
            f"Saved and showing user preset: {result.preset_id} ({result.path})",
        )
        refresh_bindings()

    def save_and_publish_draft() -> None:
        try:
            sync_slot_rows_from_preview()
            result = save_quick_create_preset(
                current_draft(),
                overwrite=True,
                publish=True,
                install_shelf=True,
                preset_dir=user_preset_dir,
            )
        except Exception as exc:
            _set_status(qt, status, "error", str(exc))
            return
        warnings = len(getattr(result.diagnostics, "warnings", ()))
        detail = (
            f"Published {len(result.published)} slot commands"
            + (f", shelf {result.shelf_button}" if result.shelf_button else "")
        )
        if result.unpublished:
            detail = f"{detail}; removed {len(result.unpublished)} stale commands"
        if warnings:
            detail = f"{detail}; {warnings} warnings in diagnostics"
        _set_status(qt, status, "ok", f"Saved user preset: {result.preset_id}. {detail}")
        refresh_bindings()

    def refresh_bindings() -> tuple[Any, ...]:
        try:
            sync_slot_rows_from_preview()
            draft = current_draft()
            spec = build_draft_spec(draft)
            targets = slot_binding_targets(
                spec.id,
                spec=spec,
                user_preset_dir=user_preset_dir,
            )
        except Exception:
            targets = ()
        _populate_bindings_table(qt, bindings_table, targets)
        return targets

    def refresh_template(index: int) -> None:
        if template_list.currentRow() != index:
            template_list.setCurrentRow(index)
        apply_values(make_default_input(templates[index].id))
        validate_draft()
        refresh_live_preview()

    edit_button_row = qt.QtWidgets.QHBoxLayout()
    edit_button_row.setContentsMargins(0, 0, 0, 0)
    edit_button_row.setSpacing(8)
    root.addLayout(edit_button_row)
    save_button_row = qt.QtWidgets.QHBoxLayout()
    save_button_row.setContentsMargins(0, 0, 0, 0)
    save_button_row.setSpacing(8)
    root.addLayout(save_button_row)
    add_slot = qt.QtWidgets.QPushButton("Add Slot")
    remove_slot = qt.QtWidgets.QPushButton("Remove Slot")
    validate = qt.QtWidgets.QPushButton("Validate Draft")
    preview = qt.QtWidgets.QPushButton("Preview")
    edit_layout_button = qt.QtWidgets.QPushButton("Edit Layout")
    slot_lock_button = qt.QtWidgets.QPushButton()
    clear_preview_button = qt.QtWidgets.QPushButton("Clear Preview")
    save = qt.QtWidgets.QPushButton("Save Preset")
    overwrite = qt.QtWidgets.QPushButton("Overwrite Preset")
    publish = qt.QtWidgets.QPushButton("Save + Publish")
    load_existing_button = qt.QtWidgets.QPushButton("Load Existing")
    preview.setObjectName(PREVIEW_BUTTON_OBJECT_NAME)
    edit_layout_button.setObjectName(EDIT_LAYOUT_BUTTON_OBJECT_NAME)
    slot_lock_button.setObjectName(SLOT_LOCK_BUTTON_OBJECT_NAME)
    clear_preview_button.setObjectName(CLEAR_PREVIEW_BUTTON_OBJECT_NAME)
    save.setObjectName(SAVE_BUTTON_OBJECT_NAME)
    publish.setObjectName(PUBLISH_BUTTON_OBJECT_NAME)
    overwrite.setObjectName(OVERWRITE_BUTTON_OBJECT_NAME)
    load_existing_button.setObjectName(LOAD_BUTTON_OBJECT_NAME)
    for button, row in (
        (add_slot, edit_button_row),
        (remove_slot, edit_button_row),
        (validate, edit_button_row),
        (preview, edit_button_row),
        (edit_layout_button, edit_button_row),
        (slot_lock_button, edit_button_row),
        (clear_preview_button, edit_button_row),
        (load_existing_button, save_button_row),
        (save, save_button_row),
        (overwrite, save_button_row),
        (publish, save_button_row),
    ):
        button.setProperty("actionRailRole", "dialogButton")
        row.addWidget(button)
    edit_button_row.addStretch(1)
    save_button_row.addStretch(1)
    root.addWidget(status)

    panel._actionrail_current_draft = current_draft
    panel._actionrail_validate_draft = validate_draft
    panel._actionrail_preview_draft = preview_draft
    panel._actionrail_edit_layout = edit_layout
    panel._actionrail_edit_slots = toggle_slot_lock
    panel._actionrail_toggle_slot_lock = toggle_slot_lock
    panel._actionrail_clear_preview = clear_preview
    panel._actionrail_save_draft = save_draft
    panel._actionrail_save_publish_draft = save_and_publish_draft
    panel._actionrail_load_existing = load_existing
    panel._actionrail_refresh_bindings = refresh_bindings

    template_combo.currentIndexChanged.connect(refresh_template)
    template_list.currentRowChanged.connect(template_combo.setCurrentIndex)
    def sync_slot_count(value: int) -> None:
        if state["applying"]:
            return
        _sync_slot_rows_to_count(qt, slots_layout, slot_rows, value)
        validate_draft()
        refresh_live_preview()

    def add_and_validate() -> None:
        _add_slot_row(
            qt,
            slots_layout,
            slot_rows,
            _generated_slot_input(len(slot_rows) + 1),
        )
        button_count.setValue(len(slot_rows))
        validate_draft()
        refresh_live_preview()

    def remove_and_validate() -> None:
        if len(slot_rows) <= 1:
            button_count.setValue(1)
            validate_draft()
            refresh_live_preview()
            return
        _remove_last_slot_row(slot_rows, slots_layout)
        button_count.setValue(max(1, len(slot_rows)))
        validate_draft()
        refresh_live_preview()

    add_slot.clicked.connect(add_and_validate)
    remove_slot.clicked.connect(remove_and_validate)
    reset_values.clicked.connect(lambda: refresh_template(template_combo.currentIndex()))
    validate_top.clicked.connect(validate_draft)
    validate.clicked.connect(validate_draft)
    preview.clicked.connect(preview_draft)
    edit_layout_button.clicked.connect(edit_layout)
    slot_lock_button.clicked.connect(toggle_slot_lock)
    clear_preview_button.clicked.connect(clear_preview)
    save.clicked.connect(lambda: save_draft(overwrite=False))
    overwrite.clicked.connect(lambda: save_draft(overwrite=True))
    publish.clicked.connect(save_and_publish_draft)
    load_existing_button.clicked.connect(load_existing)
    button_count.valueChanged.connect(sync_slot_count)
    for widget in (
        buttons_per_row,
        offset_x,
        offset_y,
        scale,
        opacity,
        pattern_opacity,
        pattern_scale,
        border_width,
    ):
        widget.valueChanged.connect(lambda _value: refresh_live_preview())
    for widget in (
        locked,
        collapse_enabled,
        collapse_default,
        inherit_global,
        background_enabled,
        border_enabled,
    ):
        widget.stateChanged.connect(lambda _value: refresh_live_preview())
    for widget in (
        anchor_combo,
        orientation_combo,
        collapse_edge,
        collapse_trigger,
        appearance_theme,
        background_pattern,
    ):
        widget.currentTextChanged.connect(lambda _value: refresh_live_preview())
    for widget in (
        collapse_handle_icon,
        accent_color,
        text_color,
        muted_text_color,
        background_color,
        pattern_color,
        border_color,
        empty_socket_background,
        empty_socket_border,
        icon_backplate,
        icon_border,
        active_color,
    ):
        widget.textChanged.connect(lambda _value: refresh_live_preview())
    template_list.setCurrentRow(0)
    tabs.setCurrentIndex(1)
    apply_values(make_default_input())
    _apply_slot_lock_button_text()
    validate_draft()


def _add_slot_row(  # pragma: no cover
    qt: QtBinding,
    parent_layout: Any,
    rows: list[dict[str, Any]],
    slot: QuickCreateSlotInput,
) -> None:
    row_widget = qt.QtWidgets.QWidget()
    row_layout = qt.QtWidgets.QHBoxLayout(row_widget)
    row_layout.setContentsMargins(0, 0, 0, 0)
    row_layout.setSpacing(6)

    slot_id = qt.QtWidgets.QLineEdit(slot.id)
    label = qt.QtWidgets.QLineEdit(slot.label)
    key_label = qt.QtWidgets.QLineEdit(slot.key_label)

    for widget, (_label, width) in zip(
        (slot_id, label, key_label),
        _SLOT_COLUMNS,
        strict=True,
    ):
        widget.setMinimumWidth(width)
        row_layout.addWidget(widget)
    parent_layout.insertWidget(max(0, parent_layout.count() - 1), row_widget)
    rows.append(
        {
            "widget": row_widget,
            "id": slot_id,
            "label": label,
            "key_label": key_label,
            "source": slot,
        }
    )


def _group_box(qt: QtBinding, title: str) -> Any:  # pragma: no cover
    group = qt.QtWidgets.QGroupBox(title)
    group.setObjectName("ActionRailQuickCreateGroup")
    return group


def _color_line_edit(qt: QtBinding, value: str) -> Any:  # pragma: no cover
    edit = qt.QtWidgets.QLineEdit(value)
    edit.setPlaceholderText("#rrggbb")
    edit.setMinimumWidth(112)
    return edit


def _apply_appearance_values(  # pragma: no cover
    appearance: RailAppearance,
    **widgets: Any,
) -> None:
    widgets["theme"].setEditText(appearance.theme)
    widgets["inherit_global"].setChecked(appearance.inherit_global)
    widgets["accent"].setText(appearance.accent or "#8ccf3f")
    widgets["text"].setText(appearance.text)
    widgets["muted_text"].setText(appearance.muted_text)
    widgets["background_enabled"].setChecked(appearance.background.enabled)
    widgets["background_color"].setText(appearance.background.color or "#1d202a")
    _set_combo_text(widgets["background_pattern"], appearance.background.pattern)
    widgets["pattern_color"].setText(appearance.background.pattern_color or "#2d2f3c")
    widgets["pattern_opacity"].setValue(appearance.background.pattern_opacity)
    widgets["pattern_scale"].setValue(appearance.background.pattern_scale)
    widgets["border_enabled"].setChecked(appearance.border.enabled)
    widgets["border_color"].setText(appearance.border.color or "#030404")
    widgets["border_width"].setValue(
        2 if appearance.border.width is None else appearance.border.width
    )
    widgets["empty_socket_background"].setText(
        appearance.slots.empty_background or "#101315"
    )
    widgets["empty_socket_border"].setText(appearance.slots.empty_border or "#020303")
    widgets["icon_backplate"].setText(appearance.slots.icon_backplate or "#444341")
    widgets["icon_border"].setText(appearance.slots.icon_border or "#171716")
    widgets["active_color"].setText(appearance.slots.active or "#8ccf3f")


def _appearance_from_panel(**widgets: Any) -> RailAppearance:  # pragma: no cover
    return RailAppearance(
        theme=widgets["theme"].currentText().strip() or "default",
        inherit_global=widgets["inherit_global"].isChecked(),
        accent=_optional_color_text(widgets["accent"], "#8ccf3f"),
        text=_optional_color_text(widgets["text"], ""),
        muted_text=_optional_color_text(widgets["muted_text"], ""),
        background=RailBackground(
            enabled=widgets["background_enabled"].isChecked(),
            color=_optional_color_text(widgets["background_color"], "#1d202a"),
            pattern=widgets["background_pattern"].currentText(),
            pattern_color=_optional_color_text(widgets["pattern_color"], "#2d2f3c"),
            pattern_opacity=widgets["pattern_opacity"].value(),
            pattern_scale=widgets["pattern_scale"].value(),
        ),
        border=RailBorder(
            enabled=widgets["border_enabled"].isChecked(),
            color=_optional_color_text(widgets["border_color"], "#030404"),
            width=_optional_int_value(widgets["border_width"], 2),
        ),
        slots=RailSlotAppearance(
            empty_background=_optional_color_text(
                widgets["empty_socket_background"],
                "#101315",
            ),
            empty_border=_optional_color_text(widgets["empty_socket_border"], "#020303"),
            icon_backplate=_optional_color_text(widgets["icon_backplate"], "#444341"),
            icon_border=_optional_color_text(widgets["icon_border"], "#171716"),
            active=_optional_color_text(widgets["active_color"], "#8ccf3f"),
        ),
    )


def _optional_color_text(widget: Any, default_value: str) -> str:
    value = widget.text().strip()
    return "" if value == default_value else value


def _optional_int_value(widget: Any, default_value: int) -> int | None:
    value = widget.value()
    return None if value == default_value else value


def _clear_slot_rows(rows: list[dict[str, Any]], parent_layout: Any) -> None:  # pragma: no cover
    while rows:
        _remove_last_slot_row(rows, parent_layout)


def _remove_last_slot_row(  # pragma: no cover
    rows: list[dict[str, Any]],
    parent_layout: Any,
) -> None:
    if not rows:
        return
    row = rows.pop()
    widget = row["widget"]
    parent_layout.removeWidget(widget)
    widget.setParent(None)
    widget.deleteLater()


def _sync_slot_rows_to_count(  # pragma: no cover
    qt: QtBinding,
    parent_layout: Any,
    rows: list[dict[str, Any]],
    count: int,
) -> None:
    target = max(1, count)
    while len(rows) > target:
        _remove_last_slot_row(rows, parent_layout)
    while len(rows) < target:
        index = len(rows) + 1
        _add_slot_row(
            qt,
            parent_layout,
            rows,
            _generated_slot_input(index),
        )


def _slot_input_from_row(row: dict[str, Any]) -> QuickCreateSlotInput:  # pragma: no cover
    source = row.get("source")
    return QuickCreateSlotInput(
        id=row["id"].text().strip(),
        label=row["label"].text().strip(),
        action=getattr(source, "action", ""),
        key_label=row["key_label"].text().strip(),
        icon=getattr(source, "icon", ""),
        type=getattr(source, "type", "button"),
        tone=getattr(source, "tone", "neutral"),
        tooltip=getattr(source, "tooltip", ""),
        visible_when=getattr(source, "visible_when", ""),
        enabled_when=getattr(source, "enabled_when", ""),
        active_when=getattr(source, "active_when", ""),
        size=getattr(source, "size", 0),
    )


def _populate_bindings_table(
    qt: QtBinding,
    table: Any,
    targets: tuple[Any, ...],
) -> None:  # pragma: no cover
    table.setRowCount(len(targets))
    for row, target in enumerate(targets):
        values = (
            f"{target.label} ({target.slot_id})",
            target.key_label,
            target.name_command,
        )
        for column, value in enumerate(values):
            item = qt.QtWidgets.QTableWidgetItem(str(value))
            item.setFlags(qt.QtCore.Qt.ItemIsSelectable | qt.QtCore.Qt.ItemIsEnabled)
            item.setToolTip(str(value))
            table.setItem(row, column, item)
    table.clearSelection()


def _generated_slot_input(index: int) -> QuickCreateSlotInput:
    return QuickCreateSlotInput(
        id=f"slot_{index}",
        label="",
        action="",
        key_label=str(index),
        icon="",
    )


def _layout_rows_for_button_count(button_count: int, buttons_per_row: int) -> int:
    return max(1, ceil(max(1, button_count) / max(1, buttons_per_row)))


def _buttons_per_row_from_values(values: QuickCreateDraftInput) -> int:
    slot_count = max(1, len(values.slots))
    return max(1, min(values.columns, slot_count, MAX_LAYOUT_COLUMNS))


def _spin_box(qt: QtBinding, minimum: int, maximum: int, value: int) -> Any:  # pragma: no cover
    spin = qt.QtWidgets.QSpinBox()
    spin.setRange(minimum, maximum)
    spin.setValue(value)
    spin.setMinimumWidth(80)
    return spin


def _double_spin_box(  # pragma: no cover
    qt: QtBinding,
    minimum: float,
    maximum: float,
    value: float,
    step: float,
) -> Any:
    spin = qt.QtWidgets.QDoubleSpinBox()
    spin.setRange(minimum, maximum)
    spin.setSingleStep(step)
    spin.setValue(value)
    spin.setMinimumWidth(80)
    return spin


def _add_grid_field(  # pragma: no cover
    qt: QtBinding,
    grid: Any,
    row: int,
    column: int,
    label_text: str,
    widget: Any,
) -> None:
    label = qt.QtWidgets.QLabel(label_text)
    label.setObjectName("ActionRailQuickCreateFieldLabel")
    grid.addWidget(label, row, column)
    grid.addWidget(widget, row, column + 1)


def _add_slider_field(  # pragma: no cover
    qt: QtBinding,
    grid: Any,
    row: int,
    column: int,
    label_text: str,
    value_widget: Any,
    minimum: int,
    maximum: int,
    *,
    scale_factor: int = 1,
) -> None:
    field = qt.QtWidgets.QWidget()
    layout = qt.QtWidgets.QVBoxLayout(field)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(4)

    top = qt.QtWidgets.QHBoxLayout()
    top.setContentsMargins(0, 0, 0, 0)
    top.setSpacing(8)
    label = qt.QtWidgets.QLabel(label_text)
    label.setObjectName("ActionRailQuickCreateFieldLabel")
    top.addWidget(label)
    top.addStretch(1)
    value_widget.setFixedWidth(84)
    top.addWidget(value_widget)
    layout.addLayout(top)

    slider_row = qt.QtWidgets.QHBoxLayout()
    slider_row.setContentsMargins(0, 0, 0, 0)
    slider_row.setSpacing(6)
    min_label = qt.QtWidgets.QLabel(_slider_label(minimum, scale_factor))
    max_label = qt.QtWidgets.QLabel(_slider_label(maximum, scale_factor))
    slider = qt.QtWidgets.QSlider(qt.QtCore.Qt.Horizontal)
    slider.setRange(minimum, maximum)
    slider.setValue(_widget_to_slider_value(value_widget, scale_factor))
    for label_widget in (min_label, max_label):
        label_widget.setObjectName("ActionRailQuickCreateSliderLimit")
        slider_row.addWidget(label_widget)
        if label_widget is min_label:
            slider_row.addWidget(slider, 1)
    layout.addLayout(slider_row)

    def set_widget_from_slider(value: int) -> None:
        value_widget.setValue(_widget_value_from_slider(value, scale_factor))

    def set_slider_from_widget(value: float) -> None:
        slider.setValue(round(float(value) * scale_factor))

    slider.valueChanged.connect(set_widget_from_slider)
    value_widget.valueChanged.connect(set_slider_from_widget)
    grid.addWidget(field, row, column)


def _slider_label(value: int, scale_factor: int) -> str:
    if scale_factor == 1:
        return str(value)
    return f"{value / scale_factor:g}"


def _widget_value_from_slider(value: int, scale_factor: int) -> int | float:
    if scale_factor == 1:
        return value
    return value / scale_factor


def _valid_draft_status_text(draft: DraftRail) -> str:
    spec = build_draft_spec(draft)
    from . import diagnostics

    report = diagnostics.diagnose_publish_spec(spec, record=False)
    if report.has_errors:
        raise ValueError(_diagnostic_status_text("Draft has errors", report.errors))
    if report.warnings:
        return (
            f"Valid draft: {spec.id} ({len(spec.items)} slots); "
            f"{_diagnostic_status_text('warnings', report.warnings)}"
        )
    return f"Valid draft: {spec.id} ({len(spec.items)} slots)"


def _diagnostic_status_text(prefix: str, issues: tuple[Any, ...]) -> str:
    first = issues[0]
    target = getattr(first, "slot_id", "") or getattr(first, "target", "")
    target_text = f" [{target}]" if target else ""
    remaining = len(issues) - 1
    suffix = f", +{remaining} more" if remaining else ""
    return f"{prefix}: {len(issues)}: {getattr(first, 'code', 'diagnostic')}{target_text}{suffix}"


def _set_status(qt: QtBinding, status: Any, state: str, text: str) -> None:  # pragma: no cover
    status.setProperty("actionRailStatus", state)
    status.setText(text)
    status.style().unpolish(status)
    status.style().polish(status)
    status.update()


def _widget_to_slider_value(widget: Any, scale_factor: int) -> int:  # pragma: no cover
    return round(float(widget.value()) * scale_factor)


def _set_combo_text(combo: Any, text: str) -> None:  # pragma: no cover
    index = combo.findText(text)
    if index >= 0:
        combo.setCurrentIndex(index)
        return
    if text and combo.isEditable():
        combo.setEditText(text)


def _close_existing_panel(qt: QtBinding) -> None:  # pragma: no cover
    global _PANEL
    if _PANEL is None:
        return
    try:
        _PANEL.close()
        _PANEL.deleteLater()
        app = qt.QtWidgets.QApplication.instance()
        if app is not None:
            app.sendPostedEvents(None, qt.QtCore.QEvent.DeferredDelete)
    except Exception:
        pass
    _PANEL = None


def _forget_panel(*_args: object) -> None:  # pragma: no cover
    global _PANEL
    _PANEL = None


def _style_sheet() -> str:  # pragma: no cover
    theme = DEFAULT_THEME
    return f"""
QWidget#{PANEL_OBJECT_NAME} {{
    background: {theme.panel_background};
    color: {theme.button_color};
}}
QFrame#ActionRailQuickCreateSidebar,
QFrame#ActionRailQuickCreateContent {{
    background: {theme.panel_surface_background};
    border: {theme.cluster_border_width}px solid {theme.cluster_border};
    border-top-color: {theme.accent_line};
    border-radius: {theme.cluster_border_radius}px;
}}
QLabel#ActionRailQuickCreateTitle {{
    color: {theme.button_color};
    font-size: 18px;
    font-weight: 700;
    letter-spacing: 0px;
}}
QLabel#ActionRailQuickCreateSectionLabel,
QLabel#{STATUS_OBJECT_NAME} {{
    color: {theme.button_color};
    font-size: 12px;
    letter-spacing: 0px;
}}
QLabel#{STATUS_OBJECT_NAME}[actionRailStatus="ok"] {{
    color: {theme.success};
}}
QLabel#{STATUS_OBJECT_NAME}[actionRailStatus="error"] {{
    color: {theme.error};
}}
QLabel#ActionRailQuickCreateNavTitle {{
    color: {theme.button_color};
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0px;
}}
QListWidget#ActionRailQuickCreateTemplateList {{
    background: transparent;
    color: {theme.button_color};
    border: 0px;
    font-size: 12px;
    letter-spacing: 0px;
}}
QListWidget#ActionRailQuickCreateTemplateList::item {{
    min-height: 24px;
    padding: 4px 7px;
}}
QListWidget#ActionRailQuickCreateTemplateList::item:selected {{
    background: {theme.button_active_background};
    color: {theme.button_color};
}}
QTabWidget#ActionRailQuickCreateTabs::pane {{
    border: {theme.cluster_border_width}px solid {theme.cluster_border};
    border-top-color: {theme.accent_line};
    border-radius: {theme.cluster_border_radius}px;
    background: transparent;
}}
QTabBar::tab {{
    min-width: 92px;
    min-height: 24px;
    border: {theme.button_border_width}px solid {theme.button_border};
    background: {theme.button_background};
    color: {theme.button_color};
    padding: 3px 10px;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0px;
}}
QTabBar::tab:selected {{
    background: {theme.button_active_background};
    border-color: {theme.button_hover_border};
}}
QGroupBox#ActionRailQuickCreateGroup {{
    border: {theme.cluster_border_width}px solid {theme.cluster_border};
    border-top-color: {theme.accent_line};
    border-radius: {theme.cluster_border_radius}px;
    margin-top: 12px;
    padding-top: 6px;
    color: {theme.button_color};
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0px;
}}
QGroupBox#ActionRailQuickCreateGroup::title {{
    subcontrol-origin: margin;
    left: 8px;
    padding: 0 4px;
}}
QLabel#ActionRailQuickCreateFieldLabel,
QLabel#ActionRailQuickCreateHeader {{
    color: {theme.button_color};
    font-size: 12px;
    letter-spacing: 0px;
}}
QScrollArea#ActionRailQuickCreateSlotScroll {{
    background: transparent;
    border: 0px;
}}
QTableWidget#ActionRailQuickCreateBindingsTable {{
    background: {theme.panel_profile_background};
    color: {theme.button_color};
    gridline-color: {theme.cluster_border};
    border: {theme.button_border_width}px solid {theme.button_border};
    selection-background-color: {theme.button_active_background};
    selection-color: {theme.button_color};
    font-size: 12px;
    letter-spacing: 0px;
}}
QHeaderView::section {{
    background: {theme.panel_inset_background};
    color: {theme.button_color};
    border: {theme.button_border_width}px solid {theme.button_border};
    padding: 4px 7px;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0px;
}}
QLabel#ActionRailQuickCreateSliderLimit {{
    color: {theme.button_color};
    font-size: 11px;
    letter-spacing: 0px;
    min-width: 22px;
}}
QSlider::groove:horizontal {{
    height: 8px;
    background: {theme.panel_inset_background};
    border: 1px solid {theme.cluster_border};
}}
QSlider::handle:horizontal {{
    width: 12px;
    margin: -4px 0;
    background: {theme.button_active_background};
    border: 1px solid {theme.button_active_border};
}}
QLineEdit,
QComboBox,
QSpinBox,
QDoubleSpinBox {{
    min-height: 24px;
    border: {theme.button_border_width}px solid {theme.button_border};
    border-radius: {theme.button_border_radius}px;
    background: {theme.button_background};
    color: {theme.button_color};
    padding: 3px 7px;
    font-size: 12px;
    letter-spacing: 0px;
}}
QPushButton[actionRailRole="dialogButton"] {{
    min-height: 26px;
    border: {theme.button_border_width}px solid {theme.button_border};
    border-radius: {theme.button_border_radius}px;
    background: {theme.button_background};
    color: {theme.button_color};
    padding: 4px 10px;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0px;
}}
QPushButton[actionRailRole="utilityButton"] {{
    min-height: 24px;
    border: {theme.button_border_width}px solid {theme.button_border};
    border-radius: {theme.button_border_radius}px;
    background: {theme.button_background};
    color: {theme.button_color};
    padding: 3px 10px;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0px;
}}
QPushButton[actionRailRole="dialogButton"]:hover {{
    background: {theme.button_hover_background};
    border-color: {theme.button_hover_border};
}}
QPushButton[actionRailRole="utilityButton"]:hover {{
    background: {theme.button_hover_background};
    border-color: {theme.button_hover_border};
}}
"""
