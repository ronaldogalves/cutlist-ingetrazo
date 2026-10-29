# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Ronaldo Alves and CutList contributors.
"""The saw packer (M2). Every layout is checked from its coordinates by an
independent checker — not by the packer's own bookkeeping: inside the
trimmed sheet, no two parts closer than the blade, grain kept, every part
placed or reported, and cuttable with straight cuts across."""
from __future__ import annotations

import json
import random
import time
from collections import Counter

import pytest

from cutlist.packing.base import Layout, Piece, SawSettings, Stock
from cutlist.packing.guillotine import pack

EPS = 1e-7
ROUND = 1e-5                            # the packer works to 0.01 mm
SHEET = Stock(2.75, 1.84)


def usable(stock: Stock, s: SawSettings):
    if stock.leftover or s.trim <= 0:
        return 0.0, 0.0, stock.length, stock.width
    if s.trim_edges == 2:
        return s.trim, s.trim, stock.length, stock.width
    return s.trim, s.trim, stock.length - s.trim, stock.width - s.trim


def apart(a, b, kerf):
    return (a.x + a.dx + kerf <= b.x + EPS or b.x + b.dx + kerf <= a.x + EPS
            or a.y + a.dy + kerf <= b.y + EPS
            or b.y + b.dy + kerf <= a.y + EPS)


def cuttable(rects) -> bool:
    """Straight cuts right across can free every rectangle (guillotine)."""
    if len(rects) <= 1:
        return True
    for lo, size in (("x", "dx"), ("y", "dy")):
        spans = sorted(rects, key=lambda r: getattr(r, lo))
        end = getattr(spans[0], lo) + getattr(spans[0], size)
        for r in spans[1:]:
            start = getattr(r, lo)
            if start >= end - EPS:
                first = [q for q in rects if getattr(q, lo) < start - EPS]
                rest = [q for q in rects if getattr(q, lo) >= start - EPS]
                return cuttable(first) and cuttable(rest)
            end = max(end, start + getattr(r, size))
    return False


def check(layout: Layout, pieces: list[Piece]) -> None:
    s = layout.settings
    by_key = {p.key: p for p in pieces}
    placed = Counter()
    for sheet in layout.sheets:
        x0, y0, x1, y1 = usable(sheet.stock, s)
        things = list(sheet.placements) + list(sheet.leftovers)
        for r in things:
            assert x0 - ROUND <= r.x and r.x + r.dx <= x1 + ROUND, r
            assert y0 - ROUND <= r.y and r.y + r.dy <= y1 + ROUND, r
            assert r.dx > 0 and r.dy > 0
        for i, a in enumerate(things):
            for b in things[i + 1:]:
                assert apart(a, b, s.kerf), (a, b)
        for p in sheet.placements:
            piece = by_key[p.key]
            along = (piece.width, piece.length) if p.rotated else \
                (piece.length, piece.width)
            assert (p.dx, p.dy) == pytest.approx(along, abs=1e-5)   # 0.01 mm
            if not piece.rotate:
                assert not p.rotated or piece.length == piece.width
            placed[p.key] += 1
        assert cuttable(list(sheet.placements))
        assert max((c.stage for c in sheet.cuts), default=0) <= s.stages
    for key, qty in layout.unplaced:
        placed[key] += qty
    assert placed == Counter({p.key: p.qty for p in pieces})


# ---------------------------------------------------------------------------

def test_one_part_the_size_of_the_trimmed_sheet():
    s = SawSettings(kerf=0.004, trim=0.01)
    layout = pack([Piece("A", 2.73, 1.82)], [SHEET], s)
    (sheet,) = layout.sheets
    (p,) = sheet.placements
    assert (p.x, p.y) == pytest.approx((0.01, 0.01))
    assert not sheet.leftovers
    assert [c.stage for c in sheet.cuts] == [0, 0, 0, 0]     # trims only
    check(layout, [Piece("A", 2.73, 1.82)])


def test_a_part_too_big_for_any_sheet_is_reported():
    pieces = [Piece("A", 3.0, 0.5), Piece("B", 0.5, 0.5, qty=2)]
    layout = pack(pieces, [SHEET])
    assert layout.unplaced == (("A", 1),)
    check(layout, pieces)


def test_grain_is_kept():
    # Long and narrow, grain along: never turned, whatever saves a sheet.
    pieces = [Piece("A", 1.5, 0.1, qty=20, rotate=False)]
    layout = pack(pieces, [Stock(2.5, 1.6)])
    assert all(not p.rotated for s in layout.sheets for p in s.placements)
    check(layout, pieces)


def test_a_shop_leftover_goes_first_untrimmed():
    pieces = [Piece("A", 0.6, 0.4, qty=3)]
    left = Stock(1.2, 0.81, qty=1, leftover=True)
    layout = pack(pieces, [SHEET, left], SawSettings(kerf=0.004))
    first = layout.sheets[0]
    assert first.stock.leftover
    assert not [c for c in first.cuts if c.stage == 0]
    assert min(p.x for p in first.placements) == 0
    check(layout, pieces)


def test_two_stages_only_strips_and_parts():
    pieces = [Piece("A", 0.6, 0.3, qty=6), Piece("B", 0.5, 0.3, qty=4),
              Piece("C", 0.4, 0.2, qty=5)]
    layout = pack(pieces, [SHEET], SawSettings(stages=2))
    assert max(c.stage for s in layout.sheets for c in s.cuts) <= 2
    check(layout, pieces)


def test_first_cut_direction():
    pieces = [Piece("A", 0.9, 0.5, qty=6)]
    for way in ("length", "width"):
        layout = pack(pieces, [SHEET], SawSettings(first_cut=way))
        assert {s.first_cut for s in layout.sheets} == {way}
        check(layout, pieces)


def test_same_input_same_layout():
    rng = random.Random(7)
    pieces = [Piece(chr(65 + i), rng.uniform(0.1, 1.2), rng.uniform(0.05, 0.6),
                    qty=rng.randint(1, 4)) for i in range(12)]
    assert pack(pieces, [SHEET]) == pack(pieces, [SHEET])


def test_a_layout_survives_the_trip_through_json():
    pieces = [Piece("A", 0.7, 0.4, qty=5), Piece("B", 0.3, 0.2, qty=7)]
    layout = pack(pieces, [SHEET, Stock(1.0, 0.8, qty=1, leftover=True)])
    again = Layout.from_dict(json.loads(json.dumps(layout.to_dict())))
    assert again == layout


def test_mixed_sizes_end_on_the_smallest_that_takes_the_rest():
    pieces = [Piece("A", 1.3, 0.8, qty=4), Piece("B", 0.4, 0.3, qty=1)]
    half = Stock(1.84, 1.375)
    layout = pack(pieces, [SHEET, half], SawSettings(kerf=0.003, trim=0.0))
    assert len(layout.sheets) == 2
    assert layout.sheets[-1].stock == half
    check(layout, pieces)


@pytest.mark.parametrize("seed", range(150))
def test_random_jobs_are_sound(seed):
    rng = random.Random(seed)
    pieces = []
    for i in range(rng.randint(1, 30)):
        a, b = rng.uniform(0.03, 1.6), rng.uniform(0.03, 0.9)
        pieces.append(Piece(f"P{i}", max(a, b), min(a, b),
                            qty=rng.randint(1, 5), rotate=rng.random() < 0.6))
    stocks = [rng.choice([SHEET, Stock(2.5, 1.6), Stock(2.2, 1.6)])]
    if rng.random() < 0.3:
        stocks.append(Stock(rng.uniform(0.4, 1.4), rng.uniform(0.3, 0.9),
                            qty=rng.randint(1, 2), leftover=True))
    settings = SawSettings(kerf=rng.choice([0.0, 0.003, 0.005]),
                           trim=rng.choice([0.0, 0.01]),
                           trim_edges=rng.choice([2, 4]),
                           first_cut=rng.choice(["best", "length", "width"]),
                           stages=rng.choice([2, 3, 4]), attempts=6,
                           seed=seed)
    check(pack(pieces, stocks, settings), pieces)


def test_two_hundred_parts_in_under_two_seconds():
    rng = random.Random(3)
    pieces = [Piece(f"P{i}", rng.uniform(0.2, 1.2), rng.uniform(0.05, 0.6),
                    qty=rng.randint(1, 4)) for i in range(70)]
    assert sum(p.qty for p in pieces) >= 170
    start = time.perf_counter()
    layout = pack(pieces, [SHEET], SawSettings(kerf=0.005, trim=0.01))
    assert time.perf_counter() - start < 2.0
    check(layout, pieces)


def test_every_cut_knows_its_piece_and_fence():
    """The fence distance is measured from the edge of the piece being cut
    (D-016 §8): the cut lies ``fence`` in from the parent's start edge."""
    pieces = [Piece("A", 0.9, 0.5, qty=3), Piece("B", 0.4, 0.3, qty=5)]
    for way in ("length", "width"):
        layout = pack(pieces, [SHEET], SawSettings(first_cut=way, stages=4))
        for sheet in layout.sheets:
            for c in sheet.cuts:
                p = c.parent
                assert p is not None and c.fence > 0
                if c.across:            # a crosscut: x is constant
                    assert p.x - EPS <= c.x0 <= p.x + p.dx + EPS
                    if c.stage:
                        assert c.x0 - p.x == pytest.approx(c.fence, abs=1e-5)
                else:
                    assert p.y - EPS <= c.y0 <= p.y + p.dy + EPS
                    if c.stage:
                        assert c.y0 - p.y == pytest.approx(c.fence, abs=1e-5)


def _saw(sheet, s):
    """Make the sheet's cuts in sequence order, like a saw: each must run
    right across a piece there is at that moment (the one it says it
    splits); at the end every part is alone in its piece."""
    from cutlist.packing.sequence import sequence
    x0, y0, x1, y1 = usable(sheet.stock, s)
    pieces = [(x0, y0, x1, y1)]
    cuts = [c for c in sequence(sheet) if c.stage > 0]
    assert len(cuts) == len([c for c in sheet.cuts if c.stage > 0])
    for c in cuts:
        p = c.parent
        match = [q for q in pieces
                 if abs(q[0] - p.x) < 1e-6 and abs(q[1] - p.y) < 1e-6
                 and abs(q[2] - (p.x + p.dx)) < 1e-6
                 and abs(q[3] - (p.y + p.dy)) < 1e-6]
        assert match, (c, pieces)
        q = match[0]
        pieces.remove(q)
        if c.across:                    # x constant: split along x
            assert abs(c.y0 - q[1]) < 1e-6 and abs(c.y1 - q[3]) < 1e-6
            pieces += [(q[0], q[1], c.x0, q[3]),
                       (min(c.x0 + s.kerf, q[2]), q[1], q[2], q[3])]
        else:
            assert abs(c.x0 - q[0]) < 1e-6 and abs(c.x1 - q[2]) < 1e-6
            pieces += [(q[0], q[1], q[2], c.y0),
                       (q[0], min(c.y0 + s.kerf, q[3]), q[2], q[3])]
    for pl in sheet.placements:
        holders = [q for q in pieces
                   if q[0] - 1e-6 <= pl.x and pl.x + pl.dx <= q[2] + 1e-6
                   and q[1] - 1e-6 <= pl.y and pl.y + pl.dy <= q[3] + 1e-6]
        assert len(holders) == 1
        inside = [o for o in sheet.placements
                  if holders[0][0] - 1e-6 <= o.x
                  and o.x + o.dx <= holders[0][2] + 1e-6
                  and holders[0][1] - 1e-6 <= o.y
                  and o.y + o.dy <= holders[0][3] + 1e-6]
        assert inside == [pl]


@pytest.mark.parametrize("seed", range(40))
def test_the_cut_sequence_can_be_sawn(seed):
    rng = random.Random(1000 + seed)
    pieces = [Piece(f"P{i}", rng.uniform(0.1, 1.2), rng.uniform(0.05, 0.6),
                    qty=rng.randint(1, 4), rotate=rng.random() < 0.7)
              for i in range(rng.randint(2, 20))]
    s = SawSettings(kerf=rng.choice([0.0, 0.003, 0.005]),
                    trim=rng.choice([0.0, 0.01]),
                    trim_edges=rng.choice([2, 4]),
                    first_cut=rng.choice(["length", "width"]),
                    stages=rng.choice([2, 3, 4]), attempts=4, seed=seed)
    for sheet in pack(pieces, [SHEET], s).sheets:
        _saw(sheet, s)
