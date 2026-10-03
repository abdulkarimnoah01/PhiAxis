<p align="center"><img src="docs/images/PhiAxis-icon.png" alt="PhiAxis icon" width="140"></p>

# PhiAxis

**Composition guides for Houdini's viewport.** Thirds, phi grid, golden spiral, vanishing points,
balance and more, drawn live over your Scene Viewer while you move the camera. Free to use (MIT).

PhiAxis is an overlay: it adds no nodes, changes nothing in your scene, and never appears in a render.

![PhiAxis drawing a golden spiral, golden rectangles and a frame over a Solaris camera in Houdini](docs/images/01_phiaxis_in_houdini.jpg)

| | |
| --- | --- |
| ![The Electra rig posed over a film still, with the rule of thirds](docs/images/02_rig_on_film_still.jpg) | ![Centered frame within a frame](docs/images/03_centered_frame_within_a_frame.jpg) |
| *A posed rig over a film still, rule of thirds* | *Centered frame within a frame* |
| ![Central symmetry](docs/images/04_central_symmetry.jpg) | ![Centered composition](docs/images/05_centered_phone_booth.jpg) |
| *Central symmetry* | *Centered composition* |
| ![Leading lines](docs/images/06_leading_lines.jpg) | ![Rule of thirds](docs/images/07_rule_of_thirds.jpg) |
| *Leading lines* | *Rule of thirds* |
| ![Balance, symmetry and centered composition together](docs/images/08_balance_symmetry_centered.jpg) | |
| *Balance, symmetry and centered composition combined* | |

*Screenshots of PhiAxis running in Houdini, drawing its guides over reference frames. The guides illustrate how each one
looks over an image and do not claim the filmmakers or game artists used that construction. Credits for the reference
frames are [below](#license-and-credits).*

## What you get

- **24 guides** that combine freely: rule of thirds, phi grid, golden spiral, golden rectangles and triangle,
  dynamic symmetry (root-2 to root-5 and root-phi), diagonals, center lines, safe area, radiating grid,
  tunnel, vanishing point, leading lines, pyramid, V / L / S / C shapes, circle, balance and asymmetric balance.
  See [GUIDE_TYPES.md](GUIDE_TYPES.md).
- **Follows your camera.** Guides fit the real camera frame: screen windows, orthographic cameras,
  non-square pixels, quad views, floating viewers and Solaris cameras.
- **Presets and styles.** Photography, Cinematography, Portrait and Landscape presets, your own saved
  presets, and a color, opacity, thickness and line style for every guide.
- **Glow and color schemes.** An optional soft glow around every line, with an amount from 0 to 200%, and
  four ready-made color schemes that give each family of guides its own hue (grids, golden-ratio guides,
  perspective, shapes) instead of shades of one color. Both live in the Style tab; glow is off until you
  turn it on.
- **Never in the way.** Clicks, selection and camera moves pass straight through the overlay.
- Works with **Houdini 20.5, 21.0 and 22.0** on Windows.

## Install (about a minute)

1. Download **PhiAxis-x.y.z.zip** from the [latest release](../../releases/latest) and unzip it anywhere.
2. Double-click **Install PhiAxis.cmd**.
3. Restart Houdini, then add the shelf: shelf **+** menu, **Shelves**, **PhiAxis**.

It sets PhiAxis up for every Houdini 20.5 to 22 you have used, needs no administrator rights and copies
nothing into Houdini itself. Details, options and uninstalling: [INSTALL.md](INSTALL.md).

## Update

Click **Check for Updates** on the PhiAxis shelf (or in the Guide Settings panel). It shows what is new and installs
after you confirm; it only runs when you click, and the download is verified against a checksum. Your settings and
presets are kept. You can also just run the new release's installer again.

## Using it

Open **Guide Settings**, tick the guides you want, and look through your camera. In quad view hover a viewport and
press Space+N to choose it, or set Coverage to all visible viewports. A few notes:

- The golden spiral and golden rectangle are 1.618 : 1. In a 16:9 frame they fit inside it with a gap at the sides;
  for a frame that fills, set the camera's aspect ratio to 1.618 : 1. In Solaris the viewport frame follows the
  **Camera LOP's aspect ratio**, not the Render Settings resolution.
- Guides are a way to see what a composition is doing, not rules. Plenty of great frames break them on purpose.

## Troubleshooting

Open Houdini's Python Shell and run `import composition_guides as cg; print(cg.diagnostics())`, then attach the output
to an [issue](../../issues) together with your Houdini version.

## Development

```
python -m unittest discover -s tests -p "test_*.py"     # plain-Python tests (guide geometry, settings, updater, release)
python tools/make_release.py                              # builds dist/PhiAxis-<version>.zip and version.json
```

Releases are built by GitHub Actions when a version tag is pushed (see [INSTALL.md](INSTALL.md)). Contributions are welcome;
please run the tests first.

## License and credits

PhiAxis is copyright © 2026 AbdulKarim Noah, released under the [MIT License](LICENSE). Houdini is a trademark of Side Effects Software Inc.; PhiAxis is not affiliated
with or endorsed by SideFX.

Reference frames in the screenshots belong to their owners and are shown only to illustrate how the
guides look over real compositions. They are not part of PhiAxis and are not covered by its license; they will be
removed on request.

- Rule of thirds, leading lines and the rig-over-film-still screenshot use stills from *Blade Runner* (1982, directed by
  Ridley Scott; The Ladd Company / Warner Bros.).
- Centered frame within a frame, central symmetry, centered composition and the combined balance shot use screenshots from *Alan Wake 2*
  (Remedy Entertainment; published by Epic Games Publishing).
- The posed figure is SideFX's Electra test character that ships with Houdini.
- The first screenshot shows PhiAxis over a Solaris camera view.
