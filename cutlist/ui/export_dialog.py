# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Ronaldo Alves and CutList contributors.
"""The export window (D-009): pick a profile, adjust it, see the result.

The window edits one :class:`~..export.profile.Profile` at a time and asks
the host, through an :class:`ExportSession`, for the rows it produces —
so the preview is always exactly what will be written. Profiles are saved
by name; a ``*`` marks changes not saved yet.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ..export.profile import (
    FIELDS,
    FLAG_FIELDS,
    TEXT_OPTIONS,
    Column,
    Numbers,
    Profile,
)
from ..export.rows import Export
from ..export.writers import clipboard_text, text_lines, unencodable
from ..i18n import tr

PREVIEW_ROWS = 40

#: Where a Yes/No cell keeps its word while the column does not use it.
_KEPT = Qt.ItemDataRole.UserRole + 10

#: Positions in the columns table.
ON, HEADER, KIND, VALUE, YES, NO, TEXT = range(7)


class _RowsTable(QTableWidget):
    """A table whose rows can be dragged to a new place. Qt's own row
    dragging cannot carry the combo boxes inside the cells, so the drop is
    reported (``row_moved(from, to)``) and the dialog rebuilds the rows in
    their new order — the same path as Move up / Move down."""

    row_moved = Signal(int, int)

    def __init__(self, rows: int, cols: int) -> None:
        super().__init__(rows, cols)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        self.setDragDropOverwriteMode(False)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)

    def dropEvent(self, event) -> None:                 # noqa: N802 — Qt
        source = self.currentRow()
        y = event.position().toPoint().y()
        target = self.rowAt(y)
        if target < 0:
            target = self.rowCount()
        elif y > self.visualRect(self.model().index(target, 0)).center().y():
            target += 1
        event.setDropAction(Qt.DropAction.IgnoreAction)
        event.accept()
        if source >= 0 and target not in (source, source + 1):
            self.row_moved.emit(source, target)


def field_label(name: str) -> str:
    # The same edge names as the panel (L1/L2 along the length, W1/W2
    # along the width — C1/C2/L1/L2 in Portuguese), grain first.
    edges = {"c1": tr("L1"), "c2": tr("L2"), "l1": tr("W1"), "l2": tr("W2")}
    for key, short in edges.items():
        if name == f"band_{key}":
            return tr("Band {edge} — name", edge=short)
        if name == f"band_{key}_code":
            return tr("Band {edge} — supplier code", edge=short)
        if name == f"band_{key}_flag":
            return tr("Band {edge} — yes/no", edge=short)
    return {
        "qty": tr("Quantity"), "length": tr("Length (along the grain)"),
        "width": tr("Width"), "thickness": tr("Thickness"),
        "name": tr("Part name"), "number": tr("Line number"),
        "material": tr("Material (your name)"),
        "material_code": tr("Material — supplier code"),
        "material_supplier": tr("Material — supplier name"),
        "grain": tr("Has grain — yes/no"),
        "rotate": tr("May rotate — yes/no"), "note": tr("Note"),
        "tag": tr("Tag"), "model": tr("Model name"),
        "face1": tr("Covering on face 1"), "face2": tr("Covering on face 2"),
    }.get(name, name)


def text_option_label(option: str) -> str:
    return {"ascii": tr("No accents"), "upper": tr("UPPERCASE"),
            "underscores": tr("Spaces → _")}[option]


def problem_text(kind: str, value: str, count: int) -> str:
    return {
        "material_code": tr("“{v}” has no supplier code (Codes tab)"),
        "material_supplier": tr("“{v}” has no supplier name (Codes tab)"),
        "band_code": tr("Band “{v}” has no supplier code (Codes tab)"),
        "no_material": tr("“{v}” has no material"),
        "encoding": tr("“{v}” cannot be written in this encoding "
                       "(File tab)"),
    }.get(kind, "{v}").format(v=value) + (f" ×{count}" if count > 1 else "")


@dataclass
class ExportSession:
    """What the window needs from the host."""

    #: Profile → rows (the model's current cut list).
    rows: Callable[[Profile], Export]
    #: name → Profile, and the one used last.
    profiles: dict
    last: str | None
    #: Save all profiles and the current name.
    save: Callable[[dict, str | None], None]
    #: Materials and bands found in the cut list (for the Codes tab).
    materials: list
    bands: list
    #: Custom field names (offered as columns, split and file names).
    fields: list
    #: Write ``{file name: bytes}`` into a folder, or set the clipboard.
    write: Callable[[str, dict], None]
    copy: Callable[[str], None]
    suggested_folder: str = ""


class ExportDialog(QDialog):
    def __init__(self, session: ExportSession, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("cutlist_export_dialog")
        self.setWindowTitle(tr("Cut List — Export"))
        self.resize(980, 720)
        self.session = session
        self.profiles = dict(session.profiles)
        name = session.last if session.last in self.profiles \
            else next(iter(self.profiles))
        self.saved = self.profiles[name]
        self.profile = self.saved
        self._loading = False

        outer = QVBoxLayout(self)
        bar = QHBoxLayout()
        bar.addWidget(QLabel(tr("Profile")))
        self.combo = QComboBox()
        self.combo.setObjectName("cutlist_profile")
        self.combo.setMinimumWidth(220)
        self.combo.activated.connect(self._pick_profile)
        bar.addWidget(self.combo)
        for text, slot, obj in (
                (tr("Save"), self.save_profile, "cutlist_profile_save"),
                (tr("Save as…"), self.save_profile_as, "cutlist_profile_save_as"),
                (tr("Rename…"), self.rename_profile, None),
                (tr("Delete"), self.delete_profile, None),
                (tr("Import…"), self.import_profile, None),
                (tr("Export profile…"), self.export_profile, None)):
            b = QPushButton(text)
            if obj:
                b.setObjectName(obj)
            b.clicked.connect(slot)
            bar.addWidget(b)
        bar.addStretch(1)
        outer.addLayout(bar)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._columns_tab(), tr("Columns"))
        self.tabs.addTab(self._file_tab(), tr("File"))
        self.tabs.addTab(self._numbers_tab(), tr("Numbers"))
        self.tabs.addTab(self._codes_tab(), tr("Codes"))
        outer.addWidget(self.tabs, 3)

        self.problems = QLabel()
        self.problems.setObjectName("cutlist_export_problems")
        self.problems.setWordWrap(True)
        self.problems.setStyleSheet("color: #b00020;")
        outer.addWidget(self.problems)
        outer.addWidget(QLabel(tr("Preview (exactly as it will be "
                                  "written):")))
        self.preview = QPlainTextEdit()
        self.preview.setObjectName("cutlist_export_preview")
        self.preview.setReadOnly(True)
        self.preview.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        mono = QFont("Monospace")
        mono.setStyleHint(QFont.StyleHint.TypeWriter)
        self.preview.setFont(mono)
        outer.addWidget(self.preview, 2)

        bottom = QHBoxLayout()
        self.summary = QLabel()
        bottom.addWidget(self.summary, 1)
        self.copy_button = QPushButton(tr("Copy to clipboard"))
        self.copy_button.setObjectName("cutlist_export_copy")
        self.copy_button.clicked.connect(self.copy)
        bottom.addWidget(self.copy_button)
        self.export_button = QPushButton(tr("Export…"))
        self.export_button.setObjectName("cutlist_export_write")
        self.export_button.setDefault(True)
        self.export_button.clicked.connect(self.export)
        bottom.addWidget(self.export_button)
        close = QPushButton(tr("Close"))
        close.clicked.connect(self.reject)
        bottom.addWidget(close)
        outer.addLayout(bottom)

        self._fill_combo()
        self._load(self.profile)

    # =====================================================================
    # Tabs
    # =====================================================================
    def _columns_tab(self) -> QWidget:
        w = QWidget()
        box = QVBoxLayout(w)
        self.columns = _RowsTable(0, 7)
        self.columns.setObjectName("cutlist_export_columns")
        self.columns.setHorizontalHeaderLabels([
            tr("On"), tr("Header"), tr("Shows"), tr("Field, text or template"),
            tr("Yes"), tr("No"), tr("Text")])
        self.columns.horizontalHeaderItem(ON).setToolTip(tr(
            "Ticked: the column is in the file. Unticked: kept in the "
            "profile, left out of the file."))
        self.columns.horizontalHeader().setStretchLastSection(False)
        self.columns.setColumnWidth(ON, 36)
        self.columns.setColumnWidth(HEADER, 160)
        self.columns.setColumnWidth(KIND, 110)
        self.columns.setColumnWidth(VALUE, 300)
        self.columns.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        self.columns.setToolTip(tr("Drag a row to move the column, or use "
                                   "Move up / Move down."))
        self.columns.itemChanged.connect(self._item_changed)
        self.columns.row_moved.connect(self._move_column_to)
        box.addWidget(self.columns)
        row = QHBoxLayout()
        for text, slot in ((tr("Add column"), self._add_column),
                           (tr("Remove"), self._remove_column),
                           (tr("Move up"), lambda: self._move_column(-1)),
                           (tr("Move down"), lambda: self._move_column(1))):
            b = QPushButton(text)
            b.clicked.connect(slot)
            row.addWidget(b)
        row.addStretch(1)
        hint = QLabel(tr("Templates fill in {placeholders}: {name}, "
                         "{material}, {thickness}, your custom fields…"))
        hint.setStyleSheet("color: gray;")
        row.addWidget(hint)
        box.addLayout(row)
        return w

    def _file_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        self.format = QComboBox()
        for label, value in ((tr("Text file (CSV, TXT)"), "text"),
                             (tr("Excel workbook (.xlsx)"), "xlsx"),
                             (tr("Clipboard only"), "clipboard")):
            self.format.addItem(label, value)
        form.addRow(tr("Format"), self.format)
        self.extension = QLineEdit()
        form.addRow(tr("File extension"), self.extension)
        self.separator = QComboBox()
        self.separator.setEditable(True)
        for label, value in ((tr("Semicolon ;"), ";"), (tr("Comma ,"), ","),
                             (tr("Tab"), "\t"), (tr("Bar |"), "|")):
            self.separator.addItem(label, value)
        form.addRow(tr("Separator"), self.separator)
        self.encoding = QComboBox()
        for label, value in zip((tr("UTF-8 with BOM (Excel)"), tr("UTF-8"),
                                 tr("Windows-1252 (older systems)")),
                                ("utf-8-sig", "utf-8", "cp1252"),
                                strict=True):
            self.encoding.addItem(label, value)
        form.addRow(tr("Encoding"), self.encoding)
        self.newline = QComboBox()
        self.newline.addItem(tr("Windows (CR LF)"), "crlf")
        self.newline.addItem(tr("Unix (LF)"), "lf")
        form.addRow(tr("Line endings"), self.newline)
        self.quoting = QComboBox()
        for label, value in ((tr("Only when needed"), "minimal"),
                             (tr("Always"), "all"), (tr("Never"), "none")):
            self.quoting.addItem(label, value)
        form.addRow(tr("Quotes around values"), self.quoting)
        self.trailing = QCheckBox(tr("Separator after the last field"))
        form.addRow("", self.trailing)
        self.header = QCheckBox(tr("First row is the column headers"))
        form.addRow("", self.header)
        self.rows = QComboBox()
        self.rows.addItem(tr("One row per line, with a quantity"), "merged")
        self.rows.addItem(tr("One row per piece"), "per_piece")
        form.addRow(tr("Rows"), self.rows)
        self.split = QComboBox()
        form.addRow(tr("Files"), self.split)
        self.filename = QLineEdit()
        self.filename.setToolTip(tr("Fill-in fields: {model}, {material}, "
                                    "{thickness}, {value} (when split by a "
                                    "field), your custom fields."))
        form.addRow(tr("File name"), self.filename)
        self.grain_first = QCheckBox(tr("Grain first: when the grain runs "
                                        "across the long side, swap length "
                                        "and width (and their bands)"))
        form.addRow("", self.grain_first)
        for widget in (self.format, self.encoding, self.newline,
                       self.quoting, self.rows, self.split):
            widget.currentIndexChanged.connect(self._edited)
        self.separator.currentTextChanged.connect(self._edited)
        for widget in (self.extension, self.filename):
            widget.textEdited.connect(self._edited)
        for widget in (self.trailing, self.header, self.grain_first):
            widget.toggled.connect(self._edited)
        return w

    def _numbers_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        self.unit = QComboBox()
        for label, value in ((tr("Millimetres"), "mm"),
                             (tr("Centimetres"), "cm"), (tr("Metres"), "m"),
                             (tr("Inches (decimal)"), "in")):
            self.unit.addItem(label, value)
        form.addRow(tr("Units"), self.unit)
        self.decimals = QSpinBox()
        self.decimals.setRange(0, 4)
        form.addRow(tr("Decimals"), self.decimals)
        self.decimal_sep = QComboBox()
        self.decimal_sep.addItem(tr("Comma (18,5)"), ",")
        self.decimal_sep.addItem(tr("Dot (18.5)"), ".")
        form.addRow(tr("Decimal separator"), self.decimal_sep)
        self.rounding = QComboBox()
        for label, value in ((tr("To the nearest"), "nearest"),
                             (tr("Always up"), "up"),
                             (tr("Always down"), "down")):
            self.rounding.addItem(label, value)
        form.addRow(tr("Rounding"), self.rounding)
        self.strip_zeros = QCheckBox(tr("No trailing zeros (18,50 → 18,5)"))
        form.addRow("", self.strip_zeros)
        self.suffix = QCheckBox(tr("Write the unit after each number"))
        form.addRow("", self.suffix)
        for widget in (self.unit, self.decimal_sep, self.rounding):
            widget.currentIndexChanged.connect(self._edited)
        self.decimals.valueChanged.connect(self._edited)
        for widget in (self.strip_zeros, self.suffix):
            widget.toggled.connect(self._edited)
        return w

    def _codes_tab(self) -> QWidget:
        w = QWidget()
        box = QVBoxLayout(w)
        hint = QLabel(tr("Your names on the left, the supplier's on the "
                         "right — set once, kept in this profile. Columns "
                         "showing a code stop the export while one is "
                         "missing."))
        hint.setWordWrap(True)
        box.addWidget(hint)
        self.codes = QTableWidget(0, 4)
        self.codes.setObjectName("cutlist_export_codes")
        self.codes.setHorizontalHeaderLabels([
            tr("Kind"), tr("Your name"), tr("Supplier code"),
            tr("Supplier name")])
        self.codes.horizontalHeader().setStretchLastSection(True)
        self.codes.setColumnWidth(1, 240)
        self.codes.setColumnWidth(2, 160)
        self.codes.itemChanged.connect(self._edited)
        box.addWidget(self.codes)
        return w

    # =====================================================================
    # Profile ⇄ widgets
    # =====================================================================
    def _load(self, p: Profile) -> None:
        self._loading = True
        try:
            self.columns.setRowCount(0)
            for c in p.columns:
                self._insert_column(self.columns.rowCount(), c)
            self._set(self.format, p.format)
            self.extension.setText(p.extension)
            i = self.separator.findData(p.separator)
            if i >= 0:
                self.separator.setCurrentIndex(i)
            else:
                self.separator.setEditText(p.separator)
            self._set(self.encoding, p.encoding)
            self._set(self.newline, p.newline)
            self._set(self.quoting, p.quoting)
            self.trailing.setChecked(p.trailing_separator)
            self.header.setChecked(p.header)
            self._set(self.rows, p.rows)
            self.split.clear()
            self.split.addItem(tr("One file"), "none")
            self.split.addItem(tr("One file per board (material + "
                                  "thickness)"), "board")
            for name in self.session.fields:
                self.split.addItem(tr("One file per {field}", field=name),
                                   f"field:{name}")
            self._set(self.split, p.split)
            self.filename.setText(p.filename)
            self.grain_first.setChecked(p.grain_first)
            n = p.numbers
            self._set(self.unit, n.unit)
            self.decimals.setValue(n.decimals)
            self._set(self.decimal_sep, n.decimal_sep)
            self._set(self.rounding, n.rounding)
            self.strip_zeros.setChecked(n.strip_zeros)
            self.suffix.setChecked(n.suffix)
            self._load_codes(p)
        finally:
            self._loading = False
        self.profile = p
        self._update()

    @staticmethod
    def _set(combo: QComboBox, value) -> None:
        i = combo.findData(value)
        if i >= 0:
            combo.setCurrentIndex(i)

    def _field_choices(self) -> list[tuple[str, str]]:
        return [(field_label(f), f) for f in FIELDS] + \
            [(tr("Custom field: {name}", name=n), f"field:{n}")
             for n in self.session.fields]

    def _insert_column(self, r: int, c: Column) -> None:
        self.columns.blockSignals(True)
        try:
            self.columns.insertRow(r)
            on = QTableWidgetItem()
            on.setFlags((on.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                        & ~Qt.ItemFlag.ItemIsEditable)
            on.setCheckState(Qt.CheckState.Unchecked if c.hidden
                             else Qt.CheckState.Checked)
            self.columns.setItem(r, ON, on)
            self.columns.setItem(r, HEADER, QTableWidgetItem(c.header))
            kind = QComboBox()
            kind.addItem(tr("Field"), "field")
            kind.addItem(tr("Fixed text"), "text")
            kind.addItem(tr("Template"), "template")
            self._set(kind, c.kind)
            kind.currentIndexChanged.connect(
                lambda _i, k=kind: self._kind_changed(k))
            self.columns.setCellWidget(r, KIND, kind)
            self._value_widget(r, c.kind, c.value)
            for col_index, word in ((YES, c.yes), (NO, c.no)):
                item = QTableWidgetItem(word)
                item.setData(_KEPT, word)
                self.columns.setItem(r, col_index, item)
            self.columns.setCellWidget(r, TEXT, self._text_button(c.text))
        finally:
            self.columns.blockSignals(False)
        self._sync_row(r)

    def _is_on(self, r: int) -> bool:
        item = self.columns.item(r, ON)
        return item is None or item.checkState() == Qt.CheckState.Checked

    def _uses_yes_no(self, r: int) -> bool:
        """Yes/No words matter for yes-or-no fields (grain, may rotate,
        band yes/no) and for templates (which may use them)."""
        kind = self.columns.cellWidget(r, KIND)
        kind = kind.currentData() if kind is not None else "field"
        if kind == "template":
            return True
        if kind != "field":
            return False
        value = self.columns.cellWidget(r, VALUE)
        return value is not None and value.currentData() in FLAG_FIELDS

    def _sync_row(self, r: int) -> None:
        """How a row looks: faded when the column is off; Yes/No shown and
        editable only where they are used (elsewhere empty and greyed, the
        words kept for when the column changes back)."""
        on = self._is_on(r)
        uses = self._uses_yes_no(r)
        grey = self.palette().color(self.palette().ColorRole.PlaceholderText)
        text = self.palette().color(self.palette().ColorRole.Text)
        self.columns.blockSignals(True)
        try:
            for col_index in (YES, NO):
                item = self.columns.item(r, col_index)
                if item is None:
                    continue
                if uses:
                    item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable
                                  | Qt.ItemFlag.ItemIsEnabled)
                    item.setText(item.data(_KEPT) or "")
                else:
                    if item.text():
                        item.setData(_KEPT, item.text())
                    item.setText("")
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable
                                  & ~Qt.ItemFlag.ItemIsEnabled)
            for col_index in (HEADER, VALUE, YES, NO):
                item = self.columns.item(r, col_index)
                if item is not None:
                    item.setForeground(text if on else grey)
            for col_index in (KIND, VALUE, TEXT):
                widget = self.columns.cellWidget(r, col_index)
                if widget is not None:
                    widget.setEnabled(on)
        finally:
            self.columns.blockSignals(False)

    def _item_changed(self, item) -> None:
        if item.column() == ON:
            self._sync_row(item.row())
        self._edited()

    def _text_button(self, options) -> QToolButton:
        """Text options of one column, ticked in a small menu; the button
        names what is on ("UPPERCASE, Spaces → _") or "As is"."""
        button = QToolButton()
        button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        menu = QMenu(button)
        for option in TEXT_OPTIONS:
            act = menu.addAction(text_option_label(option))
            act.setCheckable(True)
            act.setChecked(option in options)
            act.setData(option)
            act.toggled.connect(lambda _on, b=button: self._text_changed(b))
        button.setMenu(menu)
        self._label_text_button(button)
        return button

    @staticmethod
    def _text_options(button) -> tuple[str, ...]:
        if button is None:
            return ()
        return tuple(a.data() for a in button.menu().actions()
                     if a.isChecked())

    def _label_text_button(self, button) -> None:
        on = self._text_options(button)
        button.setText(", ".join(text_option_label(o) for o in on)
                       if on else tr("As is"))

    def _text_changed(self, button) -> None:
        self._label_text_button(button)
        self._edited()

    def _value_widget(self, r: int, kind: str, value: str) -> None:
        if kind == "field":
            combo = QComboBox()
            for label, data in self._field_choices():
                combo.addItem(label, data)
            self._set(combo, value)
            combo.currentIndexChanged.connect(
                lambda _i, w=combo: self._value_changed(w))
            self.columns.setCellWidget(r, VALUE, combo)
        else:
            self.columns.removeCellWidget(r, VALUE)
            self.columns.setItem(r, VALUE, QTableWidgetItem(value))

    def _kind_changed(self, kind_combo: QComboBox) -> None:
        for r in range(self.columns.rowCount()):
            if self.columns.cellWidget(r, KIND) is kind_combo:
                self._value_widget(r, kind_combo.currentData(), "")
                self._sync_row(r)
        self._edited()

    def _value_changed(self, combo: QComboBox) -> None:
        for r in range(self.columns.rowCount()):
            if self.columns.cellWidget(r, VALUE) is combo:
                self._sync_row(r)
        self._edited()

    def _load_codes(self, p: Profile) -> None:
        self.codes.setRowCount(0)
        rows = [("material", n, p.material_codes.get(n, {}))
                for n in sorted(set(self.session.materials)
                                | set(p.material_codes), key=str.lower)]
        rows += [("band", n, p.band_codes.get(n, {}))
                 for n in sorted(set(self.session.bands)
                                 | set(p.band_codes), key=str.lower)]
        for kind, name, entry in rows:
            r = self.codes.rowCount()
            self.codes.insertRow(r)
            k = QTableWidgetItem(tr("Material") if kind == "material"
                                 else tr("Band"))
            k.setData(Qt.ItemDataRole.UserRole, kind)
            k.setFlags(k.flags() & ~Qt.ItemFlag.ItemIsEditable)
            n = QTableWidgetItem(name)
            n.setFlags(n.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.codes.setItem(r, 0, k)
            self.codes.setItem(r, 1, n)
            self.codes.setItem(r, 2, QTableWidgetItem(entry.get("code", "")))
            self.codes.setItem(r, 3, QTableWidgetItem(
                entry.get("supplier", "")))

    def current(self) -> Profile:
        """The profile as the widgets show it."""
        cols = []
        for r in range(self.columns.rowCount()):
            def text(c, r=r):
                item = self.columns.item(r, c)
                return item.text() if item else ""
            kind = self.columns.cellWidget(r, KIND).currentData()
            value_widget = self.columns.cellWidget(r, VALUE)
            value = value_widget.currentData() if kind == "field" and \
                value_widget is not None else text(VALUE)

            def word(c, default, r=r):
                item = self.columns.item(r, c)
                if item is None:
                    return default
                if self._uses_yes_no(r):
                    return item.text()
                kept = item.data(_KEPT)
                return default if kept is None else kept
            cols.append(Column(
                header=text(HEADER), kind=kind, value=value or "",
                yes=word(YES, "1"), no=word(NO, "0"),
                text=self._text_options(self.columns.cellWidget(r, TEXT)),
                hidden=not self._is_on(r)))
        material_codes, band_codes = {}, {}
        for r in range(self.codes.rowCount()):
            kind = self.codes.item(r, 0).data(Qt.ItemDataRole.UserRole)
            name = self.codes.item(r, 1).text()
            code = (self.codes.item(r, 2).text() or "").strip()
            supplier = (self.codes.item(r, 3).text() or "").strip()
            if code or supplier:
                target = material_codes if kind == "material" else band_codes
                target[name] = {"code": code, "supplier": supplier}
        sep = self.separator.currentData()
        typed = self.separator.currentText()
        if sep is None or self.separator.itemText(
                self.separator.currentIndex()) != typed:
            sep = typed.replace("\\t", "\t")
        return replace(
            self.profile,
            format=self.format.currentData(),
            extension=self.extension.text().strip().lstrip(".") or "csv",
            separator=sep or ";",
            encoding=self.encoding.currentData(),
            newline=self.newline.currentData(),
            quoting=self.quoting.currentData(),
            trailing_separator=self.trailing.isChecked(),
            header=self.header.isChecked(),
            rows=self.rows.currentData(),
            split=self.split.currentData() or "none",
            filename=self.filename.text(),
            grain_first=self.grain_first.isChecked(),
            numbers=Numbers(
                unit=self.unit.currentData(),
                decimals=self.decimals.value(),
                decimal_sep=self.decimal_sep.currentData(),
                rounding=self.rounding.currentData(),
                strip_zeros=self.strip_zeros.isChecked(),
                suffix=self.suffix.isChecked()),
            columns=tuple(cols),
            material_codes=material_codes, band_codes=band_codes)

    # =====================================================================
    # Columns editing
    # =====================================================================
    def _add_column(self) -> None:
        r = self.columns.currentRow() + 1 if self.columns.currentRow() >= 0 \
            else self.columns.rowCount()
        self._insert_column(r, Column(header=tr("New column"), value="name"))
        self.columns.selectRow(r)
        self._edited()

    def _remove_column(self) -> None:
        r = self.columns.currentRow()
        if r >= 0:
            self.columns.removeRow(r)
            self._edited()

    def _move_column(self, step: int) -> None:
        r = self.columns.currentRow()
        if r < 0 or not 0 <= r + step < self.columns.rowCount():
            return
        self._move_column_to(r, r + step + (1 if step > 0 else 0))

    def _move_column_to(self, source: int, target: int) -> None:
        """Move column ``source`` to sit before row ``target`` (a drop, or
        Move up / down)."""
        cols = list(self.current().columns)
        if not 0 <= source < len(cols):
            return
        col = cols.pop(source)
        at = target - 1 if target > source else target
        at = max(0, min(at, len(cols)))
        cols.insert(at, col)
        self._load(replace(self.current(), columns=tuple(cols)))
        self.columns.selectRow(at)
        self._edited()

    # =====================================================================
    # Preview, problems, the profile combo
    # =====================================================================
    def _edited(self, *_args) -> None:
        if self._loading:
            return
        self.profile = self.current()
        self._update()

    def _fill_combo(self) -> None:
        self.combo.blockSignals(True)
        self.combo.clear()
        for name in sorted(self.profiles, key=str.lower):
            self.combo.addItem(name, name)
        self.combo.setCurrentIndex(self.combo.findData(self.saved.name))
        self.combo.blockSignals(False)

    def _mark(self) -> None:
        dirty = self.profile != self.saved
        i = self.combo.findData(self.saved.name)
        if i >= 0:
            self.combo.setItemText(i, self.saved.name + (" *" if dirty
                                                         else ""))

    def result_export(self) -> Export:
        return self.session.rows(self.profile)

    def _update(self) -> None:
        self._mark()
        ex = self.result_export()
        problems = list(ex.problems)
        if self.profile.format != "xlsx":
            for f in ex.files:
                problems += unencodable(f, self.profile)
        self._problems = problems
        if problems:
            self.problems.setText(tr("Fix before exporting:") + " " +
                                  "; ".join(problem_text(p.kind, p.value,
                                                         p.count)
                                            for p in problems[:8]))
        else:
            self.problems.setText("")
        self.preview.setPlainText(self._preview_text(ex))
        rows = sum(len(f.rows) for f in ex.files)
        self.summary.setText(tr("{rows} rows in {files} file(s): {names}",
                                rows=rows, files=len(ex.files),
                                names=", ".join(f.name for f in ex.files)))
        blocked = bool(problems) or not ex.files
        self.export_button.setEnabled(not blocked and
                                      self.profile.format != "clipboard")
        self.copy_button.setEnabled(not blocked)

    def _preview_text(self, ex: Export) -> str:
        p = self.profile
        if p.format == "clipboard" or p.format == "xlsx":
            return clipboard_text(ex.files, p).replace("\t", " │ ")[:20000]
        out = []
        for f in ex.files:
            if len(ex.files) > 1:
                out.append(f"── {f.name} ──")
            lines = text_lines(f, p)
            out.extend(line.replace("\t", "→") for line in
                       lines[:PREVIEW_ROWS])
            if len(lines) > PREVIEW_ROWS:
                out.append(tr("… {n} more rows", n=len(lines) -
                              PREVIEW_ROWS))
        return "\n".join(out)

    # ---- the profile bar --------------------------------------------------------
    def _pick_profile(self, index: int) -> None:
        name = self.combo.itemData(index)
        if self.profile != self.saved and not self._confirm_discard():
            self._fill_combo()
            self._mark()
            return
        self.saved = self.profiles[name]
        self._load(self.saved)
        self._persist()

    def _confirm_discard(self) -> bool:
        return QMessageBox.question(
            self, self.windowTitle(),
            tr("Discard the changes to “{name}”?", name=self.saved.name)
        ) == QMessageBox.StandardButton.Yes

    def _persist(self) -> None:
        self.session.save(self.profiles, self.saved.name)

    def save_profile(self) -> None:
        self.saved = replace(self.current(), name=self.saved.name)
        self.profiles[self.saved.name] = self.saved
        self.profile = self.saved
        self._persist()
        self._mark()

    def _ask_name(self, title: str, default: str) -> str | None:
        name, ok = QInputDialog.getText(self, title, tr("Profile name"),
                                        text=default)
        name = (name or "").strip()
        if not ok or not name:
            return None
        if name in self.profiles and name != self.saved.name:
            QMessageBox.warning(self, title, tr("There is already a profile "
                                                "called “{name}”.", name=name))
            return None
        return name

    def save_profile_as(self, name: str | None = None) -> None:
        name = name or self._ask_name(tr("Save as a new profile"),
                                      self.saved.name)
        if not name:
            return
        self.saved = replace(self.current(), name=name)
        self.profiles[name] = self.saved
        self.profile = self.saved
        self._fill_combo()
        self._persist()
        self._mark()

    def rename_profile(self) -> None:
        name = self._ask_name(tr("Rename profile"), self.saved.name)
        if not name or name == self.saved.name:
            return
        del self.profiles[self.saved.name]
        self.saved = replace(self.saved, name=name)
        self.profile = replace(self.profile, name=name)
        self.profiles[name] = self.saved
        self._fill_combo()
        self._persist()
        self._mark()

    def delete_profile(self) -> None:
        if len(self.profiles) == 1:
            QMessageBox.information(self, self.windowTitle(),
                                    tr("The last profile cannot be "
                                       "deleted."))
            return
        if QMessageBox.question(
                self, self.windowTitle(),
                tr("Delete the profile “{name}”?", name=self.saved.name)
        ) != QMessageBox.StandardButton.Yes:
            return
        del self.profiles[self.saved.name]
        self.saved = self.profiles[sorted(self.profiles, key=str.lower)[0]]
        self._fill_combo()
        self._load(self.saved)
        self._persist()

    def import_profile(self) -> None:
        import json
        path, _ = QFileDialog.getOpenFileName(
            self, tr("Import a profile"), self.session.suggested_folder,
            tr("Cut List profile (*.json)"))
        if not path:
            return
        try:
            with open(path, encoding="utf-8") as fh:
                p = Profile.from_dict(json.load(fh))
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, self.windowTitle(), str(exc))
            return
        name = p.name
        n = 2
        while name in self.profiles:
            name = f"{p.name} ({n})"
            n += 1
        self.saved = replace(p, name=name)
        self.profiles[name] = self.saved
        self._fill_combo()
        self._load(self.saved)
        self._persist()

    def export_profile(self) -> None:
        import json
        path, _ = QFileDialog.getSaveFileName(
            self, tr("Export this profile"),
            f"{self.saved.name}.json", tr("Cut List profile (*.json)"))
        if path:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(self.current().to_dict(), fh, ensure_ascii=False,
                          indent=2)

    # ---- output ------------------------------------------------------------
    def copy(self) -> None:
        ex = self.result_export()
        self.session.copy(clipboard_text(ex.files, self.profile))
        self.summary.setText(tr("Copied {rows} rows to the clipboard.",
                                rows=sum(len(f.rows) for f in ex.files)))

    def export(self, folder: str | None = None) -> None:
        from ..export.writers import file_bytes
        ex = self.result_export()
        if not ex.files or self._problems:
            return
        if folder is None:
            if len(ex.files) == 1:
                path, _ = QFileDialog.getSaveFileName(
                    self, tr("Export the cut list"),
                    _join(self.session.suggested_folder, ex.files[0].name))
                if not path:
                    return
                import os
                folder, name = os.path.split(path)
                ex.files[0].name = name
            else:
                folder = QFileDialog.getExistingDirectory(
                    self, tr("Folder for the {n} files", n=len(ex.files)),
                    self.session.suggested_folder)
                if not folder:
                    return
        self.session.write(folder, {f.name: file_bytes(f, self.profile)
                                    for f in ex.files})
        self.summary.setText(tr("Wrote {n} file(s) to {folder}.",
                                n=len(ex.files), folder=folder))


def _join(folder: str, name: str) -> str:
    import os
    return os.path.join(folder, name) if folder else name
