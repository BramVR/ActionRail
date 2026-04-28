---
summary: Live project status for agents: what is done, what is next, blockers, and verification history.
read_when:
  - Starting work after another agent.
  - Finishing any implementation or research slice.
  - Checking current blockers before editing code.
---

# Status

Last updated: 2026-04-28

## Done

- Research images collected in `research/`.
- Architecture/report written in `MAYA_UI_FRAMEWORK_REPORT.md`.
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
  - Viewport overlay host parented under the active Maya model panel.
  - Hard-coded `M/T/R/S + K` transform stack matching the research reference.
  - Maya action bindings for move/translate, rotate, scale, and set key.
  - Pure Python unit tests and allowlisted MayaSessiond smoke scripts.
- `docs/03_maya_sessiond_workflow.md` now documents the repo-specific MayaSessiond port rule. Use port `7217` for ActionRail unless it is already in use.
- Phase 1 declarative MVP started:
  - Built-in examples now load from JSON presets in `presets/`.
  - `presets/transform_stack.json` is the source of truth for the reference stack labels, actions, tones, tooltips, spacer, and anchor.
  - Preset parsing validates required ids, anchors, item lists, supported item types, button action fields, and spacer sizes.
  - The Qt stack builder now renders from the spec item stream instead of looking up a hard-coded `K` button.
  - Widget screenshot smoke now captures the ActionRail widget directly instead of the foreground desktop.
  - Theme tokens and generated QSS now live in `scripts/actionrail/theme.py`; the default theme preserves the reference `40x196` transform stack dimensions and colors.
- Phase 1A rail schema started:
  - Presets now support `layout` metadata: orientation, rows, columns, anchor, offset, scale, opacity, and locked state.
  - Items now support stable slot `id`, `key_label`, and safe declarative `visible_when`, `enabled_when`, and `active_when` predicate fields.
  - `presets/transform_stack.json` has explicit stable slot ids and layout metadata while preserving the reference `40x196` render size.
  - `presets/horizontal_tools.json` proves a horizontal rail can be defined without widget-code changes.
  - Overlay positioning now supports left/right/top/bottom/center anchors plus layout offsets.
  - Maya smoke coverage now includes a horizontal rail render check.
- Phase 1B runtime-command bridge started:
  - `actionrail.run_action(action_id)` runs registered actions without requiring an overlay.
  - `actionrail.run_slot(preset_id, slot_id)` runs action-bearing preset slots by stable slot id.
  - `actionrail.hotkeys` can publish default actions and preset slots as Maya runtime commands plus paired nameCommands for hotkey assignment.
  - Hotkey assignment now has conflict-aware helpers that refuse to overwrite existing bindings unless explicitly requested.
  - Maya smoke coverage now validates runtime command execution for an action and a preset slot with no overlay visible.
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
2. First recommended coding slice: wire assigned hotkeys back into rendered key labels.
3. Do not start full Edit Mode, Bind Mode, flyouts, command rings, or Viewport 2.0 yet.

Checks already run for the roadmap update:

- `git diff --check` -> no whitespace errors; Git reported LF/CRLF warnings only.
- No pytest, ruff, or MayaSessiond run was needed for the docs-only update.

## Next

1. Add key-label update wiring after hotkey assignment so rendered slots reflect published bindings.
2. Add real predicate evaluation for `visible_when`, `enabled_when`, and `active_when`; current support is parsed metadata plus literal `false` visibility/enabled handling.
3. Add a shelf/menu toggle once reload cleanup stays stable.
4. Add a reusable smoke command wrapper if the MayaSessiond command shape remains stable.
5. Use `docs/07_missing_features_research.md` to prioritize later authoring, icon, diagnostics, profile, flyout/ring, marking-menu, and Viewport 2.0 work.

## Blockers

- No ActionRail implementation blocker known.
- `GG_MayaSessiond doctor --mcp-src ../GG_MayaMCP` is currently blocked by a sibling repo compatibility lock: sessiond expects GG_MayaMCP commit `2e7a28df7f4d029d81f6421549fb23cb056c4693` / version `0.4.0`, while `../GG_MayaMCP` is at `637954c0510296543126c6504dd445f066eb4559` / version `0.4.1`.
- Workaround used for verification: omit `--mcp-src` so sessiond uses the MCP package installed in its venv. `doctor` passes in that mode.

## Verification History

- 2026-04-27 local venv:
  - `.\\.venv\\Scripts\\python.exe -m pytest` -> 13 passed.
  - `.\\.venv\\Scripts\\python.exe -m ruff check .` -> all checks passed.
- 2026-04-27 Maya import fallback:
  - `PYTHONPATH=C:\\PROJECTS\\GG\\ScreenUI\\scripts` with Maya 2025 `mayapy.exe` imported `actionrail 0.1.0`.
  - `PYTHONNOUSERSITE=1` avoids a user-site NumPy 2 warning while importing Maya's PySide6.
- 2026-04-27 MayaSessiond:
  - `doctor --state-dir .gg-maya-sessiond --json` passed when `--mcp-src` was omitted.
  - Started MayaSessiond on ActionRail-specific port `7217`.
  - `scene.info` returned untitled scene, unmodified, fps `24.0`, frame range `1.0-120.0`, up axis `y`.
  - Tool discovery found 71 MCP tools, including `script.execute` and `viewport.capture`.
  - `tests/maya_smoke/actionrail_phase0_smoke.py` passed through `script.execute`: import version `0.1.0`, buttons `M/T/R/S/K`, widget size `40x196`, `K` created 10 keyframes, hide left no active overlays, reload returned one visible `transform_stack`.
  - Re-ran `tests/maya_smoke/actionrail_phase0_smoke.py` with no manual `sys.path` injection; `import actionrail` worked from `--maya-module-path C:/PROJECTS/GG/ScreenUI` and `ActionRail.mod`.
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
  - Started MayaSessiond on port `7217` with `--maya-module-path C:/PROJECTS/GG/ScreenUI` and `--mcp-script-dirs C:/PROJECTS/GG/ScreenUI/tests/maya_smoke`.
  - Tool discovery found 71 MCP tools, including `script.execute` and `viewport.capture`.
  - `scene.info` returned untitled scene, fps `24.0`, frame range `1.0-120.0`, up axis `y`.
  - `tests/maya_smoke/actionrail_phase0_smoke.py` passed through `script.execute`: import version `0.1.0`, buttons `M/T/R/S/K`, widget size `40x196`, `K` created 10 keyframes, hide left no active overlays, reload returned one visible `transform_stack`.
  - `tests/maya_smoke/actionrail_capture_smoke.py` saved direct widget screenshot to `.gg-maya-sessiond/actionrail_phase0_overlay.png`; screenshot size `40x196`, visible widget size `40x196`, button count `5`.
  - Native `viewport.capture format=png width=640 height=360 show_ornaments=false` returned `size_bytes=2030` for `modelPanel4`.
- 2026-04-28 MayaSessiond after theme token/QSS generation:
  - `doctor --state-dir .gg-maya-sessiond --json` passed when `--mcp-src` was omitted.
  - Started MayaSessiond on port `7217` with `--maya-module-path C:/PROJECTS/GG/ScreenUI` and `--mcp-script-dirs C:/PROJECTS/GG/ScreenUI/tests/maya_smoke`.
  - Tool discovery found 71 MCP tools, including `script.execute` and `viewport.capture`.
  - `scene.info` returned untitled scene, unmodified, fps `24.0`, frame range `1.0-120.0`, up axis `y`.
  - `tests/maya_smoke/actionrail_phase0_smoke.py` passed through `script.execute`: import version `0.1.0`, buttons `M/T/R/S/K`, widget size `40x196`, `K` created 10 keyframes, hide left no active overlays, reload returned one visible `transform_stack`.
  - `tests/maya_smoke/actionrail_capture_smoke.py` saved direct widget screenshot to `.gg-maya-sessiond/actionrail_phase0_overlay.png`; screenshot size `40x196`, visible widget size `40x196`, button count `5`.
- 2026-04-28 local venv after Phase 1A rail schema:
  - `.\\.venv\\Scripts\\python.exe -m pytest` -> 24 passed.
  - `.\\.venv\\Scripts\\python.exe -m ruff check .` -> all checks passed.
- 2026-04-28 MayaSessiond after Phase 1A rail schema:
  - `doctor --state-dir .gg-maya-sessiond --json` passed when `--mcp-src` was omitted.
  - Started MayaSessiond on port `7217` with `--maya-module-path C:/PROJECTS/GG/ScreenUI` and `--mcp-script-dirs C:/PROJECTS/GG/ScreenUI/tests/maya_smoke`.
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
  - Started MayaSessiond on port `7217` with `--maya-module-path C:/PROJECTS/GG/ScreenUI` and `--mcp-script-dirs C:/PROJECTS/GG/ScreenUI/tests/maya_smoke`.
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

## Decisions

- PySide6/Qt overlay is the MVP path.
- Viewport 2.0 is deferred until Qt overlay is stable.
- Designer/Quick Create is deferred until Phase 0 and declarative MVP are stable.
- WoW-style customization is the long-term authoring model: Edit Mode, action slots, hover-to-bind hotkeys, flyouts, command rings, and preset/profile layers.
- Treat `M/T/R/S/K` as a proof preset and regression target; ActionRail's product goal is broader user-authored viewport UI.
- Build the hotkey bridge through Maya runtime commands so bindings remain visible to Maya and not only to ActionRail.
- Use `GG_MayaSessiond` for live Maya verification when feasible.
- Use `ActionRail` for product/module naming and `actionrail` for Python package/API naming.
- Use Python 3.11 in Maya, PySide6/Qt Widgets, custom transparent overlay, `maya.cmds`, OpenMayaUI, JSON specs, SVG icons, `.mod` packaging, and MayaSessiond verification.
- Spike Autodesk `moverlay` before committing to any overlay helper.
- Keep web tech out of the core runtime; use it only for authoring/import tooling.
