"""Qt binding loader for Maya-hosted ActionRail widgets."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class QtBinding:
    name: str
    QtCore: Any
    QtGui: Any
    QtWidgets: Any
    wrap_instance: Any


_BINDING: QtBinding | None = None


def load() -> QtBinding:
    """Load Maya's Qt binding, preferring PySide6 and falling back to PySide2."""

    global _BINDING
    if _BINDING is not None:
        return _BINDING

    try:
        from PySide6 import QtCore, QtGui, QtWidgets  # type: ignore[import-not-found]
        from shiboken6 import wrapInstance  # type: ignore[import-not-found]

        _BINDING = QtBinding("PySide6", QtCore, QtGui, QtWidgets, wrapInstance)
        return _BINDING
    except Exception:
        try:
            from PySide2 import QtCore, QtGui, QtWidgets  # type: ignore[import-not-found,no-redef]
            from shiboken2 import wrapInstance  # type: ignore[import-not-found,no-redef]

            _BINDING = QtBinding("PySide2", QtCore, QtGui, QtWidgets, wrapInstance)
            return _BINDING
        except Exception as py_side2_error:
            msg = (
                "ActionRail requires Maya's PySide6 or PySide2 Qt binding. "
                "Import actionrail outside Maya is supported, but showing overlays is not."
            )
            raise RuntimeError(msg) from py_side2_error


def reset_cache() -> None:
    """Clear the cached binding for tests or unusual Maya reload sessions."""

    global _BINDING
    _BINDING = None
