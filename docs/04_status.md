---
summary: Live project status for agents: what is done, what is next, blockers, and verification history.
read_when:
  - Starting work after another agent.
  - Finishing any implementation or research slice.
  - Checking current blockers before editing code.
---

# Status

Last updated: 2026-04-27

## Done

- Research images collected in `research/`.
- Architecture/report written in `MAYA_UI_FRAMEWORK_REPORT.md`.
- Local `AGENTS.MD` updated with ScreenUI rules and MayaSessiond workflow.
- Agent onboarding docs created:
  - `docs/00_start_here.md`
  - `docs/01_architecture.md`
  - `docs/02_implementation_plan.md`
  - `docs/03_maya_sessiond_workflow.md`
  - `docs/04_status.md`

## In Progress

- Ready for Phase 0 implementation.

## Next

1. Create Maya module skeleton.
2. Add PySide import shim.
3. Add viewport overlay host.
4. Render hard-coded `M/T/R/S + K` stack.
5. Bind Maya actions.
6. Add reload/show/hide APIs.
7. Verify with MayaSessiond.
8. Update this file.

## Blockers

- None known.
- MayaSessiond has not yet been run from this repo.

## Verification History

- Docs only. No code verification yet.

## Decisions

- PySide6/Qt overlay is the MVP path.
- Viewport 2.0 is deferred until Qt overlay is stable.
- Designer/Quick Create is deferred until Phase 0 and declarative MVP are stable.
- Use `GG_MayaSessiond` for live Maya verification when feasible.
