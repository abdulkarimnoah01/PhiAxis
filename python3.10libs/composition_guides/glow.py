"""Glow math with no HOM or Qt dependency, so it can be tested with plain Python.

The overlay draws every guide line as a few wide, faint strokes added to the picture
(the halo) and then one narrow, bright stroke on top (the core).
"""
# (width multiplier, alpha out of 255 at an amount of 1), widest and faintest first.
HALO = ((11, 12), (6, 26), (3, 56))
MIN_CORE_WIDTH = 1.25
MAX_AMOUNT = 2.0


def lighten(color, t=0.55):
    """`color` moved toward white; the core of a glowing line looks lit from inside."""
    return tuple(int(round(c + (255 - c) * t)) for c in color)


def core_width(thickness):
    return max(float(thickness), MIN_CORE_WIDTH)


def halo_layers(color, opacity, thickness, amount):
    """[(rgb, alpha 0..255, width in px)] for the halo, widest first; empty without glow."""
    amount = max(0.0, min(float(amount), MAX_AMOUNT))
    if amount <= 0:
        return []
    base = core_width(thickness)
    strength = amount * max(float(opacity), 0.35)
    return [(tuple(color), min(255, int(round(alpha * strength))),
             base * (1 + (multiplier - 1) * min(amount, 1.6)))
            for multiplier, alpha in HALO]
