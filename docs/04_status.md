---
summary: Live project status for agents: what is done, what is next, blockers, latest handoff, and latest verification.
read_when:
  - Starting work after another agent.
  - Finishing any implementation or research slice.
  - Checking current blockers before editing code.
---

# Status

Last updated: 2026-05-05

## Current Snapshot

ActionRail has a verified declarative MVP and Phase 2 authoring foundation
through Quick Create preview/save/load and the first Edit Mode layout-map
shell.

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
  save, overwrite, and load-existing user preset workflow.
- Edit Mode shell with layout-map overlay, grid controls, Snap to Grid, Sticky
  Frames, active rail frames, selection, right-click routing, and session-local
  X/Y movement for unlocked rails.

Long-form implementation and verification history belongs in
`docs/history/verification_log.md`.

## In Progress

Phase 2 step 2.5 Layout Editing And Direct Manipulation is next.

Focus this slice on:

- persisting adjusted rail offsets/layout values to user presets or user
  overrides
- drag handles, anchor pins, safe margins, snap guides, and spacing guides
- fuller right-click frame options routing
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

3. Begin Phase 2 step 2.5 on top of the verified Edit Mode shell.
4. Use `scripts/maya-smoke.ps1` for repeatable MayaSessiond smoke runs when feasible.

## Latest Handoff

- Phase 2 step 2.4 Edit Mode shell and rail selection is implemented and Maya
  screenshot verified.
- Quick Create can preview/save/load user presets.
- Edit Mode can inspect active rails, select frames, show grid/snap/sticky
  controls, move unlocked rails in-session, and route right-click options.
- Saved layout persistence and fuller direct manipulation are the exact next
  implementation step.
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

- Coverage gate:
  `.\\.venv\\Scripts\\python.exe -m coverage run -m pytest; .\\.venv\\Scripts\\python.exe -m coverage report`
  -> 395 passed, `TOTAL 4145 0 100%`.
- Ruff:
  `.\\.venv\\Scripts\\python.exe -m ruff check .`
  -> all checks passed.
- Edit Mode Maya smoke:
  `.\\scripts\\maya-smoke.ps1 -StateDir .gg-maya-sessiond-edit -Port 7219 -Script actionrail_edit_mode_smoke.py -Timeout 240 -NoStart`
  -> passed; verified layout-map overlay, Grid Size 64, Snap to Grid, Sticky
  Frames, left-click selection, X coordinate movement, sticky-frame alignment,
  right-click options routing, and screenshot capture at
  `.gg-maya-sessiond/screenshots/actionrail_edit_mode_layout_map.png`.
- Full Maya smoke baseline:
  `.\\scripts\\maya-smoke.ps1 -StateDir .gg-maya-sessiond-edit -Port 7219 -Script all -Timeout 240 -NoStart`
  -> passed against a separate MayaSessiond on port `7219`; covered capture,
  diagnostic badges, diagnostics window, hidden visibility, Edit Mode,
  horizontal and Maya icon rails, hotkey bridge, import/recovery diagnostics,
  menu/shelf UI, overlay cleanup, predicates, Quick Create, StackItem ABI, and
  transform-stack state.
- Screenshot inspection confirmed these rendered correctly:
  `.gg-maya-sessiond/screenshots/actionrail_edit_mode_layout_map.png`,
  `.gg-maya-sessiond/screenshots/actionrail_quick_create_panel.png`,
  `.gg-maya-sessiond/screenshots/actionrail_diagnostics_window.png`, and
  `.gg-maya-sessiond/screenshots/actionrail_horizontal_tools_widget.png`.
- Latest Maya note: Maya smoke used the installed MCP package in the Sessiond
  venv; do not pass `--mcp-src ../GG_MayaMCP` until the sibling repo
  compatibility blocker is resolved.

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
