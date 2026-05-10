from __future__ import annotations

import json
import sys
from pathlib import Path

__args__ = globals().get("__args__", {})

repo_scripts = __args__.get("repo_scripts")
if repo_scripts and repo_scripts not in sys.path:
    sys.path.insert(0, repo_scripts)

output_path = Path(
    __args__.get(
        "output_path",
        "C:/PROJECTS/GG/ScreenUI/.gg-maya-sessiond/screenshots/"
        "actionrail_dense_overlay.png",
    )
)
output_path.parent.mkdir(parents=True, exist_ok=True)

from maya import cmds  # noqa: E402
from PySide6 import QtCore, QtWidgets  # noqa: E402

import actionrail  # noqa: E402
from actionrail import overlay  # noqa: E402
from actionrail.widgets import (  # noqa: E402
    DENSE_ACTION_BAR_MIN_SLOTS,
    event_should_pass_through_to_maya,
)

app = QtWidgets.QApplication.instance()
if app is None:
    raise RuntimeError("Maya QApplication is not available.")

actionrail.hide_all()
app.processEvents()


def dense_spec(spec_id: str, offset: tuple[int, int]) -> actionrail.StackSpec:
    return actionrail.StackSpec(
        id=spec_id,
        layout=actionrail.RailLayout(
            anchor="viewport.bottom.center",
            orientation="horizontal",
            rows=5,
            columns=12,
            offset=offset,
            locked=True,
        ),
        items=tuple(
            actionrail.StackItem(
                type="button",
                id=f"{spec_id}.{index:02d}",
                label=str(index + 1),
                action="maya.tool.select",
                key_label=str((index % 10) or 10),
                active_when="maya.tool == 'select'",
            )
            for index in range(60)
        ),
    )


def widget_spec() -> actionrail.StackSpec:
    return actionrail.StackSpec(
        id="dense_widget_baseline",
        layout=actionrail.RailLayout(
            anchor="viewport.top.center",
            orientation="horizontal",
            rows=2,
            columns=10,
            offset=(0, 80),
            locked=True,
        ),
        items=tuple(
            actionrail.StackItem(
                type="button",
                id=f"dense_widget_baseline.{index:02d}",
                label=str(index + 1),
                action="maya.tool.select",
                key_label=str(index + 1),
            )
            for index in range(20)
        ),
    )


dense_a = actionrail.show_spec(dense_spec("dense_probe_a", (-230, -80)))
dense_b = actionrail.show_spec(dense_spec("dense_probe_b", (230, -80)))
baseline = actionrail.show_spec(widget_spec())
app.processEvents()
cmds.refresh(force=True)
app.processEvents()

dense_hosts = (dense_a, dense_b)
dense_slot_total = 0
for host in dense_hosts:
    widget = host.widget
    if widget.property("actionRailDense") != "true":
        raise AssertionError(f"{host.spec.id} did not use the dense canvas path.")
    buttons = widget.findChildren(QtWidgets.QPushButton)
    if buttons:
        raise AssertionError(f"{host.spec.id} created {len(buttons)} per-slot buttons.")
    dense_slot_total += len(getattr(widget, "_actionrail_slots", {}))

if dense_slot_total < 100:
    raise AssertionError(f"Dense probe rendered only {dense_slot_total} slots.")

baseline_buttons = baseline.widget.findChildren(QtWidgets.QPushButton)
if baseline.widget.property("actionRailDense") == "true" or len(baseline_buttons) != 20:
    raise AssertionError("Widget baseline did not stay on the QPushButton path.")

if len(overlay._PREDICATE_REFRESH_SCHEDULERS) != 1:
    raise AssertionError(
        f"Expected one shared predicate scheduler, got "
        f"{len(overlay._PREDICATE_REFRESH_SCHEDULERS)}."
    )

scheduler = next(iter(overlay._PREDICATE_REFRESH_SCHEDULERS.values()))
scheduler.refresh()
for host in dense_hosts:
    result = host.refresh_state()
    if result.needs_rebuild:
        raise AssertionError(f"{host.spec.id} requested a dense refresh rebuild.")


class FakeEvent:
    def __init__(self, *, event_type: int = 0, modifiers: int = 0, button: int = 0) -> None:
        self._event_type = event_type
        self._modifiers = modifiers
        self._button = button

    def type(self) -> int:
        return self._event_type

    def modifiers(self) -> int:
        return self._modifiers

    def button(self) -> int:
        return self._button

    def buttons(self) -> int:
        return self._button


pass_through_checks = {
    "wheel": event_should_pass_through_to_maya(
        FakeEvent(event_type=QtCore.QEvent.Wheel),
        qt=type("Qt", (), {"QtCore": QtCore}),
    ),
    "alt": event_should_pass_through_to_maya(
        FakeEvent(modifiers=QtCore.Qt.AltModifier),
        qt=type("Qt", (), {"QtCore": QtCore}),
    ),
    "middle": event_should_pass_through_to_maya(
        FakeEvent(button=QtCore.Qt.MiddleButton),
        qt=type("Qt", (), {"QtCore": QtCore}),
    ),
    "plain_left": event_should_pass_through_to_maya(
        FakeEvent(button=QtCore.Qt.LeftButton),
        qt=type("Qt", (), {"QtCore": QtCore}),
    ),
}
if not all(pass_through_checks[name] for name in ("wheel", "alt", "middle")):
    raise AssertionError(f"Navigation pass-through failed: {pass_through_checks}")
if pass_through_checks["plain_left"]:
    raise AssertionError(f"Plain slot click should stay with ActionRail: {pass_through_checks}")

pixmap = dense_a.widget.grab()
if pixmap.isNull():
    raise AssertionError("Dense overlay grab returned a null pixmap.")
if not pixmap.save(str(output_path)):
    raise AssertionError(f"Failed to save dense overlay screenshot to {output_path}")

report = {
    "dense_slot_total": dense_slot_total,
    "dense_canvas_count": len(dense_hosts),
    "baseline_button_count": len(baseline_buttons),
    "dense_threshold": DENSE_ACTION_BAR_MIN_SLOTS,
    "scheduler_count": len(overlay._PREDICATE_REFRESH_SCHEDULERS),
    "pass_through": pass_through_checks,
    "screenshot": str(output_path),
}
print(json.dumps(report, indent=2, sort_keys=True))
