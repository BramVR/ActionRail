from __future__ import annotations

import pytest

from actionrail.actions import create_default_registry
from actionrail.predicates import PredicateContext, evaluate_predicate
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


def test_predicates_evaluate_literals_and_boolean_operators() -> None:
    assert evaluate_predicate("") is True
    assert evaluate_predicate("true") is True
    assert evaluate_predicate("false") is False
    assert evaluate_predicate("selection.count > 0 and not playback.playing") is False


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


def test_predicates_use_command_info_fallback_when_available() -> None:
    context = PredicateContext(cmds_module=CommandInfoCmds())

    assert evaluate_predicate("command.exists('fallbackCommand')", context) is True
    assert evaluate_predicate("command.exists('missingCommand')", context) is False


def test_predicates_use_help_command_fallback_when_available() -> None:
    context = PredicateContext(cmds_module=HelpCmds())

    assert evaluate_predicate("command.exists('helpCommand')", context) is True
    assert evaluate_predicate("command.exists('missingCommand')", context) is False


def test_predicates_reject_unsafe_or_unsupported_syntax() -> None:
    with pytest.raises(ValueError, match="Unsupported ActionRail predicate"):
        evaluate_predicate("__import__('os').system('echo nope')")
