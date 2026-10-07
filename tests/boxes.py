# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Ronaldo Alves and CutList contributors.
"""Painted boxes for the model tests: a board as a woodworker models it —
six faces, each painted on its own."""
from __future__ import annotations

import numpy as np

from cutlist.model.geometry import FaceIn

#: Side → (axis index, sign) in the box's own frame (x = length,
#: y = width, z = thickness for a board lying flat).
_SIDES = {"L+": (0, 1), "L-": (0, -1), "W+": (1, 1), "W-": (1, -1),
          "T+": (2, 1), "T-": (2, -1)}


def box(lx, ly, lz, paint=None, default="MDF", at=(0, 0, 0), rot=None):
    """Six faces of an ``lx × ly × lz`` box (metres). ``paint`` maps a side
    (``"T+"``, ``"W-"``…, in the box's x/y/z) to a material; the others
    get ``default``. ``rot`` is an optional 3×3 rotation applied about the
    origin before moving to ``at``."""
    paint = paint or {}
    size = np.array([lx, ly, lz], dtype=float)
    r = np.eye(3) if rot is None else np.asarray(rot, dtype=float)
    faces = []
    for side, (axis, sign) in _SIDES.items():
        u, v = [i for i in range(3) if i != axis]
        corners = []
        for a, b in ((0, 0), (1, 0), (1, 1), (0, 1)):
            p = np.zeros(3)
            p[axis] = size[axis] if sign > 0 else 0.0
            p[u] = size[u] * a
            p[v] = size[v] * b
            corners.append(p)
        # Wind the loop so its normal points outwards.
        n = np.cross(corners[1] - corners[0], corners[2] - corners[0])
        if n[axis] * sign < 0:
            corners.reverse()
        loop = tuple(tuple(r @ c + np.asarray(at, dtype=float))
                     for c in corners)
        faces.append(FaceIn(loop, paint.get(side, default)))
    return tuple(faces)


def rot_z(degrees):
    a = np.radians(degrees)
    return [[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]]
