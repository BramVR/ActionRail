from __future__ import annotations


def test_package_imports_without_maya_or_qt() -> None:
    import actionrail

    assert actionrail.__version__ == "0.1.0"
    assert callable(actionrail.about)
    assert callable(actionrail.show_example)
    assert callable(actionrail.hide_all)
    assert callable(actionrail.reload)
    assert callable(actionrail.collect_diagnostics)
    assert callable(actionrail.last_report)
    assert callable(actionrail.show_last_report)
    assert callable(actionrail.safe_start)
