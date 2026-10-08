# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Ronaldo Alves and CutList contributors.
"""Settings cascade, part overrides, material specs and typed lengths."""
from __future__ import annotations

import pytest

from cutlist.model.materials import Library, MaterialSpec, Role
from cutlist.model.parts import PartOverride
from cutlist.model.settings import Settings, diff, resolve
from cutlist.model.text import (
    fmt_lengths,
    fmt_sheets,
    parse_lengths,
    parse_number,
    parse_sheets,
)


def test_cascade_most_specific_wins():
    s = resolve({"tolerance": 0.0005, "unit": "mm"}, {"unit": "cm"})
    assert s.unit == "cm" and s.tolerance == 0.0005
    assert s.merge_by_size is True                  # our default


def test_cascade_ignores_junk():
    s = resolve({"unit": "parsecs", "tolerance": "abc", "bogus": 1,
                 "excluded_tags": ["A", 2]})
    assert s.unit is None and s.tolerance == Settings().tolerance
    assert s.excluded_tags == ("A", "2")


def test_diff_stores_only_what_changed():
    base = resolve({"unit": "mm"})
    s = resolve({"unit": "mm", "merge_by_size": False})
    assert diff(s, base) == {"merge_by_size": False}


def test_part_override_round_trip():
    o = PartOverride(flip_face1=True, note="from stock", grain="width",
                     can_rotate=False)
    assert PartOverride.from_dict(o.to_dict()) == o
    assert PartOverride().is_empty
    assert PartOverride.from_dict({"grain": "diagonal"}).grain is None
    assert PartOverride.from_dict("garbage") == PartOverride()


def test_material_spec_round_trip_and_leniency():
    spec = MaterialSpec("Fita", role=Role.EDGE_BAND, thickness=0.001,
                        oversize=0.03, deduct=True)
    lib = Library.from_dict({"Fita": spec.to_dict(),
                             "Bad": {"role": "nonsense", "stocks": [[1]]}})
    assert lib.get("Fita") == spec
    assert lib.role("Bad") is Role.BOARD and lib.get("Bad").stocks == ()


def test_parse_number():
    assert parse_number("3,5") == 3.5
    assert parse_number("") is None and parse_number("x") is None
    assert parse_number("-1") is None


def test_lengths_and_sheets():
    assert parse_lengths("15; 18 / 6") == pytest.approx((0.015, 0.018, 0.006))
    sheets = parse_sheets("2750 x 1840; 1220×2440; nonsense")
    assert [v for sheet in sheets for v in sheet] == \
        pytest.approx([2.75, 1.84, 2.44, 1.22])
    assert fmt_lengths((0.015, 0.0185)) == "15; 18.5"
    assert fmt_sheets(((2.75, 1.84),)) == "2750 x 1840"


def test_material_spec_coerces_plain_strings():
    # Regression: Qt combo boxes return "ignore", not Role.IGNORE.
    spec = MaterialSpec("Vidro", role="ignore", kind="solid")
    assert spec.role is Role.IGNORE
