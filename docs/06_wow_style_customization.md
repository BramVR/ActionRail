---
summary: Roadmap for WoW-style ActionRail customization: Edit Mode, action slots, collapsible rails, hover-to-bind hotkeys, flyouts, command rings, and profiles.
read_when:
  - Planning ActionRail user authoring workflows.
  - Designing preset schema changes beyond the transform stack.
  - Adding hotkeys, edit mode, collapsible rails, flyouts, radial menus, or profile layers.
---

# WoW-Style Customization Roadmap

## Goal

ActionRail should eventually feel like a user-editable action bar system for Maya:

1. Enter Edit Mode.
2. Move, scale, lock, and configure viewport rails.
3. Collapse infrequent rails into side tabs and reveal them with a small arrow/handle.
4. Add scripts, tools, runtime commands, or presets to slots.
5. Bind keys by hovering a slot and pressing a shortcut.
6. Use compact bars for frequent actions and flyouts/rings for larger tool families.
7. Save layouts as user, project, or studio profiles.

The useful reference is the workflow model from World of Warcraft UI customization, not its fantasy visual style. ActionRail should still look like a polished Maya viewport tool.

The current `M/T/R/S/K` transform stack is only a seed example for this system. It should stay easy to recreate, but the authoring model must support arbitrary user-defined rails, slots, hotkey badges, layouts, and command groups.

## Research Signals

WoW's Dragonflight Edit Mode made the base HUD movable, configurable, saveable, copyable, shareable, and specialization-aware. The ActionRail equivalent is named layouts that can change by Maya context: modeling, rigging, animation, shot, asset, or project.

Bartender4 and Dominos validate the action-bar model: multiple configurable bars, rows/columns, scale, alpha, fade behavior, visibility rules, paging/state changes, profiles, and easy hotkey binding.

OPie validates radial command access: a key or mouse binding can show a ring of actions while held, reducing persistent screen clutter.

Mage teleport/portal addons validate smart flyouts: one compact affordance can open a contextual list that auto-populates from known commands, learned tools, selection, plugin availability, or project configuration.

WeakAuras validates trigger-driven UI, but ActionRail should use safe declarative predicates first rather than arbitrary user code as the default authoring surface.

## Product Concepts

### Edit Mode

Edit Mode is a global authoring state. Normal mode executes tools; Edit Mode edits the UI.

Edit Mode should show:

- rail outlines and hit boxes
- drag handles
- anchor pins
- snap guides
- spacing guides
- safe margins
- scale and opacity controls
- collapse side, handle, reveal trigger, and default expanded/collapsed state
- lock/unlock state
- broken action and missing icon badges

Required commands:

- `actionrail.edit_mode.toggle`
- `actionrail.edit_mode.enter`
- `actionrail.edit_mode.exit`

### Collapsible Rails

Collapsible rails let a bar fold against a viewport edge when it is not needed.
The collapsed state should leave a small visible tab, arrow, or handle so the
rail can be reopened without using a shelf/menu command.

Initial behavior:

- collapse to left, right, top, or bottom viewport edge
- show a small handle with a directional chevron
- reveal by click first; hover reveal can come later after Maya focus testing
- optionally auto-collapse when the cursor leaves the expanded rail
- keep hotkey/runtime-command bindings active while the rail is collapsed
- preserve the rail's configured anchor, offset, scale, opacity, and lock state

Edit Mode should expose collapse controls per rail, not as a global-only setting.

### Action Slots

Buttons should become slots that can contain an action payload. The payload can be:

- built-in ActionRail action id
- Maya runtime command
- Maya named command
- Python script
- MEL script
- shelf tool import
- preset reference
- flyout
- command ring

Slots need stable ids so hotkeys, user overrides, and profile migrations do not depend on label text or list order.

### Bind Mode

Bind Mode mirrors action-bar addon workflows:

1. User enters Bind Mode.
2. User hovers or clicks an ActionRail slot.
3. User presses a shortcut.
4. ActionRail detects conflicts.
5. ActionRail creates or updates a Maya runtime command and hotkey.
6. The key label appears on the slot.

Required commands:

- `actionrail.bind_mode.toggle`
- `actionrail.bind_mode.clear_hovered`
- `actionrail.hotkeys.validate`

Maya integration should prefer runtime commands so bindings remain visible in Maya's Hotkey Editor.

### Flyouts

Flyouts are compact expandable menus attached to a button. They are better than permanent bars when the actions are related but not constantly used.

Good first flyouts:

- transform tools
- keying tools
- selection tools
- display modes
- camera bookmarks
- rig controls
- project scripts

Flyouts can be click-to-open, hover-to-open, or press-and-hold. Press-and-hold behavior must be verified in Maya because keyboard focus and release handling can vary inside host applications.

### Command Rings

Command rings are radial menus inspired by OPie and Maya marking menus.

Use command rings for:

- larger command groups
- low-clutter hotkey workflows
- pen/tablet workflows
- spatial muscle-memory actions

Initial behavior:

- press hotkey to show ring
- move cursor toward a wedge
- release to execute
- escape/right click cancels
- center click can pin the ring open for inspection

Command rings should share the same action registry as bars and flyouts.

### Profiles And Preset Layers

ActionRail needs explicit layers so studio defaults and user changes do not silently overwrite each other:

1. built-in examples
2. studio locked presets
3. project presets
4. asset or scene presets
5. user overrides

Every editable object should expose its layer and lock state in Edit Mode.

### Visibility Rules

Visibility should be declarative before it becomes scriptable:

- selected object type
- selection count
- current Maya tool/context
- active panel/camera
- playback state
- animation layer/keying state
- plugin or command availability
- project/shot context

Example:

```json
{
  "visible_when": "selection.count > 0",
  "enabled_when": "action.exists",
  "active_when": "current_tool == 'moveSuperContext'"
}
```

## Schema Direction

Current Phase 1 specs describe a simple stack. The next schema should describe rails, slots, and interaction modes.

Draft shape:

```json
{
  "id": "animator_main",
  "type": "rail",
  "layout": {
    "orientation": "horizontal",
    "columns": 8,
    "anchor": "viewport.bottom.center",
    "offset": [0, -36],
    "scale": 1.0,
    "opacity": 1.0,
    "locked": false
  },
  "collapse": {
    "enabled": true,
    "mode": "edge_tab",
    "default_state": "expanded",
    "edge": "left",
    "trigger": "click",
    "auto_collapse": false,
    "handle_icon": "chevron-right"
  },
  "profile": {
    "layer": "user",
    "context": "animation"
  },
  "slots": [
    {
      "id": "set_key",
      "type": "button",
      "label": "K",
      "icon": "key",
      "action": "maya.anim.set_key",
      "hotkey": "S"
    },
    {
      "id": "keying_flyout",
      "type": "flyout",
      "label": "Key",
      "items": [
        {"id": "set_key_all", "action": "maya.anim.set_key"},
        {"id": "delete_key", "action": "maya.anim.delete_key"}
      ]
    }
  ]
}
```

## Roadmap

### Phase 1A - Declarative Rails

Extend the current stack spec into a rail spec:

- stable slot ids
- rail layout metadata
- rows/columns/orientation
- scale/opacity/locked fields
- key label field
- visibility/enabled/active predicates as strings parsed by a small safe evaluator

Exit criteria: the current transform stack still loads, and a horizontal rail can be defined without changing widget code.

### Phase 1B - Runtime Commands And Hotkey Bridge

Add Maya-native command publishing:

- create runtime commands for ActionRail actions
- create runtime commands for each published slot
- validate hotkey conflicts before assignment
- show assigned key text on buttons

Exit criteria: a preset action can be triggered from a Maya hotkey without the overlay being visible.

### Phase 2 - Edit Mode And Quick Create

Build the user-facing authoring workflow:

- global Edit Mode toggle
- drag rail position
- change scale, opacity, orientation, rows, columns, spacing
- configure collapsible edge-tab behavior, including edge, handle, reveal trigger, and default state
- add/remove/reorder slots
- action browser
- save as user preset
- validate missing actions/icons/hotkeys

Exit criteria: an artist can recreate the transform stack, create a distinct custom rail, and collapse that rail to an edge tab from Maya UI without editing JSON.

### Phase 3 - Bind Mode, Flyouts, And Command Rings

Add high-leverage interaction patterns:

- hover-to-bind hotkeys
- slot conflict warnings
- flyout button widget
- command ring widget
- press/release hotkey behavior for temporary UI

Exit criteria: a user can bind a slot by hovering it, and can open a command ring from a hotkey.

### Phase 4 - Studio Profiles And Sharing

Add production-scale sharing:

- user/project/studio layers
- locked presets
- profile copy/import/export
- migration for renamed action ids
- diagnostics for missing plugins/scripts

Exit criteria: a studio preset can be installed read-only, extended by a user preset, and inspected in Edit Mode.

## Guardrails

- Keep the Qt overlay as the primary clickable UI backend.
- Do not build command rings on Viewport 2.0 first; Qt hit testing is the right first path.
- Do not make arbitrary Python snippets the default authoring path for artists.
- Keep runtime commands and hotkeys optional until the user publishes a preset or binding.
- Collapsed handles must stay small and must not create viewport-sized transparent hit areas.
- Always offer safe mode: users must be able to disable all ActionRail overlays if a bad preset causes trouble.
- Do not let Edit Mode changes silently modify studio-locked presets; write user overrides instead.

## Sources

- Blizzard HUD/UI revamp and Edit Mode: https://news.blizzard.com/en-us/article/23841481/hud
- Bartender4 action bar addon: https://www.curseforge.com/wow/addons/bartender4
- Dominos action bar addon: https://www.curseforge.com/wow/addons/dominos
- OPie radial action-binding addon: https://www.curseforge.com/wow/addons/opie
- Mage Teleporter flyout/dropdown pattern: https://www.curseforge.com/wow/addons/mage-teleporter
- Maya runtime commands: https://help.autodesk.com/cloudhelp/2022/ENU/Maya-KeyboardShortcuts/files/GUID-2B2BE446-D622-4274-80FC-2A5EF7D87C5C.htm
- Maya hotkeys: https://help.autodesk.com/cloudhelp/2026/ENU/Maya-Tech-Docs/CommandsPython/hotkey.html
