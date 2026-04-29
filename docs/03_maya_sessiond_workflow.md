---
summary: How to use GG_MayaSessiond from this repo for live Maya verification and screenshot-capable agent loops.
read_when:
  - Verifying ActionRail inside Maya.
  - Running MCP tool calls from an agent.
  - Diagnosing a blocked Maya test loop.
---

# MayaSessiond Workflow

Use `GG_MayaSessiond` for live Maya verification when feasible. It closes the agentic loop: start Maya, call tools, inspect state, capture viewport, iterate.

## Command Prefix

Use the PATH-independent form from this repo:

```powershell
& ../GG_MayaSessiond/.venv/Scripts/python.exe -m gg_maya_sessiond.cli ...
```

Use repo-local state:

```powershell
--state-dir .gg-maya-sessiond
```

## Doctor

```powershell
& ../GG_MayaSessiond/.venv/Scripts/python.exe -m gg_maya_sessiond.cli doctor `
  --state-dir .gg-maya-sessiond `
  --json
```

Add `--mcp-src ../GG_MayaMCP` only when the sibling MCP checkout matches the Sessiond compatibility lock. As of 2026-04-28, the verified path omits `--mcp-src` and uses the MCP package installed in the Sessiond venv.

## Start

Prefer Maya 2025 unless a task needs another version.
The module path below points at the current checkout folder; product and API naming remain `ActionRail`/`actionrail`.
Use a repo/tool-specific daemon port so other Maya sessions are not affected. For this repo, prefer `7217` unless it is already in use.
Use an absolute `--mcp-script-dirs` path; relative paths may start Maya but leave `script.execute` without an allowlisted smoke-script directory.

```powershell
$smokeScripts = (Resolve-Path "tests/maya_smoke").Path
& ../GG_MayaSessiond/.venv/Scripts/python.exe -m gg_maya_sessiond.cli start `
  --state-dir .gg-maya-sessiond `
  --port 7217 `
  --maya-exe "../path/to/Maya2025/bin/maya.exe" `
  --mcp-python ../GG_MayaSessiond/.venv/Scripts/python.exe `
  --maya-module-path "." `
  --mcp-script-dirs $smokeScripts `
  --json
```

If Maya is already running under sessiond, use `status` first instead of starting a second session.

Before starting, check that the chosen port is free:

```powershell
Get-NetTCPConnection -LocalPort 7217 -ErrorAction SilentlyContinue
```

If it returns an existing listener, pick another repo-specific port and record it in `docs/04_status.md`.

## Status

```powershell
& ../GG_MayaSessiond/.venv/Scripts/python.exe -m gg_maya_sessiond.cli status `
  --state-dir .gg-maya-sessiond `
  --json
```

## Tool Discovery

Do not guess tool names.

```powershell
& ../GG_MayaSessiond/.venv/Scripts/python.exe -m gg_maya_sessiond.cli call `
  --state-dir .gg-maya-sessiond `
  --list `
  --json
```

For a specific tool:

```powershell
& ../GG_MayaSessiond/.venv/Scripts/python.exe -m gg_maya_sessiond.cli call `
  --state-dir .gg-maya-sessiond `
  <tool_name> `
  --tool-help `
  --json
```

## Basic Calls

```powershell
& ../GG_MayaSessiond/.venv/Scripts/python.exe -m gg_maya_sessiond.cli call `
  --state-dir .gg-maya-sessiond `
  scene.info `
  --json
```

Prefer native inspection tools over raw script execution. Use `script.execute` for checked-in smoke scripts under `tests/maya_smoke`; start sessiond with `--mcp-script-dirs tests/maya_smoke` so file execution is allowlisted. Use raw script execution only when needed to import/run ActionRail APIs.

## Stop

```powershell
& ../GG_MayaSessiond/.venv/Scripts/python.exe -m gg_maya_sessiond.cli stop `
  --state-dir .gg-maya-sessiond `
  --json
```

## Smoke Verification Targets

Record these in `docs/04_status.md`:

- `doctor` result.
- `start/status` result.
- `scene.info` result.
- ActionRail import result.
- show/hide/reload result.
- screenshot path, if capture works.
- exact blocker, if any step fails.

Checked-in smoke scripts live under `tests/maya_smoke/` and are allowlisted by the `--mcp-script-dirs` start flag above.

The repo-local wrapper below uses the stable `script.execute` command shape,
resolves the smoke-script directory to an absolute path, starts Sessiond only
when needed, discovers tools before running scripts, cleans Maya smoke state
before and after each selected script, validates that `script.execute` returned
the requested script payload, and fails if either the MCP call or script payload
reports failure.

```powershell
.\scripts\maya-smoke.ps1 -Script actionrail_phase0_smoke.py
```

Useful variants:

```powershell
.\scripts\maya-smoke.ps1 -NoStart -Script actionrail_maya_ui_smoke.py
.\scripts\maya-smoke.ps1 -NoStart -Script all
.\scripts\maya-smoke.ps1 -Port 7218 -Script actionrail_predicates_smoke.py
```

- `actionrail_phase0_smoke.py`: import, reference stack, action buttons, hide/reload cleanup.
- `actionrail_capture_smoke.py`: direct widget screenshot capture and reference widget metrics.
- `actionrail_horizontal_smoke.py`: horizontal rail layout, key labels, anchor, and opacity.
- `actionrail_hidden_visibility_smoke.py`: literal false visibility handling and empty-cluster regression.
- `actionrail_predicates_smoke.py`: selection/tool/action/command predicates driving initial visible, enabled, and active button state plus automatic timer refresh after tool and selection changes.
- `actionrail_hotkey_bridge_smoke.py`: runtime command publishing/execution for an action and preset slot without a visible overlay.
- `actionrail_hotkey_label_sync_smoke.py`: visible slot key-label update after ActionRail hotkey assignment.
- `actionrail_overlay_cleanup_smoke.py`: repeated show/reload cleanup for stale ActionRail viewport widgets and origin-placement regression coverage.
- `actionrail_maya_ui_smoke.py`: Maya menu/shelf toggle install, idempotency, command text, show/hide behavior, and uninstall cleanup.

After adding a new smoke script, update this list and add the exact result to `docs/04_status.md`.
