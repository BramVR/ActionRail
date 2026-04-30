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
- Pure Python tests and MayaSessiond smoke coverage.

The main gap is that the UI is still not authorable or diagnostic enough for
artists. The next work should make rails recoverable, explain broken presets or
missing commands clearly, then add narrow authoring workflows beyond the current
transform stack.

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
manifest paths before overwrite conflict checks. The remaining active backlog
is PNG fallback generation and import diagnostics.

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

Status: implemented for the default rail toggle through idempotent Maya menu and
shelf installers; Edit Mode and Bind Mode commands remain future work.

Keep expanding user-visible Maya entry points:

- Shelf button to toggle the current/default rail.
- Main menu item for ActionRail.
- Commands for show, hide, reload, safe start, Edit Mode, and Bind Mode.

The later designer should be a dockable workspace control with restore-safe
`uiScript`, not a viewport overlay.

Source: [Autodesk workspace controls](https://help.autodesk.com/cloudhelp/2024/CHS/Maya-SDK/files/Maya-Python-API/Maya_SDK_Maya_Python_API_Writing_Workspace_controls_html.html)

### 5. Quick Create And Edit Mode

The first artist-facing authoring workflow should stay narrow:

1. Pick a template: vertical stack, horizontal strip, collapsible edge tab,
   flyout, command ring, status badge strip.
2. Pick workflow context: modeling, rigging, animation, layout, camera,
   display, project.
3. Add actions from a searchable registry.
4. Pick labels/icons.
5. Place in the active viewport.
6. Preview without saving.
7. Save as a user preset.

Edit Mode should add direct manipulation:

- rail outlines and hit boxes
- drag handles
- anchor pins
- snap guides
- safe margins
- scale and opacity controls
- collapsible side-tab controls
- lock state
- source layer badges

WoW Edit Mode validates the product direction: named layouts can be saved,
edited, copied, shared, and remembered per context.

Source: [World of Warcraft HUD/UI revamp](https://worldofwarcraft.blizzard.com/en-us/news/23841481)

### 6. Bind Mode

Bind Mode should be built before broad designer work because it completes the
runtime-command bridge and makes the current MVP useful.

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
normalization, and source/license metadata. ActionRail still needs fallback
generation and broader import diagnostics before shipping more polished preset
packs.

Required features:

- import SVG icons into `icons/`. First pass done for local SVG files.
- sanitize SVGs: no scripts, no external resources, fixed viewBox. First pass
  done through manifest/import validation.
- prefer monotone `currentColor`.
- record source, license, original URL, and import date. First pass done in
  `icons/manifest.json`.
- generate PNG fallbacks at 1x, 2x, and 3x when needed.
- expose a local icon browser in the designer.

Iconify is useful as an import source because its icon sets are validated and
cleaned, but licenses must be tracked per icon set. Lucide is a good first pack
because it is consistent, lightweight SVG and ISC licensed.

Sources:

- [Iconify icon sets](https://github.com/iconify/icon-sets)
- [Lucide icons](https://lucide.dev/)

### 11. Broader Action Library

The current action registry only covers move/translate/rotate/scale/set key.
Add action groups by workflow:

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

### 12. Picker-Grade Controls

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

### 13. Diagnostics And Safe Mode

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
- disable all overlays
- list active overlays
- list callbacks/event filters
- list published runtime commands
- list missing actions/icons/plugins
- orphaned hotkey/runtime-command cleanup
- last error report
- broken-action and missing-icon badges
- themed diagnostics window with summary, issue list, selectable full report,
  and copy actions for selected issues and the full report. First pass done.

### 14. High DPI And Visual Regression

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

1. Continue the icon pipeline with PNG fallback generation and import
   diagnostics.
2. Continue visible diagnostics as the icon/preset import path expands.
3. Implement narrow Quick Create: template, action picker, collapsible edge-tab
   option, preview, save user preset.
4. Add Bind Mode.
5. Add flyouts.
6. Add command rings.
7. Add profile layers: built-in, studio locked, project, scene/asset, user
   override.
8. Add marking-menu/hotbox export.
9. Add Viewport 2.0 labels/guides only after the Qt overlay remains stable.
