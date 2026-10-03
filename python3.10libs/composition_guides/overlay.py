"""Qt renderer, using SideFX's documented viewer window integration."""
import hou
from hutil.PySide import QtCore, QtGui
from . import glow
from .guides import guide_layers
from .settings import style_for

PEN_STYLES = {"solid": QtCore.Qt.SolidLine, "dash": QtCore.Qt.DashLine,
              "dot": QtCore.Qt.DotLine}


class CompositionOverlay(hou.qt.ViewerOverlay):
    def __init__(self, viewer, settings, request_refresh):
        self._request_refresh = request_refresh
        self._frame = None
        self._frames = ()
        self._settings = settings
        self._closed = False
        super().__init__(viewer)
        self.setObjectName("composition_guides_thirds")
        self.setFocusPolicy(QtCore.Qt.NoFocus)
        self.setAttribute(QtCore.Qt.WA_ShowWithoutActivating, True)

    def onInitWindow(self):
        super().onInitWindow()
        # Native WindowTransparentForInput and Qt mouse transparency are set by
        # SideFX. No synthetic key forwarding or viewer-state registration here.

    def schedule_refresh(self, *args):
        if not self._closed:
            self._request_refresh()

    onBeginResize = schedule_refresh
    onResizing = schedule_refresh
    onEndResize = schedule_refresh
    onSizeChanged = schedule_refresh
    onLayoutChanged = schedule_refresh
    onWindowPlacement = schedule_refresh

    def onParentWindowEvent(self, event):
        self.schedule_refresh()

    def onContainerWindowEvent(self, event):
        if self.windowContainer().isMinimized():
            self.hide()
        self.schedule_refresh()

    def set_frame(self, frame):
        self.set_frames((frame,))

    def set_frames(self, frames):
        if self._frames != frames:
            self._frames = frames
            self._frame = frames[0] if frames else None
            self.update()

    def set_settings(self, settings):
        if self._settings != settings:
            self._settings = settings
            self.update()

    def _pen(self, key):
        color, opacity, thickness, line_style = style_for(self._settings, key)
        glowing = self._settings.glow
        qcolor = QtGui.QColor(*(glow.lighten(color) if glowing else color))
        qcolor.setAlphaF(opacity)
        pen = QtGui.QPen(qcolor)
        pen.setWidthF(glow.core_width(thickness) if glowing else thickness)
        pen.setStyle(PEN_STYLES[line_style])
        return pen

    def _halo_pens(self, key):
        """Faint, wide strokes drawn first and added to the picture; none without glow."""
        if not self._settings.glow:
            return []
        color, opacity, thickness, line_style = style_for(self._settings, key)
        pens = []
        for rgb, alpha, width in glow.halo_layers(color, opacity, thickness,
                                                  self._settings.glow_amount):
            qcolor = QtGui.QColor(*rgb)
            qcolor.setAlpha(alpha)
            pen = QtGui.QPen(qcolor)
            pen.setWidthF(width)
            pen.setStyle(PEN_STYLES[line_style])
            pen.setCapStyle(QtCore.Qt.RoundCap)
            pen.setJoinStyle(QtCore.Qt.RoundJoin)
            pens.append(pen)
        return pens

    @staticmethod
    def _draw(painter, geometry):
        for line in geometry.lines:
            painter.drawLine(QtCore.QLineF(*line))
        for polyline in geometry.polylines:
            painter.drawPolyline(QtGui.QPolygonF(
                [QtCore.QPointF(x, y) for x, y in polyline]))
        for ellipse in geometry.ellipses:
            painter.drawEllipse(QtCore.QRectF(
                ellipse.x, ellipse.y, ellipse.width, ellipse.height))

    def paintEvent(self, event):
        if self._closed or self._frame is None:
            return
        painter = QtGui.QPainter(self)
        try:
            painter.setRenderHint(QtGui.QPainter.Antialiasing)
            pens, halos = {}, {}
            for frame in self._frames:
                painter.save()
                rect = frame.viewport
                painter.setClipRect(QtCore.QRectF(rect.x, rect.y, rect.width, rect.height))
                for key, geometry in guide_layers(frame.gate, self._settings):
                    if key not in pens:
                        pens[key] = self._pen(key)
                        halos[key] = self._halo_pens(key)
                    if halos[key]:
                        painter.setCompositionMode(QtGui.QPainter.CompositionMode_Plus)
                        for halo_pen in halos[key]:
                            painter.setPen(halo_pen)
                            self._draw(painter, geometry)
                        painter.setCompositionMode(QtGui.QPainter.CompositionMode_SourceOver)
                    painter.setPen(pens[key])
                    self._draw(painter, geometry)
                painter.restore()
        finally:
            painter.end()

    def closeEvent(self, event):
        self._closed = True
        self._request_refresh = lambda: None
        # Removes the SideFX viewer callback and both parent/container filters.
        super().closeEvent(event)
