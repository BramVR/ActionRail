---
summary: First doc to read before working on ScreenUI; explains the goal, current state, read order, and first implementation slice.
read_when:
  - Starting a new agent session.
  - Picking up ScreenUI implementation work.
  - Updating docs after a meaningful change.
---

# Start Here

## Goal

ScreenUI is a Maya framework for polished, user-created viewport UI: compact tool stacks, buttons, badges, and later authoring tools like Quick Create.

The reference target is in `research/`:

- `Move_translate_rotate_scale.png`: compact `M/T/R/S` stack.
- `Move_translate_rotate_scale_key.png`: same stack plus separate `K` key button.

## Current State

- Research report exists: `MAYA_UI_FRAMEWORK_REPORT.md`.
- Local agent guidance exists: `AGENTS.MD`.
- No implementation exists yet.
- This directory is not currently a git repo.

## Read Order

1. `AGENTS.MD`
2. `docs/00_start_here.md`
3. `docs/04_status.md`
4. `docs/01_architecture.md`
5. `docs/02_implementation_plan.md`
6. `docs/03_maya_sessiond_workflow.md`
7. `MAYA_UI_FRAMEWORK_REPORT.md` when deeper context is needed.

## Product Decision

Build PySide6/Qt overlay first.

- PySide overlay draws on top of Maya's viewport.
- Viewport 2.0 is later, only for native scene/viewport drawing.
- Core UX is declarative presets plus reusable Maya actions.

## First Agent Task

Implement Phase 0 prototype:

1. Create Maya module/package skeleton.
2. Add PySide import shim.
3. Add a hard-coded viewport overlay host.
4. Render the `M/T/R/S + K` reference stack.
5. Bind buttons to move/translate/rotate/scale/set-key actions.
6. Add reload/show/hide entry points.
7. Verify in Maya via `GG_MayaSessiond` when feasible.
8. Update `docs/04_status.md` with exact done/next/blocker state.

## Working Rules

- Keep docs current as work changes.
- Prefer small implementation slices with visible Maya verification.
- Do not start designer, icon importer, or Viewport 2.0 backend before Phase 0 works.
- If Maya verification is blocked, record the exact blocker in `docs/04_status.md`.
