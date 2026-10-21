# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Ronaldo Alves and CutList contributors.
"""The printed plan as shapes (D-016): a page per sheet, "Page n of N" on
every page, tables that continue, identical sheets grouped, the totals
page optional, parts that fit nowhere always said."""
from __future__ import annotations

from cutlist.export.plan import (
    PAGES,
    Board,
    Options,
    PartInfo,
    build,
    groups,
    sheet_shapes,
)
from cutlist.packing.base import Piece, SawSettings, Stock
from cutlist.packing.guillotine import pack

SHEET = Stock(2.75, 1.84)


def board(pieces, **kw):
    layout = pack(pieces, [SHEET], SawSettings(kerf=0.004))
    parts = {p.key: PartInfo(f"Part {p.key}", p.length, p.width)
             for p in pieces}
    return Board("MDF Branco", 0.015, layout, parts, **kw)


def texts(page, style=None):
    return [s.text for s in page.shapes
            if s.kind == "text" and (style is None or s.style == style)]


def test_every_page_says_which_of_how_many():
    b = board([Piece("A", 1.2, 0.8, qty=7), Piece("B", 0.3, 0.2, qty=9)])
    pages = build([b], model="Cozinha", date="2026-10-21")
    n = len(pages)
    assert n == 1 + len(groups(b.layout.sheets))      # totals + sheets
    for i, page in enumerate(pages, 1):
        assert texts(page, "footer") == [f"Page {i} of {n}"]
        assert "2026-10-21" in texts(page, "meta")
        assert page.number == i and page.total == n


def test_the_totals_page_is_optional():
    b = board([Piece("A", 0.6, 0.4, qty=2)])
    with_totals = build([b], model="M", date="d")
    without = build([b], model="M", date="d",
                    options=Options(totals_page=False))
    assert len(with_totals) == len(without) + 1
    assert not any("cutting plan" in t for t in texts(without[0]))


def test_identical_sheets_are_grouped_or_shown_one_by_one():
    b = board([Piece("A", 1.3, 0.9, qty=12)])    # 4 per sheet, 3 sheets
    assert [n for _s, n in groups(b.layout.sheets)] == [3]
    grouped = build([b], model="M", date="d",
                    options=Options(totals_page=False))
    assert len(grouped) == 1
    assert any("×3" in t for t in texts(grouped[0], "heading"))
    each = build([b], model="M", date="d",
                 options=Options(totals_page=False, group_identical=False))
    assert len(each) == 3


def test_a_long_table_continues_and_a_sheet_starts_a_page():
    pieces = [Piece(f"P{i}", 0.12 + i * 0.001, 0.06, qty=1)
              for i in range(80)]
    b = board(pieces)
    pages = build([b], model="M", date="d",
                  options=Options(totals_page=False))
    assert len(b.layout.sheets) == 1 and len(pages) > 1
    keys = [t for p in pages for t in texts(p, "td_key")]
    assert sorted(keys) == sorted(p.key for p in pieces)
    # Every row lies on its page, above the footer.
    _w, ph = PAGES["A4"]
    for page in pages:
        for s in page.shapes:
            if s.style in ("td", "td_key"):
                assert s.y + s.h <= ph - 12.0


def test_parts_that_fit_no_sheet_are_said():
    b = board([Piece("A", 3.2, 0.5), Piece("B", 0.5, 0.4)])
    pages = build([b], model="M", date="d")
    said = [t for p in pages for t in texts(p, "warning")]
    assert len(said) == 2 and all("A ×1" in t for t in said)


def test_small_parts_show_their_letter_only():
    sheet = pack([Piece("A", 2.0, 1.2), Piece("B", 0.05, 0.03)],
                 [SHEET]).sheets[0]
    shapes, _h = sheet_shapes(sheet, 0, 0, 180, 120, size=4.2)
    by_ref = {s.ref: s for s in shapes if s.kind == "text" and s.ref}
    assert by_ref["A"].style == "part_text" and "×" in by_ref["A"].text
    assert by_ref["B"].style == "part_letter" and by_ref["B"].text == "B"


def test_compact_text_takes_fewer_pages():
    pieces = [Piece(f"P{i}", 0.12 + i * 0.001, 0.06) for i in range(120)]
    b = board(pieces)
    large = build([b], model="M", date="d", options=Options(text="large"))
    compact = build([b], model="M", date="d", options=Options(text="compact"))
    assert len(compact) < len(large)


def test_a_page_as_svg():
    from xml.etree import ElementTree

    from cutlist.export.svg import page_svg
    b = board([Piece("A", 0.6, 0.4, qty=2), Piece("B&C", 0.3, 0.2)])
    page = build([b], model="Família <Souza>", date="d")[1]
    root = ElementTree.fromstring(page_svg(page))
    assert root.get("width") == "210mm"
    words = " ".join(t.text or "" for t in root.iter()
                     if t.tag.endswith("text"))
    assert "Família <Souza>" in words and "B&C" in words
    assert "Page 2 of 2" in words
