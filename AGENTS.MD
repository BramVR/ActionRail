read: `../bram-agent-scripts/AGENTS.MD` before ANYTHING

# ActionRail

## Context
- Goal: ActionRail for Maya; polished viewport UI like `research/`.
- Start docs: `docs/00_start_here.md`; deep reference: `MAYA_UI_FRAMEWORK_REPORT.md`.
- PySide6/Qt overlay first. Viewport 2.0 only for scene/native drawing.

## Workflow
- Default loop: edit -> live Maya -> inspect/screenshot -> iterate.
- Use `GG_MayaSessiond` for Maya verification when feasible.
- PATH-independent CLI:
  `& ../GG_MayaSessiond/.venv/Scripts/python.exe -m gg_maya_sessiond.cli ...`
- Use repo state dir `.gg-maya-sessiond`; prefer `doctor/status/start/call/stop`.
- Discover tools before guessing: `call --state-dir .gg-maya-sessiond --list --json`.
- Prefer native MCP inspection/screenshot tools before raw script execution.
- Keep docs current so agents know big picture, done state, next work, and blockers.

## Build Rules
- Package as Maya module: `scripts/actionrail`, `icons`, `presets`, `examples`.
- Use `maya.cmds` + PySide6; no PyMEL unless asked.
- Keep UI declarative: Python API + JSON presets + reusable actions.
- Verify UI changes in MayaSessiond or state exact blocker.
