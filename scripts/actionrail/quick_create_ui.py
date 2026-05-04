"""Dockable Quick Create Qt panel for ActionRail."""

from __future__ import annotations

from typing import Any

from .authoring import DraftRail, build_draft_spec
from .overlay import maya_main_window
from .qt import QtBinding, load
from .quick_create import (
    ANCHOR_CHOICES,
    QuickCreateDraftInput,
    QuickCreateSlotInput,
    action_choices,
    build_quick_create_draft,
    icon_choices,
    make_default_input,
    template_choices,
)
from .theme import DEFAULT_THEME

PANEL_OBJECT_NAME = "ActionRailQuickCreatePanel"
STATUS_OBJECT_NAME = "ActionRailQuickCreateStatus"
TEMPLATE_COMBO_OBJECT_NAME = "ActionRailQuickCreateTemplateCombo"
TABS_OBJECT_NAME = "ActionRailQuickCreateTabs"

_PANEL: Any | None = None
_SLOT_COLUMNS = (
    ("Id", 96),
    ("Label", 108),
    ("Action", 176),
    ("Key", 64),
    ("Icon", 174),
)

__all__ = [
    "PANEL_OBJECT_NAME",
    "STATUS_OBJECT_NAME",
    "TABS_OBJECT_NAME",
    "TEMPLATE_COMBO_OBJECT_NAME",
    "show_quick_create_panel",
]


def show_quick_create_panel(  # pragma: no cover - Maya-hosted Qt panel.
    *,
    qt_binding: QtBinding | None = None,
    parent: Any | None = None,
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

    _build_panel(panel, qt)
    panel.destroyed.connect(_forget_panel)
    _PANEL = panel
    panel.show()
    panel.raise_()
    panel.activateWindow()
    return panel


def _build_panel(panel: Any, qt: QtBinding) -> None:  # pragma: no cover
    panel.setStyleSheet(_style_sheet())
    templates = template_choices()
    actions = action_choices()
    icons = icon_choices()

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
    rows = _spin_box(qt, 1, 12, 1)
    columns = _spin_box(qt, 1, 12, 1)
    offset_x = _spin_box(qt, -400, 400, 0)
    offset_y = _spin_box(qt, -400, 400, 0)
    scale = _double_spin_box(qt, 0.1, 4.0, 1.0, 0.05)
    opacity = _double_spin_box(qt, 0.0, 1.0, 1.0, 0.05)
    locked = qt.QtWidgets.QCheckBox()

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
    _add_slider_field(qt, control_grid, 0, 0, "Buttons", columns, 1, 12)
    _add_slider_field(qt, control_grid, 0, 2, "Buttons Per Row", rows, 1, 12)
    _add_slider_field(qt, control_grid, 1, 0, "Button Size", scale, 10, 400, scale_factor=100)
    _add_slider_field(qt, control_grid, 1, 2, "Alpha", opacity, 0, 100, scale_factor=100)
    _add_slider_field(qt, control_grid, 2, 0, "Offset X", offset_x, -400, 400)
    _add_slider_field(qt, control_grid, 2, 2, "Offset Y", offset_y, -400, 400)
    control_grid.setColumnStretch(0, 1)
    control_grid.setColumnStretch(2, 1)
    layout_layout.addStretch(1)

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

    status = qt.QtWidgets.QLabel("")
    status.setObjectName(STATUS_OBJECT_NAME)
    status.setWordWrap(True)

    def apply_values(values: QuickCreateDraftInput) -> None:
        preset_id.setText(values.preset_id)
        _set_combo_text(anchor_combo, values.anchor)
        _set_combo_text(orientation_combo, values.orientation)
        rows.setValue(values.rows)
        columns.setValue(values.columns)
        offset_x.setValue(values.offset[0])
        offset_y.setValue(values.offset[1])
        scale.setValue(values.scale)
        opacity.setValue(values.opacity)
        locked.setChecked(values.locked)
        _clear_slot_rows(slot_rows, slots_layout)
        for slot in values.slots:
            _add_slot_row(qt, slots_layout, slot_rows, slot, actions, icons)

    def current_input() -> QuickCreateDraftInput:
        return QuickCreateDraftInput(
            preset_id=preset_id.text().strip(),
            template_id=templates[template_combo.currentIndex()].id,
            slots=tuple(_slot_input_from_row(row) for row in slot_rows),
            anchor=anchor_combo.currentText(),
            orientation=orientation_combo.currentText(),
            rows=rows.value(),
            columns=columns.value(),
            offset=(offset_x.value(), offset_y.value()),
            scale=scale.value(),
            opacity=opacity.value(),
            locked=locked.isChecked(),
        )

    def current_draft() -> object:
        return build_quick_create_draft(current_input())

    def validate_draft() -> None:
        try:
            draft = current_draft()
            text = _valid_draft_status_text(draft)
        except Exception as exc:
            status.setProperty("actionRailStatus", "error")
            status.setText(str(exc))
            return
        status.setProperty("actionRailStatus", "ok")
        status.setText(text)

    def refresh_template(index: int) -> None:
        if template_list.currentRow() != index:
            template_list.setCurrentRow(index)
        apply_values(make_default_input(templates[index].id))
        validate_draft()

    button_row = qt.QtWidgets.QHBoxLayout()
    button_row.setContentsMargins(0, 0, 0, 0)
    button_row.setSpacing(8)
    root.addLayout(button_row)
    add_slot = qt.QtWidgets.QPushButton("Add Slot")
    remove_slot = qt.QtWidgets.QPushButton("Remove Slot")
    validate = qt.QtWidgets.QPushButton("Validate Draft")
    for button in (add_slot, remove_slot, validate):
        button.setProperty("actionRailRole", "dialogButton")
        button_row.addWidget(button)
    button_row.addStretch(1)
    root.addWidget(status)

    panel._actionrail_current_draft = current_draft
    panel._actionrail_validate_draft = validate_draft

    template_combo.currentIndexChanged.connect(refresh_template)
    template_list.currentRowChanged.connect(template_combo.setCurrentIndex)
    add_slot.clicked.connect(
        lambda: _add_slot_row(
            qt,
            slots_layout,
            slot_rows,
            QuickCreateSlotInput(f"slot_{len(slot_rows) + 1}", "New", actions[0][0]),
            actions,
            icons,
        )
    )
    remove_slot.clicked.connect(lambda: _remove_last_slot_row(slot_rows, slots_layout))
    reset_values.clicked.connect(lambda: refresh_template(template_combo.currentIndex()))
    validate_top.clicked.connect(validate_draft)
    validate.clicked.connect(validate_draft)
    template_list.setCurrentRow(0)
    tabs.setCurrentIndex(1)
    apply_values(make_default_input())
    validate_draft()


def _add_slot_row(  # pragma: no cover
    qt: QtBinding,
    parent_layout: Any,
    rows: list[dict[str, Any]],
    slot: QuickCreateSlotInput,
    actions: tuple[tuple[str, str, str], ...],
    icons: tuple[Any, ...],
) -> None:
    row_widget = qt.QtWidgets.QWidget()
    row_layout = qt.QtWidgets.QHBoxLayout(row_widget)
    row_layout.setContentsMargins(0, 0, 0, 0)
    row_layout.setSpacing(6)

    slot_id = qt.QtWidgets.QLineEdit(slot.id)
    label = qt.QtWidgets.QLineEdit(slot.label)
    key_label = qt.QtWidgets.QLineEdit(slot.key_label)
    action = qt.QtWidgets.QComboBox()
    action.addItems(("", *(choice[0] for choice in actions)))
    _set_combo_text(action, slot.action)
    icon = qt.QtWidgets.QComboBox()
    icon.addItems(("", *(descriptor.id for descriptor in icons)))
    _set_combo_text(icon, slot.icon)

    for widget, (_label, width) in zip(
        (slot_id, label, action, key_label, icon),
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
            "action": action,
            "key_label": key_label,
            "icon": icon,
        }
    )


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


def _slot_input_from_row(row: dict[str, Any]) -> QuickCreateSlotInput:  # pragma: no cover
    return QuickCreateSlotInput(
        id=row["id"].text().strip(),
        label=row["label"].text().strip(),
        action=row["action"].currentText().strip(),
        key_label=row["key_label"].text().strip(),
        icon=row["icon"].currentText().strip(),
    )


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
    return f"Valid draft: {spec.id} ({len(spec.items)} slots)"


def _widget_to_slider_value(widget: Any, scale_factor: int) -> int:  # pragma: no cover
    return round(float(widget.value()) * scale_factor)


def _set_combo_text(combo: Any, text: str) -> None:  # pragma: no cover
    index = combo.findText(text)
    if index >= 0:
        combo.setCurrentIndex(index)


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
    background: {theme.cluster_background};
    color: {theme.button_color};
}}
QFrame#ActionRailQuickCreateSidebar,
QFrame#ActionRailQuickCreateContent {{
    background: rgba(42, 42, 46, 210);
    border: {theme.cluster_border_width}px solid {theme.cluster_border};
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
QLabel#ActionRailQuickCreateSliderLimit {{
    color: {theme.button_color};
    font-size: 11px;
    letter-spacing: 0px;
    min-width: 22px;
}}
QSlider::groove:horizontal {{
    height: 8px;
    background: #26262a;
    border: 1px solid {theme.cluster_border};
}}
QSlider::handle:horizontal {{
    width: 12px;
    margin: -4px 0;
    background: {theme.button_active_background};
    border: 1px solid {theme.button_hover_border};
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
