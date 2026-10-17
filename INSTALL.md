# Installing and updating PhiAxis

PhiAxis works with Houdini 20.5, 21.0 and 22.0 on Windows. No administrator rights are
needed, and nothing is copied into Houdini's own folders.

## Artists: install

1. Unzip the PhiAxis download anywhere.
2. Double-click **Install PhiAxis.cmd**.
3. Restart Houdini, then add the shelf: shelf **+** menu, **Shelves**, **PhiAxis**.

The installer finds every Houdini 20.5 to 22 you have used (their preferences folders in
Documents) and sets PhiAxis up for all of them at once. If it says it found none, start
Houdini once so it creates its preferences folder, then run it again.

The shelf has three tools: **Toggle Guides**, **Guide Settings** and **Check for Updates**.

## Manual install (no installer)

PhiAxis is a normal Houdini **package**: a folder of Python code and shelf tools plus one small
`.json` file that tells Houdini where it is. The installer just does these steps for you. Do them by
hand when you manage packages yourself, for example a studio that keeps tools on a shared drive or
launches Houdini with its own preferences or `HOUDINI_PACKAGE_DIR`.

1. Unzip the download and copy the **`payload`** folder to a permanent place, for example
   `D:/Tools/PhiAxis/0.8.1`. It contains `python3.10libs`, `toolbar` and `config`.
2. Create a file named `phiaxis.json` in a folder Houdini reads packages from: your
   `Documents/houdini22.0/packages` (use `houdini21.0` or `houdini20.5` for those versions), or your
   studio's package folder. Put this in it, with the path from step 1 (forward slashes):

   ```json
   {
       "enable": "houdini_version >= '20.5' and houdini_version < '23.0'",
       "env": [
           {"PHIAXIS": "D:/Tools/PhiAxis/0.8.1"},
           {"PYTHONPATH": {"value": "$PHIAXIS/python3.10libs", "method": "prepend"}}
       ],
       "path": "$PHIAXIS"
   }
   ```

3. Restart Houdini, then add the shelf: shelf **+** menu, **Shelves**, **PhiAxis**.

To remove it, delete `phiaxis.json` (and the folder). To update, copy the new `payload` over a new
folder and change the path in `phiaxis.json`.

Notes: **Check for Updates** only works for a copy made by the installer, so a manual install is updated
by hand. Your settings and presets are still saved in your Houdini preferences folder as usual.

## Artists: update

Either:

- In Houdini, click **Check for Updates** (shelf, or the button in the Guide Settings
  panel). It shows what is new and installs it if you say yes. The first time it asks where
  updates come from: paste the folder or web address you were given. Then restart Houdini.
- Or unzip the new download and double-click **Install PhiAxis.cmd** again. It replaces the
  old version and keeps the one before it, so a bad update can be rolled back.

Your settings, saved defaults and presets live in your Houdini preferences
(`composition_guides.json`) and are not touched by updating.

## Artists: remove

Double-click **Uninstall PhiAxis.cmd**, then restart Houdini. Your settings are kept.

## Where things go

| What | Where |
| --- | --- |
| The plugin | `%LOCALAPPDATA%\PhiAxis\versions\<version>\` (this one and the one before) |
| The hook into Houdini | `Documents\houdiniX.Y\packages\phiaxis.json`, one per version |
| Your settings and presets | `Documents\houdiniX.Y\composition_guides.json` |
| Where updates come from | `phiaxis_update.json` in the same folder, or the `PHIAXIS_UPDATE_SOURCE` variable |

If an old `composition_guides.json` package file exists, the installer renames it to
`.bak-<date>` so two copies don't load. Pass `-KeepLegacy` to leave it.

Command line options: `Install PhiAxis.cmd -Houdini 22.0` (only that version),
`-CreatePrefs -Houdini 22.0` (prepare a version you have not started yet), `-Uninstall`.

## Whoever supplies PhiAxis: publish a release

1. Change `__version__` in `python3.10libs/composition_guides/__init__.py` and add a section to
   `CHANGELOG.md` (its bullets become the notes artists see before updating).
2. **On GitHub (the normal way):** commit, then `git tag v<version>` and
   `git push origin main v<version>`. The *release* workflow (`.github/workflows/release.yml`)
   checks the tag matches `__version__`, runs the tests, builds the zip and `version.json`,
   bakes in `https://github.com/<owner>/<repo>/releases/latest/download/` as the update
   source, and publishes both as a GitHub release. Artists get it the next time they click
   **Check for Updates**, and the Releases page is the download link to share.
3. **Without GitHub:** run `python tools/make_release.py` (add `--update-source <folder or
   https address>` once to bake in where installed copies should look). It writes
   `dist/PhiAxis-<version>.zip` and `dist/version.json`. Put **both files** in the update
   source, or send the zip to artists.

The update source is just a folder (a shared drive works) or an https address that serves
the two files, such as a GitHub release or any web host. The zip is checked against the
SHA-256 in `version.json` before it is unpacked, and plain `http://` is refused. Nothing is
checked in the background: PhiAxis only contacts the update source when an artist clicks.

The release holds the plugin, installer and docs only. Demo scenes, tests, the showcase and
reference images (some are copyrighted) are never included.
