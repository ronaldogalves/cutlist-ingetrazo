# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Ronaldo Alves and CutList contributors.
"""Measuring a part: size along its own axes, faces sorted onto sides."""
from __future__ import annotations

import pytest

from cutlist.model.geometry import FaceIn, measure
from tests.boxes import box, rot_z

MM = 0.001


def test_board_lying_flat():
    m = measure(list(box(0.7, 0.4, 0.018)))
    assert m.size == pytest.approx((0.7, 0.4, 0.018))
    assert m.is_rectangular and m.solids == 1
    assert set(m.sides) == {"T+", "T-", "W+", "W-", "L+", "L-"}


def test_board_standing_on_edge_is_still_l_w_t():
    # A side panel: 18 mm along x, 600 deep along y, 2300 tall along z.
    m = measure(list(box(0.018, 0.6, 2.3)))
    assert m.size == pytest.approx((2.3, 0.6, 0.018))


def test_board_at_an_angle_measures_on_its_own_axes():
    m = measure(list(box(0.8, 0.3, 0.015, rot=rot_z(30))))
    assert m.size == pytest.approx((0.8, 0.3, 0.015), abs=1e-9)
    assert m.is_rectangular


def test_paint_lands_on_the_right_side():
    m = measure(list(box(0.7, 0.4, 0.018, paint={"T+": "Formica"})))
    assert m.sides["T+"] == {"Formica": pytest.approx(0.7 * 0.4)}
    assert "Formica" not in m.sides["T-"]


def test_a_cut_out_makes_it_not_rectangular():
    faces = list(box(0.7, 0.4, 0.018))
    top = faces[4]                      # T+
    hole = ((0.1, 0.1, 0.018), (0.2, 0.1, 0.018),
            (0.2, 0.2, 0.018), (0.1, 0.2, 0.018))
    faces[4] = FaceIn(top.loop, top.material, holes=(hole,))
    assert not measure(faces).is_rectangular


def test_two_boards_in_one_group_are_two_solids():
    faces = list(box(0.7, 0.4, 0.018)) + list(box(0.7, 0.4, 0.018,
                                                  at=(0, 0, 0.5)))
    assert measure(faces).solids == 2


def test_a_board_with_a_through_cut_out_is_one_solid():
    # Regression (model D, oven mask): a 600 × 400 × 15 board with a
    # 200 × 100 through opening. The opening's four walls touch the board
    # only along the holes in its two faces.
    from tests.boxes import box as _box
    faces = list(_box(0.6, 0.4, 0.015))
    ring = [(0.2, 0.15), (0.4, 0.15), (0.4, 0.25), (0.2, 0.25)]
    for i in (4, 5):                                # T+ and T-
        z = 0.015 if i == 4 else 0.0
        faces[i] = FaceIn(faces[i].loop, faces[i].material,
                          holes=(tuple((x, y, z) for x, y in ring),))
    for (x0, y0), (x1, y1) in zip(ring, ring[1:] + ring[:1], strict=True):
        faces.append(FaceIn(((x0, y0, 0.0), (x1, y1, 0.0),
                             (x1, y1, 0.015), (x0, y0, 0.015)), "MDF"))
    m = measure(faces)
    assert m.solids == 1
    assert not m.is_rectangular


def test_no_faces():
    assert measure([]).size == (0.0, 0.0, 0.0)
