# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Ronaldo Alves and CutList contributors.
"""Scenes for host tests: painted boards as IngeTrazo groups."""
from __future__ import annotations


def board(lx, ly, lz, at=(0, 0, 0), paint=None, default="MDF Branco",
          name=None, layer=None):
    """A painted box as an IngeTrazo group (classic group: world coords)."""
    from core.group import Group
    from core.mesh import Mesh
    from PySide6.QtGui import QVector3D as V
    x0, y0, z0 = at
    x1, y1, z1 = x0 + lx, y0 + ly, z0 + lz
    p = [V(x0, y0, z0), V(x1, y0, z0), V(x1, y1, z0), V(x0, y1, z0),
         V(x0, y0, z1), V(x1, y0, z1), V(x1, y1, z1), V(x0, y1, z1)]
    sides = {"T-": (0, 3, 2, 1), "T+": (4, 5, 6, 7), "W-": (0, 1, 5, 4),
             "L+": (1, 2, 6, 5), "W+": (2, 3, 7, 6), "L-": (3, 0, 4, 7)}
    mesh = Mesh()
    paint = paint or {}
    for loop in sides.values():
        mesh.add_face([p[i] for i in loop])
    for f in mesh.faces:
        n = f.normal()
        side = ("L" if abs(n.x()) > 0.5 else "W" if abs(n.y()) > 0.5
                else "T") + ("+" if n.x() + n.y() + n.z() > 0 else "-")
        mat = paint.get(side, default)
        f.attrs = {"mat": mat, "color": (0.5, 0.5, 0.5)}
    g = Group(mesh, name)
    g.layer = layer
    return g
