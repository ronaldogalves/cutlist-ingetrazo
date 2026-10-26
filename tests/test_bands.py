# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Ronaldo Alves and CutList contributors.
"""Edge bands (D-017): metres to buy, the band's room to be finished, and
the board cut smaller for thick bands — only when the band says so."""
from __future__ import annotations

import pytest

from cutlist.export.plan import Board, PartInfo
from cutlist.export.plan import build as plan
from cutlist.export.profile import Column, Profile
from cutlist.export.rows import make_rows
from cutlist.model.bands import band_totals
from cutlist.model.grouping import build
from cutlist.model.materials import Library, MaterialSpec, Role
from cutlist.model.parts import Flag, RawPart, read_part
from cutlist.packing.base import Layout
from tests.boxes import box


def band(name, **kw):
    return MaterialSpec(name, role=Role.EDGE_BAND, **kw)


def part(uid, lx, ly, t, lib, paint):
    return read_part(RawPart(uid, uid, box(lx, ly, t, default="MDF",
                                           paint=paint)), lib)


def test_metres_to_buy():
    # Door 700 × 400, banded all round, twice: 2 × 2.2 m = 4.4 m of edge.
    lib = Library({"MDF": MaterialSpec("MDF"), "Fita": band("Fita")})
    all_round = {s: "Fita" for s in ("W+", "W-", "L+", "L-")}
    parts = [part(u, 0.7, 0.4, 0.018, lib, all_round) for u in "ab"]
    (b,) = band_totals(build(parts).lines(), lib)
    assert b.edges == 8 and b.net == pytest.approx(4.4)
    assert b.total == pytest.approx(4.4) and b.rolls == 0


def test_oversize_waste_and_rolls():
    lib = Library({"MDF": MaterialSpec("MDF"),
                   "Fita": band("Fita", oversize=0.03, waste=0.1, roll=2.0)})
    p = part("a", 0.7, 0.4, 0.018, lib, {"W+": "Fita"})   # one long edge
    (b,) = band_totals(build([p]).lines(), lib)
    assert b.net == pytest.approx(0.7)
    assert b.total == pytest.approx((0.7 + 0.03) * 1.1)
    assert b.rolls == 1


def test_a_band_needs_room_to_be_finished():
    """A 22 mm band fits up to 20 mm with the default 2 mm margin; a 25 mm
    board with it is flagged (Ronaldo)."""
    lib = Library({"MDF": MaterialSpec("MDF"), "Fita 22": band(
        "Fita 22", width=0.022)})
    ok = part("a", 0.7, 0.4, 0.018, lib, {"W+": "Fita 22"})
    tight = part("b", 0.7, 0.4, 0.022, lib, {"W+": "Fita 22"})
    thick = part("c", 0.7, 0.4, 0.025, lib, {"W+": "Fita 22"})
    assert Flag.NARROW_BAND not in ok.flags
    assert Flag.NARROW_BAND in tight.flags and Flag.NARROW_BAND in thick.flags
    # No width set: nothing to check.
    lib2 = Library({"MDF": MaterialSpec("MDF"), "Fita": band("Fita")})
    assert Flag.NARROW_BAND not in part("d", 0.7, 0.4, 0.025, lib2,
                                        {"W+": "Fita"}).flags


def test_deduction_only_when_the_band_says_so():
    abs2 = {"MDF": MaterialSpec("MDF")}
    ends = {"L+": "ABS", "L-": "ABS", "W+": "ABS"}  # both ends, one long edge
    off = part("a", 0.7, 0.4, 0.018,
               Library({**abs2, "ABS": band("ABS", thickness=0.002)}), ends)
    assert (off.extra_length, off.extra_width) == (0.0, 0.0)
    lib = Library({**abs2, "ABS": band("ABS", thickness=0.002, deduct=True)})
    on = part("b", 0.7, 0.4, 0.018, lib, ends)
    assert on.extra_length == pytest.approx(-0.004)        # two ends
    assert on.extra_width == pytest.approx(-0.002)         # one long edge
    (line,) = build([on]).lines()
    assert line.length == pytest.approx(0.7)               # finished kept
    assert (line.cut_length, line.cut_width) == pytest.approx((0.696, 0.398))


def test_the_band_list_beside_the_export_and_on_the_plan():
    lib = Library({"MDF": MaterialSpec("MDF"),
                   "Fita": band("Fita", width=0.022, roll=50.0)})
    p = part("a", 0.7, 0.4, 0.018, lib, {"W+": "Fita", "W-": "Fita"})
    cl = build([p])
    prof = Profile(columns=(Column("Name", value="name"),), band_list=True,
                   filename="{model}")
    ex = make_rows(cl, {"a": p}, lib, prof, context={"model": "Job"})
    assert [f.name for f in ex.files] == ["Job.csv", "Job_edge_bands.csv"]
    assert [c.text for c in ex.files[1].rows[0]] == \
        ["Fita", "22", "2", "1,40", "1"]
    off = make_rows(cl, {"a": p}, lib, Profile(columns=prof.columns))
    assert len(off.files) == 1

    pages = plan([Board("MDF", 0.018, Layout(), {"A": PartInfo("a", 0.7,
                                                               0.4)})],
                 model="Job", date="d", bands=band_totals(cl.lines(), lib))
    words = [s.text for s in pages[0].shapes if s.kind == "text"]
    assert "Fita" in words and "1.4" in words and "1 × 50 m" in words
