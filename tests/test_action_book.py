from __future__ import annotations

import pytest

import actionrail
from actionrail.action_book import (
    ACTION_BOOK_MIME_TYPE,
    ActionBookEntry,
    action_book_action_id_from_mime_text,
    action_book_choices,
    action_book_entries,
    action_book_entry_by_id,
    action_book_mime_text,
    action_book_search,
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
            id="maya.modeling.center_pivot",
            label="Center Pivot",
            tooltip="Center pivot on current selection",
            category="Modeling",
            icon="maya.center_pivot",
            keywords=("center", "pivot", "modeling", "transform"),
        ),
        ActionBookEntry(
            id="maya.modeling.delete_history",
            label="Delete History",
            tooltip="Delete construction history on current selection",
            category="Modeling",
            icon="maya.objects",
            keywords=("delete", "history", "construction", "modeling", "cleanup"),
        ),
        ActionBookEntry(
            id="maya.modeling.freeze_transforms",
            label="Freeze Transforms",
            tooltip="Freeze transforms on current selection",
            category="Modeling",
            icon="maya.freeze_transform",
            keywords=("freeze", "transforms", "modeling", "zero", "apply"),
        ),
        ActionBookEntry(
            id="maya.selection.clear",
            label="Clear Selection",
            tooltip="Clear current selection",
            category="Selection",
            icon="maya.objects",
            keywords=("clear", "deselect", "selection"),
        ),
        ActionBookEntry(
            id="maya.tool.select",
            label="Select",
            tooltip="Select tool",
            category="Selection",
            icon="maya.objects",
            keywords=("select", "selection", "tool", "q"),
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
        ActionBookEntry(
            id="maya.view.frame_selection",
            label="Frame Selection",
            tooltip="Frame current selection",
            category="Viewport",
            icon="maya.camera",
            keywords=("frame", "fit", "selection", "camera", "viewport", "f"),
        ),
        ActionBookEntry(
            id="maya.display.toggle_grid",
            label="Toggle Grid",
            tooltip="Toggle viewport grid",
            category="Viewport",
            icon="maya.grid",
            keywords=("grid", "viewport", "display", "toggle"),
        ),
        ActionBookEntry(
            id="maya.view.toggle_isolate_selected",
            label="Toggle Isolate Selected",
            tooltip="Toggle isolate selected in the active viewport",
            category="Viewport",
            icon="maya.isolate_selected",
            keywords=("isolate", "selection", "viewport", "display", "toggle"),
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


def test_action_book_search_matches_categories_keywords_and_tooltips() -> None:
    assert [entry.id for entry in action_book_search("viewport toggle")] == [
        "maya.display.toggle_grid",
        "maya.view.toggle_isolate_selected",
    ]
    assert [entry.id for entry in action_book_search("freeze")] == [
        "maya.modeling.freeze_transforms"
    ]
    assert [entry.id for entry in action_book_search("deselect")] == [
        "maya.selection.clear",
    ]


def test_action_book_mime_payload_uses_stable_action_id() -> None:
    assert ACTION_BOOK_MIME_TYPE == "application/x-actionrail-action-id"
    assert action_book_mime_text(" maya.tool.move ") == "maya.tool.move"
    assert action_book_action_id_from_mime_text(" maya.tool.move ") == "maya.tool.move"

    with pytest.raises(ValueError, match="non-empty"):
        action_book_mime_text("")
    with pytest.raises(ValueError, match="empty"):
        action_book_action_id_from_mime_text("")


def test_public_api_exposes_action_book_entries() -> None:
    assert actionrail.ActionBookEntry is ActionBookEntry
    assert actionrail.ACTION_BOOK_MIME_TYPE == ACTION_BOOK_MIME_TYPE
    assert actionrail.action_book_search("freeze")[0].id == "maya.modeling.freeze_transforms"
    assert actionrail.action_book_entry_by_id("maya.tool.move").icon == "maya.move"
    assert actionrail.action_book_entry_by_id("maya.display.toggle_grid").icon == "maya.grid"
    assert actionrail.action_book_entry_by_id("maya.tool.select").icon == "maya.objects"
    assert actionrail.action_book_entry_by_id("maya.modeling.center_pivot").icon == (
        "maya.center_pivot"
    )
