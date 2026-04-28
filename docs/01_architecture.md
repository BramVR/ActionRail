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
See `docs/05_tech_stack.md` for the current stack decision and deferred alternatives.

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

### Customization UX

Long-term ActionRail authoring should follow the WoW-style customization roadmap in `docs/06_wow_style_customization.md`.

Conceptual states:

- **Normal Mode**: rails execute actions; empty overlay space passes through to Maya.
- **Edit Mode**: rails show outlines, anchors, handles, snap guides, safe margins, and per-rail settings.
- **Bind Mode**: user hovers or selects a slot, presses a shortcut, and ActionRail publishes/updates a Maya runtime command and hotkey.

The customization layer is planned after the declarative MVP, but the spec and action registry should be designed so stable slot ids, key labels, flyouts, command rings, and preset layers can be added without replacing the core model.

### Bootstrap

- Locate Maya main window and active model panel.
- Create/recreate overlay safely.
- Expose `actionrail.reload()`, `actionrail.show_example()`, `actionrail.hide_all()`.
- Probe Maya 2026 `moverlay` as a possible helper/reference, but keep the MVP overlay host custom until the probe proves fit.

### Qt Overlay

- Transparent child widget over a Maya viewport/model panel.
- Empty space must pass through to Maya viewport interaction.
- Controls receive mouse input only inside their bounds.
- Reposition on resize, panel changes, workspace switches where possible.
- Use `QApplication.instance()` and parent widgets under Maya-owned Qt widgets.

### Widgets

MVP widgets:

- `ToolStack`
- `ToolButton`
- `ActionButton`
- `Spacer`

Widgets must have stable dimensions. Hover/active/disabled states must not shift layout.

Planned widgets after the reusable rail schema:

- `Rail`: configurable bar with rows, columns, orientation, scale, opacity, and lock state.
- `Slot`: stable action container that can hold a button, tool button, flyout, command ring, or preset reference.
- `Flyout`: compact expandable menu for related actions.
- `CommandRing`: radial menu for press/hold/release command access.
- `KeyBadge`: hotkey text drawn on a slot after binding.

### Actions

Actions are reusable named commands.

MVP action ids:

- `maya.tool.move`
- `maya.tool.translate`
- `maya.tool.rotate`
- `maya.tool.scale`
- `maya.anim.set_key`

Use `maya.cmds`. No PyMEL by default.

Future actions should be publishable as Maya runtime commands so users can bind ActionRail actions through Maya's Hotkey Editor or through ActionRail Bind Mode.

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

After Phase 1, specs should evolve from stack-only data to rail/slot data:

```json
{
  "id": "animator_main",
  "type": "rail",
  "layout": {
    "orientation": "horizontal",
    "anchor": "viewport.bottom.center",
    "columns": 8,
    "scale": 1.0,
    "locked": false
  },
  "slots": [
    {
      "id": "set_key",
      "type": "button",
      "label": "K",
      "action": "maya.anim.set_key",
      "hotkey": "S"
    }
  ]
}
```

Stable ids are required for hotkey bindings, preset migration, and user overrides.

## Non-MVP

Do not implement these in Phase 0:

- Quick Create designer.
- Edit Mode and Bind Mode.
- Full preset browser.
- Icon import pipeline.
- Flyouts and command rings.
- Viewport 2.0 drawing backend.
- QML/WebEngine runtime.
- React/Electron or network-backed web UI.
- Marking-menu export.

## Main Risks

- Overlay steals viewport navigation.
- Reload leaves duplicate widgets or callbacks.
- Maya/PySide object ownership destroys widgets.
- Model panel lookup differs between Maya versions.
- High DPI changes reference sizing.

Design every Phase 0 change around these risks.
