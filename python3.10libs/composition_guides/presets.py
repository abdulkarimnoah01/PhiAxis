"""Named guide combinations. Presets change which guides show, never the style."""
from dataclasses import asdict
from .settings import GUIDE_KEYS, STYLE_FIELDS, from_dict


BUILTIN = {
    "Photography": dict(thirds=True, thirds_mode="full", crosshair=True),
    "Cinematography": dict(thirds=True, thirds_mode="full", safe_area=True,
                           safe_x=0.1, safe_y=0.1, crosshair=True, fit_camera=True),
    "Portrait": dict(golden=True, golden_spiral=True, orientation=0, mirror=False),
    "Landscape": dict(thirds=True, thirds_mode="horizontal", leading_lines=True,
                      focal_x=0.5, focal_y=0.4, leading_width=0.9),
}


def apply(settings, values):
    """Turn every guide off, then apply a preset's guides and parameters.

    Style fields (color, opacity, thickness, line styles) and coverage scope are
    kept from `settings`, so a preset never changes how guides look.
    """
    base = asdict(settings)
    base.update({key: False for key in GUIDE_KEYS})
    base.update({key: value for key, value in values.items()
                 if key not in STYLE_FIELDS + ("scope",)})
    return from_dict(base)


def apply_builtin(settings, name):
    return apply(settings, BUILTIN[name])
