"""Global overlay lifetime, active-view tracking and low-rate change detection."""
from dataclasses import asdict
import sys
import hou
from hutil.PySide import QtCore, QtWidgets
from .adapter import frames_for
from .overlay import CompositionOverlay
from .settings import Settings


class Manager(QtCore.QObject):
    def __init__(self, viewer=None, settings=None):
        super().__init__()
        if viewer is None or not isinstance(viewer, hou.SceneViewer):
            viewer = hou.ui.paneTabOfType(hou.paneTabType.SceneViewer)
        if viewer is None:
            raise RuntimeError("Open a Scene View pane before enabling PhiAxis")
        if hou.getenv("HOUDINI_DISABLE_HUD") not in (None, "", "0"):
            raise RuntimeError("HOUDINI_DISABLE_HUD disables SideFX Qt overlays")
        self.viewer = viewer
        self.settings = settings or Settings()
        self.running = False
        self.error = None
        self._entries = {}
        self._pending = QtCore.QTimer(self)
        self._pending.setSingleShot(True)
        self._pending.timeout.connect(self.refresh)
        self._fallback = QtCore.QTimer(self)
        self._fallback.setInterval(250)
        self._fallback.timeout.connect(self.request_refresh)

    @property
    def overlay(self):
        return self._entries.get(self.viewer)

    def start(self):
        self.running = True
        self._fallback.start()
        self.refresh()

    def set_settings(self, settings):
        self.settings = settings
        self.request_refresh()

    def _viewer_event(self, **kwargs):
        viewer = kwargs.get("viewer")
        kind = kwargs.get("event_type")
        if kind == hou.sceneViewerEvent.ViewerTerminated:
            self._remove(viewer)
        elif kind in (hou.sceneViewerEvent.ViewerActivated,
                      hou.sceneViewerEvent.SelectedViewportChanged):
            if viewer in self._entries:
                self.viewer = viewer
        self.request_refresh()

    def _remove(self, viewer):
        overlay = self._entries.pop(viewer, None)
        if overlay is None:
            return
        try:
            viewer.removeEventCallback(self._viewer_event)
        except (hou.Error, RuntimeError):
            pass
        try:
            overlay.close()
        except RuntimeError:
            pass

    def request_refresh(self):
        if self.running and not self._pending.isActive():
            self._pending.start(0)

    def refresh(self):
        if not self.running:
            return
        try:
            viewers = [p for p in hou.ui.paneTabs() if isinstance(p, hou.SceneViewer)]
            for old in tuple(self._entries):
                if old not in viewers:
                    self._remove(old)
            visible = [v for v in viewers if v.isCurrentTab()]
            if self.viewer not in visible and visible:
                self.viewer = visible[0]
            for viewer in visible:
                if viewer not in self._entries:
                    overlay = CompositionOverlay(viewer, self.settings, self.request_refresh)
                    try:
                        viewer.addEventCallback(self._viewer_event)
                    except Exception:
                        overlay.close()
                        raise
                    self._entries[viewer] = overlay
            for viewer, overlay in tuple(self._entries.items()):
                try:
                    proxy = overlay.parentWidget()
                    show = (viewer in visible and proxy.isVisible()
                            and not overlay.windowContainer().isMinimized()
                            and QtWidgets.QApplication.activeModalWidget() is None
                            and (self.settings.scope == "all" or viewer == self.viewer))
                    if not show:
                        overlay.hide()
                        continue
                    frames = frames_for(viewer, proxy, self.settings)
                    bounds = QtCore.QRect(proxy.mapToGlobal(QtCore.QPoint(0, 0)), proxy.size())
                    if overlay.geometry() != bounds:
                        overlay.setGeometry(bounds)
                    overlay.set_settings(self.settings)
                    overlay.set_frames(frames)
                    if not overlay.isVisible():
                        overlay.show()
                except RuntimeError:
                    self._remove(viewer)
                    raise
            self.error = None
        except (hou.Error, RuntimeError, ValueError, AttributeError) as exc:
            message = str(exc)
            if message != self.error:
                print("PhiAxis: " + message, file=sys.stderr)
            self.error = message
            for overlay in self._entries.values():
                try:
                    overlay.hide()
                except RuntimeError:
                    pass

    def stop(self):
        self.running = False
        self._pending.stop()
        self._fallback.stop()
        for viewer in tuple(self._entries):
            self._remove(viewer)
        self.deleteLater()

    def diagnostics(self):
        overlay = self.overlay
        return {
            "enabled": self.running, "houdini": hou.applicationVersionString(),
            "python": sys.version, "qt": QtCore.qVersion(),
            "visible": bool(overlay and overlay.isVisible()),
            "device_pixel_ratio": overlay.devicePixelRatioF() if overlay else None,
            "frame": asdict(overlay._frame) if overlay and overlay._frame else None,
            "frames": [asdict(f) for o in self._entries.values() if o.isVisible()
                       for f in o._frames],
            "overlay_count": len(self._entries), "settings": asdict(self.settings),
            "error": self.error, "fallback_interval_ms": 250,
        }
