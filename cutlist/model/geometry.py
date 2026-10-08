# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Ronaldo Alves and CutList contributors.
"""Measure a part as a woodworker does: length × width × thickness along
its own axes, and which of its six sides each face lies on.

The six sides (D-007) are the two **faces** (perpendicular to the
thickness, ``"T+"``/``"T-"``) and the four **edges**: ``"W+"``/``"W-"``
run along the length, ``"L+"``/``"L-"`` along the width. Knowing the
side of every painted face is what lets a painted model become a bill of
materials: laminate on a face, a band on an edge.

The frame is chosen like IngeTrazo's ``core.parts.part_size``: the
model's axes, unless the part's own principal axes give a box much
smaller (a board lying at an angle), so the two agree on sizes.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

#: A face counts as lying on a side when its normal is within ~2.5° of it.
_SIDE_COS = 0.999
#: How much smaller the part's own box must be to beat the model's axes
#: (the same constant as IngeTrazo's ``core.parts``).
_OWN_AXES_GAIN = 0.8
#: Main faces must cover this share of L × W to count as a plain board.
_RECT_SHARE = 0.98
#: Vertices closer than this (metres) are one vertex when counting solids.
_WELD = 1e-6

SIDES = ("T+", "T-", "W+", "W-", "L+", "L-")


@dataclass(frozen=True)
class FaceIn:
    """One face as the host hands it in: world positions (metres), holes,
    and the material it is drawn with (``None`` when unpainted)."""

    loop: tuple
    material: str | None = None
    holes: tuple = ()


@dataclass
class Measured:
    """What :func:`measure` found."""

    length: float
    width: float
    thickness: float
    #: Unit vectors of the part's length, width and thickness axes.
    axes: np.ndarray = field(repr=False)
    #: ``side → {material: area}``; ``None`` is the key for unpainted faces.
    sides: dict = field(default_factory=dict)
    #: Area of faces that lie on no side (chamfers, curves, angled cuts).
    oblique_area: float = 0.0
    #: Separate pieces of geometry (several boards merged into one group?).
    solids: int = 1

    @property
    def size(self) -> tuple[float, float, float]:
        return (self.length, self.width, self.thickness)

    @property
    def is_rectangular(self) -> bool:
        """A plain board: nothing oblique, and both main faces whole (no
        cut-outs or notches)."""
        if self.oblique_area > 1e-9 or self.length <= 0 or self.width <= 0:
            return False
        full = self.length * self.width
        return all(sum(self.sides.get(s, {}).values()) >= _RECT_SHARE * full
                   for s in ("T+", "T-"))


def _newell(loop: np.ndarray) -> np.ndarray:
    """Area-weighted normal of a planar polygon (its length is 2 × area)."""
    nxt = np.roll(loop, -1, axis=0)
    return np.array([
        np.sum((loop[:, 1] - nxt[:, 1]) * (loop[:, 2] + nxt[:, 2])),
        np.sum((loop[:, 2] - nxt[:, 2]) * (loop[:, 0] + nxt[:, 0])),
        np.sum((loop[:, 0] - nxt[:, 0]) * (loop[:, 1] + nxt[:, 1])),
    ])


def _frame(points: np.ndarray) -> np.ndarray:
    """Rows = the three axes to measure along (model axes or own axes)."""
    def volume(axes):
        proj = points @ axes.T
        return float(np.prod(proj.max(axis=0) - proj.min(axis=0)))

    best = np.eye(3)
    if len(points) >= 4:
        centred = points - points.mean(axis=0)
        _w, vecs = np.linalg.eigh(centred.T @ centred)
        own = vecs.T
        if volume(own) < _OWN_AXES_GAIN * volume(best):
            best = own
    return best


def _canonical(axis: np.ndarray) -> np.ndarray:
    """Point an axis the same way every time: its largest component
    positive, so ``+`` sides do not flip between runs or copies."""
    return axis if axis[np.argmax(np.abs(axis))] > 0 else -axis


def _count_solids(loops: list[np.ndarray]) -> int:
    """Faces sharing a vertex belong to one solid; count the solids.

    Each entry holds ALL of a face's vertices, holes included: the walls
    of a cut-out touch the face only along the hole's outline, so leaving
    holes out split one board with a cut-out into two "solids" (model D's
    oven mask, 2026-10-08)."""
    parent = list(range(len(loops)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    owner: dict = {}
    for i, loop in enumerate(loops):
        for key in map(tuple, np.round(loop / _WELD).astype(np.int64)):
            j = owner.setdefault(key, i)
            ri, rj = find(i), find(j)
            if ri != rj:
                parent[ri] = rj
    return len({find(i) for i in range(len(loops))})


def measure(faces: list[FaceIn]) -> Measured:
    """Size, side by side materials, and solid count of one part."""
    loops = [np.asarray(f.loop, dtype=np.float64) for f in faces
             if len(f.loop) >= 3]
    if not loops:
        return Measured(0.0, 0.0, 0.0, np.eye(3))
    points = np.concatenate(loops)
    frame = _frame(points)
    proj = points @ frame.T
    extent = proj.max(axis=0) - proj.min(axis=0)
    order = np.argsort(-extent, kind="stable")          # L, W, T
    axes = np.array([_canonical(frame[i]) for i in order])
    length, width, thickness = (float(extent[i]) for i in order)

    sides: dict = {}
    oblique = 0.0
    for f in faces:
        if len(f.loop) < 3:
            continue
        n = _newell(np.asarray(f.loop, dtype=np.float64))
        area = 0.5 * float(np.linalg.norm(n))
        for hole in f.holes:
            if len(hole) >= 3:
                area -= 0.5 * float(np.linalg.norm(
                    _newell(np.asarray(hole, dtype=np.float64))))
        if area <= 0:
            continue
        unit = n / np.linalg.norm(n)
        dots = axes @ unit
        k = int(np.argmax(np.abs(dots)))
        if abs(dots[k]) < _SIDE_COS:
            oblique += area
            continue
        side = "LWT"[k] + ("+" if dots[k] > 0 else "-")
        bucket = sides.setdefault(side, {})
        bucket[f.material] = bucket.get(f.material, 0.0) + area
    return Measured(length, width, thickness, axes, sides, oblique,
                    _count_solids([
                        np.concatenate([np.asarray(f.loop, dtype=np.float64)]
                                       + [np.asarray(h, dtype=np.float64)
                                          for h in f.holes if len(h)])
                        for f in faces if len(f.loop) >= 3]))
