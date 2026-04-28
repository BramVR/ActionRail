---
summary: Phase-based implementation roadmap from the verified prototype through declarative rails, Edit Mode, hotkeys, flyouts, rings, profiles, and later viewport-native backends.
read_when:
  - Choosing what to implement next.
  - Checking whether a slice is complete.
  - Updating project status after implementation.
---

# Implementation Plan

## Phase 0: Viewport Overlay Prototype

Goal: prove the reference transform stack can run in Maya as a clickable PySide6 overlay.

### Tasks

1. Create module skeleton.
2. Create PySide compatibility shim.
3. Locate Maya main window and active model panel.
4. Create transparent overlay widget parented to the inner viewport-area widget,
   falling back to the model panel only when Maya does not expose an inner
   viewport child.
5. Add hard-coded reference stack:
   - `M`, `T`, `R`, `S` grouped vertically.
   - `S` pink active/accent state.
   - separate teal `K` button below.
6. Bind actions:
   - move/translate tool
   - rotate tool
   - scale tool
   - set key
7. Add reload/show/hide API:
   - `actionrail.reload()`
   - `actionrail.show_example("transform_stack")`
   - `actionrail.hide_all()`
8. Add minimal cleanup registry for widgets/callbacks.
9. Verify in Maya and capture a screenshot if possible.
10. Update `docs/04_status.md`.

### Acceptance Criteria

- `import actionrail` works in Maya.
- `actionrail.show_example("transform_stack")` shows the stack.
- Empty overlay space does not block viewport navigation.
- Buttons trigger expected Maya actions.
- Repeated show/hide/reload does not duplicate visible widgets.
- Resize or panel switch does not leave a broken overlay in the common case.
- Maya verification result is recorded in `docs/04_status.md`.

## Phase 1: Declarative MVP

Goal: make the prototype reusable so examples and user-authored rails can be created from data instead of framework code.

### Tasks

- JSON preset loader.
- Python builder API.
- Theme tokens and QSS generation.
- Reusable action registry.
- Shelf/menu toggle.
- Basic validation for missing actions and bad preset shape.
- `scripts/maya-smoke.ps1` if command shape is stable.

### Acceptance Criteria

- Reference stack can be created from JSON without editing framework code.
- At least one non-identical rail example can be created from JSON without widget-code changes.
- Built-in examples load from `examples/` or `presets/`.
- Reload cleanup is reliable.
- Basic mayapy or MayaSessiond smoke test exists.

## Phase 1A: WoW-Ready Rail Schema

Goal: make the declarative MVP compatible with later Edit Mode, Bind Mode, flyouts, and profiles.

### Tasks

- Add stable slot ids.
- Add rail layout metadata:
  - orientation
  - rows/columns
  - anchor/offset
  - scale
  - opacity
  - locked state
- Add optional key label field for displayed hotkeys.
- Add declarative `visible_when`, `enabled_when`, and `active_when` fields.
- Keep the current `transform_stack` preset compatible or provide a migration path.

### Acceptance Criteria

- The reference stack still loads from JSON.
- A horizontal rail can be defined from JSON without changing widget code.
- Pure Python tests cover rail/slot parsing and invalid schema errors.

## Phase 1B: Runtime Commands And Hotkey Bridge

Goal: make ActionRail actions bindable through Maya-native hotkeys.

Current state: runtime command publishing, paired nameCommands, conflict-aware hotkey assignment, no-overlay action/slot execution, visible key-label sync after ActionRail slot hotkey assignment, safe cleanup for renamed/removed runtime commands, and initial predicate-driven slot state are started.

### Tasks

- Publish selected ActionRail actions as Maya runtime commands.
- Publish preset slots as runtime command targets.
- Add hotkey conflict detection.
- Add key labels to rendered slots.
- Add safe unpublish/update behavior for renamed or removed slots. Done for explicit sync helpers.

### Acceptance Criteria

- A preset action can be triggered from a Maya hotkey without the overlay being visible.
- Key labels render on buttons without changing button size.
- Hotkey assignment warns before overwriting an existing binding.

## Phase 2: Quick Create And Edit Mode

Goal: let users create rails, palettes, action bars, and hotkey-labeled button layouts without code.

### Tasks

- Dockable workspace-control panel.
- Template picker.
- Action picker.
- Live preview.
- Global Edit Mode toggle.
- Drag handles, anchors, snap guides, spacing guides, and safe margins.
- Per-rail controls for orientation, rows/columns, scale, opacity, lock state, and visibility rules.
- Save/load user presets.
- Publish to shelf/hotkey/runtime command where possible.

### Acceptance Criteria

- An artist can recreate the reference stack from Maya UI only.
- An artist can also create a different rail layout from Maya UI only, proving the designer is not limited to `M/T/R/S/K`.
- Edit Mode changes save to a user preset or user override, not to a locked built-in/studio preset.
- Validation reports missing actions, missing icons, and hotkey conflicts.

## Phase 3: Bind Mode, Flyouts, And Command Rings

Goal: add high-leverage command access patterns inspired by action bar and radial menu addons.

### Tasks

- Hover-to-bind Bind Mode.
- Slot conflict warnings and clear-binding command.
- Flyout widget for grouped related actions.
- Command ring widget for radial press/hold/release workflows.
- Press/release hotkey behavior with Maya focus handling verification.

### Acceptance Criteria

- A user can enter Bind Mode, hover a slot, press a shortcut, and see the key label update.
- A flyout can hold multiple related actions and execute them.
- A command ring can open from a hotkey and execute one selected action.

## Phase 4: Studio Profiles And Sharing

Goal: support production-scale sharing and locked defaults.

### Tasks

- Built-in, studio, project, scene/asset, and user preset layers.
- Locked preset indicators.
- Profile copy/import/export.
- Migration for renamed action ids and slot ids.
- Diagnostics for missing plugins/scripts and orphaned hotkeys.

### Acceptance Criteria

- A studio preset can be installed read-only and extended by user overrides.
- Edit Mode shows each rail's source layer and lock state.
- A missing command/plugin is visible as a broken action badge instead of failing silently.

## Phase 5: Advanced Backends

Goal: add native viewport drawing only after Qt overlay is stable.

### Tasks

- Viewport 2.0 draw backend for labels/guides.
- Custom context/dragger helpers.
- Marking-menu export.
- Visual regression workflow.

## Current Priority

Continue Phase 1 declarative MVP. Keep `docs/06_wow_style_customization.md` in mind while shaping schema/action ids, but do not build the full designer, Bind Mode, flyouts, command rings, or Viewport 2.0 backend until the reusable rail/action foundation is stable.

## Research Backlog

See `docs/07_missing_features_research.md` for the current feature-gap report.
The highest-priority missing features are:

1. Live active/enabled button state driven by Maya state after overlay creation.
2. Shelf/menu entry points and safe-mode diagnostics.
3. Reusable smoke command wrapper if the MayaSessiond command shape remains stable.
4. Narrow Quick Create and Edit Mode after the declarative MVP is stable.
5. Bind Mode, then flyouts, then command rings.
6. Icon import pipeline with license/source tracking.
7. Broader workflow action library beyond transform/keyframe.
8. Profile layers for built-in, studio, project, scene/asset, and user overrides.
9. Marking-menu/hotbox export and later Viewport 2.0 labels/guides.
