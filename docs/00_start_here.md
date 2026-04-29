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

- Local agent guidance exists: `AGENTS.MD`.
- Phase 0 prototype exists and has been verified in MayaSessiond.
- Phase 1 declarative MVP is in progress.
- Phase 1B runtime-command/hotkey bridge is started; rendered key labels now update after ActionRail hotkey assignment.
- Runtime-command sync helpers now prune stale ActionRail action and preset-slot commands when ids are renamed or removed.
- Safe predicate evaluation now drives initial `visible_when`, `enabled_when`, and `active_when` state at overlay build time using the overlay's resolved model panel for `active.panel` and `active.camera`.
- `ViewportOverlayHost.refresh_state()` now updates predicate-driven enabled/active state after creation and rebuilds the rail when `visible_when` changes, without requiring `actionrail.reload()`.
- Visible overlay hosts now run a host-owned Qt timer that automatically calls the predicate refresh path, so tool and selection state changes update the rail without manual refresh calls.
- The Qt rail host now anchors from the resolved model panel but shows the visible rail as a small frameless Maya-owned tool window, avoiding viewport toolbar repaint ghosts without covering the viewport.
- The rail box model now accounts for Qt style-sheet button/frame borders, so active and toned buttons stay visibly inset inside the rail. Current corrected `transform_stack` render size is `46x214`.
- Maya-native menu and shelf toggle entry points now install idempotently and call `actionrail.toggle_default()` to show/hide the default `transform_stack` preset.
- `scripts/maya-smoke.ps1` wraps the stable MayaSessiond `script.execute` command shape for checked-in smoke scripts.
- Safe-mode diagnostics now expose `actionrail.collect_diagnostics()`,
  `actionrail.diagnose_spec()`, and `actionrail.safe_start()` for broken
  presets, missing actions, missing command/plugin predicates, and recoverable
  overlay startup failures. In Maya, the default diagnostics path resolves
  `maya.cmds` automatically, so callers do not need to pass `cmds_module` for
  command/plugin availability warnings.
- Widget rendering now resolves each action-bearing slot through a reusable
  `SlotRenderState` and shared apply path, so label, key badge, tone, tooltip,
  enabled, and active state can update in place without rebuilding the rail when
  visibility is unchanged. Runtime hotkey badge overrides are preserved during
  predicate refresh.
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
10. `docs/01_architecture.md` and `docs/05_tech_stack.md` when deeper runtime or stack context is needed.

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

1. Continue extending `SlotRenderState` toward icon and diagnostic badge state so broken actions, missing icons, and richer badges can update without rebuilding whole rails where possible.
2. Use `scripts/maya-smoke.ps1` for repeatable MayaSessiond smoke runs when Maya verification is feasible.
3. Use `docs/07_missing_features_research.md` as the feature-gap backlog, but do not start the full designer before the declarative MVP is stable.

## Working Rules

- Keep docs current as work changes.
- Prefer small implementation slices with visible Maya verification.
- Do not start designer, icon importer, or Viewport 2.0 backend before the declarative MVP works.
- If Maya verification is blocked, record the exact blocker in `docs/04_status.md`.
