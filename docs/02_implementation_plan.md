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
- Python builder API. Done through public `actionrail.StackSpec`,
  `actionrail.RailLayout`, `actionrail.StackItem`, `actionrail.parse_stack_spec()`,
  `actionrail.load_preset()`, and `actionrail.show_spec()` for user-authored
  rails without changing framework code.
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
- Maya built-in icon provider. First pass done for curated `maya.*` logical ids,
  picker-facing `IconDescriptor` metadata, Qt resource-name rendering, Maya
  resource diagnostics, and a `maya_tools` preset.
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
- Runtime-command support diagnostics. First pass done: reports include
  published ActionRail runtime-command names, the diagnostics window summary
  shows the published command count, and stale generated action/slot commands
  are reported as warning issues with sync/unpublish hints.
- Active overlay support diagnostics. First pass done: reports include compact
  active overlay state for support, including panel, widget visibility/validity,
  event-filter target count, and predicate refresh timer state; the diagnostics
  window summary shows aggregate event-filter and refresh-timer counts.
- Diagnostics overlay cleanup action. First pass done: the themed diagnostics
  window includes `Hide Overlays`, which defensively dismisses all
  runtime-owned ActionRail overlays from the same support surface as the report.
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

### Medium Steps

#### 2.1 Authoring Model And User Preset Storage

Status: complete for the first Quick Create foundation slice.

- Define the draft authoring model that maps cleanly to `StackSpec`, `RailLayout`,
  and `StackItem`. Done through public `DraftRail`, `DraftSlot`, and
  `build_draft_spec()`.
- Add a user-preset location separate from locked built-in presets.
  Done through the injectable `actionrail.user_preset_dir()` storage path, which
  defaults outside the bundled `presets/` directory and can be overridden with
  `ACTIONRAIL_USER_PRESET_DIR`.
- Add safe save/load helpers that validate ids, prevent built-in overwrite, and
  preserve existing JSON schema guarantees. Done through
  `actionrail.save_user_preset()` and `actionrail.load_user_preset()`, which
  serialize through the existing preset parser before writing.
- Extend diagnostics so malformed saved user presets are visible without
  blocking bundled presets. Done by reporting saved user-preset parse and spec
  issues as warnings during `collect_diagnostics()`.

Done when a test can build a draft rail, save it as a user preset, reload it,
and prove locked built-in presets were not modified.

Research hints:

- Review `docs/06_wow_style_customization.md` profile/layer notes before naming
  the user-preset storage concepts.
- Look at WoW Edit Mode's named, saved, copied, and shared layout model for the
  persistence shape; do not copy its visual style.
- Check Dominos/Bartender4 profile and per-bar option concepts for what should
  become data, not widget-only state.

#### 2.2 Dockable Quick Create Panel

- Add a Maya workspace-control panel entry point from the ActionRail menu.
- Provide template choices for vertical stack, horizontal strip, and
  collapsible edge-tab rail; keep flyout and command-ring templates disabled or
  absent until Phase 3.
- Provide an action picker from the registered ActionRail action ids.
- Let users choose slot labels, key-label text, icons where available, and basic
  layout values.

Done when an artist can create a valid draft rail from Maya UI without editing
JSON, even before direct viewport editing exists.

Research hints:

- Start with Autodesk workspace-control examples for restore-safe Maya panels.
- Compare WoW Edit Mode and Dominos configuration entry points for how users
  discover "configure UI" without confusing it with normal action execution.
- Browse Bartender4/Dominos screenshots or docs for compact per-bar settings;
  keep ActionRail's panel Maya-native and utilitarian.

#### 2.3 Preview And Save Workflow

- Convert the Quick Create draft into a real spec and show it through the
  existing Qt overlay runtime.
- Support preview without saving and cleanup of preview overlays.
- Save the current draft as a user preset with a stable preset id and stable slot
  ids.
- Reload and show the saved preset through the same public runtime path as
  bundled examples.

Done when Quick Create can preview a vertical or horizontal custom rail, save
it, reload it, and show it after an ActionRail reload.

Research hints:

- Check Maya tool option windows and non-destructive preview patterns for how to
  separate "preview", "apply", and "save".
- Use WoW Edit Mode's save/copy/share layout idea as a product reference, but
  keep this slice limited to local user presets.
- Inspect existing ActionRail diagnostics and safe-start behavior so failed
  previews leave a copyable report instead of a stuck overlay.

#### 2.4 Edit Mode Shell And Rail Selection

- Add a global Edit Mode toggle and Maya-facing command/menu entry.
- In Edit Mode, show rail outlines, hit boxes, selected-state styling, source
  layer, and lock state.
- Add a selected-rail inspector for anchor, offset, orientation, rows/columns,
  scale, opacity, locked state, and visibility rules.
- Keep normal action execution disabled or clearly separated while editing.

Done when existing and user-created rails can be selected and inspected in Edit
Mode without changing their saved layout.

Research hints:

- Study WoW Edit Mode for outlines, selected HUD elements, saveable layout state,
  and the distinction between play/use mode and edit mode.
- Review DCC UI patterns for manipulators and inspectors, especially Maya's
  channel box/tool settings split.
- Keep `docs/07_missing_features_research.md` nearby for source-layer, lock,
  diagnostics, and future profile constraints.

#### 2.5 Layout Editing And Direct Manipulation

- Add drag handles for moving rails in the active viewport.
- Add anchor pins, safe margins, snap guides, and spacing guides.
- Persist edited anchor/offset/layout values to a user preset or user override.
- Add controls for slot add/remove/reorder and rail layout changes.

Done when an artist can recreate the reference stack and create a distinct rail
layout from Maya UI only, then save those changes outside locked built-in
presets.

Research hints:

- Compare WoW Edit Mode and Dominos configuration mode for drag-to-position,
  per-bar scale/opacity/spacing, and safe unlock behavior.
- Look at Maya guide/snap UX before designing ActionRail guides; viewport tools
  should feel precise, quiet, and non-decorative.
- Revisit the local `research/` reference images when tuning hit boxes and
  spacing for the transform-stack regression target.

#### 2.6 Collapsible Edge Tabs And Publish Polish

- Add collapsible rail settings: edge, handle icon, reveal trigger, and default
  collapsed state.
- Render a small edge handle when collapsed without creating a viewport-sized
  transparent hit area.
- Preserve actions, runtime-command publishing, and hotkey labels while a rail
  is collapsed.
- Surface validation for missing actions, missing icons, and hotkey conflicts
  before save or publish.
- Publish saved user presets to shelf/hotkey/runtime command where possible.

Done when an artist can collapse a custom rail to a side handle, expand it
again, and keep layout, actions, and bindings intact.

Research hints:

- Study collapsible side panels, shelf tabs, and compact action-bar fade/collapse
  behavior; keep handles small and obvious without stealing viewport input.
- Review Bartender4/Dominos hotkey-label and visibility concepts for publish
  polish, but keep Bind Mode itself in Phase 3.
- Skim OPie only as a boundary check: rings reduce clutter, but this step should
  ship collapsible rails, not radial command selection.

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

Phase 2 step 2.1 is complete and verified locally. The draft authoring model and
safe user-preset storage are ready for the first Maya-facing Quick Create UI.

Next implementation slice: Phase 2 step 2.2, a dockable Quick Create panel that
can choose a vertical or horizontal template, pick registered actions, edit
basic labels/icons/layout values, and produce a valid draft. Keep
`docs/06_wow_style_customization.md` in mind, but do not start Bind Mode,
flyouts, command rings, profile layers, marking-menu export, or Viewport 2.0
yet.

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
