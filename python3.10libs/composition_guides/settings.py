"""Validated settings with no HOM, Qt, scene, or renderer dependency."""
from dataclasses import dataclass
from math import isfinite


# Every guide's enable flag, in drawing order. Labels live in the UI.
GUIDE_KEYS = ("thirds", "golden", "diagonals", "crosshair", "safe_area",
              "golden_triangle", "dynamic_symmetry", "diagonal_phi", "radiating",
              "tunnel", "center_cross", "pyramid", "vanishing_point",
              "leading_lines", "golden_spiral", "circle", "single_diagonal",
              "v_shape", "l_shape", "s_curve", "c_curve", "balance",
              "asymmetric_balance", "golden_rectangles")
LINE_STYLES = ("solid", "dash", "dot")
DYNAMIC_MODES = ("basic", "root2", "root3", "root4", "root5", "rootphi")
# Fields that describe how guides look, as opposed to which guides are shown.
STYLE_FIELDS = ("color", "opacity", "thickness", "line_style", "guide_styles")


def _check_color(color):
    if len(color) != 3 or any(type(c) is not int or not 0 <= c <= 255 for c in color):
        raise ValueError("Color requires three integers from 0 to 255")


def _check_fraction(name, value, low=0.0, high=1.0):
    if isinstance(value, bool) or not isfinite(value) or not low <= value <= high:
        raise ValueError("%s must be between %g and %g" % (name, low, high))


@dataclass(frozen=True)
class Settings:
    color: tuple = (255, 214, 102)
    opacity: float = 0.75
    thickness: float = 1.0
    line_style: str = "solid"
    # Per-guide overrides: ((key, (r, g, b), opacity, thickness, line_style), ...)
    guide_styles: tuple = ()
    fit_camera: bool = True
    thirds: bool = True
    thirds_mode: str = "full"
    golden: bool = False
    crosshair: bool = False
    diagonals: bool = False
    safe_area: bool = False
    golden_spiral: bool = False
    golden_triangle: bool = False
    dynamic_symmetry: bool = False
    dynamic_mode: str = "basic"
    diagonal_phi: bool = False
    radiating: bool = False
    tunnel: bool = False
    center_cross: bool = False
    center_mode: str = "both"
    circle: bool = False
    pyramid: bool = False
    pyramid_inverted: bool = False
    vanishing_point: bool = False
    vanishing_mode: str = "all"
    leading_lines: bool = False
    single_diagonal: bool = False
    v_shape: bool = False
    v_inverted: bool = False
    l_shape: bool = False
    s_curve: bool = False
    c_curve: bool = False
    balance: bool = False
    asymmetric_balance: bool = False
    golden_rectangles: bool = False
    safe_x: float = 0.1
    safe_y: float = 0.1
    scope: str = "active"
    orientation: int = 0
    mirror: bool = False
    flip_vertical: bool = False
    focal_x: float = 0.5
    focal_y: float = 0.5
    radial_count: int = 16
    tunnel_scale: float = 0.35
    circle_scale: float = 0.75
    pyramid_apex_x: float = 0.5
    pyramid_apex_inset: float = 0.0
    leading_width: float = 1.0
    v_apex_x: float = 0.5
    v_apex_y: float = 0.85
    v_width: float = 0.9
    l_inset: float = 0.15
    curvature: float = 0.25
    balance_spacing: float = 0.5
    balance_scale: float = 0.3
    asym_a_x: float = 0.3
    asym_a_y: float = 0.55
    asym_a_scale: float = 0.45
    asym_b_x: float = 0.75
    asym_b_y: float = 0.4
    asym_b_scale: float = 0.2

    def __post_init__(self):
        if self.scope not in ("active", "all"):
            raise ValueError("Scope must be active or all")
        for name in GUIDE_KEYS + ("fit_camera", "mirror", "flip_vertical", "pyramid_inverted",
                                  "v_inverted"):
            if type(getattr(self, name)) is not bool:
                raise ValueError(name + " must be a boolean")
        for margin in (self.safe_x, self.safe_y):
            if isinstance(margin, bool) or not isfinite(margin) or not 0 <= margin < 0.5:
                raise ValueError("Safe margins must be between 0 and 0.5 (exclusive)")
        if self.orientation not in (0, 1, 2, 3):
            raise ValueError("Orientation must be 0, 1, 2, or 3 quarter turns")
        if self.thirds_mode not in ("full", "horizontal", "vertical"):
            raise ValueError("Thirds mode must be full, horizontal, or vertical")
        if self.center_mode not in ("both", "horizontal", "vertical"):
            raise ValueError("Center mode must be both, horizontal, or vertical")
        if self.vanishing_mode not in ("lower", "all"):
            raise ValueError("Vanishing mode must be lower or all")
        if self.dynamic_mode not in DYNAMIC_MODES:
            raise ValueError("Dynamic mode must be one of " + ", ".join(DYNAMIC_MODES))
        if self.line_style not in LINE_STYLES:
            raise ValueError("Line style must be solid, dash, or dot")
        for name in ("focal_x", "focal_y", "pyramid_apex_x", "pyramid_apex_inset",
                     "v_apex_x", "v_apex_y", "asym_a_x", "asym_a_y",
                     "asym_b_x", "asym_b_y"):
            _check_fraction(name, getattr(self, name))
        if type(self.radial_count) is not int or not 4 <= self.radial_count <= 64:
            raise ValueError("Radial count must be an integer from 4 to 64")
        for name in ("tunnel_scale", "circle_scale", "leading_width", "v_width",
                     "balance_scale", "asym_a_scale", "asym_b_scale"):
            _check_fraction(name, getattr(self, name), 0.05, 1)
        _check_fraction("l_inset", self.l_inset, 0, 0.45)
        _check_fraction("curvature", self.curvature, 0.05, 0.5)
        _check_fraction("balance_spacing", self.balance_spacing, 0.05, 0.95)
        _check_color(self.color)
        if not isfinite(self.opacity) or not 0 <= self.opacity <= 1:
            raise ValueError("Opacity must be between 0 and 1")
        if not isfinite(self.thickness) or not 0 < self.thickness <= 20:
            raise ValueError("Thickness must be greater than 0 and at most 20")
        seen = set()
        for entry in self.guide_styles:
            if len(entry) != 5:
                raise ValueError("Guide styles need key, color, opacity, thickness, style")
            key, color, opacity, thickness, style = entry
            if key not in GUIDE_KEYS or key in seen:
                raise ValueError("Unknown or repeated guide style: %r" % (key,))
            seen.add(key)
            _check_color(color)
            _check_fraction("Guide opacity", opacity)
            if not isfinite(thickness) or not 0 < thickness <= 20:
                raise ValueError("Guide thickness must be greater than 0 and at most 20")
            if style not in LINE_STYLES:
                raise ValueError("Guide line style must be solid, dash, or dot")


def style_for(settings, key):
    """(color, opacity, thickness, line_style) for one guide, override or global."""
    for entry in settings.guide_styles:
        if entry[0] == key:
            return tuple(entry[1:])
    return settings.color, settings.opacity, settings.thickness, settings.line_style


def with_guide_style(settings, key, style=None):
    """Return settings with one guide's override replaced, or removed if None."""
    from dataclasses import replace
    styles = tuple(entry for entry in settings.guide_styles if entry[0] != key)
    if style is not None:
        color, opacity, thickness, line_style = style
        styles += ((key, tuple(color), opacity, thickness, line_style),)
    return replace(settings, guide_styles=styles)


def from_dict(values):
    """Settings from JSON-shaped data: lists become the tuples Settings expects."""
    values = dict(values)
    if "color" in values:
        values["color"] = tuple(values["color"])
    if "guide_styles" in values:
        values["guide_styles"] = tuple(
            (key, tuple(color), opacity, thickness, style)
            for key, color, opacity, thickness, style in values["guide_styles"])
    return Settings(**values)


def _read(path):
    import json
    from pathlib import Path
    target = Path(path)
    if not target.exists():
        return {"version": 1, "settings": {}, "presets": {}}
    data = json.loads(target.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("version") != 1:
        raise ValueError("Unsupported PhiAxis settings format")
    return data


def _write(path, data):
    import json
    import os
    import tempfile
    from pathlib import Path
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=target.parent,
                                         delete=False) as stream:
            temporary = stream.name
            json.dump(data, stream, indent=2)
        os.replace(temporary, target)
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)


def load(path):
    data = _read(path)
    return from_dict(data["settings"]) if data.get("settings") else Settings()


def save(path, settings):
    """Save defaults, keeping any user presets already in the file."""
    from dataclasses import asdict
    data = _read(path)
    data["settings"] = asdict(settings)
    _write(path, data)


def load_presets(path):
    """User presets as {name: {field: value}}, guide fields only."""
    return dict(_read(path).get("presets", {}))


def save_preset(path, name, settings):
    """Store the guide selection and parameters of `settings` under `name`."""
    from dataclasses import asdict
    if not name or not name.strip():
        raise ValueError("Preset name cannot be empty")
    data = _read(path)
    values = {key: value for key, value in asdict(settings).items()
              if key not in STYLE_FIELDS + ("scope",)}
    data.setdefault("presets", {})[name.strip()] = values
    _write(path, data)


def delete_preset(path, name):
    data = _read(path)
    data.get("presets", {}).pop(name, None)
    _write(path, data)
