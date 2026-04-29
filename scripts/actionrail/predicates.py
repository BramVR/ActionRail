"""Safe declarative predicate evaluation for ActionRail presets."""

from __future__ import annotations

import ast
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .actions import MOVE_CONTEXT, ROTATE_CONTEXT, SCALE_CONTEXT, ActionRegistry
from .spec import StackItem
from .state import MayaStateSnapshot


@dataclass(frozen=True)
class PredicateContext:
    """Data available to preset predicate expressions."""

    state: MayaStateSnapshot | None = None
    registry: ActionRegistry | None = None
    item: StackItem | None = None
    cmds_module: Any | None = None
    availability_overrides: Mapping[tuple[str, str], bool] | None = None


def evaluate_predicate(predicate: str, context: PredicateContext | None = None) -> bool:
    """Evaluate a small safe boolean expression.

    Supported expressions are literals, dotted state names, boolean operators,
    comparisons, and whitelisted availability checks such as
    ``command.exists("setKeyframe")``.
    """

    expression = predicate.strip()
    if not expression:
        return True

    lowered = expression.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False

    evaluator = _PredicateEvaluator(context or PredicateContext(), expression)
    try:
        parsed = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        msg = f"Invalid ActionRail predicate: {predicate}"
        raise ValueError(msg) from exc
    return bool(evaluator.visit(parsed.body))


def availability_targets(predicate: str) -> tuple[tuple[str, str], ...]:
    """Return command/plugin availability targets referenced by a predicate."""

    try:
        parsed = ast.parse(predicate, mode="eval")
    except SyntaxError:
        return ()

    targets: list[tuple[str, str]] = []
    for node in ast.walk(parsed):
        if not isinstance(node, ast.Call) or len(node.args) != 1:
            continue
        try:
            name = _dotted_name(node.func)
        except ValueError:
            continue
        if name not in {"command.exists", "plugin.exists"}:
            continue

        arg = node.args[0]
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            targets.append(("command" if name == "command.exists" else "plugin", arg.value))
    return tuple(targets)


def missing_availability_targets(
    predicate: str,
    cmds_module: Any | None,
) -> tuple[tuple[str, str], ...]:
    """Return unavailable command/plugin targets referenced by a predicate."""

    if cmds_module is None:
        return ()

    missing: list[tuple[str, str]] = []
    for kind, target in availability_targets(predicate):
        if (
            kind == "command"
            and not _command_exists(cmds_module, target)
            or kind == "plugin"
            and not _plugin_exists(cmds_module, target)
        ):
            missing.append((kind, target))
    return tuple(missing)


def availability_blocking_targets(
    predicate: str,
    context: PredicateContext | None = None,
) -> tuple[tuple[str, str], ...]:
    """Return missing availability targets that make a predicate fail."""

    predicate_context = context or PredicateContext()
    missing = missing_availability_targets(predicate, predicate_context.cmds_module)
    if not missing or evaluate_predicate(predicate, predicate_context):
        return ()

    repaired_context = PredicateContext(
        state=predicate_context.state,
        registry=predicate_context.registry,
        item=predicate_context.item,
        cmds_module=predicate_context.cmds_module,
        availability_overrides=dict.fromkeys(missing, True),
    )
    if not evaluate_predicate(predicate, repaired_context):
        return ()
    return missing


class _PredicateEvaluator(ast.NodeVisitor):
    def __init__(self, context: PredicateContext, source: str) -> None:
        self.context = context
        self.source = source

    def visit_BoolOp(self, node: ast.BoolOp) -> bool:  # noqa: N802
        values = [bool(self.visit(value)) for value in node.values]
        if isinstance(node.op, ast.And):
            return all(values)
        if isinstance(node.op, ast.Or):
            return any(values)
        self._unsupported(node)

    def visit_UnaryOp(self, node: ast.UnaryOp) -> bool:  # noqa: N802
        if isinstance(node.op, ast.Not):
            return not bool(self.visit(node.operand))
        self._unsupported(node)

    def visit_Compare(self, node: ast.Compare) -> bool:  # noqa: N802
        left = self.visit(node.left)
        for operator, comparator in zip(node.ops, node.comparators, strict=True):
            right = self.visit(comparator)
            if not _compare(left, operator, right):
                return False
            left = right
        return True

    def visit_Call(self, node: ast.Call) -> bool:  # noqa: N802
        if node.keywords:
            self._unsupported(node)

        name = _dotted_name(node.func)
        args = [self.visit(arg) for arg in node.args]
        if name == "command.exists" and len(args) == 1:
            override = self._availability_override("command", str(args[0]))
            if override is not None:
                return override
            return _command_exists(self.context.cmds_module, str(args[0]))
        if name == "plugin.exists" and len(args) == 1:
            override = self._availability_override("plugin", str(args[0]))
            if override is not None:
                return override
            return _plugin_exists(self.context.cmds_module, str(args[0]))
        if name == "action.exists" and not args:
            return _action_exists(self.context.registry, self.context.item)
        self._unsupported(node)

    def visit_Constant(self, node: ast.Constant) -> Any:  # noqa: N802
        if isinstance(node.value, str | int | float | bool) or node.value is None:
            return node.value
        self._unsupported(node)

    def visit_Name(self, node: ast.Name) -> Any:  # noqa: N802
        return self._resolve_name(node.id)

    def visit_Attribute(self, node: ast.Attribute) -> Any:  # noqa: N802
        return self._resolve_name(_dotted_name(node))

    def generic_visit(self, node: ast.AST) -> Any:
        self._unsupported(node)

    def _resolve_name(self, name: str) -> Any:
        lowered = name.lower()
        if lowered == "true":
            return True
        if lowered == "false":
            return False
        if name == "selection.count":
            return self.context.state.selection_count if self.context.state else 0
        if name == "current_tool":
            return self.context.state.current_tool if self.context.state else ""
        if name in {"maya.tool", "tool"}:
            current_tool = self.context.state.current_tool if self.context.state else ""
            return _tool_alias(current_tool)
        if name == "active.panel":
            return self.context.state.active_panel if self.context.state else ""
        if name == "active.camera":
            return self.context.state.active_camera if self.context.state else ""
        if name == "playback.playing":
            return self.context.state.playback_playing if self.context.state else False
        if name == "action.exists":
            return _action_exists(self.context.registry, self.context.item)

        return name

    def _unsupported(self, node: ast.AST) -> None:
        msg = f"Unsupported ActionRail predicate syntax in '{self.source}': {type(node).__name__}"
        raise ValueError(msg)

    def _availability_override(self, kind: str, target: str) -> bool | None:
        overrides = self.context.availability_overrides
        if overrides is None:
            return None
        return overrides.get((kind, target))


def _dotted_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _dotted_name(node.value)
        return f"{parent}.{node.attr}"
    msg = f"Unsupported ActionRail predicate callable: {type(node).__name__}"
    raise ValueError(msg)


def _compare(left: Any, operator: ast.cmpop, right: Any) -> bool:
    if isinstance(operator, ast.Eq):
        return left == right
    if isinstance(operator, ast.NotEq):
        return left != right
    if isinstance(operator, ast.Gt):
        return left > right
    if isinstance(operator, ast.GtE):
        return left >= right
    if isinstance(operator, ast.Lt):
        return left < right
    if isinstance(operator, ast.LtE):
        return left <= right
    msg = f"Unsupported ActionRail predicate comparison: {type(operator).__name__}"
    raise ValueError(msg)


def _tool_alias(context_name: str) -> str:
    aliases = {
        MOVE_CONTEXT: "move",
        ROTATE_CONTEXT: "rotate",
        SCALE_CONTEXT: "scale",
    }
    return aliases.get(context_name, context_name)


def _action_exists(registry: ActionRegistry | None, item: StackItem | None) -> bool:
    if registry is None or item is None or not item.action:
        return False
    return item.action in registry.ids()


def _command_exists(cmds_module: Any | None, command_name: str) -> bool:
    if cmds_module is None:
        return False
    if hasattr(cmds_module, command_name):
        return True

    command_info = getattr(cmds_module, "commandInfo", None)
    if command_info is not None:
        try:
            if bool(command_info(command_name, exists=True)):
                return True
        except Exception:
            pass

    help_command = getattr(cmds_module, "help", None)
    if help_command is not None:
        try:
            help_text = help_command(command_name)
            if isinstance(help_text, str) and help_text:
                return True
        except Exception:
            pass

    try:
        import maya.mel as mel  # type: ignore[import-not-found]
    except Exception:
        return False

    escaped_name = command_name.replace("\\", "\\\\").replace('"', '\\"')
    try:
        what_is = mel.eval(f'whatIs "{escaped_name}"')
        return isinstance(what_is, str) and not what_is.lower().startswith("unknown")
    except Exception:
        return False


def _plugin_exists(cmds_module: Any | None, plugin_name: str) -> bool:
    if cmds_module is None:
        return False
    try:
        return bool(cmds_module.pluginInfo(plugin_name, query=True, loaded=True))
    except Exception:
        return False
