# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Ronaldo Alves and CutList contributors.
"""The cutting diagrams of a job, between the cut list and the window.

Pure: the window asks, the host stores. What lives here:

- **Plans**: one per board (material + thickness), for exactly the parts
  the window covers — the same parts again when the layout is redone
  after a fix, so the selection is never rebuilt (D-012, D-014 §2).
- **Leftovers from the shop**, per board, used first (D-013 §7), and
  parts left out of this layout only — not out of the cut list.
- **Saving**: a snapshot of the parts as they were (their sizes) beside
  the layout, so a saved plan is drawn as it was and says what changed
  in the model since (D-012 §3).
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace

from ..model.grouping import build
from ..model.materials import BoardKind, Library
from ..model.parts import Part
from ..model.settings import Settings
from ..packing.base import Layout, Stock
from ..packing.jobs import Job, board_job, grain_of, letters
from .plan import Board, PartInfo

#: Sizes closer than this are "the same" when a saved plan is checked.
SAME = 0.0005


def board_id(material: str | None, thickness: float) -> str:
    """A board as a stable string: material and thickness to 0.1 mm."""
    return f"{material or ''}|{round(thickness * 10000)}"


@dataclass
class BoardPlan:
    material: str | None
    thickness: float
    job: Job
    #: letter → the part uids on that line.
    uids: dict[str, list[str]]
    parts: dict[str, PartInfo]
    grain: bool = False
    layout: Layout | None = None

    @property
    def id(self) -> str:
        return board_id(self.material, self.thickness)

    def board(self) -> Board:
        return Board(self.material or "", self.thickness,
                     self.layout or Layout(), self.parts, grain=self.grain)


@dataclass
class Prepared:
    plans: list[BoardPlan] = field(default_factory=list)
    #: Boards with no sheet size yet: material names, to ask once (D-013).
    missing_sizes: list[str] = field(default_factory=list)
    #: Boards not laid out (solid wood, no material…), with why.
    skipped: list[tuple[str, str]] = field(default_factory=list)


def prepare(parts: list[Part], library: Library, settings: Settings, *,
            tolerance: float | None = None, by_name: bool = False,
            leftovers: dict[str, tuple[Stock, ...]] | None = None,
            left_out: frozenset[str] = frozenset()) -> Prepared:
    """``parts``: the parts this layout covers. ``left_out``: uids left
    out of this layout only. Letters come from the cut list of these
    parts, so they match the panel's when the same parts are listed."""
    leftovers = leftovers or {}
    cl = build([p for p in parts if p.uid not in left_out],
               settings.tolerance if tolerance is None else tolerance,
               by_name=by_name)
    by_uid = {p.uid: p for p in parts}
    names = letters(cl)
    out = Prepared()
    for section in cl.sections:
        spec = library.get(section.material)
        if section.material is None:
            out.skipped.append(("", "no material"))
            continue
        if spec is not None and spec.kind is BoardKind.SOLID:
            out.skipped.append((section.material, "solid"))
            continue
        bid = board_id(section.material, section.thickness)
        job = board_job(section, by_uid, library, settings, names,
                        leftovers=leftovers.get(bid, ()))
        if not [s for s in job.stocks if not s.leftover]:
            if section.material not in out.missing_sizes:
                out.missing_sizes.append(section.material)
        info, uids = {}, {}
        for line in section.lines:
            key = names[id(line)]
            finished = (line.length, line.width) \
                if (line.extra_length or line.extra_width) else None
            info[key] = PartInfo(" / ".join(line.display_names()),
                                 line.cut_length, line.cut_width, finished)
            uids[key] = list(line.uids)
        grain = any(grain_of(by_uid[u[0]], library) != "none"
                    for u in uids.values())
        out.plans.append(BoardPlan(section.material, section.thickness, job,
                                   uids, info, grain=grain))
    return out


def pack_all(plans: list[BoardPlan], packer, progress=None) -> None:
    """Lay out every board (off the main thread is fine: pure)."""
    for i, plan in enumerate(plans):
        if progress is not None:
            progress(i, len(plans))
        plan.layout = packer.pack(list(plan.job.pieces),
                                  list(plan.job.stocks), plan.job.settings)


# ---------------------------------------------------------------------------
# Saved plans (D-012)
# ---------------------------------------------------------------------------

def snapshot(plans: list[BoardPlan], parts: list[Part], *,
             created: str, leftovers: dict | None = None,
             left_out=()) -> dict:
    """JSON-safe: what the plan was made from and what it is."""
    sizes = {p.uid: [p.length, p.width, p.thickness, p.extra_length,
                     p.extra_width] for p in parts}
    return {
        "schema": 1, "created": created,
        "uids": sorted(sizes), "sizes": sizes,
        "left_out": sorted(left_out),
        "leftovers": {b: [[s.length, s.width, s.qty] for s in stocks]
                      for b, stocks in (leftovers or {}).items()},
        "boards": [{
            "material": p.material, "thickness": p.thickness,
            "grain": p.grain, "uids": p.uids,
            "parts": {k: [i.name, i.length, i.width,
                          list(i.finished) if i.finished else None]
                      for k, i in p.parts.items()},
            "layout": (p.layout or Layout()).to_dict(),
        } for p in plans],
    }


def saved_boards(data: dict) -> list[Board]:
    """A saved plan, drawn as it was (the packer does not run)."""
    out = []
    for b in data.get("boards", ()):
        parts = {k: PartInfo(n, ln, w, tuple(f) if f else None)
                 for k, (n, ln, w, f) in b.get("parts", {}).items()}
        out.append(Board(b.get("material") or "", float(b["thickness"]),
                         Layout.from_dict(b["layout"]), parts,
                         grain=bool(b.get("grain"))))
    return out


def saved_leftovers(data: dict) -> dict[str, tuple[Stock, ...]]:
    return {b: tuple(Stock(ln, w, qty=q, leftover=True) for ln, w, q in rows)
            for b, rows in (data.get("leftovers") or {}).items()}


@dataclass(frozen=True)
class Changes:
    """What changed in the model since a plan was saved."""

    resized: tuple[str, ...] = ()      # uids
    gone: tuple[str, ...] = ()

    @property
    def any(self) -> bool:
        return bool(self.resized or self.gone)


def changes(data: dict, parts: dict[str, Part]) -> Changes:
    """``parts``: the model's parts now, by uid."""
    resized, gone = [], []
    for uid, size in (data.get("sizes") or {}).items():
        p = parts.get(uid)
        if p is None:
            gone.append(uid)
            continue
        now = (p.length, p.width, p.thickness, p.extra_length, p.extra_width)
        if any(abs(a - b) > SAME for a, b in zip(now, size, strict=False)):
            resized.append(uid)
    return Changes(tuple(sorted(resized)), tuple(sorted(gone)))


def with_layouts(prepared: Prepared, layouts: dict[str, Layout]
                 ) -> list[BoardPlan]:
    """Plans with layouts already made (a redo of one board keeps the
    others)."""
    return [replace(p, layout=layouts.get(p.id, p.layout))
            for p in prepared.plans]
