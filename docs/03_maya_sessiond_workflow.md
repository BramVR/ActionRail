---
summary: How to use GG_MayaSessiond from this repo for live Maya verification and screenshot-capable agent loops.
read_when:
  - Verifying ScreenUI inside Maya.
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
  --mcp-src ../GG_MayaMCP `
  --json
```

## Start

Prefer Maya 2025 unless a task needs another version.

```powershell
& ../GG_MayaSessiond/.venv/Scripts/python.exe -m gg_maya_sessiond.cli start `
  --state-dir .gg-maya-sessiond `
  --maya-exe "C:/Program Files/Autodesk/Maya2025/bin/maya.exe" `
  --mcp-python C:/PROJECTS/GG/GG_MayaSessiond/.venv/Scripts/python.exe `
  --mcp-src C:/PROJECTS/GG/GG_MayaMCP `
  --maya-module-path "C:/PROJECTS/GG/ScreenUI" `
  --json
```

If Maya is already running under sessiond, use `status` first instead of starting a second session.

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

Prefer native inspection tools over raw script execution. Use raw script execution only when needed to import/run ScreenUI APIs.

## Stop

```powershell
& ../GG_MayaSessiond/.venv/Scripts/python.exe -m gg_maya_sessiond.cli stop `
  --state-dir .gg-maya-sessiond `
  --json
```

## Verification Target For Phase 0

Record these in `docs/04_status.md`:

- `doctor` result.
- `start/status` result.
- `scene.info` result.
- ScreenUI import result.
- show/hide/reload result.
- screenshot path, if capture works.
- exact blocker, if any step fails.
