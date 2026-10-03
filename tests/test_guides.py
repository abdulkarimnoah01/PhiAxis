import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python3.10libs"))
from composition_guides.guides import (Rect, thirds, fit_aspect, from_bottom_left,
                                       camera_window_corners, gate_from_ndc)
from composition_guides.settings import Settings


class GeometryTests(unittest.TestCase):
    def test_thirds_with_offset(self):
        self.assertEqual(thirds(Rect(30, 60, 900, 600)), (
            (330, 60, 330, 660), (630, 60, 630, 660),
            (30, 260, 930, 260), (30, 460, 930, 460)))

    def test_directional_thirds(self):
        rect = Rect(0, 0, 300, 180)
        self.assertEqual(thirds(rect, "vertical"),
                         ((100, 0, 100, 180), (200, 0, 200, 180)))
        self.assertEqual(thirds(rect, "horizontal"),
                         ((0, 60, 300, 60), (0, 120, 300, 120)))
        with self.assertRaises(ValueError):
            thirds(rect, "diagonal")

    def test_quad_bottom_left_to_top_left(self):
        self.assertEqual(from_bottom_left((0, 0, 600, 400), (1200, 800),
                                         (1200, 800)), Rect(0, 400, 600, 400))
        self.assertEqual(from_bottom_left((600, 400, 600, 400), (1200, 800),
                                         (1200, 800)), Rect(600, 0, 600, 400))

    def test_dpi_mapping_without_double_scale(self):
        for scale in (1, 1.25, 1.5, 2):
            r = from_bottom_left((0, 0, 800 * scale, 600 * scale),
                                 (800 * scale, 600 * scale), (800, 600))
            self.assertEqual(r, Rect(0, 0, 800, 600))

    def test_letterbox_and_pillarbox(self):
        self.assertEqual(fit_aspect(Rect(0, 0, 1200, 900), 2),
                         Rect(0, 150, 1200, 600))
        self.assertEqual(fit_aspect(Rect(10, 20, 1200, 600), 1),
                         Rect(310, 20, 600, 600))

    def test_invalid_rectangles_and_aspects(self):
        for bad in (0, -1, math.inf, math.nan):
            with self.assertRaises(ValueError):
                Rect(0, 0, bad, 100)
            with self.assertRaises(ValueError):
                fit_aspect(Rect(0, 0, 100, 100), bad)

    def test_zero_size_during_resize_is_rejected(self):
        with self.assertRaises(ValueError):
            from_bottom_left((0, 0, 10, 10), (0, 100), (100, 100))

    def test_camera_window_corners(self):
        corners = camera_window_corners(1920, 1080, 1, 36, 36, depth=1)
        self.assertEqual(corners[0], (-0.5, -0.5 * 1080 / 1920, -1))
        self.assertEqual(corners[2], (0.5, 0.5 * 1080 / 1920, -1))
        # A screen window shifts and shrinks the frame; pixel aspect widens it.
        shifted = camera_window_corners(100, 100, 1, 10, 10, (0.25, 0, 0.5, 0.5), depth=1)
        self.assertEqual((shifted[0][0], shifted[1][0]), (0.0, 0.5))
        wide = camera_window_corners(100, 100, 2, 10, 10, depth=1)
        self.assertEqual(wide[2][:2], (0.5, 0.25))
        ortho = camera_window_corners(200, 100, ortho_width=4)
        self.assertEqual(ortho[2][:2], (2, 1))
        for kwargs in (dict(resx=0), dict(focal=0), dict(ortho_width=-1),
                       dict(window=(0, 0, 0, 1)), dict(aperture=math.nan)):
            args = dict(resx=10, resy=10)
            args.update(kwargs)
            with self.assertRaises(ValueError):
                camera_window_corners(**args)

    def test_gate_from_ndc(self):
        viewport = Rect(100, 50, 800, 400)
        full = ((-1, -1), (1, -1), (1, 1), (-1, 1))
        self.assertEqual(gate_from_ndc(viewport, full), viewport)
        # NDC y is up; the top-left rect's y is down. A pan past the edge is kept.
        self.assertEqual(gate_from_ndc(viewport, ((0, 0), (2, 0), (2, 1), (0, 1))),
                         Rect(500, 50, 800, 200))

    def test_style_validation(self):
        for kwargs in (dict(opacity=2), dict(thickness=0), dict(safe_x=True),
                       dict(color=(256, 0, 0)), dict(color=(1.0, 2, 3))):
            with self.assertRaises(ValueError):
                Settings(**kwargs)


if __name__ == "__main__":
    unittest.main()
