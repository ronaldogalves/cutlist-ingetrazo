# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Ronaldo Alves and CutList contributors.
"""The saw packer: staged guillotine layouts (D-003, D-012, D-015).

How a panel saw or table saw cuts a sheet, and so how this lays it out:

1. **Strips** — the first cuts run the whole (trimmed) sheet, along its
   length or across it (the first-cut direction).
2. **Segments** — each strip is cut into pieces along the strip.
3. **Stacks** — a segment may hold several parts of the same size along
   the strip, cut apart by a third set of cuts.
4. With four stages a part may be shorter than its segment: one more cut.

Everything that is not a part and not sawdust is a **leftover**, kept as
the real rectangle the cuts make (D-013).

The method is the textbook one every packer builds on: parts sorted
several ways, strips filled first-fit or by the best strip among a few
candidates, the best layout kept. Deterministic for a given input and
seed, so tests and saved layouts reproduce. Lengths are worked in whole
hundredths of a millimetre so that "fits exactly" means exactly.
"""
from __future__ import annotations

import random
from dataclasses import dataclass

from .base import Cut, Layout, Piece, Placement, Rect, SawSettings, Sheet, Stock

SCALE = 100_000                         # units per metre: 0.01 mm


def _i(metres: float) -> int:
    return int(round(metres * SCALE))


def _m(units: int) -> float:
    return units / SCALE


@dataclass
class _Type:
    key: str
    length: int
    width: int
    qty: int
    rotate: bool

    def orients(self, transposed: bool) -> list[tuple[int, int]]:
        """``(dx, dy)`` it may take in the packing frame (x along strips)."""
        out = [(self.length, self.width)]
        if self.rotate and self.length != self.width:
            out.append((self.width, self.length))
        return [(dy, dx) for dx, dy in out] if transposed else out

    @property
    def area(self) -> int:
        return self.length * self.width


def _after(size: int, room: int, kerf: int) -> int:
    """Room left once ``size`` is cut off ``room``: the blade takes the
    kerf; a sliver thinner than the blade is sawdust."""
    return max(0, room - size - kerf)


# ---------------------------------------------------------------------------
# Filling: a strip, then a sheet
# ---------------------------------------------------------------------------

def _fill_strip(h, length, counts, order, orients, kerf, stages):
    """Segments along a strip ``h`` high: ``[(s, [(type, dx, dy)…])…]``."""
    room = length
    segments = []
    used = 0
    while room > 0:
        start = None
        for t in order:
            if not counts[t]:
                continue
            best = None
            for dx, dy in orients[t]:
                if dx <= room and dy <= h and (stages > 2 or dy == h):
                    if best is None or dy > best[1] or (dy == best[1]
                                                        and dx < best[0]):
                        best = (dx, dy)
            if best is not None:
                start = (t, *best)
                break
        if start is None:
            break
        t, s, dy = start
        counts[t] -= 1
        stack = [(t, s, dy)]
        used += s * dy
        up = _after(dy, h, kerf)
        while stages >= 3 and up > 0:
            pick = None
            for t2 in order:
                if not counts[t2]:
                    continue
                for dx2, dy2 in orients[t2]:
                    fits = dy2 <= up and (dx2 == s if stages == 3
                                          else dx2 <= s)
                    if fits and (pick is None or dx2 * dy2 > pick[3]):
                        pick = (t2, dx2, dy2, dx2 * dy2)
            if pick is None:
                break
            t2, dx2, dy2, area = pick
            counts[t2] -= 1
            stack.append((t2, dx2, dy2))
            used += area
            up = _after(dy2, up, kerf)
        segments.append((s, stack))
        room = _after(s, room, kerf)
    return segments, used


def _fill_sheet(lx, ly, counts, order, orients, kerf, stages, mode):
    """Strips up a sheet: ``[(h, segments)…]`` and the area used.

    ``mode``: the strip's height comes from the first part that fits,
    standing tall (``tall``) or lying flat (``flat``), or the best-filled
    of a few candidate strips (``best``)."""
    room = ly
    strips = []
    used = 0
    while room > 0:
        heights = []
        for t in order:
            if not counts[t]:
                continue
            fit = [dy for dx, dy in orients[t] if dx <= lx and dy <= room]
            if not fit:
                continue
            if mode == "tall":
                heights = [max(fit)]
                break
            if mode == "flat":
                heights = [min(fit)]
                break
            heights.extend(h for h in fit if h not in heights)
            if len(heights) >= 4:
                break
        if not heights:
            break
        best = None
        for h in heights:
            trial = list(counts)
            segments, area = _fill_strip(h, lx, trial, order, orients, kerf,
                                         stages)
            if not segments:
                continue
            score = (area / (h * lx), area)
            if best is None or score > best[0]:
                best = (score, h, segments, trial, area)
        if best is None:
            break
        _score, h, segments, trial, area = best
        counts[:] = trial
        strips.append((h, segments))
        used += area
        room = _after(h, room, kerf)
    return strips, used


# ---------------------------------------------------------------------------
# From a plan to placements, cuts and leftovers
# ---------------------------------------------------------------------------

def _usable(stock: Stock, settings: SawSettings) -> tuple[int, int, int, int]:
    """``(x, y, length, width)`` of the sheet once trimmed, in units."""
    length, width = _i(stock.length), _i(stock.width)
    if stock.leftover or settings.trim <= 0:
        return 0, 0, length, width
    t = _i(settings.trim)
    if settings.trim_edges == 2:
        return t, t, max(0, length - t), max(0, width - t)
    return t, t, max(0, length - 2 * t), max(0, width - 2 * t)


def _geometry(plan, types, stock, settings, transposed) -> Sheet:
    kerf = _i(settings.kerf)
    ox, oy, ulen, uwid = _usable(stock, settings)
    lx, ly = (uwid, ulen) if transposed else (ulen, uwid)
    places, cuts, rests = [], [], []

    def to_sheet(x, y, dx, dy):
        if transposed:
            x, y, dx, dy = y, x, dy, dx
        return x + ox, y + oy, dx, dy

    def rest(x, y, dx, dy):
        if dx > 0 and dy > 0:
            rests.append(to_sheet(x, y, dx, dy))

    def cut(stage, x0, y0, x1, y1):
        a = to_sheet(x0, y0, 0, 0)
        b = to_sheet(x1, y1, 0, 0)
        cuts.append(Cut(stage, _m(a[0]), _m(a[1]), _m(b[0]), _m(b[1])))

    y = 0
    for h, segments in plan:
        x = 0
        for s, stack in segments:
            yy = y
            for t, dx, dy in stack:
                sx, sy, sdx, sdy = to_sheet(x, yy, dx, dy)
                piece = types[t]
                places.append(Placement(
                    piece.key, _m(sx), _m(sy), _m(sdx), _m(sdy),
                    rotated=sdx != piece.length))
                if dx < s:                          # one more cut (stage 4)
                    cut(4, x + dx, yy, x + dx, yy + dy)
                    rest(x + dx + kerf, yy, s - dx - kerf, dy)
                if yy + dy < y + h:
                    cut(3, x, yy + dy, x + s, yy + dy)
                yy += dy + kerf
            rest(x, yy, s, y + h - yy)
            if x + s < lx:
                cut(2, x + s, y, x + s, y + h)
            x += s + kerf
        rest(x, y, lx - x, h)
        if y + h < ly:
            cut(1, 0, y + h, lx, y + h)
        y += h + kerf
    rest(0, y, lx, ly - y)

    trims = []
    if not stock.leftover and settings.trim > 0:
        length, width = _m(_i(stock.length)), _m(_i(stock.width))
        tx, ty = _m(ox), _m(oy)
        trims = [Cut(0, tx, 0.0, tx, width), Cut(0, 0.0, ty, length, ty)]
        if settings.trim_edges != 2:
            trims += [Cut(0, length - tx, 0.0, length - tx, width),
                      Cut(0, 0.0, width - ty, length, width - ty)]
    leftovers = sorted((Rect(_m(x), _m(y), _m(dx), _m(dy))
                        for x, y, dx, dy in rests),
                       key=lambda r: -r.area)
    return Sheet(stock=stock, placements=tuple(places),
                 cuts=tuple(trims + cuts), leftovers=tuple(leftovers),
                 first_cut="width" if transposed else "length")


# ---------------------------------------------------------------------------
# The packer
# ---------------------------------------------------------------------------

_ORDERS = {
    "longest": lambda t: (-max(t.length, t.width), -min(t.length, t.width)),
    "area": lambda t: (-t.area, -max(t.length, t.width)),
    "length": lambda t: (-t.length, -t.width),
    "width": lambda t: (-t.width, -t.length),
    "perimeter": lambda t: (-(t.length + t.width), -t.area),
}
_MODES = ("best", "tall", "flat")


def _fits(t: _Type, stock: Stock, settings: SawSettings) -> bool:
    _x, _y, length, width = _usable(stock, settings)
    return any(dx <= length and dy <= width for dx, dy in t.orients(False))


class GuillotinePacker:
    name = "guillotine"

    def pack(self, pieces: list[Piece], stocks: list[Stock],
             settings: SawSettings | None = None) -> Layout:
        settings = settings or SawSettings()
        types = [_Type(p.key, _i(p.length), _i(p.width), p.qty, p.rotate)
                 for p in pieces if p.qty > 0]
        # Leftovers from the shop first, as listed; then full sheets.
        stocks = ([s for s in stocks if s.leftover]
                  + [s for s in stocks if not s.leftover])
        fits = [any(_fits(t, s, settings) for s in stocks) for t in types]
        unplaced = [(t.key, t.qty) for t, ok in zip(types, fits, strict=True)
                    if not ok]
        types = [t for t, ok in zip(types, fits, strict=True) if ok]
        if not types or not stocks:
            return Layout(unplaced=tuple(unplaced), settings=settings)

        directions = {"length": (False,), "width": (True,)}.get(
            settings.first_cut, (False, True))
        rng = random.Random(settings.seed)
        best = None
        for transposed in directions:
            for order, mode in self._strategies(types, settings, rng):
                result = self._run(types, stocks, settings, transposed,
                                   order, mode)
                key = self._score(result)
                if best is None or key < best[0]:
                    best = (key, result)
        sheets, left = best[1]
        unplaced += [(types[i].key, n) for i, n in enumerate(left) if n]
        return Layout(sheets=tuple(sheets), unplaced=tuple(unplaced),
                      settings=settings)

    @staticmethod
    def _strategies(types, settings, rng):
        """Orderings × strip rules: the fixed ones, then shuffled variants
        of the best-known order up to ``settings.attempts``."""
        fixed = [(sorted(range(len(types)), key=lambda i, k=k: k(types[i])),
                  mode) for k in _ORDERS.values() for mode in _MODES]
        yield from fixed[:max(settings.attempts, 1)]
        base = fixed[0][0]
        for n in range(len(fixed), settings.attempts):
            order = list(base)
            for _ in range(max(1, len(order) // 4)):
                i = rng.randrange(len(order))
                j = min(len(order) - 1, i + rng.randint(1, 3))
                order[i], order[j] = order[j], order[i]
            yield order, _MODES[n % len(_MODES)]

    @staticmethod
    def _run(types, stocks, settings, transposed, order, mode):
        kerf = _i(settings.kerf)
        stages = max(2, min(4, settings.stages))
        orients = [t.orients(transposed) for t in types]
        counts = [t.qty for t in types]
        left = [s.qty for s in stocks]
        sheets = []
        while any(counts):
            best = None
            for si, stock in enumerate(stocks):
                if left[si] is not None and left[si] <= 0:
                    continue
                if not stock.leftover and best is not None and best[0][0]:
                    break                # a shop leftover took parts: use it
                _x, _y, ulen, uwid = _usable(stock, settings)
                lx, ly = (uwid, ulen) if transposed else (ulen, uwid)
                trial = list(counts)
                plan, used = _fill_sheet(lx, ly, trial, order, orients, kerf,
                                         stages, mode)
                if not used:
                    continue
                done = not any(trial)
                size = _i(stock.length) * _i(stock.width)
                # Full sheets: the best-filled; the last one, the smallest
                # that takes everything left.
                score = (stock.leftover, done, -size if done else 0,
                         used / size)
                if best is None or score > best[0]:
                    best = (score, si, plan, trial)
            if best is None:
                break
            _score, si, plan, trial = best
            counts[:] = trial
            if left[si] is not None:
                left[si] -= 1
            sheets.append(_geometry(plan, types, stocks[si], settings,
                                    transposed))
        return sheets, counts

    @staticmethod
    def _score(result):
        """Fewest parts left out, then fewest sheets (and least stock
        area), then fewest cuts, then waste in the fewest, biggest
        leftovers (D-015). Smaller is better."""
        sheets, left = result
        cuts = sum(1 for s in sheets for c in s.cuts if c.stage > 0)
        stock_area = sum(s.stock.length * s.stock.width for s in sheets
                         if not s.stock.leftover)
        spread = -sum(r.area ** 2 for s in sheets for r in s.leftovers)
        return (sum(left), len(sheets), round(stock_area, 6), cuts, spread)


def pack(pieces, stocks, settings=None) -> Layout:
    """The default packer, for callers that do not choose one."""
    return GuillotinePacker().pack(pieces, stocks, settings)
