# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Ronaldo Alves and CutList contributors.
"""Reading a painted part through material roles (D-007), with the cases
from the M0 spike."""
from __future__ import annotations

import pytest

from cutlist.model.materials import Library, MaterialSpec, Role
from cutlist.model.parts import (
    Excluded,
    Flag,
    PartOverride,
    RawPart,
    read_part,
)
from tests.boxes import box


def lib(**roles):
    return Library({n: MaterialSpec(n, role=r) for n, r in roles.items()})


def raw(faces, name="Part"):
    return RawPart(uid="u1", name=name, faces=faces)


EDGE_SIDES = {"W+": "length1", "W-": "length2", "L-": "width1",
              "L+": "width2"}


def test_unpainted_setup_reads_the_board():
    p = read_part(raw(box(0.7, 0.4, 0.018, default="MDF Branco")), lib())
    assert p.core == "MDF Branco"
    assert p.size == pytest.approx((0.7, 0.4, 0.018))
    assert p.face1 is p.face2 is None
    assert p.edges == (None,) * 4
    assert not p.flags


def test_plywood_baguette_unassigned_edge_texture():
    # Model D: 2 main faces compensado, 4 edge faces the texture "*".
    faces = box(1.982, 0.015, 0.015, default="*",
                paint={"T+": "COMPENSADO", "T-": "COMPENSADO"})
    p = read_part(raw(faces), lib())
    assert p.core == "COMPENSADO"
    assert Flag.UNASSIGNED in p.flags and p.unassigned == {"*"}


def test_plywood_baguette_with_appearance_role_is_clean():
    faces = box(1.982, 0.015, 0.015, default="*",
                paint={"T+": "COMPENSADO", "T-": "COMPENSADO"})
    p = read_part(raw(faces), lib(**{"*": Role.APPEARANCE}))
    assert p.core == "COMPENSADO"
    assert p.edges == (None,) * 4 and not p.flags


def test_formica_on_one_face_is_face_1():
    faces = box(0.7, 0.4, 0.0196, default="MDF",
                paint={"T-": "Formica"})
    p = read_part(raw(faces), lib(Formica=Role.COVERING))
    assert p.core == "MDF"
    assert p.face1 == "Formica" and p.face2 is None
    assert p.face1_side == "T-"


def test_decorative_face_is_face_1_without_any_covering_role():
    faces = box(0.7, 0.4, 0.018, default="MDF Branco",
                paint={"T-": "MDF Freijo"})
    p = read_part(raw(faces), lib(**{"MDF Branco": Role.BOARD}))
    assert p.face1_side == "T-"


def test_bands_named_looking_at_face_1():
    paint = {"W+": "Fita", "L-": "Fita"}
    p = read_part(raw(box(0.7, 0.4, 0.018, paint=paint)),
                  lib(Fita=Role.EDGE_BAND))
    assert dict(zip(("length1", "length2", "width1", "width2"),
                    p.edges, strict=True)) == \
        {"length1": "Fita", "length2": None, "width1": "Fita",
         "width2": None}


def test_flipping_face_1_mirrors_the_ends():
    paint = {"W+": "Fita", "L-": "Fita"}
    p = read_part(raw(box(0.7, 0.4, 0.018, paint=paint)),
                  lib(Fita=Role.EDGE_BAND), PartOverride(flip_face1=True))
    assert p.face1_side == "T-"
    assert p.edges == ("Fita", None, None, "Fita")


def test_ignored_material_is_excluded():
    p = read_part(raw(box(0.5, 0.5, 0.004, default="Vidro")),
                  lib(Vidro=Role.IGNORE))
    assert p.excluded is Excluded.IGNORED_MATERIAL


def test_excluded_by_user():
    p = read_part(raw(box(0.5, 0.4, 0.018)), lib(),
                  PartOverride(exclude=True, note="from stock"))
    assert p.excluded is Excluded.BY_USER and p.note == "from stock"


def test_surface():
    p = read_part(raw(box(0.5, 0.4, 0.0, default="Decal")), lib())
    assert p.excluded is Excluded.SURFACE


def test_no_material():
    p = read_part(raw(box(0.5, 0.4, 0.018, default=None)), lib())
    assert p.core is None and Flag.NO_MATERIAL in p.flags


def test_covering_everywhere_uses_the_board_it_goes_on():
    library = Library({"Formica": MaterialSpec(
        "Formica", role=Role.COVERING, applied_over="MDF 18 cru")})
    p = read_part(raw(box(0.5, 0.4, 0.0196, default="Formica")), library)
    assert p.core == "MDF 18 cru"
    assert p.face1 == p.face2 == "Formica"


def test_a_cabinet_merged_into_one_group_is_flagged():
    faces = box(0.6, 0.5, 0.018) + box(0.6, 0.5, 0.018, at=(0, 0, 0.7))
    p = read_part(raw(faces), lib())
    assert Flag.SEVERAL_SOLIDS in p.flags


def test_names_are_tidied():
    # Regression (model D): "GAB MONT INT " and "GAB MONT INT" are one part.
    a = read_part(raw(box(0.7, 0.4, 0.018), name="GAB MONT INT "), lib())
    b = read_part(raw(box(0.7, 0.4, 0.018), name=" GAB  MONT INT"), lib())
    assert a.name == b.name == "GAB MONT INT"
