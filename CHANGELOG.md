# Changelog

## Update Method

- Keep newest date sections first.
- Build each date section from `git log --oneline` since the previous
  changelog update.
- Group related conventional commits into concise user-facing bullets instead
  of listing every hash.
- Include repo/process hygiene only when it changes how future work should be
  done or how the checkout behaves.

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
