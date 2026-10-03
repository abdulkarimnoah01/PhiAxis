"""The Houdini side of updating: a few plain Houdini dialogs around updater.py.

Nothing here runs by itself. The artist clicks "Check for Updates" (shelf tool or the
button in the settings panel), sees what is new, and decides.
"""
import os
import tempfile
from pathlib import Path

import hou

from . import __version__, updater

TITLE = "PhiAxis updates"


def _install_root():
    return os.path.join(os.environ.get("LOCALAPPDATA", ""), "PhiAxis")


def _is_installed_copy():
    """True when this PhiAxis was put in place by the installer (not a development copy)."""
    root = Path(_install_root()) / "versions"
    try:
        return Path(__file__).resolve().is_relative_to(root.resolve())
    except (OSError, ValueError):
        return False


def _warn(text):
    hou.ui.displayMessage(text, title=TITLE, severity=hou.severityType.Warning)


def check_for_updates():
    prefs = hou.getenv("HOUDINI_USER_PREF_DIR")
    if not _is_installed_copy():
        hou.ui.displayMessage(
            "This copy of PhiAxis (%s) is running from\n%s\nand was not put in place by the "
            "PhiAxis installer, so it is not updated from here." % (
                __version__, Path(__file__).resolve().parent.parent),
            title=TITLE)
        return
    source = updater.update_source(prefs, _install_root())
    if not source:
        button, value = hou.ui.readInput(
            "Where do PhiAxis updates come from?\n\nPaste the shared folder or the https:// "
            "address you were given with PhiAxis.",
            buttons=("Save", "Cancel"), default_choice=0, close_choice=1, title=TITLE)
        if button != 0 or not value.strip():
            return
        source = value.strip()
        updater.save_update_source(prefs, source)
    try:
        manifest = updater.check(source, __version__, hou.applicationVersion())
    except updater.UpdateError as exc:
        _warn(str(exc))
        return
    if manifest is None:
        hou.ui.displayMessage("PhiAxis %s is up to date." % __version__, title=TITLE)
        return
    notes = "\n".join("  - " + note for note in manifest.get("notes", [])[:8])
    choice = hou.ui.displayMessage(
        "PhiAxis %s is available (you have %s).\n\n%s\n\nInstall it now? Houdini needs a "
        "restart afterwards." % (manifest["version"], __version__, notes or "(no notes)"),
        buttons=("Install", "Later"), default_choice=0, close_choice=1, title=TITLE)
    if choice != 0:
        return
    try:
        with tempfile.TemporaryDirectory(prefix="phiaxis_download_") as folder:
            archive = updater.download(source, manifest, folder)
            ok, output = updater.install(archive)
    except updater.UpdateError as exc:
        _warn(str(exc))
        return
    if ok:
        hou.ui.displayMessage(
            "PhiAxis %s is installed.\n\nRestart Houdini to start using it." % manifest["version"],
            title=TITLE)
    else:
        _warn("The update could not be installed.\n\n" + output[-1500:])
