from __future__ import annotations

import json

import pytest

from actionrail.authoring import (
    DraftRail,
    DraftSlot,
    _as_valid_spec,
    _slot_item_id,
    build_draft_spec,
    load_user_preset,
    save_user_preset,
    spec_to_payload,
    user_preset_dir,
    user_preset_files,
    user_preset_ids,
    validate_preset_id,
)
from actionrail.spec import RailLayout, StackItem, StackSpec


def test_build_draft_save_reload_user_preset_without_touching_builtins(tmp_path) -> None:
    draft = DraftRail(
        id="artist_tools",
        layout=RailLayout(
            anchor="viewport.bottom.center",
            orientation="horizontal",
            rows=1,
            columns=2,
            offset=(0, -32),
            opacity=0.9,
        ),
        slots=(
            DraftSlot(
                id="move",
                label="M",
                action="maya.tool.move",
                tooltip="Move tool",
                key_label="W",
                active_when="maya.tool == move",
                icon="actionrail.move",
            ),
            DraftSlot(
                id="artist_tools.set_key",
                label="K",
                action="maya.anim.set_key",
                tone="teal",
            ),
        ),
    )

    spec = build_draft_spec(draft)
    saved_path = save_user_preset(draft, preset_dir=tmp_path)
    reloaded = load_user_preset("artist_tools", preset_dir=tmp_path)

    assert saved_path == tmp_path / "artist_tools.json"
    assert spec == reloaded
    assert reloaded.items[0].id == "artist_tools.move"
    assert reloaded.items[1].id == "artist_tools.set_key"
    assert reloaded.items[0].key_label == "W"
    assert reloaded.items[0].icon == "actionrail.move"
    assert user_preset_ids(preset_dir=tmp_path) == ("artist_tools",)
    assert user_preset_files(preset_dir=tmp_path) == (saved_path,)
    assert not (tmp_path / "transform_stack.json").exists()


def test_save_user_preset_accepts_stack_spec_and_canonicalizes_payload(tmp_path) -> None:
    spec = StackSpec(
        id="manual_spec",
        layout=RailLayout(anchor="viewport.left.center", locked=True),
        items=(
            StackItem(
                type="button",
                id="manual_spec.key",
                label="K",
                action="maya.anim.set_key",
                tooltip="Set key",
            ),
            StackItem(type="spacer", id="manual_spec.gap", size=4),
        ),
    )

    saved_path = save_user_preset(spec, preset_dir=tmp_path)
    payload = json.loads(saved_path.read_text(encoding="utf-8"))

    assert payload == spec_to_payload(spec)
    assert load_user_preset("manual_spec", preset_dir=tmp_path) == spec


def test_user_preset_storage_rejects_builtin_overwrite_and_bad_ids(tmp_path) -> None:
    with pytest.raises(ValueError, match="locked built-in"):
        save_user_preset(
            DraftRail(
                id="transform_stack",
                slots=(DraftSlot(id="move", label="M", action="maya.tool.move"),),
            ),
            preset_dir=tmp_path,
        )

    with pytest.raises(ValueError, match="preset ids"):
        validate_preset_id("../bad")

    with pytest.raises(ValueError, match="preset ids"):
        build_draft_spec(DraftRail(id="bad id", slots=(DraftSlot(id="move", label="M"),)))

    with pytest.raises(ValueError, match="preset ids"):
        build_draft_spec(DraftRail(id="good", slots=(DraftSlot(id="bad id", label="M"),)))


def test_user_preset_storage_reports_missing_and_bad_inputs(tmp_path) -> None:
    with pytest.raises(KeyError, match="Unknown ActionRail user preset"):
        load_user_preset("missing", preset_dir=tmp_path)

    with pytest.raises(TypeError, match="DraftRail or StackSpec"):
        _as_valid_spec(object())  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="label"):
        save_user_preset(
            DraftRail(
                id="missing_label",
                slots=(DraftSlot(id="move", label="", action="maya.tool.move"),),
            ),
            preset_dir=tmp_path,
        )


def test_draft_spacer_slots_validate_through_schema(tmp_path) -> None:
    draft = DraftRail(
        id="with_gap",
        slots=(
            DraftSlot(id="move", label="M", action="maya.tool.move"),
            DraftSlot(id="gap", type="spacer", size=6),
        ),
    )

    saved_path = save_user_preset(draft, preset_dir=tmp_path)
    payload = json.loads(saved_path.read_text(encoding="utf-8"))

    assert payload["items"][1] == {"id": "with_gap.gap", "size": 6, "type": "spacer"}


def test_user_preset_directory_resolution(tmp_path, monkeypatch) -> None:
    explicit = user_preset_dir(tmp_path / "explicit")
    monkeypatch.setenv("ACTIONRAIL_USER_PRESET_DIR", str(tmp_path / "env"))
    from_env = user_preset_dir()
    monkeypatch.delenv("ACTIONRAIL_USER_PRESET_DIR")
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    default = user_preset_dir()

    assert explicit == tmp_path / "explicit"
    assert from_env == tmp_path / "env"
    assert default == tmp_path / "appdata" / "ActionRail" / "presets"
    assert user_preset_files(preset_dir=tmp_path / "missing") == ()


def test_slot_item_id_keeps_prefixed_ids() -> None:
    assert _slot_item_id("rail", "rail.move") == "rail.move"
    assert _slot_item_id("rail", "move") == "rail.move"
