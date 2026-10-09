# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Ronaldo Alves and CutList contributors.
"""The cut list's dialogs: materials, part settings, settings.

Each one edits plain model objects (:class:`MaterialSpec`,
:class:`PartOverride`, :class:`Settings`) and hands them back; the host
decides where they are stored. Lengths are typed in millimetres.
"""
from __future__ import annotations

from dataclasses import replace

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..i18n import tr
from ..model.fields import FieldDef, Fields, format_rules, parse_rules
from ..model.materials import BoardKind, Library, MaterialSpec, Role
from ..model.parts import PartOverride
from ..model.settings import UNITS, Settings
from ..model.text import (
    MM,
    fmt_length,
    fmt_lengths,
    fmt_sheets,
    parse_length,
    parse_lengths,
    parse_sheets,
)


def role_label(role: Role) -> str:
    return {
        Role.BOARD: tr("Board (cut on the panel saw)"),
        Role.COVERING: tr("Covering (laminate, veneer…)"),
        Role.EDGE_BAND: tr("Edge band"),
        Role.APPEARANCE: tr("Appearance only (nothing to order)"),
        Role.IGNORE: tr("Ignore (not cut: glass, hardware…)"),
    }[role]


def unit_label(unit: str | None) -> str:
    if unit is None:
        return tr("The model's units")
    return {"mm": tr("Millimetres"), "cm": tr("Centimetres"),
            "m": tr("Metres"), "in": tr("Inches (decimal)"),
            "in-frac": tr("Inches (fractions)"),
            "ft-in": tr("Feet and inches (decimal)"),
            "ft-in-frac": tr("Feet and inches (fractions)")}[unit]


def _buttons(dialog: QDialog) -> QDialogButtonBox:
    box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok
                           | QDialogButtonBox.StandardButton.Cancel)
    box.accepted.connect(dialog.accept)
    box.rejected.connect(dialog.reject)
    return box


# ---------------------------------------------------------------------------
# Materials
# ---------------------------------------------------------------------------

class MaterialsDialog(QDialog):
    """One material at a time: pick it on the left, say what it is on the
    right. ``names`` are the materials found on the model's parts; the
    library supplies what is already known about them."""

    def __init__(self, names, library: Library, focus: str | None = None,
                 parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("cutlist_materials_dialog")
        self.setWindowTitle(tr("Cut List — Materials"))
        self.resize(720, 480)
        self._library = library
        self._specs: dict[str, MaterialSpec] = {}
        self._edited: set[str] = set()
        self._current: str | None = None
        self._loading = False

        names = sorted(set(names) | ({focus} if focus else set()),
                       key=str.lower)
        for name in names:
            self._specs[name] = library.get(name) or MaterialSpec(name)

        outer = QVBoxLayout(self)
        body = QHBoxLayout()
        outer.addLayout(body, 1)

        self.list = QListWidget()
        self.list.setObjectName("cutlist_material_list")
        for name in names:
            item = QListWidgetItem(name)
            if library.get(name) is None:
                item.setText(tr("{name} — not set up", name=name))
                item.setForeground(Qt.GlobalColor.darkYellow)
            item.setData(Qt.ItemDataRole.UserRole, name)
            self.list.addItem(item)
        self.list.currentItemChanged.connect(self._on_pick)
        body.addWidget(self.list, 2)

        right = QWidget()
        form = QFormLayout(right)
        self.form = form
        self.role = QComboBox()
        self.role.setObjectName("cutlist_role")
        for role in Role:
            self.role.addItem(role_label(role), role)
        self.kind = QComboBox()
        self.kind.addItem(tr("Sheet goods (plywood, MDF…)"), BoardKind.SHEET)
        self.kind.addItem(tr("Solid wood (listed only, for now)"),
                          BoardKind.SOLID)
        self.grain = QCheckBox(tr("Has a grain direction"))
        self.thicknesses = QLineEdit()
        self.thicknesses.setPlaceholderText(tr("e.g. 15; 18"))
        self.stocks = QLineEdit()
        self.stocks.setPlaceholderText(tr("e.g. 2750 x 1840; 2440 x 1220"))
        self.kerf = QLineEdit()
        self.trim = QLineEdit()
        self.thickness = QLineEdit()
        self.oversize = QLineEdit()
        self.applied_over = QComboBox()
        self.applied_over.setEditable(True)
        self.deduct = QCheckBox(tr("Cut the board shorter by the band "
                                   "thickness"))
        self.note = QLineEdit()
        self._rows = {
            "role": (tr("What it is"), self.role),
            "kind": (tr("Kind"), self.kind),
            "grain": ("", self.grain),
            "thicknesses": (tr("Thicknesses (mm)"), self.thicknesses),
            "stocks": (tr("Stock sheets (mm)"), self.stocks),
            "kerf": (tr("Saw kerf (mm)"), self.kerf),
            "trim": (tr("Trim per sheet edge (mm)"), self.trim),
            "thickness": (tr("Its thickness (mm)"), self.thickness),
            "oversize": (tr("Oversize (mm)"), self.oversize),
            "applied_over": (tr("Goes on board"), self.applied_over),
            "deduct": ("", self.deduct),
            "note": (tr("Note"), self.note),
        }
        for label, widget in self._rows.values():
            form.addRow(label, widget)
        self.hint = QLabel()
        self.hint.setWordWrap(True)
        self.hint.setStyleSheet("color: gray;")
        form.addRow(self.hint)
        body.addWidget(right, 3)

        for w in (self.thicknesses, self.stocks, self.kerf, self.trim,
                  self.thickness, self.oversize, self.note):
            w.textEdited.connect(self._changed)
        for w in (self.grain, self.deduct):
            w.toggled.connect(self._changed)
        for w in (self.role, self.kind):
            w.currentIndexChanged.connect(self._changed)
        self.applied_over.currentTextChanged.connect(self._changed)

        self.remember = QCheckBox(tr("Also use these materials in my other "
                                     "models"))
        self.remember.setObjectName("cutlist_remember")
        self.remember.setChecked(True)
        outer.addWidget(self.remember)
        outer.addWidget(_buttons(self))

        if names:
            start = names.index(focus) if focus in names else 0
            self.list.setCurrentRow(start)

    def _on_pick(self, item, _previous=None) -> None:
        if item is None:
            return
        self._current = item.data(Qt.ItemDataRole.UserRole)
        spec = self._specs[self._current]
        self._loading = True
        try:
            self.role.setCurrentIndex(self.role.findData(spec.role))
            self.kind.setCurrentIndex(self.kind.findData(spec.kind))
            self.grain.setChecked(spec.grain)
            self.thicknesses.setText(fmt_lengths(spec.thicknesses))
            self.stocks.setText(fmt_sheets(spec.stocks))
            self.kerf.setText(fmt_length(spec.kerf))
            self.kerf.setPlaceholderText(tr("default"))
            self.trim.setText(fmt_length(spec.trim))
            self.trim.setPlaceholderText(tr("default"))
            self.thickness.setText(fmt_length(spec.thickness or None))
            self.oversize.setText(fmt_length(spec.oversize or None))
            boards = sorted(n for n, s in self._specs.items()
                            if s.role is Role.BOARD and n != self._current)
            self.applied_over.clear()
            self.applied_over.addItem("")
            self.applied_over.addItems(boards)
            self.applied_over.setCurrentText(spec.applied_over or "")
            self.deduct.setChecked(spec.deduct)
            self.note.setText(spec.note)
        finally:
            self._loading = False
        self._show_rows(spec.role)

    def _show_rows(self, role: Role) -> None:
        visible = {
            Role.BOARD: {"kind", "grain", "thicknesses", "stocks", "kerf",
                         "trim"},
            Role.COVERING: {"grain", "thickness", "oversize", "stocks",
                            "applied_over"},
            Role.EDGE_BAND: {"thickness", "oversize", "deduct"},
            Role.APPEARANCE: set(),
            Role.IGNORE: set(),
        }[role] | {"role", "note"}
        for key, (_label, widget) in self._rows.items():
            self.form.setRowVisible(widget, key in visible)
        self.hint.setText({
            Role.BOARD: tr("Parts whose faces show this material are cut "
                           "from it. Kerf and trim left empty use the "
                           "defaults in Settings."),
            Role.COVERING: tr("Laminate or veneer glued on a face. Oversize "
                              "is added on each side; it gets its own "
                              "cutting diagrams later."),
            Role.EDGE_BAND: tr("Banding on an edge. Oversize is added to "
                               "each band's length."),
            Role.APPEARANCE: tr("A texture that only shows something, like "
                                "a plywood edge. Ignored by the cut list."),
            Role.IGNORE: tr("Parts made of it stay out of the cut list "
                            "(listed under Excluded)."),
        }[role])

    def _changed(self, *_args) -> None:
        if self._loading or self._current is None:
            return
        spec = MaterialSpec(
            name=self._current,
            role=self.role.currentData(),
            kind=self.kind.currentData(),
            grain=self.grain.isChecked(),
            thicknesses=parse_lengths(self.thicknesses.text()),
            stocks=parse_sheets(self.stocks.text()),
            kerf=parse_length(self.kerf.text()),
            trim=parse_length(self.trim.text()),
            thickness=parse_length(self.thickness.text()) or 0.0,
            oversize=parse_length(self.oversize.text()) or 0.0,
            deduct=self.deduct.isChecked(),
            applied_over=self.applied_over.currentText().strip() or None,
            note=self.note.text().strip())
        if spec.role != self._specs[self._current].role:
            self._show_rows(spec.role)
        self._specs[self._current] = spec
        self._edited.add(self._current)
        item = self.list.currentItem()
        if item is not None:
            item.setText(self._current)
            item.setForeground(self.list.palette().text())

    def result_specs(self) -> list[MaterialSpec]:
        """The materials the user touched (only those are stored)."""
        return [self._specs[n] for n in sorted(self._edited)]


# ---------------------------------------------------------------------------
# One part (or several)
# ---------------------------------------------------------------------------

class PartDialog(QDialog):
    """Settings of the selected parts; they all get the same values."""

    def __init__(self, override: PartOverride, count: int,
                 title: str = "", fields: dict | None = None,
                 parent=None) -> None:
        """``fields``: custom field name → the value the part gets without
        its own (shown greyed in the empty box)."""
        super().__init__(parent)
        self.setObjectName("cutlist_part_dialog")
        self.setWindowTitle(tr("Cut List — Part settings"))
        layout = QVBoxLayout(self)
        intro = QLabel(title if count == 1 else
                       tr("{n} parts: the values below go on all of them.",
                          n=count))
        intro.setWordWrap(True)
        layout.addWidget(intro)
        form = QFormLayout()
        layout.addLayout(form)

        self.exclude = QCheckBox(tr("Leave out of the cut list"))
        self.exclude.setChecked(override.exclude)
        form.addRow("", self.exclude)
        self.grain = QComboBox()
        for label, value in ((tr("As its material"), None),
                             (tr("Along the length"), "length"),
                             (tr("Along the width"), "width"),
                             (tr("No grain"), "none")):
            self.grain.addItem(label, value)
        self.grain.setCurrentIndex(self.grain.findData(override.grain))
        form.addRow(tr("Grain"), self.grain)
        self.rotate = QComboBox()
        for label, value in ((tr("As its material"), None),
                             (tr("Yes"), True), (tr("No"), False)):
            self.rotate.addItem(label, value)
        self.rotate.setCurrentIndex(self.rotate.findData(override.can_rotate))
        form.addRow(tr("May rotate on the sheet"), self.rotate)
        self.flip = QCheckBox(tr("Flip face 1 (the other face is the "
                                 "decorative one)"))
        self.flip.setChecked(override.flip_face1)
        form.addRow("", self.flip)
        self.note = QLineEdit(override.note)
        form.addRow(tr("Note"), self.note)
        self.field_edits: dict[str, QLineEdit] = {}
        own = override.field_values
        for name, inherited in (fields or {}).items():
            edit = QLineEdit(own.get(name, "") if count == 1 else "")
            edit.setPlaceholderText(inherited or "")
            edit.setToolTip(tr("Empty: the value from Settings (model or "
                               "tag rule)."))
            self.field_edits[name] = edit
            form.addRow(name, edit)
        self.clear_fields = QCheckBox(tr("Clear these parts' own field "
                                         "values"))
        self.clear_fields.setVisible(bool(fields))
        form.addRow("", self.clear_fields)
        layout.addWidget(_buttons(self))

    def field_values(self) -> dict[str, str]:
        """Typed field values (empty boxes are left out: they keep each
        part's own value)."""
        return {n: e.text().strip() for n, e in self.field_edits.items()
                if e.text().strip()}

    def result(self) -> PartOverride:          # noqa: D401 — Qt-style name
        return PartOverride(flip_face1=self.flip.isChecked(),
                            exclude=self.exclude.isChecked(),
                            note=self.note.text().strip(),
                            grain=self.grain.currentData(),
                            can_rotate=self.rotate.currentData())


# ---------------------------------------------------------------------------
# Settings (also the first-use scope window)
# ---------------------------------------------------------------------------

class SettingsDialog(QDialog):
    """What goes in the cut list and how it reads. With ``first_run`` it
    is the scope window shown before the first list, with "don't show
    again"."""

    def __init__(self, settings: Settings, tags=(), first_run: bool = False,
                 fields: Fields | None = None, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("cutlist_settings_dialog")
        self.setWindowTitle(tr("Cut List — What goes in the cut list")
                            if first_run else tr("Cut List — Settings"))
        self._settings = settings
        layout = QVBoxLayout(self)

        scope = QGroupBox(tr("What goes in the cut list"))
        sform = QVBoxLayout(scope)
        self.use_selection = QCheckBox(tr("Only the selection, when "
                                          "something is selected"))
        self.use_selection.setChecked(settings.use_selection)
        sform.addWidget(self.use_selection)
        self.include_groups = QCheckBox(tr("Also plain groups, not only "
                                           "components"))
        self.include_groups.setChecked(settings.include_groups)
        sform.addWidget(self.include_groups)
        self.tags = QListWidget()
        self.tags.setObjectName("cutlist_settings_tags")
        all_tags = sorted(set(tags) | set(settings.excluded_tags),
                          key=str.lower)
        if all_tags:
            sform.addWidget(QLabel(tr("Tags to include:")))
            for tag in all_tags:
                item = QListWidgetItem(tag)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Unchecked
                                   if tag in settings.excluded_tags
                                   else Qt.CheckState.Checked)
                self.tags.addItem(item)
            sform.addWidget(self.tags)
        layout.addWidget(scope)

        reading = QGroupBox(tr("How it reads"))
        rform = QFormLayout(reading)
        self.unit = QComboBox()
        self.unit.setObjectName("cutlist_unit")
        for unit in (None, *UNITS):
            self.unit.addItem(unit_label(unit), unit)
        self.unit.setCurrentIndex(self.unit.findData(settings.unit))
        rform.addRow(tr("Units"), self.unit)
        self.precision = QSpinBox()
        self.precision.setRange(-1, 4)
        self.precision.setSpecialValueText(tr("default"))
        self.precision.setValue(-1 if settings.precision is None
                                else settings.precision)
        rform.addRow(tr("Decimals"), self.precision)
        self.tolerance = QDoubleSpinBox()
        self.tolerance.setRange(0.0, 10.0)
        self.tolerance.setDecimals(2)
        self.tolerance.setSingleStep(0.5)
        self.tolerance.setSuffix(" mm")
        self.tolerance.setValue(settings.tolerance / MM)
        self.tolerance.setToolTip(tr(
            "Every size is rounded to this step before parts are compared "
            "and shown: at 1 mm, a 17.98 mm board reads 18 mm and merges "
            "with the other 18 mm ones."))
        rform.addRow(tr("Round sizes to"), self.tolerance)
        self.units_in_cells = QCheckBox(tr("Show the unit after every "
                                           "size"))
        self.units_in_cells.setToolTip(tr("Off: the unit is written once, "
                                          "in the column titles."))
        self.units_in_cells.setChecked(settings.units_in_cells)
        rform.addRow("", self.units_in_cells)
        self.merge = QCheckBox(tr("Merge parts of the same size whatever "
                                  "their names"))
        self.merge.setChecked(settings.merge_by_size)
        rform.addRow("", self.merge)
        layout.addWidget(reading)

        sheets = QGroupBox(tr("Sheets (defaults for boards)"))
        bform = QFormLayout(sheets)
        self.kerf = QDoubleSpinBox()
        self.kerf.setRange(0.0, 20.0)
        self.kerf.setDecimals(1)
        self.kerf.setSuffix(" mm")
        self.kerf.setValue(settings.kerf / MM)
        bform.addRow(tr("Saw kerf"), self.kerf)
        self.trim = QDoubleSpinBox()
        self.trim.setRange(0.0, 100.0)
        self.trim.setDecimals(1)
        self.trim.setSuffix(" mm")
        self.trim.setValue(settings.trim / MM)
        bform.addRow(tr("Trim per sheet edge"), self.trim)
        layout.addWidget(sheets)

        custom = QGroupBox(tr("Custom fields (client, room…)"))
        cbox = QVBoxLayout(custom)
        hint = QLabel(tr("Every part gets each field's value for this "
                         "model, unless a tag rule (e.g. QTO = Quarto) or "
                         "the part's own setting says otherwise. Exports "
                         "can use them as columns, to split files and in "
                         "file names."))
        hint.setWordWrap(True)
        hint.setStyleSheet("color: gray;")
        cbox.addWidget(hint)
        self.fields_table = QTableWidget(0, 3)
        self.fields_table.setObjectName("cutlist_fields")
        self.fields_table.setHorizontalHeaderLabels(
            [tr("Field"), tr("Value in this model"),
             tr("Tag rules (tag start = value; …)")])
        self.fields_table.horizontalHeader().setStretchLastSection(True)
        self.fields_table.verticalHeader().hide()
        for f in (fields or Fields()).defs:
            self._add_field_row(f.name, f.model_value, format_rules(f.rules))
        cbox.addWidget(self.fields_table)
        row = QHBoxLayout()
        add = QPushButton(tr("Add field"))
        add.clicked.connect(lambda: self._add_field_row("", "", ""))
        remove = QPushButton(tr("Remove field"))
        remove.clicked.connect(lambda: self.fields_table.removeRow(
            self.fields_table.currentRow()))
        row.addWidget(add)
        row.addWidget(remove)
        row.addStretch(1)
        cbox.addLayout(row)
        custom.setVisible(not first_run)
        layout.addWidget(custom)

        self.remember = QCheckBox(tr("Make these my defaults for every "
                                     "model"))
        self.remember.setObjectName("cutlist_remember")
        layout.addWidget(self.remember)
        self.dont_ask = QCheckBox(tr("Don't show this again (it stays in "
                                     "Settings)"))
        self.dont_ask.setVisible(first_run)
        self.dont_ask.setChecked(first_run)
        if first_run:
            self.remember.setChecked(True)
        layout.addWidget(self.dont_ask)
        layout.addWidget(_buttons(self))

    def _add_field_row(self, name, value, rules) -> None:
        r = self.fields_table.rowCount()
        self.fields_table.insertRow(r)
        for c, text in enumerate((name, value, rules)):
            self.fields_table.setItem(r, c, QTableWidgetItem(text))

    def result_fields(self) -> Fields:
        defs = []
        for r in range(self.fields_table.rowCount()):
            def text(c, r=r):
                item = self.fields_table.item(r, c)
                return item.text().strip() if item else ""
            if text(0):
                defs.append(FieldDef(text(0), text(1), parse_rules(text(2))))
        return Fields.from_list([d.to_dict() for d in defs])

    def result(self) -> Settings:              # noqa: D401 — Qt-style name
        excluded = tuple(
            self.tags.item(i).text() for i in range(self.tags.count())
            if self.tags.item(i).checkState() != Qt.CheckState.Checked)
        precision = self.precision.value()
        return replace(
            self._settings,
            unit=self.unit.currentData(),
            precision=None if precision < 0 else precision,
            tolerance=self.tolerance.value() * MM,
            merge_by_size=self.merge.isChecked(),
            units_in_cells=self.units_in_cells.isChecked(),
            use_selection=self.use_selection.isChecked(),
            include_groups=self.include_groups.isChecked(),
            excluded_tags=excluded,
            scope_asked=self._settings.scope_asked
            or self.dont_ask.isChecked(),
            kerf=self.kerf.value() * MM,
            trim=self.trim.value() * MM)
