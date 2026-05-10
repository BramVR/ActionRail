---
summary: Live project status for agents: what is done, what is next, blockers, latest handoff, and latest verification.
read_when:
  - Starting work after another agent.
  - Finishing any implementation or research slice.
  - Checking current blockers before editing code.
---

# Status

Last updated: 2026-05-10

## Current Snapshot

ActionRail has a verified declarative MVP and Phase 2 authoring foundation
through Quick Create preview/save/load, Edit Mode layout-map/direct
manipulation controls, user preset saves, built-in layout override saves, and
studio layout override saves. Phase 2 step 2.6 is now in progress with the
first collapsible edge-tab schema/runtime slice implemented and Maya-smoke
verified, a Maya-smoke verified handle/publish polish pass, and a locally
verified validation UX/saved-preset publish follow-up with Quick Create Maya
smoke coverage for the custom-store Save + Publish shelf command path. Phase 2
step 2.7 dense overlay performance foundation is implemented: shared Maya
state, one predicate refresh scheduler, cached predicate dependencies, a
custom-painted dense action bar path, dirty-slot repainting for simple state
changes, and viewport navigation pass-through so large WoW-style layouts stay
usable over Maya. The latest performance hardening removes repeated per-slot
Maya icon resource checks, reuses dense icon/pixmap objects during paint, and
samples only predicate-needed Maya state on refresh ticks. The latest viewport
redraw fix installs one shared Maya selection-change callback while overlays
are visible and defers `cmds.refresh(currentView=True, force=True)` so mesh
selection highlighting appears immediately in the README-style scene instead
of waiting for a camera move. The
latest local cleanup keeps Edit Mode layout-only by removing the frame options
popover and moving slot payload editing to Normal Mode rail lock/unlock
helpers, including Shift-drag move/swap/clear-out for populated unlocked slots.
The latest Edit Mode panel polish turns the selected rail state into a
clickable Lock/Unlock action and makes the compact panel draggable so it can be
moved away from rails underneath it. The latest Edit Mode color polish follows
the local ElvUI mover reference by replacing the bright blue grid with black
grid lines and using ActionRail's green accent for selected frames, selected
labels, Sticky Frames guides, and panel check controls. The latest Normal Mode
slot-edit fix lets
Shift-drag transfer or swap payloads between different unlocked rails without
clearing the source when the target rail is locked. The newest follow-up keeps
that cross-rail drop path stable after rail rebuilds by resolving stale Qt
slot-button callback snapshots against the live target host unlock state.
The latest Quick Create workflow bridge makes previews unlocked by default for
Action Book placement and replaces the old Edit Slots handoff wording with a
simple Lock Bar/Unlock Bar toggle. Locking the bar returns populated slot
clicks to normal action execution. The Quick Create command buttons are split
into edit-flow and save-flow rows so labels remain readable in Maya. The newest
Quick Create UX pass makes blank action bars the default and removes
Action/Icon assignment controls from the Slots tab so Quick Create stays
focused on creating bars and slots; the separate future Action Book owns action
browsing and placement. Blank action-bar sockets now use key labels for their
visible slot numbers, Action Book drops leave the primary slot label empty by
default, and labels remain an explicit optional slot field. The first Action
Book UI slice is now implemented as a
separate dockable Maya panel with search,
icon-backed action entries, click-to-run behavior, and drag/drop placement onto
unlocked action-bar slots. The latest placement fix keeps those dropped live
payloads when Quick Create Lock Bar rebuilds the preview, so assigned icons
stay visible after returning a bar to normal click-to-run mode. The latest
theme pass doubles the central diagonal stripe width on action bars and Action
Book pages; action bars now keep an opaque `rgb(29, 32, 42)` base and opaque
`rgb(45, 47, 60)` hard-stop diagonal stripes so the rail background does not
become transparent. Action-bar clusters now paint that striped bar in widget
pixels instead of relying on a stretched Qt stylesheet gradient, so the stripe
angle continues consistently behind centered buttons; the painted stripes are
now thinner and denser. README icon rendering now uses SVG-backed Maya
resources where Maya exposes true vector equivalents and requests scaled
pixmaps during high-resolution widget captures; transform-tool Maya resources
still top out at 32 px in Maya's own resource catalog. Spell icons now share a
dark tile backplate in both the Action Book and dropped action-bar slots, and
icon-bearing action-bar slots no longer paint the underlying push-button skin,
so active borders align to the tile while the striped rail stays visible around
populated slots. The latest slot-layering polish groups contiguous one-row and
one-column button slots into a single painted rail backing, removes the extra
icon backplate inset so placed icons fill their sockets more closely, and keeps
per-bar icon backplate/border colors on the custom painter. The latest
ElvUI-reference pass adds sparse per-bar `appearance` overrides for
theme/accent/text, backdrop pattern/color, border, and slot colors. Quick
Create now exposes those settings in a compact Appearance tab grouped as Theme,
Backdrop Settings, Border Settings, and Slot Colors; the settings preview live
and round-trip through saved/loaded user presets.

Architecture direction is now explicitly WoW-style frames. Current rails are
implemented action bar frames, not the whole product boundary. The planned
authoring loop is: choose a frame/template, place Maya actions or macros from
an Action Book/Macro Book onto slots, use Edit Mode for frame layout, use Bind
Mode for hover/click-to-bind hotkeys, then save. Runtime-command and shelf
publishing remain implementation plumbing for bindings and optional Maya
integration rather than the primary artist-facing workflow. The first Action
Book backend slice is now implemented: `actionrail.action_book` exposes
category/icon/keyword metadata for registered Maya actions, Quick Create uses
that catalog for action picker choices, and Toggle Grid is now Maya-smoke
verified as the first non-transform viewport action in the catalog. The latest
Action Book backend expansion adds Select, Clear Selection, and Frame Selection
as Maya-smoke verified entries and saves a catalog JSON artifact for review.
The newest Action Book starter-set pass adds Toggle Isolate Selected, Center
Pivot, Freeze Transforms, and Delete History, bringing the smoke-verified
catalog to 13 entries. Do not keep expanding the catalog one item at a time in
Phase 2.6; move the next work back to workflow-level architecture.

Working surface:

- JSON presets and Python builder API for viewport rails.
- Built-in presets: `transform_stack`, `horizontal_tools`, and `maya_tools`.
- Qt overlay lifecycle, model-panel anchoring, shared predicate refresh
  scheduling, reusable Maya actions, and runtime-command hotkey publishing.
- Dense locked action bars above the large-layout threshold now render as one
  custom-painted Qt canvas with cached slot rects/state, dirty-slot repainting,
  and Alt/middle/right/wheel viewport navigation pass-through.
- Public slot binding-target metadata through `actionrail.slot_binding_targets()`,
  including slot ids, labels, key labels, runtime commands, and Maya
  nameCommands for saved bars.
- Action Book backend metadata for registered Maya actions, currently consumed
  by Quick Create picker choices, including the Maya-smoke verified
  `maya.display.toggle_grid` viewport action and the Maya-smoke verified
  `maya.tool.select`, `maya.selection.clear`, and
  `maya.view.frame_selection` selection/viewport entries. The current
  starter set also includes Maya-smoke verified `maya.view.toggle_isolate_selected`,
  `maya.modeling.center_pivot`, `maya.modeling.freeze_transforms`, and
  `maya.modeling.delete_history`.
- Dockable Action Book panel opened from the ActionRail menu through
  `actionrail.show_action_book_panel()`. It searches the Action Book catalog,
  renders each entry with its slot icon and tooltip summary, executes clicked
  entries for immediate feedback, and drags Action Book MIME payloads onto
  unlocked Normal Mode slots.
- Safe diagnostics, diagnostic badges, diagnostics Qt window, icon import
  preflight, generated SVG PNG fallbacks, and fallback preset recovery.
- User preset storage and shared bundled/user preset resolver.
- Maya menu and shelf entry points, including diagnostics, SVG import
  diagnostics, Quick Create, and Toggle Edit Mode.
- Dockable Quick Create panel with template selection, preview, clear preview,
  save, overwrite, custom user preset store support, custom action/icon id
  preservation, load-existing user preset workflow, live preview refresh for
  layout sliders, and generated blank slots when the button-count control is
  raised beyond the template's icon-backed slots. Quick Create now also has an
  Edit Layout handoff that previews the current draft, enters Edit Mode, and
  selects the draft frame. Quick Create defaults to a blank action bar and its
  Slots tab edits only slot id, label, and displayed key text. Starter
  templates still include the original vertical stack, horizontal strip,
  edge-tab rail, and a viewport display strip seeded with Toggle Grid, but
  Quick Create should not become the action browser. A read-only Bindings tab lists
  action-bearing slots, key labels, and Maya Hotkey Editor nameCommands for the
  current draft. Previews open unlocked for Normal Mode slot editing and the
  Lock Bar/Unlock Bar toggle switches the current preview between placement and
  normal action execution.
- Edit Mode shell with layout-map overlay, grid controls, Snap to Grid, Sticky
  Frames, active rail frames, selection, direct frame dragging,
  snap/spacing guides, axis-aligned sticky alignment guides, X/Y movement for
  unlocked rails, a clickable selected-rail Lock/Unlock panel action,
  draggable compact panel placement, safe movement clamps,
  Save Position/user-preset persistence for unlocked runtime/user rails, and
  user override saves/resolution for unlocked built-in and studio rails. Edit
  Mode no longer opens the right-click frame options window and no longer edits
  slot payloads.
- Normal Mode active rails can be unlocked and locked for slot payload editing;
  while unlocked, rendered slot context menus can assign or clear payloads, and
  Shift-drag moves a populated slot payload to another slot, swaps with a
  populated target, transfers between unlocked rails, or clears when released
  outside ActionRail. Locking the rail returns populated slot clicks to normal
  action execution.
- Optional collapsible rail schema/runtime: JSON `collapse` settings for edge,
  handle icon, reveal trigger, and default collapsed state; Quick Create
  edge-tab defaults/settings; collapsed handle-only Qt overlays; click/hover
  reveal hooks; and user-preset persistence.
- Optional per-bar appearance schema/runtime: JSON `appearance` settings for
  theme id, global inheritance, accent/text overrides, backdrop enable/color/
  pattern/opacity/scale, border enable/color/width, and slot color overrides.
  Widgets resolve these sparse settings through `actionrail.theme` before
  painting, so global defaults and bar-local overrides stay separate.
- Collapsed edge handles now use larger hit targets, hug the configured
  viewport edge, preserve only tangent layout offset while collapsed, and clamp
  inside the viewport.
- Quick Create saves now run publish-facing diagnostics before writing; saved
  presets can optionally publish slot runtime commands and an idempotent preset
  shelf toggle through the Save + Publish path. Validate Draft now surfaces
  publish diagnostics before save, blocked saves include the concrete
  diagnostic issue, Save + Publish reports stale slot-command cleanup, and
  published shelf toggles preserve custom user preset stores.
- Quick Create draft conversion now infers `active_when` predicates for
  persistent Maya tool actions (`move`, `translate`, `rotate`, and `scale`) so
  saved Quick Create rails show active tool styling; one-shot actions remain
  inactive unless a slot has an explicit custom predicate.

Long-form implementation and verification history belongs in
`docs/history/verification_log.md`.

## Current Plan

`docs/02_implementation_plan.md` is the source of truth for phase completion
and next work. Phase 2 step 2.5 Layout Editing And Direct Manipulation is done;
Phase 2 step 2.6 collapsible edge tabs and authoring workflow polish is in
progress.
Local `.spec/` reports are ignored and not part of the Git-tracked handoff.

Focus the next slice on:

- keeping the fixed Quick Create round-trip and preset discovery paths stable
- keeping the Quick Create Appearance tab stable across preview, save, load,
  and existing-preset editing
- keeping locked built-in/studio presets read-only
- making the template-to-Edit-Mode and Normal Mode slot-edit handoff feel like
  one workflow that now connects to the first Action Book action-placement slice
  and can later connect to Bind Mode
- keeping the Normal Mode unlocked-slot drag/drop workflow stable: Shift-drag
  moves/swaps populated slot payloads within a rail, transfers/swaps between
  unlocked rails, and preserves the source when dropped onto a locked rail
- hardening the Phase 2 step 2.7 dense overlay performance foundation before
  later modes: shared Maya state, one refresh scheduler, cached predicates, a
  custom-painted dense bar prototype, dirty-slot repainting, and Maya viewport
  navigation pass-through

Do not implement Bind Mode, Macro Book UI, flyouts, command rings, profile
layers, marking-menu export, or Viewport 2.0 before the performance foundation.
Keep Action Book growth focused on action placement and search, not on turning
Quick Create into an action browser.

## Next Agent Start

1. Read `../bram-agent-scripts/AGENTS.MD`, then `docs/00_start_here.md`, then this file.
2. Run the project map if ownership or test routing is unclear:

```powershell
$env:PYTHONPATH = "scripts"
.\.venv\Scripts\python.exe -m actionrail --json
```

3. Finish any necessary Phase 2 step 2.6 polish on top of the completed Phase
   2 step 2.5 Edit Mode layout editing surface. The collapse schema/runtime
   first pass is in place and Maya-smoke verified; the handle/publish polish
   pass is also Maya-smoke verified; the validation UX/publish follow-up is
   locally verified, and Quick Create Maya smoke covers the custom-store Save +
   Publish shelf command path. Edit Mode slot-payload controls have since moved
   out of Edit Mode and into Normal Mode rail lock/unlock helpers. Treat
   publishing as optional infrastructure; keep the main UX vocabulary aligned
   to frames, Action Book, Macro Book, Edit Mode, and Bind Mode.
4. Harden Phase 2 step 2.7: keep the 100+ slot dense overlay probe, shared Maya
   state service, one refresh scheduler, cached predicates, custom-painted bar
   prototype, dirty-slot repainting, and viewport navigation pass-through green
   before starting later authoring modes.
5. Use `scripts/maya-smoke.ps1` for repeatable MayaSessiond smoke runs when feasible.

## Latest Handoff

- Phase 2 step 2.4 Edit Mode shell and rail selection is implemented and Maya
  screenshot verified.
- Quick Create can preview/save/load user presets.
- Edit Mode can inspect active rails, select frames, show grid/snap/sticky
  controls, and move unlocked rails in-session without opening a frame options
  popover.
- Edit Mode can save adjusted unlocked runtime/user rail specs and unlocked
  built-in/studio user override presets through `save_edit_mode_layout()` and
  the right-click Save Position control.
- The shared preset resolver now applies saved built-in `*_user_override`
  sidecars when loading the original built-in preset id, while leaving broken
  override files as user-preset diagnostics instead of blocking bundled loads.
- The shared preset resolver also supports optional read-only studio preset
  discovery through `ACTIONRAIL_STUDIO_PRESET_DIR` or `PresetStore(...,
  studio_preset_dir=...)`, with `*_user_override` sidecars applied when loading
  the original studio preset id.
- Safe startup keeps diagnostically bad built-in/studio user override sidecars
  on the user-preset warning path and starts the read-only preset instead.
- The May 5 audit items are fixed in focused conventional commits through
  `feat(edit-mode): add direct manipulation controls`, the diagnostics
  follow-up, and the status/changelog hygiene updates.
- The May 6 handle/publish polish pass enlarges and edge-clamps collapsed
  handles, adds `diagnose_publish_spec()`, blocks Quick Create saves with
  diagnostic errors, records warning diagnostics for publish review, and adds
  optional slot runtime-command plus shelf-toggle publishing from Quick Create.
- The May 6 validation UX/publish follow-up routes Quick Create Validate Draft
  through publish diagnostics, includes concrete diagnostic details in blocked
  save errors, reports stale slot-command cleanup from Save + Publish, and
  preserves custom user preset stores in published preset shelf toggles.
- Quick Create Preview now stays live while visible: the Buttons slider grows
  or trims slot rows, extra generated slots are blank/no-icon after the
  template's icon-backed slots, and Buttons Per Row/Button Size/offset/alpha
  changes refresh the active viewport preview immediately.
- Quick Create now fills blank `active_when` values for known persistent Maya
  tool actions during draft conversion, so newly saved Move/Rotate/Scale tool
  slots reflect Maya's active tool context without marking one-shot commands
  like Set Key active.
- The May 6 Edit Mode cleanup removes the frame options popover and the
  Edit Mode slot payload surface. Slot payload assignment/clear now belongs to
  Normal Mode rail lock/unlock helpers, while Edit Mode keeps the
  axis-aligned Sticky Frames layout guides.
- Normal Mode unlocked-slot editing supports context-menu assignment/clear plus
  Shift-drag payload move/swap/clear-out gestures, including cross-rail
  transfers between unlocked rails.
- The latest May 7 follow-up fixes a MayaSessiond-only cross-rail Shift-drag
  failure after a same-rail payload move rebuilt the source rail; target slot
  callbacks now use the live target host lock state instead of stale Qt button
  snapshots.
- The May 7 Edit Mode panel polish changes the selected rail button from a
  passive Locked/Unlocked label to a clickable Lock/Unlock action and lets the
  compact panel be dragged aside when it covers a rail.
- The May 7 architecture docs update reframes ActionRail around WoW-style
  frames, action bar frames, Action Book, Macro Book, and Bind Mode so future
  info frames, object frames, and macro workflows fit without making rails the
  only top-level product primitive.
- The first Action Book implementation slice adds `actionrail.action_book` and
  routes Quick Create action choices through picker-facing action metadata.
- The latest Action Book follow-up adds `maya.display.toggle_grid` with
  `maya.grid` metadata and a Maya smoke that verifies it toggles the real Maya
  viewport grid off and back on.
- The newest Action Book backend follow-up adds Select, Clear Selection, and
  Frame Selection entries and saves the smoke-tested Action Book catalog to
  `.gg-maya-sessiond/screenshots/actionrail_action_book_catalog.json` for
  backend review; the first Action Book UI now renders the catalog for placement.
- The newest Action Book starter-set follow-up adds Toggle Isolate Selected,
  Center Pivot, Freeze Transforms, and Delete History, and verifies all four
  against real Maya commands. Treat that as enough backend catalog expansion for
  now and move on to the next workflow-level slice.
- Quick Create now offers two broader starter templates: Blank Bar for empty
  action sockets and Viewport Display Strip seeded with the Toggle Grid Action
  Book entry.
- Blank action-bar sockets use their key labels for the visible slot numbers,
  and placing an Action Book entry onto a slot no longer turns the action name
  into a primary slot label by default.
- Public hotkey workflow metadata now exposes saved-bar binding targets through
  `actionrail.slot_binding_targets()`, so current Maya Hotkey Editor use and
  future Bind Mode can work from visible slots instead of raw command naming.
- Quick Create now surfaces those binding targets in a read-only Bindings tab,
  keeping hotkey prep attached to the create -> edit layout -> save/publish
  workflow without implementing full Bind Mode.
- Quick Create Edit Layout now connects the builder to Edit Mode by previewing
  the current draft and selecting it in the layout-map overlay.
- Quick Create previews now connect the builder to Normal Mode slot editing by
  opening unlocked for context-menu assignment/clear, Shift-drag rearrangement,
  and Action Book drops. Lock Bar switches the preview back to normal
  click-to-run behavior.
- Quick Create now opens on a blank action bar and the Slots tab no longer
  exposes Action/Icon assignment controls. It edits slot id, label, and key text
  only, preserving existing payload metadata internally until the separate
  Action Book placement surface is implemented.
- Quick Create previews are now unlocked by default for Action Book drag/drop
  placement, with a Lock Bar/Unlock Bar toggle replacing the old Edit Slots UI
  label.
- The first Action Book placement surface is implemented: it opens
  as its own dockable Maya panel, searches the current 13-entry Action Book
  starter catalog, runs clicked entries, and drops action payloads onto unlocked
  slots using the same icons as the bar.
- The latest Quick Create/Action Book round-trip fix preserves dropped live
  payloads when Lock Bar rebuilds the Quick Create preview, so the assigned
  action and icon survive the transition back to normal click-to-run mode.
- The May 8 ElvUI-reference appearance pass adds per-bar appearance schema,
  theme override resolution, widget painting support, and a Quick Create
  Appearance tab. The follow-up comparison keeps the next direction explicit:
  global theme defaults first, sparse per-bar overrides second, and layout,
  slot payloads, and appearance edited through separate surfaces.
- Maya smoke cleanup now removes all `ActionRail*` Qt widgets and known
  ActionRail workspace controls between smoke scripts so diagnostics/panel
  windows do not steal later Edit Mode clicks or leave blank workspace shells.
- No ActionRail implementation blocker is known.

## Blockers

- No ActionRail implementation blocker known.
- `GG_MayaSessiond doctor --mcp-src ../GG_MayaMCP` is currently blocked by a
  sibling repo compatibility lock: sessiond expects GG_MayaMCP commit
  `2e7a28df7f4d029d81f6421549fb23cb056c4693` / version `0.4.0`, while
  `../GG_MayaMCP` is at `637954c0510296543126c6504dd445f066eb4559` /
  version `0.4.1`.
- Workaround used for verification: omit `--mcp-src` so sessiond uses the MCP
  package installed in its venv. `doctor` passes in that mode.

## Latest Verification

- Latest Phase 2 step 2.7 dense overlay validation:
  `.\\.venv\\Scripts\\python.exe -m pytest`
  -> 522 passed.
- Latest Phase 2 step 2.7 Ruff:
  `.\\.venv\\Scripts\\python.exe -m ruff check .`
  -> all checks passed.
- Latest selection redraw regression validation:
  `.\\.venv\\Scripts\\python.exe -m pytest tests\\test_overlay.py tests\\test_state.py`
  -> 49 passed.
- Latest selection redraw Ruff:
  `.\\.venv\\Scripts\\python.exe -m ruff check scripts\\actionrail\\overlay.py tests\\test_overlay.py tests\\maya_smoke\\actionrail_selection_redraw_smoke.py`
  -> all checks passed.
- Latest selection redraw Maya smoke:
  `.\\scripts\\maya-smoke.ps1 -NoStart -Script actionrail_selection_redraw_smoke.py -Timeout 240`
  -> passed against the running MayaSessiond state on port `7217`; verified
  the README-style overlay-visible selection path uses one shared Maya API
  selection callback and that two mesh selection changes each call
  `cmds.refresh(currentView=True, force=True)`.
- Latest performance hardening checks:
  focused local coverage verifies per-slot icon status resolves once, Maya icon
  resource checks cache per `cmds` session object, dense paint reuses icon and
  pixmap caches, and `MayaStateService.refresh(..., dependencies={"maya.tool"})`
  does not touch selection, panel, camera, or playback APIs. The dense Maya
  smoke now also records scheduler and per-host refresh timing.
- Latest dense overlay Maya smoke:
  `.\\scripts\\maya-smoke.ps1 -NoStart -Script actionrail_dense_overlay_smoke.py -Timeout 300`
  -> passed; verified 120 visible dense slots across two custom-painted dense
  canvas bars, no per-slot dense `QPushButton` objects, a 20-button widget
  baseline on the legacy path, one shared predicate scheduler, dirty refresh
  without rebuilds, pass-through for wheel/Alt/middle while plain left clicks
  stay with ActionRail, scheduler refresh timing around `0.093 ms`,
  per-host dense refresh timing around `1.2-1.4 ms`, and screenshot capture at
  `.gg-maya-sessiond/screenshots/actionrail_dense_overlay.png`.
- Latest full Maya smoke baseline:
  `.\\scripts\\maya-smoke.ps1 -NoStart -Script all -Timeout 300`
  -> passed against the running MayaSessiond state on port `7217`; includes the
  dense overlay probe, the new selection-redraw regression, Action Book,
  capture, custom preset-store, diagnostics, Edit Mode, hidden visibility,
  horizontal and Maya icon rails, hotkey bridge/sync, import/recovery,
  menu/shelf UI, missing Maya icon resources, overlay cleanup, Phase 0,
  predicates, Quick Create, StackItem ABI, and transform-stack state smoke
  scripts.
- Latest focused Edit Mode color validation:
  `.\\.venv\\Scripts\\python.exe -m pytest tests\\test_edit_mode.py`
  -> 38 passed.
- Latest focused Edit Mode color Ruff:
  `.\\.venv\\Scripts\\python.exe -m ruff check scripts\\actionrail\\edit_mode.py tests\\test_edit_mode.py`
  -> all checks passed.
- Latest Edit Mode Maya smoke after color polish:
  `.\\scripts\\maya-smoke.ps1 -Script actionrail_edit_mode_smoke.py -Timeout 300`
  -> passed; refreshed
  `.gg-maya-sessiond/screenshots/actionrail_edit_mode_layout_map.png` with
  green selected-frame/panel accents and black grid lines.
- Latest focused slot-layering validation:
  `.\\.venv\\Scripts\\python.exe -m pytest tests\\test_widgets.py tests\\test_theme.py`
  -> 57 passed.
- Latest focused slot-layering Ruff:
  `.\\.venv\\Scripts\\python.exe -m ruff check scripts\\actionrail\\widgets.py tests\\test_widgets.py`
  -> all checks passed.
- Latest Action Book UI Maya smoke after slot-layering polish:
  `.\\scripts\\maya-smoke.ps1 -Script actionrail_action_book_ui_smoke.py -Timeout 300`
  -> passed; verified Action Book search/click/drop workflow and refreshed
  `.gg-maya-sessiond/screenshots/actionrail_action_book_drop_bar.png` with a
  continuous painted rail backing and enlarged dropped icon tile.
- Latest focused appearance schema validation:
  `.\\.venv\\Scripts\\python.exe -m pytest tests\\test_spec.py tests\\test_authoring.py tests\\test_theme.py tests\\test_quick_create.py tests\\test_widgets.py`
  -> 142 passed.
- Latest focused appearance schema Ruff:
  `.\\.venv\\Scripts\\python.exe -m ruff check scripts\\actionrail\\spec.py scripts\\actionrail\\authoring.py scripts\\actionrail\\theme.py scripts\\actionrail\\widgets.py scripts\\actionrail\\quick_create.py tests\\test_spec.py tests\\test_authoring.py tests\\test_theme.py tests\\test_quick_create.py tests\\test_widgets.py`
  -> all checks passed.
- Latest focused Quick Create Appearance tab validation:
  `.\\.venv\\Scripts\\python.exe -m pytest tests\\test_quick_create.py tests\\test_theme.py tests\\test_widgets.py`
  -> 100 passed.
- Latest Quick Create Appearance tab Ruff:
  `.\\.venv\\Scripts\\python.exe -m ruff check scripts\\actionrail\\quick_create_ui.py tests\\test_quick_create.py tests\\maya_smoke\\actionrail_quick_create_smoke.py`
  -> all checks passed.
- Latest Quick Create Maya smoke:
  `.\\scripts\\maya-smoke.ps1 -Script actionrail_quick_create_smoke.py -Timeout 300`
  -> passed; verified appearance values update the draft, preview host,
  saved preset, and Load Existing path, while preserving Save + Publish
  runtime commands and the custom user-preset shelf-toggle path. Screenshot
  inspection confirmed the Quick Create Appearance tab renders as compact
  grouped controls without overlap at the captured 900x680 panel size.
- Latest docs/project-map checks:
  `$env:PYTHONPATH='scripts'; .\\.venv\\Scripts\\python.exe -m actionrail --json`,
  `& ..\\bram-agent-scripts\\scripts\\docs-list.ps1`, and PowerShell local
  Markdown link scan over `docs/**/*.md`
  -> passed.
- Latest project-map validation:
  `.\\.venv\\Scripts\\python.exe -m pytest tests\\test_project_map.py`
  -> 6 passed.
- Latest project-map Ruff:
  `.\\.venv\\Scripts\\python.exe -m ruff check scripts\\actionrail\\project.py tests\\test_project_map.py`
  -> all checks passed.
- Latest focused Action Book placement label/key validation:
  `.\\.venv\\Scripts\\python.exe -m pytest tests\\test_quick_create.py tests\\test_overlay.py tests\\test_widgets.py tests\\test_spec.py tests\\test_authoring.py`
  -> 168 passed.
- Latest focused Action Book placement Ruff:
  `.\\.venv\\Scripts\\python.exe -m ruff check scripts\\actionrail\\quick_create.py scripts\\actionrail\\quick_create_ui.py scripts\\actionrail\\slot_payloads.py scripts\\actionrail\\slot_state.py scripts\\actionrail\\spec.py scripts\\actionrail\\widgets.py tests\\test_authoring.py tests\\test_overlay.py tests\\test_quick_create.py tests\\test_spec.py tests\\test_widgets.py tests\\maya_smoke\\actionrail_action_book_ui_smoke.py`
  -> all checks passed.
- Latest Action Book UI Maya smoke:
  `.\\scripts\\maya-smoke.ps1 -Script actionrail_action_book_ui_smoke.py -Timeout 240`
  -> passed; verified drag/drop assignment of `maya.tool.scale` onto an
  unlocked blank Quick Create slot keeps the primary slot label empty, preserves
  the slot key label, keeps the catalog icon visible, and survives Lock Bar
  rebuild. The latest run also refreshed the Action Book and drop-bar
  screenshots after the icon-tile action-bar paint pass.
- Latest project/docs checks:
  `$env:PYTHONPATH='scripts'; .\\.venv\\Scripts\\python.exe -m actionrail --json`,
  `& ..\\bram-agent-scripts\\scripts\\docs-list.ps1`, and local Markdown link
  scan -> passed.
- Latest focused theme validation:
  `.\\.venv\\Scripts\\python.exe -m pytest tests\\test_widgets.py tests\\test_theme.py`
  -> 53 passed.
- Latest focused theme/widget Ruff:
  `.\\.venv\\Scripts\\python.exe -m ruff check scripts\\actionrail\\action_book_ui.py scripts\\actionrail\\widgets.py scripts\\actionrail\\theme.py tests\\test_widgets.py tests\\test_theme.py tests\\maya_smoke\\actionrail_action_book_ui_smoke.py`
  -> all checks passed.
- Latest README screenshot generation:
  `.\\scripts\\maya-smoke.ps1 -Script actionrail_readme_screenshots.py -Timeout 300`
  -> passed; refreshed
  `docs/assets/actionrail_readme_maya_icons_showcase.png` and
  `docs/assets/actionrail_readme_edit_mode.png` from a Quick Create draft-built
  showcase layout with two close horizontal icon bars plus left/right icon
  bars, using 2x widget capture, SVG-backed Maya resources where available,
  and Maya's current viewport background rather than a forced screenshot color.
- Full pytest:
  `.\\.venv\\Scripts\\python.exe -m pytest`
  -> 501 passed.
- Ruff:
  `.\\.venv\\Scripts\\python.exe -m ruff check .`
  -> all checks passed.
- Project map:
  `$env:PYTHONPATH='scripts'; .\\.venv\\Scripts\\python.exe -m actionrail --json`
  -> passed.
- Docs list:
  `& ..\\bram-agent-scripts\\scripts\\docs-list.ps1`
  -> passed.
- Local Markdown link check:
  PowerShell local-link scan over `docs/**/*.md`
  -> `Local Markdown links OK`.
- Edit Mode Maya smoke:
  `.\\scripts\\maya-smoke.ps1 -Script actionrail_edit_mode_smoke.py -Timeout 240`
  -> passed; verified layout-map overlay, Grid Size 64, Snap to Grid, Sticky
  Frames, left-click selection, X coordinate movement, sticky-frame alignment,
  collapsed handle-only widget sizing,
  collapsed-state save persistence, `run_slot()` while collapsed, handle-click
  expansion, saved layout offset `[51, -133]`, user preset save path
  `.gg-maya-sessiond/user_presets/edit_mode_custom.json`, and screenshot capture at
  `.gg-maya-sessiond/screenshots/actionrail_edit_mode_layout_map.png`.
- Custom user-preset store Maya smoke:
  `.\\scripts\\maya-smoke.ps1 -Script actionrail_custom_preset_store_smoke.py -Timeout 240`
  -> passed; verified custom user-preset directory retention through
  `show_preset()`, Edit Mode user source classification, and Save Position
  persistence back to the same custom store.
- Diagnostics Maya smoke:
  `.\\scripts\\maya-smoke.ps1 -Script actionrail_diagnostics_smoke.py -Timeout 240`
  -> passed; verified safe diagnostics and `safe_start("transform_stack")`
  still start an overlay after the built-in override diagnostics fix.
- Full Maya smoke baseline:
  `.\\scripts\\maya-smoke.ps1 -Script all -Timeout 300`
  -> passed against the running MayaSessiond state on port `7217`; covered
  Action Book Toggle Grid metadata/execution, capture, custom user-preset store
  layout saves, diagnostic badges, diagnostics window, hidden visibility,
  Edit Mode, horizontal and Maya icon rails, hotkey bridge, hotkey label sync,
  import/recovery diagnostics, menu/shelf UI, missing Maya icon resources,
  overlay cleanup, predicates, Quick Create, StackItem ABI, and transform-stack
  state. Edit Mode smoke covered the axis-aligned Sticky Frames position path,
  collapsed-state persistence, handle expansion, and screenshot capture; Quick
  Create smoke verifies five templates, Save + Publish creates four slot
  runtime commands plus a preset shelf toggle, and the screenshot capture path.
- Latest focused cross-rail Shift-drag validation:
  `.\\.venv\\Scripts\\python.exe -m pytest tests\\test_widgets.py tests\\test_overlay.py`
  -> 83 passed.
- Latest focused cross-rail Shift-drag Ruff:
  `.\\.venv\\Scripts\\python.exe -m ruff check scripts\\actionrail\\widgets.py tests\\test_widgets.py`
  -> all checks passed.
- Latest Edit Mode Maya smoke after the stale-callback fix:
  `.\\scripts\\maya-smoke.ps1 -Script actionrail_edit_mode_smoke.py -Timeout 240`
  -> passed; verified same-rail move/clear followed by cross-rail payload
  transfer between unlocked Normal Mode rails, plus the existing Edit Mode
  layout, collapse, persistence, and screenshot checks.
- Latest focused Quick Create slot-lock workflow validation:
  `.\\.venv\\Scripts\\python.exe -m pytest tests\\test_quick_create.py tests\\test_package.py tests\\test_project_map.py`
  -> 54 passed.
- Latest focused Quick Create slot-lock workflow Ruff:
  `.\\.venv\\Scripts\\python.exe -m ruff check scripts\\actionrail\\quick_create.py scripts\\actionrail\\quick_create_ui.py scripts\\actionrail\\__init__.py tests\\test_quick_create.py tests\\maya_smoke\\actionrail_quick_create_smoke.py`
  -> all checks passed.
- Quick Create Maya smoke:
  `.\\scripts\\maya-smoke.ps1 -Script actionrail_quick_create_smoke.py -Timeout 240`
  -> passed; verified Quick Create previews open unlocked for Normal Mode slot
  editing, Lock Bar switches the preview to normal click-to-run mode, Unlock
  Bar reopens slot editing, Save + Publish creates four slot runtime commands,
  creates a preset shelf toggle, reports publish status, and preserves the
  custom user preset store path in the shelf command. The latest run also
  verifies Quick Create resizes with its Maya workspace-control parent and
  captures readable two-row command buttons in the panel screenshot.
- Screenshot inspection confirmed these rendered correctly:
  `.gg-maya-sessiond/screenshots/actionrail_edit_mode_layout_map.png`,
  `.gg-maya-sessiond/screenshots/actionrail_quick_create_panel.png`,
  `.gg-maya-sessiond/screenshots/actionrail_diagnostics_window.png`, and
  `.gg-maya-sessiond/screenshots/actionrail_horizontal_tools_widget.png`.
- Latest Maya note: Maya smoke used the installed MCP package in the Sessiond
  venv; do not pass `--mcp-src ../GG_MayaMCP` until the sibling repo
  compatibility blocker is resolved.
- Latest local focused validation:
  `.\\.venv\\Scripts\\python.exe -m pytest tests\\test_project_map.py tests\\test_quick_create.py tests\\test_maya_ui.py tests\\test_diagnostics.py`
  -> 123 passed.
- Latest targeted Ruff:
  `.\\.venv\\Scripts\\python.exe -m ruff check tests\\maya_smoke\\actionrail_cleanup_state.py tests\\maya_smoke\\actionrail_edit_mode_smoke.py tests\\maya_smoke\\actionrail_quick_create_smoke.py`
  -> all checks passed.
- Latest focused Quick Create preview validation:
  `.\\.venv\\Scripts\\python.exe -m pytest tests\\test_quick_create.py tests\\test_widgets.py`
  -> 72 passed.
- Latest focused Quick Create active-state validation:
  `.\\.venv\\Scripts\\python.exe -m pytest tests\\test_quick_create.py`
  -> 34 passed.
- Latest focused Ruff:
  `.\\.venv\\Scripts\\python.exe -m ruff check scripts\\actionrail\\quick_create.py tests\\test_quick_create.py`
  -> all checks passed.
- Latest project map:
  `$env:PYTHONPATH='scripts'; .\\.venv\\Scripts\\python.exe -m actionrail --json`
  -> passed.
- Latest focused Ruff:
  `.\\.venv\\Scripts\\python.exe -m ruff check scripts\\actionrail\\quick_create.py scripts\\actionrail\\quick_create_ui.py scripts\\actionrail\\widgets.py tests\\test_quick_create.py tests\\test_widgets.py tests\\maya_smoke\\actionrail_quick_create_smoke.py`
  -> all checks passed.
- Latest Quick Create Maya smoke:
  `.\\scripts\\maya-smoke.ps1 -Script actionrail_quick_create_smoke.py -Timeout 240`
  -> passed; verified live Preview slider refresh, Buttons=10 generating four
  icon-backed template slots plus six blank slots, Buttons Per Row=5 wrapping
  to `[2, 5]`, Button Size updating live preview scale to `1.25`, Save +
  Publish runtime commands, shelf toggle, and screenshot capture.
- Latest focused Edit/Normal Mode validation:
  `.\\.venv\\Scripts\\python.exe -m pytest tests\\test_edit_mode.py tests\\test_overlay.py tests\\test_widgets.py`
  -> 117 passed.
- Latest focused Edit/Normal Mode Ruff:
  `.\\.venv\\Scripts\\python.exe -m ruff check scripts\\actionrail\\widgets.py scripts\\actionrail\\overlay.py scripts\\actionrail\\slot_payloads.py scripts\\actionrail\\project.py tests\\test_widgets.py tests\\test_overlay.py tests\\maya_smoke\\actionrail_edit_mode_smoke.py`
  -> all checks passed.
- Latest focused Normal Mode drag/drop validation:
  `.\\.venv\\Scripts\\python.exe -m pytest tests\\test_overlay.py tests\\test_widgets.py tests\\test_edit_mode.py`
  -> 117 passed.
- Latest focused Normal Mode drag/drop Ruff:
  `.\\.venv\\Scripts\\python.exe -m ruff check scripts\\actionrail\\widgets.py scripts\\actionrail\\overlay.py scripts\\actionrail\\slot_payloads.py scripts\\actionrail\\project.py tests\\test_widgets.py tests\\test_overlay.py tests\\maya_smoke\\actionrail_edit_mode_smoke.py`
  -> all checks passed.
- Latest Edit Mode Maya smoke:
  `.\\scripts\\maya-smoke.ps1 -Script actionrail_edit_mode_smoke.py -Timeout 240`
  -> passed; verified layout-map overlay, frame selection/movement, Grid Size
  64, Snap to Grid, Sticky Frames alignment, draggable Edit Mode panel
  placement, clickable selected-rail Lock/Unlock toggling, locked-frame nudge
  blocking, layout save, collapse-state save persistence, `run_slot()` while
  collapsed, handle-click expansion, Normal Mode unlocked Shift-drag payload
  move-to-empty-slot, cross-rail payload transfer between unlocked rails,
  Normal Mode host payload clear, screenshot capture, and absence of the
  removed frame options payload path.
- Latest manual cross-bar drag setup:
  `script.execute tests\\maya_smoke\\actionrail_cross_bar_drag_scene.py` with
  `args.repo_root` set to this checkout
  -> passed; created two unlocked Normal Mode bars (`drag_source_bar` and
  `drag_target_bar`) with no scene geometry, and saved the transient Maya scene
  to `.gg-maya-sessiond/actionrail_cross_bar_drag_scene.ma`.
- Latest Action Book backend validation:
  `.\\.venv\\Scripts\\python.exe -m pytest tests\\test_action_book.py tests\\test_quick_create.py tests\\test_project_map.py`
  -> 45 passed.
- Latest Action Book backend Ruff:
  `.\\.venv\\Scripts\\python.exe -m ruff check scripts\\actionrail\\action_book.py scripts\\actionrail\\quick_create.py scripts\\actionrail\\__init__.py scripts\\actionrail\\project.py tests\\test_action_book.py tests\\test_quick_create.py tests\\test_project_map.py`
  -> all checks passed.
- Latest Action Book project map:
  `$env:PYTHONPATH='scripts'; .\\.venv\\Scripts\\python.exe -m actionrail --json`
  -> passed and includes `scripts/actionrail/action_book.py`.
- Latest Quick Create Maya smoke:
  `.\\scripts\\maya-smoke.ps1 -Script actionrail_quick_create_smoke.py -Timeout 240`
  -> passed; verified Quick Create opens on a blank six-slot action bar with no
  default binding targets, verified the simplified Slots tab screenshots show
  only Id/Label/Key columns, verified the five template starters including
  Blank Bar and Viewport Display Strip, verified the read-only Bindings tab
  lists four slot nameCommands for the saved horizontal strip, verified Edit
  Layout enters Edit Mode with
  `quick-horizontal-strip` selected, and captured
  `.gg-maya-sessiond/screenshots/actionrail_quick_create_panel.png`,
  `.gg-maya-sessiond/screenshots/actionrail_quick_create_edit_layout.png`,
  `.gg-maya-sessiond/screenshots/actionrail_quick_create_bindings.png`,
  `.gg-maya-sessiond/screenshots/actionrail_quick_create_general.png`,
  `.gg-maya-sessiond/screenshots/actionrail_quick_create_layout.png`, and
  `.gg-maya-sessiond/screenshots/actionrail_quick_create_slots.png`.
- Latest Action Book viewport validation:
  `.\\scripts\\maya-smoke.ps1 -Script actionrail_action_book_smoke.py -Timeout 240`
  -> passed; verified 13 Action Book entries; `maya.display.toggle_grid`
  metadata (`Viewport`, `maya.grid`) and real Maya grid state transitions from
  on to off and back on; Select changes Maya to `selectSuperContext`; Frame
  Selection executes `viewFit`; Clear Selection empties Maya selection; Center
  Pivot executes on a selected cube; Freeze Transforms resets translate/rotate/
  scale channels; Delete History removes bevel construction history; Toggle
  Isolate Selected flips active model-panel isolate state; and the viewable
  catalog artifact was saved to
  `.gg-maya-sessiond/screenshots/actionrail_action_book_catalog.json`.
- Latest hotkey binding-target validation:
  `.\\scripts\\maya-smoke.ps1 -Script actionrail_hotkey_bridge_smoke.py -Timeout 240`
  -> passed; verified four published `transform_stack` binding targets and the
  Set Key slot's key label, runtime command, nameCommand, slot id, and target id
  through the public `actionrail.slot_binding_targets()` API.
- Latest Action Book UI validation:
  `.\\scripts\\maya-smoke.ps1 -Script actionrail_action_book_ui_smoke.py -Timeout 240`
  -> passed; verified 13 rendered Action Book entries, search narrowing to
  `maya.tool.scale`, click-to-run Select changing Maya to `selectSuperContext`,
  drag/drop assignment of `maya.tool.scale` onto an unlocked blank Quick Create
  slot with `maya.scale` through the real Qt drag-enter/drop path, Lock Bar
  preserving that assigned action/icon after the Quick Create preview rebuild,
  Action Book workspace-control cleanup on close, and screenshots at
  `.gg-maya-sessiond/screenshots/actionrail_action_book_panel.png`,
  `.gg-maya-sessiond/screenshots/actionrail_action_book_search_scale.png`, and
  `.gg-maya-sessiond/screenshots/actionrail_action_book_drop_bar.png`.

## Decisions

- PySide6/Qt overlay is the MVP path.
- Viewport 2.0 is deferred until Qt overlay is stable and should be used only
  for scene/native drawing such as labels, guides, or object-bound graphics.
- Quick Create and the first Edit Mode shell are implemented; continue them
  through focused Phase 2 authoring slices instead of starting later modes.
- WoW-style customization remains the long-term authoring model: movable
  frames, action bar frames, Action Book, Macro Book, Edit Mode, action slots,
  hover-to-bind hotkeys, flyouts, command rings, and preset/profile layers.
- Treat `M/T/R/S/K` as a proof preset and regression target; ActionRail's
  product goal is broader user-authored viewport UI.
- Build the hotkey bridge through Maya runtime commands so bindings remain
  visible to Maya.
- Use `ActionRail` for product/module naming and `actionrail` for Python
  package/API naming.
- Use Python 3.11 in Maya, PySide6/Qt Widgets, custom Qt rail overlay,
  `maya.cmds`, OpenMayaUI, JSON specs, SVG icons, `.mod` packaging, and
  MayaSessiond verification.
- Keep web tech out of the core runtime; use it only for authoring/import tooling.
