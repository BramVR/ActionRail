# Changelog

## 2026-05-05

- Fixed Quick Create rich preset round-trips so loading and rebuilding saved
  presets preserves spacers, tones, tooltips, predicates, and spacer sizes.
- Moved the ActionRail QA reports into the repository-root `.spec` directory
  and added a current open-issue audit covering the last-24-hour commit window.
- Fixed Edit Mode layout saves for overlays loaded from a custom user preset
  directory so Save Position updates the same preset store instead of falling
  back to the default ActionRail user preset folder.
