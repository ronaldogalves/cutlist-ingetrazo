# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Ronaldo Alves and CutList contributors.
"""From a painted solid to a part of the cut list (D-006, D-007).

The host hands in a :class:`RawPart` — a name and the part's faces with
the material each is drawn with. :func:`read_part` measures it, finds the
core board, the coverings on its two faces and the bands on its four
edges, decides which face is face 1, and raises flags instead of
guessing silently.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from .geometry import FaceIn, Measured, measure
from .materials import Library, Role
from .text import tidy

#: Thinner than this (metres) a part is a surface, not a board — the same
#: limit as IngeTrazo's ``core.parts.SURFACE_BELOW``.
SURFACE_BELOW = 0.0005

#: The four edges, named looking at face 1 (D-007 §2). See ``_EDGE_SIDES``.
EDGES = ("length1", "length2", "width1", "width2")

#: Which side each edge is, by which side face 1 is on. Looking at face 1
#: with the length running left to right: length1 is the far edge, length2
#: the near one, width1 the left end, width2 the right end. Seen from the
#: other face the part is mirrored, so the two ends swap.
_EDGE_SIDES = {
    "T+": ("W+", "W-", "L-", "L+"),
    "T-": ("W+", "W-", "L+", "L-"),
}


class Flag(StrEnum):
    NOT_RECTANGULAR = "not_rectangular"     # cut-outs, angles: bounding box used
    SEVERAL_SOLIDS = "several_solids"       # boards merged into one group?
    NO_MATERIAL = "no_material"             # no face says what board it is
    UNASSIGNED = "unassigned_material"      # a finish whose role is not set


class Excluded(StrEnum):
    BY_USER = "by_user"
    IGNORED_MATERIAL = "ignored_material"
    SURFACE = "surface"


@dataclass(frozen=True)
class RawPart:
    """One part as the host found it."""

    uid: str
    name: str
    faces: tuple[FaceIn, ...]
    tag: str | None = None
    is_component: bool = False
    #: The name is IngeTrazo's automatic one ("Group 12"), not the user's.
    auto_named: bool = False


@dataclass(frozen=True)
class PartOverride:
    """What the user set on one part (stored in ``group.ext``)."""

    flip_face1: bool = False
    exclude: bool = False
    note: str = ""
    #: ``None`` = from the material; else "length", "width" or "none".
    grain: str | None = None
    can_rotate: bool | None = None
    #: The part's own custom field values, as ``((name, value), …)``.
    fields: tuple[tuple[str, str], ...] = ()

    @property
    def field_values(self) -> dict[str, str]:
        return dict(self.fields)

    def with_fields(self, values: dict) -> PartOverride:
        """These field values (empty ones removed), sorted for equality."""
        from dataclasses import replace
        clean = sorted((str(k), str(v)) for k, v in values.items() if v)
        return replace(self, fields=tuple(clean))

    def to_dict(self) -> dict:
        """Only what differs from no override (what ``group.ext`` keeps)."""
        d: dict = {"schema": 1}
        if self.flip_face1:
            d["flip_face1"] = True
        if self.exclude:
            d["exclude"] = True
        if self.note:
            d["note"] = self.note
        if self.grain is not None:
            d["grain"] = self.grain
        if self.can_rotate is not None:
            d["can_rotate"] = self.can_rotate
        if self.fields:
            d["fields"] = dict(self.fields)
        return d

    @property
    def is_empty(self) -> bool:
        return self == PartOverride()

    @classmethod
    def from_dict(cls, d) -> PartOverride:
        if not isinstance(d, dict):
            return cls()
        grain = d.get("grain")
        rot = d.get("can_rotate")
        return cls(flip_face1=bool(d.get("flip_face1", False)),
                   exclude=bool(d.get("exclude", False)),
                   note=str(d.get("note") or ""),
                   grain=grain if grain in GRAINS else None,
                   can_rotate=rot if isinstance(rot, bool) else None
                   ).with_fields(d.get("fields")
                                 if isinstance(d.get("fields"), dict) else {})


#: Grain directions a part can be set to (``None`` = from its material).
GRAINS = ("length", "width", "none")


@dataclass(frozen=True)
class Part:
    uid: str
    name: str
    length: float
    width: float
    thickness: float
    core: str | None
    face1: str | None                   # covering on face 1, None = as the core
    face2: str | None
    edges: tuple[str | None, ...]       # bands, in the order of EDGES
    face1_side: str                     # "T+" or "T-" in the part's frame
    tag: str | None = None
    is_component: bool = False
    auto_named: bool = False
    flags: frozenset[Flag] = frozenset()
    #: Finishes found on the part whose material has no role yet.
    unassigned: frozenset[str] = frozenset()
    excluded: Excluded | None = None
    note: str = ""
    grain: str | None = None
    can_rotate: bool | None = None
    measured: Measured | None = field(default=None, compare=False, repr=False)

    @property
    def size(self) -> tuple[float, float, float]:
        return (self.length, self.width, self.thickness)

    @property
    def banded_edges(self) -> tuple[bool, ...]:
        return tuple(e is not None for e in self.edges)


def _dominant(bucket: dict, accept=lambda m: True):
    best, area = None, 0.0
    for material, a in bucket.items():
        if material is not None and accept(material) and a > area:
            best, area = material, a
    return best


def _merge(*buckets: dict) -> dict:
    out: dict = {}
    for b in buckets:
        for m, a in b.items():
            out[m] = out.get(m, 0.0) + a
    return out


def _find_core(m: Measured, lib: Library) -> str | None:
    """The board: the board-like material on the two faces, else anywhere
    on the part, else the board a covering says it goes on."""
    faces = _merge(m.sides.get("T+", {}), m.sides.get("T-", {}))
    core = _dominant(faces, lib.is_board_like)
    if core is None:
        core = _dominant(_merge(*m.sides.values()), lib.is_board_like)
    if core is None:
        for material in _merge(*m.sides.values()):
            spec = lib.get(material)
            if spec is not None and spec.role is Role.COVERING \
                    and spec.applied_over:
                return spec.applied_over
    return core


def read_part(raw: RawPart, lib: Library,
              override: PartOverride | None = None) -> Part:
    over = override or PartOverride()
    m = measure(list(raw.faces))
    core = _find_core(m, lib)
    unassigned: set[str] = set()

    def slot(side: str) -> str | None:
        """What covers ``side``: a covering or band, or None (as the core)."""
        dom = _dominant(m.sides.get(side, {}))
        if dom is None or dom == core:
            return None
        role = lib.role(dom)
        if role in (Role.COVERING, Role.EDGE_BAND):
            return dom
        if role in (Role.APPEARANCE, Role.IGNORE):
            return None
        unassigned.add(dom)             # a board or a material not set up
        return None

    covers = {s: slot(s) for s in ("T+", "T-", "W+", "W-", "L+", "L-")}

    # Face 1: the face with a covering; else the decorative one (painted
    # unlike the core); else T+. The user can flip it.
    def finish(side):
        return _dominant(m.sides.get(side, {}))
    up, down = covers["T+"], covers["T-"]
    if up and not down:
        face1_side = "T+"
    elif down and not up:
        face1_side = "T-"
    elif finish("T-") not in (None, core) and finish("T+") in (None, core):
        face1_side = "T-"
    else:
        face1_side = "T+"
    if over.flip_face1:
        face1_side = "T-" if face1_side == "T+" else "T+"
    face2_side = "T-" if face1_side == "T+" else "T+"
    edges = tuple(covers[s] for s in _EDGE_SIDES[face1_side])

    flags: set[Flag] = set()
    if not m.is_rectangular:
        flags.add(Flag.NOT_RECTANGULAR)
    if m.solids > 1:
        flags.add(Flag.SEVERAL_SOLIDS)
    if unassigned:
        flags.add(Flag.UNASSIGNED)

    excluded = None
    if over.exclude:
        excluded = Excluded.BY_USER
    elif m.thickness < SURFACE_BELOW:
        excluded = Excluded.SURFACE
    elif core is None and lib.role(
            _dominant(_merge(*m.sides.values()))) is Role.IGNORE:
        excluded = Excluded.IGNORED_MATERIAL
    elif core is not None and lib.role(core) is Role.IGNORE:
        excluded = Excluded.IGNORED_MATERIAL
    if core is None and excluded is None:
        flags.add(Flag.NO_MATERIAL)

    return Part(
        uid=raw.uid, name=tidy(raw.name), length=m.length, width=m.width,
        thickness=m.thickness, core=core,
        face1=covers[face1_side], face2=covers[face2_side], edges=edges,
        face1_side=face1_side, tag=raw.tag, is_component=raw.is_component,
        auto_named=raw.auto_named, flags=frozenset(flags),
        unassigned=frozenset(unassigned), excluded=excluded,
        note=tidy(over.note),
        grain=over.grain, can_rotate=over.can_rotate, measured=m)
