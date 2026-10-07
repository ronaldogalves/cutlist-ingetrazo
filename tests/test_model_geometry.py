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


def test_no_faces():
    assert measure([]).size == (0.0, 0.0, 0.0)
