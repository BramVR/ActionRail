---
summary: Live project status for agents: what is done, what is next, blockers, latest handoff, and latest verification.
read_when:
  - Starting work after another agent.
  - Finishing any implementation or research slice.
  - Checking current blockers before editing code.
---

# Status

Last updated: 2026-05-06

## Current Snapshot

ActionRail has a verified declarative MVP and Phase 2 authoring foundation
through Quick Create preview/save/load, Edit Mode layout-map/direct
manipulation controls, user preset saves, built-in layout override saves, and
studio layout override saves. Phase 2 step 2.6 is now in progress with the
first collapsible edge-tab schema/runtime slice implemented and Maya-smoke
verified, a Maya-smoke verified handle/publish polish pass, and a locally
verified validation UX/saved-preset publish follow-up with Quick Create Maya
smoke coverage for the custom-store Save + Publish shelf command path. A first
guide/slot-edit affordance polish pass is locally verified.

Working surface:

- JSON presets and Python builder API for viewport rails.
- Built-in presets: `transform_stack`, `horizontal_tools`, and `maya_tools`.
- Qt overlay lifecycle, model-panel anchoring, predicate refresh, reusable Maya
  actions, and runtime-command hotkey publishing.
- Safe diagnostics, diagnostic badges, diagnostics Qt window, icon import
  preflight, generated SVG PNG fallbacks, and fallback preset recovery.
- User preset storage and shared bundled/user preset resolver.
- Maya menu and shelf entry points, including diagnostics, SVG import
  diagnostics, Quick Create, and Toggle Edit Mode.
- Dockable Quick Create panel with template selection, preview, clear preview,
  save, overwrite, custom user preset store support, custom action/icon id
  preservation, load-existing user preset workflow, live preview refresh for
  layout sliders, and generated blank slots when the button-count control is
  raised beyond the template's icon-backed slots.
- Edit Mode shell with layout-map overlay, grid controls, Snap to Grid, Sticky
  Frames, active rail frames, selection, drag handles, anchor pins,
  snap/spacing guides, axis-aligned sticky alignment guides, right-click
  options, X/Y movement for unlocked rails, slot add/remove/reorder controls
  with last-slot affordance text, real edge-tab collapse/expand controls, safe
  movement clamps, Save Position/user-preset persistence for unlocked
  runtime/user rails, and user override saves/resolution for unlocked built-in
  and studio rails.
- Optional collapsible rail schema/runtime: JSON `collapse` settings for edge,
  handle icon, reveal trigger, and default collapsed state; Quick Create
  edge-tab defaults/settings; collapsed handle-only Qt overlays; click/hover
  reveal hooks; and user-preset persistence.
- Collapsed edge handles now use larger hit targets, hug the configured
  viewport edge, preserve only tangent layout offset while collapsed, and clamp
  inside the viewport.
- Quick Create saves now run publish-facing diagnostics before writing; saved
  presets can optionally publish slot runtime commands and an idempotent preset
  shelf toggle through the Save + Publish path. Validate Draft now surfaces
  publish diagnostics before save, blocked saves include the concrete
  diagnostic issue, Save + Publish reports stale slot-command cleanup, and
  published shelf toggles preserve custom user preset stores.
- Quick Create draft conversion now infers `active_when` predicates for
  persistent Maya tool actions (`move`, `translate`, `rotate`, and `scale`) so
  saved Quick Create rails show active tool styling; one-shot actions remain
  inactive unless a slot has an explicit custom predicate.

Long-form implementation and verification history belongs in
`docs/history/verification_log.md`.

## Current Plan

`docs/02_implementation_plan.md` is the source of truth for phase completion
and next work. Phase 2 step 2.5 Layout Editing And Direct Manipulation is done;
Phase 2 step 2.6 collapsible edge tabs and publish polish is in progress.
Local `.spec/` reports are ignored and not part of the Git-tracked handoff.

Focus the next slice on:

- keeping the fixed Quick Create round-trip and preset discovery paths stable
- keeping locked built-in/studio presets read-only

Do not start Bind Mode, flyouts, command rings, profile layers,
marking-menu export, or Viewport 2.0 in this slice.

## Next Agent Start

1. Read `../bram-agent-scripts/AGENTS.MD`, then `docs/00_start_here.md`, then this file.
2. Run the project map if ownership or test routing is unclear:

```powershell
$env:PYTHONPATH = "scripts"
.\.venv\Scripts\python.exe -m actionrail --json
```

3. Continue Phase 2 step 2.6 on top of the completed Phase 2 step 2.5 Edit Mode
   layout editing surface. The collapse schema/runtime first pass is in place
   and Maya-smoke verified; the handle/publish polish pass is also Maya-smoke
   verified; the validation UX/publish follow-up is locally verified, and Quick
   Create Maya smoke covers the custom-store Save + Publish shelf command path.
   The first guide/slot-affordance polish pass is locally verified.
4. Use `scripts/maya-smoke.ps1` for repeatable MayaSessiond smoke runs when feasible.

## Latest Handoff

- Phase 2 step 2.4 Edit Mode shell and rail selection is implemented and Maya
  screenshot verified.
- Quick Create can preview/save/load user presets.
- Edit Mode can inspect active rails, select frames, show grid/snap/sticky
  controls, move unlocked rails in-session, and route right-click options.
- Edit Mode can save adjusted unlocked runtime/user rail specs and unlocked
  built-in/studio user override presets through `save_edit_mode_layout()` and
  the right-click Save Position control.
- The shared preset resolver now applies saved built-in `*_user_override`
  sidecars when loading the original built-in preset id, while leaving broken
  override files as user-preset diagnostics instead of blocking bundled loads.
- The shared preset resolver also supports optional read-only studio preset
  discovery through `ACTIONRAIL_STUDIO_PRESET_DIR` or `PresetStore(...,
  studio_preset_dir=...)`, with `*_user_override` sidecars applied when loading
  the original studio preset id.
- Safe startup keeps diagnostically bad built-in/studio user override sidecars
  on the user-preset warning path and starts the read-only preset instead.
- The May 5 audit items are fixed in focused conventional commits through
  `feat(edit-mode): add direct manipulation controls`, the diagnostics
  follow-up, and the status/changelog hygiene updates.
- The May 6 handle/publish polish pass enlarges and edge-clamps collapsed
  handles, adds `diagnose_publish_spec()`, blocks Quick Create saves with
  diagnostic errors, records warning diagnostics for publish review, and adds
  optional slot runtime-command plus shelf-toggle publishing from Quick Create.
- The May 6 validation UX/publish follow-up routes Quick Create Validate Draft
  through publish diagnostics, includes concrete diagnostic details in blocked
  save errors, reports stale slot-command cleanup from Save + Publish, and
  preserves custom user preset stores in published preset shelf toggles.
- Quick Create Preview now stays live while visible: the Buttons slider grows
  or trims slot rows, extra generated slots are blank/no-icon after the
  template's icon-backed slots, and Buttons Per Row/Button Size/offset/alpha
  changes refresh the active viewport preview immediately.
- Quick Create now fills blank `active_when` values for known persistent Maya
  tool actions during draft conversion, so newly saved Move/Rotate/Scale tool
  slots reflect Maya's active tool context without marking one-shot commands
  like Set Key active.
- The May 6 guide/slot-affordance polish pass replaces Sticky Frames diagonal
  hints with axis-aligned alignment guides and makes frame options report the
  last editable action slot while disabling unavailable slot moves.
- Maya smoke cleanup now removes all `ActionRail*` Qt widgets between smoke
  scripts so diagnostics/panel windows do not steal later Edit Mode clicks.
- No ActionRail implementation blocker is known.

## Blockers

- No ActionRail implementation blocker known.
- `GG_MayaSessiond doctor --mcp-src ../GG_MayaMCP` is currently blocked by a
  sibling repo compatibility lock: sessiond expects GG_MayaMCP commit
  `2e7a28df7f4d029d81f6421549fb23cb056c4693` / version `0.4.0`, while
  `../GG_MayaMCP` is at `637954c0510296543126c6504dd445f066eb4559` /
  version `0.4.1`.
- Workaround used for verification: omit `--mcp-src` so sessiond uses the MCP
  package installed in its venv. `doctor` passes in that mode.

## Latest Verification

- Full pytest:
  `.\\.venv\\Scripts\\python.exe -m pytest`
  -> 445 passed.
- Ruff:
  `.\\.venv\\Scripts\\python.exe -m ruff check .`
  -> all checks passed.
- Project map:
  `$env:PYTHONPATH='scripts'; .\\.venv\\Scripts\\python.exe -m actionrail --json`
  -> passed.
- Docs list:
  `& ..\\bram-agent-scripts\\scripts\\docs-list.ps1`
  -> passed.
- Local Markdown link check:
  PowerShell local-link scan over `docs/**/*.md`
  -> `Local Markdown links OK`.
- Edit Mode Maya smoke:
  `.\\scripts\\maya-smoke.ps1 -Script actionrail_edit_mode_smoke.py -Timeout 240`
  -> passed after restarting a stale Sessiond state; verified layout-map
  overlay, Grid Size 64, Snap to Grid, Sticky Frames, left-click selection, X
  coordinate movement, sticky-frame alignment, right-click options routing,
  collapsed handle-only widget sizing, collapsed-state save persistence,
  `run_slot()` while collapsed, handle-click expansion, saved layout offset
  `[51, -133]`, user preset save path
  `.gg-maya-sessiond/user_presets/edit_mode_custom.json`, and screenshot
  capture at
  `.gg-maya-sessiond/screenshots/actionrail_edit_mode_layout_map.png`.
- Custom user-preset store Maya smoke:
  `.\\scripts\\maya-smoke.ps1 -Script actionrail_custom_preset_store_smoke.py -Timeout 240`
  -> passed; verified custom user-preset directory retention through
  `show_preset()`, Edit Mode user source classification, and Save Position
  persistence back to the same custom store.
- Diagnostics Maya smoke:
  `.\\scripts\\maya-smoke.ps1 -Script actionrail_diagnostics_smoke.py -Timeout 240`
  -> passed; verified safe diagnostics and `safe_start("transform_stack")`
  still start an overlay after the built-in override diagnostics fix.
- Full Maya smoke baseline:
  `.\\scripts\\maya-smoke.ps1 -Script all -Timeout 300`
  -> passed against the running MayaSessiond state on port `7217`; covered capture,
  custom user-preset store layout saves, diagnostic badges, diagnostics window,
  hidden visibility, Edit Mode, horizontal and Maya icon rails, hotkey bridge,
  hotkey label sync, import/recovery diagnostics, menu/shelf UI, missing Maya
  icon resources, overlay cleanup, predicates, Quick Create, StackItem ABI, and
  transform-stack state. Quick Create smoke now also verifies Save + Publish
  creates four slot runtime commands plus a preset shelf toggle.
- Quick Create Maya smoke:
  `.\\scripts\\maya-smoke.ps1 -Script actionrail_quick_create_smoke.py -Timeout 240`
  -> passed; verified Save + Publish creates four slot runtime commands, creates
  a preset shelf toggle, reports publish status, and preserves the custom user
  preset store path in the shelf command. The latest run also verifies Quick
  Create resizes with its Maya workspace-control parent.
- Screenshot inspection confirmed these rendered correctly:
  `.gg-maya-sessiond/screenshots/actionrail_edit_mode_layout_map.png`,
  `.gg-maya-sessiond/screenshots/actionrail_quick_create_panel.png`,
  `.gg-maya-sessiond/screenshots/actionrail_diagnostics_window.png`, and
  `.gg-maya-sessiond/screenshots/actionrail_horizontal_tools_widget.png`.
- Latest Maya note: Maya smoke used the installed MCP package in the Sessiond
  venv; do not pass `--mcp-src ../GG_MayaMCP` until the sibling repo
  compatibility blocker is resolved.
- Latest local focused validation:
  `.\\.venv\\Scripts\\python.exe -m pytest tests\\test_project_map.py tests\\test_quick_create.py tests\\test_maya_ui.py tests\\test_diagnostics.py`
  -> 123 passed.
- Latest targeted Ruff:
  `.\\.venv\\Scripts\\python.exe -m ruff check tests\\maya_smoke\\actionrail_cleanup_state.py tests\\maya_smoke\\actionrail_edit_mode_smoke.py tests\\maya_smoke\\actionrail_quick_create_smoke.py`
  -> all checks passed.
- Latest focused Quick Create preview validation:
  `.\\.venv\\Scripts\\python.exe -m pytest tests\\test_quick_create.py tests\\test_widgets.py`
  -> 72 passed.
- Latest focused Quick Create active-state validation:
  `.\\.venv\\Scripts\\python.exe -m pytest tests\\test_quick_create.py`
  -> 34 passed.
- Latest focused Ruff:
  `.\\.venv\\Scripts\\python.exe -m ruff check scripts\\actionrail\\quick_create.py tests\\test_quick_create.py`
  -> all checks passed.
- Latest project map:
  `$env:PYTHONPATH='scripts'; .\\.venv\\Scripts\\python.exe -m actionrail --json`
  -> passed.
- Latest focused Ruff:
  `.\\.venv\\Scripts\\python.exe -m ruff check scripts\\actionrail\\quick_create.py scripts\\actionrail\\quick_create_ui.py scripts\\actionrail\\widgets.py tests\\test_quick_create.py tests\\test_widgets.py tests\\maya_smoke\\actionrail_quick_create_smoke.py`
  -> all checks passed.
- Latest Quick Create Maya smoke:
  `.\\scripts\\maya-smoke.ps1 -Script actionrail_quick_create_smoke.py -Timeout 240`
  -> passed; verified live Preview slider refresh, Buttons=10 generating four
  icon-backed template slots plus six blank slots, Buttons Per Row=5 wrapping
  to `[2, 5]`, Button Size updating live preview scale to `1.25`, Save +
  Publish runtime commands, shelf toggle, and screenshot capture.
- Latest focused Edit Mode validation:
  `.\\.venv\\Scripts\\python.exe -m pytest tests\\test_edit_mode.py`
  -> 37 passed.
- Latest focused Edit Mode Ruff:
  `.\\.venv\\Scripts\\python.exe -m ruff check scripts\\actionrail\\edit_mode.py tests\\test_edit_mode.py`
  -> all checks passed.

## Decisions

- PySide6/Qt overlay is the MVP path.
- Viewport 2.0 is deferred until Qt overlay is stable and should be used only
  for scene/native drawing such as labels, guides, or object-bound graphics.
- Quick Create and the first Edit Mode shell are implemented; continue them
  through focused Phase 2 authoring slices instead of starting later modes.
- WoW-style customization remains the long-term authoring model: Edit Mode,
  action slots, hover-to-bind hotkeys, flyouts, command rings, and
  preset/profile layers.
- Treat `M/T/R/S/K` as a proof preset and regression target; ActionRail's
  product goal is broader user-authored viewport UI.
- Build the hotkey bridge through Maya runtime commands so bindings remain
  visible to Maya.
- Use `ActionRail` for product/module naming and `actionrail` for Python
  package/API naming.
- Use Python 3.11 in Maya, PySide6/Qt Widgets, custom Qt rail overlay,
  `maya.cmds`, OpenMayaUI, JSON specs, SVG icons, `.mod` packaging, and
  MayaSessiond verification.
- Keep web tech out of the core runtime; use it only for authoring/import tooling.
