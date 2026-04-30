---
summary: Archived ActionRail verification log moved out of the live status file to keep agent context small.
read_when:
  - Auditing old MayaSessiond or local test runs.
  - Investigating when a regression was last verified.
  - Updating long-form verification history after recording the live status summary.
---

# Verification Log

This archive preserves older verification history. Keep `docs/04_status.md` focused on current state, latest handoff, blockers, and the latest verification summary.

## History

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
- 2026-04-30 SVG import helper:
  - `scripts/actionrail/icons.py` now exposes
    `actionrail.icons.import_svg_icon()` for local SVG imports with existing SVG
    safety validation, safe target-path resolution under `icons/`, manifest
    upsert behavior, overwrite controls, and source/license/url/import-date
    metadata.
  - `tests/test_icons.py` covers successful import, unsafe SVG rejection
    without manifest mutation, duplicate rejection, overwrite behavior, and
    out-of-tree target rejection.
  - `.\\.venv\\Scripts\\python.exe -m pytest tests\\test_icons.py` -> 12 passed.
  - `.\\.venv\\Scripts\\python.exe -m ruff check scripts\\actionrail\\icons.py tests\\test_icons.py` -> all checks passed.
  - `.\\.venv\\Scripts\\python.exe -m pytest` -> 130 passed.
  - `.\\.venv\\Scripts\\python.exe -m ruff check .` -> all checks passed.
  - Maya smoke was not run because this slice only changes pure Python import
    tooling and docs, not Maya overlay/UI behavior.
- 2026-04-30 SVG import helper review hardening:
  - `scripts/actionrail/icons.py` now rejects external stylesheet references
    inside SVG `<style>` blocks, not only in attributes.
  - Import path conflict detection now compares normalized resolved manifest
    paths, so supported spellings like `custom/arrow.svg` and
    `icons/custom/arrow.svg` cannot overwrite another icon id's asset.
  - `tests/test_icons.py` covers both review regressions.
  - `.\\.venv\\Scripts\\python.exe -m pytest tests\\test_icons.py` -> 14 passed.
  - `.\\.venv\\Scripts\\python.exe -m ruff check scripts\\actionrail\\icons.py tests\\test_icons.py` -> all checks passed.
  - `.\\.venv\\Scripts\\python.exe -m pytest` -> 132 passed.
  - `.\\.venv\\Scripts\\python.exe -m ruff check .` -> all checks passed.
- 2026-04-30 docs/navigation optimization:
  - `actionrail.about()` and `python -m actionrail --json` now expose a
    JSON-safe project map for agents.
  - `docs/04_status.md` was trimmed to live status; this file now carries the
    long-form historical verification log.
  - `.\\.venv\\Scripts\\python.exe -m pytest tests\\test_project_map.py tests\\test_package.py tests\\test_icons.py` -> 18 passed.
  - `.\\.venv\\Scripts\\python.exe -m ruff check scripts\\actionrail\\project.py scripts\\actionrail\\__main__.py scripts\\actionrail\\__init__.py scripts\\actionrail\\actions.py scripts\\actionrail\\spec.py scripts\\actionrail\\runtime.py scripts\\actionrail\\icons.py scripts\\actionrail\\diagnostics.py scripts\\actionrail\\hotkeys.py scripts\\actionrail\\widgets.py scripts\\actionrail\\overlay.py tests\\test_project_map.py tests\\test_package.py` -> all checks passed.
  - `$env:PYTHONPATH='scripts'; .\\.venv\\Scripts\\python.exe -m actionrail --json` -> printed valid project map.
  - `.\\.venv\\Scripts\\python.exe -m pytest` -> 135 passed.
  - `.\\.venv\\Scripts\\python.exe -m ruff check .` -> all checks passed.
  - Maya smoke was not run because this slice only changes pure Python
    navigation helpers and docs, not Maya overlay/UI behavior.
