"""Glow settings, glow math and color schemes (plain Python, no Houdini)."""
from dataclasses import replace
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python3.10libs"))

from composition_guides import glow, schemes                     # noqa: E402
from composition_guides.settings import (                        # noqa: E402
    GUIDE_KEYS, STYLE_FIELDS, Settings, load, load_presets, save, save_preset, style_for)


class GlowSettingsTests(unittest.TestCase):
    def test_glow_is_off_by_default_and_validated(self):
        settings = Settings()
        self.assertFalse(settings.glow)
        self.assertEqual(settings.glow_amount, 1.0)
        for bad in (dict(glow=1), dict(glow_amount=-0.1), dict(glow_amount=2.5),
                    dict(glow_amount=float("nan"))):
            with self.assertRaises(ValueError):
                Settings(**bad)
        Settings(glow=True, glow_amount=0)
        Settings(glow=True, glow_amount=2)

    def test_round_trip_and_old_files(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "settings.json"
            wanted = replace(Settings(), glow=True, glow_amount=1.4)
            save(path, wanted)
            self.assertEqual(load(path), wanted)
            # A file written before glow existed still loads, with glow off.
            import json
            data = json.loads(path.read_text(encoding="utf-8"))
            del data["settings"]["glow"], data["settings"]["glow_amount"]
            path.write_text(json.dumps(data), encoding="utf-8")
            old = load(path)
            self.assertFalse(old.glow)
            self.assertEqual(old.glow_amount, 1.0)

    def test_glow_is_a_style_field_so_guide_presets_keep_it(self):
        self.assertIn("glow", STYLE_FIELDS)
        self.assertIn("glow_amount", STYLE_FIELDS)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "settings.json"
            save_preset(path, "Mine", replace(Settings(), glow=True, glow_amount=1.9))
            stored = load_presets(path)["Mine"]
            self.assertNotIn("glow", stored)
            self.assertNotIn("glow_amount", stored)


class GlowMathTests(unittest.TestCase):
    def test_no_halo_without_amount(self):
        self.assertEqual(glow.halo_layers((255, 0, 0), 0.75, 1.0, 0), [])
        self.assertEqual(glow.halo_layers((255, 0, 0), 0.75, 1.0, -1), [])

    def test_halo_grows_with_amount_and_stays_in_range(self):
        small = glow.halo_layers((10, 200, 30), 0.75, 1.0, 0.5)
        large = glow.halo_layers((10, 200, 30), 0.75, 1.0, 2.0)
        self.assertEqual(len(small), 3)
        for (_c, alpha_s, width_s), (_d, alpha_l, width_l) in zip(small, large):
            self.assertLess(alpha_s, alpha_l)
            self.assertLess(width_s, width_l)
            self.assertTrue(0 <= alpha_l <= 255)
        widths = [w for _c, _a, w in large]
        self.assertEqual(widths, sorted(widths, reverse=True))     # widest first
        for _c, alpha, _w in glow.halo_layers((1, 2, 3), 1.0, 20, 99):   # amount is clamped
            self.assertLessEqual(alpha, 255)

    def test_core_is_lighter_and_never_thinner_than_a_hairline(self):
        self.assertEqual(glow.lighten((0, 0, 0), 0), (0, 0, 0))
        self.assertEqual(glow.lighten((0, 0, 0), 1), (255, 255, 255))
        self.assertTrue(all(a >= b for a, b in zip(glow.lighten((100, 150, 200)), (100, 150, 200))))
        self.assertEqual(glow.core_width(0.25), glow.MIN_CORE_WIDTH)
        self.assertEqual(glow.core_width(3), 3)


class SchemeTests(unittest.TestCase):
    def test_every_guide_belongs_to_exactly_one_family(self):
        placed = [key for keys in schemes.FAMILIES.values() for key in keys]
        self.assertEqual(sorted(placed), sorted(GUIDE_KEYS))
        self.assertEqual(len(placed), len(set(placed)))

    def test_schemes_are_valid_and_multi_hue_where_promised(self):
        for name, colors in schemes.SCHEMES.items():
            self.assertEqual(set(colors), set(schemes.FAMILIES), name)
            for rgb in colors.values():
                self.assertEqual(len(rgb), 3)
                self.assertTrue(all(type(c) is int and 0 <= c <= 255 for c in rgb), name)
        multi = [n for n in schemes.SCHEMES if "one color" not in n]
        self.assertEqual(len(multi), 4)
        for name in multi:
            self.assertEqual(len(set(schemes.SCHEMES[name].values())), 4, name)

    def test_apply_sets_colors_and_keeps_everything_else(self):
        name = next(iter(schemes.SCHEMES))
        base = replace(Settings(), thirds=False, golden_spiral=True, opacity=0.5, thickness=2.0,
                       line_style="dash", orientation=1, mirror=True, glow=True)
        base = replace(base, guide_styles=(("thirds", (1, 2, 3), 0.3, 4.0, "dot"),))
        result = schemes.apply_scheme(base, name)
        for key in GUIDE_KEYS:
            color, opacity, thickness, line_style = style_for(result, key)
            self.assertEqual(color, schemes.scheme_color(name, key))
        # existing per-guide opacity, thickness and style survive; others keep the shared ones
        self.assertEqual(style_for(result, "thirds")[1:], (0.3, 4.0, "dot"))
        self.assertEqual(style_for(result, "golden_spiral")[1:], (0.5, 2.0, "dash"))
        for key in GUIDE_KEYS:
            self.assertEqual(getattr(result, key), getattr(base, key))
        self.assertTrue(result.glow and result.mirror and result.orientation == 1)
        self.assertEqual(result.color, schemes.SCHEMES[name]["structure"])

    def test_families_get_different_colors_in_a_multi_hue_scheme(self):
        result = schemes.apply_scheme(Settings(), "Cargo bay (green, amber, orange, red)")
        self.assertNotEqual(style_for(result, "thirds")[0], style_for(result, "golden_spiral")[0])
        self.assertNotEqual(style_for(result, "golden_spiral")[0], style_for(result, "l_shape")[0])

    def test_default_scheme_and_unknown_names(self):
        styled = schemes.apply_scheme(Settings(), next(iter(schemes.SCHEMES)))
        self.assertEqual(schemes.apply_scheme(styled, schemes.DEFAULT_SCHEME).guide_styles, ())
        with self.assertRaises(KeyError):
            schemes.apply_scheme(Settings(), "Nope")

    def test_current_scheme_is_found_again(self):
        self.assertEqual(schemes.current_scheme(Settings()), schemes.DEFAULT_SCHEME)
        for name in schemes.SCHEMES:
            applied = schemes.apply_scheme(Settings(), name)
            self.assertEqual(schemes.current_scheme(applied), name)
        first = next(iter(schemes.SCHEMES))
        edited = schemes.apply_scheme(Settings(), first)
        edited = replace(edited, guide_styles=tuple(
            (k, (1, 2, 3) if k == "thirds" else c, o, t, st)
            for k, c, o, t, st in edited.guide_styles))
        self.assertEqual(schemes.current_scheme(edited), schemes.CUSTOM_SCHEME)
        one = replace(Settings(), guide_styles=(("thirds", (9, 9, 9), 0.5, 1.0, "solid"),))
        self.assertEqual(schemes.current_scheme(one), schemes.CUSTOM_SCHEME)
        # opacity, thickness and line style per guide do not hide the scheme
        styled = schemes.apply_scheme(replace(Settings(), opacity=0.4, thickness=3.0), first)
        self.assertEqual(schemes.current_scheme(styled), first)
        self.assertNotIn(schemes.CUSTOM_SCHEME, schemes.SCHEMES)

    def test_schemes_survive_save_and_load(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "settings.json"
            wanted = schemes.apply_scheme(replace(Settings(), glow=True),
                                          "Compound (cyan, orange, ice, red)")
            save(path, wanted)
            self.assertEqual(load(path), wanted)


if __name__ == "__main__":
    unittest.main()
