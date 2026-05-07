---
summary: Research-backed feature gap report for ActionRail, with prioritized missing capabilities and source links.
read_when:
  - Planning ActionRail feature work after the declarative MVP.
  - Deciding what to build next beyond the transform stack.
  - Reviewing whether ActionRail is competitive with Maya-native workflows, pickers, action bars, and radial menus.
---

# Missing Features Research

Date: 2026-04-28

## Current Product Shape

ActionRail has a solid MVP base:

- JSON presets for vertical and horizontal rails.
- Stable slot ids and layout metadata.
- Qt overlay rendering over a Maya model panel.
- Theme tokens and generated QSS.
- Built-in transform and keyframe actions.
- Runtime-command and nameCommand publishing for Maya hotkeys.
- Conflict-aware hotkey assignment helpers.
- Safe predicate evaluation and automatic timer-driven refresh for visible
  overlay hosts.
- Safe-mode diagnostics and visible missing-action, missing-icon, missing-command,
  and missing-plugin badges.
- Provider-backed icon catalog, first-party SVG icons, curated Maya resource
  icons, SVG import diagnostics, and PNG fallback generation.
- User preset storage, shared bundled/user preset resolution, dockable Quick
  Create, preview/save/load workflow, and the first Edit Mode layout-map shell.
- Pure Python tests and MayaSessiond smoke coverage.

The main product gap is now a unified WoW-style authoring workflow. Current
rails should be treated as action bar frames, not the whole product boundary.
Edit Mode should remain frame layout/configuration; slot payload changes should
stay outside Edit Mode behind Normal Mode rail lock/unlock controls; later
Action Book, Macro Book, and Bind Mode should make placing actions and binding
keys feel like one connected workflow.

2026-04-29 status note: safe predicate evaluation, live predicate refresh,
hotkey label sync, shelf/menu toggles, reusable smoke wrapper, safe-mode
diagnostics, and visible missing-action/missing-icon/command/plugin badges are now implemented.
First-pass last diagnostic report API/UI is also implemented. The sections
below remain useful research context; the active backlog starts with
icon-backed presets/import tooling.

2026-04-30 status note: the first icon-backed built-in rail is implemented.
`horizontal_tools` now references first-party SVG icons through
`icons/manifest.json`, and diagnostics validate required metadata, duplicate
ids, invalid local paths, missing files, unknown ids, invalid SVG files, and
unsafe SVG content.

2026-04-30 follow-up: `actionrail.icons.import_svg_icon()` now covers the first
local import-tooling slice by validating local SVG safety, copying assets under
`icons/`, and upserting manifest source/license/url/import-date metadata. The
helper now rejects external resources in SVG style blocks and normalizes
manifest paths before overwrite conflict checks. PNG fallback generation now
records 1x/2x/3x assets plus source hashes in the manifest, and diagnostics
report missing or stale fallback assets.

2026-05-05 status note: Maya-facing icon import diagnostics, fallback preset
recovery, Quick Create preview/save/load, curated Maya resource icons, and
Phase 2 step 2.5 layout editing/direct manipulation are implemented and smoke
verified. The active backlog starts with Phase 2 step 2.6 collapsible edge tabs
and authoring workflow polish.

2026-05-07 architecture note: WoW should remain the primary reference. ActionRail
now uses frames as the broad product concept: action bars are one frame type,
with future room for info frames, tooltip frames, selection/object frames, and
deformer-stack frames. The next major authoring concepts are an Action Book for
curated Maya commands/tools, a Macro Book for user script actions with icons,
and Bind Mode for hover/click-to-bind slot hotkeys. Runtime-command publishing
is implementation plumbing, not the main user-facing workflow.

## Highest Priority Gaps

### 1. Real Predicate Evaluation

Status: implemented for the Phase 1 predicate set; keep this section as source
context for future predicate expansion.

Earlier Phase 1 code parsed `visible_when`, `enabled_when`, and `active_when`
before fully applying them to rendered slot state. The current implementation
evaluates these predicates through a safe evaluator and refreshes visible
overlays automatically; future work should broaden predicate coverage only as
needed.

Build a small safe evaluator before adding the designer:

- `selection.count`
- `selection.type`
- `maya.tool`
- `active.panel`
- `active.camera`
- `playback.playing`
- `plugin.exists`
- `command.exists`
- `action.exists`

Do not make arbitrary Python snippets the default predicate path for artists.

### 2. Live Active And Enabled State

Status: implemented for rendered action slots through predicate refresh and
`SlotRenderState`; continue expanding it for diagnostic badges and future icon
states.

Transform buttons should show the active Maya tool without requiring reload.
Disabled actions should be visually disabled when missing commands, missing
plugins, empty selection, playback state, or unsupported contexts make an action
invalid.

The internal model should move toward an action/state object that can drive
checked, enabled, icon, tooltip, and badge state. Qt `QToolButton` and `QAction`
support this pattern directly.

Source: [Qt QToolButton](https://doc.qt.io/qt-6/qtoolbutton.html)

### 3. Hotkey Label Sync

Status: implemented for ActionRail hotkey assignment and visible slot refresh;
Bind Mode remains future work.

Key labels originally rendered only from static preset data. Current ActionRail
assignment helpers update visible slot badges after binding; future Bind Mode
should reuse the same runtime-command bridge and conflict checks.

Required behavior:

- Query press and release bindings.
- Format modifiers consistently.
- Update visible overlays after assignment.
- Show conflict state before overwrite.
- Preserve slot ids so bindings survive label/order changes.

Maya runtime commands are the right bridge because they are visible in Maya's
Hotkey Editor and can be edited there.

Source: [Autodesk runtime commands](https://help.autodesk.com/cloudhelp/2026/ENU/Maya-Customizing/files/GUID-2B2BE446-D622-4274-80FC-2A5EF7D87C5C.htm)

### 4. Shelf And Menu Entry Points

Status: implemented for the default rail toggle, diagnostics, SVG import
preflight, Quick Create, and Toggle Edit Mode through Maya menu/shelf entry
points where applicable. Bind Mode commands remain future work.

Keep expanding user-visible Maya entry points:

- Shelf button to toggle the current/default rail.
- Main menu item for ActionRail.
- Commands for show, hide, reload, safe start, Edit Mode, and Bind Mode.

The later designer should be a dockable workspace control with restore-safe
`uiScript`, not a viewport overlay.

Source: [Autodesk workspace controls](https://help.autodesk.com/cloudhelp/2024/CHS/Maya-SDK/files/Maya-Python-API/Maya_SDK_Maya_Python_API_Writing_Workspace_controls_html.html)

### 5. Unified Frame Authoring Workflow

Status: Quick Create and the Phase 2 step 2.5 Edit Mode layout editing surface
are implemented and Maya-smoke verified. Quick Create can create draft rails
from templates, preview, save, overwrite, and load user presets. Edit Mode can
inspect active rails in a layout-map overlay, select rail frames, show
Grid/Grid Size/Snap to Grid/Sticky Frames controls, apply X/Y movement with
snap/sticky alignment, and persist layout edits to user presets or user
override sidecars. The old right-click frame options popover has been removed
from Edit Mode. The remaining authoring gap begins with Phase 2 step 2.6
collapsible edge-tab runtime/persistence, Normal Mode slot lock/unlock polish,
and unified authoring workflow polish.

The first artist-facing authoring workflow should stay narrow and connected:

1. Pick a frame/template: blank action bar, starter Maya tool bar,
   collapsible edge tab, compact grid/palette, and later info/object frames.
2. Pick workflow context: modeling, rigging, animation, layout, camera,
   display, project.
3. Add actions from the Action Book.
4. Add user scripts from the Macro Book when built-in Maya actions are not
   enough.
5. Pick labels/icons.
6. Place/configure the frame in the active viewport.
7. Bind slot hotkeys in Bind Mode.
8. Preview without saving.
9. Save as a user preset or user override.

Edit Mode has the first layout-map shell and should continue toward direct
manipulation:

- rail outlines and hit boxes
- layout-map view of bars/frames as labeled dark rectangles
- direct frame dragging
- optional grid overlay
- optional snap-to-grid
- optional sticky-frame snapping between rails
- snap guides
- safe margins
- scale and opacity controls
- selected-frame position popover with arrow nudges, numeric X/Y, and Reset
- draggable compact Edit Mode control panel
- selected-rail Lock/Unlock control
- Normal Mode rail lock/unlock helpers for slot payload assignment, clear,
  move, swap, and cross-rail transfer
- collapsible side-tab controls
- lock state
- source layer badges
- persisted user preset or user override writes for edited layouts

WoW Edit Mode validates the product direction: named layouts can be saved,
edited, copied, shared, and remembered per context.

Source: [World of Warcraft HUD/UI revamp](https://worldofwarcraft.blizzard.com/en-us/news/23841481)

### 6. Bind Mode

Bind Mode should be built together with the first Action Book workflow because
it completes the Maya action-bar loop: put an action on a slot, hover/click the
slot, press a shortcut, and see the key label update.

Workflow:

1. User enters Bind Mode.
2. User hovers or selects a slot.
3. User presses a shortcut.
4. ActionRail detects conflicts.
5. ActionRail creates or updates the Maya hotkey.
6. The key badge updates in the visible overlay.

Required commands:

- `actionrail.bind_mode.toggle`
- `actionrail.bind_mode.clear_hovered`
- `actionrail.hotkeys.validate`

### 7. Flyouts

Flyouts are the next compact control after normal buttons. They keep the
viewport clean while grouping related actions.

Good first flyouts:

- transform tools
- keying tools
- selection tools
- display modes
- camera bookmarks
- rig controls
- project scripts

Qt `QToolButton` supports menus and delayed popup modes, but press-and-hold
behavior must be tested inside Maya because host focus handling can differ from
standalone Qt.

Source: [Qt QToolButton](https://doc.qt.io/qt-6/qtoolbutton.html)

### 8. Command Rings

Command rings should share the same action registry as rails and flyouts.

Initial behavior:

- press hotkey to show ring
- move cursor toward a wedge
- release to execute
- click center or press Escape to cancel
- optionally pin open for inspection

OPie and Houdini validate the pattern: radial menus reduce persistent screen
clutter and work well with hotkeys, mouse, and tablet workflows.

Sources:

- [OPie radial action-binding addon](https://www.curseforge.com/wow/addons/opie)
- [Houdini radial menus](https://www.sidefx.com/docs/houdini/basics/radialmenus)

### 9. Maya Marking Menu And Hotbox Bridge

ActionRail should eventually export an action group to a native Maya marking
menu or hotbox region. This gives users a Maya-native escape hatch and makes
ActionRail actions available to people who prefer gestural menus over visible
rails.

Source: [Autodesk hotbox marking menus](https://help.autodesk.com/cloudhelp/2020/ENU/MayaLT-CustomizingMayaLT/files/GUID-108EB516-4913-4623-9A31-15582F983B1C.htm)

### 10. Icon Pipeline

The icon manifest now has first-party entries, and `import_svg_icon()` covers
the first local import path with SVG safety validation, manifest path
normalization, source/license metadata, and generated PNG fallbacks. ActionRail
also has a first provider-aware descriptor layer for curated Maya built-in
resource icons. ActionRail still needs a polished icon browser before shipping
larger preset packs.

Required features:

- import SVG icons into `icons/`. First pass done for local SVG files.
- sanitize SVGs: no scripts, no external resources, fixed viewBox. First pass
  done through manifest/import validation.
- prefer monotone `currentColor`.
- record source, license, original URL, and import date. First pass done in
  `icons/manifest.json`.
- generate PNG fallbacks at 1x, 2x, and 3x when needed. First pass done for
  import-time generation, explicit regeneration, and fallback asset
  diagnostics.
- expose a local icon browser in the designer.
- expose Maya built-in resources in the same browser through stable logical ids
  such as `maya.move`, not raw resource names such as `move_M.png`. First pass
  done for a curated provider and `IconDescriptor` metadata.

Iconify is useful as an import source because its icon sets are validated and
cleaned, but licenses must be tracked per icon set. Lucide is a good first pack
because it is consistent, lightweight SVG and ISC licensed.

Sources:

- [Iconify icon sets](https://github.com/iconify/icon-sets)
- [Lucide icons](https://lucide.dev/)

### 11. Broader Action Library

The current action registry only covers move/translate/rotate/scale/set key.
Evolve it into the Action Book: a searchable, curated, provider-backed catalog
of Maya actions that can be placed onto slots. Add action groups by workflow:

- selection and component mode
- display and viewport toggles
- camera bookmarks
- playback and timeline
- keying variants: translate, rotate, scale, selected channels
- graph editor and tangent operations
- rig picker controls
- project/studio scripts
- plugin commands

Maya's own animation hotkeys show useful targets, including set-key variants
and keyframe/tangent marking menus.

Source: [Maya animation hotkeys](https://help.autodesk.com/cloudhelp/2025/ENU/Maya-KeyboardShortcuts/files/GUID-0639ADA0-EBE5-4703-A874-92C80E4A0516.htm)

### 12. Macro Book

ActionRail should eventually let users create WoW-macro-like Maya actions
without editing framework code. A macro entry should have a stable id, display
name, icon, tooltip, Python or MEL body, optional safe predicates, and source
metadata if it was imported from a shelf button. Once saved, the macro should
appear in the Action Book and be assignable to any slot like a built-in action.

The Macro Book should come after the first Action Book and Bind Mode pass so
custom scripts use the same placement and hotkey path as native Maya actions.

### 13. Picker-Grade Controls

Animation picker tools prove users need more than square buttons:

- custom shapes
- background images
- right-click context menus
- custom scripts per button
- per-control colors and alpha
- label size/color
- namespace-aware rig association
- scene or asset preset links
- mirror/copy/key helpers

ActionRail should not become a full character picker immediately, but its slot
schema should not block picker-grade controls later.

Sources:

- [mGear Anim Picker](https://mgear4.readthedocs.io/en/stable/quickStart.html)
- [anim_picker features](https://www.highend3d.com/maya/script/anim_picker)

### 14. Diagnostics And Safe Mode

Status: first pass implemented through `actionrail.collect_diagnostics()`,
`actionrail.diagnose_spec()`, `actionrail.safe_start()`,
`actionrail.last_report()`, `actionrail.format_report()`, visible
missing-action/missing-icon badges, missing command/plugin predicate badges,
and a Maya menu item for showing the latest diagnostic report in a themed Qt
diagnostics window.

Viewport overlays can break trust if they get stuck, steal input, or fail on
startup. Add diagnostics before complex authoring.

User feedback on the first report UI was addressed: the raw Maya
`confirmDialog` has been replaced with an ActionRail-themed Qt diagnostics
window. Error details are available in a selectable report area, and issue/full
report copy actions are available for support or issue reports.

Reference direction from WoW add-on tooling: do not copy the visual style, but
borrow the workflow. BugSack/BugGrabber-style tools collect errors, show a
navigable error frame, include full debug text, and make the error text
copy/pasteable. ActionRail should use the same pattern: a quiet diagnostics
viewer, not repeated blocking popups.

Required features:

- `actionrail.safe_start()`
- disable all overlays. First visible support pass done through the diagnostics
  window `Hide Overlays` action.
- list active overlays
- list callbacks/event filters
- list published runtime commands
- list missing actions/icons/plugins
- orphaned hotkey/runtime-command cleanup
- last error report
- broken-action and missing-icon badges
- themed diagnostics window with summary, issue list, selectable full report,
  visible selected-issue details, and copy actions for selected issues and the
  full report. First pass done.

### 15. High DPI And Visual Regression

Maya 2025+ uses Qt6/PySide6, and Qt High DPI is always on. ActionRail should
verify mixed display scaling, fractional Windows scaling, and screenshot
stability before accepting theme/layout changes.

Add visual verification commands that capture:

- preset id
- Maya version
- viewport size
- device pixel ratio
- theme id
- rail size
- screenshot artifact path

Sources:

- [Maya Qt6 migration](https://help.autodesk.com/cloudhelp/2025/CHS/Maya-DEVHELP/files/Whats-New-Whats-Changed/2025-Whats-New-in-API/Qt6Migration.html)
- [Qt High DPI](https://doc.qt.io/qt-6.8/highdpi.html)

## Backend Guidance

Keep Qt as the clickable UI backend.

Maya 2026 includes `moverlay`, a Qt-based overlay module intended for 2D UI
over Maya. It is worth spiking as a helper or reference, especially for tutorial
style overlays and hotkey hints, but ActionRail still needs precise hit testing,
viewport anchoring, styling, and cleanup.

Source: [Autodesk moverlay documentation](https://help.autodesk.com/cloudhelp/2026/ENU/Maya-Scripting/files/GUID-77D2AC6E-97D2-41FC-8FF8-A86410093708.htm)

Viewport 2.0 should stay deferred to non-clickable labels, guides, and
object-bound graphics. Autodesk's `MUIDrawManager` supports 2D drawables in
screen pixels, but rebuilding normal buttons, menus, layout, and hit testing
there would add unnecessary complexity.

Source: [Maya UI draw manager](https://help.autodesk.com/cloudhelp/2022/ENU/Maya-SDK/Viewport-2-0-API/Maya-Viewport-2-0-API-Guide/Plug-in-Entry-Points/UI-draw-manager.html)

## Recommended Next Roadmap

1. Finish Phase 2 step 2.6 collapsible edge tabs and authoring workflow polish,
   including Quick Create stability, locked-preset read-only behavior, and
   clearer handoff between templates, Edit Mode, and Normal Mode slot editing.
2. Add the Action Book and Bind Mode.
3. Add the Macro Book for user script actions with icons.
4. Add flyouts.
5. Add command rings.
6. Add profile layers: built-in, studio locked, project, scene/asset, user
   override.
7. Add marking-menu/hotbox export.
8. Add Viewport 2.0 labels/guides only after the Qt overlay remains stable.
