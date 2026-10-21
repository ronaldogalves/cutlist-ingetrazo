# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Ronaldo Alves and CutList contributors.
"""The diagrams of a job: one plan per board, sizes asked when missing,
shop leftovers first, saved plans drawn as they were and checked against
the model (D-012, D-013)."""
from __future__ import annotations

import json
from dataclasses import replace

from cutlist.export.diagrams import (
    board_id,
    changes,
    pack_all,
    prepare,
    saved_boards,
    saved_leftovers,
    snapshot,
)
from cutlist.model.materials import BoardKind, Library, MaterialSpec
from cutlist.model.parts import RawPart, read_part
from cutlist.model.settings import Settings
from cutlist.packing.base import Stock
from cutlist.packing.guillotine import GuillotinePacker
from tests.boxes import box

LIB = Library({
    "MDF": MaterialSpec("MDF", stocks=((2.75, 1.84),)),
    "Freijo": MaterialSpec("Freijo", grain=True),            # no size yet
    "Ipê": MaterialSpec("Ipê", kind=BoardKind.SOLID),
})


def part(uid, material, lx=0.6, ly=0.4, t=0.015, lib=LIB):
    return read_part(RawPart(uid, uid, box(lx, ly, t, default=material)),
                     lib)


def test_one_plan_per_board_and_what_needs_asking():
    parts = [part("a", "MDF"), part("b", "MDF", t=0.006),
             part("c", "Freijo"), part("d", "Ipê")]
    prep = prepare(parts, LIB, Settings())
    assert sorted(p.id for p in prep.plans) == sorted([
        board_id("MDF", 0.015), board_id("MDF", 0.006),
        board_id("Freijo", 0.015)])
    assert prep.missing_sizes == ["Freijo"]
    assert prep.skipped == [("Ipê", "solid")]
    freijo = next(p for p in prep.plans if p.material == "Freijo")
    assert freijo.grain


def test_shop_leftovers_first_and_parts_left_out_of_this_layout():
    parts = [part(u, "MDF") for u in "abcd"]
    bid = board_id("MDF", 0.015)
    left = {bid: (Stock(1.3, 0.9, qty=1, leftover=True),)}
    prep = prepare(parts, LIB, Settings(), leftovers=left,
                   left_out=frozenset({"d"}))
    pack_all(prep.plans, GuillotinePacker())
    (plan,) = prep.plans
    assert plan.layout.sheets[0].stock.leftover
    placed = sum(len(s.placements) for s in plan.layout.sheets)
    assert placed == 3


def test_a_saved_plan_is_drawn_as_it_was_and_says_what_changed():
    parts = [part("a", "MDF"), part("b", "MDF", 0.5, 0.3)]
    prep = prepare(parts, LIB, Settings())
    pack_all(prep.plans, GuillotinePacker())
    left = {board_id("MDF", 0.015): (Stock(1.0, 0.5, qty=2, leftover=True),)}
    data = json.loads(json.dumps(snapshot(prep.plans, parts,
                                          created="2026-10-21",
                                          leftovers=left)))
    (b,) = saved_boards(data)
    assert b.layout == prep.plans[0].layout
    assert saved_leftovers(data) == left

    now = {p.uid: p for p in parts}
    assert not changes(data, now).any
    now["a"] = replace(now["a"], length=0.65)
    del now["b"]
    c = changes(data, now)
    assert c.resized == ("a",) and c.gone == ("b",)
