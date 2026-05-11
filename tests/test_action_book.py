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


def test_default_action_book_entries_have_picker_metadata() -> None:
    entries = action_book_entries(create_default_registry())
    entries_by_id = {entry.id: entry for entry in entries}

    assert len(entries) == 33
    assert entries == tuple(sorted(entries, key=lambda entry: (entry.category, entry.label)))
    assert entries_by_id["maya.anim.set_key"] == ActionBookEntry(
        id="maya.anim.set_key",
        label="Set Key",
        tooltip="Set keyframe",
        category="Animation",
        icon="maya.set_key",
        keywords=("key", "keyframe", "animation", "set key", "s"),
    )
    assert entries_by_id["maya.modeling.poly_cube"] == ActionBookEntry(
        id="maya.modeling.poly_cube",
        label="Polygon Cube",
        tooltip="Create a polygon cube",
        category="Modeling Primitives",
        icon="maya.poly_cube",
        keywords=("polygon", "poly", "cube", "primitive", "modeling", "shelf"),
    )
    assert entries_by_id["maya.modeling.extrude"] == ActionBookEntry(
        id="maya.modeling.extrude",
        label="Extrude",
        tooltip="Extrude selected polygon components",
        category="Modeling",
        icon="maya.extrude",
        keywords=("extrude", "face", "edge", "polygon", "modeling", "shelf"),
    )
    assert entries_by_id["maya.modeling.quad_draw"] == ActionBookEntry(
        id="maya.modeling.quad_draw",
        label="Quad Draw Tool",
        tooltip="Draw quad topology on live objects",
        category="Modeling Tools",
        icon="maya.quad_draw",
        keywords=("quad", "draw", "retopology", "topology", "modeling", "shelf"),
    )
    assert entries_by_id["maya.view.toggle_isolate_selected"].icon == "maya.isolate_selected"


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
    assert [entry.id for entry in action_book_search("shelf topology")] == [
        "maya.modeling.remesh",
        "maya.modeling.retopologize",
        "maya.modeling.quad_draw",
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
