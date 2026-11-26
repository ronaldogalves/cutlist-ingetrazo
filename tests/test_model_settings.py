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
    parse_lengths,
    parse_number,
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


def test_lengths():
    assert parse_lengths("15; 18 / 6") == pytest.approx((0.015, 0.018, 0.006))
    assert fmt_lengths((0.015, 0.0185)) == "15; 18.5"


def test_material_spec_coerces_plain_strings():
    # Regression: Qt combo boxes return "ignore", not Role.IGNORE.
    spec = MaterialSpec("Vidro", role="ignore", kind="solid")
    assert spec.role is Role.IGNORE


@pytest.fixture
def inches():
    from cutlist.model import text
    text.set_unit_source(lambda: "in")
    yield
    text.set_unit_source(None)


def test_lengths_typed_in_an_inch_model(inches):
    """Issue #1: an imperial user types inches, as a woodworker writes
    them; a unit typed by hand still wins."""
    from cutlist.model.text import fmt_length, parse_length
    inch = 0.0254
    for typed, want in (("3/4", 0.75), ("1 1/2", 1.5), ("1-1/2", 1.5),
                        ('23 9/16"', 23.5625), ("0.118", 0.118),
                        ("96", 96.0), ("3,5", 3.5), ("8'", 96.0),
                        ("4' 1/2\"", 48.5), ("2 in", 2.0)):
        assert parse_length(typed) == pytest.approx(want * inch), typed
    assert parse_length("18mm") == pytest.approx(0.018)
    assert parse_length("1/0") is None and parse_length("3/") is None
    assert parse_lengths("3/4; 1/2") == pytest.approx((0.01905, 0.0127))
    # Written back as typed: fractions on a 1/64 step, else decimals.
    assert fmt_length(0.01905) == "3/4"
    assert fmt_length(0.5984875) == "23 9/16"
    assert fmt_length(2.4384) == "96"
    assert fmt_length(0.003) == "0.1181"            # a 3 mm kerf
    assert fmt_lengths((0.01905, 0.0127)) == "3/4; 1/2"


def test_a_unit_typed_by_hand_in_a_metric_model():
    from cutlist.model.text import input_unit, parse_length
    assert input_unit() == "mm"
    assert parse_length("18") == pytest.approx(0.018)
    assert parse_length('3/4"') == pytest.approx(0.01905)
    assert parse_length("1.8 cm") == pytest.approx(0.018)
    assert parse_length("8'") == pytest.approx(2.4384)
    assert parse_lengths("15; 18 / 6") == pytest.approx((0.015, 0.018, 0.006))


def test_a_failing_unit_source_reads_as_millimetres():
    from cutlist.model import text

    def broken():
        raise RuntimeError("host went away")
    text.set_unit_source(broken)
    try:
        assert text.input_unit() == "mm"
    finally:
        text.set_unit_source(None)
