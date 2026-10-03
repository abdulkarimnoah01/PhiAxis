"""Public HOM to renderer data. No private widget names or hierarchy scans."""
from dataclasses import dataclass
from .guides import (Rect, from_bottom_left, fit_aspect, camera_window_corners,
                     gate_from_ndc, FOCAL_UNITS_MM)


@dataclass(frozen=True)
class Frame:
    viewport: Rect
    gate: Rect
    camera_path: str
    gate_source: str = "viewport"


def _obj_camera_corners(camera):
    """World-space frame corners of an OBJ camera, or None if it is not one."""
    import hou
    if camera is None or camera.parm("resx") is None or camera.parm("aperture") is None:
        return None
    value = lambda name: camera.parm(name).eval()
    ortho = camera.parm("projection").evalAsString() == "ortho"
    units = camera.parm("focalunits")
    focal = value("focal") * FOCAL_UNITS_MM.get(units.evalAsString() if units else "mm", 1.0)
    corners = camera_window_corners(
        value("resx"), value("resy"), value("aspect"), value("aperture"), focal,
        (value("winx"), value("winy"), value("winsizex"), value("winsizey")),
        value("orthowidth") if ortho else None)
    transform = camera.worldTransform()
    return [hou.Vector3(point) * transform for point in corners]


def _usd_camera_corners(viewer, camera_path):
    """Near-plane corners of a Solaris (USD) camera, or None if unavailable."""
    import hou
    try:
        from pxr import Usd, UsdGeom
        stage = viewer.stage()
    except (ImportError, AttributeError, hou.Error):
        return None
    if stage is None:
        return None
    prim = stage.GetPrimAtPath(camera_path)
    if not prim or not prim.IsA(UsdGeom.Camera):
        return None
    frustum = UsdGeom.Camera(prim).GetCamera(Usd.TimeCode(hou.frame())).frustum
    near = frustum.ComputeCorners()[:4]  # left-bottom, right-bottom, left-top, right-top
    return [hou.Vector3(tuple(near[i])) for i in (0, 1, 3, 2)]


def projected_gate(viewer, viewport, rect, camera_path):
    """Project the camera's rendered frame through the viewport's real view.

    Follows 2D pan/zoom, camera screen windows and off-center gates. Returns
    None when the camera cannot be projected, so callers can fall back.
    """
    import hou
    camera = viewport.camera()
    corners = (_obj_camera_corners(camera) if camera is not None
               else _usd_camera_corners(viewer, camera_path))
    if not corners:
        return None
    to_ndc = viewport.viewportToNDCTransform()
    ndc = []
    for point in corners:
        x, y = viewport.mapToScreen(point)
        n = hou.Vector4(x, y, 0, 1) * to_ndc
        if not n[3]:
            return None
        ndc.append((n[0] / n[3], n[1] / n[3]))
    return gate_from_ndc(rect, ndc)


def frame_for(viewer, proxy, settings, viewport=None):
    viewport = viewport or viewer.selectedViewport()
    _, _, sw, sh = viewer.geometry()
    rect = from_bottom_left(viewport.geometry(), (sw, sh),
                            (proxy.width(), proxy.height()))
    camera_path = viewport.cameraPath()
    if not (camera_path and settings.fit_camera):
        return Frame(rect, rect, camera_path)
    import hou
    try:
        gate = projected_gate(viewer, viewport, rect, camera_path)
    except (hou.Error, ValueError, ArithmeticError, TypeError, AttributeError):
        gate = None
    if gate is not None:
        return Frame(rect, gate, camera_path, "projected")
    # Fallback: centered, inscribed mask using the masked view aspect.
    aspect = viewport.settings().viewAspectRatio(True)
    # Aspect is reported in HOM UI units. Account for unequal scaling too.
    aspect *= (proxy.width() / sw) / (proxy.height() / sh)
    return Frame(rect, fit_aspect(rect, aspect), camera_path, "centered")


def frames_for(viewer, proxy, settings):
    if settings.scope == "active":
        return (frame_for(viewer, proxy, settings),)
    # Maximized single layout can retain other viewport objects. Query only the
    # selected one in Single, otherwise reject zero-sized hidden quadrants.
    import hou
    viewports = ((viewer.selectedViewport(),) if
                 viewer.viewportLayout() == hou.geometryViewportLayout.Single
                 else viewer.viewports())
    return tuple(frame_for(viewer, proxy, settings, vp) for vp in viewports
                 if vp.geometry()[2] > 0 and vp.geometry()[3] > 0)
