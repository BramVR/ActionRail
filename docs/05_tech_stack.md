---
summary: Current ActionRail tech stack decision and what to avoid for the Maya viewport UI framework.
read_when:
  - Choosing libraries or implementation patterns.
  - Starting Phase 0 implementation.
  - Considering web, Viewport 2.0, or overlay alternatives.
---

# Tech Stack

## Decision

Build ActionRail as:

```text
Python 3.11 in Maya
+ PySide6 / Qt Widgets
+ custom transparent viewport overlay
+ maya.cmds / OpenMayaUI / shiboken6
+ JSON specs and Python builder API
+ SVG icons with PNG fallbacks
+ Maya .mod packaging
+ MayaSessiond verification
```

## Core Runtime

- Use Maya's bundled Python and Qt. Maya 2026 is Python 3.11.4 with Qt/PySide6 6.5.3.
- Use `QApplication.instance()`. Never create a new `QApplication`.
- Parent widgets under Maya widgets and keep stable `objectName()` values.
- Use `maya.cmds` first. Use Maya API 2.0 only where `cmds` is not enough.
- Avoid PyMEL unless explicitly requested.

## UI Layer

- Use PySide6 / Qt Widgets for the MVP.
- Implement a custom transparent viewport overlay host.
- Use custom `QWidget`/`QPainter` controls for the compact stack when standard buttons fight the design.
- Use `QAction` concepts internally for reusable commands, even if widgets are custom-painted.
- Use QSS/theme tokens for consistent colors, spacing, radius, and states.
- Design for Qt6 High DPI from the first prototype.

## Maya Overlay Spike

Maya 2026 includes Autodesk's `moverlay` module for Qt-based 2D overlays over Maya UI.

Spike it early as a reference or adapter, but do not make it the core until it proves:

- viewport/model-panel anchoring works for ActionRail
- empty overlay space can pass through viewport input
- controls can own precise hit areas
- reload cleanup is reliable
- styling can match the reference UI

## Assets

- Use SVG as source icons.
- Cache PNG fallbacks at 1x/2x/3x when needed.
- Track icon source, license, original URL, and import date in `icons/manifest.json`.
- Preferred icon sources: Lucide, Tabler Icons, Google Material Symbols, and Iconify as a discovery/import source.
- Do not load live CDN icons at runtime.

## Web Tools

Use web tech for authoring and import workflows, not the core Maya runtime.

Good uses:

- Figma, Illustrator, Inkscape, or web icon browsers for design.
- Optional Node/TypeScript importer for Iconify JSON to local SVG.
- Optional local web preview that exports JSON/SVG.

Avoid in the MVP:

- React/Electron inside Maya.
- Required `QWebEngineView`.
- Remote web pages or online JavaScript bundles.
- CDN icons or runtime network dependencies.

`QWebEngineView` can be revisited later for a designer panel only after a runtime import probe confirms it is available and stable in the target Maya version.

## Viewport 2.0

Defer Viewport 2.0 until the Qt overlay MVP is stable.

Use it later for:

- non-clickable labels and guides
- object-bound viewport graphics
- high-frequency native drawing

Do not use it first for normal clickable buttons, menus, or designer UI. Interaction, hit testing, and layout are cheaper and safer in Qt.

## Packaging And Verification

- Ship as a Maya module: `ActionRail.mod`, `scripts/actionrail`, `icons`, `presets`, `examples`.
- Verify with `GG_MayaSessiond` when feasible.
- Add pure Python tests for specs, themes, icon manifests, and action registry code.
- Add Maya smoke tests for import/show/hide/reload once command shape stabilizes.
