"""Runs inside a real Houdini (started by test_update_in_houdini.py): the artist's
"Check for Updates" flow. hou.ui dialogs are replaced by recorders that answer for the artist.
"""
import json
import os
import traceback
import hou
from hutil.PySide import QtCore

OUT = os.environ["PHIAXIS_TEST_OUT"]
LOG = {"messages": [], "inputs": [], "scenarios": []}
ANSWERS = {"display": [0], "input": [(0, "")]}      # Install / Save


def display_message(text, buttons=("OK",), **kwargs):
    LOG["messages"].append({"text": text, "buttons": list(buttons)})
    return ANSWERS["display"][0]


def read_input(message, buttons=("OK",), **kwargs):
    LOG["inputs"].append(message)
    return ANSWERS["input"][0]


def run():
    try:
        hou.ui.displayMessage = display_message
        hou.ui.readInput = read_input
        import composition_guides as cg
        LOG["version"] = cg.__version__
        LOG["file"] = cg.__file__
        # 1. an update exists: the artist presses Install
        cg.check_for_updates()
        LOG["scenarios"].append("install")
        # 2. the artist declines
        before = len(LOG["messages"])
        os.environ["PHIAXIS_UPDATE_SOURCE"] = os.environ["PHIAXIS_TEST_FEED_SAME"]
        cg.check_for_updates()
        LOG["up_to_date"] = LOG["messages"][before:]
        # 3. no source anywhere: the artist is asked, and cancels
        os.environ.pop("PHIAXIS_UPDATE_SOURCE", None)
        ANSWERS["input"] = [(1, "")]
        cg.check_for_updates()
    except Exception:
        LOG["error"] = traceback.format_exc()
    with open(os.path.join(OUT, "houdini_log.json"), "w") as stream:
        json.dump(LOG, stream, indent=2)
    hou.exit(suppress_save_prompt=True)


QtCore.QTimer.singleShot(3000, run)
