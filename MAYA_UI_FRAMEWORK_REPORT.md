---
summary: Research and architecture proposal for ActionRail, a Maya UI framework that creates polished viewport and tool UIs like the reference screenshots.
read_when: Planning ActionRail architecture, implementation phases, user workflow, or Maya/Qt extension choices.
---

# ActionRail Framework Research

Date: 2026-04-27

## Brief

Build a Maya framework that lets a user create small, polished, reusable UI elements inside Maya, especially viewport-adjacent controls like the local references in ignored `research/` checkouts:

- `research/Move_translate_rotate_scale.png`: 229 x 227, vertical stack of square buttons labeled `M`, `T`, `R`, `S`, with `S` highlighted.
- `research/Move_translate_rotate_scale_key.png`: 68 x 258, same stack plus a separate accented `K` button.

The reference style is screen-space, compact, tool-like, low-chrome, dark neutral UI with clear active/accent states. It should feel like a native Maya tool overlay, not a large docked app.

## Recommendation

Use a hybrid framework:

1. **Primary renderer: PySide6/Qt rail overlay**
   - Best match for polished clickable controls, hover/press states, animation, tooltips, menus, high-level layouts, theme tokens, and user-defined actions.
   - Parent overlay widgets to Maya's existing Qt widgets. Do not create a new `QApplication`.

2. **Maya action/runtime layer**
   - Bind buttons to Maya commands, MEL/Python callbacks, named commands, contexts, hotkeys, shelves, and optionVars.
   - Wrap actions in undo chunks where appropriate.

3. **Optional Viewport 2.0 draw backend**
   - Use `MUIDrawManager`, `MPxDrawOverride`, and/or `MRenderOverride` only for overlay graphics that need to be drawn by the viewport pipeline, not for the first clickable widget MVP.
   - Use custom contexts or `draggerContext` for viewport manipulation tools that need press/drag/release behavior.

This keeps the MVP simple and useful while leaving room for more serious viewport-native tools.

## Source-Grounded Constraints

- Maya 2025+ moved from Qt5/PySide2 to Qt6/PySide6. Autodesk notes that Qt High DPI is always on in Qt 6 and recommends `try/except` imports when supporting both Qt5 and Qt6 Maya builds. Source: [Maya Qt6 migration](https://help.autodesk.com/cloudhelp/2025/ENU/Maya-DEVHELP/files/Whats-New-Whats-Changed/2025-Whats-New-in-API/Qt6Migration.html).
- Maya 2026 documents PySide6 as the Python Qt binding. Widgets need stable `objectName()` values, sizing must be managed explicitly, and widgets must be parented under Maya widgets to avoid Python garbage collection issues. Source: [Working with PySide in Maya](https://help.autodesk.com/cloudhelp/2026/ENU/Maya-DEVHELP/files/Maya-Python-API/Maya_DEVHELP_Maya_Python_API_Working_with_PySide_in_Maya_html.html).
- Maya already owns the Qt application object. A Qt plug-in or script should use `QApplication.instance()` and must not create another `QApplication`. Source: [Writing Qt plug-ins](https://help.autodesk.com/cloudhelp/2026/CHS/Maya-DEVHELP/files/Working-with-Qt/Maya_DEVHELP_Working_with_Qt_WritingQtPlugins_html.html).
- Dockable panels should use workspace controls and `MayaQWidgetDockableMixin` when the UI is a panel, with a `uiScript` capable of recreating the widget on workspace restore. Source: [Writing Workspace controls](https://help.autodesk.com/cloudhelp/2022/ENU/Maya-SDK/Maya-Python-API/Writing-Workspace-controls.html).
- Viewport 2.0 UI drawing can use `MUIDrawManager`, including 2D drawables and text, but those callbacks are tied to the Viewport 2.0 render flow. Source: [UI draw manager](https://help.autodesk.com/cloudhelp/2022/ENU/Maya-SDK/Viewport-2-0-API/Maya-Viewport-2-0-API-Guide/Plug-in-Entry-Points/UI-draw-manager.html).
- `MPxDrawOverride` gives low-level draw control but requires careful caching and draw-state management. Maya warns not to pull dependency graph data during the draw method. Source: [Draw Overrides](https://help.autodesk.com/cloudhelp/2026/ENU/Maya-DEVHELP/files/Viewport-2-0-API/Maya-Viewport-2-0-API-Guide/Plug-in-Entry-Points/Viewport_2_draw_overrides_html.html).
- `headsUpDisplay` is useful for simple text HUDs but is a 2D inactive overlay plane, not a polished interactive control toolkit. Source: [headsUpDisplay command](https://help.autodesk.com/cloudhelp/2024/ENU/Maya-Tech-Docs/CommandsPython/headsUpDisplay.html).
- Maya native `iconTextButton` supports labels, icons, colors, drag/drop, and callbacks, but it is a standard control, not a full viewport overlay system by itself. Source: [iconTextButton command](https://help.autodesk.com/cloudhelp/2022/ENU/Maya-Tech-Docs/Commands/iconTextButton.html).
- Maya modules are the right packaging format for a multi-file add-on. `.mod` files can target Maya version/platform and set paths such as `scripts`, `plug-ins`, `icons`, and `PYTHONPATH`. Sources: [Creating a module package](https://help.autodesk.com/cloudhelp/2023/ENU/Maya-SDK/files/Distributing-Maya-Plug-ins/DistributingUsingModules/Maya_SDK_Distributing_Maya_Plug_ins_DistributingUsingModules_CreatingAModulePackage_html.html), [Module description files](https://help.autodesk.com/cloudhelp/2025/ENU/Maya-DEVHELP/files/Distributing-Maya-Plug-ins/DistributingUsingModules/Maya_DEVHELP_Distributing_Maya_Plug_ins_DistributingUsingModules_ModuleDescriptionFiles_html.html).
- Qt Style Sheets can customize widgets with CSS-like syntax, and Qt Graphics View can manage custom 2D items, events, transforms, and animations. Sources: [Qt Style Sheets](https://doc.qt.io/qt-6/stylesheet.html), [Qt Graphics View Framework](https://doc.qt.io/archives/qt-6.9/graphicsview.html).
- Qt can render SVG through `QSvgRenderer`, and `QIcon` can use SVG image files when the SVG icon engine is available. Sources: [QSvgRenderer](https://doc.qt.io/qt-6/qsvgrenderer.html), [QIcon](https://doc.qt.io/qt-6/qicon.html).
- Qt WebEngine can embed HTML/CSS/JavaScript web content in Qt applications, but Maya's official component list should be treated as the compatibility source for what is actually bundled in a Maya install. Do not make WebEngine required for the core overlay unless a runtime probe confirms it exists. Sources: [Qt WebEngine Overview](https://doc.qt.io/qt-6/qtwebengine-overview.html), [Maya 2026 Open Source Components](https://help.autodesk.com/cloudhelp/2026/ENU/Maya-DEVHELP/files/Maya_DEVHELP_Open_Source_Components_html.html).
- Open icon packs are practical for this project if licenses are tracked. Good candidates: Lucide SVG icons under ISC, Tabler Icons under MIT, and Google Material Symbols under Apache 2.0. Sources: [Lucide](https://lucide.dev/), [Tabler Icons](https://github.com/tabler/tabler-icons), [Material Symbols guide](https://developers.google.com/fonts/docs/material_symbols).

## Evaluated Approaches

| Approach | Fit | Strengths | Weaknesses | Use |
|---|---:|---|---|---|
| Maya `cmds` UI controls | Medium | Native, simple, undo/query/edit support for many controls | Hard to make modern overlays, limited layout/styling | Shelf buttons, quick panels, fallback widgets |
| `headsUpDisplay` | Low | Easy viewport text/status | Not interactive, limited styling | Status readouts only |
| PySide6 transparent overlay | High | Polished widgets, events, styling, animation, menus, user workflow | Must track viewport panels, DPI, focus, input pass-through, cleanup | Primary MVP |
| QGraphicsView overlay | Medium-high | Custom item scene, transforms, animation, embedded widgets | More custom code than widgets; may be overkill for simple stacks | Advanced designer canvas or node-like palettes |
| Qt Quick/QML | Medium | Modern animation and declarative UI | More deployment risk inside Maya, Qt Quick/widget embedding complexity | Later experimental backend |
| Viewport 2.0 `MUIDrawManager` | Medium | Proper viewport drawing, 2D/3D drawables, render-flow aware | Not a normal widget system; interaction and hit testing are custom | Non-widget overlays, guides, labels |
| `MPxDrawOverride`/`MRenderOverride` | Medium | Deep viewport integration | More plugin complexity, caching restrictions, selection complexity | Custom in-scene/viewport elements |
| `MPxContext` / `draggerContext` | Medium | Correct route for press/drag/release viewport tools | Tool-centric, not UI layout-centric | Manipulators, transform drags, gesture tools |
| SVG/icon asset pipeline | High | Huge pool of polished icons, easy recoloring, scalable | License tracking and SVG feature compatibility needed | Buttons, menus, status badges |
| Embedded web UI | Low-medium | Familiar HTML/CSS/JS authoring, rich designer tools | WebEngine availability/deployment risk, focus/input complexity | Optional designer panel, not core overlay |

## Existing Open-Source References

I did not find an open-source GitHub project that already provides the exact proposed product: an artist-friendly Maya framework for declarative, polished, clickable viewport overlay UI elements with designer, themes, action registry, icons, and optional Viewport 2.0 backend. There are useful adjacent projects:

| Project | What it is | Useful for ActionRail | Gap |
|---|---|---|---|
| [danbradham/mvp](https://github.com/danbradham/mvp) | Maya Viewport API wrapper | Model panel/model editor abstraction; draws viewport text with Qt labels | Not a UI creation framework or designer |
| [theodox/mGui](https://github.com/theodox/mGui) | Cleaner syntax around Maya built-in UI commands | Declarative-ish API ideas and simple Maya UI ergonomics | Built on Maya cmds widgets, not PySide overlay |
| [mottosso/Qt.py](https://github.com/mottosso/Qt.py) | Qt binding compatibility shim | Import compatibility across PySide/PyQt versions | Not Maya-specific overlay framework; limited abstraction |
| [shiningdesign/universal_tool_template.py](https://github.com/shiningdesign/universal_tool_template.py) | Cross-DCC Qt tool template | Host detection, UI template ideas, icon/style conventions | Large generic app template, not viewport overlay system |
| [mgear-dev/mgear](https://github.com/mgear-dev/mgear) | Maya rigging/animation framework | Production-grade Maya package structure, tools, UI examples, anim picker references | Domain-specific; not a reusable general overlay UI framework |
| [TrevisanGMW/gt-tools](https://github.com/TrevisanGMW/gt-tools) | Free Maya script/tool collection with Qt UI utilities | Packaging, installer, menu/tool organization, Maya UI utility patterns | Tool suite, not a UI framework for user-created overlays |
| [blockinhead VP2 draw override gist](https://gist.github.com/blockinhead/940e3032ad5e2663136d1309e90a0cc0) | Minimal Python Viewport 2.0 locator draw override | Tiny reference for `MPxDrawOverride`/`MUIDrawManager` backend | Demo only; not interactive overlay UI |
| [Autodesk/maya-hydra](https://github.com/Autodesk/maya-hydra) | Alternative Hydra viewport plugin | Serious viewport architecture reference | Overkill and unrelated to small clickable UI overlays |
| [Autodesk/maya-usd](https://github.com/Autodesk/maya-usd) | USD integration with viewport/editor tooling | Mature Maya plugin layout and viewport integration patterns | USD domain; not an overlay UI authoring toolkit |

Conclusion: reuse ideas, not code wholesale. `mvp` is the closest reference for viewport-panel abstraction; `mGui` and `universal_tool_template.py` are useful for authoring ergonomics; `Qt.py` helps if older Maya support matters; the VP2 gist is useful when adding the later viewport-native drawing backend.

## Agent Workflow References

Steipete's public GitHub material is useful for how we build ActionRail, not for the Maya UI runtime itself.

Relevant references:

- [steipete/agent-scripts](https://github.com/steipete/agent-scripts): canonical shared agent instructions, small reusable scripts, docs listing, commit helper, browser tools, and sync conventions.
- [steipete/agent-rules](https://github.com/steipete/agent-rules): older archived rules repo; useful mainly as historical context because it now points to `agent-scripts`.
- [steipete/oracle](https://github.com/steipete/oracle): bundles prompts and selected files for another model to review architecture, bugs, or implementation risk.
- [steipete/Peekaboo](https://github.com/steipete/Peekaboo): macOS screenshot/GUI automation. Not directly portable to Windows Maya, but the visual verification workflow is relevant.
- [steipete/mcporter](https://github.com/steipete/mcporter): MCP/CLI packaging pattern for making tools easy for agents to call.

Practices worth borrowing:

1. **Pointer-style instructions**
   - Keep shared agent rules in one canonical place and make project `AGENTS.MD` files point to it.
   - This repo already follows the same idea via `../bram-agent-scripts/AGENTS.MD`.

2. **Docs with discoverability metadata**
   - New docs should include `summary` and `read_when` front matter.
   - This report already uses that shape.
   - Future docs should cover install, architecture, icon pipeline, Maya smoke tests, and designer workflow.

3. **Small reusable scripts**
   - Add project scripts that agents and humans can run without remembering fragile commands:
     - `scripts/docs-list.ps1`
     - `scripts/maya-smoke.ps1`
     - `scripts/import-icons.ps1`
     - `scripts/render-reference.ps1`
     - `scripts/package-module.ps1`

4. **Explicit review loops**
   - Use a second-model review through Oracle or an equivalent tool for:
     - PySide overlay architecture before implementation.
     - Viewport 2.0 backend design.
     - Maya callback cleanup/reload safety.
     - Release readiness before packaging.
   - Keep API-costing runs opt-in; browser/copy mode is safer for exploratory review.

5. **Visual verification loop**
   - Steipete's Peekaboo workflow points at the right habit: capture UI, inspect it, adjust, repeat.
   - For this Windows/Maya project, use Maya viewport screenshots, Qt widget screenshots, or Playwright-style visual checks where possible.

6. **Tool wrappers over tribal knowledge**
   - If a workflow will happen more than twice, create a script or documented command.
   - This matters for Maya because startup flags, module paths, mayapy, and UI smoke tests are easy to get subtly wrong.

What not to copy:

- Personal machine assumptions, macOS-specific paths, private tools, or direct `op`/secret workflows.
- Browser automation as a core dependency for the Maya runtime.
- Multi-agent workflows as a substitute for narrow specs and reproducible smoke tests.

## UX And Workflow Updates From Research

The main UX update is to make ActionRail feel like a visual authoring layer for Maya's existing command ecosystem, not a separate UI universe.

For the focused WoW-style customization roadmap, including Edit Mode, action slots, Bind Mode, flyouts, command rings, profiles, and schema direction, see `docs/06_wow_style_customization.md`.

Research signals:

- Maya's marking menus are designed for speed once users learn item positions, and can be assigned to hotkeys or hotbox zones. Source: [Marking Menus](https://help.autodesk.com/cloudhelp/2024/ENU/Maya-KeyboardShortcuts/files/GUID-8BA1A3AA-4C44-4779-8B22-0AAE3627E8EB.htm), [Marking Menu Editor](https://help.autodesk.com/cloudhelp/2026/ENU/Maya-Customizing/files/GUID-9C43FD30-D92F-4035-9820-4C3FFDD8E211.htm).
- Maya's hotbox already supports command access without visible menus and exposes customizable zones around the viewport. Source: [Select actions from the hotbox](https://help.autodesk.com/cloudhelp/2024/ENU/Maya-Basics/files/GUID-06174D85-0B39-4EAD-B814-D1E06C3344AE.htm), [Customize the hotbox](https://help.autodesk.com/cloudhelp/2022/ENU/Maya-Customizing/files/GUID-F182139D-1E00-44E6-9D79-4AF053860EDA.htm).
- Runtime commands are the right Maya-native bridge for scripts that should also be assignable to hotkeys. Source: [Create a runtime command](https://help.autodesk.com/cloudhelp/2022/ENU/Maya-KeyboardShortcuts/files/GUID-2B2BE446-D622-4274-80FC-2A5EF7D87C5C.htm).
- Hotkeys have press/release behavior, which matters for modal or momentary controls. Source: [Assign a hotkey to a command](https://help.autodesk.com/cloudhelp/2022/ENU/Maya-KeyboardShortcuts/files/GUID-92F8EBD9-A658-4A1E-9D85-571B5B809F52.htm).
- Workspace controls need restore-safe `uiScript` behavior. The designer should be a workspace control, while viewport overlays should be toggleable runtime UI. Source: [Writing Workspace controls](https://help.autodesk.com/cloudhelp/2022/ENU/Maya-SDK/Maya-Python-API/Writing-Workspace-controls.html).
- Qt's `QToolButton`, `QAction`, and `QIcon` map well to tool/action UI, including active/disabled icon states and high-DPI image handling. Sources: [QToolButton](https://doc.qt.io/qt-6/qtoolbutton.html), [QIcon for PySide6](https://doc.qt.io/qtforpython-6.8/PySide6/QtGui/QIcon.html).
- mGear's Synoptic/Anim Picker pattern validates the broader idea that visual pickers help animators interact with rigs faster, including selection, keying, mirroring, and space switching. Source: [mGear Synoptic](https://mgear4.readthedocs.io/en/master/synopticModules.html), [mGear anim_picker package](https://mgear4.readthedocs.io/en/latest/mgear/mgear.anim_picker.html).
- WoW's Edit Mode validates direct manipulation of HUD/layout components with named, saved, copied, and shared layouts. Source: [Blizzard HUD/UI revamp](https://news.blizzard.com/en-us/article/23841481/hud).
- WoW action bar addons validate configurable bars, visibility rules, profiles, and hover-to-bind workflows. Sources: [Bartender4](https://www.curseforge.com/wow/addons/bartender4), [Dominos](https://www.curseforge.com/wow/addons/dominos).
- Radial/flyout addons validate compact command access for large action sets. Sources: [OPie](https://www.curseforge.com/wow/addons/opie), [Mage Teleporter](https://www.curseforge.com/wow/addons/mage-teleporter).

### Product UX Changes

Add a **Quick Create** flow before the full designer:

1. Choose a template: vertical stack, horizontal strip, radial menu, status badge strip, mini picker.
2. Choose workflow context: Modeling, Rigging, Animation, FX, Rendering, or Custom.
3. Choose placement: active viewport edge/corner, hotbox-zone-inspired direction, or docked panel.
4. Add controls from built-in action groups: transform, selection, keying, playback, camera, display, rig picker.
5. Pick icons from a local icon library or type short labels like `M`, `R`, `S`, `K`.
6. Preview immediately in the active viewport.
7. Save as a preset and optionally create a shelf button, hotkey, or runtime command.

Add a **Command Capture** workflow:

- User clicks `Record Action`.
- User performs an operation in Maya.
- ActionRail inspects the Script Editor/history/runtime command where possible and proposes a binding.
- User can save the result as a reusable ActionRail action.
- If the capture is ambiguous, ActionRail stores a draft and asks the user to choose between detected MEL/Python/runtime-command candidates.

Add a **Live Edit Mode** separate from normal use:

- Normal mode: overlay controls are clickable; ActionRail avoids viewport-sized transparent hit areas so normal viewport interaction remains available outside visible controls.
- Edit mode: show anchors, hit boxes, spacing guides, safe margins, and drag handles.
- Test mode: controls execute in a temporary preset without writing user prefs.
- Publish mode: validates actions, icons, hotkeys, DPI assets, and missing dependencies before saving.

Add a **Bind Mode** for hotkeys:

- User enters Bind Mode from a shelf button, designer command, or hotkey.
- User hovers or selects an ActionRail slot and presses a shortcut.
- ActionRail detects conflicts, creates or updates a Maya runtime command/hotkey, and displays the key label on the slot.

Add **flyouts and command rings** for compact action groups:

- Flyout: a button opens a contextual list of related actions, such as keying tools, selection tools, camera bookmarks, or project scripts.
- Command ring: a radial menu opens from a click or press-and-hold hotkey and executes a wedge on release.
- Both reuse the same action registry and preset schema as normal bars.

Add **Maya-native launch targets**:

- Shelf button: toggles a palette or opens the designer.
- Hotkey press: show a palette while held.
- Hotkey release: hide it or commit a temporary mode.
- Runtime command: makes every palette/action visible to Maya's Hotkey Editor.
- Hotbox/marking-menu bridge: generate a Maya marking menu from the same action registry for users who prefer gestural access.

Add **preset layers**:

1. Built-in examples.
2. Studio locked presets.
3. Project presets.
4. Scene/asset presets where appropriate.
5. User overrides.

The designer should show which layer each palette came from and whether it is editable. This prevents a common DCC pipeline problem: users silently editing studio defaults.

Add **validation and recovery UX**:

- Broken action badge on controls with missing commands.
- Missing icon badge with fallback label.
- Hotkey conflict warning before assignment.
- Startup safe mode: hold a modifier or run `actionrail.safe_start()` to disable all overlays if one breaks Maya startup.
- Diagnostics panel: active overlays, callbacks, object names, model panel parents, preset source, icon source, and last errors.

Add **visual review workflow**:

- `Capture Reference` button in the designer.
- Side-by-side before/after screenshot panel for a preset.
- Screenshot filenames include preset id, Maya version, DPI, viewport size, and theme.
- Use this in reviews before accepting new built-in themes or templates.

### Agent/Developer Workflow Changes

Add repeatable scripts early:

- `scripts/docs-list.ps1`: lists docs by `summary` and `read_when`.
- `scripts/maya-smoke.ps1`: starts Maya/mayapy with the module path and runs import/show/hide smoke tests.
- `scripts/import-icons.ps1`: imports SVGs, writes PNG fallbacks, updates `icons/manifest.json`.
- `scripts/package-module.ps1`: builds a clean Maya module folder.
- `scripts/capture-ui.ps1`: triggers a known example and captures a reference screenshot where possible.

Add explicit architecture gates:

- Gate 1: PySide overlay prototype reviewed before building designer.
- Gate 2: action registry and command capture reviewed before user presets.
- Gate 3: icon import/licensing reviewed before shipping icon packs.
- Gate 4: Viewport 2.0 backend reviewed separately from Qt overlay.

Use Oracle or an equivalent second-model review for those gates, but only with selected files and a concrete question. Do not use broad "review everything" prompts.

### Updated UX North Star

ActionRail should let a Maya user make a polished tool palette in under five minutes:

1. Pick a template.
2. Record or choose commands.
3. Pick icons/labels.
4. Place it in the viewport.
5. Test it safely.
6. Publish to shelf/hotkey/preset.

The advanced designer and Python API can be deeper, but the first-run path must be this short.

## Target Architecture

```text
actionrail/
  bootstrap/
    install shelf/hotkey/menu entry points
    locate Maya main window and model panels
  runtime/
    session lifecycle, callback cleanup, logging
    central registry of overlays, panels, specs, actions
  overlay/
    ViewportOverlayHost anchored from modelPanel widgets
    small MayaWindow-owned rail windows, resize tracking, input isolation
  widgets/
    Button, ToggleButton, ToolStack, Separator, Badge, Slider, PieMenu
    all styled by theme tokens, not per-widget ad hoc CSS
  theme/
    tokens.json, QSS compiler, icon registry, density presets
  actions/
    Maya command registry, undo wrappers, context switching, hotkey integration
  state/
    current tool, selection, time, playback, active panel, active camera
    callbacks and scriptJobs normalized into signals
  spec/
    Python API and JSON/YAML schema for declarative UI definitions
  designer/
    dockable editor for building palettes and binding actions
  backends/
    qt_overlay backend for clickable UI
    vp2_draw backend for non-widget viewport drawing
    maya_cmds backend for simple shelf/native controls
  packaging/
    .mod template, install scripts, examples, icons
  tests/
    pure Python spec tests
    Maya smoke tests
    screenshot/visual regression tests where practical
```

## Runtime Model

The framework should treat UI definitions as data, then mount them into a backend:

```python
from actionrail import ui

palette = ui.palette(
    id="transform_stack",
    anchor="viewport.left.center",
    offset=(28, 0),
    theme="maya_dark_compact",
)

palette.tool_button("M", action="maya.tool.move", active_when="tool == move")
palette.tool_button("T", action="maya.tool.translate", active_when="tool == translate")
palette.tool_button("R", action="maya.tool.rotate", active_when="tool == rotate")
palette.tool_button("S", action="maya.tool.scale", active_when="tool == scale", tone="pink")
palette.spacer(14)
palette.button("K", action="maya.anim.set_key", tone="teal")

palette.show()
```

The same spec should also be serializable for non-programmers:

```json
{
  "id": "transform_stack",
  "anchor": "viewport.left.center",
  "offset": [28, 0],
  "theme": "maya_dark_compact",
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

## Key Components

### 1. Overlay Host

Responsibilities:

- Find the active model panel and its Qt widget.
- Resolve model-panel viewport geometry for anchors.
- Create small frameless Maya-owned rail windows positioned over the viewport.
- Reposition on viewport resize, panel change, workspace switch, DPI change, and full-screen changes.
- Avoid viewport-sized transparent hit areas; only visible ActionRail controls should receive input.
- Clean up all widgets and callbacks on reload/unload.

Implementation notes:

- Use `QApplication.instance()`.
- Use Maya's Qt parent hierarchy via `MQtUtil` where necessary.
- Use stable `objectName()` values for all root widgets.
- Keep hard references to widgets in a registry so Python GC does not destroy them.
- Default to PySide6, with a small import compatibility shim for PySide2 if Maya 2024 support is required.

### 2. Widget Kit

MVP widgets:

- `ToolStack`: vertical or horizontal grouped controls, matching the reference images.
- `ToolButton`: square fixed-size button with label/icon, active state, disabled state, tooltip, context menu.
- `ActionButton`: normal command button, e.g. `K` set key.
- `Separator`/`Spacer`: visual grouping.
- `Badge`: small state indicators.
- `MiniSlider`: compact numeric scrub control for animator-friendly values.
- `RadialMenu`: optional later control for marking-menu style workflows.

The widget kit should enforce stable dimensions. Hover, active, pressed, and disabled states must not shift layout.

### 3. Theme System

Use design tokens as the source of truth:

```json
{
  "colors": {
    "panel": "#3f4044",
    "panelBorder": "#2e3033",
    "button": "#62636d",
    "buttonHover": "#70717a",
    "buttonActivePink": "#d875c8",
    "buttonAccentTeal": "#20b9a8",
    "text": "#d9d9df"
  },
  "sizes": {
    "button": 32,
    "gap": 4,
    "radius": 2,
    "border": 2
  }
}
```

Compile tokens to QSS for Qt widgets. Avoid one-off per-button styles except through semantic roles such as `active`, `accent`, `warning`, `muted`.

### 4. Easy Authoring And Assets

The framework should support three authoring levels:

1. **Preset-first**
   - User starts with templates: vertical stack, horizontal toolbar, radial menu, status strip, mini inspector.
   - They change labels/icons/actions/colors in the ActionRail Designer.

2. **Data-first**
   - UI is stored in JSON/YAML specs.
   - Artists can share presets without editing Python.
   - TDs can review diffs and keep studio presets in source control.

3. **Code-first**
   - Python API for TDs who want dynamic behavior, custom predicates, and generated palettes.

Recommended asset pipeline:

- Use SVG as source assets for icons.
- Normalize icons on import: fixed viewBox, no scripts, no external resources, monotone `currentColor` where possible.
- Store imported icons under `icons/` and track source, license, and original URL in `icons/manifest.json`.
- Generate PNG fallbacks at 1x/2x/3x for Maya installs where SVG rendering is incomplete or inconsistent.
- Recolor icons through theme tokens, not separate duplicated files.
- Prefer one or two consistent icon families per UI so the result does not look stitched together.

Useful icon sources:

- Lucide: clean stroke icons, ISC license.
- Tabler Icons: large MIT-licensed SVG set.
- Google Material Symbols: broad Apache 2.0 set; better for common app/action concepts than bespoke DCC tools.
- Iconify can be used as a search/import service, but each underlying icon set has its own license, so the importer must store per-icon attribution/license metadata.

Recommended web-tool usage:

- Good: Figma/Illustrator/Inkscape/SVG editors for designing icons and mockups, Iconify or icon-pack websites for discovery, local SVG import into ActionRail.
- Good: optional web-based preset/icon browser during development if it exports static JSON/SVG.
- Risky for core runtime: live CDN icons, remote web pages, online JS bundles, or WebEngine-only controls inside the viewport.
- Acceptable later: an optional `QWebEngineView` designer panel if `PySide6.QtWebEngineWidgets` imports successfully in the target Maya version.

### 5. Action Registry

Actions should be registered once, then reused by Python API, JSON specs, hotkeys, shelves, and designer UI.

Action types:

- Maya tool switch: move/rotate/scale/select.
- Maya commands: `cmds.setKeyframe`, playback, isolate select, framing, marking menu entry points.
- MEL commands.
- Python callables.
- Named commands/hotkeys.
- Custom contexts.
- Toggle actions with `is_checked` state.
- Long-running actions with busy/disabled state.

Action features:

- Undo chunk wrapper.
- Error reporting to Maya script editor and optional toast.
- Command repeatability where applicable.
- Context-aware enabled/visible state.
- Optional command palette search.

### 6. State Observers

Normalize Maya state into a small reactive store:

- Current tool/context.
- Active model panel and camera.
- Selection count/type.
- Timeline frame, playback state, auto-key state.
- Modifier keys and focus.
- Workspace/control visibility.
- Custom user variables.

The UI binds to state with simple expressions or Python predicates. Example: a scale button is active when the current context is the scale tool. A set-key button changes accent if selected channels are keyable.

### 7. Designer

Provide a dockable `ActionRail Designer` for non-coders:

- Choose template: tool stack, floating toolbar, status strip, radial menu.
- Add buttons, spacers, sliders, badges.
- Pick command from registry or paste Python/MEL.
- Preview in a live viewport overlay.
- Save as user preset, project preset, or studio package.
- Export JSON spec.
- Validate missing actions/icons and show conflicts.

This designer should use a dockable workspace control, not the viewport overlay itself.

### 8. Viewport 2.0 Backend

Add after the Qt overlay MVP.

Use it for:

- Non-clickable labels and guides.
- Visual guides tied to DAG objects.
- High-frequency viewport drawing.
- Drawing that should move through the Viewport 2.0 render pipeline.

Avoid using this backend for normal buttons at first. Interactive hit testing, selection, and tool state are expensive to rebuild compared with Qt widgets.

### 9. Packaging

Ship as a Maya module:

```text
ActionRail/
  ActionRail.mod
  scripts/
    actionrail/
  icons/
  plug-ins/
  presets/
  examples/
```

The `.mod` file should add `scripts` to `PYTHONPATH` and expose icons. Use version/platform conditions only when needed.

## User Workflow

### Coder Workflow

1. Install the module or add the source checkout to `MAYA_MODULE_PATH`.
2. In Maya, run `import actionrail; actionrail.show_example("transform_stack")`.
3. Create a Python UI spec using `actionrail.ui`.
4. Bind controls to registered Maya actions.
5. Run live reload while iterating.
6. Save the spec to a user or project preset.
7. Optionally add a shelf button or hotkey that toggles the overlay.
8. Run `scripts/maya-smoke.ps1` and capture a reference screenshot before sharing.

### Artist Workflow

1. Open `ActionRail Quick Create` from shelf/menu.
2. Pick `Vertical Tool Stack`.
3. Choose context: Modeling, Rigging, Animation, FX, Rendering, or Custom.
4. Add buttons `M`, `T`, `R`, `S`, and `K`.
5. Assign actions from a searchable list or use `Record Action`.
6. Pick icons or short labels, then choose a compact dark theme and accent colors.
7. Preview in the active viewport and switch to Edit Mode only for placement/spacing.
8. Run validation for missing actions, icons, and hotkey conflicts.
9. Save as `Transform Stack`.
10. Publish to shelf, hotkey, runtime command, or shared preset.

### Studio Workflow

1. TD creates shared action registry and approved themes.
2. TD imports approved icon packs and locks source/license metadata.
3. Artists build or request palette presets.
4. Presets are stored in built-in, studio, project, scene, or user layers.
5. Versioned `.mod` deployment controls compatibility per Maya version.
6. CI or a smoke-test Maya session validates import, examples, icon assets, and no callback leaks.
7. Visual review compares screenshots before accepting built-in presets or theme changes.

## Tools To Add

MVP:

1. `actionrail.reload()` for fast iteration.
2. `actionrail.show_example("transform_stack")`.
3. Viewport overlay host with anchors and input hit testing.
4. `ToolStack`, `ToolButton`, `ActionButton`, `Spacer`.
5. Theme token loader and QSS compiler.
6. Action registry with built-in Maya transform/keyframe actions.
7. State observer for current tool and selection.
8. Shelf/menu installer to toggle examples.
9. JSON spec loader/saver.
10. SVG icon loader with PNG fallback.
11. Icon manifest with license/source metadata.
12. Quick Create wizard for template-first palette creation.
13. Live Edit Mode with anchors, hit boxes, spacing guides, and safe margins.
14. Publish targets for shelf button, hotkey, runtime command, and preset.
15. Validation panel for missing actions, icons, hotkey conflicts, and unsafe startup state.
16. Basic error console/logging.

Next:

1. Designer dockable panel.
2. User preset browser.
3. Hotkey registration helper.
4. Icon browser and SVG/PNG asset pipeline.
5. Visual screenshot testing in Maya.
6. Viewport 2.0 draw backend.
7. Custom context helper for drag tools.
8. Radial/marking-menu widget.
9. Project/studio preset layering.
10. Command Capture from Script Editor/runtime-command history.
11. Maya marking-menu export from the ActionRail action registry.
12. Telemetry-free diagnostics panel for callbacks, widgets, and orphan cleanup.

## Implementation Phases

### Phase 0 - Prototype

Goal: prove the reference UI can be recreated as a clickable Qt rail overlay in Maya.

Deliverables:

- PySide import shim.
- Main-window/model-panel widget discovery.
- Qt overlay host anchored to model-panel geometry.
- Hard-coded `M/T/R/S + K` stack.
- Tool switching and set-key command.
- Active-state polling or minimal callbacks.
- Manual screenshot capture of the reference example.

Exit criteria:

- Overlay appears in the active viewport.
- Buttons are clickable without blocking viewport navigation outside button bounds.
- It survives panel resize and workspace switching.

### Phase 1 - MVP Framework

Goal: make the prototype declarative and reusable.

Deliverables:

- Python API.
- JSON spec loader.
- Theme tokens.
- Action registry.
- Built-in transform/key actions.
- Shelf toggle.
- Quick Create wizard.
- Validation panel.
- Module package.

Exit criteria:

- A user can create the reference UI without editing core framework code.
- Reloading does not leave duplicate widgets or callbacks.
- Works in Maya 2025/2026 on Windows.
- Palette can be published to shelf/hotkey/runtime command.

### Phase 2 - Designer

Goal: allow non-coders to create palettes.

Deliverables:

- Dockable workspace-control designer.
- Live preview.
- Save/load presets.
- Action picker.
- Theme picker.

Exit criteria:

- Artist can build and save the reference stack from Maya UI only.

### Phase 3 - Advanced Backends

Goal: support viewport-native graphics and custom manipulation tools.

Deliverables:

- `MUIDrawManager` backend for labels/guides.
- Custom context/dragger helper.
- Optional object-bound overlay specs.
- Visual test harness.

Exit criteria:

- Framework can mix Qt controls with Viewport 2.0 guides safely.

## Risks And Mitigations

| Risk | Why it matters | Mitigation |
|---|---|---|
| Overlay intercepts viewport input | Artists need normal tumble/pan/select behavior | Use small rail windows or precise hit regions; avoid viewport-sized transparent hit areas |
| Model panel widget discovery is fragile | Maya UI hierarchy changes across versions | Isolate in one adapter module; support active-panel remounting |
| PySide2/PySide6 split | Maya 2024 and 2025+ differ | Support PySide6 first; add import shim only if 2024 is required |
| High DPI sizing bugs | Qt6 high DPI is always on | Use device-independent sizes, test mixed scaling |
| Callback leaks on reload | Common Maya tool problem | Central callback registry with explicit `dispose()` |
| Workspace restore duplicates widgets | Maya restores dock/UI state | Stable object names, singleton registry, cleanup before create |
| Viewport draw backend overreach | Can become plugin-heavy quickly | Keep it optional until Qt overlay is proven |
| QML complexity | Qt Quick embedding can be brittle inside host apps | Do not use QML for MVP |

## Test Plan

Minimum manual tests:

- Launch Maya 2025/2026, import module, show example.
- Toggle overlay on/off 20 times, confirm no duplicate widgets.
- Resize viewport, switch layouts, maximize panel, restore layout.
- Test normal viewport navigation outside controls.
- Click each button and verify active state.
- Set key with selection and without selection.
- Change DPI scaling and restart Maya.
- Save/reopen workspace with overlay disabled and enabled.

Automated where practical:

- Pure Python tests for spec parsing, action registry, theme compilation.
- Maya batch or mayapy import tests for package availability.
- Interactive smoke test script inside Maya for show/hide/reload.
- Screenshot comparison for example UI at fixed viewport size.

## MVP Definition

The smallest useful product is:

- A module-installable package.
- A Python API and JSON spec format.
- A Qt rail overlay backend anchored to viewport/model-panel geometry.
- A compact dark theme matching the research images.
- `ToolStack` buttons with active/accent states.
- Built-in move/translate/rotate/scale/set-key actions.
- SVG icon support with PNG fallback and license manifest.
- Shelf toggle and live reload.

Do not build the designer, QML backend, or Viewport 2.0 backend until this MVP works reliably.

## Final Architecture Decision

Build **ActionRail as a PySide6-first Maya overlay framework** with a declarative spec, theme tokens, action registry, and state observer. Package it as a Maya module. Add Viewport 2.0 drawing later as a second backend, not as the foundation.

This matches the research images because the desired UI is fundamentally a polished, clickable, screen-space widget stack. Qt gives the fastest path to that result inside Maya, while Maya APIs remain responsible for tool execution, state, packaging, and later deep viewport integration.
