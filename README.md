# ActionRail - Polished viewport UI for Maya

![Maya](https://img.shields.io/badge/Maya-2025%2F2026-37a5cc)
![Python](https://img.shields.io/badge/Python-3.11-3776ab)
![PySide](https://img.shields.io/badge/UI-PySide6%20%2F%20Qt-41cd52)
![Status](https://img.shields.io/badge/status-Phase%202%20authoring%20foundation-37a5cc)

ActionRail is a Maya module for compact, polished, user-created viewport UI:
tool rails, action bars, action buttons, hotkey badges, diagnostics, and
authoring utilities. It is PySide6-first, data-driven, and built to feel like
part of Maya instead of a large docked tool window.

<p align="center">
  <img src="docs/assets/actionrail_readme_hero.png" alt="ActionRail viewport UI hero image">
</p>

## In Maya

<p align="center">
  <img src="docs/assets/actionrail_readme_maya_showcase.png" alt="ActionRail action bars shown over a minimal Maya viewport scene">
</p>

## Why

Maya has shelves, hotkeys, hotbox zones, marking menus, and dockable editors.
ActionRail fills a different slot: tiny viewport-adjacent controls that artists
and TDs can define as data, share as presets, and bind through Maya's native
command system.

The included examples are a compact transform stack, `M/T/R/S` plus a separate
`K` key button, and an icon-backed horizontal tool rail.

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

Useful commands:

```python
actionrail.reload()
actionrail.hide_all()
actionrail.run_action("maya.tool.rotate")
actionrail.run_slot("transform_stack", "set_key")
```

Install Maya-native entry points:

```python
actionrail.install_menu_toggle()
actionrail.install_shelf_toggle()
actionrail.toggle_default()
actionrail.run_diagnostics_from_maya()
```

Inspect the current package map, presets, user preset directory, public APIs,
module ownership, and verification commands:

```powershell
$env:PYTHONPATH = "scripts"
.\.venv\Scripts\python.exe -m actionrail --json
```

For a local checkout, set the module path before launching Maya:

```powershell
$env:MAYA_MODULE_PATH = "."
```

## Authoring Utilities

The first Phase 2 authoring foundation is code-facing: draft rails can be
validated, converted into runtime specs, and saved as user presets without
touching locked built-in presets.

```python
import actionrail

draft = actionrail.DraftRail(
    id="artist_tools",
    layout=actionrail.RailLayout(
        anchor="viewport.bottom.center",
        orientation="horizontal",
        offset=(0, -32),
    ),
    slots=(
        actionrail.DraftSlot(
            id="move",
            label="M",
            action="maya.tool.move",
            key_label="W",
            active_when="maya.tool == move",
            icon="actionrail.move",
        ),
        actionrail.DraftSlot(
            id="set_key",
            label="K",
            action="maya.anim.set_key",
            tone="teal",
        ),
    ),
)

spec = actionrail.build_draft_spec(draft)
path = actionrail.save_user_preset(draft)
loaded = actionrail.load_user_preset("artist_tools")
actionrail.show_spec(loaded)
```

User presets default to `%APPDATA%\ActionRail\presets` on Windows. Override the
location with `ACTIONRAIL_USER_PRESET_DIR`, or pass `preset_dir=` to the user
preset helpers.

## What Works Now

- Qt rail overlay anchored to Maya model-panel geometry and shown as a small
  frameless Maya-owned tool window to avoid Viewport 2.0 repaint artifacts.
- Built-in `transform_stack` and icon-backed `horizontal_tools` JSON presets.
- Declarative layout metadata: orientation, rows, columns, anchor, offset,
  scale, opacity, and locked state.
- Stable slot ids for hotkeys, user overrides, and preset migrations.
- Draft authoring model with `DraftRail`, `DraftSlot`,
  `build_draft_spec()`, `spec_to_payload()`, `save_user_preset()`,
  `load_user_preset()`, `user_preset_dir()`, and `user_preset_ids()`.
- Built-in Maya actions for move, translate, rotate, scale, and set key.
- Runtime-command and nameCommand publishing for Maya-native hotkey binding.
- Conflict-aware hotkey assignment helpers.
- Key-label sync and stale runtime-command cleanup helpers for published slots.
- Automatic predicate refresh for visible overlays.
- Safe-mode diagnostics through `actionrail.collect_diagnostics()`,
  `actionrail.diagnose_spec()`, and `actionrail.safe_start()`.
- User preset diagnostics in `collect_diagnostics()`, with broken saved presets
  reported as warnings so bundled presets remain available.
- Visible diagnostic badges for missing actions, missing icons, and missing
  command/plugin predicate dependencies.
- Icon manifest validation for required metadata, duplicate ids, invalid local
  paths, missing files, invalid SVG files, unsafe SVG content, and unknown icon
  ids.
- Local SVG import helper that validates source SVG safety, copies the asset
  into `icons/`, normalizes manifest path conflicts, and records
  source/license/url/import-date metadata.
- PNG fallback generation for SVG icons at 1x/2x/3x, with manifest diagnostics
  for missing or stale fallback assets.
- Idempotent Maya menu and shelf toggle entry points, plus Maya menu flows for
  diagnostics and SVG import preflight.
- Copyable Qt diagnostics window with severity filtering, overlay support
  state, published runtime-command summary, and a hide-overlays support action.
- `actionrail.about()` and `python -m actionrail --json` project map output for
  public APIs, built-ins, user preset state, icon health, docs, module
  ownership, and verification commands.
- Theme tokens compiled to QSS.

## Roadmap

For the current handoff, blockers, and latest verification summary, see
[`docs/04_status.md`](docs/04_status.md).

Near-term:

- Build the Phase 2 Quick Create dockable panel on top of the draft/user preset
  storage layer.
- Add template and action selection, preview through `show_spec()`, and save to
  the user preset directory.
- Keep user preset validation, diagnostics, and recovery visible while the UI
  grows.

Next:

- Edit Mode for non-coders.
- Bind Mode: hover a slot, press a shortcut, update Maya hotkeys.
- Flyouts for compact command groups.
- Command rings for press/hold/release workflows.
- Built-in, studio, project, scene/asset, and user preset layers.

Later:

- Maya marking-menu and hotbox export.
- Viewport 2.0 labels/guides for non-clickable viewport-native drawing.

## Project Layout

```text
ActionRail.mod              Maya module descriptor
scripts/actionrail/         Runtime package
presets/                    Built-in JSON rail presets
icons/                      Local icon assets and manifest
tests/                      Pure Python and Maya smoke tests
docs/                       Architecture, workflow, roadmap, and status
```

## Development

Run local tests:

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
```

Run the coverage gate:

```powershell
.\.venv\Scripts\python.exe -m coverage run -m pytest
.\.venv\Scripts\python.exe -m coverage report
```

Show the compact agent/project map:

```powershell
$env:PYTHONPATH = "scripts"
.\.venv\Scripts\python.exe -m actionrail --json
```

For Maya-facing changes, use the checked-in MayaSessiond wrapper:

```powershell
.\scripts\maya-smoke.ps1 -Script all
.\scripts\maya-smoke.ps1 -Script actionrail_maya_ui_smoke.py
```

The wrapper uses `.gg-maya-sessiond`, starts Sessiond only when needed, injects
this module path, discovers MCP tools, and runs cleanup before and after each
selected smoke script.

## Contributor Docs

- [Start here](docs/00_start_here.md) - current goal, state, and read order.
- [Architecture](docs/01_architecture.md) - runtime boundaries and planned
  layers.
- [Implementation plan](docs/02_implementation_plan.md) - phase roadmap.
- [Status](docs/04_status.md) - live state, blockers, latest handoff, and latest verification.
- [Verification log](docs/history/verification_log.md) - archived historical
  test and MayaSessiond runs.
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

ActionRail has a verified declarative MVP and the first Phase 2 authoring
foundation. JSON presets, viewport rails, Maya actions, runtime-command hotkey
publishing, predicate refresh, safe diagnostics, icon import diagnostics, menu
and shelf entry points, and code-facing user preset storage are working. It is
not yet a finished designer or production preset manager.

## License

Apache License 2.0. See [LICENSE](LICENSE).
