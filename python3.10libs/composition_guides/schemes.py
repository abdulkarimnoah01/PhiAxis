"""Color schemes: ready-made Style presets that give each family of guides its own hue.

Pure Python. A scheme only sets colors (the global one and one per guide); each guide keeps
its own opacity, thickness and line style. They are designed for the glow, after the
phosphor screens of science-fiction control rooms: contrast comes from different hues, not
from shades of one.
"""
from dataclasses import replace
from .settings import GUIDE_KEYS, style_for

FAMILIES = {
    "structure": ("thirds", "golden", "crosshair", "center_cross", "diagonals",
                  "single_diagonal", "safe_area"),
    "golden": ("golden_spiral", "golden_rectangles", "golden_triangle", "diagonal_phi",
               "dynamic_symmetry"),
    "perspective": ("radiating", "tunnel", "vanishing_point", "leading_lines"),
    "shapes": ("pyramid", "v_shape", "l_shape", "s_curve", "c_curve", "circle", "balance",
               "asymmetric_balance"),
}
FAMILY_OF = {key: family for family, keys in FAMILIES.items() for key in keys}

# family colors: structure, golden, perspective, shapes
SCHEMES = {
    "Cargo bay (green, amber, orange, red)":
        dict(structure=(140, 235, 150), golden=(245, 200, 60), perspective=(245, 135, 50),
             shapes=(240, 92, 88)),
    "Compound (cyan, orange, ice, red)":
        dict(structure=(60, 190, 235), golden=(255, 130, 50), perspective=(170, 235, 250),
             shapes=(240, 80, 70)),
    "Computer (yellow, teal, amber, pale)":
        dict(structure=(235, 215, 80), golden=(90, 205, 215), perspective=(240, 150, 50),
             shapes=(255, 235, 170)),
    "Quota (teal, amber, pale, coral)":
        dict(structure=(120, 205, 190), golden=(255, 170, 50), perspective=(215, 235, 225),
             shapes=(255, 110, 80)),
    "Amber phosphor (one color)":
        dict(structure=(255, 150, 28), golden=(255, 150, 28), perspective=(255, 150, 28),
             shapes=(255, 150, 28)),
    "Green phosphor (one color)":
        dict(structure=(120, 255, 70), golden=(120, 255, 70), perspective=(120, 255, 70),
             shapes=(120, 255, 70)),
}
DEFAULT_SCHEME = "Single color (default)"
CUSTOM_SCHEME = "Custom (your own per-guide styles)"


def scheme_color(name, key):
    return SCHEMES[name][FAMILY_OF[key]]


def current_scheme(settings):
    """Name of the scheme whose colors every guide uses, DEFAULT_SCHEME when no guide has its
    own style, else CUSTOM_SCHEME (a mix, or a scheme edited by hand)."""
    if not settings.guide_styles:
        return DEFAULT_SCHEME
    for name in SCHEMES:
        if all(tuple(style_for(settings, key)[0]) == tuple(scheme_color(name, key))
               for key in GUIDE_KEYS):
            return name
    return CUSTOM_SCHEME


def apply_scheme(settings, name):
    """Settings with the scheme's colors. The default scheme removes every per-guide style
    (colors, and any opacity, thickness or line style set per guide) and keeps the shared one."""
    if name == DEFAULT_SCHEME:
        return replace(settings, guide_styles=())
    if name not in SCHEMES:
        raise KeyError("Unknown color scheme: %r" % (name,))
    styles = []
    for key in GUIDE_KEYS:
        _color, opacity, thickness, line_style = style_for(settings, key)
        styles.append((key, tuple(scheme_color(name, key)), opacity, thickness, line_style))
    return replace(settings, color=tuple(SCHEMES[name]["structure"]), guide_styles=tuple(styles))
