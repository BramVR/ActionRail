---
summary: Compact architecture for ActionRail's WoW-style Maya viewport frame system, action bars, Action Book, presets, and later Viewport 2.0.
read_when:
  - Implementing or reviewing ActionRail code structure.
  - Deciding where a feature belongs.
  - Avoiding premature Viewport 2.0 or designer work.
---

# Architecture

## Product Model

ActionRail is a WoW-style viewport UI framework for Maya. The reference
`M/T/R/S/K` stack is a regression preset, not the product center. The durable
product model is:

- **Frames**: movable/configurable viewport UI objects. Current rails/action
  bars are the implemented frame type. Later frame types can include pinned
  info boxes, HUD tooltip panels, selection frames, object-linked frames, and
  deformer-stack frames.
- **Action Bar Frames**: frames with slots arranged as rows, columns, strips,
  stacks, or collapsible edge tabs.
- **Slots**: stable containers on an action bar. A slot references an action,
  macro, flyout, command ring, preset, or empty placeholder, and owns display
  overrides such as icon, label, key label, tooltip, and tone.
- **Appearance**: global theme tokens provide the default ActionRail look, while
  each action bar frame can carry sparse appearance overrides for its main
  accent, text, backdrop, border, and slot colors.
- **Action Book**: searchable catalog of Maya-native tools and commands that
  can be placed onto slots. The current action registry and icon catalog are
  now connected through the first `actionrail.action_book` backend slice; the
  authoring UI should evolve toward a WoW-style browser for Maya actions
  such as transform tools, grid/display toggles, selection modes, playback,
  keying, viewport controls, and studio commands.
- **Macro Book**: user-authored script actions. A macro should have a stable
  id, name, icon, tooltip, Python or MEL body, and optional safe predicates, then
  appear in the Action Book like any other placeable action.
- **Bindings**: slot hotkeys backed by Maya runtime commands. Publishing those
  runtime commands is the implementation mechanism; the user-facing workflow is
  Bind Mode: hover/click a slot, press a shortcut, resolve conflicts, and see
  the key label on the slot. The current public bridge exposes
  `SlotBindingTarget` records through `actionrail.slot_binding_targets()` so a
  saved bar can list the exact slot ids, current key labels, runtime commands,
  and Maya nameCommands before full Bind Mode exists.

This vocabulary keeps the current rail implementation useful while leaving the
schema open for WoW-like non-bar frames and later Maya-specific HUD widgets.
Avoid introducing new top-level concepts that only work for buttons.

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
      slot_state.py
      actions.py
      hotkeys.py
      state.py
      spec.py
      authoring.py
      preset_store.py
      quick_create.py
      quick_create_ui.py
      edit_mode.py
      diagnostics.py
      diagnostics_ui.py
      icon_catalog.py
      icon_manifest.py
      icon_import.py
      icon_fallbacks.py
      icon_svg.py
      icon_types.py
      icon_paths.py
      theme.py
  icons/
  presets/
  examples/
```

Use the machine-readable project map for exact ownership and tests:

```powershell
$env:PYTHONPATH = "scripts"
.\.venv\Scripts\python.exe -m actionrail --json
```

## Layers

### Customization UX

Long-term ActionRail authoring should follow the WoW-style customization roadmap in `docs/06_wow_style_customization.md`.

Conceptual states:

- **Normal Mode**: frames execute their normal interactions. Action bar frames
  execute slot actions; active rails can be explicitly
  unlocked for slot payload assignment/clear plus Shift-drag move/swap/clear-out
  and locked again for normal action execution. While unlocked, populated slot
  clicks are edit gestures rather than action execution. The overlay host avoids
  viewport-sized transparent hit areas so normal Maya viewport interaction
  remains available outside visible controls.
- **Edit Mode**: frames switch into a layout-map view with labeled dark frame
  rectangles, outlines, optional placement grid overlay,
  optional snap-to-grid, snap guides, and safe margins. Edit Mode is for frame
  layout/configuration, not slot payload editing or macro authoring.
- **Bind Mode**: user hovers or selects a slot, presses a shortcut, and
  ActionRail publishes/updates the slot's Maya runtime command and hotkey.
  The first keyboard-capture slice is implemented for visible action slots:
  enter Bind Mode, hover a slot, press a key, clear the hovered slot with
  Escape, and save or discard touched chords.
- **Action Book**: user browses available Maya actions and assigns them to
  slots.
- **Macro Book**: user creates custom script actions with icons, then places
  them onto slots through the same Action Book workflow.

The first Edit Mode shell is implemented in `actionrail.edit_mode`: it discovers
active runtime rails, draws their edit footprints over a grid, supports
left-click selection, Grid Size, Snap to Grid, Sticky Frames, lock/source
labels, and non-persistent X/Y nudging for unlocked rails. See
`docs/08_edit_mode.md` for current user behavior and limits.

The remaining customization layers build on the declarative MVP, but the spec
and action registry should continue to preserve stable frame ids, slot ids, key
labels, flyouts, command rings, action-library entries, macro entries, and
preset layers without replacing the core model.

### Bootstrap

- Locate Maya main window and active model panel.
- Create/recreate overlay safely.
- Expose `actionrail.reload()`, `actionrail.show_example()`,
  `actionrail.show_preset()`, `actionrail.show_spec()`,
  `actionrail.hide_all()`, `actionrail.run_action()`, and
  `actionrail.run_slot()`.
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

Current widgets:

- `ToolStack`
- `ToolButton`
- `ActionButton`
- `Spacer`

Widgets must have stable dimensions. Hover/active/disabled states must not shift layout.

State belongs to slots, not to a specific built-in button. A user-authored slot may be a persistent tool, a one-shot macro, a disabled-until-valid command, a locked studio control, a flyout, or a command ring. Presets declare state predicates such as `active_when`, `enabled_when`, and `visible_when`; themes decide how those states render. `actionrail.slot_state` resolves those predicates, icons, action availability, diagnostics, and tooltip fallbacks without importing Qt, while `widgets.py` applies the resolved state to Qt controls. For example, a scale slot can declare `active_when: "maya.tool == scale"`, while a Set Key macro has no `active_when` because clicking it performs one immediate action.

Planned widgets after the reusable frame/action-bar schema:

- `Frame`: base movable/configurable viewport UI object with id, type, anchor,
  lock state, source layer, and saved layout values.
- `ActionBarFrame` / `Rail`: configurable bar with rows, columns, orientation,
  scale, opacity, collapse settings, and lock state.
- `Slot`: stable action container that can hold a button, tool button, flyout, command ring, or preset reference.
- `InfoFrame`: pinned or hover-revealed contextual information panel.
- `ObjectFrame`: selection/object-linked frame for future scene-aware UI such
  as deformer stack summaries or rig controls.
- `Flyout`: compact expandable menu for related actions.
- `CommandRing`: radial menu for press/hold/release command access.
- `KeyBadge`: hotkey text drawn on a slot after binding.

### Theme And Appearance

ActionRail follows the useful part of the ElvUI structure in `research/`: global
media/theme defaults define the product look, while each action bar stores only
the overrides it needs. Keep these concerns separate:

- layout and movement live on `RailLayout` / Edit Mode save paths
- slot payloads live on slots and Normal Mode unlock/lock editing
- render defaults live in `actionrail.theme`
- per-bar visual overrides live in `RailAppearance` / JSON `appearance`

The current appearance schema intentionally stays smaller than ElvUI's full
option surface. It covers the controls artists need first: theme id, inherit
global defaults, main accent, text/muted text, backdrop on/off, backdrop color,
pattern/color/opacity/scale, border on/off/color/width, and slot colors for
empty sockets, icon tiles, and active state. Add broader profile/media systems
later; do not put profile layers, Bind Mode, or Action Book browsing into this
appearance object.

### Actions

Actions are reusable named commands that can be placed into slots.

MVP action ids:

- `maya.tool.move`
- `maya.tool.translate`
- `maya.tool.rotate`
- `maya.tool.scale`
- `maya.anim.set_key`

Use `maya.cmds`. No PyMEL by default.

ActionRail actions and action-bearing preset slots can be published as Maya
runtime commands through `actionrail.hotkeys` so users can bind them through
Maya's Hotkey Editor or through future ActionRail Bind Mode. For artist-facing
tooling, prefer `actionrail.slot_binding_targets()` over showing raw command
names first; it returns the slot label, action id, key label, runtime command,
and nameCommand as one workflow object.

The Action Book should not try to expose every Maya command at once. Start with
curated provider-backed groups that behave like a WoW ability browser:

- transform and selection tools
- grid, snapping, viewport display, and camera controls
- playback and timeline commands
- keying and animation commands
- imported Maya shelf buttons or studio tools
- user macros from the Macro Book

Each action entry should provide a stable id, label, category, icon id, tooltip,
execution function or command payload, and optional safe predicates. Slots
reference action ids and may override display fields locally.

The current implementation has a searchable Action Book panel backed by
`actionrail.action_book`. Its starter catalog is intentionally curated rather
than exhaustive: transform/key/viewport basics, selection utilities, and a
33-entry smoke-verified shelf-replacement set with 20 polygon modeling actions
using Maya shelf command/icon names.

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

The schema is still named `StackSpec` in code for compatibility, but current presets already carry action-bar-frame layout metadata, optional `collapse` settings, optional `appearance` overrides, stable slot ids, key labels, and predicate fields. The Python `StackItem(...)` API keeps the original positional constructor order through `tone`; newer optional fields such as `icon` should be passed by keyword or appended after the legacy fields. Collapse settings use `RailCollapse` / JSON `collapse` for edge, handle icon, reveal trigger, and default collapsed state; disabled collapse remains the default for legacy presets. Appearance settings use `RailAppearance` / JSON `appearance` and resolve through `apply_appearance_overrides()` before widgets paint the rail. `tone` is optional visual decoration, not the active-state system. Active rendering comes from the generic `actionRailActive="true"` property after a slot's `active_when` predicate evaluates true. Slots with no `action` are intentional placeholders: they render disabled/locked, do not publish as action-bearing slots, and are not clickable. Python callers can build `StackSpec` objects directly or parse JSON-like dictionaries with `actionrail.parse_stack_spec()`, then render them with `actionrail.show_spec()`.

Phase 2 step 2.1 adds `actionrail.authoring` as the first authoring layer. It defines `DraftRail` and `DraftSlot` for Quick Create drafts, converts them into validated `StackSpec` payloads, and saves user presets outside locked bundled presets through `save_user_preset()` / `load_user_preset()`. `actionrail.preset_store` is the shared resolver for bundled, optional studio, and saved user presets; runtime overlay startup, no-overlay slot execution, hotkey publishing/sync, diagnostics, Maya menu toggles, and the project map should resolve preset ids through it instead of directly assuming `presets/` built-ins. This remains a compact preset-layer slice; broader project/profile layering is still reserved for a later phase.

Phase 2 steps 2.2-2.3 add `actionrail.quick_create` and
`actionrail.quick_create_ui` as the first Maya-facing authoring surface. Quick
Create owns template defaults, picker-facing action/icon choices, editable draft
input, preview cleanup, load-existing conversion, and save/show helpers.
Preview uses `show_spec()` with a validated draft spec and tracks preview ids
for cleanup; save uses the same user-preset writer as other authoring code with
explicit overwrite required for existing files, then shows the saved preset
through the normal runtime resolver without closing unrelated overlays. Saved
user presets can be loaded back into editable Quick Create values; locked
built-in presets remain read-only.

Phase 2 step 2.4 adds `actionrail.edit_mode` as the first viewport-facing
authoring shell. It owns the public `EditModeSettings`, `EditModeState`, and
`RailFrameInfo` value objects; global enter/exit/toggle state; layout-map
painting; selected-rail state; grid/snap/sticky options; and session-local
position changes. It reads active overlay geometry from the runtime registry
and should not mutate locked built-in presets directly. Phase 2 step 2.5 now
persists unlocked runtime/user rail layout edits by saving the current spec to
the user preset store; unlocked built-in and studio rail edits save as
`*_user_override` sidecars in the user preset store and are applied when the
original read-only preset id is resolved.

Icon fields should store stable logical ids, not raw file paths. The icon
provider layer currently resolves manifest-backed ids such as
`actionrail.move` and curated Maya resource ids such as `maya.move`. This keeps
runtime rendering simple while giving Quick Create a picker-friendly
`IconDescriptor` model with provider, label, category, keywords, source, and
resolved Qt resource/file data.

The icon implementation is intentionally split by workflow. `actionrail.icons`
is the public compatibility facade; new internal code should prefer narrower
imports. `actionrail.icon_catalog` owns provider descriptors and read-only icon
lookup for picker/search UI. `actionrail.icon_manifest` owns manifest storage,
path normalization, and validation. `actionrail.icon_import` owns SVG import
preflight, manifest writes, target conflict checks, and rollback. `actionrail.icon_svg`
owns SVG parse/safety rules. `actionrail.icon_fallbacks` owns generated PNG
fallback checks and mayapy rendering. `actionrail.icon_types` and
`actionrail.icon_paths` hold shared value objects and storage paths. Quick
Create icon browsing should depend on `icon_catalog`, not import/write or
fallback-rendering modules.

Maya resource icons intentionally keep their raw resource names in descriptor
metadata and diagnostics, for example `move_M.png`, because that is what
`cmds.resourceManager(nameFilter=...)` validates. The Qt widget render path
adds the `:/` resource prefix only when constructing the `QIcon`, for example
`:/move_M.png`. ActionRail slot buttons paint icons as full-size inner-button
underlays and then draw the label, key label, or diagnostic badge over them.

Later phases should evolve the public naming toward user-authored frame data.
Current rails map to `type: "action_bar"`:

```json
{
  "id": "animator_main",
  "type": "action_bar",
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

Future non-bar frames should use the same id/layout/source-layer/persistence
rules but different `content` and `interaction` payloads:

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

Stable frame ids and slot ids are required for hotkey bindings, preset
migration, user overrides, and UI authoring tools that create ActionRail UI
without hand-editing JSON.

The intended artist workflow is:

1. Create or show an action bar frame from a template.
2. Open the Action Book and place Maya actions or macros onto slots.
3. Use Edit Mode to move/configure frames.
4. Use Bind Mode to hover/click slots and assign hotkeys.
5. Save the frame/layout as a user preset or user override.

The first Bind Mode slice supports keyboard chords only. Mouse button and wheel
binding should wait until Maya focus and native hotkey-editor compatibility are
verified.

Optional shelf toggles and runtime-command publishing remain useful plumbing,
but they should not be the primary concept shown to artists.

## Non-MVP

Do not implement these in the remaining Phase 2 layout-editing slice unless the
slice explicitly calls for them:

- Full preset browser.
- Bind Mode.
- Action Book and Macro Book UI.
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
