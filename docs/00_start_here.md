---
summary: First doc to read before working on ActionRail; explains the goal, current state, read order, and first implementation slice.
read_when:
  - Starting a new agent session.
  - Picking up ActionRail implementation work.
  - Updating docs after a meaningful change.
---

# Start Here

## Goal

ActionRail is a Maya framework for polished, user-created viewport UI: compact rails, action bars, buttons, hotkey badges, and later authoring tools like Quick Create.

The `M/T/R/S/K` transform stack is the first proof preset, not the product boundary. ActionRail should be able to recreate it, but the broader goal is to let users compose their own rails, slots, hotkey badges, flyouts, and command layouts without changing framework code.

The proof-preset visual references live in local `research/` checkouts when present.
That folder is ignored by Git; committed documentation images live in `docs/assets/`.

- `Move_translate_rotate_scale.png`: compact `M/T/R/S` stack.
- `Move_translate_rotate_scale_key.png`: same stack plus separate `K` key button.

## Current State

- Research report exists: `MAYA_UI_FRAMEWORK_REPORT.md`.
- Local agent guidance exists: `AGENTS.MD`.
- Phase 0 prototype exists and has been verified in MayaSessiond.
- Phase 1 declarative MVP is in progress.
- Phase 1B runtime-command/hotkey bridge is started; rendered key labels now update after ActionRail hotkey assignment.
- WoW-style customization roadmap exists in `docs/06_wow_style_customization.md`.

## Read Order

1. `AGENTS.MD`
2. `docs/00_start_here.md`
3. `docs/04_status.md`
4. `docs/01_architecture.md`
5. `docs/02_implementation_plan.md`
6. `docs/03_maya_sessiond_workflow.md`
7. `docs/05_tech_stack.md`
8. `docs/06_wow_style_customization.md` when planning Edit Mode, hotkeys, flyouts, rings, or profile layers.
9. `docs/07_missing_features_research.md` when planning missing features or prioritizing the next roadmap slice.
10. `MAYA_UI_FRAMEWORK_REPORT.md` when deeper context is needed.

## Product Decision

Build PySide6/Qt overlay first.

- PySide overlay draws on top of Maya's viewport.
- Use Python 3.11 in Maya, PySide6/Qt Widgets, `maya.cmds`, OpenMayaUI, JSON specs, SVG icons with PNG fallbacks, Maya `.mod` packaging, and MayaSessiond verification.
- Spike Maya 2026 `moverlay` early, but only adopt it if it proves ActionRail's anchoring, hit testing, styling, and cleanup needs.
- Viewport 2.0 is later, only for native scene/viewport drawing.
- Web tools are for authoring/import only, not the core runtime.
- Core UX is user-authored declarative presets plus reusable Maya actions.
- Longer-term authoring UX borrows from WoW-style action bar customization: Edit Mode, action slots, hover-to-bind hotkeys, flyouts, command rings, and user/project/studio profiles.

## Current Priority

Continue Phase 1 declarative MVP:

1. Add real predicate evaluation for `visible_when`, `enabled_when`, and `active_when`.
2. Add safe unpublish/update behavior for renamed or removed published hotkey commands.
3. Add shelf/menu toggle once reload cleanup stays stable.
4. Use `docs/07_missing_features_research.md` as the feature-gap backlog, but do not start the full designer before the declarative MVP is stable.

## Working Rules

- Keep docs current as work changes.
- Prefer small implementation slices with visible Maya verification.
- Do not start designer, icon importer, or Viewport 2.0 backend before the declarative MVP works.
- If Maya verification is blocked, record the exact blocker in `docs/04_status.md`.
