read: `../bram-agent-scripts/AGENTS.MD` before ANYTHING

# ActionRail

## Context
- Goal: ActionRail for Maya; polished viewport UI like `research/`.
- Start docs: `docs/00_start_here.md`; live handoff: `docs/04_status.md`; Edit Mode reference: `docs/08_edit_mode.md`.
- Deep reference: `docs/01_architecture.md`; roadmap: `docs/02_implementation_plan.md`; Maya verification: `docs/03_maya_sessiond_workflow.md`.
- Fast project map: `$env:PYTHONPATH="scripts"; .\.venv\Scripts\python.exe -m actionrail --json`.
- Live state stays compact in `docs/04_status.md`; long verification history belongs in `docs/history/verification_log.md`.
- Current implementation boundary: Phase 2 step 2.5 layout editing/direct manipulation on top of the verified Quick Create and Edit Mode shell. Do not jump to Bind Mode, flyouts, command rings, profile layers, marking-menu export, or Viewport 2.0.
- PySide6/Qt overlay first. Viewport 2.0 only for scene/native drawing.

## Workflow
- Start by reading `docs/00_start_here.md` and `docs/04_status.md`; run the project map command when code ownership or test routing is unclear.
- Prefer `actionrail.about()` / `python -m actionrail --json` before broad code crawling; use module `__all__` and ownership headers to pick files.
- Read `docs/08_edit_mode.md` before changing layout-map, selection, snapping, or persistence behavior.
- Default loop: edit -> live Maya -> inspect/screenshot -> iterate.
- Use `GG_MayaSessiond` for Maya verification when feasible.
- PATH-independent CLI:
  `& ../GG_MayaSessiond/.venv/Scripts/python.exe -m gg_maya_sessiond.cli ...`
- Use repo state dir `.gg-maya-sessiond`; prefer `doctor/status/start/call/stop`.
- Discover tools before guessing: `call --state-dir .gg-maya-sessiond --list --json`.
- Prefer native MCP inspection/screenshot tools before raw script execution.
- Before saying all tests passed, run full pytest, Ruff, and `maya-smoke.ps1 -Script all`.
- For docs-only changes, at minimum run the project map, docs-list, local Markdown link check, and any targeted consistency check such as smoke-list parity.
- Keep docs current so agents know big picture, done state, next work, blockers, and the active verification route.
- Keep `CHANGELOG.md` in sync with following updates; group related conventional commits into dated, user-facing bullets.
- Keep `docs/04_status.md` compact; archive long verification entries in `docs/history/verification_log.md`.
- After adding or renaming a Maya smoke script, update `docs/03_maya_sessiond_workflow.md` and the project/status docs as needed.

## Build Rules
- Package as Maya module: `scripts/actionrail`, `icons`, `presets`, `examples`.
- Use `maya.cmds` + PySide6; no PyMEL unless asked.
- Keep UI declarative: Python API + JSON presets + reusable actions.
- Verify UI changes in MayaSessiond or state exact blocker.
- Preserve locked built-in presets. Layout edits should persist through user presets or user overrides, not direct mutation of bundled/studio presets.
