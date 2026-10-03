# Changelog

All notable changes to PhiAxis. Newest first. Version numbers follow
`major.minor.patch`: patch for fixes, minor for new guides or features, major for
changes that break saved settings.

### 0.6.1 (2026-10-03)

- Fixed: opening Guide Settings raised "cannot import name 'check_for_updates'" in a Houdini
  session that had been running since before an update. The panel now opens, the update
  button shows a plain "restart Houdini" message instead of an error, and **reload_plugin()**
  now reloads the package itself so newer functions appear without a restart.

### 0.6.0 (2026-10-03)

- One-double-click installer for Windows (`Install PhiAxis.cmd`): sets PhiAxis up for every
  Houdini 20.5 to 22 on the PC, no administrator rights, nothing copied into Houdini itself.
  Running a newer release the same way updates it and keeps the previous version for rollback.
  `Uninstall PhiAxis.cmd` removes it and keeps your settings.
- **Check for Updates** on the PhiAxis shelf and in the Guide Settings panel: shows what is
  new and installs it after you confirm. Only runs when clicked; the download is verified
  against a SHA-256 checksum first.
- `tools/make_release.py` builds the release zip and `version.json` for whoever supplies PhiAxis.
- New: INSTALL.md (artist and publisher instructions), CHANGELOG.md.

### 0.5.1 (2026-10-03)

- Golden Rectangles draws each cut once, so dashed line styles stay dashed.
- The built-in Architecture preset is removed (your saved presets are unaffected).
- The PhiAxis shelf tools use a circular PhiAxis icon (`config/Icons/PhiAxis.png`).
- Docs: the Solaris frame-aspect note above. The demo galleries, reference images and
  tests also grew a lot since 0.5.0; they are not part of the plugin and do not
  change its behavior.

### 0.5.0 (2026-09-25)

24 guides, root-rectangle dynamic symmetry, per-guide styles, presets, a tabbed
settings panel, camera frames projected through the viewport (screen windows,
orthographic, quad, Solaris cameras), and Houdini 21 and 22 support.

### 0.4.1

16 guides over Houdini 20.5 with a centered camera frame.
