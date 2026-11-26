# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Ronaldo Alves and CutList contributors.
"""Laminate and edge band drawn as pieces of their own (D-019): boards
stacked and glued, then laminated or banded as one."""
from __future__ import annotations

import numpy as np
import pytest

from cutlist.model.bands import band_totals
from cutlist.model.geometry import FaceIn
from cutlist.model.grouping import build
from cutlist.model.materials import Library, MaterialSpec, Role, SheetSize
from cutlist.model.overlap import mark_double_covers
from cutlist.model.parts import (
    Excluded,
    Flag,
    Kind,
    PartOverride,
    RawPart,
    read_part,
)
from cutlist.model.settings import Settings
from cutlist.packing.jobs import board_job, letters
from tests.boxes import box, rot_z


def library(**extra):
    specs = {
        "Ply": MaterialSpec("Ply"),
        "Formica": MaterialSpec("Formica", role=Role.COVERING,
                                thickness=0.0008),
        "Fita": MaterialSpec("Fita", role=Role.EDGE_BAND, thickness=0.001),
    }
    specs.update(extra)
    return Library(specs)


def plane(origin, u, v, material, holes=()):
    """One flat rectangle: ``origin`` + spans ``u`` and ``v`` (metres)."""
    o, u, v = (np.asarray(x, dtype=float) for x in (origin, u, v))
    loop = (o, o + u, o + u + v, o + v)
    return (FaceIn(tuple(map(tuple, loop)), material, holes),)


def read(uid, faces, lib, over=None):
    return read_part(RawPart(uid, uid, faces), lib, over)


def test_a_surface_painted_with_laminate_is_a_covering_piece():
    p = read("top", plane((0, 0, 0.054), (1.2, 0, 0), (0, 0.6, 0),
                          "Formica"), library())
    assert p.kind is Kind.COVERING and p.excluded is None
    assert p.core == "Formica"
    assert (p.length, p.width) == pytest.approx((1.2, 0.6))
    assert p.thickness == pytest.approx(0.0008)       # the covering's own
    assert not p.flags


def test_a_surface_painted_otherwise_stays_excluded():
    lib = library()
    for paint in ("Ply", None, "Not set up"):
        p = read("s", plane((0, 0, 0), (1, 0, 0), (0, 1, 0), paint), lib)
        assert p.kind is Kind.BOARD and p.excluded is Excluded.SURFACE


def test_thin_laminate_counts_up_to_two_millimetres():
    lib = library()
    for t in (0.0008, 0.002):
        p = read("t", box(1.0, 0.5, t, default="Formica"), lib)
        assert p.kind is Kind.COVERING, t
    # Thicker: a board read as before (no board face → no material).
    p = read("t", box(1.0, 0.5, 0.003, default="Formica"), lib)
    assert p.kind is Kind.BOARD and Flag.NO_MATERIAL in p.flags


def test_covering_thickness_falls_back_to_the_model():
    lib = library(Formica=MaterialSpec("Formica", role=Role.COVERING))
    p = read("t", box(1.0, 0.5, 0.001, default="Formica"), lib)
    assert p.thickness == pytest.approx(0.001)


def test_covering_pieces_get_a_section_after_the_boards():
    lib = library(Formica=MaterialSpec("Formica", role=Role.COVERING,
                                       thickness=0.0008, oversize=0.005))
    parts = [read("b", box(1.2, 0.6, 0.018, default="Ply"), lib),
             read("c", plane((0, 0, 0.018), (1.2, 0, 0), (0, 0.6, 0),
                             "Formica"), lib)]
    cl = build(parts)
    assert [(s.material, s.kind) for s in cl.sections] == [
        ("Ply", Kind.BOARD), ("Formica", Kind.COVERING)]
    (line,) = cl.sections[1].lines
    # Oversize on each side: 5 mm all round.
    assert (line.cut_length, line.cut_width) == pytest.approx((1.21, 0.61))


def test_covering_pieces_are_laid_out_on_the_coverings_sheets():
    lib = library(Formica=MaterialSpec(
        "Formica", role=Role.COVERING, thickness=0.0008,
        stocks=(SheetSize(3.08, 1.25),)))
    p = read("c", plane((0, 0, 0), (1.2, 0, 0), (0, 0.6, 0), "Formica"), lib)
    cl = build([p])
    job = board_job(cl.sections[0], {p.uid: p}, lib, Settings(), letters(cl))
    assert [(s.length, s.width) for s in job.stocks] == [(3.08, 1.25)]
    assert job.pieces[0].length == pytest.approx(1.2)


def test_a_band_piece_over_stacked_boards_adds_one_edge():
    # Three 18 mm boards glued: one 54 mm strip of band on the front.
    lib = library()
    strip = read("f", plane((0, 0, 0), (1.0, 0, 0), (0, 0, 0.054), "Fita"),
                 lib)
    assert strip.kind is Kind.BAND
    assert (strip.length, strip.width) == pytest.approx((1.0, 0.054))
    cl = build([strip])
    assert cl.sections == [] and cl.band_pieces == [strip]
    (b,) = band_totals(cl.lines(), lib, cl.band_pieces)
    assert b.name == "Fita" and b.edges == 1
    assert b.net == pytest.approx(1.0)


def test_band_pieces_add_to_painted_edges_with_oversize():
    lib = library(Fita=MaterialSpec("Fita", role=Role.EDGE_BAND,
                                    oversize=0.05))
    board = read("b", box(0.7, 0.4, 0.018, default="Ply",
                          paint={"W+": "Fita"}), lib)
    strip = read("s", box(1.0, 0.054, 0.001, default="Fita"), lib)
    cl = build([board, strip])
    (b,) = band_totals(cl.lines(), lib, cl.band_pieces)
    assert b.edges == 2
    assert b.net == pytest.approx(1.7)
    assert b.total == pytest.approx(1.8)


def test_a_band_piece_wider_than_its_band_is_flagged():
    lib = library(Fita=MaterialSpec("Fita", role=Role.EDGE_BAND,
                                    width=0.022))
    strip = read("f", plane((0, 0, 0), (1.0, 0, 0), (0, 0, 0.054), "Fita"),
                 lib)
    assert Flag.NARROW_BAND in strip.flags
    ok = read("g", plane((0, 0, 0), (1.0, 0, 0), (0, 0, 0.018), "Fita"), lib)
    assert Flag.NARROW_BAND not in ok.flags


def test_a_tilted_surface_is_measured_on_its_own_axes():
    r = np.array(rot_z(30))
    p = read("t", plane((0, 0, 0), r @ (1.0, 0, 0), (0, 0, 0.6), "Formica"),
             library())
    assert p.kind is Kind.COVERING
    assert (p.length, p.width) == pytest.approx((1.0, 0.6))


def test_a_laminate_piece_with_a_hole_is_flagged_not_rectangular():
    hole = ((0.4, 0.2, 0), (0.6, 0.2, 0), (0.6, 0.4, 0), (0.4, 0.4, 0))
    p = read("h", plane((0, 0, 0), (1, 0, 0), (0, 0.6, 0), "Formica",
                        holes=(hole,)), library())
    assert p.kind is Kind.COVERING and Flag.NOT_RECTANGULAR in p.flags


def test_exclude_and_grain_apply_to_pieces():
    p = read("x", plane((0, 0, 0), (1, 0, 0), (0, 0.6, 0), "Formica"),
             library(), PartOverride(exclude=True, grain="width"))
    assert p.excluded is Excluded.BY_USER and p.grain == "width"
    assert build([p]).excluded == [p]


def _stack_with_front(lib, front_paint, gap=0.0):
    """Three 1000 × 400 × 18 boards stacked; a laminate surface on their
    front (the x = 1.0 end), ``gap`` off it."""
    boards = [read(f"b{i}", box(1.0, 0.4, 0.018, default="Ply",
                                paint={"L+": front_paint} if front_paint
                                else None, at=(0, 0, 0.018 * i)), lib)
              for i in range(3)]
    front = read("front", plane((1.0 + gap, 0, 0), (0, 0.4, 0),
                                (0, 0, 0.054), "Formica"), lib)
    return boards + [front]


def test_laminate_both_painted_and_drawn_flags_both():
    parts = mark_double_covers(_stack_with_front(library(), "Formica"))
    assert all(Flag.DOUBLE_COVER in p.flags for p in parts)


def test_laminate_drawn_over_plain_boards_is_fine():
    parts = mark_double_covers(_stack_with_front(library(), None))
    assert not any(Flag.DOUBLE_COVER in p.flags for p in parts)


def test_a_piece_lifted_a_little_still_lies_on_the_board():
    lib = library()
    near = mark_double_covers(_stack_with_front(lib, "Formica", gap=0.001))
    assert Flag.DOUBLE_COVER in near[-1].flags
    far = mark_double_covers(_stack_with_front(lib, "Formica", gap=0.01))
    assert Flag.DOUBLE_COVER not in far[-1].flags


def test_a_piece_beside_a_painted_face_is_not_on_it():
    lib = library()
    board = read("b", box(1.0, 0.4, 0.018, default="Ply",
                          paint={"T+": "Formica"}), lib)
    # The same plane as the board's top, but next to it.
    piece = read("p", plane((1.1, 0, 0.018), (1.0, 0, 0), (0, 0.4, 0),
                            "Formica"), lib)
    parts = mark_double_covers([board, piece])
    assert not any(Flag.DOUBLE_COVER in p.flags for p in parts)
