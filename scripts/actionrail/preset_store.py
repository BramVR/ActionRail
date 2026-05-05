"""Shared preset resolver for bundled and saved user ActionRail presets."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import replace as dataclass_replace
from pathlib import Path
from typing import Literal

from .authoring import (
    load_user_preset,
    user_preset_files,
)
from .authoring import (
    user_preset_dir as resolve_user_preset_dir,
)
from .spec import StackSpec, builtin_preset_ids, load_builtin_preset

PresetSource = Literal["builtin", "user", "builtin_override"]
BUILTIN_USER_OVERRIDE_SUFFIX = "_user_override"

__all__ = [
    "BUILTIN_USER_OVERRIDE_SUFFIX",
    "PresetEntry",
    "PresetSource",
    "PresetStore",
    "builtin_user_override_id",
    "preset_entries",
    "preset_ids",
    "resolve_preset",
]


@dataclass(frozen=True)
class PresetEntry:
    """One discoverable preset id and its storage source."""

    id: str
    source: PresetSource
    path: Path | None = None
    error: str = ""

    @property
    def is_loadable(self) -> bool:
        """Return whether this discovered entry passed lightweight validation."""

        return not self.error


class PresetStore:
    """Resolve ActionRail preset ids across bundled and user storage."""

    def __init__(self, *, user_preset_dir: str | Path | None = None) -> None:
        self._user_preset_dir = resolve_user_preset_dir(user_preset_dir)

    @property
    def user_preset_dir(self) -> Path:
        """Return the user preset directory used by this store."""

        return self._user_preset_dir

    def builtin_ids(self) -> tuple[str, ...]:
        """Return locked bundled preset ids."""

        return builtin_preset_ids()

    def user_ids(self) -> tuple[str, ...]:
        """Return saved user preset ids."""

        return tuple(entry.id for entry in self.user_entries() if entry.is_loadable)

    def ids(self) -> tuple[str, ...]:
        """Return every known preset id, with built-ins taking precedence."""

        return tuple(sorted({*self.builtin_ids(), *self.user_ids()}))

    def entries(self) -> tuple[PresetEntry, ...]:
        """Return discoverable built-in and user preset entries."""

        return (
            *(PresetEntry(preset_id, "builtin") for preset_id in self.builtin_ids()),
            *self.user_entries(),
        )

    def user_entries(self) -> tuple[PresetEntry, ...]:
        """Return saved user preset entries with discovery validation state."""

        return tuple(
            self._user_entry_from_path(path)
            for path in user_preset_files(preset_dir=self._user_preset_dir)
        )

    def entry(self, preset_id: str) -> PresetEntry:
        """Return the entry that would be loaded for a preset id."""

        if preset_id in self.builtin_ids():
            override_entry = self._builtin_override_entry(preset_id)
            if override_entry is not None:
                return override_entry
            return PresetEntry(preset_id, "builtin")
        for entry in self.user_entries():
            if entry.id == preset_id and entry.is_loadable:
                return entry
        msg = f"Unknown ActionRail preset: {preset_id}"
        raise KeyError(msg)

    def load(self, preset_id: str) -> StackSpec:
        """Load a preset by id from bundled or user storage."""

        return self.load_entry(self.entry(preset_id))

    def load_entry(self, entry: PresetEntry) -> StackSpec:
        """Load a specific preset entry, preserving its source layer."""

        if entry.source == "builtin":
            return load_builtin_preset(entry.id)
        if entry.source == "builtin_override":
            if entry.path is None:
                msg = f"Missing ActionRail user override path for preset: {entry.id}"
                raise ValueError(msg)
            override = load_user_preset(entry.path.stem, preset_dir=entry.path.parent)
            return _rebase_builtin_override_spec(override, entry.id)
        preset_dir = entry.path.parent if entry.path is not None else self._user_preset_dir
        return load_user_preset(entry.id, preset_dir=preset_dir)

    def _builtin_override_entry(self, preset_id: str) -> PresetEntry | None:
        override_id = builtin_user_override_id(preset_id)
        for entry in self.user_entries():
            if entry.id == override_id and entry.is_loadable:
                return PresetEntry(preset_id, "builtin_override", entry.path)
        return None

    def _user_entry_from_path(self, path: Path) -> PresetEntry:
        preset_id = path.stem
        try:
            load_user_preset(preset_id, preset_dir=path.parent)
        except Exception as exc:
            return PresetEntry(preset_id, "user", path, str(exc))
        return PresetEntry(preset_id, "user", path)


def resolve_preset(
    preset_id: str,
    *,
    user_preset_dir: str | Path | None = None,
) -> StackSpec:
    """Load a preset by id from the shared built-in/user resolver."""

    return PresetStore(user_preset_dir=user_preset_dir).load(preset_id)


def builtin_user_override_id(preset_id: str) -> str:
    """Return the user-preset id used to override a locked bundled preset."""

    return f"{preset_id}{BUILTIN_USER_OVERRIDE_SUFFIX}"


def preset_ids(*, user_preset_dir: str | Path | None = None) -> tuple[str, ...]:
    """Return every known built-in or saved user preset id."""

    return PresetStore(user_preset_dir=user_preset_dir).ids()


def preset_entries(
    *,
    user_preset_dir: str | Path | None = None,
) -> tuple[PresetEntry, ...]:
    """Return every known built-in or saved user preset entry."""

    return PresetStore(user_preset_dir=user_preset_dir).entries()


def _rebase_builtin_override_spec(spec: StackSpec, preset_id: str) -> StackSpec:
    override_id = builtin_user_override_id(preset_id)
    return dataclass_replace(
        spec,
        id=preset_id,
        items=tuple(_rebase_override_item_id(override_id, preset_id, item) for item in spec.items),
    )


def _rebase_override_item_id(
    override_id: str,
    preset_id: str,
    item: object,
) -> object:
    item_id = str(getattr(item, "id", ""))
    prefix = f"{override_id}."
    if item_id.startswith(prefix):
        item_id = f"{preset_id}.{item_id.removeprefix(prefix)}"
    return dataclass_replace(item, id=item_id)
