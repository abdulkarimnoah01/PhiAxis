"""Modeless controls; edits apply live, saved defaults are explicitly requested."""
from dataclasses import replace
import hou
from hutil.PySide import QtCore, QtGui, QtWidgets
from . import get_settings, set_settings, enable, disable, _current, settings_path, __version__
from . import presets
from .settings import (Settings, GUIDE_KEYS, LINE_STYLES, style_for, with_guide_style,
                       load_presets, save_preset, delete_preset)


GUIDE_LABELS = {
    "thirds": "Rule of thirds", "golden": "Phi grid", "crosshair": "Center crosshair",
    "center_cross": "Center lines", "diagonals": "Frame diagonals",
    "single_diagonal": "Single diagonal", "safe_area": "Safe area",
    "golden_spiral": "Golden spiral", "golden_rectangles": "Golden rectangles",
    "golden_triangle": "Golden triangle", "diagonal_phi": "Diagonal phi",
    "dynamic_symmetry": "Dynamic symmetry", "radiating": "Radiating grid",
    "tunnel": "Tunnel", "vanishing_point": "Vanishing point",
    "leading_lines": "Leading lines", "pyramid": "Pyramid", "v_shape": "V shape",
    "l_shape": "L shape", "s_curve": "S curve", "c_curve": "C curve",
    "circle": "Circle", "balance": "Balance", "asymmetric_balance": "Asymmetric balance",
}
GUIDE_GROUPS = (
    ("Grids and lines", ("thirds", "golden", "crosshair", "center_cross", "diagonals",
                         "single_diagonal", "safe_area")),
    ("Golden ratio and armatures", ("golden_spiral", "golden_rectangles",
                                    "golden_triangle", "diagonal_phi",
                                    "dynamic_symmetry")),
    ("Perspective", ("radiating", "tunnel", "vanishing_point", "leading_lines")),
    ("Shapes and balance", ("pyramid", "v_shape", "l_shape", "s_curve", "c_curve",
                            "circle", "balance", "asymmetric_balance")),
)
LINE_STYLE_LABELS = {"solid": "Solid", "dash": "Dashed", "dot": "Dotted"}
DYNAMIC_LABELS = (("Basic (frame)", "basic"), ("Root 2", "root2"), ("Root 3", "root3"),
                  ("Root 4", "root4"), ("Root 5", "root5"), ("Root φ", "rootphi"))
# (attribute, label, minimum %, maximum %, step %) for fraction parameters.
PERCENT_FIELDS = (
    ("focal_x", "Focal point X", 0, 100, 1), ("focal_y", "Focal point Y", 0, 100, 1),
    ("tunnel_scale", "Tunnel inner size", 5, 100, 5),
    ("circle_scale", "Circle size", 5, 100, 5),
    ("pyramid_apex_x", "Pyramid apex X", 0, 100, 1),
    ("pyramid_apex_inset", "Pyramid apex inset", 0, 100, 1),
    ("leading_width", "Leading-lines width", 5, 100, 5),
    ("v_apex_x", "V apex X", 0, 100, 1), ("v_apex_y", "V apex depth", 0, 100, 1),
    ("v_width", "V opening width", 5, 100, 5), ("l_inset", "L corner inset", 0, 45, 1),
    ("curvature", "S / C curvature", 5, 50, 1),
    ("balance_spacing", "Balance spacing", 5, 95, 1),
    ("balance_scale", "Balance size", 5, 100, 5),
    ("balance_y", "Balance height", 5, 95, 1),
    ("asym_a_x", "Large region X", 0, 100, 1), ("asym_a_y", "Large region Y", 0, 100, 1),
    ("asym_a_scale", "Large region size", 5, 100, 5),
    ("asym_b_x", "Small region X", 0, 100, 1), ("asym_b_y", "Small region Y", 0, 100, 1),
    ("asym_b_scale", "Small region size", 5, 100, 5),
    ("safe_x", "Left / right margin", 0, 49, 1), ("safe_y", "Top / bottom margin", 0, 49, 1),
)


def run_update_check():
    """The panel's "Check for updates" button. The package is looked up when clicked, not
    imported at the top: after an update installed while Houdini stayed open, this session can
    hold an older package without the newer names, and a plain message beats a traceback."""
    try:
        import composition_guides as cg
        cg.check_for_updates()
    except (AttributeError, ImportError):
        hou.ui.displayMessage(
            "PhiAxis was updated while Houdini was running, so this session holds a mix of "
            "old and new files.\n\nRestart Houdini to finish the update.",
            title="PhiAxis updates", severity=hou.severityType.Warning)


class SettingsDialog(QtWidgets.QDialog):
    def __init__(self):
        super().__init__(hou.qt.mainWindow())
        self.setWindowTitle("PhiAxis")
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.Tool)
        self.setMinimumWidth(500)
        self._syncing = False
        layout = QtWidgets.QVBoxLayout(self)

        top = QtWidgets.QHBoxLayout()
        self.enabled = QtWidgets.QCheckBox("Show guides")
        self.enabled.toggled.connect(self.toggle_enabled)
        top.addWidget(self.enabled)
        top.addStretch()
        top.addWidget(QtWidgets.QLabel("Coverage"))
        self.scope = self.combo(("Active viewport", "active"),
                                ("All visible viewports", "all"))
        top.addWidget(self.scope)
        layout.addLayout(top)

        preset_row = QtWidgets.QHBoxLayout()
        preset_row.addWidget(QtWidgets.QLabel("Preset"))
        self.preset = QtWidgets.QComboBox()
        self.preset.setMinimumWidth(170)
        preset_row.addWidget(self.preset, 1)
        for text, slot in (("Apply", self.apply_preset), ("Save as…", self.save_preset),
                           ("Delete", self.delete_preset)):
            button = QtWidgets.QPushButton(text)
            button.clicked.connect(slot)
            preset_row.addWidget(button)
        layout.addLayout(preset_row)

        self.tabs = QtWidgets.QTabWidget()
        self.tabs.addTab(self._guides_tab(), "Guides")
        self.tabs.addTab(self._adjust_tab(), "Adjust")
        self.tabs.addTab(self._style_tab(), "Style")
        layout.addWidget(self.tabs)

        buttons = QtWidgets.QHBoxLayout()
        for text, slot in (("Reset", self.reset), ("Save defaults", self.save_defaults),
                           ("Close", self.close)):
            button = QtWidgets.QPushButton(text)
            button.clicked.connect(slot)
            buttons.addWidget(button)
        layout.addLayout(buttons)
        self.message = QtWidgets.QLabel("Changes apply immediately.")
        self.message.setWordWrap(True)
        layout.addWidget(self.message)
        footer = QtWidgets.QHBoxLayout()
        footer.addWidget(QtWidgets.QLabel("PhiAxis " + __version__))
        footer.addStretch()
        updates = QtWidgets.QPushButton("Check for updates…")
        updates.clicked.connect(run_update_check)
        footer.addWidget(updates)
        layout.addLayout(footer)
        self.sync()

    # ----- construction -------------------------------------------------
    def _guides_tab(self):
        page = QtWidgets.QWidget()
        column = QtWidgets.QVBoxLayout(page)
        self.checks = {}
        for title, keys in GUIDE_GROUPS:
            group = QtWidgets.QGroupBox(title)
            grid = QtWidgets.QGridLayout(group)
            for index, key in enumerate(keys):
                check = QtWidgets.QCheckBox(GUIDE_LABELS[key])
                check.toggled.connect(self.apply)
                self.checks[key] = check
                grid.addWidget(check, index // 3, index % 3)
            column.addWidget(group)
        fit = QtWidgets.QCheckBox("Fit to camera frame")
        fit.toggled.connect(self.apply)
        self.checks["fit_camera"] = fit
        column.addWidget(fit)
        column.addStretch()
        return page

    def _adjust_tab(self):
        page = QtWidgets.QWidget()
        form = QtWidgets.QFormLayout(page)
        self.thirds_mode = self.combo(("Full grid", "full"), ("Horizontal only", "horizontal"),
                                      ("Vertical only", "vertical"))
        form.addRow("Thirds orientation", self.thirds_mode)
        self.center_mode = self.combo(("Horizontal and vertical", "both"),
                                      ("Horizontal only", "horizontal"),
                                      ("Vertical only", "vertical"))
        form.addRow("Center-line orientation", self.center_mode)
        self.dynamic_mode = self.combo(*DYNAMIC_LABELS)
        form.addRow("Dynamic symmetry", self.dynamic_mode)
        self.vanishing_mode = self.combo(("All four corners", "all"),
                                         ("Lower corners", "lower"))
        form.addRow("Vanishing-point rays", self.vanishing_mode)
        self.pyramid_inverted = self.check("Point downward")
        form.addRow("Pyramid", self.pyramid_inverted)
        self.v_inverted = self.check("Open downward")
        form.addRow("V shape", self.v_inverted)
        self.orientation = self.combo(("0°", 0), ("90°", 1), ("180°", 2), ("270°", 3))
        form.addRow("Rotate golden ratio / diagonal guides", self.orientation)
        self.mirror = self.check("Flip left ↔ right")
        form.addRow("Golden ratio direction", self.mirror)
        self.flip_vertical = self.check("Flip up ↕ down")
        form.addRow("", self.flip_vertical)
        self.radial_count = QtWidgets.QSpinBox()
        self.radial_count.setRange(4, 64)
        self.radial_count.setSingleStep(2)
        self.radial_count.valueChanged.connect(self.apply)
        form.addRow("Radiating spokes", self.radial_count)
        for name, label, low, high, step in PERCENT_FIELDS:
            spin = self.spin(low, high, step, "%")
            setattr(self, name, spin)
            form.addRow(label, spin)
        note = QtWidgets.QLabel("Rotation and the two flips apply to the golden spiral, "
                                "rectangles and triangle, diagonal phi, single "
                                "diagonal, L shape and S / C curves.")
        note.setWordWrap(True)
        form.addRow(note)
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(page)
        scroll.setMinimumHeight(360)
        return scroll

    def _style_tab(self):
        page = QtWidgets.QWidget()
        column = QtWidgets.QVBoxLayout(page)
        shared = QtWidgets.QGroupBox("All guides")
        form = QtWidgets.QFormLayout(shared)
        self.opacity = self.spin(0, 100, 5, "%")
        self.thickness = self.spin(0.25, 20, 0.25, " px")
        self.line_style = self.combo(*((LINE_STYLE_LABELS[s], s) for s in LINE_STYLES))
        self.color = QtWidgets.QPushButton("Choose color…")
        self.color.clicked.connect(self.choose_color)
        form.addRow("Color", self.color)
        form.addRow("Opacity", self.opacity)
        form.addRow("Line thickness", self.thickness)
        form.addRow("Line style", self.line_style)
        column.addWidget(shared)

        custom = QtWidgets.QGroupBox("One guide")
        form = QtWidgets.QFormLayout(custom)
        self.style_guide = QtWidgets.QComboBox()
        for key in GUIDE_KEYS:
            self.style_guide.addItem(GUIDE_LABELS[key], key)
        self.style_guide.currentIndexChanged.connect(self.sync)
        form.addRow("Guide", self.style_guide)
        self.style_custom = QtWidgets.QCheckBox("Use its own style")
        self.style_custom.toggled.connect(self.apply_guide_style)
        form.addRow(self.style_custom)
        self.style_color = QtWidgets.QPushButton("Choose color…")
        self.style_color.clicked.connect(self.choose_guide_color)
        self.style_opacity = self.spin(0, 100, 5, "%", self.apply_guide_style)
        self.style_thickness = self.spin(0.25, 20, 0.25, " px", self.apply_guide_style)
        self.style_line = self.combo(*((LINE_STYLE_LABELS[s], s) for s in LINE_STYLES),
                                     slot=self.apply_guide_style)
        form.addRow("Color", self.style_color)
        form.addRow("Opacity", self.style_opacity)
        form.addRow("Line thickness", self.style_thickness)
        form.addRow("Line style", self.style_line)
        column.addWidget(custom)
        column.addStretch()
        return page

    def spin(self, minimum, maximum, step, suffix, slot=None):
        spin = QtWidgets.QDoubleSpinBox()
        spin.setRange(minimum, maximum)
        spin.setSingleStep(step)
        spin.setDecimals(2)
        spin.setSuffix(suffix)
        spin.valueChanged.connect(slot or self.apply)
        return spin

    def combo(self, *items, slot=None):
        combo = QtWidgets.QComboBox()
        for label, value in items:
            combo.addItem(label, value)
        combo.currentIndexChanged.connect(slot or self.apply)
        return combo

    def check(self, label):
        check = QtWidgets.QCheckBox(label)
        check.toggled.connect(self.apply)
        return check

    # ----- model <-> widgets --------------------------------------------
    def sync(self, *args):
        self._syncing = True
        try:
            settings = get_settings()
            self.enabled.setChecked(_current() is not None)
            for key, check in self.checks.items():
                check.setChecked(getattr(settings, key))
            for name in ("scope", "thirds_mode", "center_mode", "dynamic_mode",
                         "vanishing_mode", "orientation", "line_style"):
                widget = getattr(self, name)
                widget.setCurrentIndex(widget.findData(getattr(settings, name)))
            for name in ("pyramid_inverted", "v_inverted", "mirror", "flip_vertical"):
                getattr(self, name).setChecked(getattr(settings, name))
            self.radial_count.setValue(settings.radial_count)
            for name, *_ in PERCENT_FIELDS:
                getattr(self, name).setValue(getattr(settings, name) * 100)
            self.opacity.setValue(settings.opacity * 100)
            self.thickness.setValue(settings.thickness)
            self.color.setStyleSheet("background-color: rgb(%d,%d,%d);" % settings.color)
            key = self.style_guide.currentData()
            custom = any(entry[0] == key for entry in settings.guide_styles)
            color, opacity, thickness, line_style = style_for(settings, key)
            self._guide_color = color
            self.style_custom.setChecked(custom)
            for widget in (self.style_color, self.style_opacity, self.style_thickness,
                           self.style_line):
                widget.setEnabled(custom)
            self.style_color.setStyleSheet("background-color: rgb(%d,%d,%d);" % color)
            self.style_opacity.setValue(opacity * 100)
            self.style_thickness.setValue(thickness)
            self.style_line.setCurrentIndex(self.style_line.findData(line_style))
            self._fill_presets()
        finally:
            self._syncing = False

    def apply(self, *args):
        if self._syncing:
            return
        values = {key: check.isChecked() for key, check in self.checks.items()}
        for name in ("scope", "thirds_mode", "center_mode", "dynamic_mode",
                     "vanishing_mode", "orientation", "line_style"):
            values[name] = getattr(self, name).currentData()
        for name in ("pyramid_inverted", "v_inverted", "mirror", "flip_vertical"):
            values[name] = getattr(self, name).isChecked()
        for name, *_ in PERCENT_FIELDS:
            values[name] = getattr(self, name).value() / 100
        values.update(radial_count=self.radial_count.value(),
                      opacity=self.opacity.value() / 100,
                      thickness=self.thickness.value())
        set_settings(replace(get_settings(), **values))
        self.message.setText("Changes apply immediately. Save defaults to keep them "
                             "next session.")

    def apply_guide_style(self, *args):
        if self._syncing:
            return
        key = self.style_guide.currentData()
        style = None
        if self.style_custom.isChecked():
            style = (self._guide_color, self.style_opacity.value() / 100,
                     self.style_thickness.value(), self.style_line.currentData())
        set_settings(with_guide_style(get_settings(), key, style))
        self.sync()

    # ----- actions ------------------------------------------------------
    def toggle_enabled(self, checked):
        if self._syncing:
            return
        try:
            enable() if checked else disable()
        except Exception as exc:
            self.message.setText(str(exc))
        self.sync()

    def choose_color(self):
        color = QtWidgets.QColorDialog.getColor(QtGui.QColor(*get_settings().color), self)
        if color.isValid():
            set_settings(replace(get_settings(), color=(color.red(), color.green(), color.blue())))
            self.sync()

    def choose_guide_color(self):
        color = QtWidgets.QColorDialog.getColor(QtGui.QColor(*self._guide_color), self)
        if color.isValid():
            self._guide_color = (color.red(), color.green(), color.blue())
            self.apply_guide_style()

    def _fill_presets(self):
        current = self.preset.currentText()
        self.preset.blockSignals(True)
        self.preset.clear()
        for name in presets.BUILTIN:
            self.preset.addItem(name, ("builtin", name))
        try:
            mine = load_presets(settings_path())
        except (OSError, ValueError) as exc:
            mine = {}
            self.message.setText("Cannot read saved presets: " + str(exc))
        if mine:
            self.preset.insertSeparator(self.preset.count())
            for name in sorted(mine):
                self.preset.addItem(name, ("user", name))
        index = self.preset.findText(current)
        self.preset.setCurrentIndex(max(index, 0))
        self.preset.blockSignals(False)

    def apply_preset(self):
        kind, name = self.preset.currentData() or (None, None)
        try:
            if kind == "builtin":
                set_settings(presets.apply_builtin(get_settings(), name))
            elif kind == "user":
                values = load_presets(settings_path())[name]
                set_settings(presets.apply(get_settings(), values))
            else:
                return
            self.message.setText("Applied preset “%s”. Style was kept." % name)
        except (OSError, ValueError, TypeError, KeyError) as exc:
            self.message.setText("Could not apply preset: " + str(exc))
        self.sync()

    def save_preset(self):
        name, ok = QtWidgets.QInputDialog.getText(
            self, "Save preset", "Preset name (saves the guides shown and their settings):")
        if not ok or not name.strip():
            return
        if name.strip() in presets.BUILTIN:
            self.message.setText("“%s” is a built-in preset; choose another name." % name)
            return
        try:
            save_preset(settings_path(), name, get_settings())
            self.message.setText("Saved preset “%s”." % name.strip())
        except (OSError, ValueError) as exc:
            self.message.setText("Could not save preset: " + str(exc))
        self.sync()
        self.preset.setCurrentIndex(self.preset.findText(name.strip()))

    def delete_preset(self):
        kind, name = self.preset.currentData() or (None, None)
        if kind != "user":
            self.message.setText("Only presets you saved can be deleted.")
            return
        try:
            delete_preset(settings_path(), name)
            self.message.setText("Deleted preset “%s”." % name)
        except (OSError, ValueError) as exc:
            self.message.setText("Could not delete preset: " + str(exc))
        self.sync()

    def reset(self):
        set_settings(Settings())
        self.sync()

    def save_defaults(self):
        try:
            set_settings(get_settings(), persist=True)
            self.message.setText("Defaults saved for this Houdini preferences directory.")
        except OSError as exc:
            self.message.setText("Could not save defaults: " + str(exc))

    def closeEvent(self, event):
        # Closing controls leaves guides enabled; no timers or callbacks on this dialog.
        import composition_guides as cg
        if getattr(hou.session, cg._UI_KEY, None) is self:
            delattr(hou.session, cg._UI_KEY)
        self.deleteLater()
        event.accept()
