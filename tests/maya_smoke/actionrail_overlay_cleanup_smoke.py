from __future__ import annotations

import json
import sys

__args__ = globals().get("__args__", {})

repo_scripts = __args__.get("repo_scripts")
if repo_scripts and repo_scripts not in sys.path:
    sys.path.insert(0, repo_scripts)

from maya import cmds  # noqa: E402
from PySide6 import QtCore, QtWidgets  # noqa: E402
from shiboken6 import getCppPointer, isValid  # noqa: E402

import actionrail  # noqa: E402
from actionrail.overlay import _anchored_position  # noqa: E402
from actionrail.runtime import active_overlay_ids  # noqa: E402

app = QtWidgets.QApplication.instance()
if app is None:
    raise RuntimeError("Maya QApplication is not available.")


def geometry(widget: QtWidgets.QWidget) -> list[int]:
    rect = widget.geometry()
    return [rect.x(), rect.y(), rect.width(), rect.height()]


cmds.file(new=True, force=True)

first_host = actionrail.show_example("transform_stack")
app.processEvents()
second_host = actionrail.show_example("transform_stack")
app.processEvents()
cmds.refresh(force=True)
app.processEvents()

parent = second_host.parent
expected_x, expected_y = _anchored_position(
    second_host.spec.anchor,
    parent.rect().width(),
    parent.rect().height(),
    second_host.widget.width(),
    second_host.widget.height(),
    second_host.margin,
)
expected_x += second_host.spec.layout.offset[0]
expected_y += second_host.spec.layout.offset[1]
expected_global_position = parent.mapToGlobal(QtCore.QPoint(expected_x, expected_y))
seen_widgets: set[int] = set()
overlay_widgets = []
for widget in app.allWidgets():
    if not isValid(widget):
        continue
    object_name = widget.objectName()
    if not object_name.startswith("ActionRailViewportOverlay"):
        continue
    identifier = int(getCppPointer(widget)[0])
    if identifier in seen_widgets:
        continue
    seen_widgets.add(identifier)
    overlay_widgets.append(object_name)
buttons = second_host.widget.findChildren(QtWidgets.QPushButton)

result = {
    "active_ids": active_overlay_ids(),
    "button_count": len(buttons),
    "expected_global_position": [expected_global_position.x(), expected_global_position.y()],
    "first_widget_alive": bool(first_host.widget is not None),
    "overlay_widgets": sorted(overlay_widgets),
    "panel": second_host.panel,
    "widget_geometry": geometry(second_host.widget),
    "widget_parent": second_host.widget.parentWidget().objectName(),
    "widget_visible": bool(second_host.widget.isVisible()),
}

expected_widgets = [
    "ActionRailViewportOverlay_transform_stack",
]
if result["active_ids"] != ("transform_stack",):
    raise AssertionError(f"Expected one active overlay id, got {result['active_ids']!r}")
if result["button_count"] != 5:
    raise AssertionError(f"Expected 5 buttons, got {result['button_count']!r}")
if result["first_widget_alive"]:
    raise AssertionError("First show_example host still owns a widget after replacement.")
if result["overlay_widgets"] != expected_widgets:
    raise AssertionError(f"Expected one rail widget, got {overlay_widgets!r}")
if result["widget_geometry"][:2] == [0, 0]:
    raise AssertionError(f"Rail is still painted at viewport origin: {result['widget_geometry']!r}")
if result["widget_geometry"][:2] != result["expected_global_position"]:
    raise AssertionError(
        "Rail is not positioned at the resolved viewport anchor: "
        f"{result['widget_geometry']!r} vs {result['expected_global_position']!r}"
    )
if result["widget_parent"] == second_host.parent.objectName():
    raise AssertionError("Rail is still parented directly under the viewport widget.")
if not result["widget_visible"]:
    raise AssertionError("Rail widget is not visible.")

print(json.dumps(result, sort_keys=True))
