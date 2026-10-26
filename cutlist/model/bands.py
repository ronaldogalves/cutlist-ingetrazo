# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Ronaldo Alves and CutList contributors.
"""How much edge band to buy (D-017).

Per band material: every banded edge of the listed parts — the long edges
count the part's length, the short ones its width, finished size — times
the quantity; plus the band's oversize on each edge (the overhang trimmed
after gluing) and its waste %. Total metres is the number that matters;
rolls only when the band says how long a roll is.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from .materials import Library


@dataclass(frozen=True)
class BandTotal:
    name: str
    width: float                    # metres; 0 when not set
    edges: int                      # banded edges, all parts
    net: float                      # metres of edge
    total: float                    # metres to buy: + oversize, + waste
    roll: float = 0.0               # metres per roll; 0: not sold in rolls
    rolls: int = 0

    @property
    def added(self) -> float:
        return self.total - self.net


def band_totals(lines, library: Library) -> list[BandTotal]:
    """``lines``: cut-list lines (``CutListLine``). Bands in name order."""
    acc: dict[str, list] = {}
    for line in lines:
        for i, band in enumerate(line.edges):
            if not band:
                continue
            edge = line.length if i < 2 else line.width   # length1/2 first
            a = acc.setdefault(band, [0, 0.0])
            a[0] += line.qty
            a[1] += edge * line.qty
    out = []
    for name in sorted(acc, key=str.lower):
        edges, net = acc[name]
        spec = library.get(name)
        oversize = spec.oversize if spec else 0.0
        waste = spec.waste if spec else 0.0
        roll = spec.roll if spec else 0.0
        total = (net + oversize * edges) * (1 + waste)
        out.append(BandTotal(name, spec.width if spec else 0.0, edges, net,
                             total, roll,
                             math.ceil(total / roll - 1e-9) if roll > 0
                             else 0))
    return out
