# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Ronaldo Alves and CutList contributors.
"""Part labels on sticker sheets (D-018), as plan shapes.

One label per piece, laid out on a sheet of stickers for an ordinary
printer — the common Pimaco sheets and their Avery twins, or a custom
grid. The same shapes go to the PDF (QPainter) as the cutting plan.

Sizes in millimetres; text is not measured (no Qt here), so it is sized
to fit on the safe side.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..i18n import tr
from .plan import CHAR, PAGES, Page, Shape, _mm


@dataclass(frozen=True)
class LabelSheet:
    """A sheet of stickers: ``cols`` × ``rows`` labels of ``w`` × ``h``,
    the first one ``left``/``top`` from the page's corner, ``dx``/``dy``
    from one label's corner to the next."""

    name: str
    page: str                   # A4 or Letter
    cols: int
    rows: int
    w: float
    h: float
    left: float
    top: float
    dx: float
    dy: float

    @property
    def per_page(self) -> int:
        return self.cols * self.rows


#: The common sheets, from their makers' published measurements.
SHEETS = (
    LabelSheet("Pimaco 6180 / Avery 5160 (30, Letter)", "Letter",
               3, 10, 66.68, 25.4, 4.76, 12.7, 69.85, 25.4),
    LabelSheet("Pimaco 6181 / Avery 5161 (20, Letter)", "Letter",
               2, 10, 101.6, 25.4, 3.97, 12.7, 104.78, 25.4),
    LabelSheet("Pimaco 6183 / Avery 5163 (10, Letter)", "Letter",
               2, 5, 101.6, 50.8, 3.97, 12.7, 104.78, 50.8),
    LabelSheet("Pimaco A4360 / Avery L7160 (21, A4)", "A4",
               3, 7, 63.5, 38.1, 7.2, 15.15, 66.04, 38.1),
    LabelSheet("Pimaco A4363 / Avery L7163 (14, A4)", "A4",
               2, 7, 99.1, 38.1, 4.65, 15.15, 101.6, 38.1),
    LabelSheet("Pimaco A4364 / Avery L7165 (8, A4)", "A4",
               2, 4, 99.1, 67.7, 4.65, 13.1, 101.6, 67.7),
)


@dataclass(frozen=True)
class Label:
    """One piece's label."""

    letter: str
    name: str
    length: float               # finished, metres
    width: float
    material: str
    thickness: float
    #: Banded edges, as in the cut list: length1, length2, width1, width2.
    bands: tuple[bool, bool, bool, bool] = (False, False, False, False)
    grain: str = "none"         # length, width, none
    cut: tuple[float, float] | None = None   # when it differs
    info: str = ""              # model · client · room…
    index: int = 1              # "3 of 4"
    count: int = 1
    sheet: int | None = None    # from the diagrams


@dataclass(frozen=True)
class Options:
    sheet: LabelSheet = SHEETS[0]
    start: int = 1              # the first free label on the first sheet
    frames: bool = False        # outline each label (custom sheets, tests)


def _fit(text: str, size: float, width: float) -> float:
    """A text size at most ``size`` that keeps ``text`` within ``width``."""
    need = len(text) * size * CHAR
    return size if need <= width or not text else max(1.6, size * width / need)


def label_shapes(label: Label, x: float, y: float, w: float, h: float,
                 fmt=_mm) -> list[Shape]:
    """One label, drawn into its sticker (x, y, w, h)."""
    pad = min(2.0, h * 0.08)
    x0, y0, w0, h0 = x + pad, y + pad, w - 2 * pad, h - 2 * pad
    out: list[Shape] = []
    # Left: the letter, large, and the part's sketch under it.
    col = min(w0 * 0.3, h0 * 0.95)
    letter = min(h0 * 0.42, col * 0.75 / max(1, len(label.letter)) / CHAR)
    out.append(Shape("text", x0, y0, col, letter * 1.15, style="label_letter",
                     text=label.letter, size=letter, align="center"))
    out += _sketch(label, x0, y0 + letter * 1.2, col, h0 - letter * 1.25)
    # Right: the words, as many lines as fit.
    tx, tw = x0 + col + 1.5, w0 - col - 1.5
    size = min(3.4, h0 / 6.2)
    size_line = f"{fmt(label.length)} × {fmt(label.width)}"
    if label.cut:
        size_line += "  " + tr("(cut {l} × {w})", l=fmt(label.cut[0]),
                               w=fmt(label.cut[1]))
    lines = [(label.name, "label_name", size * 1.15),
             (size_line, "label_size", size * 1.1),
             (f"{label.material} · {fmt(label.thickness)} mm", "label_text",
              size)]
    if label.info:
        lines.append((label.info, "label_text", size * 0.9))
    tail = tr("{i} of {n}", i=label.index, n=label.count)
    if label.sheet is not None:
        tail += "  ·  " + tr("sheet {n}", n=label.sheet)
    lines.append((tail, "label_text", size * 0.9))
    ty = y0
    for text, style, z in lines:
        z = _fit(text, z, tw)
        if ty + z * 1.25 > y0 + h0 + 0.01:
            break                           # a small sticker: what fits
        out.append(Shape("text", tx, ty, tw, z * 1.25, style=style,
                         text=text, size=z))
        ty += z * 1.3
    return out


def _sketch(label: Label, x: float, y: float, w: float, h: float):
    """The part in small, length across: banded edges thick, the grain as
    an arrow (D-018 §3)."""
    if w <= 2 or h <= 2:
        return []
    ratio = label.width / label.length if label.length else 1.0
    sw = w * 0.9
    sh = max(2.0, min(h * 0.9, sw * ratio))
    sw = min(sw, sh / ratio if ratio else sw)
    sx, sy = x + (w - sw) / 2, y + (h - sh) / 2
    out = [Shape("rect", sx, sy, sw, sh, style="label_part")]
    l1, l2, w1, w2 = label.bands
    # Looking at face 1: length1 the far (top) edge, length2 the near
    # (bottom) one, width1 the left end, width2 the right end (D-007).
    for banded, line in ((l1, (sx, sy, sw, 0)), (l2, (sx, sy + sh, sw, 0)),
                         (w1, (sx, sy, 0, sh)), (w2, (sx + sw, sy, 0, sh))):
        if banded:
            out.append(Shape("line", *line, style="label_band"))
    if label.grain == "length":
        out.append(Shape("line", sx + sw * 0.2, sy + sh / 2, sw * 0.6, 0,
                         style="grain"))
    elif label.grain == "width":
        out.append(Shape("line", sx + sw / 2, sy + sh * 0.2, 0, sh * 0.6,
                         style="grain"))
    return out


@dataclass
class LabelPages:
    pages: list[Page] = field(default_factory=list)
    size: str = "A4"


def build(labels: list[Label], options: Options | None = None,
          fmt=_mm) -> LabelPages:
    """Pages of stickers; the first ``start - 1`` stickers left blank."""
    o = options or Options()
    s = o.sheet
    out = LabelPages(size=s.page if s.page in PAGES else "A4")
    slot = max(0, min(o.start - 1, s.per_page - 1))
    page = None
    for label in labels:
        if page is None or slot >= s.per_page:
            page = Page()
            out.pages.append(page)
            slot = 0 if out.pages[:-1] else slot
        r, c = divmod(slot, s.cols)
        x, y = s.left + c * s.dx, s.top + r * s.dy
        if o.frames:
            page.shapes.append(Shape("rect", x, y, s.w, s.h,
                                     style="label_frame"))
        page.shapes += label_shapes(label, x, y, s.w, s.h, fmt)
        slot += 1
    for i, p in enumerate(out.pages, 1):
        p.number, p.total = i, len(out.pages)
    return out
