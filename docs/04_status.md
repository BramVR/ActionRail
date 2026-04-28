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

## In Progress

- Phase 1 declarative MVP.

## Next

1. Add theme token/QSS generation.
2. Add a shelf/menu toggle once reload cleanup stays stable.
3. Add a reusable smoke command wrapper if the MayaSessiond command shape remains stable.

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
- 2026-04-28 MayaSessiond:
  - `doctor --state-dir .gg-maya-sessiond --json` passed when `--mcp-src` was omitted.
  - Started MayaSessiond on port `7217` with `--maya-module-path C:/PROJECTS/GG/ScreenUI` and `--mcp-script-dirs C:/PROJECTS/GG/ScreenUI/tests/maya_smoke`.
  - Tool discovery found 71 MCP tools, including `script.execute` and `viewport.capture`.
  - `scene.info` returned untitled scene, fps `24.0`, frame range `1.0-120.0`, up axis `y`.
  - `tests/maya_smoke/actionrail_phase0_smoke.py` passed through `script.execute`: import version `0.1.0`, buttons `M/T/R/S/K`, widget size `40x196`, `K` created 10 keyframes, hide left no active overlays, reload returned one visible `transform_stack`.
  - `tests/maya_smoke/actionrail_capture_smoke.py` saved direct widget screenshot to `.gg-maya-sessiond/actionrail_phase0_overlay.png`; screenshot size `40x196`, visible widget size `40x196`, button count `5`.
  - Native `viewport.capture format=png width=640 height=360 show_ornaments=false` returned `size_bytes=2030` for `modelPanel4`.

## Decisions

- PySide6/Qt overlay is the MVP path.
- Viewport 2.0 is deferred until Qt overlay is stable.
- Designer/Quick Create is deferred until Phase 0 and declarative MVP are stable.
- Use `GG_MayaSessiond` for live Maya verification when feasible.
- Use `ActionRail` for product/module naming and `actionrail` for Python package/API naming.
- Use Python 3.11 in Maya, PySide6/Qt Widgets, custom transparent overlay, `maya.cmds`, OpenMayaUI, JSON specs, SVG icons, `.mod` packaging, and MayaSessiond verification.
- Spike Autodesk `moverlay` before committing to any overlay helper.
- Keep web tech out of the core runtime; use it only for authoring/import tooling.
