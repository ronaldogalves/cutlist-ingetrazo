# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Ronaldo Alves and CutList contributors.
"""From a cut list to the packer: letters (D-016), grain and rotation, the
board's saw (D-014)."""
from __future__ import annotations

import pytest

from cutlist.model.grouping import build
from cutlist.model.materials import Library, MaterialSpec
from cutlist.model.parts import PartOverride, RawPart, read_part
from cutlist.model.settings import Settings
from cutlist.packing.guillotine import pack
from cutlist.packing.jobs import board_job, letter, letters
from tests.boxes import box


@pytest.mark.parametrize("n, text", [(0, "A"), (25, "Z"), (26, "AA"),
                                     (27, "AB"), (51, "AZ"), (52, "BA"),
                                     (701, "ZZ"), (702, "AAA")])
def test_letters_like_spreadsheet_columns(n, text):
    assert letter(n) == text


LIB = Library({
    "Naval": MaterialSpec("Naval", grain=True, stocks=((2.5, 1.6),),
                          kerf=0.005),
    "MDF": MaterialSpec("MDF", stocks=((1.84, 2.75),)),
})


def job(*specs):
    parts = {}
    for uid, material, lx, ly, over in specs:
        parts[uid] = read_part(RawPart(uid, uid, box(lx, ly, 0.015,
                                                     default=material)),
                               LIB, over)
    cl = build(list(parts.values()), by_name=True)
    names = letters(cl)
    return [board_job(s, parts, LIB, Settings(), names)
            for s in cl.sections], names, cl


def test_grain_and_rotation():
    jobs, _names, _cl = job(
        ("side", "Naval", 2.3, 0.6, None),                     # grain along
        ("rail", "Naval", 0.9, 0.1, PartOverride(grain="width")),
        ("free", "Naval", 0.5, 0.4, PartOverride(can_rotate=True)),
        ("door", "MDF", 0.7, 0.4, None),                       # no grain
        ("fixed", "MDF", 0.6, 0.3, PartOverride(can_rotate=False)))
    pieces = {round(p.length, 4): p for j in jobs for p in j.pieces}
    assert not pieces[2.3].rotate
    rail = next(p for j in jobs for p in j.pieces
                if (p.length, p.width) == pytest.approx((0.1, 0.9)))
    assert not rail.rotate                  # given turned: grain across
    assert pieces[0.5].rotate               # "ignore grain"
    assert pieces[0.7].rotate and not pieces[0.6].rotate


def test_the_board_s_saw_and_sheets():
    jobs, _n, _cl = job(("side", "Naval", 2.3, 0.6, None),
                        ("door", "MDF", 0.7, 0.4, None))
    naval = next(j for j in jobs if j.material == "Naval")
    mdf = next(j for j in jobs if j.material == "MDF")
    assert naval.settings.kerf == 0.005 and mdf.settings.kerf == 0.003
    # Sizes are written either way round; a sheet is length × width.
    assert (mdf.stocks[0].length, mdf.stocks[0].width) == (2.75, 1.84)


def test_one_letter_per_line_across_the_job():
    jobs, names, cl = job(("a", "Naval", 2.3, 0.6, None),
                          ("b", "MDF", 0.7, 0.4, None),
                          ("c", "MDF", 0.6, 0.3, None))
    assert sorted(names.values()) == ["A", "B", "C"]
    keys = [p.key for j in jobs for p in j.pieces]
    assert sorted(keys) == ["A", "B", "C"]
    layout = pack(list(jobs[0].pieces), list(jobs[0].stocks),
                  jobs[0].settings)
    assert not layout.unplaced
