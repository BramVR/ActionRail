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
      hotkeys.py
      state.py
      spec.py
      authoring.py
      theme.py
  icons/
  presets/
  examples/
```

Use this layout unless implementation proves a smaller split is cleaner.

## Layers

### Customization UX

Long-term ActionRail authoring should follow the WoW-style customization roadmap in `docs/06_wow_style_customization.md`.

Conceptual states:

- **Normal Mode**: rails execute actions; the overlay host avoids viewport-sized
  transparent hit areas so normal Maya viewport interaction remains available
  outside visible controls.
- **Edit Mode**: rails show outlines, anchors, handles, snap guides, safe margins, and per-rail settings.
- **Bind Mode**: user hovers or selects a slot, presses a shortcut, and ActionRail publishes/updates a Maya runtime command and hotkey.

The customization layer is planned after the declarative MVP, but the spec and action registry should be designed so stable slot ids, key labels, flyouts, command rings, and preset layers can be added without replacing the core model.

### Bootstrap

- Locate Maya main window and active model panel.
- Create/recreate overlay safely.
- Expose `actionrail.reload()`, `actionrail.show_example()`,
  `actionrail.show_spec()`, `actionrail.hide_all()`, `actionrail.run_action()`,
  and `actionrail.run_slot()`.
- Probe Maya 2026 `moverlay` as a possible helper/reference, but keep the MVP overlay host custom until the probe proves fit.

### Qt Overlay

- Resolve the active model panel and its inner viewport-area widget for anchor
  geometry.
- Show visible rails as small frameless Maya-owned tool windows positioned from
  that viewport geometry. Avoid parenting the rail directly under the OpenGL
  viewport widget or a viewport-sized transparent container because Maya can
  briefly repaint those child widgets at local origin during model-panel toolbar
  refreshes.
- Do not create empty viewport-sized overlay space; normal Maya viewport
  interaction should remain available outside the visible controls.
- Controls receive mouse input only inside their bounds.
- Reposition on resize, panel changes, workspace switches where possible.
- Use `QApplication.instance()` and parent visible rail windows under Maya's main
  Qt window to keep object ownership stable.

### Widgets

MVP widgets:

- `ToolStack`
- `ToolButton`
- `ActionButton`
- `Spacer`

Widgets must have stable dimensions. Hover/active/disabled states must not shift layout.

State belongs to slots, not to a specific built-in button. A user-authored slot may be a persistent tool, a one-shot macro, a disabled-until-valid command, a locked studio control, a flyout, or a command ring. Presets declare state predicates such as `active_when`, `enabled_when`, and `visible_when`; themes decide how those states render. For example, a scale slot can declare `active_when: "maya.tool == scale"`, while a Set Key macro has no `active_when` because clicking it performs one immediate action.

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

ActionRail actions and action-bearing preset slots can be published as Maya runtime commands through `actionrail.hotkeys` so users can bind them through Maya's Hotkey Editor or through future ActionRail Bind Mode.

### State

MVP state:

- current Maya tool/context
- selection count
- active model panel where practical

Use polling if callbacks are too risky for Phase 0. Callback lifecycle must be centralized before adding many observers.

### Spec

Phase 0 started with a hard-coded reference stack. Phase 1 now loads built-in examples from JSON presets in `presets/`. The transform stack remains a regression target and demonstration preset; it should not be treated as the only rail shape ActionRail is designed to support.

```json
{
  "id": "transform_stack",
  "layout": {
    "anchor": "viewport.left.center",
    "orientation": "vertical",
    "rows": 5,
    "columns": 1,
    "offset": [0, 0],
    "scale": 1.0,
    "opacity": 1.0,
    "locked": true
  },
  "items": [
    {"type": "toolButton", "id": "transform_stack.move", "label": "M", "action": "maya.tool.move", "active_when": "maya.tool == move"},
    {"type": "toolButton", "id": "transform_stack.translate", "label": "T", "tooltip": "Unassigned slot"},
    {"type": "toolButton", "id": "transform_stack.rotate", "label": "R", "action": "maya.tool.rotate", "active_when": "maya.tool == rotate"},
    {"type": "toolButton", "id": "transform_stack.scale", "label": "S", "action": "maya.tool.scale", "active_when": "maya.tool == scale"},
    {"type": "spacer", "id": "transform_stack.gap", "size": 14},
    {"type": "button", "id": "transform_stack.set_key", "label": "K", "action": "maya.anim.set_key", "tone": "teal", "key_label": "S"}
  ]
}
```

The schema is still named `StackSpec` in code for compatibility, but current presets already carry rail-ready layout metadata, stable slot ids, key labels, and predicate fields. The Python `StackItem(...)` API keeps the original positional constructor order through `tone`; newer optional fields such as `icon` should be passed by keyword or appended after the legacy fields. `tone` is optional visual decoration, not the active-state system. Active rendering comes from the generic `actionRailActive="true"` property after a slot's `active_when` predicate evaluates true. Slots with no `action` are intentional placeholders: they render disabled/locked, do not publish as action-bearing slots, and are not clickable. Python callers can build `StackSpec` objects directly or parse JSON-like dictionaries with `actionrail.parse_stack_spec()`, then render them with `actionrail.show_spec()`.

Phase 2 step 2.1 adds `actionrail.authoring` as the first authoring layer. It defines `DraftRail` and `DraftSlot` for Quick Create drafts, converts them into validated `StackSpec` payloads, and saves user presets outside locked bundled presets through `save_user_preset()` / `load_user_preset()`. This is a local user-preset layer only; project/studio/profile layering is still reserved for a later phase.

Later phases should evolve the public naming toward user-authored rail/slot data:

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
    },
    {
      "id": "scale_tool",
      "type": "button",
      "label": "S",
      "action": "maya.tool.scale",
      "hotkey": "R",
      "active_when": "maya.tool == scale"
    }
  ]
}
```

Stable ids are required for hotkey bindings, preset migration, user overrides, and UI authoring tools that create rails instead of hand-editing JSON.

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
