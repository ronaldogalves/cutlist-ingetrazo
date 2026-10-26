# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Ronaldo Alves and CutList contributors.
"""The cutting diagrams window (M3).

Boards on the left, the sheets of the chosen board in the middle, how to
print on the right. The sheets answer the mouse (D-016 §8): a part shows
the cuts that free it, a cut its fence distance, and a first-stage cut
says it can go first. A right-click fixes a part where it is seen — grain,
rotation, its settings — and the layout is redone for the same parts
(D-014 §2). Packing runs on a worker thread; results come back through a
queued signal to a bound method (CLAUDE.md, threading).

The window knows nothing of IngeTrazo: a :class:`DiagramSession` from the
host gives it the parts, the settings and somewhere to store things.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace

from PySide6.QtCore import QObject, QPointF, QSize, Qt, QThread, Signal
from PySide6.QtGui import QFont, QPainter
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QToolTip,
    QVBoxLayout,
    QWidget,
)

from ..export.diagrams import (
    BoardPlan,
    Changes,
    pack_all,
    saved_bands,
    saved_boards,
    saved_leftovers,
)
from ..export.plan import TEXT, Options, build, groups, sheet_shapes
from ..i18n import tr
from ..model.text import fmt_length, parse_length, parse_number
from ..packing.base import Stock
from ..packing.guillotine import GuillotinePacker
from .plan_painter import draw_shapes, shape_at, write_pdf

#: The canvas is laid out this many millimetres wide, then zoomed to fit.
CANVAS_MM = 260.0


def stage_label(stage: int) -> str:
    return {0: tr("Trim"), 1: tr("1st cut (strips)"), 2: tr("2nd cut"),
            3: tr("3rd cut"), 4: tr("4th cut")}.get(stage, str(stage))


@dataclass
class DiagramSession:
    """What the host gives the window."""

    model: str
    date: str
    #: The parts the window covers (uids): the cut list's when it opens.
    scope: list
    #: (scope, leftovers by board id, uids left out) → ``Prepared``.
    prepare: Callable
    #: The saw settings in force; ``save_settings(**values)`` sets them in
    #: the model (one undo step each).
    settings: Callable
    save_settings: Callable
    #: (action, uids) → True when the model changed (the host re-reads).
    part_action: Callable
    show_in_model: Callable
    #: Ask the sheet sizes of these materials once; True when saved.
    ask_sizes: Callable
    options: dict
    save_options: Callable
    layouts: Callable
    save_layout: Callable
    #: (plans, leftovers, left_out) → JSON-safe data to save.
    snapshot: Callable
    #: saved data → :class:`Changes` against the model now.
    changes: Callable
    #: uids → readable part names, for messages.
    names: Callable
    suggested_folder: str = ""
    #: Told where files were written, to open there next time.
    folder_used: Callable = lambda _folder: None


# ---------------------------------------------------------------------------
# Packing off the main thread
# ---------------------------------------------------------------------------

class _Worker(QObject):
    done = Signal(object)

    def __init__(self, plans, generation) -> None:
        super().__init__()
        self.plans, self.generation = plans, generation

    def run(self) -> None:
        try:
            pack_all(self.plans, GuillotinePacker())
            self.done.emit((self.generation, self.plans, None))
        except Exception as exc:            # noqa: BLE001 — reported in UI
            self.done.emit((self.generation, None, exc))


# ---------------------------------------------------------------------------
# The sheets
# ---------------------------------------------------------------------------

class SheetsCanvas(QWidget):
    """Every sheet of one board, stacked, drawn from the plan shapes."""

    part_menu = Signal(str, object)         # key, global pos

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("cutlist_sheets_canvas")
        self.setMouseTracking(True)
        self.board = None                   # export.plan.Board
        self.group_identical = True
        self.blocks: list = []              # (sheet, count, shapes, y)
        self.height_mm = 10.0
        self.highlight: set = set()
        self.fmt = lambda m: f"{round(m * 1000)}"

    def set_board(self, board, group_identical: bool) -> None:
        self.board = board
        self.group_identical = group_identical
        self.highlight = set()
        self._layout()
        self.update()

    def _layout(self) -> None:
        self.blocks = []
        y = 4.0
        if self.board is None:
            self.height_mm = 10.0
            self.updateGeometry()
            return
        t = TEXT["compact"]
        sheets = groups(self.board.layout.sheets) if self.group_identical \
            else [(s, 1) for s in self.board.layout.sheets]
        for i, (sheet, count) in enumerate(sheets):
            y += t * 1.8                     # the heading
            shapes, used = sheet_shapes(
                sheet, 6.0, y, CANVAS_MM - 12.0, 400.0, size=t,
                fmt=self.fmt, grain=self.board.grain)
            shapes = [replace(s, ref=f"{i}:{s.ref}")
                      if s.ref.startswith(("cut:", "leftover:")) else s
                      for s in shapes]
            self.blocks.append((sheet, count, shapes, y - t * 1.8))
            y += used + 8.0
        self.height_mm = y
        self.updateGeometry()

    def k(self) -> float:
        return max(self.width(), 200) / CANVAS_MM

    def sizeHint(self) -> QSize:
        return QSize(800, int(self.height_mm * self.k()))

    def resizeEvent(self, event) -> None:
        self.setMinimumHeight(int(self.height_mm * self.k()))
        super().resizeEvent(event)

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.fillRect(self.rect(), Qt.GlobalColor.white)
        k = self.k()
        t = TEXT["compact"]
        n = len(self.blocks)
        for i, (sheet, count, shapes, y) in enumerate(self.blocks):
            p.setPen(Qt.GlobalColor.black)
            font = QFont(self.font())
            font.setBold(True)
            font.setPixelSize(max(9, round(t * 1.1 * k)))
            p.setFont(font)
            label = tr("Sheet {n} of {total}", n=i + 1, total=n) + \
                f"   ·   {self.fmt(sheet.stock.length)} × " \
                f"{self.fmt(sheet.stock.width)}   ·   " + \
                tr("{p:.0%} used", p=sheet.efficiency)
            if count > 1:
                label += "   ·   " + tr("×{n} — cut {n} identical sheets",
                                        n=count)
            if sheet.stock.leftover:
                label += "   ·   " + tr("a leftover from the shop")
            p.drawText(QPointF(6.0 * k, (y + t * 1.2) * k), label)
            draw_shapes(p, shapes, k, highlight=self.highlight)
        p.end()

    # ---- the mouse ----------------------------------------------------------
    def _at(self, pos):
        k = self.k()
        x, y = pos.x() / k, pos.y() / k
        for i, (sheet, _count, shapes, _y) in enumerate(self.blocks):
            part = shape_at(shapes, x, y)
            if part is not None:
                return ("part", i, sheet, part, shapes)
            for s in shapes:
                if s.kind == "line" and s.ref.startswith(f"{i}:cut:"):
                    if _near(s, x, y, 1.0):
                        return ("cut", i, sheet, s, shapes)
        return None

    def mouseMoveEvent(self, event) -> None:
        hit = self._at(event.position())
        highlight, tip = set(), ""
        if hit and hit[0] == "part":
            _kind, i, sheet, shape, _shapes = hit
            tip, cut_refs = self._part_tip(sheet, shape.ref, i)
            highlight = {shape.ref, *cut_refs}
        elif hit and hit[0] == "cut":
            _kind, i, sheet, shape, _shapes = hit
            index = int(shape.ref.split(":")[-1])
            tip = self._cut_tip(sheet, sheet.cuts[index])
            highlight = {shape.ref}
        if highlight != self.highlight:
            self.highlight = highlight
            self.update()
        if tip:
            QToolTip.showText(event.globalPosition().toPoint(), tip, self)
        else:
            QToolTip.hideText()

    def leaveEvent(self, _event) -> None:
        if self.highlight:
            self.highlight = set()
            self.update()

    def contextMenuEvent(self, event) -> None:
        hit = self._at(QPointF(event.pos()))
        if hit and hit[0] == "part":
            self.part_menu.emit(hit[3].ref, event.globalPos())

    def _part_tip(self, sheet, key, i):
        f = self.fmt
        place = next(p for p in sheet.placements if p.key == key)
        info = self.board.parts.get(key)
        lines = [f"{key} — {info.name if info else ''}",
                 f"{f(place.dx)} × {f(place.dy)}"
                 + ("  " + tr("(turned)") if place.rotated else "")]
        if info and info.finished:
            lines.append(tr("finished {l} × {w}", l=f(info.finished[0]),
                            w=f(info.finished[1])))
        freeing = [(c.stage, n, c) for n, c in enumerate(sheet.cuts)
                   if c.stage and c.parent and _inside(place, c.parent)]
        if freeing:
            lines.append(tr("The cuts that free it:"))
            for stage, _n, c in sorted(freeing, key=lambda t: (t[0], t[1])):
                lines.append(f"  {stage_label(stage)}: " + tr(
                    "fence at {d}", d=f(c.fence)))
        return "\n".join(lines), {f"{i}:cut:{n}" for _s, n, _c in freeing}

    def _cut_tip(self, sheet, cut) -> str:
        f = self.fmt
        lines = [stage_label(cut.stage),
                 tr("fence at {d} from the edge of the piece", d=f(cut.fence)),
                 tr("{l} long", l=f(cut.length))]
        if cut.stage == 1 and cut.parent is not None:
            p = cut.parent
            if cut.across:
                a, b = cut.x0 - p.x, p.x + p.dx - cut.x0
                rest = p.dy
            else:
                a, b = cut.y0 - p.y, p.y + p.dy - cut.y0
                rest = p.dx
            lines.append(tr("Can go first: it runs across the whole sheet."))
            lines.append(tr("Splits it into {a} and {b}",
                            a=f"{f(rest)} × {f(a)}",
                            b=f"{f(rest)} × {f(max(0.0, b))}"))
        return "\n".join(lines)


def _near(s, x, y, tol) -> bool:
    if s.w == 0:                            # vertical
        return abs(x - s.x) <= tol and min(s.y, s.y + s.h) - tol <= y <= \
            max(s.y, s.y + s.h) + tol
    return abs(y - s.y) <= tol and min(s.x, s.x + s.w) - tol <= x <= \
        max(s.x, s.x + s.w) + tol


def _inside(place, rect, eps=1e-6) -> bool:
    return (rect.x - eps <= place.x and place.x + place.dx <= rect.x + rect.dx
            + eps and rect.y - eps <= place.y
            and place.y + place.dy <= rect.y + rect.dy + eps)


# ---------------------------------------------------------------------------
# The window
# ---------------------------------------------------------------------------

class DiagramWindow(QDialog):
    def __init__(self, session: DiagramSession, saved: str | None = None,
                 parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("cutlist_diagram_window")
        self.setWindowTitle(tr("Cut List — Cutting diagrams"))
        self.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint)
        self.resize(1280, 820)
        self.session = session
        self.scope: list[str] = list(session.scope)
        self.plans: list[BoardPlan] = []
        self.boards = []                    # export.plan.Board, shown
        self.leftovers: dict[str, tuple[Stock, ...]] = {}
        self.left_out: frozenset[str] = frozenset()
        self.saved_name: str | None = None
        self.saved_data: dict | None = None
        self.skipped: list = []
        self.bands: list = []
        self._generation = 0
        self._threads: list = []
        #: The user cancelled before anything was laid out: do not show.
        self.cancelled = False

        outer = QVBoxLayout(self)
        top = QHBoxLayout()
        self.status = QLabel()
        self.status.setObjectName("cutlist_diagram_status")
        self.status.setWordWrap(True)
        top.addWidget(self.status, 1)
        self.redo_button = QPushButton(tr("Redo the layout for these parts"))
        self.redo_button.setObjectName("cutlist_diagram_redo")
        self.redo_button.clicked.connect(lambda _c=False: self.redo_saved())
        self.redo_button.hide()
        top.addWidget(self.redo_button)
        save = QPushButton(tr("Save layout…"))
        save.setObjectName("cutlist_diagram_save")
        save.clicked.connect(lambda _c=False: self.save_layout())
        top.addWidget(save)
        self.open_button = QToolButton()
        self.open_button.setText(tr("Saved layouts"))
        self.open_button.setPopupMode(
            QToolButton.ToolButtonPopupMode.InstantPopup)
        self._open_menu = QMenu(self.open_button)
        self._open_menu.aboutToShow.connect(self._fill_open_menu)
        self.open_button.setMenu(self._open_menu)
        top.addWidget(self.open_button)
        outer.addLayout(top)

        split = QSplitter()
        outer.addWidget(split, 1)
        split.addWidget(self._left())
        self.canvas = SheetsCanvas()
        self.canvas.part_menu.connect(self._part_menu)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.canvas)
        split.addWidget(scroll)
        split.addWidget(self._right())
        split.setStretchFactor(1, 1)
        split.setSizes([300, 760, 260])

        if saved is not None:
            self.open_saved(saved)
        else:
            self.start()

    # ---- panels -------------------------------------------------------------
    def _left(self) -> QWidget:
        w = QWidget()
        box = QVBoxLayout(w)
        box.addWidget(QLabel(tr("Boards")))
        self.board_list = QListWidget()
        self.board_list.setObjectName("cutlist_diagram_boards")
        self.board_list.currentRowChanged.connect(self._show_board)
        box.addWidget(self.board_list, 2)

        saw = QGroupBox(tr("The saw"))
        form = QFormLayout(saw)
        s = self.session.settings()
        self.first_cut = QComboBox()
        for label, value in ((tr("Best of both"), "best"),
                             (tr("Lengthwise first"), "length"),
                             (tr("Crosswise first"), "width")):
            self.first_cut.addItem(label, value)
        self.first_cut.setToolTip(tr("Crosswise first cuts the sheet into "
                                     "shorter pieces before the rest: easier "
                                     "when you cut alone."))
        self.stages = QComboBox()
        for label, value in ((tr("2 — strips, then parts"), 2),
                             (tr("3 — one more cut on a part"), 3),
                             (tr("4 — tighter, more handling"), 4)):
            self.stages.addItem(label, value)
        self.kerf = QLineEdit(fmt_length(s.kerf))
        self.kerf.setToolTip(tr("The blade's width. Sectioning saws at "
                                "cutting services are usually 5 mm."))
        self.trim = QLineEdit(fmt_length(s.trim))
        self.trim_edges = QComboBox()
        self.trim_edges.addItem(tr("All four edges"), 4)
        self.trim_edges.addItem(tr("Two (where the saw starts)"), 2)
        for combo, value in ((self.first_cut, s.first_cut),
                             (self.stages, s.cut_stages),
                             (self.trim_edges, s.trim_edges)):
            combo.setCurrentIndex(max(0, combo.findData(value)))
        form.addRow(tr("First cuts"), self.first_cut)
        form.addRow(tr("Stages"), self.stages)
        form.addRow(tr("Kerf (mm)"), self.kerf)
        form.addRow(tr("Trim (mm)"), self.trim)
        form.addRow(tr("Trim on"), self.trim_edges)
        apply = QPushButton(tr("Redo the layout"))
        apply.setObjectName("cutlist_diagram_apply")
        apply.clicked.connect(lambda _c=False: self._apply_saw())
        form.addRow("", apply)
        box.addWidget(saw)

        left = QGroupBox(tr("Leftovers from the shop (this board)"))
        lbox = QVBoxLayout(left)
        self.leftover_table = QTableWidget(0, 3)
        self.leftover_table.setObjectName("cutlist_diagram_leftovers")
        self.leftover_table.setHorizontalHeaderLabels(
            [tr("Length (mm)"), tr("Width (mm)"), tr("Qty")])
        self.leftover_table.verticalHeader().hide()
        self.leftover_table.setToolTip(tr("Pieces you already have: used "
                                          "before full sheets, never "
                                          "trimmed."))
        lbox.addWidget(self.leftover_table)
        row = QHBoxLayout()
        add = QPushButton(tr("Add"))
        add.clicked.connect(lambda _c=False: self._add_leftover())
        use = QPushButton(tr("Use them"))
        use.setObjectName("cutlist_diagram_use_leftovers")
        use.clicked.connect(lambda _c=False: self._read_leftovers())
        row.addWidget(add)
        row.addWidget(use)
        lbox.addLayout(row)
        box.addWidget(left, 1)
        return w

    def _right(self) -> QWidget:
        w = QWidget()
        box = QVBoxLayout(w)
        group = QGroupBox(tr("Printing"))
        form = QFormLayout(group)
        o = self.session.options
        self.page = QComboBox()
        self.page.addItems(["A4", "Letter"])
        self.page.setCurrentText(o.get("page", "A4"))
        self.text = QComboBox()
        self.text.addItem(tr("Large"), "large")
        self.text.addItem(tr("Compact (fewer pages)"), "compact")
        self.text.setCurrentIndex(max(0, self.text.findData(
            o.get("text", "large"))))
        self.group_identical = QCheckBox(tr("Identical sheets once (×n)"))
        self.group_identical.setChecked(o.get("group_identical", True))
        self.group_identical.toggled.connect(lambda _v: self._show_board(
            self.board_list.currentRow()))
        self.totals = QCheckBox(tr("A totals page first"))
        self.totals.setChecked(o.get("totals_page", True))
        self.marks = QCheckBox(tr("Cut positions along the edge"))
        self.marks.setChecked(o.get("cut_marks", False))
        form.addRow(tr("Paper"), self.page)
        form.addRow(tr("Text"), self.text)
        form.addRow("", self.group_identical)
        form.addRow("", self.totals)
        form.addRow("", self.marks)
        box.addWidget(group)
        pdf = QPushButton(tr("PDF…"))
        pdf.setObjectName("cutlist_diagram_pdf")
        pdf.clicked.connect(lambda _c=False: self.export_pdf())
        svg = QPushButton(tr("SVG…"))
        svg.clicked.connect(lambda _c=False: self.export_svg())
        box.addWidget(pdf)
        box.addWidget(svg)
        box.addStretch(1)
        hint = QLabel(tr("Hover a part to see the cuts that free it, a cut to "
                         "see where to set the fence. Right-click a part to "
                         "fix it here."))
        hint.setWordWrap(True)
        hint.setStyleSheet("color: gray;")
        box.addWidget(hint)
        close = QPushButton(tr("Close"))
        close.clicked.connect(lambda _c=False: self.close())
        box.addWidget(close)
        return w

    # ---- laying out -----------------------------------------------------------
    def options(self) -> Options:
        return Options(page=self.page.currentText(),
                       text=self.text.currentData(),
                       group_identical=self.group_identical.isChecked(),
                       totals_page=self.totals.isChecked(),
                       cut_marks=self.marks.isChecked())

    def start(self) -> bool:
        """Prepare the boards and lay them out on the worker thread.

        Boards with no sheet size are asked once. Cancel stops: nothing is
        laid out, and a window that had nothing to show yet is marked
        ``cancelled`` for the host not to open it (Ronaldo, 2026-10-21).
        Boards left without a size are said, not drawn as sheets where
        nothing fits."""
        prep = self.session.prepare(self.scope, self.leftovers,
                                    self.left_out)
        if prep.missing_sizes:
            if not self.session.ask_sizes(prep.missing_sizes):
                if not self.boards:
                    self.cancelled = True
                else:
                    self.status.setText(tr("Cancelled: the layout shown "
                                           "is the one before."))
                return False
            prep = self.session.prepare(self.scope, self.leftovers,
                                        self.left_out)
        unsized = set(prep.missing_sizes)
        prep.plans = [p for p in prep.plans if p.material not in unsized]
        self.skipped = prep.skipped + [(m, "no size") for m in sorted(unsized)]
        self.bands = prep.bands
        if not prep.plans:
            if not self.boards:
                self.cancelled = True
            self.status.setText(tr("Nothing to lay out: no board has a "
                                   "sheet size."))
            return False
        self.saved_name, self.saved_data = None, None
        self.redo_button.hide()
        self._generation += 1
        self.status.setText(tr("Laying out {n} board(s)…",
                               n=len(prep.plans)))
        thread = QThread(self)
        worker = _Worker(prep.plans, self._generation)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.done.connect(self._packed,
                            Qt.ConnectionType.QueuedConnection)
        # quit() is thread-safe: called directly from the worker, it does
        # not wait for the main loop (which may be waiting on the thread).
        worker.done.connect(thread.quit, Qt.ConnectionType.DirectConnection)
        thread.finished.connect(lambda: self._threads.remove(
            (thread, worker)) if (thread, worker) in self._threads else None)
        self._threads.append((thread, worker))
        thread.start()
        return True

    def _packed(self, result) -> None:
        generation, plans, error = result
        if generation != self._generation:
            return                          # an older layout: superseded
        if error is not None:
            self.status.setText(tr("The layout failed: {error}",
                                   error=f"{type(error).__name__}: {error}"))
            return
        self.plans = plans
        self.boards = [p.board() for p in plans]
        self._fill_boards()
        sheets = sum(len(b.layout.sheets) for b in self.boards)
        text = tr("{boards} board(s), {sheets} sheet(s).",
                  boards=len(self.boards), sheets=sheets)
        if self.skipped:
            text += " " + tr("Not laid out: {boards}.", boards=", ".join(
                f"{m or tr('(no material)')} ({_why(why)})"
                for m, why in self.skipped))
        self.status.setText(text)

    def wait(self, ms: int = 10000) -> None:
        """Let the worker finish (tests, closing)."""
        for thread, _worker in list(self._threads):
            thread.wait(ms)

    def _fill_boards(self) -> None:
        row = max(0, self.board_list.currentRow())
        self.board_list.blockSignals(True)
        self.board_list.clear()
        for b in self.boards:
            lay = b.layout
            text = f"{b.material} · {self.canvas.fmt(b.thickness)} mm — " + \
                tr("{n} sheet(s)", n=len(lay.sheets)) + \
                f" · {lay.efficiency:.0%}"
            if lay.unplaced:
                text += "  ⚠"
            item = QListWidgetItem(text)
            if lay.unplaced:
                item.setToolTip(tr("Parts that fit no sheet: {parts}",
                                   parts=", ".join(f"{k} ×{q}"
                                                   for k, q in lay.unplaced)))
            self.board_list.addItem(item)
        self.board_list.blockSignals(False)
        if self.boards:
            self.board_list.setCurrentRow(min(row, len(self.boards) - 1))
            self._show_board(self.board_list.currentRow())
        else:
            self.canvas.set_board(None, True)

    def _show_board(self, row: int) -> None:
        if not (0 <= row < len(self.boards)):
            return
        self.canvas.set_board(self.boards[row],
                              self.group_identical.isChecked())
        self._load_leftovers()

    def current_plan(self) -> BoardPlan | None:
        row = self.board_list.currentRow()
        return self.plans[row] if 0 <= row < len(self.plans) else None

    # ---- the saw and the shop's leftovers --------------------------------------
    def _apply_saw(self) -> None:
        values = {"first_cut": self.first_cut.currentData(),
                  "cut_stages": self.stages.currentData(),
                  "trim_edges": self.trim_edges.currentData()}
        kerf, trim = parse_length(self.kerf.text()), \
            parse_length(self.trim.text())
        if kerf is not None:
            values["kerf"] = kerf
        if trim is not None:
            values["trim"] = trim
        current = self.session.settings()
        changed = {k: v for k, v in values.items()
                   if getattr(current, k) != v}
        if changed:
            self.session.save_settings(**changed)
        self.start()

    def _load_leftovers(self) -> None:
        plan = self.current_plan()
        rows = self.leftovers.get(plan.id, ()) if plan else ()
        self.leftover_table.setRowCount(0)
        for s in rows:
            self._add_leftover(fmt_length(s.length), fmt_length(s.width),
                               str(s.qty or 1))

    def _add_leftover(self, *texts) -> None:
        r = self.leftover_table.rowCount()
        self.leftover_table.insertRow(r)
        for c, t in enumerate(texts or ("", "", "1")):
            self.leftover_table.setItem(r, c, QTableWidgetItem(t))

    def _read_leftovers(self) -> None:
        plan = self.current_plan()
        if plan is None:
            return
        rows = []
        for r in range(self.leftover_table.rowCount()):
            def text(c, r=r):
                item = self.leftover_table.item(r, c)
                return item.text() if item else ""
            a, b = parse_length(text(0)), parse_length(text(1))
            q = parse_number(text(2)) or 1
            if a and b:
                rows.append(Stock(max(a, b), min(a, b), qty=int(q),
                                  leftover=True))
        self.leftovers = {**self.leftovers, plan.id: tuple(rows)}
        self.start()

    # ---- fixing a part on the diagram (D-014 §2) -------------------------------
    def _part_menu(self, key: str, pos) -> None:
        plan = self.current_plan()
        uids = plan.uids.get(key, []) if plan else []
        menu = QMenu(self)
        if self.saved_data is None and uids:
            n = len(uids)
            menu.addAction(tr("Switch grain ({n} pieces)", n=n),
                           lambda: self._act("switch_grain", uids))
            if n > 1:
                menu.addAction(tr("Switch grain — only this piece"),
                               lambda: self._act("switch_grain", uids[-1:]))
            menu.addAction(tr("Allow or forbid rotation"),
                           lambda: self._act("toggle_rotation", uids))
            menu.addAction(tr("Part settings (oversize, grain…)"),
                           lambda: self._act("settings", uids))
            menu.addAction(tr("Leave out of this layout"),
                           lambda: self._leave_out(uids))
            menu.addSeparator()
        menu.addAction(tr("Show in model"),
                       lambda: self.session.show_in_model(uids))
        menu.exec(pos)

    def _act(self, action: str, uids: list[str]) -> None:
        if not self.session.options.get("warned_redo"):
            box = QMessageBox(QMessageBox.Icon.Information,
                              self.windowTitle(),
                              tr("The part changes in the model, and the "
                                 "whole layout is redone for the same "
                                 "parts."),
                              QMessageBox.StandardButton.Ok
                              | QMessageBox.StandardButton.Cancel, self)
            dont = QCheckBox(tr("Don't show again"))
            box.setCheckBox(dont)
            if box.exec() != QMessageBox.StandardButton.Ok:
                return
            if dont.isChecked():
                self.session.options["warned_redo"] = True
                self.session.save_options(dict(self.session.options))
        if self.session.part_action(action, uids):
            self.start()

    def _leave_out(self, uids) -> None:
        self.left_out = frozenset(self.left_out | set(uids))
        self.start()

    # ---- saved layouts (D-012) ------------------------------------------------
    def save_layout(self, name: str | None = None) -> None:
        if not self.plans or self.saved_data is not None:
            return
        if name is None:
            name, ok = QInputDialog.getText(self, tr("Save layout"),
                                            tr("Layout name"),
                                            text=self.session.model)
            if not ok:
                return
        name = (name or "").strip()
        if not name:
            return
        if name in self.session.layouts() and QMessageBox.question(
                self, tr("Save layout"),
                tr("Replace the layout “{name}”?", name=name)
        ) != QMessageBox.StandardButton.Yes:
            return
        self.session.save_layout(name, self.session.snapshot(
            self.plans, self.leftovers, self.left_out, self.bands))
        self.status.setText(tr("Saved in the model as “{name}”.", name=name))

    def _fill_open_menu(self) -> None:
        menu = self._open_menu
        menu.clear()
        layouts = self.session.layouts()
        if not layouts:
            act = menu.addAction(tr("No layout saved in this model yet"))
            act.setEnabled(False)
            return
        for name in sorted(layouts, key=str.lower):
            menu.addAction(name, lambda n=name: self.open_saved(n))
        menu.addSeparator()
        sub = menu.addMenu(tr("Delete a saved layout"))
        for name in sorted(layouts, key=str.lower):
            sub.addAction(name, lambda n=name: self.session.save_layout(
                n, None))
        if self.saved_data is not None:
            menu.addSeparator()
            menu.addAction(tr("Back to a fresh layout"), self.start)

    def open_saved(self, name: str) -> None:
        """Draw a saved plan as it was: the packer does not run."""
        data = self.session.layouts().get(name)
        if data is None:
            return
        self._generation += 1                # drop a layout in progress
        self.saved_name, self.saved_data = name, data
        self.scope = list(data.get("uids", ()))
        self.plans = []
        self.boards = saved_boards(data)
        self.bands = saved_bands(data)
        self.leftovers = saved_leftovers(data)
        self.left_out = frozenset(data.get("left_out", ()))
        self._fill_boards()
        c: Changes = self.session.changes(data)
        text = tr("Saved layout “{name}” ({date}).", name=name,
                  date=data.get("created", ""))
        if c.any:
            parts = self.session.names(list(c.resized) + list(c.gone))
            text += " " + tr("Since then: {resized} part(s) changed size, "
                             "{gone} gone ({parts}).",
                             resized=len(c.resized), gone=len(c.gone),
                             parts=", ".join(parts[:6])
                             + (" …" if len(parts) > 6 else ""))
            self.redo_button.show()
        else:
            text += " " + tr("The model has not changed since.")
            self.redo_button.hide()
        self.status.setText(text)

    def redo_saved(self) -> None:
        """The saved plan's parts as they are now, laid out again."""
        self.start()

    # ---- output -----------------------------------------------------------------
    def _pages(self):
        return build(self.boards, model=self.session.model,
                     date=self.session.date, options=self.options(),
                     fmt=self.canvas.fmt, bands=self.bands)

    def _remember_options(self) -> None:
        o = self.options()
        self.session.options.update(page=o.page, text=o.text,
                                    group_identical=o.group_identical,
                                    totals_page=o.totals_page,
                                    cut_marks=o.cut_marks)
        self.session.save_options(dict(self.session.options))

    def export_pdf(self, path: str | None = None) -> None:
        if not self.boards:
            return
        if path is None:
            from ..export.rows import safe_stem
            path, _ = QFileDialog.getSaveFileName(
                self, tr("Cutting plan as PDF"),
                _join(self.session.suggested_folder,
                      safe_stem(f"{self.session.model} plan") + ".pdf"),
                tr("PDF (*.pdf)"))
            if not path:
                return
        self._remember_options()
        write_pdf(path, self._pages(), self.options().page)
        import os
        self.session.folder_used(os.path.dirname(path))
        self.status.setText(tr("Wrote {path}", path=path))

    def export_svg(self, folder: str | None = None) -> None:
        if not self.boards:
            return
        if folder is None:
            folder = QFileDialog.getExistingDirectory(
                self, tr("Folder for the SVG pages"),
                self.session.suggested_folder)
            if not folder:
                return
        from pathlib import Path

        from ..export.rows import safe_stem
        from ..export.svg import page_svg
        self._remember_options()
        pages = self._pages()
        stem = safe_stem(f"{self.session.model} plan")
        for page in pages:
            (Path(folder) / f"{stem}_{page.number:02d}.svg").write_text(
                page_svg(page, self.options().page), encoding="utf-8")
        self.session.folder_used(folder)
        self.status.setText(tr("Wrote {n} SVG page(s) to {folder}",
                               n=len(pages), folder=folder))

    def closeEvent(self, event) -> None:
        self._generation += 1
        self.wait(5000)
        super().closeEvent(event)


def _why(reason: str) -> str:
    return {"solid": tr("solid wood: listed only, for now"),
            "no material": tr("no material"),
            "no size": tr("no sheet size — set it in Materials")
            }.get(reason, reason)


def _join(folder: str, name: str) -> str:
    import os
    return os.path.join(folder, name) if folder else name

