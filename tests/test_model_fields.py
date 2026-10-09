# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Ronaldo Alves and CutList contributors.
"""Custom fields (D-009 §10): part value, else tag rule, else model value."""
from __future__ import annotations

from cutlist.model.fields import FieldDef, Fields, TagRule

FIELDS = Fields((
    FieldDef("Cliente", "Família Souza"),
    FieldDef("Ambiente", "Cozinha",
             (TagRule("QTO", "Quarto"), TagRule("BNH", "Banheiro"))),
))


def test_model_value_for_every_part():
    assert FIELDS.values(None) == {"Cliente": "Família Souza",
                                   "Ambiente": "Cozinha"}


def test_tag_rule_then_part_value():
    assert FIELDS.values("qto armário")["Ambiente"] == "Quarto"
    assert FIELDS.values("QTO", {"Ambiente": "Closet"})["Ambiente"] == \
        "Closet"


def test_round_trip_and_junk():
    assert Fields.from_list(FIELDS.to_list()) == FIELDS
    assert Fields.from_list([{"name": ""}, "x", {"name": "A"},
                             {"name": "A"}]).names == ("A",)


def test_rules_typed_as_text():
    from cutlist.model.fields import format_rules, parse_rules
    rules = parse_rules("QTO = Quarto; BNH=Banheiro; junk; =x")
    assert [(r.prefix, r.value) for r in rules] == [("QTO", "Quarto"),
                                                   ("BNH", "Banheiro")]
    assert format_rules(rules) == "QTO = Quarto; BNH = Banheiro"


def test_part_field_values_round_trip():
    from cutlist.model.parts import PartOverride
    o = PartOverride().with_fields({"Ambiente": "Quarto", "Cliente": ""})
    assert o.field_values == {"Ambiente": "Quarto"}
    assert PartOverride.from_dict(o.to_dict()) == o
