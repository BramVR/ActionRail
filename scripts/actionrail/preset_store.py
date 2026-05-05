"""Shared preset resolver for bundled, studio, and saved user ActionRail presets."""

from __future__ import annotations

import os
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
from .spec import StackSpec, builtin_preset_ids, load_builtin_preset, load_preset

PresetSource = Literal["builtin", "studio", "user", "builtin_override", "studio_override"]
USER_OVERRIDE_SUFFIX = "_user_override"
BUILTIN_USER_OVERRIDE_SUFFIX = USER_OVERRIDE_SUFFIX
STUDIO_PRESET_DIR_ENV = "ACTIONRAIL_STUDIO_PRESET_DIR"

__all__ = [
    "BUILTIN_USER_OVERRIDE_SUFFIX",
    "PresetEntry",
    "PresetSource",
    "PresetStore",
    "STUDIO_PRESET_DIR_ENV",
    "USER_OVERRIDE_SUFFIX",
    "builtin_user_override_id",
    "preset_user_override_id",
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
    """Resolve ActionRail preset ids across bundled, studio, and user storage."""

    def __init__(
        self,
        *,
        user_preset_dir: str | Path | None = None,
        studio_preset_dir: str | Path | None = None,
    ) -> None:
        self._user_preset_dir = resolve_user_preset_dir(user_preset_dir)
        self._studio_preset_dir = _resolve_studio_preset_dir(studio_preset_dir)

    @property
    def user_preset_dir(self) -> Path:
        """Return the user preset directory used by this store."""

        return self._user_preset_dir

    @property
    def studio_preset_dir(self) -> Path | None:
        """Return the optional read-only studio preset directory."""

        return self._studio_preset_dir

    def builtin_ids(self) -> tuple[str, ...]:
        """Return locked bundled preset ids."""

        return builtin_preset_ids()

    def studio_ids(self) -> tuple[str, ...]:
        """Return loadable read-only studio preset ids."""

        return tuple(entry.id for entry in self.studio_entries() if entry.is_loadable)

    def user_ids(self) -> tuple[str, ...]:
        """Return saved user preset ids."""

        return tuple(entry.id for entry in self.user_entries() if entry.is_loadable)

    def ids(self) -> tuple[str, ...]:
        """Return every known preset id, with read-only layers taking precedence."""

        return tuple(sorted({*self.builtin_ids(), *self.studio_ids(), *self.user_ids()}))

    def entries(self) -> tuple[PresetEntry, ...]:
        """Return discoverable built-in, studio, and user preset entries."""

        return (
            *(PresetEntry(preset_id, "builtin") for preset_id in self.builtin_ids()),
            *self.studio_entries(),
            *self.user_entries(),
        )

    def studio_entries(self) -> tuple[PresetEntry, ...]:
        """Return studio preset entries with discovery validation state."""

        if self._studio_preset_dir is None:
            return ()
        return tuple(
            self._studio_entry_from_path(path)
            for path in _preset_files(self._studio_preset_dir)
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
            override_entry = self._user_override_entry(preset_id, "builtin_override")
            if override_entry is not None:
                return override_entry
            return PresetEntry(preset_id, "builtin")
        if preset_id in self.studio_ids():
            override_entry = self._user_override_entry(preset_id, "studio_override")
            if override_entry is not None:
                return override_entry
            return self._studio_entry(preset_id)
        for entry in self.user_entries():
            if entry.id == preset_id and entry.is_loadable:
                return entry
        msg = f"Unknown ActionRail preset: {preset_id}"
        raise KeyError(msg)

    def base_entry(self, preset_id: str) -> PresetEntry:
        """Return the non-user-override entry for a preset id."""

        if preset_id in self.builtin_ids():
            return PresetEntry(preset_id, "builtin")
        if preset_id in self.studio_ids():
            return self._studio_entry(preset_id)
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
        if entry.source == "studio":
            if entry.path is None:
                msg = f"Missing ActionRail studio preset path for preset: {entry.id}"
                raise ValueError(msg)
            return load_preset(entry.path)
        if entry.source in {"builtin_override", "studio_override"}:
            if entry.path is None:
                msg = f"Missing ActionRail user override path for preset: {entry.id}"
                raise ValueError(msg)
            override = load_user_preset(entry.path.stem, preset_dir=entry.path.parent)
            return _rebase_user_override_spec(override, entry.id)
        preset_dir = entry.path.parent if entry.path is not None else self._user_preset_dir
        return load_user_preset(entry.id, preset_dir=preset_dir)

    def _user_override_entry(
        self,
        preset_id: str,
        source: Literal["builtin_override", "studio_override"],
    ) -> PresetEntry | None:
        override_id = preset_user_override_id(preset_id)
        for entry in self.user_entries():
            if entry.id == override_id and entry.is_loadable:
                return PresetEntry(preset_id, source, entry.path)
        return None

    def _studio_entry(self, preset_id: str) -> PresetEntry:
        for entry in self.studio_entries():
            if entry.id == preset_id and entry.is_loadable:
                return entry
        msg = f"Unknown ActionRail studio preset: {preset_id}"
        raise KeyError(msg)

    def _studio_entry_from_path(self, path: Path) -> PresetEntry:
        preset_id = path.stem
        try:
            spec = load_preset(path)
            if spec.id != preset_id:
                msg = (
                    f"ActionRail studio preset file '{path.name}' declares id "
                    f"'{spec.id}' but was discovered as '{preset_id}'."
                )
                raise ValueError(msg)
            if spec.id in self.builtin_ids():
                msg = f"Studio preset '{spec.id}' would shadow a locked built-in preset."
                raise ValueError(msg)
        except Exception as exc:
            return PresetEntry(preset_id, "studio", path, str(exc))
        return PresetEntry(preset_id, "studio", path)

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
    studio_preset_dir: str | Path | None = None,
) -> StackSpec:
    """Load a preset by id from the shared built-in/studio/user resolver."""

    return PresetStore(
        user_preset_dir=user_preset_dir,
        studio_preset_dir=studio_preset_dir,
    ).load(preset_id)


def builtin_user_override_id(preset_id: str) -> str:
    """Return the user-preset id used to override a locked bundled preset."""

    return preset_user_override_id(preset_id)


def preset_user_override_id(preset_id: str) -> str:
    """Return the user-preset id used to override a read-only preset layer."""

    return f"{preset_id}{USER_OVERRIDE_SUFFIX}"


def preset_ids(
    *,
    user_preset_dir: str | Path | None = None,
    studio_preset_dir: str | Path | None = None,
) -> tuple[str, ...]:
    """Return every known built-in, studio, or saved user preset id."""

    return PresetStore(
        user_preset_dir=user_preset_dir,
        studio_preset_dir=studio_preset_dir,
    ).ids()


def preset_entries(
    *,
    user_preset_dir: str | Path | None = None,
    studio_preset_dir: str | Path | None = None,
) -> tuple[PresetEntry, ...]:
    """Return every known built-in, studio, or saved user preset entry."""

    return PresetStore(
        user_preset_dir=user_preset_dir,
        studio_preset_dir=studio_preset_dir,
    ).entries()


def _rebase_user_override_spec(spec: StackSpec, preset_id: str) -> StackSpec:
    override_id = preset_user_override_id(preset_id)
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


def _resolve_studio_preset_dir(studio_preset_dir: str | Path | None) -> Path | None:
    if studio_preset_dir is not None:
        return Path(studio_preset_dir)
    env_path = os.environ.get(STUDIO_PRESET_DIR_ENV)
    if env_path:
        return Path(env_path)
    return None


def _preset_files(directory: Path) -> tuple[Path, ...]:
    if not directory.is_dir():
        return ()
    return tuple(sorted(path for path in directory.glob("*.json") if path.is_file()))
