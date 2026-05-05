# ActionRail Open-Issue Audit

Date: 2026-05-05
Repo: `C:\PROJECTS\GG\ScreenUI`
Branch inspected: `main`
Scope: commits from the last 24 hours, prior Codex QA notes, local model probes,
and MayaSessiond-hosted Quick Create smoke.

## Summary

This report is separate from `actionrail-qa-report-2026-05-05.md`, which mostly
records regressions already fixed in earlier commits. The items below are open
at current `HEAD` and should not be counted as fixed.

Current result: 18 open issues found. Several are data-loss paths in Quick
Create load/save workflows, and several are Phase 2.5 direct-manipulation gaps
that still affect whether ActionRail feels safe as an authoring tool.

## Evidence

- Recent commit window inspected:
  `git log --since='24 hours ago' --date=iso --pretty=format:'%h %ad %an %s'`
- Project map:
  `$env:PYTHONPATH='scripts'; .\.venv\Scripts\python.exe -m actionrail --json`
- Prior Codex QA report/log context:
  `.spec/actionrail-qa-report-2026-05-05.md` and session log search under
  `C:\Users\ZO\.codex\sessions\2026\05\04` and `...\05\05`
- MayaSessiond MCP status/tool discovery:
  `gg_maya_sessiond.cli status --state-dir .gg-maya-sessiond --json`
  and `call --state-dir .gg-maya-sessiond --list --json`
- Maya-hosted smoke:
  `.\scripts\maya-smoke.ps1 -Script actionrail_quick_create_smoke.py -Timeout 240`
  -> passed, proving the default happy path works in Maya but not covering the
  richer preset round-trip failures below.
- Local probes:
  direct Python probes against `actionrail.quick_create`, `actionrail.spec`,
  `actionrail.preset_store`, and `actionrail.edit_mode`.

## Open Issues

1. AR-OPEN-001: Quick Create load/save drops spacer items.
   Evidence: a saved user preset with item types `button, spacer, button`
   loads as two editable slots and rebuilds as `button, button`. Code:
   `scripts/actionrail/quick_create.py` filters out spacers in
   `load_quick_create_preset`.
   Impact: editing an existing rail in Quick Create can permanently remove
   deliberate spacing.
   Status: fixed in `fix(quick-create): preserve rich preset round trips`.

2. AR-OPEN-002: Quick Create load/save drops per-button `tone`.
   Evidence: a button with `tone='teal'` round-trips back as `neutral`.
   Impact: authoring an existing styled preset through Quick Create resets
   semantic button color.
   Status: fixed in `fix(quick-create): preserve rich preset round trips`.

3. AR-OPEN-003: Quick Create load/save drops custom `tooltip`.
   Evidence: a button with `tooltip='Custom tip'` round-trips back as the
   action id fallback.
   Impact: user-authored help text is lost on overwrite.
   Status: fixed in `fix(quick-create): preserve rich preset round trips`.

4. AR-OPEN-004: Quick Create load/save drops `visible_when`.
   Evidence: `visible_when='selection.count > 0'` round-trips back as an empty
   predicate.
   Impact: conditional visibility rules can be silently erased.
   Status: fixed in `fix(quick-create): preserve rich preset round trips`.

5. AR-OPEN-005: Quick Create load/save drops `enabled_when`.
   Evidence: `enabled_when='plugin.exists("foo")'` round-trips back as an empty
   predicate.
   Impact: actions that should be disabled until their dependency is present
   can become clickable.
   Status: fixed in `fix(quick-create): preserve rich preset round trips`.

6. AR-OPEN-006: Quick Create load/save drops `active_when`.
   Evidence: `active_when='maya.tool == move'` round-trips back as an empty
   predicate.
   Impact: active-state feedback can disappear after editing a preset.
   Status: fixed in `fix(quick-create): preserve rich preset round trips`.

7. AR-OPEN-007: Quick Create UI load/save does not accept or retain a custom
   user preset directory.
   Evidence: `quick_create_ui.load_existing()` calls
   `load_quick_create_preset(preset_text)` and `save_draft()` calls
   `save_quick_create_preset(... overwrite=...)` without a `preset_dir`, unlike
   the recently fixed Edit Mode custom-store path.
   Impact: a preset opened from a non-default store can be saved to the wrong
   store or fail to load from the visible project/session store.
   Status: fixed in `fix(quick-create): preserve panel store and custom ids`.

8. AR-OPEN-008: Unknown action or icon values cannot be faithfully edited in
   the Quick Create UI.
   Evidence: `_set_combo_text()` leaves a combo unchanged when the saved value
   is not in the fixed combo list, and `_slot_input_from_row()` later reads the
   current combo text.
   Impact: externally authored action or icon ids can be overwritten by an
   unrelated visible combo selection.
   Status: fixed in `fix(quick-create): preserve panel store and custom ids`.

9. AR-OPEN-009: Quick Create accepts contradictory layout dimensions.
   Evidence: building the horizontal template with `rows=1`, `columns=1`, and
   four slots produces a spec with one row, one column, and four items.
   Impact: users can save ambiguous layout metadata that the runtime has to
   interpret later.
   Status: fixed in `fix(authoring): align layout bounds`.

10. AR-OPEN-010: Runtime schema allows row counts the Quick Create UI cannot
    preserve.
    Evidence: `parse_stack_spec()` accepts `rows=99`, while the UI spin box is
    capped at 12.
    Impact: loading and saving a valid existing preset through the UI can clamp
    its layout.
    Status: fixed in `fix(authoring): align layout bounds`.

11. AR-OPEN-011: Runtime schema allows column counts the Quick Create UI cannot
    preserve.
    Evidence: `parse_stack_spec()` accepts `columns=99`, while the UI spin box
    is capped at 12.
    Impact: wide or dense rails can be damaged by the authoring panel.
    Status: fixed in `fix(authoring): align layout bounds`.

12. AR-OPEN-012: Runtime schema allows offset values the Quick Create UI cannot
    preserve.
    Evidence: `parse_stack_spec()` accepts `offset=[5000, -5000]`, while the UI
    offset controls are capped at `-400..400`.
    Impact: existing off-edge or workspace-specific placement can be clamped on
    edit/save.
    Status: fixed in `fix(authoring): align layout bounds`.

13. AR-OPEN-013: Runtime schema allows scale values the Quick Create UI cannot
    preserve.
    Evidence: `parse_stack_spec()` accepts `scale=10.0`, while the UI scale
    control is capped at `4.0`.
    Impact: large-format rails can be shrunk silently after editing.
    Status: fixed in `fix(authoring): align layout bounds`.

14. AR-OPEN-014: Preset discovery lists invalid user preset ids.
    Evidence: `PresetStore.ids()` reports a user file named `bad id!.json`, but
    attempting to load it raises a preset-id validation error.
    Impact: pickers can present ids that cannot actually be opened.
    Status: fixed in `fix(presets): filter broken discovery ids`.

15. AR-OPEN-015: Preset discovery lists malformed user preset files as normal
    entries.
    Evidence: `PresetStore.entries()` reports `mismatch.json`, but loading it
    raises schema validation because its layout is malformed.
    Impact: UI lists can include broken presets without an error marker or
    recovery path.
    Status: fixed in `fix(presets): filter broken discovery ids`.

16. AR-OPEN-016: Edit Mode snapping has no viewport clamp or safe-margin guard.
    Evidence: `_snapped_position()` returns `(-128, -128)` for a negative move
    and `(99968, 99968)` for a huge move with a 64px grid.
    Impact: a rail can be moved far outside the useful viewport area.
    Status: fixed in `fix(edit-mode): clamp rail movement to safe bounds`.

17. AR-OPEN-017: Built-in/studio user-override persistence is still missing.
    Evidence: `docs/08_edit_mode.md` lists it as not implemented, and current
    Save Position behavior is scoped to unlocked runtime/user rails.
    Impact: users cannot safely personalize locked shipped/studio rails without
    creating separate user presets.
    Status: fixed in `fix(edit-mode): save builtin layout overrides`.

18. AR-OPEN-018: Edit Mode direct-manipulation controls are still incomplete.
    Evidence: `docs/08_edit_mode.md` lists drag handles, anchor pins,
    snap/spacing guide rendering, fuller rail options, slot add/remove/reorder,
    and collapsible edge-tab controls as not implemented.
    Impact: the current Edit Mode shell still requires indirect controls and
    cannot yet serve as the polished viewport layout editor described in the
    Phase 2.5 goal.
    Status: fixed in `feat(edit-mode): add direct manipulation controls`.

## Fixed Items Not Counted

The previous report's fixed items are intentionally excluded from the 18-item
open count. That includes the custom user-preset store save regression fixed by
`7a06d56`, snap/grid regressions fixed in earlier Edit Mode commits, hotkey
runtime-command collision handling, empty-selection Set Key protection, and the
Quick Create basic validation/load-protection fixes.

## Recommended Fix Order

1. Fix Quick Create round-trip data loss first: preserve spacers and metadata or
   explicitly reject richer presets with a non-destructive warning.
2. Make Quick Create UI store-aware, matching the custom preset directory route
   already added for Edit Mode.
3. Add discovery diagnostics for broken user preset files so pickers can show
   actionable errors instead of unusable entries.
4. Add viewport clamps/safe margins before expanding direct manipulation.
5. Then continue the planned Phase 2.5 editor controls: built-in overrides,
   handles, anchor pins, guides, and slot operations.
