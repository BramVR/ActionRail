---
summary: Roadmap for WoW-style ActionRail customization: frames, Action Book, Macro Book, Edit Mode, action slots, hover-to-bind hotkeys, flyouts, command rings, and profiles.
read_when:
  - Planning ActionRail user authoring workflows.
  - Designing preset schema changes beyond the transform stack.
  - Adding hotkeys, edit mode, collapsible rails, flyouts, radial menus, or profile layers.
---

# WoW-Style Customization Roadmap

## Goal

ActionRail should eventually feel like a user-editable WoW-style frame and
action-bar system for Maya:

1. Create or show a viewport frame, usually an action bar frame.
2. Open the Action Book and place Maya tools, commands, shelf actions, or
   macros onto slots.
3. Enter Edit Mode to move, scale, lock, and configure frames.
4. Collapse infrequent action bar frames into side tabs and reveal them with a
   small arrow/handle.
5. Enter Bind Mode, hover or click a slot, and press a shortcut.
6. Use compact bars for frequent actions and flyouts/rings for larger tool
   families.
7. Save layouts as user, project, or studio profiles.

The useful reference is the workflow model from World of Warcraft UI customization, not its fantasy visual style. ActionRail should still look like a polished Maya viewport tool.

The current `M/T/R/S/K` transform stack is only a seed example and regression
target. It should stay easy to recreate, but the authoring model must support
arbitrary user-defined frames, action bars, slots, hotkey badges, layouts,
action-library entries, macros, and command groups.

## Research Signals

WoW's Dragonflight Edit Mode made the base HUD movable, configurable, saveable, copyable, shareable, and specialization-aware. The ActionRail equivalent is named layouts that can change by Maya context: modeling, rigging, animation, shot, asset, or project.

Bartender4 and Dominos validate the action-bar model: multiple configurable bars, rows/columns, scale, alpha, fade behavior, visibility rules, paging/state changes, profiles, and easy hotkey binding.

WoW's own UI also validates non-bar frames. Edit Mode covers action bars, unit
frames, cast bars, buffs/debuffs, minimap, tooltip placement, and extra/encounter
bars. ActionRail should use **Frame** as the general top-level word and treat
rails/action bars as one frame type, not the whole product.

OPie validates radial command access: a key or mouse binding can show a ring of actions while held, reducing persistent screen clutter.

Mage teleport/portal addons validate smart flyouts: one compact affordance can open a contextual list that auto-populates from known commands, learned tools, selection, plugin availability, or project configuration.

WeakAuras validates trigger-driven UI, but ActionRail should use safe declarative predicates first rather than arbitrary user code as the default authoring surface.

## Product Concepts

### Frame System

Frames are ActionRail-owned UI objects in or around the Maya viewport. The
current rail is an action bar frame. Future frame types can include:

- action bar frames with slots
- collapsible edge-tab frames
- pinned or hover-revealed info frames
- HUD tooltip frames
- selection or object-linked frames
- deformer-stack frames for selected scene objects
- macro palettes

Every frame should have a stable id, type, layout/anchor, source layer, lock
state, visibility rules, and saved settings. Frame type owns the content and
interactions.

### Action Book

The Action Book uses WoW's ability-book workflow as a reference. It is a searchable
catalog of placeable actions, not a bar by itself.

Initial provider groups:

- transform and selection tools
- grid, snapping, display, and viewport toggles
- camera, playback, timeline, and keying commands
- Maya shelf buttons imported as actions
- studio/project tool commands
- user macros from the Macro Book

Action entries should have stable ids, labels, categories, icons, tooltips,
execution payloads, and optional predicates. Slots reference action ids and can
override display fields without changing the underlying action.

### Macro Book

The Macro Book is the WoW-macro-like authoring surface for custom Maya actions.
A macro should capture:

- stable id and display name
- icon id
- tooltip/help text
- Python or MEL body
- optional safe predicates for visible/enabled/active state
- optional shelf import/source metadata

Macros should become Action Book entries so the slot assignment workflow stays
the same for built-in Maya actions and user-authored script actions.

### Edit Mode

Edit Mode is a global authoring state for frame layout. Normal Mode executes
tools and owns slot payload editing when an action bar frame is explicitly unlocked,
including context-menu assignment/clear and Shift-drag move/swap/clear-out.
When the bar is unlocked, populated slot clicks are edit gestures; locking the
bar returns those clicks to normal action execution.

Edit Mode should show:

- a layout-map view where each frame is shown as a labeled dark rectangle
  over the viewport
- frame outlines and hit boxes
- direct frame dragging
- optional grid overlay for precise placement
- optional snap-to-grid while dragging frames
- optional sticky-frame snapping so dragged frames can align to nearby frames
- snap guides
- spacing guides
- safe margins
- scale and opacity controls for compatible frame types
- collapse side, handle, reveal trigger, and default expanded/collapsed state
- lock/unlock state
- broken action and missing icon badges for action bar frames

Required commands:

- `actionrail.edit_mode.toggle`
- `actionrail.edit_mode.enter`
- `actionrail.edit_mode.exit`

Edit Mode grid behavior should be user-controlled. Users can show or hide the
grid overlay independently from enabling snap-to-grid, and snapping should only
affect authoring gestures such as dragging or nudging rails. Normal mode should
not show the grid or alter viewport interaction.

Frame-level Edit Mode interaction should stay direct:

- left-click a frame to select it and open a compact position popover with
  arrow nudge controls, numeric X/Y coordinates, and Reset
- `Sticky Frames` makes dragged frames snap to other frames for quick alignment
- `Grid Size` controls the visible edit-only grid spacing used for precise
  placement

The visual treatment should make placement obvious at a glance: frames
should render as dark blocks with thin high-contrast outlines and compact
centered names, even when their normal buttons are not the focus. This is an
edit-only overview of layout footprints and hit boxes, not the Normal Mode look.

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

Slots also own interaction state. A slot can be active, disabled, hidden, warning/error badged, or later locked depending on declarative predicates and diagnostics. The theme owns how those states look; the preset owns when they apply.

Examples:

```json
{
  "id": "scale_tool",
  "type": "button",
  "label": "S",
  "action": "maya.tool.scale",
  "active_when": "maya.tool == scale"
}
```

This is a persistent stateful tool slot. It receives the generic active visual whenever Maya's current tool is scale.

```json
{
  "id": "set_key",
  "type": "button",
  "label": "KS",
  "action": "maya.anim.set_key"
}
```

This is a one-shot macro slot. It stays clickable but has no persistent active state unless the user deliberately adds one.

### Theme And Bar Appearance

ElvUI is useful here as a structure reference, not as a feature-count target.
Its action bars separate global media/color defaults from per-bar settings such
as backdrop, mouseover/fade behavior, button count, buttons per row, spacing,
button size, and backdrop spacing. ActionRail should keep that separation:

- global theme tokens own the default text, accent, panel, slot, border, and
  stripe treatment
- each action bar frame may override only the appearance values it needs
- Edit Mode owns frame placement and movement
- Normal Mode unlock/lock owns slot payload editing
- Quick Create should expose appearance as grouped options, not as hundreds of
  independent controls

The current first-pass control set is intentionally compact: Theme,
Backdrop Settings, Border Settings, and Slot Colors. Add secondary color,
font/media choices, profile-level themes, or copied/shared theme presets only
when the Phase 2 authoring loop proves that users need them.

### Bind Mode

Bind Mode mirrors action-bar addon workflows:

1. User enters Bind Mode.
2. User hovers or clicks an ActionRail slot.
3. User presses a shortcut.
4. ActionRail detects conflicts.
5. ActionRail creates or updates the slot's Maya runtime command and hotkey.
6. The key label appears on the slot.

Required commands:

- `actionrail.bind_mode.toggle`
- `actionrail.bind_mode.clear_hovered`
- `actionrail.hotkeys.validate`

Maya integration should prefer runtime commands so bindings remain visible in
Maya's Hotkey Editor. This publishing is infrastructure; artists should see the
WoW-like action of binding a visible slot, not a runtime-command management task.

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

Completed Phase 1 specs describe reusable action bar frames with stable slots, layout
metadata, predicates, icons, hotkey labels, and diagnostics. The next schema
work should move toward user-authored frames, slots, action-library references,
macro references, and interaction modes.

Draft shape:

```json
{
  "id": "animator_main",
  "type": "action_bar",
  "layout": {
    "orientation": "horizontal",
    "columns": 8,
    "anchor": "viewport.bottom.center",
    "offset": [0, -36],
    "scale": 1.0,
    "opacity": 1.0,
    "locked": false
  },
  "edit_mode": {
    "show_grid": false,
    "snap_to_grid": false,
    "sticky_frames": false,
    "grid_size": 12
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

Future non-bar frame draft:

```json
{
  "id": "selection_info",
  "type": "info_frame",
  "layout": {
    "anchor": "viewport.top.right",
    "offset": [-24, 24],
    "locked": false
  },
  "content": {
    "provider": "maya.selection.summary"
  },
  "interaction": {
    "hover": "show_tooltip",
    "click": "pin"
  }
}
```

## Roadmap

### Phase 1A - Declarative Rails

Extend the current stack spec into a rail spec:

Status: complete for the declarative MVP.

- stable slot ids
- rail layout metadata
- rows/columns/orientation
- scale/opacity/locked fields
- key label field
- visibility/enabled/active predicates as strings parsed by a small safe evaluator
- generic theme rendering for active state; demo presets must not rely on a hard-coded pink tone to signal active

Exit criteria: the current transform stack still loads, and a horizontal rail can be defined without changing widget code.

### Phase 1B - Runtime Commands And Hotkey Bridge

Add Maya-native command publishing:

Status: complete for the declarative MVP.

- create runtime commands for ActionRail actions
- create runtime commands for each published slot
- validate hotkey conflicts before assignment
- show assigned key text on buttons

Exit criteria: a preset action can be triggered from a Maya hotkey without the overlay being visible.

### Phase 2 - Edit Mode And Quick Create

Build the user-facing authoring workflow in medium slices:

1. Authoring model and user preset storage: complete for the first foundation
   slice through `DraftRail`, `DraftSlot`, safe user-preset writes, schema
   validation, and non-blocking diagnostics for broken user presets.
2. Dockable Quick Create panel: complete for the first Maya-facing authoring
   slice through a workspace-control entry point, vertical/horizontal/edge-tab
   starter templates, action picker, labels, icons, and basic layout values.
3. Preview and save workflow: complete for the first Quick Create workflow
   slice through preview without saving, cleanup preview overlays, stable user
   preset ids and slot ids, explicit overwrite, load existing, and reload
   through the normal runtime path.
4. Edit Mode shell and rail selection: global toggle, layout-map frame view,
   rail outlines, hit boxes, selected-rail inspector, source-layer badges,
   lock-state display, and optional grid overlay visibility for placement
   preview. Status: first shell implemented and Maya-smoke verified.
5. Layout editing and direct manipulation: direct frame dragging, safe
   margins, left-click position popover with X/Y and Reset, optional
   snap-to-grid, optional sticky-frame snapping to nearby rails, snap/spacing
   guides, and persisted layout edits. Status: user-preset layout saves are
   implemented for unlocked runtime/user rails, and user-override layout saves
   are implemented for unlocked built-in/studio rails. Slot payload edits have
   moved to Normal Mode rail lock/unlock helpers.
   Future button-style controls should let users independently show/hide,
   offset, and colorize the slot label and hotkey/key-label overlay.
6. Collapsible edge tabs and authoring-workflow polish: edge handles, reveal
   behavior, collapsed-state persistence, validation for missing
   actions/icons/hotkeys, optional shelf/runtime-command publishing where
   useful, and clearer handoff between Quick Create, Edit Mode, Normal Mode
   slot editing, and future Bind Mode.

Research hints by slice:

- 2.1: WoW Edit Mode named layouts, Dominos/Bartender4 profiles, and ActionRail
  profile/layer notes.
- 2.2: Autodesk Maya workspace controls, WoW/Dominos configuration entry
  points, and compact action-bar settings UI.
- 2.3: Maya preview/apply/save patterns, WoW save/copy/share layout behavior,
  and ActionRail safe-start diagnostics.
- 2.4: WoW Edit Mode outlines and selected elements, Maya inspector/tool
  settings patterns, and ActionRail source-layer/lock constraints.
- 2.5: WoW/Dominos drag positioning, per-bar scale/opacity/spacing, optional
  grid snapping, sticky-frame alignment, Maya snap guides, and local
  `research/` reference images.
- 2.6: collapsible side panels, action-bar visibility/hotkey labels, and OPie
  only as a boundary reference for later Phase 3 command rings.
- 2.7: dense overlay performance foundation. Before later modes, make large
  WoW-style action-bar layouts fast over Maya by replacing per-rail polling with
  shared state, caching predicates, prototyping a custom-painted dense bar,
  repainting only dirty slots, and passing Maya navigation gestures through
  unless ActionRail intentionally captures them.

Exit criteria: an artist can recreate the transform stack, create a distinct
custom rail, collapse that rail to an edge tab from Maya UI without editing
JSON, and keep a dense 100+ slot layout visible while normal viewport
tumble/pan/zoom remains usable.

### Phase 3 - Action Book, Bind Mode, Macro Book, Flyouts, And Command Rings

Add high-leverage interaction patterns:

- searchable Action Book for Maya tools, commands, shelf actions, and macros
- hover-to-bind hotkeys
- slot conflict warnings
- Macro Book for user-authored Python/MEL actions with icons
- flyout button widget
- command ring widget
- press/release hotkey behavior for temporary UI

Exit criteria: a user can assign a Maya action from the Action Book to a slot,
bind that slot by hovering it, create a simple macro action with an icon, and
open a command ring from a hotkey.

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
- Keep runtime-command publishing as implementation plumbing for saved bindings
  and optional shelf integration; do not make it the primary authoring workflow.
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
