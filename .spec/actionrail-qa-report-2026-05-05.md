# ActionRail 24h Commit QA Report

Date: 2026-05-05
Repo: C:\PROJECTS\GG\ScreenUI
Branch: main
Scope: commits from the last 24 hours, with emphasis on Quick Create,
diagnostics, hotkeys, Edit Mode, layout persistence, and Maya-hosted overlay
behavior.

## Summary

I reviewed the last-24-hour commit stack, mined prior Codex QA logs, reran the
local and Maya gates, added a regression smoke for a newly found issue, and
implemented a fix for the current regression found in this pass.

Current new fix: Edit Mode Save Position now preserves custom user-preset store
routing for overlays loaded with `show_preset(..., user_preset_dir=...)`.

Fix commit: `7a06d56 fix(edit-mode): preserve custom preset store saves`.

## Evidence

- Recent commit window inspected with:
  `git log --since='24 hours ago' --date=iso --pretty=format:'%h %ad %an %s'`
- Prior Codex logs mined from:
  `C:\Users\ZO\.codex\sessions\2026\05\04`
  and `C:\Users\ZO\.codex\sessions\2026\05\05`
- MayaSessiond MCP status/tool discovery:
  `doctor`, `status`, and `call --list --json` against `.gg-maya-sessiond`
- Local verification:
  `.\\.venv\\Scripts\\python.exe -m pytest` -> 401 passed
- Lint:
  `.\\.venv\\Scripts\\python.exe -m ruff check .` -> passed
- Project map:
  `$env:PYTHONPATH='scripts'; .\\.venv\\Scripts\\python.exe -m actionrail --json` -> passed
- Docs:
  `docs-list.ps1` -> passed
  local Markdown link scan -> `Local Markdown links OK`
- Maya targeted verification:
  `.\\scripts\\maya-smoke.ps1 -Script actionrail_custom_preset_store_smoke.py -Timeout 240` -> passed
- Maya full baseline:
  `.\\scripts\\maya-smoke.ps1 -Script all -Timeout 300` -> passed, including
  the new custom user-preset store smoke.

## Issue Inventory

1. AR-QA-001: Edit Mode Save Position wrote custom-store user presets to the
   default ActionRail preset folder.
   Status: fixed in this pass. Evidence:
   `actionrail_custom_preset_store_smoke.py`, `tests/test_edit_mode.py`,
   `tests/test_package.py`.

2. AR-EDIT-QA-001: Snap to Grid was bypassed by X/Y spinbox edits and arrow
   nudges.
   Status: fixed before this pass, reverified by current Edit Mode smoke.

3. AR-EDIT-QA-002: Sticky Frames could override Snap to Grid and leave the final
   rail position off-grid.
   Status: fixed before this pass, reverified by current Edit Mode smoke.

4. AR-EDIT-QA-003: Grid Size accepted 4px, making the layout map visually
   unusable.
   Status: fixed before this pass, covered by tests and smoke.

5. AR-EDIT-QA-004: Right-click recorded an options target but opened no visible
   options surface.
   Status: fixed before this pass, reverified by current Edit Mode smoke.

6. AR-EDIT-QA-005: Edit Mode panel summary clipped selected/options text.
   Status: fixed before this pass, covered by tests.

7. AR-EDIT-QA-006: Lock state showed `Unlocked` when no rail frame was selected.
   Status: fixed before this pass, reverified by smoke and tests.

8. AR-EDIT-QA-007: Grid Size remained enabled while Grid was hidden, making the
   dependency unclear.
   Status: fixed before this pass, reverified by current Edit Mode smoke.

9. AR-EDIT-QA-008: Options popover could drift after overlay resize instead of
   resyncing to the frame.
   Status: fixed before this pass by `fix(edit-mode): keep options popover anchored`.

10. AR-QC-001: Quick Create drafts could reach preview/save without enough
    validation.
    Status: fixed in recent commits, covered by `tests/test_quick_create.py`.

11. AR-QC-002: Saved Quick Create presets needed load/edit protection so built-ins
    could not be edited through the saved-preset workflow.
    Status: fixed in recent commits, covered by Quick Create tests and Maya smoke.

12. AR-HOTKEY-001: Sanitized runtime command names could collide for different
    slots.
    Status: fixed in recent commits, covered by hotkey tests and smoke.

13. AR-ACTION-001: Set Key could run against empty selection and break the user
    flow.
    Status: fixed in recent commits, covered by action tests and Maya smoke.

14. AR-DIAG-001: Diagnostics report copy behavior needed smoke hardening to avoid
    regressions in support/reporting flows.
    Status: fixed in recent commits, covered by diagnostics smoke.

15. AR-LAYOUT-001: Edit Mode adjusted positions had no durable layout-save path
    before the latest layout persistence slice.
    Status: fixed in current HEAD and reverified by Edit Mode smoke.

16. AR-DOC-001: Edit Mode README screenshot alignment drifted from the actual
    UI state.
    Status: fixed in recent commits; screenshot artifacts were inspected during
    this QA pass.

## Current Fix

Changed:

- `scripts/actionrail/runtime.py`
- `scripts/actionrail/edit_mode.py`
- `tests/test_edit_mode.py`
- `tests/test_package.py`
- `tests/maya_smoke/actionrail_custom_preset_store_smoke.py`
- `docs/03_maya_sessiond_workflow.md`
- `docs/04_status.md`
- `CHANGELOG.md`

Behavior:

- `show_preset(..., user_preset_dir=...)` stores the resolved user preset dir on
  the runtime host.
- Edit Mode source classification checks that same custom store.
- `save_edit_mode_layout()` defaults to the runtime host's custom store when no
  explicit `user_preset_dir` is passed.

## Residual Risk

- This pass does not claim mathematical 100% coverage. It does cover the recent
  public API path, Maya-hosted Qt path, and full smoke baseline.
- Existing unrelated local edit: `AGENTS.MD` remains outside the fix and should
  be reviewed separately.
