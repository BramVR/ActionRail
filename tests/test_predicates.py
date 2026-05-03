from __future__ import annotations

import ast

import pytest

from actionrail.actions import create_default_registry
from actionrail.predicates import (
    PredicateContext,
    _PredicateEvaluator,
    availability_blocking_targets,
    availability_targets,
    evaluate_predicate,
    missing_availability_targets,
)
from actionrail.spec import StackItem
from actionrail.state import MayaStateSnapshot


class FakeCmds:
    def setKeyframe(self) -> None:
        return None

    def pluginInfo(self, plugin_name: str, *, query: bool = False, loaded: bool = False) -> bool:  # noqa: N802
        return plugin_name == "loadedPlugin" and query and loaded


class CommandInfoCmds:
    def commandInfo(self, command_name: str, *, exists: bool = False) -> bool:  # noqa: N802
        return command_name == "fallbackCommand" and exists


class HelpCmds:
    def help(self, command_name: str) -> str:
        if command_name == "helpCommand":
            return "Synopsis: helpCommand"
        raise RuntimeError("No object matches name")


class BrokenPluginCmds:
    def pluginInfo(self, plugin_name: str, *, query: bool = False, loaded: bool = False) -> bool:  # noqa: N802
        raise RuntimeError("pluginInfo unavailable")


class MelFallbackCmds:
    def commandInfo(self, command_name: str, *, exists: bool = False) -> bool:  # noqa: N802
        raise RuntimeError("commandInfo unavailable")

    def help(self, command_name: str) -> str:
        raise RuntimeError("help unavailable")


def test_predicates_evaluate_literals_and_boolean_operators() -> None:
    assert evaluate_predicate("") is True
    assert evaluate_predicate("true") is True
    assert evaluate_predicate("false") is False
    assert evaluate_predicate("selection.count > 0 and not playback.playing") is False
    assert evaluate_predicate("false or true") is True


def test_predicates_evaluate_selection_tool_and_active_context() -> None:
    context = PredicateContext(
        state=MayaStateSnapshot(
            current_tool="scaleSuperContext",
            selection_count=2,
            active_panel="modelPanel4",
            active_camera="persp",
        )
    )

    assert evaluate_predicate("selection.count > 0", context) is True
    assert evaluate_predicate("maya.tool == scale", context) is True
    assert evaluate_predicate("tool != rotate", context) is True
    assert evaluate_predicate("current_tool == 'scaleSuperContext'", context) is True
    assert evaluate_predicate("active.panel == 'modelPanel4'", context) is True
    assert evaluate_predicate("active.camera == 'persp'", context) is True
    assert evaluate_predicate("playback.playing == false", context) is True
    assert evaluate_predicate("selection.count >= 2", context) is True
    assert evaluate_predicate("selection.count < 3", context) is True
    assert evaluate_predicate("selection.count <= 2", context) is True


def test_predicates_evaluate_action_command_and_plugin_availability() -> None:
    item = StackItem(type="button", label="K", action="maya.anim.set_key")
    context = PredicateContext(
        registry=create_default_registry(FakeCmds()),
        item=item,
        cmds_module=FakeCmds(),
    )

    assert evaluate_predicate("action.exists", context) is True
    assert evaluate_predicate("action.exists()", context) is True
    assert evaluate_predicate("command.exists('setKeyframe')", context) is True
    assert evaluate_predicate("plugin.exists('loadedPlugin')", context) is True
    assert evaluate_predicate("plugin.exists('missingPlugin')", context) is False


def test_predicates_default_missing_context_values_are_falsey() -> None:
    assert evaluate_predicate("selection.count == 0") is True
    assert evaluate_predicate("current_tool == ''") is True
    assert evaluate_predicate("maya.tool == ''") is True
    assert evaluate_predicate("active.panel == ''") is True
    assert evaluate_predicate("active.camera == ''") is True
    assert evaluate_predicate("playback.playing == false") is True
    assert evaluate_predicate("action.exists") is False
    assert evaluate_predicate("command.exists('setKeyframe')") is False
    assert evaluate_predicate("plugin.exists('loadedPlugin')") is False


def test_predicates_use_command_info_fallback_when_available() -> None:
    context = PredicateContext(cmds_module=CommandInfoCmds())

    assert evaluate_predicate("command.exists('fallbackCommand')", context) is True
    assert evaluate_predicate("command.exists('missingCommand')", context) is False


def test_predicates_use_help_command_fallback_when_available() -> None:
    context = PredicateContext(cmds_module=HelpCmds())

    assert evaluate_predicate("command.exists('helpCommand')", context) is True
    assert evaluate_predicate("command.exists('missingCommand')", context) is False


def test_predicates_use_mel_what_is_fallback(monkeypatch) -> None:
    class FakeMel:
        def eval(self, expression: str) -> str:
            if 'knownCommand' in expression:
                return "Mel procedure found in: scripts"
            if 'raisingCommand' in expression:
                raise RuntimeError("whatIs failed")
            return "Unknown"

    import sys
    from types import ModuleType

    maya_module = ModuleType("maya")
    monkeypatch.setitem(sys.modules, "maya", maya_module)
    monkeypatch.setitem(sys.modules, "maya.mel", FakeMel())
    context = PredicateContext(cmds_module=MelFallbackCmds())

    assert evaluate_predicate("command.exists('knownCommand')", context) is True
    assert evaluate_predicate("command.exists('missingCommand')", context) is False
    assert evaluate_predicate("command.exists('raisingCommand')", context) is False


def test_availability_helpers_report_targets_and_blocking_missing_targets() -> None:
    predicate = "command.exists('missingCommand') and plugin.exists('loadedPlugin')"
    context = PredicateContext(cmds_module=FakeCmds())

    assert availability_targets(predicate) == (
        ("command", "missingCommand"),
        ("plugin", "loadedPlugin"),
    )
    assert missing_availability_targets(predicate, FakeCmds()) == (("command", "missingCommand"),)
    assert missing_availability_targets(predicate, None) == ()
    assert availability_blocking_targets(predicate, context) == (("command", "missingCommand"),)


def test_availability_helpers_ignore_invalid_and_non_blocking_targets() -> None:
    assert availability_targets("not valid python") == ()
    assert availability_targets("factory().exists('x')") == ()
    assert availability_targets("other.exists('x')") == ()
    assert availability_targets("command.exists(dynamicName)") == ()

    context = PredicateContext(cmds_module=FakeCmds())

    assert availability_blocking_targets("command.exists('missing') and false", context) == ()
    assert availability_blocking_targets("command.exists('setKeyframe')", context) == ()


def test_predicates_honor_availability_overrides() -> None:
    context = PredicateContext(
        cmds_module=FakeCmds(),
        availability_overrides={
            ("command", "missingCommand"): True,
            ("plugin", "loadedPlugin"): False,
        },
    )

    assert evaluate_predicate("command.exists('missingCommand')", context) is True
    assert evaluate_predicate("plugin.exists('loadedPlugin')", context) is False


def test_predicates_handle_plugin_info_exceptions() -> None:
    context = PredicateContext(cmds_module=BrokenPluginCmds())

    assert evaluate_predicate("plugin.exists('broken')", context) is False


def test_predicates_reject_unsafe_or_unsupported_syntax() -> None:
    with pytest.raises(ValueError, match="Invalid ActionRail predicate"):
        evaluate_predicate("selection.count >")

    with pytest.raises(ValueError, match="Unsupported ActionRail predicate"):
        evaluate_predicate("__import__('os').system('echo nope')")

    with pytest.raises(ValueError, match="Unsupported ActionRail predicate"):
        evaluate_predicate("command.exists(name='setKeyframe')")

    with pytest.raises(ValueError, match="Unsupported ActionRail predicate"):
        evaluate_predicate("command.exists('setKeyframe', 'extra')")

    with pytest.raises(ValueError, match="Unsupported ActionRail predicate"):
        evaluate_predicate("+true")

    with pytest.raises(ValueError, match="Unsupported ActionRail predicate"):
        evaluate_predicate("b'bytes'")

    with pytest.raises(ValueError, match="Unsupported ActionRail predicate"):
        evaluate_predicate("[1, 2, 3]")

    with pytest.raises(ValueError, match="Unsupported ActionRail predicate comparison"):
        evaluate_predicate("'a' in 'abc'")

    with pytest.raises(ValueError, match="Unsupported ActionRail predicate callable"):
        evaluate_predicate("('command').exists('setKeyframe')")


def test_predicate_evaluator_rejects_unknown_bool_operator_directly() -> None:
    evaluator = _PredicateEvaluator(PredicateContext(), "manual")
    node = ast.BoolOp(op=ast.Not(), values=[ast.Constant(True)])

    with pytest.raises(ValueError, match="Unsupported ActionRail predicate"):
        evaluator.visit_BoolOp(node)
