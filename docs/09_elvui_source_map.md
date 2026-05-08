---
summary: Local source map for the ElvUI research checkout; helps agents find action bar, appearance, layout, profile, and options references without broad crawling.
read_when:
  - Using the local ElvUI source in research/ as an ActionRail design reference.
  - Looking for WoW-style action bar, Edit Mode, appearance, profile, or options patterns.
  - Comparing ActionRail authoring surfaces against ElvUI's runtime/options split.
---

# ElvUI Source Map

## Purpose

The local `research/` checkout contains ElvUI source used as a structure and UX
reference for ActionRail. Treat it as research material, not a runtime
dependency and not a feature-count target.

Current observed source version is `v15.13` from the `.toc` manifests. The
checkout is split into three WoW addon packages:

- `research/ElvUI`: main runtime addon, defaults, modules, layout/movers, media,
  and game-version-specific skins.
- `research/ElvUI_Libraries`: vendored libraries such as Ace3, oUF,
  LibActionButton, LibSharedMedia, LibSimpleSticky, and LibCustomGlow.
- `research/ElvUI_Options`: load-on-demand configuration UI for ElvUI.

`research/` is ignored by Git. Keep paths in docs as lookup hints and avoid
making committed ActionRail code depend on files in this folder.

## Load Order

Start from the manifests, then follow the XML loaders:

- `research/ElvUI/ElvUI_Mainline.toc`: main retail manifest. Other variants are
  `ElvUI_Vanilla.toc`, `ElvUI_TBC.toc`, `ElvUI_Wrath.toc`, and
  `ElvUI_Mists.toc`.
- `research/ElvUI/Game/load_mainline.xml`: retail runtime load order. It loads
  shared initialization/defaults/core code first, then shared modules, then
  retail-specific filters, tags, data texts, data bars, skins, and Blizzard UI
  adapters.
- `research/ElvUI/Game/load_classic.xml`, `load_tbc.xml`, `load_wrath.xml`, and
  `load_mists.xml`: variant-specific runtime load order.
- `research/ElvUI_Options/ElvUI_Options_Mainline.toc` and
  `research/ElvUI_Options/Game/load.xml`: options addon entry points.
- `research/ElvUI_Libraries/ElvUI_Libraries_Mainline.toc` and
  `research/ElvUI_Libraries/Game/load_mainline.xml`: library entry points.

When a behavior differs by game version, check `Game/Shared/` first, then the
matching `Game/Mainline/`, `Game/Classic/`, `Game/TBC/`, `Game/Wrath/`, or
`Game/Mists/` folder.

## Runtime Core

- `research/ElvUI/Game/Shared/General/Initialize.lua`: creates the global ElvUI
  engine tuple. The common import shape is `local E, L, V, P, G = unpack(ElvUI)`,
  where `E` is the engine, `L` localization, `V` private defaults, `P` profile
  defaults, and `G` global defaults. It also registers modules such as
  `ActionBars`, `Layout`, `Skins`, `Tooltip`, and `UnitFrames`.
- `research/ElvUI/Game/Shared/General/Core.lua`: central runtime setup,
  constants, screen metrics, shared tables, callbacks, profile initialization,
  and the `ElvUIParent` frame that other ElvUI UI anchors to.
- `research/ElvUI/Game/Shared/General/API.lua`: shared helper API and frame
  utility methods.
- `research/ElvUI/Game/Shared/General/Toolkit.lua`: common UI construction and
  styling helpers.
- `research/ElvUI/Game/Shared/General/Commands.lua`: slash command and command
  routing reference.
- `research/ElvUI/Game/Shared/General/Config.lua`: configuration-mode entry
  points, grid display, mover visibility, and options-window integration.

Use these files to understand ElvUI's architecture vocabulary before reading
individual modules.

## Defaults, Profiles, And Persistence

- `research/ElvUI/Game/Shared/Defaults/Profile.lua`: large profile-default tree.
  This is the main reference for option shape, action bar defaults, colors,
  fonts, backdrop values, movers, and module defaults.
- `research/ElvUI/Game/Shared/Defaults/Global.lua`: global defaults.
- `research/ElvUI/Game/Shared/Defaults/Private.lua`: private/per-character style
  defaults.
- `research/ElvUI/Game/Shared/General/Distributor.lua`: profile/import/export
  and distribution workflow reference.
- `research/ElvUI/Game/Shared/General/ModuleCopy.lua`: module-setting copy
  workflow reference.

ActionRail should keep the useful separation: global theme defaults first,
sparse per-frame/per-bar overrides second, with profile layers deferred until
the current authoring loop is stable.

## Layout, Movers, And Edit Mode References

- `research/ElvUI/Game/Shared/General/Movers.lua`: draggable mover frames,
  saved point strings, sticky movement, connected movers, combat-lockdown
  guards, coordinate display, and mover registration.
- `research/ElvUI/Game/Shared/General/Config.lua`: toggles configuration mode,
  grid visibility, and mover visibility groups such as `ALL`, `GENERAL`, and
  `ACTIONBARS`.
- `research/ElvUI/Game/Shared/Layout/Layout.lua`: layout application and
  top/bottom panel behavior.
- `research/ElvUI_Libraries/Game/Shared/LibSimpleSticky/LibSimpleSticky.lua`:
  sticky frame snapping used by movers.

For ActionRail, these are references for Edit Mode feel, snap behavior, and
stored anchor strings. Do not copy WoW combat-lockdown mechanics directly into
Maya; translate only the user-facing layout ideas that fit Qt overlays.

## Action Bars, Slots, And Binding

- `research/ElvUI/Game/Shared/Modules/ActionBars/ActionBars.lua`: main action
  bar module. Key references include `AB.barDefaults`, button counts, buttons
  per row, spacing, backdrop sizing, page/visibility conditions, range/usable
  coloring, button text, and update paths.
- `research/ElvUI/Game/Shared/Modules/ActionBars/Bind.lua`: keybinding mode
  workflow for hovering/clicking buttons and assigning bindings.
- `research/ElvUI/Game/Shared/Modules/ActionBars/PetBar.lua`: pet-action bar
  variant.
- `research/ElvUI/Game/Shared/Modules/ActionBars/StanceBar.lua`: stance/action
  state variant.
- `research/ElvUI/Game/Shared/Modules/ActionBars/MicroBar.lua`: compact system
  action bar reference.
- `research/ElvUI/Game/Shared/Modules/ActionBars/ExtraAB.lua`: extra action bar
  reference for special-case bars.
- `research/ElvUI_Libraries/Game/Shared/LibActionButton-1.0/LibActionButton-1.0.lua`:
  low-level action button library for cooldowns, charges, macro/item/spell
  payloads, usable state, range state, overlays, glows, flyouts, and callbacks.

For ActionRail, use these as references for action-slot concepts, visible
hotkey labels, binding mode shape, state-driven styling, and action-button
metadata. Keep Maya actions provider-backed through `actionrail.action_book`
instead of mirroring WoW action slots one-for-one.

## Appearance, Media, And Skinning

- `research/ElvUI/Game/Shared/Media/SharedMedia.lua`: registers fonts, sounds,
  textures, arrows, logos, icons, and status bar textures through LibSharedMedia.
- `research/ElvUI/Game/Shared/Media/`: bundled visual assets.
- `research/ElvUI/Game/Shared/Modules/Skins/Skins.lua`: skin module entry point.
- `research/ElvUI/Game/Shared/Modules/Skins/Ace3.lua`: skinning for Ace3 option
  widgets.
- `research/ElvUI/Game/Mainline/Skins/` and sibling game-version `Skins/`
  folders: Blizzard UI skin adapters.

For ActionRail, the relevant pattern is the split between global media/theme
defaults and module/bar-local options. ActionRail's current appearance scope is
smaller by design: theme id, sparse color overrides, backdrop settings, border
settings, and slot colors.

## Options Addon

`ElvUI_Options` is the best place to inspect user-facing option grouping. It is
load-on-demand and does not own profile data.

- `research/ElvUI_Options/Game/Shared/Core.lua`: options root setup.
- `research/ElvUI_Options/Game/Shared/General.lua`: general settings layout.
- `research/ElvUI_Options/Game/Shared/ActionBars.lua`: action bar options,
  including shared bar groups for button settings, backdrop settings, bar
  settings, strata/level, visibility state, paging, text display, colors, and
  apply-to-all workflows.
- `research/ElvUI_Options/Game/Shared/Skins.lua`: skin options grouping.
- `research/ElvUI_Options/Game/Shared/Search.lua`: options search reference.

ActionRail should borrow the grouping discipline, not the full option count.
Quick Create should stay compact; deeper global theme/profile/media tools can
come later.

## Other Module Areas

- `research/ElvUI/Game/Shared/Modules/DataTexts/`: small text-display modules.
  Useful reference for future viewport info frames.
- `research/ElvUI/Game/Shared/Modules/DataBars/`: progress/status bars. Useful
  reference for future state or progress frames.
- `research/ElvUI/Game/Shared/Modules/UnitFrames/`: complex frame composition
  and oUF integration. Useful as a distant reference for future object/selection
  frames, but too broad for the current ActionRail phase.
- `research/ElvUI/Game/Shared/Modules/Auras/`, `Nameplates/`, `Tooltip/`,
  `Bags/`, `Chat/`, `Maps/`, `Misc/`, and `Blizzard/`: module-specific
  references that are mostly outside the current ActionRail boundary.
- `research/ElvUI/Game/Shared/Tags/`: tag parsing/display logic. Useful only if
  ActionRail later needs declarative text expressions.
- `research/ElvUI/Game/Shared/Filters/`: filter lists and filter application
  patterns. Useful only if ActionRail later adds richer predicate/filter UI.

## Libraries To Know

- `AceAddon-3.0`: module lifecycle and addon composition.
- `AceConfig-3.0`, `AceConfigDialog-3.0`, `AceGUI-3.0`: options schema and UI.
- `LibActionButton-1.0`: action button behavior.
- `LibSharedMedia-3.0`: named fonts/textures/sounds registry.
- `LibSimpleSticky`: sticky mover snapping.
- `LibCustomGlow-1.0`: glow/active-highlight effects.
- `oUF` and `oUF_Plugins`: unit frame framework and plugins.
- `LibElvUIPlugin-1.0`: plugin extension integration.

These are architectural references only. ActionRail remains Python/PySide6 for
Maya and should use its own declarative presets, Qt widgets, and Maya command
providers.

## Search Recipes

Use targeted searches instead of broad crawling:

```powershell
rg -n "barDefaults|buttonsPerRow|backdropSpacing" research\ElvUI\Game\Shared\Modules\ActionBars
rg -n "ActivateBindMode|Keybind|SetBinding" research\ElvUI\Game\Shared\Modules\ActionBars research\ElvUI_Options\Game\Shared
rg -n "CreateMover|ToggleMoveMode|stickyFrames|snap" research\ElvUI\Game\Shared\General research\ElvUI_Libraries\Game\Shared\LibSimpleSticky
rg -n "SharedBarOptions|Backdrop Settings|Button Settings|Visibility State" research\ElvUI_Options\Game\Shared\ActionBars.lua
rg -n "backdropcolor|bordercolor|valuecolor|actionbar" research\ElvUI\Game\Shared\Defaults\Profile.lua
rg -n "LibSharedMedia|AddMedia|LSM:Register" research\ElvUI\Game\Shared\Media research\ElvUI_Libraries
```

## ActionRail Translation Notes

- Use ElvUI for workflow structure: frames, action bars, editable movers,
  grouped options, profile separation, media/theme defaults, and bind mode.
- Keep current ActionRail phase boundaries: do not start Bind Mode, Macro Book
  UI, flyouts, command rings, profile layers, marking-menu export, or Viewport
  2.0 from this reference alone.
- Prefer ActionRail terms in committed docs and code: frames, action bar frames,
  slots, Action Book, Macro Book, Edit Mode, Bind Mode, presets, and sparse
  appearance overrides.
- Translate WoW-specific Lua/Ace/secure-frame patterns into Maya/PySide6
  concepts only when they solve a current ActionRail problem.
