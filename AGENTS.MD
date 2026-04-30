read: `../bram-agent-scripts/AGENTS.MD` before ANYTHING

# ActionRail

## Context
- Goal: ActionRail for Maya; polished viewport UI like `research/`.
- Start docs: `docs/00_start_here.md`; deep reference: `docs/01_architecture.md`.
- Fast project map: `$env:PYTHONPATH="scripts"; .\.venv\Scripts\python.exe -m actionrail --json`.
- Live state: `docs/04_status.md`; old verification history: `docs/history/verification_log.md` only when auditing regressions.
- PySide6/Qt overlay first. Viewport 2.0 only for scene/native drawing.

## Workflow
- Start by reading `docs/00_start_here.md` and `docs/04_status.md`; run the project map command when code ownership or test routing is unclear.
- Prefer `actionrail.about()` / `python -m actionrail --json` before broad code crawling; use module `__all__` and ownership headers to pick files.
- Default loop: edit -> live Maya -> inspect/screenshot -> iterate.
- Use `GG_MayaSessiond` for Maya verification when feasible.
- PATH-independent CLI:
  `& ../GG_MayaSessiond/.venv/Scripts/python.exe -m gg_maya_sessiond.cli ...`
- Use repo state dir `.gg-maya-sessiond`; prefer `doctor/status/start/call/stop`.
- Discover tools before guessing: `call --state-dir .gg-maya-sessiond --list --json`.
- Prefer native MCP inspection/screenshot tools before raw script execution.
- Before saying all tests passed, run full pytest, Ruff, and `maya-smoke.ps1 -Script all`.
- Keep docs current so agents know big picture, done state, next work, and blockers.
- Keep `docs/04_status.md` compact; archive long verification entries in `docs/history/verification_log.md`.

## Build Rules
- Package as Maya module: `scripts/actionrail`, `icons`, `presets`, `examples`.
- Use `maya.cmds` + PySide6; no PyMEL unless asked.
- Keep UI declarative: Python API + JSON presets + reusable actions.
- Verify UI changes in MayaSessiond or state exact blocker.
