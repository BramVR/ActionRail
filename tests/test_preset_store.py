from __future__ import annotations

import json

import pytest

from actionrail.authoring import DraftRail, DraftSlot, save_user_preset
from actionrail.preset_store import (
    PresetEntry,
    PresetStore,
    builtin_user_override_id,
    preset_entries,
    preset_ids,
    resolve_preset,
)
from actionrail.spec import RailLayout, StackItem, StackSpec


def test_preset_store_lists_builtin_and_user_presets(tmp_path) -> None:
    saved_path = save_user_preset(
        DraftRail(
            id="artist_tools",
            slots=(DraftSlot(id="move", label="M", action="maya.tool.move"),),
        ),
        preset_dir=tmp_path,
    )

    store = PresetStore(user_preset_dir=tmp_path)

    assert store.user_preset_dir == tmp_path
    assert store.builtin_ids() == ("horizontal_tools", "maya_tools", "transform_stack")
    assert store.user_ids() == ("artist_tools",)
    assert store.ids() == (
        "artist_tools",
        "horizontal_tools",
        "maya_tools",
        "transform_stack",
    )
    assert PresetEntry("transform_stack", "builtin") in store.entries()
    assert PresetEntry("artist_tools", "user", saved_path) in store.entries()
    assert store.entry("artist_tools") == PresetEntry("artist_tools", "user", saved_path)


def test_resolve_preset_loads_builtin_and_user_presets(tmp_path) -> None:
    save_user_preset(
        DraftRail(
            id="artist_tools",
            slots=(DraftSlot(id="key", label="K", action="maya.anim.set_key"),),
        ),
        preset_dir=tmp_path,
    )

    builtin = resolve_preset("transform_stack", user_preset_dir=tmp_path)
    user = resolve_preset("artist_tools", user_preset_dir=tmp_path)

    assert builtin.id == "transform_stack"
    assert user.id == "artist_tools"
    assert user.items[0].id == "artist_tools.key"
    assert preset_ids(user_preset_dir=tmp_path)[0] == "artist_tools"
    assert preset_entries(user_preset_dir=tmp_path)[-1].id == "artist_tools"


def test_resolve_builtin_preset_applies_user_override_layer(tmp_path) -> None:
    override_id = builtin_user_override_id("transform_stack")
    save_user_preset(
        StackSpec(
            id=override_id,
            layout=RailLayout(
                anchor="viewport.left.top",
                offset=(88, 99),
                locked=False,
            ),
            items=(
                StackItem(
                    type="button",
                    id=f"{override_id}.move",
                    label="Move",
                    action="maya.tool.move",
                ),
            ),
        ),
        preset_dir=tmp_path,
    )

    store = PresetStore(user_preset_dir=tmp_path)
    spec = store.load("transform_stack")

    assert store.entry("transform_stack") == PresetEntry(
        "transform_stack",
        "builtin_override",
        tmp_path / "transform_stack_user_override.json",
    )
    assert spec.id == "transform_stack"
    assert spec.layout.offset == (88, 99)
    assert spec.layout.locked is False
    assert spec.items[0].id == "transform_stack.move"
    assert resolve_preset(override_id, user_preset_dir=tmp_path).id == override_id


def test_broken_builtin_override_does_not_block_bundled_preset(tmp_path) -> None:
    (tmp_path / "transform_stack_user_override.json").write_text(
        json.dumps({"id": "different", "layout": {}, "items": []}),
        encoding="utf-8",
    )

    store = PresetStore(user_preset_dir=tmp_path)
    spec = store.load("transform_stack")

    assert store.entry("transform_stack") == PresetEntry("transform_stack", "builtin")
    assert spec.id == "transform_stack"
    assert store.user_entries()[0].error


def test_preset_store_reports_unknown_preset(tmp_path) -> None:
    store = PresetStore(user_preset_dir=tmp_path)

    with pytest.raises(KeyError, match="Unknown ActionRail preset"):
        store.entry("missing")


def test_preset_store_builtin_precedence_does_not_hide_user_entry_validation(tmp_path) -> None:
    shadow_path = tmp_path / "transform_stack.json"
    shadow_path.write_text(
        json.dumps(
            {
                "id": "transform_stack",
                "layout": {"anchor": "viewport.left.center"},
                "items": [
                    {
                        "type": "button",
                        "id": "transform_stack.move",
                        "label": "M",
                        "action": "maya.tool.move",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    store = PresetStore(user_preset_dir=tmp_path)

    assert store.entry("transform_stack") == PresetEntry("transform_stack", "builtin")
    assert store.load("transform_stack").id == "transform_stack"
    user_entry = store.user_entries()[0]

    with pytest.raises(ValueError, match="shadow a locked built-in"):
        store.load_entry(user_entry)


def test_preset_store_marks_broken_user_entries_without_listing_ids(tmp_path) -> None:
    (tmp_path / "bad id!.json").write_text(
        json.dumps(
            {
                "id": "bad id!",
                "layout": {"anchor": "viewport.left.center"},
                "items": [{"type": "button", "label": "B"}],
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "mismatch.json").write_text(
        json.dumps({"id": "different", "layout": {}, "items": []}),
        encoding="utf-8",
    )

    store = PresetStore(user_preset_dir=tmp_path)
    entries = {entry.id: entry for entry in store.user_entries()}

    assert store.user_ids() == ()
    assert "bad id!" not in store.ids()
    assert "mismatch" not in store.ids()
    assert entries["bad id!"].error
    assert entries["mismatch"].error
    with pytest.raises(KeyError, match="Unknown ActionRail preset"):
        store.load("bad id!")
    with pytest.raises(KeyError, match="Unknown ActionRail preset"):
        store.load("mismatch")
