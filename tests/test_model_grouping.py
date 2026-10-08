# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Ronaldo Alves and CutList contributors.
"""Parts into sections and lines: merge by measurement (D-006 §4)."""
from __future__ import annotations

import pytest

from cutlist.model.grouping import build, quantize
from cutlist.model.materials import Library, MaterialSpec, Role
from cutlist.model.parts import RawPart, read_part
from tests.boxes import box

LIB = Library({"Fita": MaterialSpec("Fita", role=Role.EDGE_BAND),
               "Vidro": MaterialSpec("Vidro", role=Role.IGNORE)})


def part(uid, lx, ly, lz, name="P", component=False, **kw):
    r = RawPart(uid, name, box(lx, ly, lz, **kw), is_component=component)
    return read_part(r, LIB)


def test_quantize():
    assert quantize(0.01798, 0.001) == pytest.approx(0.018)
    assert quantize(0.0183, 0.0005) == pytest.approx(0.0185)


def test_groups_and_components_of_one_board_are_one_line():
    cl = build([part("a", 0.5, 0.5, 0.5, component=True),
                part("b", 0.5, 0.5, 0.5)])
    (line,) = cl.lines()
    assert line.qty == 2 and line.components == 1 and line.groups == 1


def test_sloppy_board_merges_within_tolerance():
    cl = build([part("a", 0.6, 0.3, 0.018), part("b", 0.6002, 0.3, 0.01798)])
    (section,) = cl.sections
    assert section.thickness == pytest.approx(0.018)
    assert [ln.qty for ln in section.lines] == [2]


def test_sections_by_material_and_thickness():
    cl = build([part("a", 0.6, 0.3, 0.015, default="Branco"),
                part("b", 0.6, 0.3, 0.018, default="Branco"),
                part("c", 0.6, 0.3, 0.015, default="Verde")])
    assert [(s.material, round(s.thickness * 1000)) for s in cl.sections] \
        == [("Branco", 15), ("Branco", 18), ("Verde", 15)]


def test_different_bands_are_different_lines():
    cl = build([part("a", 0.6, 0.3, 0.015, paint={"W+": "Fita"}),
                part("b", 0.6, 0.3, 0.015)])
    assert sorted(ln.qty for ln in cl.lines()) == [1, 1]


def test_lines_largest_first_and_names_natural():
    cl = build([part("a", 0.3, 0.2, 0.015, name="Shelf 10"),
                part("b", 0.3, 0.2, 0.015, name="Shelf 2"),
                part("c", 0.9, 0.2, 0.015, name="Side")])
    lines = list(cl.lines())
    assert lines[0].display_names() == ["Side"]
    assert lines[1].display_names() == ["Shelf 2", "Shelf 10"]


def test_excluded_and_unassigned_are_reported():
    cl = build([part("a", 0.5, 0.5, 0.004, default="Vidro"),
                part("b", 0.6, 0.3, 0.015, paint={"L+": "*"})])
    assert [p.uid for p in cl.excluded] == ["a"]
    assert cl.unassigned == {"*": 1}
    assert [p.uid for p in cl.flagged] == ["b"]
    assert cl.qty == 1


def test_same_size_different_names_merge_unless_kept_apart():
    parts = [part("a", 0.6, 0.3, 0.015, name="Door left"),
             part("b", 0.6, 0.3, 0.015, name="Door right"),
             part("c", 0.6, 0.3, 0.015, name="Door left")]
    (merged,) = build(parts).lines()
    assert merged.qty == 3
    assert merged.display_names() == ["Door left", "Door right"]
    apart = sorted((ln.display_names()[0], ln.qty)
                   for ln in build(parts, by_name=True).lines())
    assert apart == [("Door left", 2), ("Door right", 1)]
