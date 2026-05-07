from __future__ import annotations

import pytest

import actionrail
from actionrail.action_book import (
    ActionBookEntry,
    action_book_choices,
    action_book_entries,
    action_book_entry_by_id,
)
from actionrail.actions import Action, ActionRegistry, create_default_registry


def test_default_action_book_entries_have_spellbook_metadata() -> None:
    entries = action_book_entries(create_default_registry())

    assert entries == (
        ActionBookEntry(
            id="maya.anim.set_key",
            label="Set Key",
            tooltip="Set keyframe",
            category="Animation",
            icon="maya.set_key",
            keywords=("key", "keyframe", "animation", "set key", "s"),
        ),
        ActionBookEntry(
            id="maya.tool.move",
            label="Move",
            tooltip="Move tool",
            category="Transform",
            icon="maya.move",
            keywords=("move", "translate", "tool", "transform", "w"),
        ),
        ActionBookEntry(
            id="maya.tool.rotate",
            label="Rotate",
            tooltip="Rotate tool",
            category="Transform",
            icon="maya.rotate",
            keywords=("rotate", "tool", "transform", "e"),
        ),
        ActionBookEntry(
            id="maya.tool.scale",
            label="Scale",
            tooltip="Scale tool",
            category="Transform",
            icon="maya.scale",
            keywords=("scale", "tool", "transform", "r"),
        ),
        ActionBookEntry(
            id="maya.tool.translate",
            label="Translate",
            tooltip="Translate tool",
            category="Transform",
            icon="maya.move",
            keywords=("translate", "move", "tool", "transform", "w"),
        ),
    )


def test_action_book_wraps_custom_registry_actions() -> None:
    registry = ActionRegistry()
    registry.register(Action("studio.publish", "Publish", lambda: None, "Studio publish"))

    assert action_book_entries(registry) == (
        ActionBookEntry(
            id="studio.publish",
            label="Publish",
            tooltip="Studio publish",
            category="Custom",
        ),
    )


def test_action_book_choices_keep_quick_create_tuple_contract() -> None:
    registry = ActionRegistry()
    registry.register(Action("custom.z", "Zeta", lambda: None, "Last"))
    registry.register(Action("custom.a", "Alpha", lambda: None, "First"))

    assert action_book_choices(registry) == (
        ("custom.a", "Alpha", "First"),
        ("custom.z", "Zeta", "Last"),
    )


def test_action_book_entry_by_id_reports_unknown_actions() -> None:
    with pytest.raises(KeyError, match="missing.action"):
        action_book_entry_by_id("missing.action")


def test_public_api_exposes_action_book_entries() -> None:
    assert actionrail.ActionBookEntry is ActionBookEntry
    assert actionrail.action_book_entry_by_id("maya.tool.move").icon == "maya.move"
    assert any(entry.id == "maya.anim.set_key" for entry in actionrail.action_book_entries())
