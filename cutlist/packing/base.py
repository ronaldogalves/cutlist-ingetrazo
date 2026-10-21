# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Ronaldo Alves and CutList contributors.
"""What goes into a packer and what comes out.

Plain frozen dataclasses with ``to_dict``/``from_dict``: a layout is saved
in the model as it was made and drawn again without packing (D-012).

Lengths are metres. On a sheet, **x runs along its length** — the way the
grain runs — and y across; (0, 0) is the corner where the saw starts.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Protocol

#: First cuts along the sheet's length (strips as long as the sheet), across
#: it (shorter pieces first: easier alone at the saw), or both tried (D-015).
FIRST_CUTS = ("best", "length", "width")


@dataclass(frozen=True)
class Piece:
    """One kind of part: ``qty`` identical pieces under one ``key`` (the
    part's letter). ``length`` runs along the part's grain when it has
    one; ``rotate`` says it may also lie turned 90° on the sheet."""

    key: str
    length: float
    width: float
    qty: int = 1
    rotate: bool = True


@dataclass(frozen=True)
class Stock:
    """A sheet size. ``qty`` None: as many as needed. A ``leftover`` from
    the shop is used before full sheets and is not trimmed (D-013)."""

    length: float
    width: float
    qty: int | None = None
    leftover: bool = False
    key: str = ""


@dataclass(frozen=True)
class SawSettings:
    kerf: float = 0.003
    trim: float = 0.010
    #: 4: every edge trimmed; 2: the two where the saw starts (D-014).
    trim_edges: int = 4
    first_cut: str = "best"
    #: Strips, parts, one more cut on a part (3); 2 is simpler at the saw;
    #: 4 allows one more cut again — tighter, more handling (D-015).
    stages: int = 3
    #: How many orderings are tried: more is slower and rarely worse.
    attempts: int = 24
    seed: int = 1


@dataclass(frozen=True)
class Placement:
    key: str
    x: float
    y: float
    #: Size as it lies on the sheet (``dx`` along x).
    dx: float
    dy: float
    #: Turned 90° from the piece's own length along x.
    rotated: bool = False


@dataclass(frozen=True)
class Rect:
    x: float
    y: float
    dx: float
    dy: float

    @property
    def area(self) -> float:
        return self.dx * self.dy


@dataclass(frozen=True)
class Cut:
    """A saw cut: ``stage`` 0 trims the sheet, 1 the first cuts (strips),
    2 the next… From (x0, y0) to (x1, y1), on the near side of the blade."""

    stage: int
    x0: float
    y0: float
    x1: float
    y1: float

    @property
    def length(self) -> float:
        return abs(self.x1 - self.x0) + abs(self.y1 - self.y0)


@dataclass(frozen=True)
class Sheet:
    stock: Stock
    placements: tuple[Placement, ...] = ()
    cuts: tuple[Cut, ...] = ()
    #: The real pieces the cuts leave over (D-013), largest first.
    leftovers: tuple[Rect, ...] = ()
    #: "length" or "width": which way this sheet's first cuts run.
    first_cut: str = "length"

    @property
    def used_area(self) -> float:
        return sum(p.dx * p.dy for p in self.placements)

    @property
    def efficiency(self) -> float:
        area = self.stock.length * self.stock.width
        return self.used_area / area if area else 0.0


@dataclass(frozen=True)
class Layout:
    sheets: tuple[Sheet, ...] = ()
    #: ``(key, qty)`` that fit no sheet — said, never dropped silently.
    unplaced: tuple[tuple[str, int], ...] = ()
    settings: SawSettings = field(default_factory=SawSettings)

    @property
    def cut_count(self) -> int:
        return sum(1 for s in self.sheets for c in s.cuts if c.stage > 0)

    @property
    def efficiency(self) -> float:
        area = sum(s.stock.length * s.stock.width for s in self.sheets)
        return (sum(s.used_area for s in self.sheets) / area) if area else 0.0

    # ---- (de)serialisation (saved layouts, D-012) --------------------------
    def to_dict(self) -> dict:
        d = asdict(self)
        d["unplaced"] = [list(u) for u in self.unplaced]
        d["schema"] = 1
        return d

    @classmethod
    def from_dict(cls, d: dict) -> Layout:
        def sheet(s: dict) -> Sheet:
            return Sheet(
                stock=Stock(**s["stock"]),
                placements=tuple(Placement(**p) for p in s["placements"]),
                cuts=tuple(Cut(**c) for c in s["cuts"]),
                leftovers=tuple(Rect(**r) for r in s["leftovers"]),
                first_cut=s.get("first_cut", "length"))
        return cls(sheets=tuple(sheet(s) for s in d.get("sheets", ())),
                   unplaced=tuple((str(k), int(q))
                                  for k, q in d.get("unplaced", ())),
                   settings=SawSettings(**d.get("settings", {})))


class Packer(Protocol):
    """Anything that lays pieces out on stock (D-003): a second packer —
    CNC nesting, a native one — plugs in here without touching the UI."""

    name: str

    def pack(self, pieces: list[Piece], stocks: list[Stock],
             settings: SawSettings) -> Layout: ...
