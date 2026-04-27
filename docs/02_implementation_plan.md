---
summary: Phase-based implementation plan with the immediate task list and acceptance criteria for the first agent.
read_when:
  - Choosing what to implement next.
  - Checking whether a slice is complete.
  - Updating project status after implementation.
---

# Implementation Plan

## Phase 0: Viewport Overlay Prototype

Goal: show the research UI in Maya as a clickable PySide6 overlay.

### Tasks

1. Create module skeleton.
2. Create PySide compatibility shim.
3. Locate Maya main window and active model panel.
4. Create transparent overlay widget parented to the viewport/model panel.
5. Add hard-coded reference stack:
   - `M`, `T`, `R`, `S` grouped vertically.
   - `S` pink active/accent state.
   - separate teal `K` button below.
6. Bind actions:
   - move/translate tool
   - rotate tool
   - scale tool
   - set key
7. Add reload/show/hide API:
   - `actionrail.reload()`
   - `actionrail.show_example("transform_stack")`
   - `actionrail.hide_all()`
8. Add minimal cleanup registry for widgets/callbacks.
9. Verify in Maya and capture a screenshot if possible.
10. Update `docs/04_status.md`.

### Acceptance Criteria

- `import actionrail` works in Maya.
- `actionrail.show_example("transform_stack")` shows the stack.
- Empty overlay space does not block viewport navigation.
- Buttons trigger expected Maya actions.
- Repeated show/hide/reload does not duplicate visible widgets.
- Resize or panel switch does not leave a broken overlay in the common case.
- Maya verification result is recorded in `docs/04_status.md`.

## Phase 1: Declarative MVP

Goal: make the prototype reusable.

### Tasks

- JSON preset loader.
- Python builder API.
- Theme tokens and QSS generation.
- Reusable action registry.
- Shelf/menu toggle.
- Basic validation for missing actions and bad preset shape.
- `scripts/maya-smoke.ps1` if command shape is stable.

### Acceptance Criteria

- Reference stack can be created from JSON without editing framework code.
- Built-in example loads from `examples/` or `presets/`.
- Reload cleanup is reliable.
- Basic mayapy or MayaSessiond smoke test exists.

## Phase 2: Quick Create

Goal: let users create palettes without code.

### Tasks

- Dockable workspace-control panel.
- Template picker.
- Action picker.
- Live preview.
- Save/load user presets.
- Publish to shelf/hotkey/runtime command where possible.

## Phase 3: Advanced Backends

Goal: add native viewport drawing only after Qt overlay is stable.

### Tasks

- Viewport 2.0 draw backend for labels/guides.
- Custom context/dragger helpers.
- Marking-menu export.
- Visual regression workflow.

## Current Priority

Only Phase 0 is in scope for the first implementation agent.
