---
summary: Phase-based implementation roadmap from the verified prototype through WoW-style frames, action bars, Action Book, Bind Mode, macros, profiles, and later viewport-native backends.
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
- Reusable per-slot render state. First pass done through pure
  `actionrail.slot_state.SlotRenderState`, which centralizes label, hotkey
  badge, tone, tooltip, enabled, and active updates for action-bearing buttons
  without rebuilding the rail when visibility is unchanged.
- Active color is generic theme state. Presets should use `active_when` for
  persistent buttons; one-shot macro buttons should omit it.
- Icon and diagnostic badge inputs for `SlotRenderState`. First pass done for
  optional `icon` ids, manifest path lookup, visible missing-action error
  badges, visible missing-icon warning badges, and matching diagnostics.
- Icon-backed preset path. First pass done for a manifest-backed
  `horizontal_tools` rail plus icon metadata, missing-file, unknown-id, and
  unsafe-SVG validation before render path resolution.
- Maya built-in icon provider. First pass done for curated `maya.*` logical ids,
  picker-facing `IconDescriptor` metadata, Maya resource diagnostics,
  Qt `:/` resource rendering, full-slot icon underlays, and a `maya_tools`
  preset.
- Icon subsystem split. First pass done behind the public `actionrail.icons`
  facade: provider descriptors/read-only lookup live in `icon_catalog`,
  manifest storage/validation in `icon_manifest`, SVG import/preflight and
  writes in `icon_import`, SVG safety in `icon_svg`, and generated PNG
  fallback/mayapy rendering in `icon_fallbacks`.
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
Slot binding-target metadata is now exposed through
`actionrail.slot_binding_targets()` so current Maya Hotkey Editor workflows and
future Bind Mode can work from visible slot ids/key labels instead of raw
runtime-command naming.

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

Goal: let users create the first WoW-style action bar frames and
hotkey-labeled button layouts without code, while keeping the architecture open
for later non-bar frames such as info boxes, tooltip frames, and object-linked
HUD frames.

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
- Resolve saved user presets through the same id path as bundled presets for
  runtime preview/startup, no-overlay slot execution, hotkey publishing/sync,
  runtime-command diagnostics, and Maya menu toggles. Done through
  `actionrail.PresetStore`, `actionrail.resolve_preset()`,
  `actionrail.preset_ids()`, and `actionrail.show_preset()`.

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

Status: complete for the first Maya-facing authoring slice.

- Add a Maya workspace-control panel entry point from the ActionRail menu.
- Provide template choices for vertical stack, horizontal strip, collapsible
  edge-tab rail, blank action bar, and viewport display strip; keep flyout and
  command-ring templates disabled or absent until Phase 3. Done through
  `scripts/actionrail/quick_create.py` and the dockable Qt panel.
- Provide an action picker from the registered ActionRail action ids. Done for
  the early Quick Create slice; Quick Create has since been narrowed back to
  bar/slot creation, with action browsing moved to the separate Action Book UI.
- Let users choose slot labels, key-label text, icons where available, and basic
  layout values. Done for the draft validation panel.
- Show hotkey-ready slot binding targets without entering Bind Mode. Done
  through the read-only Quick Create Bindings tab, which lists action-bearing
  slots, key labels, and Maya nameCommands for the current draft.
- Route action choices through the first Action Book backend metadata instead
  of raw action registry labels. Done through `actionrail.action_book`; the
  first separate Action Book UI now consumes the same metadata for placement.

Done when an artist can create a valid draft rail from Maya UI without editing
JSON, even before direct viewport editing exists.

Research hints:

- Start with Autodesk workspace-control examples for restore-safe Maya panels.
- Compare WoW Edit Mode and Dominos configuration entry points for how users
  discover "configure UI" without confusing it with normal action execution.
- Browse Bartender4/Dominos screenshots or docs for compact per-bar settings;
  keep ActionRail's panel Maya-native and utilitarian.

#### 2.3 Preview And Save Workflow

Status: complete for the first Quick Create workflow slice.

- Convert the Quick Create draft into a real spec and show it through the
  existing Qt overlay runtime. Done through
  `preview_quick_create_draft()`.
- Handoff from Quick Create into viewport placement/configuration. Done through
  `edit_quick_create_layout()`, which previews the current draft, enters Edit
  Mode, and selects the draft frame.
- Support preview without saving and cleanup of preview overlays. Done through
  session-tracked Quick Create preview ids and
  `clear_quick_create_previews()`.
- Save the current draft as a user preset with a stable preset id and stable slot
  ids. Done through `save_quick_create_preset()`, which saves through the
  existing user-preset writer and requires explicit overwrite for existing
  files.
- Load existing saved user presets back into Quick Create for editing. Done
  through `load_quick_create_preset()` and the panel's Load Existing action for
  user presets only.
- Reload and show the saved preset through the same public runtime path as
  bundled examples. Done by saving through the shared user-preset resolver,
  showing the saved preset with targeted overlay replacement, and smoke-testing
  that the saved preset can still be shown after `actionrail.reload(...)`.

Done when Quick Create can preview a vertical or horizontal custom rail, save
it, load an existing saved user rail for editing, reload it, and show it after
an ActionRail reload.

Research hints:

- Check Maya tool option windows and non-destructive preview patterns for how to
  separate "preview", "apply", and "save".
- Use WoW Edit Mode's save/copy/share layout idea as a product reference, but
  keep this slice limited to local user presets.
- Inspect existing ActionRail diagnostics and safe-start behavior so failed
  previews leave a copyable report instead of a stuck overlay.

#### 2.4 Edit Mode Shell And Rail Selection

Status: complete for the first shell slice.

- Add a global Edit Mode toggle and Maya-facing command/menu entry.
  Done through `actionrail.toggle_edit_mode()`, `enter_edit_mode()`,
  `exit_edit_mode()`, `edit_mode_state()`, and the ActionRail Maya menu.
- In Edit Mode, show a layout-map view of rails/frames as labeled dark
  rectangles over the viewport, plus rail outlines, hit boxes, selected-state
  styling, source layer, and lock state. Done for active runtime rails.
- Add a selected-rail inspector for anchor, offset, orientation, rows/columns,
  scale, opacity, locked state, and visibility rules. Done as the first compact
  Edit Mode control panel and position popover.
- Add user-visible Edit Mode options for showing a placement grid overlay and
  configuring grid size, sticky-frame snapping, and snap-to-grid later; the
  first shell may show the grid and settings without moving or saving rails yet.
  Done for grid visibility, Grid Size, Snap to Grid, and Sticky Frames controls;
  in-session snap/sticky movement was implemented here and saved persistence
  was completed in 2.5.
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

Status: done.

- Added direct frame dragging for moving rails in the active viewport.
- Added safe margins, optional snap-to-grid behavior, snap guides, and spacing
  guides.
- Added left-click selected-rail position controls with arrow nudges, numeric
  X/Y coordinates, and Reset.
- Added Sticky Frames behavior so dragged rails can snap to other rails for
  quick alignment.
- Persisted edited layout offsets and saveable layout values to user presets or
  user override sidecars for read-only built-in/studio presets.
- Removed the right-click frame options popover so Edit Mode stays focused on
  whole-rail layout editing.

Done when an artist can recreate the reference stack and create a distinct rail
layout from Maya UI only, then save those changes outside locked built-in
presets.

Research hints:

- Compare WoW Edit Mode and Dominos configuration mode for drag-to-position,
  per-bar scale/opacity/spacing, and safe unlock behavior.
- Look at Maya guide/snap UX before designing ActionRail grid and snap guides;
  viewport tools should feel precise, quiet, optional, and non-decorative.
- Use the attached edit-mode reference for frame selection semantics:
  left-click opens precise X/Y placement controls, Sticky Frames snaps frames
  together, and Grid Size controls the edit-only grid.
- Revisit the local `research/` reference images when tuning hit boxes and
  spacing for the transform-stack regression target.

#### 2.6 Collapsible Edge Tabs And Authoring Workflow Polish

Status: in progress. The first runtime/persistence slice is implemented and
Maya-smoke verified for the optional `collapse` schema, Quick Create edge-tab
template/settings, small collapsed Qt handles, click/hover reveal hooks, Edit
Mode collapse/expand toggling, user-preset round-trips, and in-memory hotkey
label retention while collapsed. A focused Maya-smoke verified polish pass now
improves collapsed-handle size/edge placement, adds publish-facing diagnostics,
blocks Quick Create saves with diagnostic errors, and can publish saved Quick
Create presets to slot runtime commands plus an idempotent shelf toggle. A
local validation UX follow-up now uses publish diagnostics in Quick Create
Validate Draft, includes the concrete blocking issue in save errors, reports
stale slot-command cleanup from Save + Publish, and preserves custom user
preset stores in published shelf toggles; Quick Create draft conversion also
infers active-state predicates for persistent Maya tool actions while leaving
one-shot commands inactive. Guide polish now draws axis-aligned Sticky Frames
guides. The old Edit Mode frame options popover and slot payload editor have
been removed; slot payload assignment/clear now belongs to Normal Mode rail
lock/unlock helpers, and unlocked populated slots can now be Shift-dragged to
move/swap payloads or clear them when released anywhere that is not a
different slot. Edit Mode panel polish now exposes selected rail state as a
clickable Lock/Unlock action and lets the compact panel be dragged away from
covered rails. The Quick Create Maya smoke verifies the Save + Publish shelf
command carries that custom store path.

Architecture note: publishing remains the runtime-command/shelf implementation
path for saved bindings and optional Maya integration. It should not be the
center of the artist workflow. The user-facing loop should read as: choose a
frame/template, fill slots from an Action Book or Macro Book, place/configure in
Edit Mode, bind slots in Bind Mode, then save.

- Add collapsible rail settings: edge, handle icon, reveal trigger, and default
  collapsed state. First pass done through `RailCollapse` / JSON `collapse`.
- Render a small edge handle when collapsed without creating a viewport-sized
  transparent hit area. First pass done through a handle-only overlay widget;
  hit-target and placement polish now uses larger edge handles that hug the
  viewport side and preserve only tangent layout offset while collapsed.
- Preserve actions, runtime-command publishing, and hotkey labels while a rail
  is collapsed. First pass done for no-overlay slot execution and visible label
  restoration after expand.
- Surface validation for missing actions, missing icons, and hotkey conflicts
  before save or publish. First publish-facing diagnostics pass is done through
  `diagnose_publish_spec()` and Quick Create save validation; Quick Create
  Validate Draft now surfaces the same publish diagnostics locally before save.
- Publish saved user presets to shelf/hotkey/runtime command where useful, but
  keep this optional and secondary to the Action Book / Edit Mode / Bind Mode
  workflow.
  First pass is done for slot runtime-command publishing and preset shelf-toggle
  publishing from Quick Create Save + Publish; custom user preset store paths
  are preserved in published shelf toggles, and stale slot-command cleanup is
  reported. Slot binding-target metadata is exposed for saved bars as the
  Phase 2 bridge to Maya's Hotkey Editor and future Bind Mode. Explicit
  hotkey assignment remains Bind Mode territory.
- Keep Edit Mode layout-only. Slot payload changes belong to Normal Mode rail
  lock/unlock helpers, not the Edit Mode layout map. Context-menu
  assignment/clear and Shift-drag move/swap/clear-out are implemented for
  unlocked Normal Mode rails; locking the rail returns populated slot clicks to
  normal action execution. Quick Create now exposes this as an `Edit Slots`
  handoff for the current draft, keeping bar creation, frame placement, and
  slot editing connected to the first Action Book placement slice without
  starting Bind Mode.
- Keep Quick Create minimal. Its current default is a blank action bar, and its
  Slots tab edits only slot id, label, and displayed key text. Do not add
  Action/Icon assignment browsing back into Quick Create; action placement
  belongs to a separate Action Book surface that can feed unlocked
  slots through the same slot-edit workflow.
- Add the first separate Action Book placement surface. Done as a
  dockable Maya panel that searches Action Book entries, displays their action
  bar icons and brief tooltips, lets users click entries to run the Maya action,
  and drags Action Book MIME payloads onto unlocked Normal Mode slots.
- Make Edit Mode controls practical in dense viewports. First panel polish is
  Maya-smoke verified: the selected rail button now says Lock or Unlock and
  toggles whether that rail can move in the current Edit Mode session, while
  the compact panel itself can be dragged aside when it covers a rail.

Done when an artist can collapse a custom action bar frame to a side handle,
expand it again, and keep layout, actions, and bindings intact.

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

## Phase 3: Action Book, Bind Mode, Macro Book, Flyouts, And Command Rings

Goal: complete the WoW-style authoring loop: browse Maya actions like a
WoW-inspired action browser, place them on action bar slots, bind keys by hovering a slot, create
user macro actions with icons, and then add compact grouped access patterns.

### Tasks

- Searchable Action Book for curated Maya tools, commands, shelf imports,
  studio tools, and user macros. First curated Maya-action placement slice is
  implemented in Phase 2.6; shelf imports, studio providers, and macro entries
  remain future work.
- Hover-to-bind Bind Mode.
- Slot conflict warnings and clear-binding command.
- Macro Book for user-authored Python/MEL actions with stable ids, icons,
  tooltips, and optional safe predicates.
- Flyout widget for grouped related actions.
- Command ring widget for radial press/hold/release workflows.
- Press/release hotkey behavior with Maya focus handling verification.

### Acceptance Criteria

- A user can assign a Maya action from the Action Book to an empty slot.
- A user can enter Bind Mode, hover a slot, press a shortcut, and see the key label update.
- A user can create a simple macro action with an icon and place it on a slot.
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

Phase 2 steps 2.1-2.5 are complete and verified locally. The draft authoring
model, safe user-preset storage, shared preset resolver, dockable Quick Create
panel, preview cleanup, load-existing support, save/reload workflow, Edit Mode
layout-map shell, direct manipulation, snap/sticky guides, Normal Mode slot
payload lock/unlock helpers, Quick Create handoffs into both Edit Mode layout
and Normal Mode slot editing, and user override persistence are in place.

Current implementation slice: Phase 2 step 2.6 collapsible edge tabs and
authoring workflow polish. The collapse schema/runtime first pass is implemented and
Maya-smoke verified; the handle/publish polish pass is also Maya-smoke
verified. A local validation UX/saved-preset publishing polish follow-up is in
place, Quick Create Maya smoke now covers the custom-store Save + Publish shelf
command path and the five-template starter set, and the first
guide/slot-edit/control-panel affordance polish pass is Maya-smoke verified.
Quick Create now also has a Maya-smoke verified `Edit Slots` handoff that
previews the current draft, exits Edit Mode, and unlocks the visible bar for
Normal Mode slot payload editing. Quick Create has been narrowed back to a
minimal action-bar creator: it opens on a blank bar, supports adding/removing
slots and layout settings, and no longer exposes action/icon assignment controls
in the Slots tab. The first separate Action Book UI now owns action browsing and
placement: it opens from the ActionRail Maya menu, searches the Action Book
catalog, renders icon-backed entries, runs clicked entries, and drops actions
onto those unlocked Quick Create/Normal Mode slots.
The Action Book backend has also expanded beyond the original transform/key/grid
seed set with Maya-smoke verified selection, viewport, and modeling entries:
Select, Clear Selection, Frame Selection, Toggle Isolate Selected, Center
Pivot, Freeze Transforms, and Delete History. The smoke writes a catalog JSON
artifact for backend review, and the dedicated Action Book UI now renders that
starter set for placement. Stop broadening the catalog one item at a time for
now; treat this as a useful starter set and move the next effort back to
workflow-level architecture.
Carry forward only polish that naturally supports 2.6 and the unified
WoW-style workflow, such as Quick Create round-trip stability, locked
built-in/studio read-only behavior, clearer template-to-Edit-Mode and
template-to-slot-edit handoffs, and slot editing that can later connect to
Action Book and Bind Mode. Keep `docs/06_wow_style_customization.md` in mind,
but do not implement Bind Mode, Macro Book UI, flyouts, command rings, profile
layers, marking-menu export, or Viewport 2.0 yet.

## Research Backlog

See `docs/07_missing_features_research.md` for the current feature-gap report.
The active backlog priorities are:

1. Verify and continue Phase 2 step 2.6 Quick Create stability, locked-preset
   read-only polish, and unified authoring workflow handoff.
2. Add the Action Book and Bind Mode.
3. Add the Macro Book for user script actions with icons.
4. Add flyouts, then command rings.
5. Broaden the workflow action library beyond transform/keyframe.
6. Add profile layers for built-in, studio, project, scene/asset, and user
   overrides.
7. Add marking-menu/hotbox export and later Viewport 2.0 labels/guides.
