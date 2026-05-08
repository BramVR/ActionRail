# Changelog

## Update Method

- Keep newest date sections first.
- Build each date section from `git log --oneline` since the previous
  changelog update.
- Group related conventional commits into concise user-facing bullets instead
  of listing every hash.
- Include repo/process hygiene only when it changes how future work should be
  done or how the checkout behaves.

## 2026-05-08

- Added sparse per-bar appearance data to presets and drafts, including theme
  inheritance, accent/text overrides, backdrop color and stripe pattern
  controls, border color/thickness, and slot color overrides.
- Added theme resolution and widget painting support so bar-local appearance
  overrides layer on top of ActionRail's global theme without mixing layout,
  slot payloads, and visual settings.
- Added a Quick Create Appearance tab grouped like compact ElvUI-style action
  bar options: Theme, Backdrop Settings, Border Settings, and Slot Colors.
  These settings preview live and persist through save/load/edit workflows.
- Updated Quick Create smoke coverage to verify appearance values flow through
  the draft, live preview host, saved user preset, and Load Existing path, and
  inspected the captured Appearance screenshot for readable grouped controls.
- Documented the ElvUI-informed architecture direction: global theme defaults
  first, sparse per-bar overrides second, with profile/media systems deferred
  until the current Phase 2 authoring loop is stable.

## 2026-05-07

- Reframed the ActionRail architecture around WoW-style frames: current rails
  are action bar frames, with future Action Book, Macro Book, Bind Mode,
  info-frame, object-frame, and macro workflows documented as the product
  direction.
- Added the first Action Book backend slice: registered Maya actions now expose
  picker-facing category/icon/keyword metadata, and Quick Create consumes that
  catalog for action choices.
- Added the first non-transform Action Book command, Toggle Grid, with real
  Maya smoke coverage so the catalog is no longer limited to the original
  transform/keyframe examples.
- Added Quick Create starter templates for a blank action bar and a viewport
  display strip seeded with Toggle Grid, giving the authoring workflow both
  empty sockets and pre-populated Action Book examples.
- Added public slot binding-target metadata so saved bars can expose the exact
  slot ids, key labels, runtime commands, and Maya nameCommands that current
  Hotkey Editor workflows and future Bind Mode need.
- Added a read-only Quick Create Bindings tab that lists action-bearing slots
  and their Maya hotkey nameCommands, keeping hotkey prep connected to the bar
  creation flow without starting full Bind Mode.
- Connected Quick Create to Edit Mode with an Edit Layout action that previews
  the current draft and selects it in the layout-map overlay for placement.
- Improved Edit Mode control-panel usability: the selected rail state is now a
  clickable Lock/Unlock action, and the compact panel can be dragged aside when
  it covers a rail in the viewport.
- Fixed Normal Mode unlocked slot dragging across bars: Shift-drag now moves or
  swaps payloads between different unlocked rails, and dropping onto a locked
  different rail preserves the source instead of clearing it.
- Fixed the MayaSessiond cross-bar Shift-drag path after rail rebuilds by
  resolving slot-edit callbacks against the live target host unlock state, so
  rebuilt/stale Qt button snapshots no longer block valid transfers.
- Added a Quick Create slot-edit bridge that previews the current draft and
  unlocks the visible bar for Normal Mode slot editing; the bottom command area
  now uses separate edit/save rows so button labels do not clip in Maya.
- Refocused Quick Create on action-bar creation: it now opens on a blank
  six-slot action bar, and the Slots tab edits only slot id, label, and key
  text while preserving loaded action/icon payloads internally for the separate
  Action Book workflow.
- Expanded the Action Book backend beyond transform/key/grid entries with
  Select, Clear Selection, and Frame Selection actions, including Maya smoke
  verification and a saved catalog JSON artifact for review.
- Added a compact Action Book starter set for common modeling/viewport commands:
  Toggle Isolate Selected, Center Pivot, Freeze Transforms, and Delete History,
  with Maya smoke verification and the saved catalog artifact updated to 13
  entries.
- Added the first separate Action Book UI: a dockable, searchable, two-page
  Maya panel with category tabs, icon-backed action rows, click-to-run action
  previews, and drag/drop placement onto unlocked action-bar slots.
- Fixed Action Book smoke cleanup so tests close the Maya workspace control
  shell, not only the child widget, and stale ActionRail workspace controls are
  removed between smoke scripts.
- Fixed live Action Book drag/drop into unlocked bars by making the rail root
  accept Qt drag-enter/drop events and route them to the slot under the cursor.
- Simplified the Quick Create slot-edit workflow: previews now open unlocked
  for Action Book placement, and the old Edit Slots control is presented as a
  direct Lock Bar/Unlock Bar toggle.
- Fixed the Quick Create Lock Bar round-trip after Action Book placement so
  dropped action payloads and icons survive the preview rebuild when the bar is
  locked, saved, or otherwise refreshed.
- Changed Action Book placement defaults so dropped actions keep the primary
  slot label empty, while blank action-bar sockets show their default numbers as
  key labels.
- Increased the ActionRail diagonal stripe weight on action bars and Action
  Book pages, with both stripe treatments rendered at 40% opacity.
- Kept the action-bar stripe base fully opaque at `rgb(29, 32, 42)` and
  changed the diagonal highlight to an opaque `rgb(45, 47, 60)` line with hard
  stops so the stripe does not make the rail background transparent.
- Moved action-bar stripe rendering from a stretched Qt stylesheet gradient to
  pixel-based cluster-frame painting so the striped bar continues behind the
  buttons with a consistent diagonal angle.
- Centered buttons inside the custom-painted action-bar frame and changed the
  painted stripes to thinner, denser lines.
- Improved README icon capture quality by using SVG-backed Maya resources where
  Maya exposes true vector equivalents, and by requesting scaled pixmaps during
  high-resolution widget rendering.
- Added a shared dark spell-icon backplate so Action Book entries and dropped
  action-bar icons render as framed icon tiles instead of floating transparent
  icons.
- Removed the underlying push-button skin from icon-bearing action-bar slots so
  selected borders align to the icon tile and the striped rail background stays
  visible around populated slots.
- Refreshed the README normal-view and Edit Mode screenshots from the same
  Maya example scene so the public docs show the current interface style.
- Retuned the shared ActionRail theme toward an ElvUI-style look: transparent
  near-black frames, square recessed slots, white default text, green
  active accents and panel frame lines, black-bordered opaque striped
  action-bar frames, gold warnings, denser 50% opacity inset profile lines,
  and matching Quick Create, Action Book, diagnostics, and Edit Mode panel
  surfaces.

## 2026-05-06

- Started Phase 2 step 2.6 with real collapsible edge-tab schema/runtime
  support: optional persisted `collapse` settings, Quick Create edge-tab
  defaults/settings, collapsed handle-only Qt overlays, Edit Mode
  collapse/expand controls, hotkey label restoration after expand, and Maya
  smoke coverage for collapse/save/run/expand.
- Fixed review issues in the collapsible edge-tab slice: temporary handle
  reveal no longer changes saved default collapse state, Edit Mode can toggle
  configured collapse rails with non-edge anchors, and Quick Create infers
  disabled collapse edge defaults from each template anchor.
- Updated status, architecture, Edit Mode, roadmap, and project-map docs so the
  next slice is handle tuning plus publish polish for saved presets.
- Polished the first 2.6 publish/handle pass: collapsed handles now use larger
  edge-clamped hit targets, Quick Create saves run publish-facing diagnostics
  before writing, saved drafts can publish slot runtime commands, and Quick
  Create exposes a Save + Publish path that also installs an idempotent preset
  shelf toggle.
- Continued the 2.6 validation/publish polish: Quick Create Validate Draft now
  surfaces publish diagnostics before save, blocked saves include the concrete
  diagnostic issue, Save + Publish reports stale slot-command cleanup, and
  preset shelf toggles preserve custom user preset stores.
- Fixed the Quick Create workspace-control resize behavior so the panel fills
  the resized Maya window instead of staying at its initial dimensions.
- Made Quick Create previews live while the Preview overlay is visible:
  changing button count, buttons per row, offsets, alpha, or button size now
  refreshes the viewport preview immediately, and increasing the button count
  generates extra blank slots after the template's icon-backed slots.
- Made Quick Create infer active-state predicates for persistent Maya tool
  actions so saved Move/Translate/Rotate/Scale slots highlight when that tool
  context is active, while one-shot actions such as Set Key remain inactive.
- Polished Edit Mode guide feedback for the 2.6 authoring pass: Sticky Frames
  now draws axis-aligned alignment guides instead of diagonal hints.
- Removed the Edit Mode frame options popover and moved slot payload editing
  out of Edit Mode. Active rails now expose Normal Mode lock/unlock helpers so
  slot payloads can be assigned or cleared from the rendered rail while Edit
  Mode stays focused on whole-rail layout.
- Added Normal Mode Shift-drag editing for unlocked rails: populated slot
  payloads can move to empty slots, swap with populated slots, or clear when
  released anywhere that is not another slot; locking the rail returns buttons
  to normal action execution.
- Fixed Normal Mode Shift-drag release hit-testing so dropping a slot outside
  the rail reliably clears the source payload before later swaps rebuild the
  rail.
- Fixed Normal Mode Shift-drag slot-drop hit-testing for active viewport
  overlays so overlay-hosted rails still move or swap payloads when Qt's
  `widgetAt()` fallback misses the target button.
- Darkened locked/no-action slots so generated empty Quick Create buttons read
  more like recessed sockets while keeping the existing square shape.
- Hardened Maya smoke cleanup so ActionRail diagnostics and authoring windows
  are removed between smoke scripts instead of stealing later Edit Mode clicks.

## 2026-05-05

- Fixed Quick Create rich preset round-trips so loading and rebuilding saved
  presets preserves spacers, tones, tooltips, predicates, and spacer sizes.
- Fixed the Quick Create panel to preserve explicit user preset stores and
  custom action/icon ids that are not in the built-in pickers.
- Aligned Quick Create layout bounds with runtime schema limits and normalized
  saved horizontal/vertical layout capacity to the authored slot count.
- Fixed preset discovery so invalid user preset files are marked with an error
  and excluded from loadable preset id lists.
- Fixed diagnostics to keep explicit broken user preset ids as warnings when
  preset discovery has already marked the files invalid.
- Fixed Edit Mode rail movement to clamp snapped/dragged positions inside a
  safe viewport margin.
- Added Edit Mode Save Position support for unlocked built-in rails by writing
  separate user override presets instead of mutating bundled presets.
- Fixed built-in preset resolution to apply saved Edit Mode user override
  sidecars when loading the original built-in preset id.
- Fixed safe startup so diagnostically bad built-in user override sidecars stay
  user-preset warnings and the bundled preset can still start.
- Added Edit Mode direct-manipulation controls for drag handles, anchor pins,
  guide rendering, slot add/remove/reorder, and edge-tab opacity collapse.
- Fixed Edit Mode layout saves for overlays loaded from a custom user preset
  directory so Save Position updates the same preset store instead of falling
  back to the default ActionRail user preset folder.
- Added optional read-only studio preset discovery and Edit Mode Save Position
  user overrides for unlocked studio rails.
- Recorded the audit/status docs from the May 5 fix pass, then stopped
  tracking local `.spec/` reports so future reports stay out of Git.
- Refreshed README/status docs to reflect the current bundled presets and
  implemented Edit Mode persistence/direct-manipulation surface.
- Marked Phase 2 step 2.5 complete in the implementation plan and aligned
  start/status/Edit Mode docs so Phase 2 step 2.6 is the next active slice.
