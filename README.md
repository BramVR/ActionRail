# ActionRail - Polished viewport UI for Maya

![Maya](https://img.shields.io/badge/Maya-2025%2F2026-37a5cc)
![Python](https://img.shields.io/badge/Python-3.11-3776ab)
![PySide](https://img.shields.io/badge/UI-PySide6%20%2F%20Qt-41cd52)
![Status](https://img.shields.io/badge/status-MVP%20in%20progress-f0ad4e)

ActionRail is a Maya module for compact, polished, user-created viewport UI:
tool rails, action bars, action buttons, hotkey badges, and later edit-mode
authoring. It is PySide6-first, data-driven, and built to feel like part of
Maya instead of a large docked tool window.

<p align="center">
  <img src="docs/assets/actionrail_readme_hero.png" alt="ActionRail viewport UI hero image">
</p>

## Why

Maya has shelves, hotkeys, hotbox zones, marking menus, and many dockable
editors. ActionRail fills a different slot: tiny viewport-adjacent controls that
artists and TDs can define as data, share as presets, and bind through Maya's
native command system.

The first proof preset is the compact transform stack: `M/T/R/S` plus a
separate `K` key button. Local reference images can live in `research/`, which
is intentionally ignored by Git.

## Quick Start

Add this checkout to Maya's module path, then run the example from Maya's Python
environment:

```python
import actionrail

actionrail.show_example("transform_stack")
```

Try the horizontal rail:

```python
actionrail.show_example("horizontal_tools")
```

Useful during iteration:

```python
actionrail.reload()
actionrail.hide_all()
actionrail.run_action("maya.tool.rotate")
actionrail.run_slot("transform_stack", "set_key")
```

During local development this repo is verified as a Maya module with:

```powershell
$env:MAYA_MODULE_PATH = "."
```

## What Works Now

- Qt rail overlay anchored to Maya model-panel geometry and shown as a small
  frameless Maya-owned tool window to avoid Viewport 2.0 repaint artifacts.
- Built-in `transform_stack` and `horizontal_tools` JSON presets.
- Declarative layout metadata: orientation, rows, columns, anchor, offset,
  scale, opacity, and locked state.
- Stable slot ids for future hotkeys, user overrides, and migrations.
- Built-in Maya actions for move, translate, rotate, scale, and set key.
- Runtime-command and nameCommand publishing for Maya-native hotkey binding.
- Conflict-aware hotkey assignment helpers.
- Key-label sync and stale runtime-command cleanup helpers for published slots.
- Theme tokens compiled to QSS.
- Pure Python tests plus Maya smoke scripts.

## Roadmap

Near-term:

- Show live active/enabled button state without rebuilding the overlay.
- Add shelf/menu toggles and safe-mode diagnostics.

Next:

- Quick Create and Edit Mode for non-coders.
- Bind Mode: hover a slot, press a shortcut, update Maya hotkeys.
- Flyouts for compact command groups.
- Command rings for press/hold/release workflows.
- Icon import pipeline with source/license tracking.
- Built-in, studio, project, scene/asset, and user preset layers.

Later:

- Maya marking-menu and hotbox export.
- Viewport 2.0 labels/guides for non-clickable viewport-native drawing.

See [docs/07_missing_features_research.md](docs/07_missing_features_research.md)
for the current feature-gap report.

## Project Layout

```text
ActionRail.mod              Maya module descriptor
scripts/actionrail/         Runtime package
presets/                    Built-in JSON rail presets
icons/                      Icon manifest and future imported assets
docs/assets/                README and documentation images
tests/                      Pure Python and Maya smoke tests
docs/                       Architecture, workflow, roadmap, status
```

## Development

Run local tests:

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
```

For Maya-facing changes, run the relevant smoke scripts from `tests/maya_smoke/`
in a Maya Python environment with this checkout on `MAYA_MODULE_PATH`.

## Docs

- [Start here](docs/00_start_here.md) - current goal, state, and read order.
- [Architecture](docs/01_architecture.md) - runtime boundaries and planned
  layers.
- [Implementation plan](docs/02_implementation_plan.md) - phase roadmap.
- [Status](docs/04_status.md) - done state, blockers, verification history.
- [Tech stack](docs/05_tech_stack.md) - PySide6/Qt overlay decision.
- [Customization roadmap](docs/06_wow_style_customization.md) - Edit Mode,
  Bind Mode, flyouts, rings, and profiles.
- [Missing features research](docs/07_missing_features_research.md) -
  source-backed backlog.

## Design Principles

- Qt overlay first; Viewport 2.0 only for scene/native drawing later.
- `maya.cmds` first; no PyMEL by default.
- Data-driven rails: Python API plus JSON presets.
- Stable dimensions; hover, active, disabled, and badge states must not shift
  layout.
- The rail must not create viewport-sized transparent widgets; normal viewport
  interaction should remain available outside the visible controls.
- Runtime commands for anything that should be visible in Maya's Hotkey Editor.
- Locked studio presets should never be silently overwritten by user edits.

## Status

ActionRail is an early MVP. The transform-stack prototype is verified, the
declarative rail schema is started, and the runtime-command hotkey bridge is in
progress. It is not yet a finished designer or production preset manager.

## License

Apache License 2.0. See [LICENSE](LICENSE).
