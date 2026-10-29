# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Ronaldo Alves and CutList contributors.
"""The labels window (D-018): pick the sticker sheet, where to start on a
sheet already used, see the first page, write the PDF."""
from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..export.labels import SHEETS, LabelSheet, Options, build
from ..export.plan import PAGES
from ..i18n import tr
from .plan_painter import draw_shapes, write_pdf

CUSTOM = "custom"


class _Preview(QWidget):
    """The first page, as it will print."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.page = None
        self.size_name = "A4"
        self.setMinimumSize(260, 360)

    def show_page(self, page, size_name: str) -> None:
        self.page, self.size_name = page, size_name
        self.update()

    def sizeHint(self) -> QSize:
        return QSize(380, 520)

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.fillRect(self.rect(), self.palette().window())
        pw, ph = PAGES.get(self.size_name, PAGES["A4"])
        k = min((self.width() - 16) / pw, (self.height() - 16) / ph)
        ox = (self.width() - pw * k) / 2 / k
        oy = (self.height() - ph * k) / 2 / k
        p.fillRect(int(ox * k), int(oy * k), int(pw * k), int(ph * k),
                   Qt.GlobalColor.white)
        if self.page is not None:
            draw_shapes(p, self.page.shapes, k, dx=ox, dy=oy)
        p.end()


class LabelsDialog(QDialog):
    """``labels``: the :class:`Label` list, one per piece. ``options``
    and ``save_options``: the user's remembered choice of sheet."""

    def __init__(self, labels, *, title: str, options: dict,
                 save_options, folder: str = "", stem: str = "labels",
                 folder_used=None, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("cutlist_labels_dialog")
        self.setWindowTitle(tr("Cut List — Labels"))
        self.labels = list(labels)
        self._save_options = save_options
        self._folder, self._stem = folder, stem
        self._folder_used = folder_used or (lambda _f: None)
        o = dict(options or {})

        outer = QHBoxLayout(self)
        left = QVBoxLayout()
        outer.addLayout(left)
        intro = QLabel(title + "\n" + tr("{n} labels, one per piece.",
                                         n=len(self.labels)))
        intro.setWordWrap(True)
        left.addWidget(intro)

        form = QFormLayout()
        self.sheet = QComboBox()
        self.sheet.setObjectName("cutlist_label_sheet")
        for s in SHEETS:
            self.sheet.addItem(s.name, s.name)
        self.sheet.addItem(tr("Custom sheet…"), CUSTOM)
        i = self.sheet.findData(o.get("sheet", SHEETS[0].name))
        self.sheet.setCurrentIndex(max(0, i))
        form.addRow(tr("Sticker sheet"), self.sheet)
        self.start = QSpinBox()
        self.start.setObjectName("cutlist_label_start")
        self.start.setMinimum(1)
        self.start.setToolTip(tr("On a sheet already used: the first free "
                                 "label, counted along the rows."))
        form.addRow(tr("Start at label"), self.start)
        self.frames = QCheckBox(tr("Outline each label (to test on plain "
                                   "paper)"))
        self.frames.setChecked(bool(o.get("frames", False)))
        form.addRow("", self.frames)
        left.addLayout(form)

        self.custom = QGroupBox(tr("Custom sheet (mm)"))
        cform = QFormLayout(self.custom)
        c = o.get("custom") or {}
        self.page = QComboBox()
        self.page.addItems(["A4", "Letter"])
        self.page.setCurrentText(c.get("page", "A4"))
        cform.addRow(tr("Paper"), self.page)
        self.cols, self.rows = QSpinBox(), QSpinBox()
        for box, value in ((self.cols, c.get("cols", 3)),
                           (self.rows, c.get("rows", 7))):
            box.setRange(1, 20)
            box.setValue(int(value))
        grid = QHBoxLayout()
        grid.addWidget(self.cols)
        grid.addWidget(QLabel("×"))
        grid.addWidget(self.rows)
        cform.addRow(tr("Columns × rows"), grid)
        self.dims = {}
        for key, label, value in (
                ("w", tr("Label width"), 63.5), ("h", tr("Label height"), 38.1),
                ("left", tr("Left margin"), 7.2), ("top", tr("Top margin"),
                                                   15.15),
                ("dx", tr("Across, label to label"), 66.04),
                ("dy", tr("Down, label to label"), 38.1)):
            spin = QDoubleSpinBox()
            spin.setRange(0.0, 300.0)
            spin.setDecimals(2)
            spin.setValue(float(c.get(key, value)))
            spin.valueChanged.connect(self._changed)
            self.dims[key] = spin
            cform.addRow(label, spin)
        left.addWidget(self.custom)
        left.addStretch(1)

        row = QHBoxLayout()
        pdf = QPushButton(tr("PDF…"))
        pdf.setObjectName("cutlist_labels_pdf")
        pdf.clicked.connect(lambda _c=False: self.export_pdf())
        close = QPushButton(tr("Close"))
        close.clicked.connect(lambda _c=False: self.close())
        row.addWidget(pdf)
        row.addWidget(close)
        left.addLayout(row)

        self.preview = _Preview()
        outer.addWidget(self.preview, 1)

        for w in (self.sheet, self.page):
            w.currentIndexChanged.connect(self._changed)
        for w in (self.cols, self.rows, self.start):
            w.valueChanged.connect(self._changed)
        self.frames.toggled.connect(self._changed)
        self._changed()

    def label_sheet(self) -> LabelSheet:
        data = self.sheet.currentData()
        if data != CUSTOM:
            return next(s for s in SHEETS if s.name == data)
        d = {k: s.value() for k, s in self.dims.items()}
        return LabelSheet(tr("Custom sheet"), self.page.currentText(),
                          self.cols.value(), self.rows.value(), **d)

    def options(self) -> Options:
        return Options(sheet=self.label_sheet(), start=self.start.value(),
                       frames=self.frames.isChecked())

    def _changed(self, *_args) -> None:
        sheet = self.label_sheet()
        self.custom.setVisible(self.sheet.currentData() == CUSTOM)
        self.start.setMaximum(sheet.per_page)
        pages = build(self.labels, self.options())
        self.preview.show_page(pages.pages[0] if pages.pages else None,
                               pages.size)

    def _remember(self) -> None:
        o = {"sheet": self.sheet.currentData(),
             "frames": self.frames.isChecked()}
        if self.sheet.currentData() == CUSTOM:
            s = self.label_sheet()
            o["custom"] = {"page": s.page, "cols": s.cols, "rows": s.rows,
                           "w": s.w, "h": s.h, "left": s.left, "top": s.top,
                           "dx": s.dx, "dy": s.dy}
        self._save_options(o)

    def export_pdf(self, path: str | None = None) -> str | None:
        if not self.labels:
            return None
        if path is None:
            import os
            path, _ = QFileDialog.getSaveFileName(
                self, tr("Labels as PDF"),
                os.path.join(self._folder, f"{self._stem}.pdf")
                if self._folder else f"{self._stem}.pdf", tr("PDF (*.pdf)"))
            if not path:
                return None
        self._remember()
        pages = build(self.labels, self.options())
        write_pdf(path, pages.pages, pages.size)
        import os
        self._folder_used(os.path.dirname(path))
        return path

