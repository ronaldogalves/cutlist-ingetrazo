# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Ronaldo Alves and CutList contributors.
"""Part labels on sticker sheets (D-018)."""
from __future__ import annotations

import pytest

from cutlist.export.labels import SHEETS, Label, Options, build, label_shapes
from cutlist.export.plan import PAGES


def door(i=1, n=1, **kw):
    return Label("A", "Porta", 0.716, 0.396, "MDF Branco", 0.018,
                 bands=(True, True, True, True), grain="length",
                 info="Cozinha 03 · Família Souza · Cozinha", index=i,
                 count=n, **kw)


def texts(shapes, style=None):
    return [s.text for s in shapes if s.kind == "text"
            and (style is None or s.style == style)]


@pytest.mark.parametrize("sheet", SHEETS, ids=lambda s: s.name)
def test_every_sheet_fits_its_page_and_each_label_its_sticker(sheet):
    pw, ph = PAGES[sheet.page]
    assert sheet.left + (sheet.cols - 1) * sheet.dx + sheet.w <= pw + 0.5
    assert sheet.top + (sheet.rows - 1) * sheet.dy + sheet.h <= ph + 0.5
    labels = [door(i, sheet.per_page + 1) for i in
              range(1, sheet.per_page + 2)]
    out = build(labels, Options(sheet=sheet))
    assert len(out.pages) == 2 and out.size == sheet.page
    for page in out.pages:
        for s in page.shapes:
            assert 0 <= s.x and s.x + s.w <= pw + 0.01
            assert 0 <= s.y and s.y + s.h <= ph + 0.01


def test_start_at_label_n_and_one_label_per_piece():
    sheet = SHEETS[0]                                   # 30 a page
    labels = [door(i, 10) for i in range(1, 11)]
    out = build(labels, Options(sheet=sheet, start=25))
    assert len(out.pages) == 2                          # 6 on the first
    first = out.pages[0].shapes
    assert len(texts(first, "label_letter")) == 6
    top = min(s.y for s in first)
    assert top >= sheet.top + 8 * sheet.dy - 0.01       # row 9: label 25


def test_what_a_label_says():
    shapes = label_shapes(door(3, 4, sheet=2, cut=(0.72, 0.4)), 0, 0,
                          101.6, 50.8)
    words = " ".join(texts(shapes))
    for part in ("A", "Porta", "716 × 396", "cut 720 × 400", "MDF Branco",
                 "18 mm", "Família Souza", "3 of 4", "sheet 2"):
        assert part in words
    assert len([s for s in shapes if s.style == "label_band"]) == 4
    assert len([s for s in shapes if s.style == "grain"]) == 1


def test_a_small_sticker_keeps_the_essentials():
    shapes = label_shapes(door(), 0, 0, 66.68, 25.4)
    assert texts(shapes, "label_letter") == ["A"]
    assert texts(shapes, "label_name") == ["Porta"]
    for s in shapes:
        assert s.x + s.w <= 66.68 + 0.01 and s.y + s.h <= 25.4 + 0.01


def test_the_grain_arrow_points_the_way_it_runs():
    from cutlist.export.plan import Shape, arrow_head
    across = arrow_head(Shape("line", 10, 10, 0, 20, style="grain"))
    assert across[0] == (10, 30)                       # tip at the end
    assert all(abs(y - 28) < 1e-9 for _x, y in across[1:])   # base above
    along = arrow_head(Shape("line", 10, 10, 20, 0, style="grain"))
    assert along[0] == (30, 10)
    assert all(abs(x - 28) < 1e-9 for x, _y in along[1:])
