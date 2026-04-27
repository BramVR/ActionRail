---
summary: Compact architecture for the ActionRail MVP and the boundaries between Qt overlay, Maya actions, presets, and later Viewport 2.0.
read_when:
  - Implementing or reviewing ActionRail code structure.
  - Deciding where a feature belongs.
  - Avoiding premature Viewport 2.0 or designer work.
---

# Architecture

## MVP Shape

ActionRail is a PySide6-first Maya module.

```text
ActionRail/
  ActionRail.mod
  scripts/
    actionrail/
      __init__.py
      qt.py
      runtime.py
      overlay.py
      widgets.py
      actions.py
      state.py
      spec.py
      themes/
      examples/
  icons/
  presets/
  examples/
```

Use this layout unless implementation proves a smaller split is cleaner.

## Layers

### Bootstrap

- Locate Maya main window and active model panel.
- Create/recreate overlay safely.
- Expose `actionrail.reload()`, `actionrail.show_example()`, `actionrail.hide_all()`.

### Qt Overlay

- Transparent child widget over a Maya viewport/model panel.
- Empty space must pass through to Maya viewport interaction.
- Controls receive mouse input only inside their bounds.
- Reposition on resize, panel changes, workspace switches where possible.

### Widgets

MVP widgets:

- `ToolStack`
- `ToolButton`
- `ActionButton`
- `Spacer`

Widgets must have stable dimensions. Hover/active/disabled states must not shift layout.

### Actions

Actions are reusable named commands.

MVP action ids:

- `maya.tool.move`
- `maya.tool.translate`
- `maya.tool.rotate`
- `maya.tool.scale`
- `maya.anim.set_key`

Use `maya.cmds`. No PyMEL by default.

### State

MVP state:

- current Maya tool/context
- selection count
- active model panel where practical

Use polling if callbacks are too risky for Phase 0. Callback lifecycle must be centralized before adding many observers.

### Spec

Phase 0 can hard-code the reference stack.

Phase 1 should add JSON/Python declarative specs:

```json
{
  "id": "transform_stack",
  "anchor": "viewport.left.center",
  "items": [
    {"type": "toolButton", "label": "M", "action": "maya.tool.move"},
    {"type": "toolButton", "label": "T", "action": "maya.tool.translate"},
    {"type": "toolButton", "label": "R", "action": "maya.tool.rotate"},
    {"type": "toolButton", "label": "S", "action": "maya.tool.scale", "tone": "pink"},
    {"type": "spacer", "size": 14},
    {"type": "button", "label": "K", "action": "maya.anim.set_key", "tone": "teal"}
  ]
}
```

## Non-MVP

Do not implement these in Phase 0:

- Quick Create designer.
- Full preset browser.
- Icon import pipeline.
- Viewport 2.0 drawing backend.
- QML/WebEngine runtime.
- Marking-menu export.

## Main Risks

- Overlay steals viewport navigation.
- Reload leaves duplicate widgets or callbacks.
- Maya/PySide object ownership destroys widgets.
- Model panel lookup differs between Maya versions.
- High DPI changes reference sizing.

Design every Phase 0 change around these risks.
