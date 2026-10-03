"""PhiAxis node-free composition guides. Importing has no UI side effects."""
__version__ = "0.7.2"
_SESSION_KEY = "_composition_guides_manager_v1"
_SETTINGS_KEY = "_composition_guides_settings_v1"
_UI_KEY = "_composition_guides_dialog_v1"
STALE_SESSION_MESSAGE = (
    "PhiAxis was updated while Houdini was running, so this session holds a mix of old and "
    "new files.\n\nRestart Houdini to finish the update.")


def _current():
    import hou
    return getattr(hou.session, _SESSION_KEY, None)


def enable(scene_viewer=None, settings=None):
    """Enable once, bound to the chosen Scene Viewer's selected viewport."""
    import hou
    if not hou.isUIAvailable():
        raise RuntimeError("PhiAxis requires Houdini's GUI")
    current = _current()
    if current is not None:
        return current
    from .manager import Manager
    from .settings import Settings
    from dataclasses import asdict
    settings = Settings(**asdict(settings or get_settings()))
    manager = Manager(scene_viewer, settings)
    setattr(hou.session, _SETTINGS_KEY, manager.settings)
    setattr(hou.session, _SESSION_KEY, manager)
    try:
        manager.start()
        _sync_dialog()
    except Exception:
        disable()
        raise
    return manager


def disable():
    import hou
    manager = _current()
    if manager is not None:
        setattr(hou.session, _SETTINGS_KEY, manager.settings)
        delattr(hou.session, _SESSION_KEY)
        manager.stop()
        _sync_dialog()


def toggle(scene_viewer=None):
    if _current() is not None:
        disable()
        return False
    enable(scene_viewer)
    return True


def reload_plugin():
    """Explicit hot reload: stop old owners before replacing class definitions."""
    import importlib
    import sys
    manager = _current()
    was_enabled = manager is not None
    viewer = manager.viewer if was_enabled else None
    settings = manager.settings if was_enabled else None
    close_settings()
    disable()
    # The package itself first, so functions added in a newer version exist before the
    # submodules (which import names from it) are reloaded. State lives in hou.session.
    importlib.reload(sys.modules[__name__])
    for name in ("guides", "settings", "presets", "updater", "update_ui", "adapter",
                 "overlay", "manager", "ui"):
        module = sys.modules.get(__name__ + "." + name)
        if module is not None:
            importlib.reload(module)
    if was_enabled:
        return enable(viewer, settings)


def diagnostics():
    manager = _current()
    return manager.diagnostics() if manager else {"enabled": False}


def settings_path():
    import hou
    from pathlib import Path
    return Path(hou.getenv("HOUDINI_USER_PREF_DIR")) / "composition_guides.json"


def get_settings():
    import hou
    import warnings
    from .settings import Settings, load
    from dataclasses import asdict
    current = getattr(hou.session, _SETTINGS_KEY, None)
    if current is None:
        try:
            current = load(settings_path())
        except (OSError, ValueError, TypeError, KeyError) as exc:
            warnings.warn("Cannot load PhiAxis defaults: " + str(exc))
            current = Settings()
        setattr(hou.session, _SETTINGS_KEY, current)
    current = Settings(**asdict(current))
    setattr(hou.session, _SETTINGS_KEY, current)
    return current


def set_settings(settings, persist=False):
    import hou
    from dataclasses import asdict
    from .settings import Settings, save
    settings = Settings(**asdict(settings))
    if persist:
        save(settings_path(), settings)
    setattr(hou.session, _SETTINGS_KEY, settings)
    manager = _current()
    if manager:
        manager.set_settings(settings)


def flip(axis):
    """Flip the golden ratio guides ("horizontal" left-right or "vertical" up-down) and
    return the new state. Works whether or not PhiAxis is currently drawing."""
    from dataclasses import replace
    field = {"horizontal": "mirror", "vertical": "flip_vertical"}.get(axis)
    if field is None:
        raise ValueError("axis must be 'horizontal' or 'vertical'")
    current = get_settings()
    new = not getattr(current, field)
    set_settings(replace(current, **{field: new}))
    _sync_dialog()
    return new


def show_settings():
    import hou
    if not hou.isUIAvailable():
        raise RuntimeError("PhiAxis requires Houdini's GUI")
    dialog = getattr(hou.session, _UI_KEY, None)
    if dialog is None:
        try:
            from .ui import SettingsDialog
        except ImportError:
            # Newer files on disk than the package held in this session (an update installed
            # while Houdini was running).
            hou.ui.displayMessage(STALE_SESSION_MESSAGE, title="PhiAxis",
                                  severity=hou.severityType.Warning)
            return None
        dialog = SettingsDialog()
        setattr(hou.session, _UI_KEY, dialog)
    dialog.sync()
    dialog.show()
    dialog.raise_()
    dialog.activateWindow()
    return dialog


def check_for_updates():
    """Ask the update source for a newer PhiAxis and offer to install it (explicit only)."""
    from .update_ui import check_for_updates as run
    return run()


def close_settings():
    import hou
    dialog = getattr(hou.session, _UI_KEY, None)
    if dialog is not None:
        delattr(hou.session, _UI_KEY)
        dialog.close()


def _sync_dialog():
    import hou
    dialog = getattr(hou.session, _UI_KEY, None)
    if dialog is not None:
        dialog.sync()
