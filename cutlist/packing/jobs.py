# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Ronaldo Alves and CutList contributors.
"""From a cut list to what the packer needs, one board at a time.

- **Letters** (D-016): A–Z, then AA, AB… like spreadsheet columns, one per
  cut-list line, across the whole job — one letter is one part on every
  board, in the list, on the diagrams and in the 3D highlight.
- **Grain and rotation**: a piece's length runs along its grain. A part
  whose grain runs across its width is given turned; it may turn on the
  sheet only when it has no grain, or the user said it may (and never
  when the user said it may not).
- **The saw**: the model's settings, overridden by the board's own kerf
  and trim (D-014).
"""
from __future__ import annotations

from dataclasses import dataclass

from ..model.grouping import CutList, Section
from ..model.materials import Library
from ..model.parts import Part
from ..model.settings import Settings
from .base import Piece, SawSettings, Stock


def letter(n: int) -> str:
    """0 → A, 25 → Z, 26 → AA, 27 → AB… (spreadsheet columns)."""
    out = ""
    n += 1
    while n:
        n, r = divmod(n - 1, 26)
        out = chr(65 + r) + out
    return out


def letters(cut_list: CutList) -> dict[int, str]:
    """``id(line)`` → its letter, in cut-list order."""
    return {id(line): letter(i) for i, line in enumerate(cut_list.lines())}


def grain_of(part: Part, library: Library) -> str:
    """"length", "width" or "none": the part's own, else its board's."""
    if part.grain is not None:
        return part.grain
    spec = library.get(part.core)
    return "length" if spec is not None and spec.grain else "none"


@dataclass(frozen=True)
class Job:
    """One board's packing: its pieces, its sheets, its saw."""

    material: str | None
    thickness: float
    pieces: tuple[Piece, ...]
    stocks: tuple[Stock, ...]
    settings: SawSettings


def board_job(section: Section, parts: dict[str, Part], library: Library,
              settings: Settings, names: dict[int, str],
              leftovers: tuple[Stock, ...] = ()) -> Job:
    """``parts`` by uid; ``names`` from :func:`letters`. ``stocks`` is
    empty when the board has no sheet size yet: the caller asks for one
    (ask once, never guess — D-013)."""
    pieces = []
    for line in section.lines:
        part = parts[line.uids[0]]          # a line is uniform (grouping key)
        grain = grain_of(part, library)
        length, width = line.cut_length, line.cut_width   # oversize in
        if grain == "width":
            length, width = width, length
        rotate = grain == "none" if part.can_rotate is None \
            else part.can_rotate
        pieces.append(Piece(names[id(line)], length, width, line.qty, rotate))
    spec = library.get(section.material)
    kerf = settings.kerf if spec is None or spec.kerf is None else spec.kerf
    trim = settings.trim if spec is None or spec.trim is None else spec.trim
    stocks = tuple(Stock(s.length, s.width,
                         key=f"{round(s.length * 1000)}x"
                             f"{round(s.width * 1000)}")
                   for s in (spec.stocks if spec is not None else ())
                   if s.fits(section.thickness))
    return Job(
        material=section.material, thickness=section.thickness,
        pieces=tuple(pieces), stocks=tuple(leftovers) + stocks,
        settings=SawSettings(kerf=kerf, trim=trim,
                             trim_edges=settings.trim_edges,
                             first_cut=settings.first_cut,
                             stages=settings.cut_stages))
