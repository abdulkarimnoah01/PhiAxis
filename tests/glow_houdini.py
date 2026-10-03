"""Disposable GUI test: glow and color schemes through the settings panel.

Launch in its own Houdini process with isolated preferences:
    tests\run_gui.ps1 demo\phiaxis_painting_gallery.hip tests\glow_houdini.py glow

Draws one guide, renders the overlay offscreen (QWidget.grab) and compares the painted pixels
with glow off, on, at 0 and at 200%; applies a color scheme from the panel and looks for its
colors in the picture.
"""
from dataclasses import replace
from pathlib import Path
import json
import os
import traceback
import hou
from hutil.PySide import QtCore

import composition_guides as cg
from composition_guides import schemes
from composition_guides.settings import GUIDE_KEYS, style_for

ROOT = Path(cg.__file__).resolve().parents[2]
OUT = ROOT / "tests" / "results" / os.environ.get("CG_TEST_RUN", "glow")
OUT.mkdir(parents=True, exist_ok=True)
CAMERA = "/obj/PHIAXIS_PAINTING_GALLERY/CAM_RULE_OF_THIRDS"
evidence = []
state = {}
viewer = hou.ui.paneTabOfType(hou.paneTabType.SceneViewer)
before = tuple(node.path() for node in hou.node("/").allSubChildren())
SCHEME = "Cargo bay (green, amber, orange, red)"


def record(case, passed, **details):
    evidence.append(dict(case=case, passed=bool(passed), **details))


def mass():
    """(sum of alpha, pixels with any alpha) over the overlay."""
    image = cg._current().overlay.grab().toImage()
    total = pixels = 0
    for y in range(0, image.height(), 2):
        for x in range(0, image.width(), 2):
            alpha = image.pixelColor(x, y).alpha()
            if alpha:
                total += alpha
                pixels += 1
    return total, pixels


def count_color(rgb, tolerance=45):
    image = cg._current().overlay.grab().toImage()
    hits = 0
    for y in range(0, image.height(), 2):
        for x in range(0, image.width(), 2):
            c = image.pixelColor(x, y)
            if (c.alpha() > 50 and abs(c.red() - rgb[0]) < tolerance and
                    abs(c.green() - rgb[1]) < tolerance and abs(c.blue() - rgb[2]) < tolerance):
                hits += 1
    return hits


def start():
    viewer.selectedViewport().setCamera(hou.node(CAMERA))
    only = {key: key in ("golden_spiral", "thirds") for key in GUIDE_KEYS}
    cg.set_settings(replace(cg.get_settings(), glow=False, glow_amount=1.0, guide_styles=(),
                            **only))
    cg.enable(viewer)
    state["dialog"] = cg.show_settings()
    state["dialog"].tabs.setCurrentIndex(2)
    state["dialog"].sync()


def measure_off():
    state["off"] = mass()
    record("overlay paints with glow off", state["off"][1] > 500, mass=state["off"])
    dialog = state["dialog"]
    record("panel shows glow off and its amount disabled",
           not dialog.glow.isChecked() and not dialog.glow_amount.isEnabled())
    dialog.glow.setChecked(True)


def measure_on():
    settings = cg.get_settings()
    state["on"] = mass()
    record("panel checkbox turns glow on", settings.glow)
    record("glow adds a halo (more painted area and alpha)",
           state["on"][1] > state["off"][1] * 1.5 and state["on"][0] > state["off"][0] * 1.5,
           off=state["off"], on=state["on"])
    state["dialog"].glow_amount.setValue(200)


def measure_strong():
    state["strong"] = mass()
    record("amount spin sets glow_amount", abs(cg.get_settings().glow_amount - 2.0) < 1e-6,
           value=cg.get_settings().glow_amount)
    record("200% paints a wider, stronger halo than 100%",
           state["strong"][0] > state["on"][0] * 1.15, on=state["on"], strong=state["strong"])
    state["dialog"].glow_amount.setValue(0)


def measure_zero():
    state["zero"] = mass()
    record("0% glow leaves only the core (less than 100%)",
           state["zero"][0] < state["on"][0] * 0.8 and state["zero"][1] <= state["on"][1],
           zero=state["zero"], on=state["on"])
    state["dialog"].glow_amount.setValue(100)
    state["dialog"].glow.setChecked(False)


def apply_scheme():
    dialog = state["dialog"]
    dialog.scheme.setCurrentIndex(dialog.scheme.findText(SCHEME))
    dialog.apply_scheme()
    settings = cg.get_settings()
    colors = {k: style_for(settings, k)[0] for k in GUIDE_KEYS}
    record("scheme sets a color for every guide",
           len(settings.guide_styles) == len(GUIDE_KEYS) and
           colors["golden_spiral"] == schemes.SCHEMES[SCHEME]["golden"] and
           colors["thirds"] == schemes.SCHEMES[SCHEME]["structure"] and
           colors["golden_spiral"] != colors["thirds"],
           spiral=colors["golden_spiral"], thirds=colors["thirds"])
    record("glow stayed off while applying a scheme", not settings.glow)
    dialog.sync()
    record("Color scheme list shows the applied scheme", dialog.scheme.currentText() == SCHEME,
           shown=dialog.scheme.currentText())


def measure_scheme():
    golden = schemes.SCHEMES[SCHEME]["golden"]
    structure = schemes.SCHEMES[SCHEME]["structure"]
    a, b = count_color(golden), count_color(structure)
    record("painted lines use the scheme's different hues", a > 100 and b > 100,
           golden=a, structure=b)


def single_color():
    dialog = state["dialog"]
    dialog.scheme.setCurrentIndex(0)
    dialog.apply_scheme()
    record("Single color removes per-guide styles", cg.get_settings().guide_styles == ())
    dialog.sync()
    record("Color scheme list shows Single color again",
           dialog.scheme.currentText() == schemes.DEFAULT_SCHEME, shown=dialog.scheme.currentText())
    cg.set_settings(schemes.apply_scheme(cg.get_settings(), SCHEME))
    from composition_guides.settings import with_guide_style
    cg.set_settings(with_guide_style(cg.get_settings(), "thirds", ((1, 2, 3), 0.5, 1.0, "solid")))
    dialog.sync()
    record("Color scheme list shows Custom after a hand edit",
           dialog.scheme.currentText() == schemes.CUSTOM_SCHEME, shown=dialog.scheme.currentText())
    dialog.apply_scheme()
    record("Apply on Custom leaves per-guide styles alone",
           style_for(cg.get_settings(), "thirds")[0] == (1, 2, 3))
    cg.set_settings(schemes.apply_scheme(cg.get_settings(), schemes.DEFAULT_SCHEME))
    dialog.glow.setChecked(True)
    dialog.glow_amount.setValue(140)


def reload_keeps():
    cg.reload_plugin()
    settings = cg.get_settings()
    record("hot reload keeps glow settings", settings.glow and abs(settings.glow_amount - 1.4) < 1e-6)
    record("scene unchanged",
           tuple(node.path() for node in hou.node("/").allSubChildren()) == before)


steps = [start, measure_off, measure_on, measure_strong, measure_zero, apply_scheme,
         measure_scheme, single_color, reload_keeps]


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
