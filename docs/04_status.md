---
summary: Live project status for agents: what is done, what is next, blockers, latest handoff, and latest verification.
read_when:
  - Starting work after another agent.
  - Finishing any implementation or research slice.
  - Checking current blockers before editing code.
---

# Status

Last updated: 2026-05-04

## Done

- Reference images were collected in local `research/`; that folder is now ignored by Git.
- README/documentation images live in `docs/assets/`.
- Architecture is documented in `docs/01_architecture.md` and the stack decision in `docs/05_tech_stack.md`.
- Local `AGENTS.MD` updated with ActionRail rules and MayaSessiond workflow.
- Product name selected and docs renamed to ActionRail.
- Agent onboarding docs created:
  - `docs/00_start_here.md`
  - `docs/01_architecture.md`
  - `docs/02_implementation_plan.md`
  - `docs/03_maya_sessiond_workflow.md`
  - `docs/04_status.md`
- Tech stack decision documented in `docs/05_tech_stack.md`.
- Phase 0 prototype implemented:
  - Maya module skeleton: `ActionRail.mod`, `scripts/actionrail`, `icons`, `presets`, `examples`.
  - Lazy PySide6/PySide2 import shim in `scripts/actionrail/qt.py`.
  - Runtime APIs: `actionrail.show_example("transform_stack")`, `actionrail.hide_all()`, `actionrail.reload()`.
  - Viewport overlay host resolves the active Maya model panel's inner viewport-area widget for anchor geometry.
  - Hard-coded `M/T/R/S + K` transform stack matching the research reference.
  - Maya action bindings for move/translate, rotate, scale, and set key.
  - Pure Python unit tests and allowlisted MayaSessiond smoke scripts.
- `docs/03_maya_sessiond_workflow.md` now documents the repo-specific MayaSessiond port rule. Use port `7217` for ActionRail unless it is already in use.
- Phase 1 declarative MVP complete:
  - Built-in examples now load from JSON presets in `presets/`.
  - The public Python builder API is now exposed from `actionrail`: callers can
    construct `StackSpec`, `RailLayout`, and `StackItem` objects directly or use
    `parse_stack_spec()`/`load_preset()`, then render user-authored rails with
    `show_spec()` through the same runtime cleanup registry as built-in
    examples.
  - `presets/transform_stack.json` is the source of truth for the reference stack labels, actions, active predicates, tooltips, spacer, and anchor.
  - Preset parsing validates required ids, anchors, item lists, supported item types, button action fields, and spacer sizes.
  - The Qt stack builder now renders from the spec item stream instead of looking up a hard-coded `K` button.
  - Widget screenshot smoke now captures the ActionRail widget directly instead of the foreground desktop.
  - Theme tokens and generated QSS now live in `scripts/actionrail/theme.py`; the default theme accounts for Qt style-sheet button/frame borders so buttons keep a visible inset inside framed slots.
- Phase 1A rail schema started:
  - Presets now support `layout` metadata: orientation, rows, columns, anchor, offset, scale, opacity, and locked state.
  - Items now support stable slot `id`, `key_label`, and safe declarative `visible_when`, `enabled_when`, and `active_when` predicate fields.
  - `presets/transform_stack.json` has explicit stable slot ids and layout metadata; the current corrected transform-stack render size is `46x214`.
  - `presets/horizontal_tools.json` proves a horizontal rail can be defined without widget-code changes.
  - Overlay positioning now supports left/right/top/bottom/center anchors plus layout offsets.
  - Maya smoke coverage now includes a horizontal rail render check.
- Phase 1B runtime-command bridge started:
  - `actionrail.run_action(action_id)` runs registered actions without requiring an overlay.
  - `actionrail.run_slot(preset_id, slot_id)` runs action-bearing preset slots by stable slot id.
  - `actionrail.hotkeys` can publish default actions and preset slots as Maya runtime commands plus paired nameCommands for hotkey assignment.
  - Hotkey assignment now has conflict-aware helpers that refuse to overwrite existing bindings unless explicitly requested.
  - Slot-aware hotkey assignment now updates visible rendered key labels through the runtime overlay registry.
  - Overwrite rebinding clears the previously bound visible ActionRail slot label so stale shortcut badges are not left behind.
  - Explicit runtime-command sync helpers now publish the current default actions or preset slots and remove stale generated ActionRail commands for renamed/removed ids.
  - A safe predicate evaluator now drives initial `visible_when`, `enabled_when`, and `active_when` state from Maya selection/tool/panel/camera/playback state plus action, command, and plugin availability checks.
  - `ViewportOverlayHost.refresh_state()` now refreshes predicate-driven enabled/active button state from the current Maya state and rebuilds the rail when `visible_when` changes, preserving rendered key labels where possible.
  - Predicate state snapshots now receive the overlay's resolved model panel, so `active.panel` and `active.camera` match explicit `panel=` targets and model-panel fallback instead of whatever UI control currently has focus.
  - Overlay anchoring now prefers the inner `modelPanel` viewport-area widget instead of the outer model-panel container.
  - Overlay creation now removes stale ActionRail Qt widgets for the same preset before creating a replacement rail, preventing duplicate rails after reload/show cycles or interrupted live development.
  - Stale overlay cleanup now closes owning hosts when possible, event filters keep weak host references, and `position()` returns early for deleted Qt objects so resize/layout callbacks do not touch deleted `_ActionRailRoot` instances.
  - The visible rail now uses a small frameless Maya-owned tool window positioned from the resolved viewport geometry instead of being parented directly under the OpenGL viewport widget, avoiding model-panel toolbar repaint ghosts without covering the viewport.
  - Visible overlay hosts now start a host-owned Qt timer that automatically calls `ViewportOverlayHost.refresh_state()` while the rail is visible, so predicate-driven active/enabled/visible state updates after Maya tool or selection changes without manual refresh calls.
  - Action-bearing buttons now resolve through reusable `SlotRenderState` objects and a shared apply path for label, hotkey badge, tone, tooltip, enabled, and active state. Predicate refresh preserves runtime hotkey badge overrides while updating state in place when visibility is unchanged.
  - Active color is now a generic theme state applied through `actionRailActive="true"` after `active_when` evaluates true. Built-in tool slots declare active predicates; one-shot macro buttons such as Set Key do not.
  - Preset slots may intentionally omit `action`; these unassigned placeholders render disabled/locked, are skipped by action id validation and hotkey publishing, and do not show missing-action diagnostics. The demo transform stack keeps `M` as the active move slot while `T` is an unassigned locked placeholder.
  - Optional slot `icon` ids now resolve through the icon manifest, and `SlotRenderState` carries icon path plus diagnostic code/severity/badge state. Missing actions render disabled with an error badge; missing icons render warning badges while leaving actions enabled.
  - `horizontal_tools` is now the first manifest-backed icon rail, with
    first-party SVG icons for move, rotate, scale, and set key.
  - `actionrail.icons` now has a provider-aware icon descriptor layer for future
    picker UIs. It supports manifest-backed ids such as `actionrail.move` and
    curated Maya built-in resource ids such as `maya.move`, `maya.rotate`,
    `maya.scale`, and `maya.set_key`.
  - The icon subsystem is split behind the public `actionrail.icons` facade:
    `icon_catalog` owns provider descriptors and read-only lookup,
    `icon_manifest` owns manifest storage/validation, `icon_import` owns SVG
    import preflight and writes, `icon_svg` owns SVG safety,
    `icon_fallbacks` owns PNG fallback generation/mayapy rendering, and
    `icon_types`/`icon_paths` own shared contracts and storage paths. Quick
    Create icon picker work should depend on the catalog, not import/write or
    fallback rendering code.
  - `maya_tools` is a bundled horizontal rail proving Maya resource icons can
    render without copying Autodesk assets into the ActionRail icon manifest.
  - Maya icon descriptors and diagnostics keep raw resource names such as
    `move_M.png`, while widget rendering uses Qt resource URLs such as
    `:/move_M.png`. Slot icons now fill the inner button area and labels,
    hotkey text, and diagnostic badges draw over the icon.
  - Icon diagnostics now validate manifest metadata, duplicate ids, invalid
    local paths, missing files, unknown icon ids, invalid SVG files, and unsafe
    SVG content before widget rendering resolves an icon path.
  - `actionrail.icons.import_svg_icon()` now validates local SVG sources,
    copies safe assets under `icons/`, and upserts source, license, URL,
    import-date, and manifest path metadata into `icons/manifest.json`.
  - SVG import safety now rejects external resources declared inside SVG
    `<style>` blocks, and import overwrite checks compare normalized manifest
    paths so equivalent `icons/...` and package-relative paths cannot alias the
    same asset across two ids.
  - `actionrail.icons.generate_png_fallbacks()` now generates 1x/2x/3x PNG
    fallbacks for manifest SVG icons, `import_svg_icon()` can generate those
    fallbacks at import time, and manifest diagnostics report missing or stale
    generated fallback assets.
  - `actionrail.icons.import_svg_icon()` now rolls back copied SVG and PNG
    fallback asset changes when fallback generation fails, so failed imports do
    not leave orphan files or stale manifest/file mismatches.
  - First-party ActionRail SVG icons now have checked-in `@1x`, `@2x`, and
    `@3x` PNG fallback assets recorded in `icons/manifest.json`.
  - `actionrail.icons.validate_svg_icon_import()` now preflights local SVG
    imports without writing files and returns structured issues for bad source
    files, import metadata, target paths, duplicate ids, path conflicts,
    unsafe SVGs, and existing target assets.
  - `actionrail.diagnose_icon_import()` records those import preflight issues
    as the latest copyable diagnostics report, and `DiagnosticIssue` now carries
    optional `path` and `field` details for import/manifest problems.
  - SVG import preflight now reports generated PNG fallback target conflicts
    before writing files, including orphaned fallback files and fallback paths
    already owned by another manifest icon.
  - Report-backed and Maya-facing icon import diagnostics now honor
    `generate_fallbacks=False`, so preflight reports match imports that
    intentionally skip PNG fallback generation.
  - `actionrail.safe_start(..., fallback_preset_id="transform_stack")` can now
    opt in to recovering from a broken requested preset by starting a
    diagnostics-clean fallback preset while preserving the original errors in
    the report.
  - `tests/maya_smoke/actionrail_import_recovery_smoke.py` now verifies import
    diagnostics in the Qt report window with a saved screenshot and verifies
    fallback preset startup recovery in Maya.
  - Missing `command.exists(...)` and `plugin.exists(...)` predicate targets now render disabled warning badges on affected slots. Slots hidden only by a missing command/plugin availability predicate are kept visible so broken dependencies are not silent, while compound context clauses and negated availability checks keep their declared predicate semantics.
  - `StackItem(...)` preserves the documented Python API positional constructor order through `tone`; optional `icon` support is appended after existing fields so JSON presets and Python callers both remain compatible.
  - Diagnostic entry points now remember the latest `DiagnosticReport`, expose
    `actionrail.last_report()`, `actionrail.clear_last_report()`,
    `actionrail.format_report()`, and `actionrail.show_last_report()`, and add a
    Maya menu item for showing the latest report.
  - `actionrail.show_last_report()` now opens a themed ActionRail Qt diagnostics
    window with a summary, warning/error issue list, selectable full report text,
    and `Copy Selected`, `Copy Full Report`, `Clear`, and `Close` actions.
  - The diagnostics window now includes a `Hide Overlays` support action wired
    to the runtime overlay registry, so users can dismiss active ActionRail
    overlays from the same report surface when diagnosing stuck or broken UI.
    The support action hides each active overlay under its own exception guard,
    so one broken close does not prevent later overlays from being dismissed.
  - The diagnostics window now includes a severity filter for large reports, so
    users can switch the visible issue list between all issues, errors,
    warnings, and info entries while keeping copyable selected-issue details
    and the full report intact.
  - Diagnostic reports now include published ActionRail runtime-command names,
    the diagnostics window summary shows the published command count, and
    stale generated action/slot runtime commands are reported as warning issues
    with sync/unpublish hints.
  - Diagnostic reports now include compact active overlay support state,
    including panel, widget visibility/validity, event-filter target count, and
    predicate refresh timer state. The diagnostics window summary shows
    aggregate event-filter and refresh-timer counts.
  - Copyable diagnostic reports and selected issue details now include
    structured `path` and `field` values, so icon import and manifest problems
    expose the exact source/target path and metadata field in the diagnostics
    window.
  - Icon import and manifest diagnostics now carry structured `hint` text, so
    the full report and selected-issue copy text include remediation guidance
    such as choosing a valid SVG, using `overwrite=True`, or regenerating PNG
    fallbacks.
  - `DiagnosticIssue(...)` preserves the public positional constructor order
    through `exception_type`; optional `hint` support is appended after existing
    fields while report and diagnostics-window display order still shows hints
    before exception details.
  - `cmds.hotkey` query now follows Maya's positional-key query form while preserving keyword-based assignment.
  - Maya smoke coverage now validates runtime command execution for an action and a preset slot with no overlay visible.
  - Maya smoke coverage now validates key-label sync on a visible slot after hotkey assignment.
  - Maya smoke coverage now validates the real transform-stack button-state sequence: M/R/S switch active state, T is a locked unassigned placeholder, and K remains a one-shot keyframe button.
- Maya-native UI entry point:
  - `actionrail.toggle_default()` shows the default `transform_stack` preset when hidden and hides it when visible.
  - `actionrail.install_menu_toggle()` and `actionrail.uninstall_menu_toggle()` manage an idempotent Maya menu item.
  - The ActionRail Maya menu includes `Diagnose SVG Icon Import...`, which
    chooses a local SVG, prompts for an icon id, runs the non-writing icon
    import preflight, records the latest report, and opens the themed
    diagnostics window. The same flow can be driven directly through
    `actionrail.diagnose_icon_import_from_maya(...)`.
  - The ActionRail Maya menu now includes `Run Diagnostics`, which collects a
    fresh bundled preset/icon diagnostics report, records it as the latest
    report, and opens the themed diagnostics window. The same flow can be
    driven directly through `actionrail.run_diagnostics_from_maya()`.
  - `actionrail.install_shelf_toggle()` and `actionrail.uninstall_shelf_toggle()` manage an idempotent Maya shelf button.
  - `tests/maya_smoke/actionrail_maya_ui_smoke.py` verifies menu/shelf command text, run diagnostics and icon import diagnostics command text, idempotent reinstall, toggle show/hide, and uninstall cleanup in Maya.
- Reusable Maya smoke wrapper:
  - `scripts/maya-smoke.ps1` wraps the stable MayaSessiond command shape for checked-in smoke scripts.
  - The wrapper uses repo-local state, starts Sessiond only when needed, passes the repo module path and absolute smoke-script directory, discovers MCP tools before running, and fails on either MCP-call or script-payload failure.
  - `tests/maya_smoke/actionrail_cleanup_state.py` runs before and after each wrapper-selected smoke to close runtime overlays, close smoke-owned hosts, remove stale ActionRail Qt widgets, reset the Maya scene, and purge cached `actionrail` modules so live daemon runs load current files.
  - The wrapper validates that `script.execute` returned a payload for the requested script and retries transient stale-payload or JSON transport failures.
  - The wrapper now treats a stopped Sessiond status response as a valid startable state instead of aborting before launch.
  - `-Script all` runs all `tests/maya_smoke/*_smoke.py`; individual script names can be passed with or without `.py`.
- Safe-mode diagnostics:
  - `actionrail.collect_diagnostics()` validates bundled presets without showing an overlay.
  - `actionrail.diagnose_spec()` reports missing actions, invalid predicates, and missing command/plugin predicate targets for parsed specs.
  - `actionrail.safe_start()` validates first, starts the overlay only when there are no diagnostic errors, returns recoverable overlay startup failures as report issues, and resolves importable `maya.cmds` automatically for default command/plugin availability diagnostics.
  - `tests/maya_smoke/actionrail_diagnostics_smoke.py` verifies diagnostics and `safe_start()` inside Maya.
- Test/docs hardening:
  - Slot diagnostic internals now use a private named diagnostic value instead
    of positional tuples, and stale overlay cleanup is split into focused
    private discovery/close/delete helpers without changing public APIs.
  - Schema tests now cover duplicate slot ids and boolean values incorrectly accepted as integer layout/spacer fields.
  - Runtime tests now cover unknown slots and slots without actions.
  - Hotkey tests now cover idempotent publishing, same-binding assignment, release bindings, command modifiers, conflict text, and unpublish behavior.
  - Overlay tests now cover active model-panel fallback behavior.
  - Icon manifest tests now guard the expected metadata shape.
  - `actionrail.about()` and `python -m actionrail --json` now expose a
    JSON-safe project map with public APIs, built-in presets/actions, doc
    routing, module ownership, icon manifest health, and verification commands.
  - `docs/04_status.md` is now the compact live status file; older verification
    details live in `docs/history/verification_log.md`.
  - Pure-Python package coverage is now 100% line coverage for
    `scripts/actionrail` and `.coveragerc` enforces `fail_under = 100`.
- WoW-style customization direction documented:
  - `docs/06_wow_style_customization.md` defines Edit Mode, action slots, Bind Mode, flyouts, command rings, profiles, visibility rules, schema direction, and phased roadmap.
  - `docs/01_architecture.md` and `docs/02_implementation_plan.md` now reserve room for stable slot ids, runtime-command hotkeys, user/project/studio layers, and later radial/flyout controls.
- Missing-features research documented:
  - `docs/07_missing_features_research.md` captures current feature gaps, source-backed recommendations, and a prioritized roadmap for stateful predicates, hotkey label sync, Edit/Bind Mode, flyouts, command rings, icon pipeline, diagnostics, profiles, marking-menu export, and later Viewport 2.0 labels/guides.
  - `docs/00_start_here.md` and `docs/02_implementation_plan.md` link to the new research backlog.
- Product scope clarified:
  - `M/T/R/S/K` is documented as the first proof preset and regression target, not the boundary of ActionRail.
  - The docs now state that the product goal is user-authored rails, slots, hotkey badges, flyouts, and command layouts.
- Phase 2 step 2.1 authoring model and user-preset storage complete:
  - `scripts/actionrail/authoring.py` defines `DraftRail` and `DraftSlot` as
    the narrow Quick Create draft model that validates into the existing
    `StackSpec`, `RailLayout`, and `StackItem` runtime schema.
  - `actionrail.save_user_preset()` and `actionrail.load_user_preset()` save and
    reload user presets from a user storage path separate from locked built-in
    presets. The storage path is injectable for tests and honors
    `ACTIONRAIL_USER_PRESET_DIR`.
  - User preset saves validate file-safe ids, prevent overwriting bundled preset
    ids such as `transform_stack`, and round-trip through the existing JSON
    preset parser before writing.
  - `actionrail.collect_diagnostics()` now scans saved user preset files and
    reports malformed or otherwise broken user presets as warnings, so bundled
    preset diagnostics and startup are not blocked by a bad saved user file.
  - `actionrail.about()` now lists the authoring module and current user preset
    storage summary.
- User presets are now first-class runtime/hotkey targets:
  - `scripts/actionrail/preset_store.py` provides `PresetStore`,
    `resolve_preset()`, `preset_ids()`, and `preset_entries()` for shared
    bundled/user preset id resolution.
  - `actionrail.show_preset()`, `show_example()`, `reload()`, and `run_slot()`
    resolve saved user presets by id; `toggle_default()` uses the same runtime
    preset path.
  - `actionrail.hotkeys.publish_preset_slots()` and `sync_preset_slots()` can
    publish/sync saved user preset slots by id, and persisted slot nameCommand
    fallback can resolve saved user slots in the current user preset store.
  - Published slot runtime commands now preserve explicit `user_preset_dir`
    values in the generated `actionrail.run_slot(...)` command, and persisted
    nameCommand fallback parses the saved runtime-command payload before using
    legacy runtime-name splitting. Custom stores and dotted/hyphenated preset
    ids therefore survive Maya restart and hotkey overwrite flows.
  - Runtime-command diagnostics honor a stored `user_preset_dir` on published
    slot commands when checking saved-user slots for stale/orphaned targets.
  - Diagnostics now use the shared store for explicit preset ids, saved-user
    scans, `safe_start(..., user_preset_dir=...)`, and stale runtime-command
    checks, so a published saved-user slot is not reported as orphaned.
  - `actionrail.about()` now includes the shared preset store module and a
    combined preset id summary.
- Public-contract test hardening:
  - `actionrail.widgets.resolve_slot_render_state()` exposes the public
    `SlotRenderState` contract without requiring tests to import the private
    resolver.
  - Slot render-state resolution now lives in pure `actionrail.slot_state`;
    `widgets.py` keeps Qt construction/painting focused while preserving
    compatibility wrappers for `build_transform_stack()` and
    `resolve_slot_render_state()`.
  - `actionrail.active_overlay_ids()` and `actionrail.active_overlay_states()`
    are now top-level public helpers for tests, diagnostics, and smoke scripts.
  - Hotkey tests isolate published-command memory through public
    `PublishedCommand`/`unpublish()` paths instead of a private cache reset.
  - Maya UI and diagnostics smoke tests assert overlay visibility/validity
    through public overlay state instead of runtime `_OVERLAYS`.
- Phase 2 step 2.2 Dockable Quick Create Panel complete:
  - `scripts/actionrail/quick_create.py` defines Phase 2.2 template choices,
    picker-facing action/icon data, editable Quick Create values, and conversion
    into the existing `DraftRail`/`DraftSlot` authoring model.
  - Templates cover vertical stack, horizontal strip, and an edge-tab rail
    starter without adding flyout, command-ring, or collapse runtime behavior.
  - `scripts/actionrail/quick_create_ui.py` provides the Maya-hosted Qt Quick
    Create panel for preset id, template, anchor, orientation, rows/columns,
    offset, scale, opacity, lock state, slot labels, key labels, actions, icons,
    and draft validation.
  - The ActionRail Maya menu now includes `Quick Create...`, which opens a
    workspace-control panel through `actionrail.show_quick_create_panel()`;
    workspace-control restore uses `actionrail.restore_quick_create_panel()`.
  - `tests/maya_smoke/actionrail_quick_create_smoke.py` opens the new UI in
    Maya, switches templates, validates the produced draft, and saves panel
    screenshots for the General, Layout, and Slots tabs under
    `.gg-maya-sessiond/screenshots/`.
- Phase 2 step 2.3 Preview And Save Workflow complete:
  - `actionrail.preview_quick_create_draft()` converts a Quick Create draft into
    a validated runtime spec, records diagnostics for broken drafts, previews it
    through the normal Qt overlay runtime, and tracks preview ids for cleanup.
  - `actionrail.clear_quick_create_previews()` hides active preview overlays
    without requiring the draft to be saved.
  - `actionrail.save_quick_create_preset()` saves the current draft through the
    existing user-preset writer, preserves stable preset and slot ids, clears
    matching previews, and shows the saved preset through the normal user preset
    resolver without closing unrelated overlays.
  - User-preset saves now require explicit overwrite for existing files; Quick
    Create exposes separate Save Preset and Overwrite Preset actions.
  - `actionrail.load_quick_create_preset()` loads saved user presets back into
    editable Quick Create values without allowing locked built-in presets to be
    edited.
  - The Quick Create panel now has Preview, Clear Preview, Save Preset,
    Overwrite Preset, and Load Existing actions, and smoke coverage verifies
    preview, save, explicit overwrite, load, reload, and screenshot capture in
    Maya.
- Phase 2 step 2.4 Edit Mode Shell And Rail Selection complete for the first
  shell slice:
  - `scripts/actionrail/edit_mode.py` adds the public Edit Mode state model,
    global toggle, edit-only layout-map overlay, grid settings, rail frame
    discovery, selected-rail state, and compact X/Y position popover.
  - Public APIs now include `actionrail.toggle_edit_mode()`,
    `enter_edit_mode()`, `exit_edit_mode()`, `edit_mode_state()`,
    `set_edit_mode_options()`, and `select_edit_mode_rail()`.
  - The ActionRail Maya menu includes `Toggle Edit Mode`.
  - Edit Mode draws active rails as labeled translucent frame rectangles over a
    grid, shows Grid, Grid Size, Snap to Grid, Sticky Frames, and locked state,
    supports left-click frame selection, records right-click frame options
    routing, allows non-persistent X/Y nudging/reset for unlocked active rails,
    and applies in-session snap-to-grid/sticky-frame alignment during edit
    movement.
  - `tests/maya_smoke/actionrail_edit_mode_smoke.py` verifies the Maya-facing
    layout-map overlay, grid/settings controls, left-click selection, X
    coordinate movement, right-click options routing, and screenshot capture.
  - `scripts/maya-smoke.ps1` now accepts Sessiond structured payloads that omit
    `success` when they explicitly report `errors: null`, matching the current
    cleanup payload shape.

## In Progress

- Phase 2 step 2.5 Layout Editing And Direct Manipulation is next.

## Next Agent Start

Start here:

1. Read `../bram-agent-scripts/AGENTS.MD`, then `docs/00_start_here.md`, then this file.
2. First recommended coding slice: begin Phase 2 step 2.5 Layout Editing And
   Direct Manipulation. Persist edited rail offsets to user presets or user
   overrides, add snap/spacing guides, and expand right-click frame routing into
   the options surface without starting Bind Mode or flyouts.
3. Use `scripts/maya-smoke.ps1` for repeatable MayaSessiond smoke runs when feasible.
4. Do not start full Edit Mode, Bind Mode, flyouts, command rings, or Viewport 2.0 yet.

## Latest Handoff

- Task goal completed: Phase 2 step 2.4 Edit Mode shell and rail selection has
  its first implementation and Maya screenshot verification.
- Implemented Edit Mode shell:
  - Public state/options APIs and Maya menu toggle.
  - Edit-only layout-map overlay with visible grid, Grid Size, Snap to Grid,
    Sticky Frames, source-layer/lock display, and translucent rail frame
    footprints.
  - Left-click selection, selected-frame X/Y popover with arrow nudges and
    Reset, and right-click options routing marker.
  - Non-persistent in-session offset movement for unlocked active rails,
    including snap-to-grid and sticky-frame edge alignment.
- Verification hardening: `scripts/maya-smoke.ps1` now accepts Sessiond
  structured payloads without `success` when they explicitly report
  `errors: null`, matching the current cleanup payload shape.
- Current live state: Quick Create can preview/save/load; Edit Mode can inspect
  and temporarily position active rails in the viewport layout-map view with
  snap-to-grid and sticky-frame alignment; saved layout persistence and fuller
  frame options are next.
- Blockers/risks: no implementation blocker known.
- Exact next step: begin Phase 2 step 2.5 layout editing/direct manipulation
  on top of the verified Edit Mode shell.

## Next

1. Start Phase 2 step 2.5 layout editing/direct manipulation, then continue
   through the medium Quick Create/Edit Mode steps in
   `docs/02_implementation_plan.md`.
2. Keep `actionrail_import_recovery_smoke.py` in the smoke set when changing
   import diagnostics, diagnostics-window behavior, or safe-start recovery.
3. Use `scripts/maya-smoke.ps1` for repeatable MayaSessiond smoke runs when feasible.
4. Use `docs/06_wow_style_customization.md` and
   `docs/07_missing_features_research.md` to prioritize later authoring, icon,
   profile, flyout/ring, marking-menu, and Viewport 2.0 work.

## Blockers

- No ActionRail implementation blocker known.
- `GG_MayaSessiond doctor --mcp-src ../GG_MayaMCP` is currently blocked by a sibling repo compatibility lock: sessiond expects GG_MayaMCP commit `2e7a28df7f4d029d81f6421549fb23cb056c4693` / version `0.4.0`, while `../GG_MayaMCP` is at `637954c0510296543126c6504dd445f066eb4559` / version `0.4.1`.
- Workaround used for verification: omit `--mcp-src` so sessiond uses the MCP package installed in its venv. `doctor` passes in that mode.

## Latest Verification

- Coverage gate:
  `.\\.venv\\Scripts\\python.exe -m coverage run -m pytest; .\\.venv\\Scripts\\python.exe -m coverage report`
  -> 395 passed, `TOTAL 4145 0 100%`.
- Full local checks:
  `.\\.venv\\Scripts\\python.exe -m ruff check .` -> all checks passed.
- Edit Mode Maya smoke:
  `.\\scripts\\maya-smoke.ps1 -StateDir .gg-maya-sessiond-edit -Port 7219 -Script actionrail_edit_mode_smoke.py -Timeout 240 -NoStart`
  -> passed; verified the Edit Mode layout-map overlay, Grid Size 64,
  Snap to Grid and Sticky Frames settings, left-click selection, X coordinate
  movement, sticky-frame edge alignment, right-click options routing, and
  screenshot capture at
  `.gg-maya-sessiond/screenshots/actionrail_edit_mode_layout_map.png`.
- Full Maya smoke baseline:
  `.\\scripts\\maya-smoke.ps1 -StateDir .gg-maya-sessiond-edit -Port 7219 -Script all -Timeout 240 -NoStart`
  -> passed against a separate MayaSessiond on port `7219`; verified capture,
  diagnostic badges, diagnostics window copy actions, hidden visibility,
  Edit Mode layout-map screenshot and sticky-frame alignment, horizontal icon
  rail, hotkey bridge, hotkey label sync, import/recovery diagnostics, Maya
  icons, menu/shelf UI, missing Maya icon resources, overlay cleanup, phase 0,
  predicates, Quick Create save/overwrite/load screenshots, StackItem ABI, and
  transform-stack state.
- Screenshot inspection:
  `.gg-maya-sessiond/screenshots/actionrail_edit_mode_layout_map.png`,
  `.gg-maya-sessiond/screenshots/actionrail_quick_create_panel.png`,
  `.gg-maya-sessiond/screenshots/actionrail_diagnostics_window.png`, and
  `.gg-maya-sessiond/screenshots/actionrail_horizontal_tools_widget.png`
  rendered correctly after the full smoke run.
- Latest Maya note: Maya smoke used the installed MCP package in the Sessiond
  venv; do not pass `--mcp-src ../GG_MayaMCP` until the sibling repo
  compatibility blocker is resolved. The `.gg-maya-sessiond-edit` daemon used
  for this verification was stopped after the run.
- Full historical verification log moved to `docs/history/verification_log.md`.

## Decisions

- PySide6/Qt overlay is the MVP path.
- Viewport 2.0 is deferred until Qt overlay is stable.
- Designer/Quick Create is deferred until Phase 0 and declarative MVP are stable.
- WoW-style customization is the long-term authoring model: Edit Mode, action slots, hover-to-bind hotkeys, flyouts, command rings, and preset/profile layers.
- Treat `M/T/R/S/K` as a proof preset and regression target; ActionRail's product goal is broader user-authored viewport UI.
- Build the hotkey bridge through Maya runtime commands so bindings remain visible to Maya and not only to ActionRail.
- Use `GG_MayaSessiond` for live Maya verification when feasible.
- Use `ActionRail` for product/module naming and `actionrail` for Python package/API naming.
- Use Python 3.11 in Maya, PySide6/Qt Widgets, custom Qt rail overlay, `maya.cmds`, OpenMayaUI, JSON specs, SVG icons, `.mod` packaging, and MayaSessiond verification.
- Spike Autodesk `moverlay` before committing to any overlay helper.
- Keep web tech out of the core runtime; use it only for authoring/import tooling.
