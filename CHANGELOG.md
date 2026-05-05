# Changelog

## 2026-05-05

- Fixed Quick Create rich preset round-trips so loading and rebuilding saved
  presets preserves spacers, tones, tooltips, predicates, and spacer sizes.
- Fixed the Quick Create panel to preserve explicit user preset stores and
  custom action/icon ids that are not in the built-in pickers.
- Aligned Quick Create layout bounds with runtime schema limits and normalized
  saved horizontal/vertical layout capacity to the authored slot count.
- Fixed preset discovery so invalid user preset files are marked with an error
  and excluded from loadable preset id lists.
- Fixed Edit Mode rail movement to clamp snapped/dragged positions inside a
  safe viewport margin.
- Added Edit Mode Save Position support for unlocked built-in rails by writing
  separate user override presets instead of mutating bundled presets.
- Added Edit Mode direct-manipulation controls for drag handles, anchor pins,
  guide rendering, slot add/remove/reorder, and edge-tab opacity collapse.
- Moved the ActionRail QA reports into the repository-root `.spec` directory
  and added a current open-issue audit covering the last-24-hour commit window.
- Fixed Edit Mode layout saves for overlays loaded from a custom user preset
  directory so Save Position updates the same preset store instead of falling
  back to the default ActionRail user preset folder.
