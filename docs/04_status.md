---
summary: Live project status for agents: what is done, what is next, blockers, and verification history.
read_when:
  - Starting work after another agent.
  - Finishing any implementation or research slice.
  - Checking current blockers before editing code.
---

# Status

Last updated: 2026-04-30

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
- Phase 1 declarative MVP started:
  - Built-in examples now load from JSON presets in `presets/`.
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
  - Missing `command.exists(...)` and `plugin.exists(...)` predicate targets now render disabled warning badges on affected slots. Slots hidden only by a missing command/plugin availability predicate are kept visible so broken dependencies are not silent, while compound context clauses and negated availability checks keep their declared predicate semantics.
  - `StackItem(...)` preserves the documented Python API positional constructor order through `tone`; optional `icon` support is appended after existing fields so JSON presets and Python callers both remain compatible.
  - Diagnostic entry points now remember the latest `DiagnosticReport`, expose
    `actionrail.last_report()`, `actionrail.clear_last_report()`,
    `actionrail.format_report()`, and `actionrail.show_last_report()`, and add a
    Maya menu item for showing the latest report.
  - `actionrail.show_last_report()` now opens a themed ActionRail Qt diagnostics
    window with a summary, warning/error issue list, selectable full report text,
    and `Copy Selected`, `Copy Full Report`, `Clear`, and `Close` actions.
  - `cmds.hotkey` query now follows Maya's positional-key query form while preserving keyword-based assignment.
  - Maya smoke coverage now validates runtime command execution for an action and a preset slot with no overlay visible.
  - Maya smoke coverage now validates key-label sync on a visible slot after hotkey assignment.
  - Maya smoke coverage now validates the real transform-stack button-state sequence: M/R/S switch active state, T is a locked unassigned placeholder, and K remains a one-shot keyframe button.
- Maya-native UI entry point:
  - `actionrail.toggle_default()` shows the default `transform_stack` preset when hidden and hides it when visible.
  - `actionrail.install_menu_toggle()` and `actionrail.uninstall_menu_toggle()` manage an idempotent Maya menu item.
  - `actionrail.install_shelf_toggle()` and `actionrail.uninstall_shelf_toggle()` manage an idempotent Maya shelf button.
  - `tests/maya_smoke/actionrail_maya_ui_smoke.py` verifies menu/shelf command text, idempotent reinstall, toggle show/hide, and uninstall cleanup in Maya.
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
  - Schema tests now cover duplicate slot ids and boolean values incorrectly accepted as integer layout/spacer fields.
  - Runtime tests now cover unknown slots and slots without actions.
  - Hotkey tests now cover idempotent publishing, same-binding assignment, release bindings, command modifiers, conflict text, and unpublish behavior.
  - Overlay tests now cover active model-panel fallback behavior.
  - Icon manifest tests now guard the expected metadata shape.
- WoW-style customization direction documented:
  - `docs/06_wow_style_customization.md` defines Edit Mode, action slots, Bind Mode, flyouts, command rings, profiles, visibility rules, schema direction, and phased roadmap.
  - `docs/01_architecture.md` and `docs/02_implementation_plan.md` now reserve room for stable slot ids, runtime-command hotkeys, user/project/studio layers, and later radial/flyout controls.
- Missing-features research documented:
  - `docs/07_missing_features_research.md` captures current feature gaps, source-backed recommendations, and a prioritized roadmap for stateful predicates, hotkey label sync, Edit/Bind Mode, flyouts, command rings, icon pipeline, diagnostics, profiles, marking-menu export, and later Viewport 2.0 labels/guides.
  - `docs/00_start_here.md` and `docs/02_implementation_plan.md` link to the new research backlog.
- Product scope clarified:
  - `M/T/R/S/K` is documented as the first proof preset and regression target, not the boundary of ActionRail.
  - The docs now state that the product goal is user-authored rails, slots, hotkey badges, flyouts, and command layouts.

## In Progress

- Phase 1 declarative MVP.

## Next Agent Start

Start here:

1. Read `../bram-agent-scripts/AGENTS.MD`, then `docs/00_start_here.md`, then this file.
2. First recommended coding slice: continue visible diagnostics toward the
   future icon-backed preset/import path.
3. Use `scripts/maya-smoke.ps1` for repeatable MayaSessiond smoke runs when feasible.
4. Do not start full Edit Mode, Bind Mode, flyouts, command rings, or Viewport 2.0 yet.

Checks already run for the latest transform-stack state smoke:

- `.\\.venv\\Scripts\\python.exe -m ruff check tests\\maya_smoke\\actionrail_transform_stack_state_smoke.py` -> all checks passed.
- `.\\.venv\\Scripts\\python.exe -m pytest` -> 118 passed.
- `.\\scripts\\maya-smoke.ps1 -NoStart -Script actionrail_transform_stack_state_smoke.py` passed against the live MayaSessiond on port `7217`; M/R/S each became the only active slot after click, T stayed disabled/locked/inactive, K set 10 keyframes, and S stayed active after K.

## Latest Handoff

- Task goal completed: added a checked-in Maya smoke for generalized
  transform-stack button-state clicks.
- Files changed in this handoff update:
  `tests/maya_smoke/actionrail_transform_stack_state_smoke.py`,
  `docs/03_maya_sessiond_workflow.md`, and `docs/04_status.md`.
- Behavior verified: using the real `transform_stack` preset, M/R/S each become
  the only active slot after click, T stays disabled/locked/inactive as an
  unassigned placeholder, and K sets keyframes without becoming active.
- Checks run:
  `.\\.venv\\Scripts\\python.exe -m ruff check tests\\maya_smoke\\actionrail_transform_stack_state_smoke.py` -> all checks passed;
  `.\\.venv\\Scripts\\python.exe -m pytest` -> 118 passed;
  `.\\scripts\\maya-smoke.ps1 -NoStart -Script actionrail_transform_stack_state_smoke.py` -> passed against live MayaSessiond on port `7217`.
- Current live state: MayaSessiond is running on port `7217`. The smoke used
  checked-in allowlisted smoke-script paths and cleaned up after itself.
- Blockers/risks: no current implementation blocker known.
- Exact next step: continue the next ActionRail feature slice using the smoke
  wrapper for Maya verification when feasible.

## Next

1. Continue diagnostic work toward the future icon-backed preset/import pipeline.
2. Use the new diagnostics Qt window as the support/error-report surface for those checks.
3. Use `scripts/maya-smoke.ps1` for repeatable MayaSessiond smoke runs when feasible.
4. Use `docs/07_missing_features_research.md` to prioritize later authoring, icon, profile, flyout/ring, marking-menu, and Viewport 2.0 work.

## Blockers

- No ActionRail implementation blocker known.
- `GG_MayaSessiond doctor --mcp-src ../GG_MayaMCP` is currently blocked by a sibling repo compatibility lock: sessiond expects GG_MayaMCP commit `2e7a28df7f4d029d81f6421549fb23cb056c4693` / version `0.4.0`, while `../GG_MayaMCP` is at `637954c0510296543126c6504dd445f066eb4559` / version `0.4.1`.
- Workaround used for verification: omit `--mcp-src` so sessiond uses the MCP package installed in its venv. `doctor` passes in that mode.

## Verification History

- 2026-04-27 local venv:
  - `.\\.venv\\Scripts\\python.exe -m pytest` -> 13 passed.
  - `.\\.venv\\Scripts\\python.exe -m ruff check .` -> all checks passed.
- 2026-04-27 Maya import fallback:
  - `PYTHONPATH=./scripts` with Maya 2025 `mayapy.exe` imported `actionrail 0.1.0`.
  - `PYTHONNOUSERSITE=1` avoids a user-site NumPy 2 warning while importing Maya's PySide6.
- 2026-04-27 MayaSessiond:
  - `doctor --state-dir .gg-maya-sessiond --json` passed when `--mcp-src` was omitted.
  - Started MayaSessiond on ActionRail-specific port `7217`.
  - `scene.info` returned untitled scene, unmodified, fps `24.0`, frame range `1.0-120.0`, up axis `y`.
  - Tool discovery found 71 MCP tools, including `script.execute` and `viewport.capture`.
  - `tests/maya_smoke/actionrail_phase0_smoke.py` passed through `script.execute`: import version `0.1.0`, buttons `M/T/R/S/K`, widget size `40x196`, `K` created 10 keyframes, hide left no active overlays, reload returned one visible `transform_stack`.
  - Re-ran `tests/maya_smoke/actionrail_phase0_smoke.py` with no manual `sys.path` injection; `import actionrail` worked from `--maya-module-path .` and `ActionRail.mod`.
  - `tests/maya_smoke/actionrail_capture_smoke.py` saved overlay screenshot to `.gg-maya-sessiond/actionrail_phase0_overlay.png`; screenshot size `2560x1440`, visible widget size `40x196`, button count `5`.
  - Native `viewport.capture format=png width=640 height=360 show_ornaments=false` returned `size_bytes=2030` for `modelPanel4`.
  - Session stopped cleanly after verification.
- 2026-04-28 local venv:
  - `.\\.venv\\Scripts\\python.exe -m pytest` -> 16 passed.
  - `.\\.venv\\Scripts\\python.exe -m ruff check .` -> all checks passed.
- 2026-04-28 local venv after theme token/QSS generation:
  - `.\\.venv\\Scripts\\python.exe -m pytest` -> 19 passed.
  - `.\\.venv\\Scripts\\python.exe -m ruff check .` -> all checks passed.
- 2026-04-28 MayaSessiond:
  - `doctor --state-dir .gg-maya-sessiond --json` passed when `--mcp-src` was omitted.
  - Started MayaSessiond on port `7217` with `--maya-module-path .` and `--mcp-script-dirs tests/maya_smoke`.
  - Tool discovery found 71 MCP tools, including `script.execute` and `viewport.capture`.
  - `scene.info` returned untitled scene, fps `24.0`, frame range `1.0-120.0`, up axis `y`.
  - `tests/maya_smoke/actionrail_phase0_smoke.py` passed through `script.execute`: import version `0.1.0`, buttons `M/T/R/S/K`, widget size `40x196`, `K` created 10 keyframes, hide left no active overlays, reload returned one visible `transform_stack`.
  - `tests/maya_smoke/actionrail_capture_smoke.py` saved direct widget screenshot to `.gg-maya-sessiond/actionrail_phase0_overlay.png`; screenshot size `40x196`, visible widget size `40x196`, button count `5`.
  - Native `viewport.capture format=png width=640 height=360 show_ornaments=false` returned `size_bytes=2030` for `modelPanel4`.
- 2026-04-28 MayaSessiond after theme token/QSS generation:
  - `doctor --state-dir .gg-maya-sessiond --json` passed when `--mcp-src` was omitted.
  - Started MayaSessiond on port `7217` with `--maya-module-path .` and `--mcp-script-dirs tests/maya_smoke`.
  - Tool discovery found 71 MCP tools, including `script.execute` and `viewport.capture`.
  - `scene.info` returned untitled scene, unmodified, fps `24.0`, frame range `1.0-120.0`, up axis `y`.
  - `tests/maya_smoke/actionrail_phase0_smoke.py` passed through `script.execute`: import version `0.1.0`, buttons `M/T/R/S/K`, widget size `40x196`, `K` created 10 keyframes, hide left no active overlays, reload returned one visible `transform_stack`.
  - `tests/maya_smoke/actionrail_capture_smoke.py` saved direct widget screenshot to `.gg-maya-sessiond/actionrail_phase0_overlay.png`; screenshot size `40x196`, visible widget size `40x196`, button count `5`.
- 2026-04-28 local venv after Phase 1A rail schema:
  - `.\\.venv\\Scripts\\python.exe -m pytest` -> 24 passed.
  - `.\\.venv\\Scripts\\python.exe -m ruff check .` -> all checks passed.
- 2026-04-28 MayaSessiond after Phase 1A rail schema:
  - `doctor --state-dir .gg-maya-sessiond --json` passed when `--mcp-src` was omitted.
  - Started MayaSessiond on port `7217` with `--maya-module-path .` and `--mcp-script-dirs tests/maya_smoke`.
  - Tool discovery found 71 MCP tools, including `script.execute` and `viewport.capture`.
  - `scene.info` returned untitled scene, modified after smoke setup, fps `24.0`, frame range `1.0-120.0`, up axis `y`.
  - `tests/maya_smoke/actionrail_phase0_smoke.py` passed through `script.execute`: import version `0.1.0`, buttons `M/T/R/S/K`, widget size `40x196`, `K` created 10 keyframes, hide left no active overlays, reload returned one visible `transform_stack`.
  - `tests/maya_smoke/actionrail_capture_smoke.py` saved direct widget screenshot to `.gg-maya-sessiond/actionrail_phase0_overlay.png`; screenshot size `40x196`, visible widget size `40x196`, button count `5`.
  - `tests/maya_smoke/actionrail_horizontal_smoke.py` passed through `script.execute`: `horizontal_tools` rendered visible at `156x40`, orientation `horizontal`, anchor `viewport.bottom.center`, opacity `0.92`, button labels `M/W`, `R/E`, `S/R`, `K/S`.
- 2026-04-28 hidden visibility regression:
  - `.\\.venv\\Scripts\\python.exe -m pytest` -> 25 passed.
  - `.\\.venv\\Scripts\\python.exe -m ruff check .` -> all checks passed.
  - `tests/maya_smoke/actionrail_hidden_visibility_smoke.py` passed through `script.execute`: hidden buttons were absent, only visible button `VK` remained, no empty cluster frames were created, visible rail size was `40x40`, and widget screenshot artifact was saved to `.gg-maya-sessiond/screenshots/actionrail_hidden_visibility_widget.png`.
  - MCP `viewport.capture format=png width=640 height=360 show_ornaments=false panel=modelPanel4` returned a `640x360` PNG with `size_bytes=2030`; the image was saved locally to `.gg-maya-sessiond/screenshots/actionrail_hidden_visibility_viewport.png`.
- 2026-04-28 runtime-command/hotkey bridge:
  - `.\\.venv\\Scripts\\python.exe -m pytest` -> 55 passed after review fixes.
  - `.\\.venv\\Scripts\\python.exe -m ruff check .` -> all checks passed.
  - `doctor --state-dir .gg-maya-sessiond --json` passed when `--mcp-src` was omitted.
  - Started MayaSessiond on port `7217` with `--maya-module-path .` and `--mcp-script-dirs tests/maya_smoke`.
  - `tests/maya_smoke/actionrail_hotkey_bridge_smoke.py` passed through `script.execute`: default action runtime command existed and switched Maya to `RotateSuperContext`, repeated action publish reused the same runtime command name, preset slot runtime command existed and set 10 keyframes, unqualified slot publishing also set 10 keyframes, 5 action-bearing slots were published, and no overlay ids were active.
- 2026-04-28 tests/docs hardening:
  - `.\\.venv\\Scripts\\python.exe -m pytest` -> 52 passed.
  - `.\\.venv\\Scripts\\python.exe -m ruff check .` -> all checks passed.
  - MayaSessiond was not rerun; changes were limited to pure Python validation/runtime edge cases plus documentation.
- 2026-04-28 missing-features research docs:
  - Docs-only update; no pytest, ruff, or MayaSessiond run needed.
- 2026-04-28 product-scope docs clarification:
  - `git diff --check` -> no whitespace errors; Git reported LF/CRLF warnings only.
  - No pytest, ruff, or MayaSessiond run needed for this docs-only wording update.
- 2026-04-28 hotkey label sync:
  - `.\\.venv\\Scripts\\python.exe -m pytest` -> 59 passed.
  - `.\\.venv\\Scripts\\python.exe -m ruff check .` -> all checks passed.
  - `doctor --state-dir .gg-maya-sessiond --json` passed when `--mcp-src` was omitted.
  - Started MayaSessiond on port `7217` with `--maya-module-path .` and absolute `--mcp-script-dirs tests/maya_smoke`.
  - Tool discovery found 71 MCP tools, including `script.execute` and `viewport.capture`.
  - `scene.info` returned untitled scene, unmodified, fps `24.0`, frame range `1.0-120.0`, up axis `y`.
  - `tests/maya_smoke/actionrail_hotkey_label_sync_smoke.py` passed through `script.execute`: visible `transform_stack.set_key` button changed from `K\nS` to `K\nF12`, `actionRailKeyLabel` became `F12`, and the button kept its fixed `34x34` size.
- 2026-04-28 hotkey overwrite label cleanup:
  - `.\\.venv\\Scripts\\python.exe -m pytest` -> 62 passed.
  - `.\\.venv\\Scripts\\python.exe -m ruff check .` -> all checks passed.
  - Started MayaSessiond on port `7217` with `--maya-module-path .` and absolute `--mcp-script-dirs tests/maya_smoke`.
  - Tool discovery found 71 MCP tools, including `script.execute` and `viewport.capture`.
  - `scene.info` returned untitled scene, unmodified, fps `24.0`, frame range `1.0-120.0`, up axis `y`.
  - `tests/maya_smoke/actionrail_hotkey_label_sync_smoke.py` passed through `script.execute`: after rebinding `F12` from `transform_stack.move` to `transform_stack.set_key`, Move changed from `M\nF12` back to `M`, Set Key changed to `K\nF12`, and Set Key kept its fixed `34x34` size.
- 2026-04-28 predicate evaluation:
  - `.\\.venv\\Scripts\\python.exe -m pytest` -> 70 passed.
  - `.\\.venv\\Scripts\\python.exe -m ruff check .` -> all checks passed.
  - `doctor --state-dir .gg-maya-sessiond --json` passed when `--mcp-src` was omitted.
  - Started MayaSessiond on port `7217` with `--maya-module-path .` and absolute `--mcp-script-dirs tests/maya_smoke`.
  - Tool discovery found 71 MCP tools, including `script.execute` and `viewport.capture`.
  - `scene.info` returned untitled scene, unmodified, fps `24.0`, frame range `1.0-120.0`, up axis `y`.
  - `tests/maya_smoke/actionrail_predicates_smoke.py` passed through `script.execute`: selection and scale-tool predicates rendered only `VS/DK/CK`, active predicates marked `VS` and `CK`, missing command disabled `DK`, existing command enabled `CK`, widget size was `40x120`, and the widget screenshot artifact was saved to `.gg-maya-sessiond/screenshots/actionrail_predicates_widget.png`.
  - `tests/maya_smoke/actionrail_phase0_smoke.py` passed through `script.execute`: buttons `M/T/R/S/K`, widget size `40x196`, `K` created 10 keyframes, hide left no active overlays, reload returned one visible `transform_stack`.
  - `tests/maya_smoke/actionrail_horizontal_smoke.py` passed through `script.execute`: `horizontal_tools` rendered visible at `156x40`, orientation `horizontal`, anchor `viewport.bottom.center`, opacity `0.92`, button labels `M/W`, `R/E`, `S/R`, `K/S`.
- 2026-04-28 runtime-command stale cleanup:
  - `.\\.venv\\Scripts\\python.exe -m pytest tests\\test_hotkeys.py` -> 26 passed.
  - `.\\.venv\\Scripts\\python.exe -m ruff check scripts\\actionrail\\hotkeys.py tests\\test_hotkeys.py tests\\maya_smoke\\actionrail_hotkey_bridge_smoke.py` -> all checks passed.
  - `.\\.venv\\Scripts\\python.exe -m pytest` -> 74 passed.
  - `.\\.venv\\Scripts\\python.exe -m ruff check .` -> all checks passed.
  - `doctor --state-dir .gg-maya-sessiond --json` passed when `--mcp-src` was omitted.
  - Started MayaSessiond on port `7217` with `--maya-module-path .` and absolute `--mcp-script-dirs tests/maya_smoke`.
  - Tool discovery found 71 MCP tools, including `script.execute` and `viewport.capture`.
  - `scene.info` returned untitled scene, unmodified, fps `24.0`, frame range `1.0-120.0`, up axis `y`.
  - `tests/maya_smoke/actionrail_hotkey_bridge_smoke.py` passed through `script.execute`: action runtime command still switched to `RotateSuperContext`, slot runtime commands set 10 keyframes, 5 current slots were published by sync, 1 stale slot command was removed, and no overlays were active.
- 2026-04-28 viewport-parent and predicate panel snapshot fix:
  - `.\\.venv\\Scripts\\python.exe -m pytest` -> 77 passed.
  - `.\\.venv\\Scripts\\python.exe -m ruff check .` -> all checks passed.
  - `doctor --state-dir .gg-maya-sessiond --json` passed when `--mcp-src` was omitted.
  - Started MayaSessiond on port `7217` with `--maya-module-path .` and absolute `--mcp-script-dirs C:\\PROJECTS\\GG\\ScreenUI\\tests\\maya_smoke`.
  - Tool discovery found 71 MCP tools, including `script.execute` and `viewport.capture`.
  - `tests/maya_smoke/actionrail_predicates_smoke.py` passed through `script.execute`: selection and scale-tool predicates rendered only `VS/DK/CK`, active predicates marked `VS` and `CK`, missing command disabled `DK`, existing command enabled `CK`, widget size was `40x120`, panel was `modelPanel4`, and the widget screenshot artifact was saved to `.gg-maya-sessiond/screenshots/actionrail_predicates_widget.png`.
  - Live interactive inspection reproduced the outer model-panel repaint artifact, then verified the overlay could anchor from the inner `QmayaLayoutWidget modelPanel4`; this was superseded by the later floating rail host fix after direct viewport-child parenting still produced toolbar repaint ghosts.
  - `tests/maya_smoke/actionrail_phase0_smoke.py` passed through `script.execute`: buttons `M/T/R/S/K`, widget size `40x196`, `K` created 10 keyframes, hide left no active overlays, reload returned one visible `transform_stack`.
  - A fresh interactive `transform_stack` overlay was restored after the smoke run.
- 2026-04-28 stale overlay cleanup and floating rail host:
  - `.\\.venv\\Scripts\\python.exe -m pytest` -> 78 passed.
  - `.\\.venv\\Scripts\\python.exe -m ruff check .` -> all checks passed.
  - Restarted MayaSessiond on port `7217` with `--maya-module-path .`, absolute `--mcp-script-dirs C:\\PROJECTS\\GG\\ScreenUI\\tests\\maya_smoke`, and raw execution enabled.
  - `tests/maya_smoke/actionrail_overlay_cleanup_smoke.py` passed through `script.run` raw execution after `script.execute` returned stale structured payloads in this daemon run: repeated `show_example("transform_stack")` left one active overlay id, one `ActionRailViewportOverlay_transform_stack`, parent `MayaWindow`, rail geometry `[328, 621, 40, 196]`, and expected global anchor `[328, 621]`.
  - `tests/maya_smoke/actionrail_phase0_smoke.py` passed through `script.run` raw execution: buttons still clicked through the floating rail host, current context became `scaleSuperContext`, `K` created 10 keyframes, hide left no active overlays, and reload returned one visible `transform_stack`.
  - Restored a fresh interactive `transform_stack` overlay after smoke verification; live inspection showed parent `MayaWindow`, geometry `[328, 621, 40, 196]`, and visible `true`.
- 2026-04-28 rail inset fix:
  - `.\\.venv\\Scripts\\python.exe -m pytest` -> 78 passed.
  - `.\\.venv\\Scripts\\python.exe -m ruff check .` -> all checks passed.
  - Live MayaSessiond metric inspection showed the old issue: a styled `34x34` button at `[6, 6]` inside a `40x40` frame landed on the frame edge.
  - After the fix, live MayaSessiond metric inspection showed the transform stack at `46x214`; buttons remain `34x34` and sit at `[6, 6]` inside `46`-wide framed slots, leaving matching inset on both sides.
  - `tests/maya_smoke/actionrail_phase0_smoke.py` passed through `script.execute`: buttons `M/T/R/S/K`, current context `scaleSuperContext`, `K` created 10 keyframes, hide left no active overlays, reload returned one visible `transform_stack`, and size was `[46, 214]`.
  - `tests/maya_smoke/actionrail_horizontal_smoke.py` passed through `script.execute`: `horizontal_tools` rendered visible at `[172, 46]`, orientation `horizontal`, anchor `viewport.bottom.center`, opacity `0.92`, button labels `M/W`, `R/E`, `S/R`, `K/S`.
  - `tests/maya_smoke/actionrail_overlay_cleanup_smoke.py` passed through `script.execute`: one active overlay id, one visible `ActionRailViewportOverlay_transform_stack`, parent `MayaWindow`, and rail geometry `[328, 612, 46, 214]` matched the expected global viewport anchor.
  - `tests/maya_smoke/actionrail_capture_smoke.py` passed through `script.execute`: direct widget screenshot saved to `.gg-maya-sessiond/actionrail_phase0_overlay.png`, pixmap/widget size `[46, 214]`, and button count `5`.
  - `tests/maya_smoke/actionrail_hidden_visibility_smoke.py` passed through `script.execute`: hidden buttons were absent, only visible button `VK` remained, no empty cluster frames were created, and visible rail size was `[46, 46]`.
  - `tests/maya_smoke/actionrail_predicates_smoke.py` passed through `script.execute`: selection and scale-tool predicates rendered `VS/DK/CK`, active predicates marked `VS` and `CK`, missing command disabled `DK`, existing command enabled `CK`, and widget size was `[46, 138]`.
  - Follow-up live MayaSessiond user-visible check reloaded ActionRail in the existing Maya process and left `transform_stack` visible on `modelPanel4`; live geometry was `[328, 612, 46, 214]`, parent `MayaWindow`, active ids `["transform_stack"]`, and screenshot `.gg-maya-sessiond/screenshots/actionrail_visible_now.png`.
- 2026-04-28 live predicate refresh:
  - `.\\.venv\\Scripts\\python.exe -m pytest` -> 80 passed.
  - `.\\.venv\\Scripts\\python.exe -m ruff check .` -> all checks passed.
  - `doctor --state-dir .gg-maya-sessiond --json` passed when `--mcp-src` was omitted.
  - Started MayaSessiond on port `7217` with `--maya-module-path .` and absolute `--mcp-script-dirs C:\\PROJECTS\\GG\\ScreenUI\\tests\\maya_smoke`.
  - Tool discovery found 71 MCP tools, including `script.execute` and `viewport.capture`.
  - `tests/maya_smoke/actionrail_predicates_smoke.py` passed through `script.execute`: initial buttons were `VS/DK/CK`; tool-only `host.refresh_state()` did not rebuild and cleared `VS`/`CK` active state with `refreshed=2`; clearing selection requested a visibility rebuild and rendered `HE/DK/CK` at size `[46, 138]` with no empty cluster frames.
- 2026-04-28 Maya UI toggle:
  - `.\\.venv\\Scripts\\python.exe -m pytest` -> 88 passed.
  - `.\\.venv\\Scripts\\python.exe -m ruff check .` -> all checks passed.
  - `doctor --state-dir .gg-maya-sessiond --json` passed when `--mcp-src` was omitted.
  - Started MayaSessiond on port `7217` with `--maya-module-path .` and absolute `--mcp-script-dirs C:\\PROJECTS\\GG\\ScreenUI\\tests\\maya_smoke`.
  - Tool discovery found 71 MCP tools, including `script.execute` and `viewport.capture`.
  - `tests/maya_smoke/actionrail_maya_ui_smoke.py` passed through `script.execute`: menu and shelf entries installed idempotently, both command strings were `import actionrail; actionrail.toggle_default()`, toggle showed `transform_stack` at size `[46, 214]`, toggle hid it back to no active overlays, and uninstall removed both entries.
  - `tests/maya_smoke/actionrail_phase0_smoke.py` passed through `script.execute`: buttons `M/T/R/S/K`, current context `scaleSuperContext`, `K` created 10 keyframes, hide left no active overlays, reload returned one visible `transform_stack`, and size was `[46, 214]`.
- 2026-04-28 reusable Maya smoke wrapper:
  - PowerShell syntax parse passed: `$null = [scriptblock]::Create((Get-Content -Raw scripts\\maya-smoke.ps1))`.
  - `.\\scripts\\maya-smoke.ps1 -NoStart -Script actionrail_phase0_smoke.py` passed against the already-running MayaSessiond on port `7217`: tool discovery succeeded, `script.execute` ran `actionrail_phase0_smoke.py`, buttons were `M/T/R/S/K`, current context became `scaleSuperContext`, `K` created 10 keyframes, reload returned one visible `transform_stack`, and size was `[46, 214]`.
  - `git diff --check` passed with Git LF/CRLF warnings only.
  - `.\\.venv\\Scripts\\python.exe -m pytest` -> 88 passed.
  - `.\\.venv\\Scripts\\python.exe -m ruff check .` -> all checks passed.
- 2026-04-28 smoke wrapper all-mode isolation fix:
  - PowerShell syntax parse passed for `scripts\\maya-smoke.ps1`.
  - `.\\scripts\\maya-smoke.ps1 -NoStart -Script all` passed against the already-running MayaSessiond on port `7217`: tool discovery succeeded, cleanup ran before and after each smoke, and all 9 `*_smoke.py` scripts passed through `script.execute`.
- 2026-04-29 automatic predicate refresh:
  - `scripts/actionrail/overlay.py` now starts a host-owned Qt timer when an overlay is shown, calls the existing `ViewportOverlayHost.refresh_state()` path while the widget is visible, and stops/deletes the timer during host cleanup.
  - `tests/maya_smoke/actionrail_predicates_smoke.py` now waits for automatic timer refresh after tool and selection changes instead of calling `host.refresh_state()` manually.
  - `scripts/maya-smoke.ps1` now accepts nonzero stopped-status output as a startable state, allowing the wrapper to launch MayaSessiond from a stopped repo state.
  - PowerShell syntax parse passed for `scripts\\maya-smoke.ps1`.
  - `.\\.venv\\Scripts\\python.exe -m pytest` -> 89 passed.
  - `.\\.venv\\Scripts\\python.exe -m ruff check .` -> all checks passed.
  - `.\\scripts\\maya-smoke.ps1 -Script actionrail_predicates_smoke.py` started MayaSessiond on port `7217`, discovered MCP tools, and passed through `script.execute`: initial buttons were `VS/DK/CK`; automatic timer refresh cleared active state after switching from scale to move; automatic timer refresh rebuilt visible buttons to `HE/DK/CK` after clearing selection; widget size stayed `[46, 138]`.
  - `.\\scripts\\maya-smoke.ps1 -NoStart -Script actionrail_predicates_smoke.py` passed against the live daemon after refining the timer to start only for specs with predicate fields.
- 2026-04-29 safe-mode diagnostics:
  - `scripts/actionrail/diagnostics.py` adds `DiagnosticIssue`, `DiagnosticReport`, `collect_diagnostics()`, `diagnose_spec()`, and `safe_start()`.
  - `scripts/actionrail/spec.py` now exposes `builtin_preset_ids()` for diagnostics and future preset listing.
  - `tests/maya_smoke/actionrail_cleanup_state.py` now purges cached `actionrail` modules after cleanup so live-daemon smoke runs load current source files.
  - `.\\.venv\\Scripts\\python.exe -m pytest` -> 97 passed.
  - `.\\.venv\\Scripts\\python.exe -m ruff check .` -> all checks passed.
  - `.\\scripts\\maya-smoke.ps1 -Script actionrail_diagnostics_smoke.py` passed against the live MayaSessiond on port `7217`: built-in `transform_stack` diagnostics had zero issues, synthetic missing command/plugin predicates reported `missing_command` and `missing_plugin`, synthetic missing action reported `missing_action`, and `safe_start("transform_stack")` showed one active overlay at size `[46, 214]`.
- 2026-04-29 safe-start diagnostics default cmds:
  - `scripts/actionrail/diagnostics.py` now resolves importable `maya.cmds` by default for `collect_diagnostics()` and `diagnose_spec()`, so `actionrail.safe_start()` reports missing command/plugin predicate targets in Maya without callers passing `cmds_module`.
  - `tests/test_diagnostics.py` covers the public `safe_start()` path with an importable fake `maya.cmds`.
  - `.\\.venv\\Scripts\\python.exe -m pytest` -> 98 passed.
  - `.\\.venv\\Scripts\\python.exe -m ruff check scripts\\actionrail\\diagnostics.py tests\\test_diagnostics.py` -> all checks passed.
  - `.\\scripts\\maya-smoke.ps1 -Script actionrail_diagnostics_smoke.py` passed against the live MayaSessiond on port `7217`: `availability_warning_codes` were `["missing_command","missing_plugin"]`, synthetic missing action reported `missing_action`, and `safe_start("transform_stack")` showed one active overlay at size `[46,214]`.
- 2026-04-29 slot render-state refactor:
  - `scripts/actionrail/widgets.py` now resolves action-bearing button display through `SlotRenderState` and `_apply_slot_render_state()`, centralizing label, hotkey badge, tone, tooltip, enabled, and active updates.
  - Predicate refresh preserves runtime key-label overrides from visible buttons while still applying fresh enabled/active state and action tooltip fallbacks.
  - `.\\.venv\\Scripts\\python.exe -m pytest` -> 100 passed.
  - `.\\.venv\\Scripts\\python.exe -m ruff check .` -> all checks passed.
  - `.\\scripts\\maya-smoke.ps1 -Script actionrail_predicates_smoke.py` passed against the live MayaSessiond on port `7217`: automatic tool refresh updated active state in place, clearing selection rebuilt visible buttons to `HE/DK/CK`, and widget size stayed `[46,138]`.
  - `.\\scripts\\maya-smoke.ps1 -NoStart -Script actionrail_phase0_smoke.py` passed against the live MayaSessiond on port `7217`: buttons were `M/T/R/S/K`, current context became `scaleSuperContext`, `K` created 10 keyframes, reload returned one visible `transform_stack`, and size was `[46,214]`.
- 2026-04-29 diagnostic badge state:
  - `scripts/actionrail/spec.py` now parses optional slot `icon` ids.
  - `scripts/actionrail/icons.py` resolves icon ids through `icons/manifest.json` and verifies the referenced file exists.
  - `scripts/actionrail/widgets.py` extends `SlotRenderState` with icon id/path plus diagnostic code, severity, and badge text. Missing actions render disabled with `!`; missing icons render `?` while staying enabled.
  - `scripts/actionrail/diagnostics.py` now reports missing icon ids as warnings.
  - `.\\.venv\\Scripts\\python.exe -m pytest` -> 105 passed.
  - `.\\.venv\\Scripts\\python.exe -m ruff check .` -> all checks passed.
  - `.\\scripts\\maya-smoke.ps1 -Script actionrail_diagnostic_badges_smoke.py` passed against the live MayaSessiond on port `7217`: missing action rendered `X\n!` disabled, missing icon rendered `I\n?` enabled, and the rail size was `[46,92]`.
  - `.\\scripts\\maya-smoke.ps1 -NoStart -Script actionrail_diagnostics_smoke.py` passed against the live MayaSessiond on port `7217`: missing icon diagnostics reported `missing_icon`, and `safe_start("transform_stack")` still showed `[46,214]`.
  - `.\\scripts\\maya-smoke.ps1 -NoStart -Script actionrail_phase0_smoke.py` passed against the live MayaSessiond on port `7217`: buttons were `M/T/R/S/K`, current context became `scaleSuperContext`, `K` created 10 keyframes, reload returned one visible `transform_stack`, and size was `[46,214]`.
- 2026-04-29 command/plugin predicate badges:
  - `scripts/actionrail/predicates.py` now exposes shared availability target helpers; diagnostics report missing command/plugin references, and widget rendering uses semantic blocking checks for runtime badges.
  - `scripts/actionrail/widgets.py` now renders `missing_command` and `missing_plugin` warning badges as `?`, disables affected slots, and keeps slots visible when a missing availability predicate would otherwise hide them.
  - Badge rendering now only treats a missing command/plugin as blocking when re-evaluating the predicate with the missing availability call repaired would make the predicate pass. This preserves non-availability visibility clauses such as `selection.count > 0 and plugin.exists(...)` and avoids badges/disabled state for intentional fallbacks such as `not command.exists(...)`.
  - `.\\.venv\\Scripts\\python.exe -m pytest tests\\test_widgets.py tests\\test_predicates.py` -> 23 passed.
  - `.\\.venv\\Scripts\\python.exe -m pytest` -> 112 passed.
  - `.\\.venv\\Scripts\\python.exe -m ruff check .` -> all checks passed.
  - `.\\scripts\\maya-smoke.ps1 -NoStart -Script actionrail_diagnostic_badges_smoke.py` passed against the live MayaSessiond on port `7217`: missing action rendered `X\n!`, missing icon rendered `I\n?`, missing command rendered `C\n?`, missing plugin rendered `P\n?`, negated fallback rendered `F` enabled with no badge, the compound context-gated missing plugin slot stayed hidden, and the rail size was `[46,230]`.
  - `.\\scripts\\maya-smoke.ps1 -NoStart -Script actionrail_predicates_smoke.py` passed against the live MayaSessiond on port `7217`: automatic refresh preserved the missing-command warning badge as `DK\n?` while visible/enabled/active predicates updated.
- 2026-04-29 last diagnostic report UI:
  - `scripts/actionrail/diagnostics.py` now records the most recent diagnostic
    report from `collect_diagnostics()`, `diagnose_spec()`, and `safe_start()`.
  - Public helpers now expose `actionrail.last_report()`,
    `actionrail.clear_last_report()`, `actionrail.format_report()`, and
    `actionrail.show_last_report()`.
  - `scripts/actionrail/maya_ui.py` installs a "Show Last Diagnostic Report"
    menu item alongside the default rail toggle; the command opens the latest
    report through Maya `confirmDialog`.
  - `.\\.venv\\Scripts\\python.exe -m pytest tests\\test_diagnostics.py tests\\test_maya_ui.py tests\\test_package.py` -> 21 passed.
  - `.\\.venv\\Scripts\\python.exe -m pytest` -> 114 passed.
  - `.\\.venv\\Scripts\\python.exe -m ruff check .` -> all checks passed.
  - `.\\scripts\\maya-smoke.ps1 -NoStart -Script actionrail_diagnostics_smoke.py` passed against live MayaSessiond on port `7217`: `safe_start("transform_stack")` recorded an ok last report with active overlay `transform_stack`.
  - `.\\scripts\\maya-smoke.ps1 -NoStart -Script actionrail_maya_ui_smoke.py` passed against live MayaSessiond on port `7217`: the diagnostics menu item installed idempotently, used `import actionrail; actionrail.show_last_report()`, and uninstalled cleanly.
- 2026-04-29 themed diagnostics report window:
  - `scripts/actionrail/diagnostics_ui.py` adds a themed non-modal Qt
    diagnostics dialog with summary text, warning/error issue list, read-only
    selectable full report text, and `Copy Selected`, `Copy Full Report`,
    `Clear`, and `Close` actions.
  - `actionrail.show_last_report()` now routes to the Qt diagnostics window
    while keeping the formatted string return value and stable Maya menu command.
  - `.\\.venv\\Scripts\\python.exe -m pytest tests\\test_diagnostics.py tests\\test_package.py` -> 13 passed.
  - `.\\.venv\\Scripts\\python.exe -m pytest` -> 114 passed.
  - `.\\.venv\\Scripts\\python.exe -m ruff check .` -> all checks passed.
  - `.\\scripts\\maya-smoke.ps1 -NoStart -Script actionrail_diagnostics_smoke.py` passed against live MayaSessiond on port `7217`: the diagnostics window showed the missing-action issue, copied selected and full report text to the clipboard, cleared the stored report, saved screenshot `.gg-maya-sessiond/screenshots/actionrail_diagnostics_window.png` at `720x520`, and `safe_start("transform_stack")` still showed `[46,214]`.

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
