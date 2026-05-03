from __future__ import annotations

import sys
from types import ModuleType

import pytest

import actionrail.qt as qt


@pytest.fixture(autouse=True)
def reset_qt_cache() -> None:
    qt.reset_cache()
    yield
    qt.reset_cache()


def _fake_module(name: str) -> ModuleType:
    module = ModuleType(name)
    module.QtCore = object()
    module.QtGui = object()
    module.QtWidgets = object()
    return module


def test_load_prefers_pyside6_and_caches_binding(monkeypatch) -> None:
    pyside6 = _fake_module("PySide6")
    shiboken6 = ModuleType("shiboken6")
    shiboken6.wrapInstance = object()
    monkeypatch.setitem(sys.modules, "PySide6", pyside6)
    monkeypatch.setitem(sys.modules, "shiboken6", shiboken6)

    binding = qt.load()

    assert binding.name == "PySide6"
    assert qt.load() is binding


def test_load_falls_back_to_pyside2(monkeypatch) -> None:
    pyside2 = _fake_module("PySide2")
    shiboken2 = ModuleType("shiboken2")
    shiboken2.wrapInstance = object()
    monkeypatch.setitem(sys.modules, "PySide2", pyside2)
    monkeypatch.setitem(sys.modules, "shiboken2", shiboken2)
    monkeypatch.delitem(sys.modules, "PySide6", raising=False)
    monkeypatch.delitem(sys.modules, "shiboken6", raising=False)

    binding = qt.load()

    assert binding.name == "PySide2"
    assert binding.QtCore is pyside2.QtCore


def test_load_reports_missing_qt_bindings(monkeypatch) -> None:
    for name in ("PySide6", "shiboken6", "PySide2", "shiboken2"):
        monkeypatch.delitem(sys.modules, name, raising=False)

    with pytest.raises(RuntimeError, match="requires Maya's PySide6 or PySide2"):
        qt.load()
