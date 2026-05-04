"""Shared preset resolver for bundled and saved user ActionRail presets."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .authoring import (
    load_user_preset,
    user_preset_files,
    user_preset_ids,
)
from .authoring import (
    user_preset_dir as resolve_user_preset_dir,
)
from .spec import StackSpec, builtin_preset_ids, load_builtin_preset

PresetSource = Literal["builtin", "user"]

__all__ = [
    "PresetEntry",
    "PresetSource",
    "PresetStore",
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

        return user_preset_ids(preset_dir=self._user_preset_dir)

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
        """Return saved user preset entries without parsing them."""

        return tuple(
            PresetEntry(path.stem, "user", path)
            for path in user_preset_files(preset_dir=self._user_preset_dir)
        )

    def entry(self, preset_id: str) -> PresetEntry:
        """Return the entry that would be loaded for a preset id."""

        if preset_id in self.builtin_ids():
            return PresetEntry(preset_id, "builtin")
        for entry in self.user_entries():
            if entry.id == preset_id:
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
        preset_dir = entry.path.parent if entry.path is not None else self._user_preset_dir
        return load_user_preset(entry.id, preset_dir=preset_dir)


def resolve_preset(
    preset_id: str,
    *,
    user_preset_dir: str | Path | None = None,
) -> StackSpec:
    """Load a preset by id from the shared built-in/user resolver."""

    return PresetStore(user_preset_dir=user_preset_dir).load(preset_id)


def preset_ids(*, user_preset_dir: str | Path | None = None) -> tuple[str, ...]:
    """Return every known built-in or saved user preset id."""

    return PresetStore(user_preset_dir=user_preset_dir).ids()


def preset_entries(
    *,
    user_preset_dir: str | Path | None = None,
) -> tuple[PresetEntry, ...]:
    """Return every known built-in or saved user preset entry."""

    return PresetStore(user_preset_dir=user_preset_dir).entries()
