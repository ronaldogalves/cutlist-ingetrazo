# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Ronaldo Alves and CutList contributors.
"""Laminate drawn *and* painted on the same face (D-019 §5).

A designer may paint a board's face with laminate, or draw a piece of
laminate over it — either way works, both at once means buying it twice.
That is the designer's slip, not ours to fix: both parts are flagged and
neither is dropped. The same holds for a band piece over a banded edge.
"""
from __future__ import annotations

from dataclasses import replace

from .parts import Flag, Kind, Part

#: A piece this close to a board's face lies on it: designers lift the
#: laminate a little off the board so the two do not fight on screen.
NEAR = 0.003
#: …and must overlap it at least this much both ways, not just touch.
OVERLAP = 0.001
#: Parallel within ~2.5°, as the sides of a part are told apart.
_PARALLEL = 0.999


def _lies_on(piece: Part, board: Part, side: str) -> bool:
    """``piece`` lies flat on ``side`` of ``board``, overlapping it."""
    mb, mp = board.measured, piece.measured
    if mb is None or mp is None or mb.low is None or mp.low is None:
        return False
    k = "LWT".index(side[0])
    if abs(float(mp.axes[2] @ mb.axes[k])) < _PARALLEL:
        return False
    q = mp.corners() @ mb.axes.T            # the piece in the board's frame
    lo, hi = q.min(axis=0), q.max(axis=0)
    plane = mb.high[k] if side[1] == "+" else mb.low[k]
    if lo[k] < plane - NEAR or hi[k] > plane + NEAR:
        return False
    return all(min(hi[j], mb.high[j]) - max(lo[j], mb.low[j]) > OVERLAP
               for j in range(3) if j != k)


def mark_double_covers(parts: list[Part]) -> list[Part]:
    """``parts`` again, with :attr:`Flag.DOUBLE_COVER` on each covering or
    band piece lying on a board side painted with a covering or band, and
    on that board."""
    pieces = [p for p in parts if p.kind is not Kind.BOARD
              and p.excluded is None]
    boards = [(p, p.covered_sides()) for p in parts
              if p.kind is Kind.BOARD and p.excluded is None]
    boards = [(b, sides) for b, sides in boards if sides]
    if not pieces or not boards:
        return parts
    hit: set[str] = set()
    for piece in pieces:
        for board, sides in boards:
            if any(_lies_on(piece, board, side) for side in sides):
                hit.update((piece.uid, board.uid))
    if not hit:
        return parts
    return [replace(p, flags=p.flags | {Flag.DOUBLE_COVER})
            if p.uid in hit else p for p in parts]


__all__ = ["NEAR", "OVERLAP", "mark_double_covers"]
