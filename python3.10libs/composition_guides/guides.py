"""Renderer-independent geometry, in top-left-origin logical coordinates."""
from dataclasses import dataclass
from math import cos, isfinite, pi, sin


@dataclass(frozen=True)
class Rect:
    x: float
    y: float
    width: float
    height: float

    def __post_init__(self):
        if not all(isfinite(v) for v in (self.x, self.y, self.width, self.height)):
            raise ValueError("Rectangle must be finite")
        if self.width <= 0 or self.height <= 0:
            raise ValueError("Rectangle dimensions must be positive")


@dataclass(frozen=True)
class GuideGeometry:
    lines: tuple = ()
    polylines: tuple = ()
    ellipses: tuple = ()


def from_bottom_left(bounds, source_size, target_size):
    """Map HOM UI units to Qt logical units; never apply DPR a second time."""
    x, y, width, height = bounds
    sw, sh = source_size
    tw, th = target_size
    if min(sw, sh, tw, th) <= 0:
        raise ValueError("Mapping dimensions must be positive")
    return Rect(x * tw / sw, (sh - y - height) * th / sh,
                width * tw / sw, height * th / sh)


def fit_aspect(rect, aspect):
    """Centered inscribed frame. Only for a conventional centered camera gate."""
    if not isfinite(aspect) or aspect <= 0:
        raise ValueError("Aspect ratio must be positive and finite")
    width = min(rect.width, rect.height * aspect)
    height = width / aspect
    return Rect(rect.x + (rect.width - width) / 2,
                rect.y + (rect.height - height) / 2, width, height)


FOCAL_UNITS_MM = {"mm": 1.0, "m": 1000.0, "nm": 1e-6, "in": 25.4, "ft": 304.8}


def camera_window_corners(resx, resy, pixel_aspect=1.0, aperture=41.4214, focal=50.0,
                          window=(0.0, 0.0, 1.0, 1.0), ortho_width=None, depth=10.0):
    """Camera-space corners of the rendered frame, counter-clockwise from bottom-left.

    `window` is Houdini's (winx, winy, winsizex, winsizey), in units of the full
    frame. Perspective corners lie `depth` units in front of the camera (-Z);
    orthographic corners use `ortho_width`, the full frame width.
    """
    values = (resx, resy, pixel_aspect, aperture, focal, depth) + tuple(window)
    if not all(isfinite(v) for v in values) or min(resx, resy, pixel_aspect) <= 0:
        raise ValueError("Camera resolution and pixel aspect must be positive")
    if ortho_width is None and (aperture <= 0 or focal <= 0):
        raise ValueError("Camera aperture and focal length must be positive")
    if ortho_width is not None and (not isfinite(ortho_width) or ortho_width <= 0):
        raise ValueError("Orthographic width must be positive")
    image_aspect = resx * pixel_aspect / resy
    wx, wy, sx, sy = window
    if sx <= 0 or sy <= 0:
        raise ValueError("Camera window size must be positive")
    width = ortho_width if ortho_width is not None else aperture / focal * depth
    return tuple(((wx + u * sx) * width, (wy + v * sy) / image_aspect * width, -depth)
                 for u, v in ((-.5, -.5), (.5, -.5), (.5, .5), (-.5, .5)))


def gate_from_ndc(viewport, ndc_points):
    """Bounding frame of NDC points ([-1, 1], y up) inside a top-left viewport rect."""
    xs = [viewport.x + (x + 1) / 2 * viewport.width for x, _ in ndc_points]
    ys = [viewport.y + (1 - y) / 2 * viewport.height for _, y in ndc_points]
    return Rect(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))


def thirds(rect, mode="full"):
    """Return full, vertical-only, or horizontal-only thirds."""
    vertical = tuple(
        (rect.x + rect.width * f, rect.y,
         rect.x + rect.width * f, rect.y + rect.height)
        for f in (1 / 3, 2 / 3)
    )
    horizontal = tuple(
        (rect.x, rect.y + rect.height * f,
         rect.x + rect.width, rect.y + rect.height * f)
        for f in (1 / 3, 2 / 3)
    )
    if mode == "vertical":
        return vertical
    if mode == "horizontal":
        return horizontal
    if mode != "full":
        raise ValueError("Thirds mode must be full, horizontal, or vertical")
    return vertical + horizontal


def grid(rect, fractions):
    return tuple((rect.x + rect.width * f, rect.y,
                  rect.x + rect.width * f, rect.y + rect.height) for f in fractions) + tuple(
        (rect.x, rect.y + rect.height * f,
         rect.x + rect.width, rect.y + rect.height * f) for f in fractions)


def _safe_area(rect, settings):
    left = rect.x + rect.width * settings.safe_x
    right = rect.x + rect.width * (1 - settings.safe_x)
    top = rect.y + rect.height * settings.safe_y
    bottom = rect.y + rect.height * (1 - settings.safe_y)
    return ((left, top, right, top), (right, top, right, bottom),
            (right, bottom, left, bottom), (left, bottom, left, top))


def _crosshair(rect):
    cx, cy = rect.x + rect.width / 2, rect.y + rect.height / 2
    arm = min(rect.width, rect.height) * 0.025
    return ((cx - arm, cy, cx + arm, cy), (cx, cy - arm, cx, cy + arm))


def _circle(rect, settings):
    diameter = min(rect.width, rect.height) * settings.circle_scale
    cx = rect.x + rect.width * settings.focal_x
    cy = rect.y + rect.height * settings.focal_y
    return Rect(cx - diameter / 2, cy - diameter / 2, diameter, diameter)


def _lines(values):
    return GuideGeometry(lines=tuple(values))


# One builder per guide flag, in drawing order. Each returns a GuideGeometry.
_BUILDERS = (
    ("thirds", lambda r, s: _lines(thirds(r, s.thirds_mode))),
    ("golden", lambda r, s: _lines(grid(r, ((3 - 5 ** 0.5) / 2, (5 ** 0.5 - 1) / 2)))),
    ("diagonals", lambda r, s: _lines(((r.x, r.y, r.x + r.width, r.y + r.height),
                                       (r.x + r.width, r.y, r.x, r.y + r.height)))),
    ("crosshair", lambda r, s: _lines(_crosshair(r))),
    ("safe_area", lambda r, s: _lines(_safe_area(r, s))),
    ("golden_triangle", lambda r, s: _lines(golden_triangle(r, s.orientation, s.mirror))),
    ("dynamic_symmetry", lambda r, s: _lines(dynamic_symmetry(r, s.dynamic_mode))),
    ("diagonal_phi", lambda r, s: _lines(diagonal_phi(r, s.orientation, s.mirror))),
    ("radiating", lambda r, s: _lines(radiating(r, s.focal_x, s.focal_y, s.radial_count))),
    ("tunnel", lambda r, s: _lines(tunnel(r, s.focal_x, s.focal_y, s.tunnel_scale))),
    ("center_cross", lambda r, s: _lines(center_lines(r, s.center_mode))),
    ("pyramid", lambda r, s: _lines(pyramid(r, s.pyramid_apex_x, s.pyramid_apex_inset,
                                            s.pyramid_inverted))),
    ("vanishing_point", lambda r, s: _lines(vanishing_point(r, s.focal_x, s.focal_y,
                                                            s.vanishing_mode))),
    ("leading_lines", lambda r, s: _lines(leading_lines(r, s.focal_x, s.focal_y,
                                                        s.leading_width))),
    ("golden_spiral", lambda r, s: GuideGeometry(
        polylines=(golden_spiral(r, s.orientation, s.mirror),))),
    ("circle", lambda r, s: GuideGeometry(ellipses=(_circle(r, s),))),
    ("single_diagonal", lambda r, s: _lines(single_diagonal(r, s.orientation, s.mirror))),
    ("v_shape", lambda r, s: _lines(v_shape(r, s.v_apex_x, s.v_apex_y, s.v_width,
                                            s.v_inverted))),
    ("l_shape", lambda r, s: _lines(l_shape(r, s.l_inset, s.orientation, s.mirror))),
    ("s_curve", lambda r, s: GuideGeometry(
        polylines=(s_curve(r, s.curvature, s.orientation, s.mirror),))),
    ("c_curve", lambda r, s: GuideGeometry(
        polylines=(c_curve(r, s.curvature, s.orientation, s.mirror),))),
    ("balance", lambda r, s: balance(r, s.balance_spacing, s.balance_scale)),
    ("asymmetric_balance", lambda r, s: asymmetric_balance(
        r, (s.asym_a_x, s.asym_a_y, s.asym_a_scale),
        (s.asym_b_x, s.asym_b_y, s.asym_b_scale))),
    ("golden_rectangles", lambda r, s: golden_rectangles(r, s.orientation, s.mirror)),
)


def guide_layers(rect, settings):
    """((guide key, GuideGeometry), ...) for every enabled guide, in drawing order.

    Keeping guides separate lets a renderer give each one its own style.
    """
    return tuple((key, build(rect, settings)) for key, build in _BUILDERS
                 if getattr(settings, key))


def guide_geometry(rect, settings):
    """All enabled guides merged into one GuideGeometry."""
    layers = [geometry for _, geometry in guide_layers(rect, settings)]
    return GuideGeometry(tuple(l for g in layers for l in g.lines),
                         tuple(p for g in layers for p in g.polylines),
                         tuple(e for g in layers for e in g.ellipses))


def guide_lines(rect, settings):
    """Immutable line segments suitable for either Qt or a future HDK renderer."""
    return guide_geometry(rect, settings).lines


def _map(rect, point, orientation=0, mirror=False):
    x, y = point
    if mirror:
        x = 1 - x
    for _ in range(orientation):
        x, y = 1 - y, x
    return rect.x + x * rect.width, rect.y + y * rect.height


def _projection(point, start, end):
    dx, dy = end[0] - start[0], end[1] - start[1]
    length2 = dx * dx + dy * dy
    t = ((point[0] - start[0]) * dx + (point[1] - start[1]) * dy) / length2
    return start[0] + t * dx, start[1] + t * dy


def golden_triangle(rect, orientation=0, mirror=False):
    a, b, c, d = tuple(_map(rect, p, orientation, mirror) for p in
                       ((0, 0), (1, 0), (1, 1), (0, 1)))
    return ((a[0], a[1], c[0], c[1]),
            (b[0], b[1], *_projection(b, a, c)),
            (d[0], d[1], *_projection(d, a, c)))


def _clip_line(rect, point, direction):
    px, py = point
    dx, dy = direction
    candidates = []
    if dx:
        for x in (rect.x, rect.x + rect.width):
            t = (x - px) / dx
            y = py + t * dy
            if rect.y - 1e-7 <= y <= rect.y + rect.height + 1e-7:
                candidates.append((t, x, y))
    if dy:
        for y in (rect.y, rect.y + rect.height):
            t = (y - py) / dy
            x = px + t * dx
            if rect.x - 1e-7 <= x <= rect.x + rect.width + 1e-7:
                candidates.append((t, x, y))
    unique = {}
    for item in candidates:
        unique[(round(item[1], 7), round(item[2], 7))] = item
    points = sorted(unique.values())
    if len(points) < 2:
        return None
    return points[0][1], points[0][2], points[-1][1], points[-1][2]


def _armature(rect):
    """Both diagonals plus the four reciprocals (perpendiculars from corners)."""
    a = (rect.x, rect.y)
    b = (rect.x + rect.width, rect.y)
    c = (rect.x + rect.width, rect.y + rect.height)
    d = (rect.x, rect.y + rect.height)
    ac = (c[0] - a[0], c[1] - a[1])
    bd = (d[0] - b[0], d[1] - b[1])
    lines = [(a[0], a[1], c[0], c[1]), (b[0], b[1], d[0], d[1])]
    for point, diagonal in ((a, bd), (c, bd), (b, ac), (d, ac)):
        line = _clip_line(rect, point, (-diagonal[1], diagonal[0]))
        if line is not None:
            lines.append(line)
    return tuple(lines)


def diagonal_phi(rect, orientation=0, mirror=False):
    f = (3 - 5 ** 0.5) / 2
    pairs = (((0, 0), (1, 1)), ((1, 0), (0, 1)),
             ((0, 0), (1, f)), ((0, 0), (f, 1)),
             ((1, 1), (0, 1 - f)), ((1, 1), (1 - f, 0)),
             ((1, 0), (0, f)), ((1, 0), (1 - f, 1)),
             ((0, 1), (1, 1 - f)), ((0, 1), (f, 0)))
    result = []
    for start, end in pairs:
        a, b = _map(rect, start, orientation, mirror), _map(rect, end, orientation, mirror)
        result.append((a[0], a[1], b[0], b[1]))
    return tuple(result)


def radiating(rect, focal_x=0.5, focal_y=0.5, count=16):
    center = (rect.x + rect.width * focal_x, rect.y + rect.height * focal_y)
    lines = []
    for index in range(count):
        angle = 2 * pi * index / count
        dx, dy = cos(angle), sin(angle)
        distances = []
        if dx > 0:
            distances.append((rect.x + rect.width - center[0]) / dx)
        elif dx < 0:
            distances.append((rect.x - center[0]) / dx)
        if dy > 0:
            distances.append((rect.y + rect.height - center[1]) / dy)
        elif dy < 0:
            distances.append((rect.y - center[1]) / dy)
        distance = min(value for value in distances if value >= 0)
        lines.append((center[0], center[1], center[0] + dx * distance,
                      center[1] + dy * distance))
    return tuple(lines)


def tunnel(rect, focal_x=0.5, focal_y=0.5, scale=0.35):
    width, height = rect.width * scale, rect.height * scale
    cx, cy = rect.x + rect.width * focal_x, rect.y + rect.height * focal_y
    left = max(rect.x, min(cx - width / 2, rect.x + rect.width - width))
    top = max(rect.y, min(cy - height / 2, rect.y + rect.height - height))
    right, bottom = left + width, top + height
    outer = ((rect.x, rect.y), (rect.x + rect.width, rect.y),
             (rect.x + rect.width, rect.y + rect.height),
             (rect.x, rect.y + rect.height))
    inner = ((left, top), (right, top), (right, bottom), (left, bottom))
    frame = tuple((*inner[i], *inner[(i + 1) % 4]) for i in range(4))
    connectors = tuple((*outer[i], *inner[i]) for i in range(4))
    return frame + connectors


def center_lines(rect, mode="both"):
    """Return full-frame horizontal, vertical, or paired center lines."""
    cx = rect.x + rect.width * 0.5
    cy = rect.y + rect.height * 0.5
    horizontal = (rect.x, cy, rect.x + rect.width, cy)
    vertical = (cx, rect.y, cx, rect.y + rect.height)
    if mode == "horizontal":
        return (horizontal,)
    if mode == "vertical":
        return (vertical,)
    if mode != "both":
        raise ValueError("Center-line mode must be both, horizontal, or vertical")
    return horizontal, vertical


def pyramid(rect, apex_x=0.5, apex_inset=0.0, inverted=False):
    """A centered or offset triangular composition with an adjustable apex."""
    apex_x = rect.x + rect.width * apex_x
    if inverted:
        apex_y = rect.y + rect.height * (1 - apex_inset)
        base_y = rect.y
    else:
        apex_y = rect.y + rect.height * apex_inset
        base_y = rect.y + rect.height
    return ((rect.x, base_y, apex_x, apex_y),
            (apex_x, apex_y, rect.x + rect.width, base_y),
            (rect.x, base_y, rect.x + rect.width, base_y))


def vanishing_point(rect, focal_x=0.5, focal_y=0.5, mode="all"):
    """Connect lower corners or all frame corners to a movable focal point."""
    focal = (rect.x + rect.width * focal_x, rect.y + rect.height * focal_y)
    bottom = ((rect.x, rect.y + rect.height),
              (rect.x + rect.width, rect.y + rect.height))
    corners = ((rect.x, rect.y), (rect.x + rect.width, rect.y)) + bottom
    points = bottom if mode == "lower" else corners
    if mode not in ("lower", "all"):
        raise ValueError("Vanishing-point mode must be lower or all")
    return tuple((point[0], point[1], focal[0], focal[1]) for point in points)


def leading_lines(rect, focal_x=0.5, focal_y=0.5, width=1.0):
    """A two-line wedge from an adjustable part of the lower frame edge."""
    focal = (rect.x + rect.width * focal_x, rect.y + rect.height * focal_y)
    half_width = rect.width * width * 0.5
    center = rect.x + rect.width * 0.5
    bottom = rect.y + rect.height
    return ((center - half_width, bottom, focal[0], focal[1]),
            (center + half_width, bottom, focal[0], focal[1]))


ROOT_RATIOS = {"root2": 2 ** 0.5, "root3": 3 ** 0.5, "root4": 2.0, "root5": 5 ** 0.5,
               "rootphi": ((1 + 5 ** 0.5) / 2) ** 0.5}


def dynamic_symmetry(rect, mode="basic"):
    """Dynamic-symmetry armature of the frame, or of a fitted root rectangle.

    Root modes fit the largest centered root-N rectangle (its long side follows
    the frame's), draw its armature, and divide it at the reciprocal feet: a
    root-N rectangle holds N reciprocal rectangles, root-phi one at 1/phi.
    """
    if mode == "basic":
        return _armature(rect)
    if mode not in ROOT_RATIOS:
        raise ValueError("Unknown dynamic-symmetry mode: " + str(mode))
    ratio = ROOT_RATIOS[mode]
    landscape = rect.width >= rect.height
    frame = fit_aspect(rect, ratio if landscape else 1 / ratio)
    lines = list(_armature(frame))
    step = 1 / ratio ** 2  # reciprocal foot, as a fraction of the long side
    position = step
    while position < 1 - 1e-9:
        if landscape:
            x = frame.x + frame.width * position
            lines.append((x, frame.y, x, frame.y + frame.height))
        else:
            y = frame.y + frame.height * position
            lines.append((frame.x, y, frame.x + frame.width, y))
        position += step
    border = ((frame.x, frame.y), (frame.x + frame.width, frame.y),
              (frame.x + frame.width, frame.y + frame.height),
              (frame.x, frame.y + frame.height))
    lines.extend((*border[i], *border[(i + 1) % 4]) for i in range(4))
    return tuple(lines)


PHI = (1 + 5 ** 0.5) / 2
_SPIRAL_ARCS = 9


def _golden_arcs():
    """Arc centers and radii of the spiral in a phi-by-1 golden rectangle."""
    centers = [(1.0, 1.0)]
    directions = ((0, -1), (1, 0), (0, 1), (-1, 0))
    for index in range(1, _SPIRAL_ARCS):
        dx, dy = directions[(index - 1) % 4]
        distance = PHI ** -(index + 1)
        previous = centers[-1]
        centers.append((previous[0] + dx * distance, previous[1] + dy * distance))
    return tuple((center, PHI ** -index) for index, center in enumerate(centers))


def _golden_frame(rect, orientation):
    # A landscape golden rectangle is phi by 1. Odd orientations use the
    # rotated 1 by phi frame. Mapping normalized coordinates into those
    # matching aspect ratios preserves every quarter circle in screen pixels.
    return fit_aspect(rect, PHI if orientation % 2 == 0 else 1 / PHI)


def golden_spiral(rect, orientation=0, mirror=False, samples=181):
    """Circular golden-rectangle arcs fitted without non-uniform scaling."""
    arcs = _golden_arcs()
    frame = _golden_frame(rect, orientation)
    result = []
    for index in range(samples):
        progress = _SPIRAL_ARCS * index / (samples - 1)
        arc = min(int(progress), _SPIRAL_ARCS - 1)
        angle = pi + progress * pi / 2
        center, radius = arcs[arc]
        point = ((center[0] + radius * cos(angle)) / PHI,
                 center[1] + radius * sin(angle))
        result.append(_map(frame, point, orientation, mirror))
    return tuple(result)


def golden_rectangles(rect, orientation=0, mirror=False):
    """The fitted golden rectangle and the cuts that divide it into nested squares.

    Spiral arc i is a quarter circle centered on a corner of square i; the
    segment from that center to the arc's end point is the cut separating the
    square from the smaller golden rectangle left over. Each segment is drawn
    once, so dashed line styles stay dashed.
    """
    frame = _golden_frame(rect, orientation)
    outline = tuple(_map(frame, p, orientation, mirror)
                    for p in ((0, 0), (1, 0), (1, 1), (0, 1), (0, 0)))
    cuts = []
    for index, (center, radius) in enumerate(_golden_arcs()):
        end = pi + (index + 1) * pi / 2
        tip = (center[0] + radius * cos(end), center[1] + radius * sin(end))
        a = _map(frame, (center[0] / PHI, center[1]), orientation, mirror)
        b = _map(frame, (tip[0] / PHI, tip[1]), orientation, mirror)
        cuts.append((a[0], a[1], b[0], b[1]))
    return GuideGeometry(lines=tuple(cuts), polylines=(outline,))


def single_diagonal(rect, orientation=0, mirror=False):
    """One corner-to-corner line; orientation and mirror choose which."""
    a, b = _map(rect, (0, 0), orientation, mirror), _map(rect, (1, 1), orientation, mirror)
    return ((a[0], a[1], b[0], b[1]),)


def v_shape(rect, apex_x=0.5, apex_y=0.85, width=0.9, inverted=False):
    """Two lines from the top edge meeting at an apex; inverted opens downward."""
    def point(x, y):
        return (rect.x + rect.width * x,
                rect.y + rect.height * (1 - y if inverted else y))
    apex = point(apex_x, apex_y)
    left, right = point(0.5 - width / 2, 0), point(0.5 + width / 2, 0)
    return ((left[0], left[1], apex[0], apex[1]), (right[0], right[1], apex[0], apex[1]))


def l_shape(rect, inset=0.15, orientation=0, mirror=False):
    """A vertical stroke meeting a horizontal base, inset from one corner."""
    points = [_map(rect, p, orientation, mirror) for p in
              ((inset, inset), (inset, 1 - inset), (1 - inset, 1 - inset))]
    return ((*points[0], *points[1]), (*points[1], *points[2]))


def s_curve(rect, amount=0.25, orientation=0, mirror=False, samples=121):
    """A sine-wave S running the frame's height, swinging `amount` each side."""
    return tuple(_map(rect, (0.5 + amount * sin(2 * pi * t), t), orientation, mirror)
                 for t in (i / (samples - 1) for i in range(samples)))


def c_curve(rect, amount=0.25, orientation=0, mirror=False, samples=91):
    """A half-ellipse C opening to the right, `amount` deep, 80% of the height."""
    result = []
    for i in range(samples):
        theta = -pi / 2 + pi * i / (samples - 1)
        point = (0.5 + amount / 2 - amount * cos(theta), 0.5 + 0.4 * sin(theta))
        result.append(_map(rect, point, orientation, mirror))
    return tuple(result)


def _fulcrum(point, size):
    """Small upward triangle whose apex sits exactly on `point`."""
    x, y = point
    base = y + size * 1.6
    return ((x, y, x - size, base), (x - size, base, x + size, base), (x + size, base, x, y))


def _masses(rect, masses):
    """Circles, the beam joining their centers and a fulcrum at the balance point."""
    unit = min(rect.width, rect.height)
    ellipses, centers, weights = [], [], []
    for x, y, scale in masses:
        cx, cy, d = rect.x + rect.width * x, rect.y + rect.height * y, unit * scale
        ellipses.append(Rect(cx - d / 2, cy - d / 2, d, d))
        centers.append((cx, cy))
        weights.append(d * d)  # visual weight grows with area
    (x1, y1), (x2, y2) = centers
    total = sum(weights)
    pivot = ((x1 * weights[0] + x2 * weights[1]) / total,
             (y1 * weights[0] + y2 * weights[1]) / total)
    lines = ((x1, y1, x2, y2),) + _fulcrum(pivot, unit * 0.02)
    return GuideGeometry(lines=lines, ellipses=tuple(ellipses))


def balance(rect, spacing=0.5, scale=0.3):
    """Two equal regions mirrored about the center, balanced on a central fulcrum."""
    return _masses(rect, ((0.5 - spacing / 2, 0.5, scale), (0.5 + spacing / 2, 0.5, scale)))


def asymmetric_balance(rect, a=(0.3, 0.55, 0.45), b=(0.75, 0.4, 0.2)):
    """Two independently placed regions; the fulcrum marks their area-weighted center."""
    return _masses(rect, (a, b))
