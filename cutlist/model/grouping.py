# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Ronaldo Alves and CutList contributors.
"""Parts into a cut list: sections by board and thickness, lines by size.

Parts merge by what was **measured**, whatever they are built as (D-006
§4): the same board, thickness, length and width — within the size
tolerance — and the same coverings and bands, are one line with a
quantity. Bands and coverings are part of the key because a supplier
treats a side panel banded on one edge and one banded on two as two
different pieces.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .parts import Excluded, Flag, Part

DEFAULT_TOLERANCE = 0.001       # 1 mm


def _natural(text: str) -> tuple:
    """"Shelf 2" before "Shelf 10"."""
    return tuple(int(t) if t.isdigit() else t.lower()
                 for t in re.split(r"(\d+)", text))


def quantize(value: float, tolerance: float) -> float:
    """``value`` rounded to the tolerance (17.98 mm → 18 mm at 1 mm)."""
    if tolerance <= 0:
        return value
    return round(value / tolerance) * tolerance


@dataclass
class CutListLine:
    core: str | None
    length: float
    width: float
    thickness: float
    face1: str | None
    face2: str | None
    edges: tuple
    names: list[str] = field(default_factory=list)
    uids: list[str] = field(default_factory=list)
    flags: set[Flag] = field(default_factory=set)
    components: int = 0
    groups: int = 0

    @property
    def qty(self) -> int:
        return len(self.uids)

    @property
    def area(self) -> float:
        return self.length * self.width * self.qty

    def display_names(self) -> list[str]:
        """Distinct names, naturally sorted."""
        return sorted(set(self.names), key=_natural)


@dataclass
class Section:
    """All the lines of one board at one thickness."""

    material: str | None
    thickness: float
    lines: list[CutListLine] = field(default_factory=list)

    @property
    def qty(self) -> int:
        return sum(ln.qty for ln in self.lines)

    @property
    def area(self) -> float:
        return sum(ln.area for ln in self.lines)


@dataclass
class CutList:
    sections: list[Section] = field(default_factory=list)
    excluded: list[Part] = field(default_factory=list)
    #: Parts that are in the list but need a look (they carry flags).
    flagged: list[Part] = field(default_factory=list)
    #: Material name → how many parts show it without a role.
    unassigned: dict[str, int] = field(default_factory=dict)

    @property
    def qty(self) -> int:
        return sum(s.qty for s in self.sections)

    def lines(self):
        for s in self.sections:
            yield from s.lines


def build(parts: list[Part], tolerance: float = DEFAULT_TOLERANCE,
          *, by_name: bool = False) -> CutList:
    """``by_name`` keeps parts with different names on different lines,
    even when they are the same board at the same size."""
    out = CutList()
    sections: dict = {}
    lines: dict = {}
    for p in parts:
        if p.excluded is not None:
            out.excluded.append(p)
            continue
        for name in p.unassigned:
            out.unassigned[name] = out.unassigned.get(name, 0) + 1
        if p.flags:
            out.flagged.append(p)
        t = quantize(p.thickness, tolerance)
        section = sections.get((p.core, t))
        if section is None:
            section = sections[(p.core, t)] = Section(p.core, t)
        key = (p.core, t, quantize(p.length, tolerance),
               quantize(p.width, tolerance), p.face1, p.face2, p.edges,
               p.grain, p.can_rotate, p.name if by_name else None)
        line = lines.get(key)
        if line is None:
            line = lines[key] = CutListLine(p.core, key[2], key[3], t,
                                            p.face1, p.face2, p.edges)
            section.lines.append(line)
        line.names.append(p.name)
        line.uids.append(p.uid)
        line.flags |= p.flags
        if p.is_component:
            line.components += 1
        else:
            line.groups += 1
    for section in sections.values():
        section.lines.sort(key=lambda ln: (-ln.length, -ln.width,
                                           _natural(ln.display_names()[0])))
    out.sections = sorted(
        sections.values(),
        key=lambda s: (s.material is None, _natural(s.material or ""),
                       s.thickness))
    out.excluded.sort(key=lambda p: (p.excluded, _natural(p.name)))
    out.flagged.sort(key=lambda p: _natural(p.name))
    return out


__all__ = ["CutList", "CutListLine", "DEFAULT_TOLERANCE", "Excluded",
           "Section", "build", "quantize"]
