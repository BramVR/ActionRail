---
summary: First doc to read before working on ActionRail; routes agents to current status, architecture, workflow, and deeper backlog docs.
read_when:
  - Starting a new agent session.
  - Picking up ActionRail implementation work.
  - Updating docs after a meaningful change.
---

# Start Here

## Goal

ActionRail is a Maya framework for polished, user-created viewport UI: compact rails, action bars, buttons, hotkey badges, and later authoring tools like Quick Create.

The `M/T/R/S/K` transform stack is the first proof preset, not the product boundary. ActionRail should be able to recreate it, but the broader goal is to let users compose their own rails, slots, hotkey badges, flyouts, and command layouts without changing framework code. Think of buttons as user-authored action slots/macros: each slot defines what it does and which state predicates it uses; the theme defines how active, disabled, locked, hovered, or warning states look.

The proof-preset visual references live in local `research/` checkouts when present.
That folder is ignored by Git; committed documentation images live in `docs/assets/`.

- `Move_translate_rotate_scale.png`: compact `M/T/R/S` stack.
- `Move_translate_rotate_scale_key.png`: same stack plus separate `K` key button.

## Current State

Live detail belongs in `docs/04_status.md`; keep this page as a routing
document.

Snapshot:

- Phase 0 prototype is verified; Phase 1 declarative MVP is in progress.
- Working surface includes JSON presets, Qt overlay lifecycle, reusable actions,
  runtime-command hotkey publishing, predicate refresh, diagnostic badges,
  safe-mode diagnostics, menu/shelf toggles, the diagnostics Qt window, and the
  SVG import helper with generated PNG fallbacks.
- Built-in preset ids currently include `transform_stack` and
  `horizontal_tools`.
- Icon import diagnostics are now exposed through a Maya menu flow that
  preflights a local SVG and opens the copyable diagnostics window.
- Current next implementation slice: keep hardening visible diagnostics as the
  import path expands; do not start the full designer yet.
- Long verification history is archived in
  `docs/history/verification_log.md`; `docs/04_status.md` keeps only the live
  snapshot, blockers, latest handoff, and latest verification summary.
- For a machine-readable map, run:

```powershell
$env:PYTHONPATH = "scripts"
.\.venv\Scripts\python.exe -m actionrail --json
```

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
10. `docs/history/verification_log.md` only when auditing older verification runs.
11. `docs/01_architecture.md` and `docs/05_tech_stack.md` when deeper runtime or stack context is needed.

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

1. Replace `actionrail.show_last_report()`'s `confirmDialog` with a polished,
   themed Qt diagnostics window that supports visible issue details and
   copyable reports. Done.
2. Continue diagnostic work toward the future icon-backed preset/import
   pipeline. First icon-backed rail, manifest/SVG validation, local SVG import,
   PNG fallback generation, fallback asset diagnostics, import preflight
   reports, and opt-in preset recovery are done.
3. Use `scripts/maya-smoke.ps1` for repeatable MayaSessiond smoke runs when Maya verification is feasible.
4. Use `docs/07_missing_features_research.md` as the feature-gap backlog, but do not start the full designer before the declarative MVP is stable.

## Working Rules

- Keep docs current as work changes.
- Prefer small implementation slices with visible Maya verification.
- Do not start designer, icon importer, or Viewport 2.0 backend before the declarative MVP works.
- If Maya verification is blocked, record the exact blocker in `docs/04_status.md`.
