"""Disposable GUI test: flipping the golden ratio guides left-right and up-down.

Launch in its own Houdini process with isolated preferences:
    tests\\run_gui.ps1 demo\\phiaxis_painting_gallery.hip tests\\flip_houdini.py flip

Draws only the golden spiral and renders the overlay offscreen (QWidget.grab). The painted
pixels' center of mass must move to the mirrored side for each flip, through the panel's
checkboxes and through composition_guides.flip (the Python API).
"""
from dataclasses import replace
from pathlib import Path
import json
import os
import traceback
import hou
from hutil.PySide import QtCore

import composition_guides as cg
from composition_guides.settings import GUIDE_KEYS

ROOT = Path(cg.__file__).resolve().parents[2]
OUT = ROOT / "tests" / "results" / os.environ.get("CG_TEST_RUN", "flip")
OUT.mkdir(parents=True, exist_ok=True)
CAMERA = "/obj/PHIAXIS_PAINTING_GALLERY/CAM_RULE_OF_THIRDS"
evidence = []
state = {}
viewer = hou.ui.paneTabOfType(hou.paneTabType.SceneViewer)
before = tuple(node.path() for node in hou.node("/").allSubChildren())


def record(case, passed, **details):
    evidence.append(dict(case=case, passed=bool(passed), **details))


def center_of_mass():
    image = cg._current().overlay.grab().toImage()
    sx = sy = count = 0
    for y in range(0, image.height(), 2):
        for x in range(0, image.width(), 2):
            if image.pixelColor(x, y).alpha() > 60:
                sx += x
                sy += y
                count += 1
    return (sx / count, sy / count, image.width(), image.height()) if count else None


def start():
    viewer.selectedViewport().setCamera(hou.node(CAMERA))
    only_spiral = {key: key == "golden_spiral" for key in GUIDE_KEYS}
    cg.set_settings(replace(cg.get_settings(), mirror=False, flip_vertical=False,
                            orientation=0, **only_spiral))
    cg.enable(viewer)
    state["dialog"] = cg.show_settings()


def measure_plain():
    state["plain"] = center_of_mass()
    record("spiral is painted", state["plain"] is not None, center=state["plain"])


def flip_left_right_by_panel():
    dialog = state["dialog"]
    dialog.mirror.setChecked(True)


def check_left_right():
    plain, now = state["plain"], center_of_mass()
    record("panel flip left-right mirrors the painting",
           now is not None and cg.get_settings().mirror and
           abs((now[0] + plain[0]) - plain[2]) < plain[2] * 0.02 and abs(now[1] - plain[1]) < 6,
           plain=plain, flipped=now)
    state["dialog"].mirror.setChecked(False)


def flip_up_down_by_panel():
    state["dialog"].flip_vertical.setChecked(True)


def check_up_down():
    plain, now = state["plain"], center_of_mass()
    record("panel flip up-down mirrors the painting",
           now is not None and cg.get_settings().flip_vertical and
           abs((now[1] + plain[1]) - plain[3]) < plain[3] * 0.02 and abs(now[0] - plain[0]) < 6,
           plain=plain, flipped=now)
    state["dialog"].flip_vertical.setChecked(False)


def shelf_function():
    first = cg.flip("horizontal")
    state["h_on"] = first and cg.get_settings().mirror and state["dialog"].mirror.isChecked()
    second = cg.flip("horizontal")
    state["h_off"] = (not second) and not cg.get_settings().mirror
    third = cg.flip("vertical")
    state["v_on"] = third and cg.get_settings().flip_vertical and \
        state["dialog"].flip_vertical.isChecked()
    cg.flip("vertical")
    try:
        cg.flip("sideways")
        state["bad_axis"] = False
    except ValueError:
        state["bad_axis"] = True
    record("flip() toggles each axis, updates the panel, rejects other axes",
           state["h_on"] and state["h_off"] and state["v_on"] and state["bad_axis"],
           horizontal_on=state["h_on"], horizontal_off=state["h_off"],
           vertical_on=state["v_on"], rejects_bad_axis=state["bad_axis"])


def both_flips_and_reload():
    cg.flip("horizontal")
    cg.flip("vertical")
    cg.reload_plugin()
    settings = cg.get_settings()
    record("both flips survive a hot reload", settings.mirror and settings.flip_vertical)
    record("scene unchanged",
           tuple(node.path() for node in hou.node("/").allSubChildren()) == before)


steps = [start, measure_plain, flip_left_right_by_panel, check_left_right, flip_up_down_by_panel,
         check_up_down, shelf_function, both_flips_and_reload]


def advance():
    try:
        if not steps:
            cg.close_settings()
            cg.disable()
            failures = [e["case"] for e in evidence if not e["passed"]]
            (OUT / "results.json").write_text(json.dumps({
                "houdini": hou.applicationVersionString(),
                "status": "failed" if failures else "passed", "failures": failures,
                "cases": evidence}, indent=2, default=str), encoding="utf-8")
            hou.exit(suppress_save_prompt=True)
            return
        steps.pop(0)()
        QtCore.QTimer.singleShot(900, advance)
    except Exception:
        (OUT / "error.txt").write_text(traceback.format_exc() + "\n" +
                                       json.dumps(evidence, indent=2, default=str),
                                       encoding="utf-8")
        cg.disable()
        hou.exit(suppress_save_prompt=True)


QtCore.QTimer.singleShot(2500, advance)
