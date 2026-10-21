# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Ronaldo Alves and CutList contributors.
"""The printed cutting plan as plain shapes (D-016).

One description, three readers: the diagram window and the PDF draw it
with QPainter, :mod:`.svg` writes it as SVG. Pages are in millimetres,
y downwards. Text is not measured (no Qt here): widths are estimated, on
the safe side, so a size is shown on a part only when it surely fits.

What a page carries — what cutting plans in shops look like (Ronaldo):

- every sheet starts a page: the whole board with its cuts, each part's
  letter and size (the letter alone when small), leftovers faded with
  their size, then the parts on that sheet in a table, continued on the
  next page when long;
- identical sheets once, marked "×3" (or each one, by choice);
- "Page 3 of 12", the model, the board and the date on every page —
  printed pages get scattered in the shop;
- an optional totals page first; parts that fit no sheet are always
  said, on the board's first page too.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from ..i18n import tr
from ..packing.base import Layout, Sheet

PAGES = {"A4": (210.0, 297.0), "Letter": (215.9, 279.4)}
#: Text heights in mm: Large reads for everyone; Compact saves pages.
TEXT = {"large": 4.2, "compact": 3.0}
CHAR = 0.56                     # a character's width, in text heights


#: How each style looks, for every reader (screen, PDF, SVG): fill and
#: stroke colours, stroke width in mm, bold text. Parts are white — the
#: plan is printed, and white is what the saw makes; the sheet behind is
#: the kerf's colour, leftovers faded (D-013 §6).
STYLES = {
    "sheet": {"fill": "#d9d2c3", "stroke": "#3a3a3a", "width": 0.35},
    "leftover": {"fill": "#efebe3", "stroke": "#b8b0a2", "width": 0.15},
    "part": {"fill": "#ffffff", "stroke": "#1e1e1e", "width": 0.3},
    "cut0": {"stroke": "#8a8a8a", "width": 0.15},
    "cut1": {"stroke": "#4d4d4d", "width": 0.2},
    "cut2": {"stroke": "#4d4d4d", "width": 0.2},
    "cut3": {"stroke": "#4d4d4d", "width": 0.2},
    "cut4": {"stroke": "#4d4d4d", "width": 0.2},
    "rule": {"stroke": "#555555", "width": 0.3},
    "grid": {"stroke": "#bdbdbd", "width": 0.15},
    "grain": {"stroke": "#4d4d4d", "width": 0.3},
    "title": {"color": "#000000", "bold": True},
    "heading": {"color": "#000000", "bold": True},
    "meta": {"color": "#555555"},
    "footer": {"color": "#555555"},
    "warning": {"color": "#b00020", "bold": True},
    "th": {"color": "#333333", "bold": True},
    "td": {"color": "#000000"},
    "td_key": {"color": "#000000", "bold": True},
    "part_text": {"color": "#000000", "bold": True},
    "part_letter": {"color": "#000000", "bold": True},
    "leftover_text": {"color": "#7a7364"},
    "mark": {"color": "#333333"},
}


@dataclass(frozen=True)
class Shape:
    """``kind``: rect, line or text. ``style`` names what it is (part,
    leftover, sheet, trim, cut1…, grid, title…), so each reader colours it
    its own way; ``ref`` points back (a part's key, a cut's index) for the
    window's mouse."""

    kind: str
    x: float
    y: float
    w: float = 0.0
    h: float = 0.0
    style: str = ""
    text: str = ""
    size: float = 0.0
    align: str = "left"          # left, center, right
    ref: str = ""


@dataclass
class Page:
    shapes: list[Shape] = field(default_factory=list)
    number: int = 0
    total: int = 0


@dataclass(frozen=True)
class PartInfo:
    """What the table says about a part, by its letter."""

    name: str
    length: float               # as cut (what the saw makes)
    width: float
    finished: tuple[float, float] | None = None   # when oversize differs


@dataclass(frozen=True)
class Board:
    """One board's layout and what the plan needs around it."""

    material: str
    thickness: float
    layout: Layout
    parts: dict[str, PartInfo]
    grain: bool = False


@dataclass(frozen=True)
class Options:
    page: str = "A4"
    text: str = "large"
    group_identical: bool = True
    totals_page: bool = True
    cut_marks: bool = False
    margin: float = 12.0


def _mm(metres: float) -> str:
    return f"{round(metres * 1000)}"


def fits(text: str, size: float, w: float, h: float) -> bool:
    return len(text) * size * CHAR <= w - 1.0 and size <= h - 1.0


# ---------------------------------------------------------------------------
# One sheet, drawn into a box — shared by the pages and the window
# ---------------------------------------------------------------------------

def sheet_shapes(sheet: Sheet, x: float, y: float, w: float, h: float, *,
                 size: float, fmt=_mm, grain: bool = False,
                 cut_marks: bool = False) -> tuple[list[Shape], float]:
    """The sheet scaled into the box (x, y, w, h), keeping its proportions;
    returns its shapes and the height it took. Sheet x runs right, sheet y
    up (the saw's corner bottom left)."""
    sl, sw = sheet.stock.length, sheet.stock.width
    scale = min(w / sl, h / sw)
    top = y
    out: list[Shape] = []

    def box(rx, ry, rdx, rdy):
        return (x + rx * scale, top + (sw - ry - rdy) * scale,
                rdx * scale, rdy * scale)

    out.append(Shape("rect", *box(0, 0, sl, sw), style="sheet"))
    last_mark = -1e9
    for i, lo in enumerate(sheet.leftovers):
        bx, by, bw, bh = box(lo.x, lo.y, lo.dx, lo.dy)
        out.append(Shape("rect", bx, by, bw, bh, style="leftover",
                         ref=f"leftover:{i}"))
        label = f"{fmt(lo.dx)} × {fmt(lo.dy)}"
        small = size * 0.7
        if fits(label, small, bw, bh):
            out.append(Shape("text", bx, by, bw, bh, style="leftover_text",
                             text=label, size=small, align="center"))
    for i, c in enumerate(sheet.cuts):
        x0, y0, _w, _h = box(c.x0, c.y0, 0, 0)
        x1, y1, _w, _h = box(c.x1, c.y1, 0, 0)
        out.append(Shape("line", x0, y0, x1 - x0, y1 - y0,
                         style=f"cut{c.stage}", ref=f"cut:{i}"))
        if cut_marks and c.stage == 1 and abs(y0 - last_mark) > size * 0.9:
            last_mark = y0
            mark = fmt(c.fence)
            ty = y0 - size * 0.5
            out.append(Shape("text", x - len(mark) * size * CHAR * 0.75 - 1,
                             ty, len(mark) * size * CHAR * 0.75, size,
                             style="mark", text=mark, size=size * 0.75,
                             align="right"))
    for p in sheet.placements:
        bx, by, bw, bh = box(p.x, p.y, p.dx, p.dy)
        out.append(Shape("rect", bx, by, bw, bh, style="part", ref=p.key))
        full = f"{p.key}  {fmt(p.dx)} × {fmt(p.dy)}"
        letter_size = min(size * 1.6, max(bh * 0.6, size * 0.6))
        # The size when it fits, at the text size or a little smaller.
        shown = next((z for z in (size, size * 0.75)
                      if fits(full, z, bw, bh * 0.95)), None)
        if shown:
            out.append(Shape("text", bx, by, bw, bh, style="part_text",
                             text=full, size=shown, align="center",
                             ref=p.key))
        else:
            out.append(Shape("text", bx, by, bw, bh, style="part_letter",
                             text=p.key, size=min(letter_size, bw * 0.8),
                             align="center", ref=p.key))
    if grain:
        out.append(Shape("line", x + sl * scale * 0.4, top + sw * scale + 4,
                         sl * scale * 0.2, 0, style="grain"))
    return out, sw * scale + (8 if grain else 0)


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

def groups(sheets) -> list[tuple[Sheet, int]]:
    """Identical sheets together, ``(sheet, how many)``, in first order."""
    seen: dict = {}
    order = []
    for s in sheets:
        key = (s.stock.length, s.stock.width,
               tuple(sorted((p.key, round(p.x, 5), round(p.y, 5),
                             round(p.dx, 5), round(p.dy, 5))
                            for p in s.placements)))
        if key not in seen:
            seen[key] = [s, 0]
            order.append(key)
        seen[key][1] += 1
    return [(seen[k][0], seen[k][1]) for k in order]


def build(boards: list[Board], *, model: str, date: str,
          options: Options | None = None, fmt=_mm) -> list[Page]:
    o = options or Options()
    pw, ph = PAGES.get(o.page, PAGES["A4"])
    t = TEXT.get(o.text, TEXT["large"])
    m = o.margin
    width = pw - 2 * m
    pages: list[Page] = []

    def new_page(title: str) -> tuple[Page, float]:
        page = Page()
        pages.append(page)
        page.shapes.append(Shape("text", m, m, width, t * 1.4, style="title",
                                 text=title, size=t * 1.25))
        page.shapes.append(Shape("text", m, m, width, t * 1.4, style="meta",
                                 text=date, size=t * 0.85, align="right"))
        page.shapes.append(Shape("line", m, m + t * 1.9, width, 0,
                                 style="rule"))
        return page, m + t * 2.6

    if o.totals_page:
        page, y = new_page(tr("{model} — cutting plan", model=model))
        y = _totals(page, boards, m, y, width, t, fmt)

    for board in boards:
        name = f"{board.material} · {fmt(board.thickness)} mm"
        grouped = groups(board.layout.sheets) if o.group_identical else \
            [(s, 1) for s in board.layout.sheets]
        sheet_no = 0
        for gi, (sheet, count) in enumerate(grouped):
            sheet_no += 1
            label = tr("Sheet {n} of {total}", n=sheet_no,
                       total=len(grouped))
            if count > 1:
                label += "  " + tr("×{n} — cut {n} identical sheets", n=count)
            page, y = new_page(f"{model} — {name}")
            page.shapes.append(Shape(
                "text", m, y, width, t * 1.3, style="heading",
                text=f"{label}   ·   {fmt(sheet.stock.length)} × "
                     f"{fmt(sheet.stock.width)}   ·   "
                     + tr("{p:.0%} used", p=sheet.efficiency),
                size=t * 1.05))
            y += t * 1.9
            if gi == 0 and board.layout.unplaced:
                text = tr("Parts that fit no sheet: {parts}", parts=", ".join(
                    f"{k} ×{q}" for k, q in board.layout.unplaced))
                page.shapes.append(Shape("text", m, y, width, t * 1.3,
                                         style="warning", text=text, size=t))
                y += t * 1.8
            draw_w = width - (8 * t * CHAR if o.cut_marks else 0)
            shapes, used = sheet_shapes(
                sheet, m + (width - draw_w), y, draw_w, (ph - 2 * m) * 0.5,
                size=t, fmt=fmt, grain=board.grain, cut_marks=o.cut_marks)
            page.shapes.extend(shapes)
            y += used + t * 1.5
            y = _table(page, sheet, count, board, y, m, width, ph, t, fmt,
                       lambda n=name: new_page(f"{model} — {n}"))
    total = len(pages)
    for i, page in enumerate(pages, 1):
        page.number, page.total = i, total
        page.shapes.append(Shape("text", m, ph - m + t * 0.2, width, t,
                                 style="footer", size=t * 0.85,
                                 align="center",
                                 text=tr("Page {n} of {total}", n=i,
                                         total=total)))
    return pages


def _table(page, sheet, count, board, y, m, width, ph, t, fmt,
           new_page) -> float:
    """The parts on this sheet: letter, name, size as cut, how many."""
    qty = Counter(p.key for p in sheet.placements)
    keys = sorted(qty, key=lambda k: (len(k), k))
    oversize = any(board.parts.get(k, PartInfo("", 0, 0)).finished
                   for k in keys)
    cols = [(tr("Part"), 0.09, "center"), (tr("Name"), 0.44 if oversize
                                           else 0.56, "left"),
            (tr("Length"), 0.13, "right"), (tr("Width"), 0.13, "right")]
    if oversize:
        cols.append((tr("Finished"), 0.12, "right"))
    cols.append((tr("Qty"), 0.09, "right"))
    row = t * 1.75

    def header(page, y):
        x = m
        for title, share, align in cols:
            page.shapes.append(Shape("text", x + 1, y, width * share - 2,
                                     row, style="th", text=title,
                                     size=t * 0.9, align=align))
            x += width * share
        page.shapes.append(Shape("line", m, y + row, width, 0, style="grid"))
        return y + row

    y = header(page, y)
    for k in keys:
        if y + row > ph - m - t * 1.5:
            page, y = new_page()
            y = header(page, y)
        info = board.parts.get(k, PartInfo(k, 0.0, 0.0))
        cells = [k, info.name, fmt(info.length), fmt(info.width)]
        if oversize:
            cells.append(f"{fmt(info.finished[0])} × {fmt(info.finished[1])}"
                         if info.finished else "")
        # Per sheet; "2 ×3" when the sheet is cut three times.
        cells.append(str(qty[k]) if count == 1 else f"{qty[k]} ×{count}")
        x = m
        for text, (_title, share, align) in zip(cells, cols, strict=True):
            page.shapes.append(Shape(
                "text", x + 1, y, width * share - 2, row,
                style="td_key" if x == m else "td", text=text,
                size=t, align=align, ref=k))
            x += width * share
        page.shapes.append(Shape("line", m, y + row, width, 0, style="grid"))
        y += row
    return y


def _totals(page, boards, m, y, width, t, fmt) -> float:
    row = t * 1.8
    cols = [(tr("Board"), 0.42, "left"), (tr("Sheets"), 0.14, "right"),
            (tr("Parts"), 0.12, "right"), (tr("Used"), 0.14, "right"),
            (tr("Cuts"), 0.18, "right")]
    x = m
    for title, share, align in cols:
        page.shapes.append(Shape("text", x + 1, y, width * share - 2, row,
                                 style="th", text=title, size=t * 0.9,
                                 align=align))
        x += width * share
    page.shapes.append(Shape("line", m, y + row, width, 0, style="grid"))
    y += row
    for b in boards:
        lay = b.layout
        sizes = Counter((s.stock.length, s.stock.width) for s in lay.sheets)
        sheets = ", ".join(f"{n}× {fmt(a)}×{fmt(c)}"
                           for (a, c), n in sizes.items()) or "0"
        cells = [f"{b.material} · {fmt(b.thickness)} mm", sheets,
                 str(sum(len(s.placements) for s in lay.sheets)),
                 f"{lay.efficiency:.0%}", str(lay.cut_count)]
        x = m
        for text, (_t, share, align) in zip(cells, cols, strict=True):
            page.shapes.append(Shape("text", x + 1, y, width * share - 2,
                                     row, style="td", text=text, size=t,
                                     align=align))
            x += width * share
        page.shapes.append(Shape("line", m, y + row, width, 0, style="grid"))
        y += row
        if lay.unplaced:
            page.shapes.append(Shape(
                "text", m, y, width, row, style="warning", size=t,
                text=tr("Parts that fit no sheet: {parts}", parts=", ".join(
                    f"{k} ×{q}" for k, q in lay.unplaced))))
            y += row
    return y
