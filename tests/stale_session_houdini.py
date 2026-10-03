"""Disposable GUI test: a Houdini session that holds an OLD PhiAxis package in memory while
newer files are on disk (an update installed while Houdini stayed open).

    tests\\run_gui.ps1 none tests\\stale_session_houdini.py stale 22.0.368

Simulates it by deleting names the newer package added from the loaded module and forgetting
the lazily imported submodules, then opens the settings panel and presses its update button.
Neither may raise; the artist gets a plain message, and a hot reload brings the names back.
"""
from pathlib import Path
import json
import os
import sys
import traceback
import hou
from hutil.PySide import QtCore

import composition_guides as _cg
ROOT = Path(_cg.__file__).resolve().parents[2]   # python3.10libs/composition_guides/__init__.py
OUT = ROOT / "tests" / "results" / os.environ.get("CG_TEST_RUN", "stale")
OUT.mkdir(parents=True, exist_ok=True)
log = {"messages": []}


def run():
    try:
        import composition_guides as cg
        hou.ui.displayMessage = lambda text, **kw: (log["messages"].append(text), 0)[1]
        # An old package: it never had check_for_updates, and the panel module is not loaded yet.
        del cg.check_for_updates
        for name in [n for n in sys.modules if n.startswith("composition_guides.") and
                     n.split(".")[-1] in ("ui", "update_ui")]:
            del sys.modules[name]
        dialog = cg.show_settings()
        log["panel_opened"] = dialog is not None
        from composition_guides import ui
        ui.run_update_check()                      # what the button does; must not raise
        log["button_ok"] = True
        cg.reload_plugin()                         # a hot reload restores the new names
        log["restored"] = hasattr(cg, "check_for_updates")
    except Exception:
        log["error"] = traceback.format_exc()
    (OUT / "results.json").write_text(json.dumps(log, indent=2), encoding="utf-8")
    hou.exit(suppress_save_prompt=True)


QtCore.QTimer.singleShot(3000, run)
