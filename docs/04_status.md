---
summary: Live project status for agents: what is done, what is next, blockers, latest handoff, and latest verification.
read_when:
  - Starting work after another agent.
  - Finishing any implementation or research slice.
  - Checking current blockers before editing code.
---

# Status

Last updated: 2026-05-03

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
  - `maya_tools` is a bundled horizontal rail proving Maya resource icons can
    render without copying Autodesk assets into the ActionRail icon manifest.
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

## In Progress

- Phase 2 step 2.2 Dockable Quick Create Panel is next; not started yet.

## Next Agent Start

Start here:

1. Read `../bram-agent-scripts/AGENTS.MD`, then `docs/00_start_here.md`, then this file.
2. First recommended coding slice: begin Phase 2 step 2.2, Dockable Quick
   Create Panel. Use the `DraftRail`/`DraftSlot` helpers from
   `scripts/actionrail/authoring.py` instead of inventing another draft model.
3. Use `scripts/maya-smoke.ps1` for repeatable MayaSessiond smoke runs when feasible.
4. Do not start full Edit Mode, Bind Mode, flyouts, command rings, or Viewport 2.0 yet.

## Latest Handoff

- Task goal completed: Maya built-in icon provider groundwork for future
  macro-style icon selection.
- Files changed in this handoff update: icon provider/runtime resolution,
  diagnostics/project-map exposure, `maya_tools` preset, focused tests, Maya
  smoke coverage, and docs.
- Behavior verified: provider-aware icon descriptors, Maya logical ids,
  manifest icon compatibility, missing Maya resource diagnostics, Qt resource
  icon rendering, coverage-gated full pytest, full Ruff, and full Maya smoke
  all passed.
- Current live state: Presets can reference `maya.move`, `maya.rotate`,
  `maya.scale`, and `maya.set_key` without copying Autodesk assets. Future
  Quick Create work can use `actionrail.list_icon_descriptors()` for
  picker-facing provider/category/keyword metadata.
- Blockers/risks: no implementation blocker known.
- Exact next step: build the Phase 2 step 2.2 dockable Quick Create panel on top
  of the draft/user-preset helpers and the provider-aware icon descriptor list.

## Next

1. Start Phase 2 step 2.2, then continue through the medium Quick Create/Edit
   Mode steps in `docs/02_implementation_plan.md`.
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
  -> 312 passed, `TOTAL 3251 0 100%`.
- Full local checks:
  `.\\.venv\\Scripts\\python.exe -m ruff check .` -> all checks passed.
- Latest full Maya smoke baseline:
  `.\\scripts\\maya-smoke.ps1 -NoStart -Script all` -> passed against the
  already-running MayaSessiond on port `7217`; verified capture, diagnostic
  badges, diagnostics window, hidden visibility, manifest-backed horizontal
  icon rail, hotkey bridge, hotkey label sync, import/recovery diagnostics,
  curated Maya built-in icon rendering, Maya menu/shelf UI, overlay cleanup,
  phase 0, predicates, StackItem ABI, and transform-stack state.
- Latest Maya note: Maya smoke used the installed MCP package in the Sessiond
  venv; do not pass `--mcp-src ../GG_MayaMCP` until the sibling repo
  compatibility blocker is resolved.
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
