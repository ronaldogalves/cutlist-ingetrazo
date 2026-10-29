# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Ronaldo Alves and CutList contributors.
"""The order the saw makes a sheet's cuts (lesson from Sawhorse, IDEAS).

The packer writes a sheet's cuts as it builds the layout: inside a strip
first, the cut that frees the strip last. At the saw it is the other way
round: free a strip, then cut it into pieces, then the pieces into parts.
This reorders them; every cut keeps its fence distance (from the edge of
the piece being cut, D-016 §8).
"""
from __future__ import annotations

from .base import Cut, Sheet


def _split(cuts: list[Cut], stage: int) -> list[tuple[Cut | None, list]]:
    """``(the cut of this stage that ends a chunk, what came before it)``;
    the last chunk has no ending cut (the piece left at the end)."""
    chunks, buffer = [], []
    for c in cuts:
        if c.stage == stage:
            chunks.append((c, buffer))
            buffer = []
        else:
            buffer.append(c)
    if buffer:
        chunks.append((None, buffer))
    return chunks


def sequence(sheet: Sheet) -> list[Cut]:
    """The sheet's cuts in sawing order: trims, then for each strip the
    cut that frees it and its own cuts, depth first."""
    trims = [c for c in sheet.cuts if c.stage == 0]
    out = list(trims)

    def walk(cuts, stage):
        if stage >= 3:              # a stack: parts apart, then trimmed
            out.extend(c for c in cuts if c.stage == 3)
            out.extend(c for c in cuts if c.stage == 4)
            return
        for ending, inner in _split(cuts, stage):
            if ending is not None:
                out.append(ending)
            walk(inner, stage + 1)
    walk([c for c in sheet.cuts if c.stage > 0], 1)
    return out
