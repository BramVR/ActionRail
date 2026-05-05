---
summary: Current Edit Mode behavior, user workflow, public APIs, limits, and verification for ActionRail's layout-map authoring shell.
read_when:
  - Using or documenting ActionRail Edit Mode.
  - Extending Phase 2 layout editing or direct manipulation.
  - Checking which Edit Mode features are implemented versus planned.
---

# Edit Mode

Edit Mode is ActionRail's global authoring state for inspecting and adjusting
viewport rail layouts. Normal Mode executes rail actions; Edit Mode draws an
edit-only layout map over the active Maya viewport so rails can be selected and
positioned without triggering their buttons.

The first shell slice is implemented and Maya-smoke verified. It is intended as
the base for Phase 2 step 2.5 layout persistence and direct manipulation.

## What It Shows

When Edit Mode is enabled, ActionRail draws:

- a viewport-sized layout-map overlay owned by Maya's main window
- an optional placement grid
- one translucent labeled frame for each active runtime rail
- selected-frame styling
- rail source layer and lock state labels
- a compact Edit Mode panel with Grid, Grid Size, Snap to Grid, Sticky Frames,
  and selected lock-state display
- a selected-rail position popover with arrow nudges, numeric X/Y controls, and
  Reset

The frame view represents rail footprints and hit boxes. It is deliberately not
the Normal Mode button rendering.

![ActionRail Edit Mode layout map](assets/actionrail_readme_edit_mode.png)

## Maya Workflow

Install the ActionRail Maya menu, show one or more rails, then toggle Edit Mode:

```python
import actionrail

actionrail.install_menu_toggle()
actionrail.show_preset("transform_stack")
actionrail.toggle_edit_mode()
```

The Maya menu exposes `Toggle Edit Mode` after `install_menu_toggle()` is run.

Inside Edit Mode:

- left-click a rail frame to select it and open the X/Y popover
- edit the X/Y fields or use the arrow controls to nudge an unlocked rail
- right-click a rail frame to open options routing for that rail
- enable Grid to show or hide the edit-only grid
- adjust Grid Size to change the grid spacing
- enable Snap to Grid to snap authoring movement to the grid
- enable Sticky Frames to align moved rails to nearby rail edges
- use Save Position from the right-click options popover, or
  `save_edit_mode_layout()`, to persist an unlocked runtime/user rail as a user
  preset

Movement updates active rail overlay positions immediately. Saved persistence is
implemented for unlocked runtime/user rails by writing the current runtime spec
to the user preset store. Locked built-in presets remain read-only; built-in
user-override layering is still a later persistence refinement.

## Public API

Top-level helpers:

```python
import actionrail

state = actionrail.enter_edit_mode()
state = actionrail.toggle_edit_mode()
state = actionrail.exit_edit_mode()
state = actionrail.edit_mode_state()
state = actionrail.set_edit_mode_options(
    show_grid=True,
    snap_to_grid=True,
    sticky_frames=True,
    grid_size=32,
)
state = actionrail.select_edit_mode_rail("my_user_rail")
path = actionrail.save_edit_mode_layout("my_user_rail")
```

State objects:

- `EditModeSettings`: `show_grid`, `snap_to_grid`, `sticky_frames`,
  `grid_size`
- `EditModeState`: `enabled`, `selected_preset_id`, `settings`, `rail_count`,
  `options_preset_id`
- `RailFrameInfo`: viewport-local frame geometry, layout metadata, lock state,
  and source layer

Implementation ownership:

- `scripts/actionrail/edit_mode.py`: state model, layout-map overlay, grid,
  frame selection, options routing, and non-persistent rail nudging
- `scripts/actionrail/maya_ui.py`: Maya menu entry point
- `tests/test_edit_mode.py`: pure Python API/model coverage
- `tests/maya_smoke/actionrail_edit_mode_smoke.py`: Maya layout-map,
  selection, movement, sticky-frame, right-click routing, and screenshot smoke

## Current Limits

Implemented now:

- global enter/exit/toggle state
- active-rail frame discovery
- grid visibility and grid-size controls
- left-click frame selection
- selected-frame X/Y popover
- X/Y movement for unlocked rails
- snap-to-grid and Sticky Frames during movement
- right-click frame options routing marker
- Save Position for unlocked runtime/user rails
- public layout-save helper that persists adjusted offsets to user presets
- Maya menu toggle
- Maya screenshot verification

Not implemented yet:

- built-in/studio user-override persistence
- drag handles
- anchor pins
- snap/spacing guide rendering
- fuller rail options panel
- slot add/remove/reorder from Edit Mode
- collapsible edge-tab controls
- Bind Mode, flyouts, command rings, profile layers, marking-menu export, and
  Viewport 2.0 drawing

Do not modify locked built-in or studio presets directly when adding
persistence. Save layout changes as user presets or user overrides.

## Verification

Focused smoke:

```powershell
.\scripts\maya-smoke.ps1 -Script actionrail_edit_mode_smoke.py
```

Full Maya-facing baseline:

```powershell
.\scripts\maya-smoke.ps1 -Script all
```

The verified overview screenshot used by the README is stored at
`docs/assets/actionrail_readme_edit_mode.png`.
