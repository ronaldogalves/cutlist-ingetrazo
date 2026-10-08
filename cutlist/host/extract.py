# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Ronaldo Alves and CutList contributors.
"""Find the parts of an IngeTrazo scene (D-006) as plain records.

Walks the selection — or the whole model when nothing is selected — and
returns a :class:`~..model.parts.RawPart` for every **leaf container**: a
group or component instance with faces of its own and no containers
inside. Each face comes with its world positions and the material it is
drawn with (its own paint, else its container's), which is all the model
layer needs. Nothing here changes the document.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import PurePath

import numpy as np

from ..model.geometry import FaceIn
from ..model.parts import RawPart

#: IngeTrazo's automatic container names ("Group 12"): not the user's.
_AUTO_NAME = re.compile(r"^Group \d+$")


@dataclass
class Notice:
    """Something found while walking that is not a part but needs a look."""

    kind: str               # "loose_geometry"
    name: str
    uid: str


@dataclass
class Extraction:
    parts: list[RawPart] = field(default_factory=list)
    notices: list[Notice] = field(default_factory=list)
    #: "selection" or "model": what was walked.
    scope: str = "model"
    #: Every tag a part carries, before the tag filter (for the filter menu).
    tags: set[str] = field(default_factory=set)
    #: Parts left out by the tag filter.
    filtered_out: int = 0
    #: Plain groups left out because only components were asked for.
    not_components: int = 0
    #: uid → the IngeTrazo group of every part found (for its settings).
    groups: dict = field(default_factory=dict)
    #: Every material seen on the parts' faces (for the material library).
    materials: set[str] = field(default_factory=set)
    #: uid → list of world edge segments ``(N, 2, 3)`` for the highlight.
    outlines: dict[str, np.ndarray] = field(default_factory=dict)


def _label(attrs) -> str | None:
    """What a face is painted with, as a person names it: the registry
    name, else the texture's file name, else the colour (as IngeTrazo's
    ``core.parts`` does)."""
    if not attrs:
        return None
    if attrs.get("mat"):
        return str(attrs["mat"])
    tex = attrs.get("texture")
    if tex and tex.get("path"):
        return PurePath(str(tex["path"])).stem
    col = attrs.get("color")
    if col is not None:
        r, g, b = (int(round(c * 255)) for c in list(col)[:3])
        return f"#{r:02x}{g:02x}{b:02x}"
    return None


def _matrix(m) -> np.ndarray | None:
    if m is None:
        return None
    return np.array([[m(r, c) for c in range(4)] for r in range(4)])


def _compose(parent: np.ndarray | None, own) -> np.ndarray | None:
    own = _matrix(own)
    if parent is None:
        return own
    return parent if own is None else parent @ own


def _apply(m: np.ndarray | None, pts: np.ndarray) -> np.ndarray:
    if m is None or len(pts) == 0:
        return pts
    return pts @ m[:3, :3].T + m[:3, 3]


def _positions(vectors) -> np.ndarray:
    return np.array([(v.x(), v.y(), v.z()) for v in vectors],
                    dtype=np.float64).reshape(-1, 3)


def extract(scene, *, use_selection: bool = True,
            excluded_tags=frozenset(), include_groups: bool = True,
            outline_uids=None) -> Extraction:
    """The parts in scope. ``excluded_tags`` leaves out parts by tag;
    ``outline_uids`` (a set, or ``None`` for all) chooses which parts keep
    their edges for the viewport highlight."""
    from core.group import Group
    from core.layers import DEFAULT_LAYER
    from core.materials import has_own_material

    out = Extraction()
    roots = []
    if use_selection:
        roots = [e for e in getattr(scene, "selection", ()) or ()
                 if isinstance(e, Group)]
    if roots:
        out.scope = "selection"
    else:
        roots = list(scene.groups)

    def visible(g) -> bool:
        """Drawn, and not a face-me billboard (the scale figure every new
        document starts with is one: a picture, not a part)."""
        return (scene.entity_visible(g) and not getattr(g, "hidden", False)
                and not getattr(g, "billboard", False))

    def walk(g, world, inherited_paint, inherited_tag):
        if not visible(g):
            return
        world = _compose(world, g.xform)
        paint = g.material or inherited_paint
        tag = g.layer if g.layer and g.layer != DEFAULT_LAYER \
            else inherited_tag
        kids = [c for c in (g.children or []) if visible(c)]
        own = [f for f in g.mesh.faces if not getattr(f, "interior", False)]
        if kids:
            if own:
                out.notices.append(Notice("loose_geometry", g.name, g.uid))
            for c in kids:
                walk(c, world, paint, tag)
            return
        if not own:
            return
        if tag:
            out.tags.add(tag)
        if tag in excluded_tags:
            out.filtered_out += 1
            return
        if not include_groups and not g.is_component():
            out.not_components += 1
            return
        inherited_label = _label(paint)
        faces = []
        for f in own:
            attrs = f.attrs
            material = _label(attrs) if has_own_material(attrs) \
                else (inherited_label or _label(attrs))
            loop = _apply(world, _positions(f.vertices))
            holes = tuple(tuple(map(tuple, _apply(world, _positions(h))))
                          for h in f.holes)
            faces.append(FaceIn(tuple(map(tuple, loop)), material, holes))
            if material is not None:
                out.materials.add(material)
        out.parts.append(RawPart(
            uid=g.uid, name=g.name, faces=tuple(faces), tag=tag,
            is_component=g.is_component(),
            auto_named=bool(_AUTO_NAME.match(g.name or ""))))
        out.groups[g.uid] = g
        if outline_uids is None or g.uid in outline_uids:
            out.outlines[g.uid] = _edges(g, world)

    for g in roots:
        # A selected nested part (picked inside a group) has an owner chain
        # we cannot see from here; it is walked with its own matrix only.
        walk(g, None, None, None)
    return out


def _edges(g, world) -> np.ndarray:
    """The container's visible edges in world coordinates, as segments."""
    segs = []
    for e in getattr(g.mesh, "edges", ()):
        if getattr(e, "hidden", False) or getattr(e, "soft", False):
            continue
        try:
            a, b = e.v0.position, e.v1.position
        except AttributeError:
            continue
        segs.append(((a.x(), a.y(), a.z()), (b.x(), b.y(), b.z())))
    if not segs:
        return np.empty((0, 2, 3))
    arr = np.array(segs, dtype=np.float64)
    flat = _apply(world, arr.reshape(-1, 3))
    return flat.reshape(-1, 2, 3)
