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
4. Resolve the inner viewport-area widget for anchor geometry and show the
   visible rail as a small frameless Maya-owned tool window, falling back to
   direct viewport parenting only outside Maya or when the main window cannot be
   resolved.
5. Add hard-coded reference stack:
   - `M`, `T`, `R`, `S` grouped vertically.
   - active tool buttons use the generic active/accent theme state.
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
- The overlay does not create viewport-sized transparent hit areas and does not
  block viewport navigation outside visible controls.
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
- Shelf/menu toggle. Done for the default `transform_stack` preset through idempotent menu and shelf installers.
- Basic validation for missing actions and bad preset shape.
- `scripts/maya-smoke.ps1` wrapper for stable MayaSessiond smoke execution. Done for checked-in scripts under `tests/maya_smoke`.
- Safe-mode diagnostics for broken presets/actions, missing command/plugin
  predicates, and recoverable overlay startup failures. First pass done through
  `actionrail.collect_diagnostics()`, `actionrail.diagnose_spec()`, and
  `actionrail.safe_start()`.
- Reusable per-slot render state. First pass done through `SlotRenderState`,
  which centralizes label, hotkey badge, tone, tooltip, enabled, and active
  updates for action-bearing buttons without rebuilding the rail when
  visibility is unchanged.
- Active color is generic theme state. Presets should use `active_when` for
  persistent buttons; one-shot macro buttons should omit it.
- Icon and diagnostic badge inputs for `SlotRenderState`. First pass done for
  optional `icon` ids, manifest path lookup, visible missing-action error
  badges, visible missing-icon warning badges, and matching diagnostics.
- Icon-backed preset path. First pass done for a manifest-backed
  `horizontal_tools` rail plus icon metadata, missing-file, unknown-id, and
  unsafe-SVG validation before render path resolution.
- SVG import helper. First pass done through
  `actionrail.icons.import_svg_icon()`, which validates local SVG sources,
  rejects external resources in style blocks, writes safe assets under
  `icons/`, normalizes manifest path conflicts before overwrite, and upserts
  manifest source/license/url/import metadata.
- PNG fallback generation. First pass done through
  `actionrail.icons.generate_png_fallbacks()` and import-time fallback
  generation, with manifest diagnostics for missing or stale generated assets.
- Icon import diagnostics and preset recovery polish. First pass done through
  non-writing `actionrail.icons.validate_svg_icon_import()` preflight,
  report-backed `actionrail.diagnose_icon_import()`, optional diagnostic
  `path`/`field` details, and opt-in
  `actionrail.safe_start(..., fallback_preset_id=...)` recovery.
- Command/plugin predicate availability badges. First pass done for missing
  `command.exists(...)` and `plugin.exists(...)` targets, including visible
  disabled warning slots when a missing dependency would otherwise hide the
  slot. Runtime badge rendering now preserves the rest of the predicate
  semantics, including compound context clauses and negated availability checks.
- Last diagnostic report UI. First pass done through `actionrail.last_report()`,
  `actionrail.clear_last_report()`, `actionrail.format_report()`, and
  `actionrail.show_last_report()`, plus a Maya menu item that opens the latest
  report.
- Polished diagnostics window. Done: `actionrail.show_last_report()` now opens
  an ActionRail-themed Qt dialog/window that lists warnings/errors, shows the
  selected issue details and full report in selectable text areas, and provides
  `Copy Selected`, `Copy Full Report`, `Clear`, and `Close` actions. Visible
  and copyable selected issue details include structured issue `path`, `field`,
  and `hint` values for import and manifest diagnostics.
- Maya-facing icon import diagnostics. First pass done: the ActionRail Maya
  menu includes `Diagnose SVG Icon Import...`, which lets a user choose a local
  SVG, enter an icon id, runs the non-writing import preflight, records the
  latest report, and opens the themed diagnostics window.

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

Current state: runtime command publishing, paired nameCommands, conflict-aware hotkey assignment, no-overlay action/slot execution, visible key-label sync after ActionRail slot hotkey assignment, safe cleanup for renamed/removed runtime commands, initial predicate-driven slot state, manual live predicate refresh, and timer-driven automatic predicate refresh are started.

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
- Collapsible edge-tab rails that can fold against a viewport side and leave a small arrow/handle for reveal.
- Save/load user presets.
- Publish to shelf/hotkey/runtime command where possible.

### Acceptance Criteria

- An artist can recreate the reference stack from Maya UI only.
- An artist can also create a different rail layout from Maya UI only, proving the designer is not limited to `M/T/R/S/K`.
- An artist can collapse a rail to a side handle and expand it again without losing its layout or bindings.
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

Next implementation slice: keep hardening visible diagnostics as the import
path expands and preserve the existing fallback preset startup smoke coverage.
Use `docs/04_status.md` as the detailed handoff.

## Research Backlog

See `docs/07_missing_features_research.md` for the current feature-gap report.
The highest-priority missing features are:

1. Wire icon-backed preset/import diagnostics into Maya-facing support flows.
2. Continue visible diagnostics as the import path expands.
3. Narrow Quick Create and Edit Mode after the declarative MVP is stable, including collapsible edge-tab rail controls.
4. Bind Mode, then flyouts, then command rings.
5. Broader workflow action library beyond transform/keyframe.
6. Profile layers for built-in, studio, project, scene/asset, and user overrides.
7. Marking-menu/hotbox export and later Viewport 2.0 labels/guides.
