from dataclasses import replace
from math import isclose
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python3.10libs"))
from composition_guides.settings import Settings, load, save
from composition_guides.guides import (Rect, guide_geometry, guide_lines,
                                       golden_triangle, dynamic_symmetry,
                                       diagonal_phi, radiating, tunnel,
                                       center_lines, pyramid, vanishing_point,
                                       leading_lines)


class MVPTests(unittest.TestCase):
    def test_golden(self):
        lines = guide_lines(Rect(0, 0, 100, 100), Settings(thirds=False, golden=True))
        self.assertEqual(len(lines), 4)
        self.assertAlmostEqual(lines[0][0], 38.196601125)
        self.assertAlmostEqual(lines[1][0], 61.803398875)

    def test_safe_margins_each_edge(self):
        lines = guide_lines(Rect(20, 30, 1000, 500),
                            Settings(thirds=False, safe_area=True, safe_x=.1, safe_y=.2))
        self.assertEqual(lines, ((120, 130, 920, 130), (920, 130, 920, 430),
                                 (920, 430, 120, 430), (120, 430, 120, 130)))

    def test_crosshair_diagonals_and_empty(self):
        rect = Rect(0, 0, 400, 200)
        self.assertEqual(guide_lines(rect, Settings(thirds=False)), ())
        lines = guide_lines(rect, Settings(thirds=False, diagonals=True, crosshair=True))
        self.assertEqual(lines, ((0, 0, 400, 200), (400, 0, 0, 200),
                                 (195, 100, 205, 100), (200, 95, 200, 105)))

    def test_all_guides(self):
        self.assertEqual(len(guide_lines(Rect(0, 0, 100, 100), Settings(
            golden=True, crosshair=True, diagonals=True, safe_area=True))), 16)

    def test_roundtrip_and_corrupt_preferences(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "prefs.json"
            self.assertEqual(load(path), Settings())
            expected = Settings(golden=True, scope="all", color=(10, 20, 30))
            save(path, expected)
            self.assertEqual(load(path), expected)
            path.write_text('{"version": 99}')
            with self.assertRaises(ValueError):
                load(path)

    def test_invalid_scope_and_margin(self):
        for kwargs in (dict(scope="bad"), dict(safe_x=.5), dict(safe_y=-.1),
                       dict(golden=1), dict(orientation=4), dict(focal_x=1.1),
                       dict(radial_count=3), dict(radial_count=8.0),
                       dict(tunnel_scale=0), dict(circle_scale=2),
                       dict(thirds_mode="bad"), dict(center_mode="bad"),
                       dict(vanishing_mode="bad"), dict(pyramid_apex_x=1.1),
                       dict(leading_width=0)):
            with self.assertRaises(ValueError):
                Settings(**kwargs)

    def test_golden_triangle_is_perpendicular(self):
        lines = golden_triangle(Rect(0, 0, 1600, 900))
        self.assertEqual(len(lines), 3)
        self.assertEqual(lines[0], (0, 0, 1600, 900))
        main = (1600, 900)
        for line in lines[1:]:
            branch = (line[2] - line[0], line[3] - line[1])
            self.assertAlmostEqual(main[0] * branch[0] + main[1] * branch[1], 0)
        self.assertNotEqual(lines, golden_triangle(Rect(0, 0, 1600, 900), 1, True))

    def test_dynamic_and_diagonal_phi_armatures(self):
        rect = Rect(10, 20, 600, 400)
        dynamic = dynamic_symmetry(rect)
        self.assertEqual(len(dynamic), 6)
        for line in dynamic:
            for x, y in ((line[0], line[1]), (line[2], line[3])):
                self.assertGreaterEqual(x, rect.x)
                self.assertLessEqual(x, rect.x + rect.width)
                self.assertGreaterEqual(y, rect.y)
                self.assertLessEqual(y, rect.y + rect.height)
        self.assertEqual(len(diagonal_phi(rect)), 10)

    def test_radiating_and_tunnel(self):
        rect = Rect(0, 0, 1000, 500)
        rays = radiating(rect, .25, .75, 12)
        self.assertEqual(len(rays), 12)
        self.assertTrue(all((isclose(x2, 0, abs_tol=1e-7) or
                             isclose(x2, 1000, abs_tol=1e-7) or
                             isclose(y2, 0, abs_tol=1e-7) or
                             isclose(y2, 500, abs_tol=1e-7))
                            for _, _, x2, y2 in rays))
        self.assertEqual(len(tunnel(rect, .5, .5, .4)), 8)

    def test_curved_guides_and_full_cross(self):
        settings = Settings(thirds=False, golden_spiral=True, circle=True,
                            center_cross=True, circle_scale=.8)
        geometry = guide_geometry(Rect(0, 0, 1000, 1000), settings)
        self.assertEqual(len(geometry.lines), 2)
        self.assertEqual(len(geometry.polylines), 1)
        self.assertEqual(len(geometry.polylines[0]), 181)
        self.assertEqual(geometry.ellipses, (Rect(100, 100, 800, 800),))

    def test_golden_spiral_preserves_circular_arcs_and_fits_gate(self):
        rect = Rect(0, 0, 1600, 900)
        spiral = guide_geometry(rect, Settings(
            thirds=False, golden_spiral=True)).polylines[0]
        self.assertEqual(len(spiral), 181)
        epsilon = 1e-7
        self.assertTrue(all(rect.x - epsilon <= x <= rect.x + rect.width + epsilon and
                            rect.y - epsilon <= y <= rect.y + rect.height + epsilon
                            for x, y in spiral))
        # The first arc is a true pixel-space quarter circle. Its start,
        # midpoint and end remain the same radius from the arc center.
        phi = (1 + 5 ** .5) / 2
        golden_width = rect.height * phi
        left = (rect.width - golden_width) / 2
        center = (left + rect.height, rect.height)
        radii = [((spiral[i][0] - center[0]) ** 2 +
                  (spiral[i][1] - center[1]) ** 2) ** .5 for i in (0, 10, 20)]
        self.assertAlmostEqual(radii[0], radii[1], places=7)
        self.assertAlmostEqual(radii[1], radii[2], places=7)
        self.assertAlmostEqual(radii[0], rect.height, places=7)
        rotated = guide_geometry(rect, Settings(
            thirds=False, golden_spiral=True, orientation=1)).polylines[0]
        self.assertTrue(all(rect.x - epsilon <= x <= rect.x + rect.width + epsilon and
                            rect.y - epsilon <= y <= rect.y + rect.height + epsilon
                            for x, y in rotated))

    def test_center_line_orientations(self):
        rect = Rect(10, 20, 200, 100)
        horizontal = (10, 70, 210, 70)
        vertical = (110, 20, 110, 120)
        self.assertEqual(center_lines(rect, "horizontal"), (horizontal,))
        self.assertEqual(center_lines(rect, "vertical"), (vertical,))
        self.assertEqual(center_lines(rect), (horizontal, vertical))

    def test_pyramid_upright_and_inverted(self):
        rect = Rect(0, 0, 200, 100)
        self.assertEqual(pyramid(rect),
                         ((0, 100, 100, 0), (100, 0, 200, 100),
                          (0, 100, 200, 100)))
        self.assertEqual(pyramid(rect, .25, .1, True),
                         ((0, 0, 50, 90), (50, 90, 200, 0),
                          (0, 0, 200, 0)))

    def test_vanishing_point_and_leading_lines(self):
        rect = Rect(0, 0, 200, 100)
        self.assertEqual(vanishing_point(rect, .5, .25, "lower"),
                         ((0, 100, 100, 25), (200, 100, 100, 25)))
        self.assertEqual(len(vanishing_point(rect, .4, .6, "all")), 4)
        self.assertEqual(leading_lines(rect, .5, .25, .5),
                         ((50, 100, 100, 25), (150, 100, 100, 25)))

    def test_new_guides_are_composable(self):
        geometry = guide_geometry(Rect(0, 0, 300, 180), Settings(
            thirds=True, thirds_mode="vertical", center_cross=True,
            center_mode="horizontal", pyramid=True, vanishing_point=True,
            vanishing_mode="lower", leading_lines=True))
        self.assertEqual(len(geometry.lines), 10)
