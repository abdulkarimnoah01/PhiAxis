from dataclasses import replace
from math import isclose
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python3.10libs"))
from composition_guides.guides import (
    Rect, PHI, guide_layers, guide_geometry, dynamic_symmetry, golden_rectangles,
    golden_spiral, single_diagonal, v_shape, l_shape, s_curve, c_curve, balance,
    asymmetric_balance, golden_triangle, diagonal_phi)
from composition_guides.settings import (
    Settings, GUIDE_KEYS, style_for, with_guide_style, load, save, load_presets,
    save_preset, delete_preset)
from composition_guides import presets

EPS = 1e-7


def rounded(values, places=6):
    if isinstance(values, (tuple, list)):
        return tuple(rounded(v, places) for v in values)
    return round(values, places)


def inside(rect, x, y):
    return (rect.x - EPS <= x <= rect.x + rect.width + EPS and
            rect.y - EPS <= y <= rect.y + rect.height + EPS)


class ShapeTests(unittest.TestCase):
    rect = Rect(10, 20, 1600, 900)

    def test_every_guide_has_a_layer_and_stays_in_frame(self):
        everything = Settings(**{key: True for key in GUIDE_KEYS})
        layers = guide_layers(self.rect, everything)
        self.assertEqual([key for key, _ in layers], list(GUIDE_KEYS))
        for key, geometry in layers:
            points = [(l[0], l[1]) for l in geometry.lines] + \
                     [(l[2], l[3]) for l in geometry.lines] + \
                     [p for poly in geometry.polylines for p in poly]
            self.assertTrue(points or geometry.ellipses, key)
            for x, y in points:
                self.assertTrue(inside(self.rect, x, y), (key, x, y))
        merged = guide_geometry(self.rect, everything)
        self.assertEqual(len(merged.lines), sum(len(g.lines) for _, g in layers))

    def test_single_diagonal_orientations(self):
        self.assertEqual(single_diagonal(Rect(0, 0, 200, 100)), ((0, 0, 200, 100),))
        self.assertEqual(single_diagonal(Rect(0, 0, 200, 100), mirror=True),
                         ((200, 0, 0, 100),))

    def test_v_shape(self):
        rect = Rect(0, 0, 200, 100)
        self.assertEqual(v_shape(rect, .5, .8, .5),
                         ((50, 0, 100, 80), (150, 0, 100, 80)))
        self.assertEqual(rounded(v_shape(rect, .5, .8, .5, inverted=True)),
                         ((50, 100, 100, 20), (150, 100, 100, 20)))

    def test_l_shape_is_a_right_angle(self):
        (a, b) = l_shape(Rect(0, 0, 100, 100), .1)
        self.assertEqual(a, (10, 10, 10, 90))
        self.assertEqual(b, (10, 90, 90, 90))
        rotated = l_shape(Rect(0, 0, 100, 100), .1, orientation=1)
        self.assertNotEqual(rotated, (a, b))

    def test_s_and_c_curves(self):
        rect = Rect(0, 0, 100, 100)
        s = s_curve(rect, .25)
        self.assertEqual(rounded((s[0], s[-1])), ((50, 0), (50, 100)))
        xs = [x for x, _ in s]
        self.assertAlmostEqual(max(xs), 75)
        self.assertAlmostEqual(min(xs), 25)
        c = c_curve(rect, .3)
        self.assertAlmostEqual(min(x for x, _ in c), 35)   # bulge reaches left
        self.assertAlmostEqual(c[0][0], 65)                # both ends on the right
        self.assertAlmostEqual(c[-1][0], 65)

    def test_balance_pivot_is_centered_or_weighted(self):
        geometry = balance(Rect(0, 0, 200, 100), .5, .4)
        self.assertEqual(len(geometry.ellipses), 2)
        self.assertEqual(geometry.ellipses[0].width, geometry.ellipses[1].width)
        apex = geometry.lines[1][:2]
        self.assertEqual(apex, (100, 50))
        weighted = asymmetric_balance(Rect(0, 0, 100, 100), (.2, .5, .4), (.8, .5, .2))
        pivot_x = weighted.lines[1][0]
        # Area 4:1, so the pivot sits 1/5 of the way from the big circle.
        self.assertAlmostEqual(pivot_x, 20 + (80 - 20) / 5)

    def test_root_rectangles(self):
        for mode, ratio, divisions in (("root2", 2 ** .5, 1), ("root3", 3 ** .5, 2),
                                       ("root4", 2.0, 3), ("root5", 5 ** .5, 4),
                                       ("rootphi", PHI ** .5, 1)):
            lines = dynamic_symmetry(self.rect, mode)
            self.assertEqual(len(lines), 6 + divisions + 4, mode)
            border = lines[-4:]
            width = border[0][2] - border[0][0]
            height = border[1][3] - border[1][1]
            self.assertAlmostEqual(width / height, ratio, places=7)
            # A reciprocal's foot lands exactly on the first division line.
            first = lines[6]
            self.assertAlmostEqual(first[0] - border[0][0], width / ratio ** 2, places=6)
        portrait = dynamic_symmetry(Rect(0, 0, 500, 1000), "root2")
        self.assertEqual(portrait[6][1], portrait[6][3])   # horizontal division
        with self.assertRaises(ValueError):
            dynamic_symmetry(self.rect, "root7")

    def test_golden_rectangles_are_squares_matching_spiral(self):
        for orientation in range(4):
            geometry = golden_rectangles(self.rect, orientation)
            self.assertEqual(len(geometry.polylines), 1)     # outer rectangle
            cuts = geometry.lines
            self.assertEqual(len(cuts), 9)
            lengths = [((x2 - x1) ** 2 + (y2 - y1) ** 2) ** .5 for x1, y1, x2, y2 in cuts]
            # Each cut is one square's side; successive squares shrink by 1/phi.
            for big, small in zip(lengths, lengths[1:]):
                self.assertAlmostEqual(small / big, 1 / PHI, places=7)
            outline = geometry.polylines[0]
            side = min(abs(outline[1][0] - outline[0][0]) + abs(outline[1][1] - outline[0][1]),
                       abs(outline[2][0] - outline[1][0]) + abs(outline[2][1] - outline[1][1]))
            self.assertAlmostEqual(lengths[0], side, places=6)
            # The spiral's first arc ends exactly where the first cut ends.
            spiral = golden_spiral(self.rect, orientation)
            self.assertEqual(rounded(spiral[20]), rounded(cuts[0][2:]))
            segments = {rounded(c) for c in cuts}
            self.assertEqual(len(segments), 9)                # nothing drawn twice

    def test_golden_flips_move_the_spiral_to_every_corner(self):
        rect = Rect(0, 0, 1000, 618)
        start = golden_spiral(rect)[0]
        left_right = golden_spiral(rect, mirror=True)[0]
        up_down = golden_spiral(rect, flip=True)[0]
        both = golden_spiral(rect, mirror=True, flip=True)[0]
        corners = {rounded((p,))[0] for p in (start, left_right, up_down, both)}
        self.assertEqual(len(corners), 4)
        self.assertAlmostEqual(left_right[0], rect.width - start[0], places=6)
        self.assertAlmostEqual(left_right[1], start[1], places=6)
        self.assertAlmostEqual(up_down[0], start[0], places=6)
        self.assertAlmostEqual(up_down[1], rect.height - start[1], places=6)
        # Flipping twice returns to the start; the shape is only mirrored, not distorted.
        flipped = golden_spiral(rect, flip=True)
        for a, b in zip(golden_spiral(rect), flipped):
            self.assertAlmostEqual(a[0], b[0], places=6)
            self.assertAlmostEqual(a[1], rect.height - b[1], places=6)
        for guide in (golden_rectangles, golden_triangle, diagonal_phi):
            plain = guide(rect)
            plain = plain.lines if hasattr(plain, "lines") else plain
            mirrored = guide(rect, mirror=True)
            mirrored = mirrored.lines if hasattr(mirrored, "lines") else mirrored
            self.assertNotEqual(rounded(plain), rounded(mirrored))

    def test_balance_height(self):
        rect = Rect(0, 0, 2000, 1000)
        middle = balance(rect, .5, .3)
        high = balance(rect, .5, .3, y=.25)
        self.assertEqual([round(e.y + e.height / 2) for e in middle.ellipses], [500, 500])
        self.assertEqual([round(e.y + e.height / 2) for e in high.ellipses], [250, 250])
        self.assertEqual([e.x for e in middle.ellipses], [e.x for e in high.ellipses])
        with self.assertRaises(ValueError):
            Settings(balance_y=1.0)

    def test_flips_are_screen_space_after_rotation(self):
        rect = Rect(0, 0, 100, 100)
        base = l_shape(rect, .1, orientation=1)
        flipped = l_shape(rect, .1, orientation=1, mirror=True)
        for (ax, ay, bx, by), (cx, cy, dx, dy) in zip(base, flipped):
            self.assertAlmostEqual(cx, 100 - ax); self.assertAlmostEqual(cy, ay)
            self.assertAlmostEqual(dx, 100 - bx); self.assertAlmostEqual(dy, by)

    def test_new_settings_validation(self):
        for kwargs in (dict(dynamic_mode="root9"), dict(line_style="wavy"),
                       dict(v_width=0), dict(l_inset=.5), dict(curvature=.6),
                       dict(balance_spacing=1), dict(asym_a_scale=0),
                       dict(v_shape=1), dict(guide_styles=(("nope", (1, 2, 3), 1, 1, "solid"),)),
                       dict(guide_styles=(("thirds", (1, 2, 3), 2, 1, "solid"),)),
                       dict(guide_styles=(("thirds", (1, 2, 3), 1, 1, "solid"),
                                          ("thirds", (1, 2, 3), 1, 1, "dash")))):
            with self.assertRaises(ValueError, msg=kwargs):
                Settings(**kwargs)


class StyleAndPresetTests(unittest.TestCase):
    def test_style_override_and_fallback(self):
        base = Settings(color=(1, 2, 3), opacity=.5, thickness=2, line_style="dash")
        self.assertEqual(style_for(base, "thirds"), ((1, 2, 3), .5, 2, "dash"))
        custom = with_guide_style(base, "thirds", ((9, 9, 9), 1.0, 4.0, "dot"))
        self.assertEqual(style_for(custom, "thirds"), ((9, 9, 9), 1.0, 4.0, "dot"))
        self.assertEqual(style_for(custom, "golden"), ((1, 2, 3), .5, 2, "dash"))
        self.assertEqual(with_guide_style(custom, "thirds"), base)

    def test_styles_and_presets_persist_together(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "prefs.json"
            styled = with_guide_style(Settings(v_shape=True, dynamic_mode="root3"),
                                      "v_shape", ((10, 20, 30), .4, 3.0, "dot"))
            save_preset(path, "Mine", styled)
            save(path, styled)
            self.assertEqual(load(path), styled)
            stored = load_presets(path)
            self.assertIn("Mine", stored)
            self.assertNotIn("guide_styles", stored["Mine"])
            save(path, Settings())            # saving defaults keeps presets
            self.assertIn("Mine", load_presets(path))
            delete_preset(path, "Mine")
            self.assertEqual(load_presets(path), {})
            with self.assertRaises(ValueError):
                save_preset(path, "  ", styled)

    def test_old_settings_files_still_load(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "prefs.json"
            path.write_text('{"version": 1, "settings": {"golden": true, '
                            '"color": [1, 2, 3]}}')
            self.assertEqual(load(path), Settings(golden=True, color=(1, 2, 3)))

    def test_presets_change_guides_not_style(self):
        styled = with_guide_style(Settings(color=(5, 6, 7), thickness=3, golden=True,
                                           scope="all"),
                                  "thirds", ((1, 1, 1), 1, 1, "dot"))
        for name in presets.BUILTIN:
            result = presets.apply_builtin(styled, name)
            self.assertEqual((result.color, result.thickness, result.scope,
                              result.guide_styles),
                             (styled.color, styled.thickness, styled.scope,
                              styled.guide_styles), name)
            enabled = {key for key in GUIDE_KEYS if getattr(result, key)}
            expected = {key for key, value in presets.BUILTIN[name].items()
                        if key in GUIDE_KEYS and value}
            self.assertEqual(enabled, expected, name)
        cinema = presets.apply_builtin(styled, "Cinematography")
        self.assertTrue(cinema.safe_area and cinema.thirds and not cinema.golden)


if __name__ == "__main__":
    unittest.main()
