# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Ronaldo Alves and CutList contributors.
"""Exports (D-009): the two real supplier layouts Ronaldo works with,
reproduced exactly, and the traps that send people to a spreadsheet."""
from __future__ import annotations

import io
import zipfile
from xml.dom import minidom

import pytest

from cutlist.export.profile import Column, Numbers, Profile, generic
from cutlist.export.rows import fill, format_length, make_rows
from cutlist.export.writers import (
    clipboard_text,
    file_bytes,
    text_bytes,
    unencodable,
    xlsx_bytes,
)
from cutlist.model.grouping import build
from cutlist.model.materials import Library, MaterialSpec, Role
from cutlist.model.parts import PartOverride, RawPart, read_part
from tests.boxes import box

LIB = Library({
    "Branco ABS": MaterialSpec("Branco ABS", role=Role.EDGE_BAND),
    "Branco 0.4": MaterialSpec("Branco 0.4", role=Role.EDGE_BAND),
    "Freijo": MaterialSpec("Freijo", grain=True),
})


def cut(*specs):
    """``(uid, name, lx, ly, lz, kwargs-for-box, override)`` → cut list."""
    parts = {}
    for uid, name, lx, ly, lz, kw, over in specs:
        raw = RawPart(uid, name, box(lx, ly, lz, **kw))
        parts[uid] = read_part(raw, LIB, over)
    return build(list(parts.values())), parts


def col(header, value, kind="field", **kw):
    return Column(header=header, kind=kind, value=value, **kw)


# ---------------------------------------------------------------------------
# Layout 1: the paste-from-Excel template (header, named bands, S for rotate)
# ---------------------------------------------------------------------------

PASTE = Profile(
    name="Paste template", format="clipboard",
    columns=(
        col("Quantidade", "qty"), col("Comprimento", "length"),
        col("Largura", "width"), col("Função", "name"),
        col("Fita C1", "band_c1"), col("Fita C2", "band_c2"),
        col("Fita L1", "band_l1"), col("Fita L2", "band_l2"),
        col("Material", "{material} {thickness}", kind="template"),
        col("Complemento", "field:Ambiente"),
        col("Ignorar veio", "rotate", yes="S", no=""),
    ))


def test_paste_template_row_exactly():
    # The template's own example: 500 × 400 "lateral" in Branco TX 15,
    # ABS on one long edge, 0.4 mm on both short ones, room Balcão Cozinha.
    cl, parts = cut(("a", "lateral", 0.5, 0.4, 0.015,
                     {"default": "Branco TX",
                      "paint": {"W+": "Branco ABS", "L+": "Branco 0.4",
                                "L-": "Branco 0.4"}},
                     None))
    lib = Library({**LIB.specs, "Branco TX": MaterialSpec("Branco TX")})
    ex = make_rows(cl, parts, lib, PASTE,
                   part_fields={"a": {"Ambiente": "Balcão Cozinha"}})
    assert ex.ok
    assert clipboard_text(ex.files, PASTE) == (
        "Quantidade\tComprimento\tLargura\tFunção\tFita C1\tFita C2\t"
        "Fita L1\tFita L2\tMaterial\tComplemento\tIgnorar veio\n"
        "1\t500\t400\tlateral\tBranco ABS\t\tBranco 0.4\tBranco 0.4\t"
        "Branco TX 15\tBalcão Cozinha\tS\n")


# ---------------------------------------------------------------------------
# Layout 2: the strict template (codes, no header, Windows-1252, CRLF,
# a separator after the last field)
# ---------------------------------------------------------------------------

STRICT = Profile(
    name="Strict codes", format="text", extension="txt",
    encoding="cp1252", newline="crlf", trailing_separator=True,
    header=False, quoting="none",
    columns=(
        col("", "material_code"), col("", "material_supplier"),
        col("", "qty"), col("", "length"), col("", "width"),
        col("", "grain", yes="1", no="0"),
        col("", "field:Ambiente"), col("", "field:Cliente"),
        col("", "name"),
        col("", "band_c1_code"), col("", "band_c2_code"),
        col("", "band_l1_code"), col("", "band_l2_code"),
    ),
    material_codes={"Branco TX": {"code": "1234567",
                                  "supplier": "MDF BRANCO TX 15MM"}},
    band_codes={"Branco 0.4": {"code": "7654321", "supplier": ""}})


def test_strict_template_bytes_exactly():
    cl, parts = cut(
        ("a", "Porta", 0.72, 0.45, 0.015,
         {"default": "Branco TX", "paint": {s: "Branco 0.4" for s in
                                            ("W+", "W-", "L+", "L-")}},
         None),
        ("b", "Porta", 0.72, 0.45, 0.015,
         {"default": "Branco TX", "paint": {s: "Branco 0.4" for s in
                                            ("W+", "W-", "L+", "L-")}},
         None))
    lib = Library({**LIB.specs, "Branco TX": MaterialSpec("Branco TX")})
    fields = {u: {"Ambiente": "Cozinha", "Cliente": "Família Souza"}
              for u in ("a", "b")}
    ex = make_rows(cl, parts, lib, STRICT, part_fields=fields)
    assert ex.ok
    (f,) = ex.files
    assert f.name.endswith(".txt")
    assert text_bytes(f, STRICT) == (
        "1234567;MDF BRANCO TX 15MM;2;720;450;0;Cozinha;Família Souza;"
        "Porta;7654321;7654321;7654321;7654321;\r\n").encode("cp1252")


def test_a_band_without_a_code_stops_the_export():
    cl, parts = cut(("a", "Side", 0.6, 0.3, 0.015,
                     {"default": "Branco TX",
                      "paint": {"W+": "Branco ABS"}}, None))
    lib = Library({**LIB.specs, "Branco TX": MaterialSpec("Branco TX")})
    ex = make_rows(cl, parts, lib, STRICT)
    assert not ex.ok
    assert [(p.kind, p.value) for p in ex.problems] == \
        [("band_code", "Branco ABS")]


def test_a_character_windows_1252_cannot_hold_is_reported():
    cl, parts = cut(("a", "Prateleira ≥ 30", 0.6, 0.3, 0.015,
                     {"default": "Branco TX"}, None))
    lib = Library({**LIB.specs, "Branco TX": MaterialSpec("Branco TX")})
    ex = make_rows(cl, parts, lib, STRICT)
    bad = unencodable(ex.files[0], STRICT)
    assert [p.value for p in bad] == ["≥"]


# ---------------------------------------------------------------------------
# Grain first
# ---------------------------------------------------------------------------

def test_grain_across_the_long_side_swaps_sizes_and_bands():
    # 800 × 200 drawer front, grain vertical (along the 200), banded only
    # on its two short ends.
    cl, parts = cut(("a", "Gaveta", 0.8, 0.2, 0.015,
                     {"default": "Freijo",
                      "paint": {"L+": "Branco 0.4", "L-": "Branco 0.4"}},
                     PartOverride(grain="width")))
    ex = make_rows(cl, parts, LIB, PASTE)
    row = [c.text for c in ex.files[0].rows[0]]
    assert row[1:3] == ["200", "800"]
    assert row[4:8] == ["Branco 0.4", "Branco 0.4", "", ""]
    assert row[10] == ""                       # grained: may not rotate


def test_no_grain_on_a_grained_board_may_rotate():
    cl, parts = cut(("a", "Fundo interno", 0.8, 0.2, 0.015,
                     {"default": "Freijo"}, PartOverride(grain="none")))
    ex = make_rows(cl, parts, LIB, PASTE)
    row = [c.text for c in ex.files[0].rows[0]]
    assert row[1:3] == ["800", "200"] and row[10] == "S"


# ---------------------------------------------------------------------------
# Numbers, templates, rows, files
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("metres, numbers, text", [
    (0.6004, Numbers(), "600"),
    (0.6005, Numbers(), "601"),
    (0.6001, Numbers(rounding="up"), "601"),
    (0.6009, Numbers(rounding="down"), "600"),
    (0.0185, Numbers(decimals=1), "18,5"),
    (0.018, Numbers(decimals=2), "18"),
    (0.018, Numbers(decimals=2, strip_zeros=False, decimal_sep="."),
     "18.00"),
    (0.6, Numbers(suffix=True), "600 mm"),
    (0.6, Numbers(unit="cm", decimals=1), "60"),
    (0.0254 * 23.5, Numbers(unit="in", decimals=2, decimal_sep="."),
     "23.5"),
])
def test_numbers(metres, numbers, text):
    assert format_length(metres, numbers).text == text


def test_templates_are_placeholders_only():
    assert fill("{name} - {tag}", {"name": "Side", "tag": "A"}) == "Side - A"
    assert fill("{name.__class__}", {"name": "x"}) == "{name.__class__}"
    assert fill("{missing}", {}) == ""


def test_one_row_per_piece_and_one_file_per_board():
    cl, parts = cut(
        ("a", "Side", 0.6, 0.3, 0.015, {"default": "Branco"}, None),
        ("b", "Side", 0.6, 0.3, 0.015, {"default": "Branco"}, None),
        ("c", "Back", 0.6, 0.3, 0.006, {"default": "Branco"}, None))
    p = Profile(rows="per_piece", split="board",
                filename="{model} - {material} {thickness}",
                columns=(col("Qty", "qty"), col("Name", "name")))
    ex = make_rows(cl, parts, Library(), p, context={"model": "Kitchen"})
    assert [f.name for f in ex.files] == ["Kitchen_-_Branco_6.csv",
                                         "Kitchen_-_Branco_15.csv"]
    assert [[c.text for c in r] for r in ex.files[1].rows] == \
        [["1", "Side"], ["1", "Side"]]


def test_split_by_custom_field_splits_merged_lines_too():
    cl, parts = cut(
        ("a", "Shelf", 0.6, 0.3, 0.015, {"default": "Branco"}, None),
        ("b", "Shelf", 0.6, 0.3, 0.015, {"default": "Branco"}, None))
    p = Profile(split="field:Ambiente", filename="{value}",
                columns=(col("Qty", "qty"),))
    ex = make_rows(cl, parts, Library(), p,
                   part_fields={"a": {"Ambiente": "Cozinha"},
                                "b": {"Ambiente": "Quarto"}})
    assert sorted((f.name, f.rows[0][0].text) for f in ex.files) == \
        [("Cozinha.csv", "1"), ("Quarto.csv", "1")]


def test_text_options():
    cl, parts = cut(("a", 'Side; "left"', 0.6, 0.3, 0.015,
                     {"default": "Branco"}, None))
    p = Profile(separator=";", encoding="utf-8", newline="lf",
                columns=(col("Name", "name"), col("L", "length")))
    ex = make_rows(cl, parts, Library(), p)
    assert text_bytes(ex.files[0], p) == \
        b'Name;L\n"Side; ""left""";600\n'
    bom = Profile(**{**p.__dict__, "encoding": "utf-8-sig"})
    assert text_bytes(ex.files[0], bom).startswith(b"\xef\xbb\xbf")


def test_xlsx_is_a_valid_workbook_with_real_numbers():
    cl, parts = cut(("a", "Side & top", 0.6, 0.3, 0.015,
                     {"default": "Branco"}, None))
    p = Profile(format="xlsx", extension="xlsx",
                columns=(col("Qty", "qty"), col("Name", "name"),
                         col("Length", "length")))
    ex = make_rows(cl, parts, Library(), p)
    data = file_bytes(ex.files[0], p)
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        sheet = z.read("xl/worksheets/sheet1.xml").decode("utf-8")
        for name in z.namelist():
            minidom.parseString(z.read(name))          # well-formed XML
    assert "Side &amp; top" in sheet
    assert '<c r="C2"><v>600</v></c>' in sheet
    assert data == xlsx_bytes(ex.files[0]) or data


def test_profile_round_trip_and_leniency():
    assert Profile.from_dict(STRICT.to_dict()) == STRICT
    assert Profile.from_dict(generic().to_dict()) == generic()
    junk = Profile.from_dict({"encoding": "ebcdic", "columns": [
        {"kind": "eval", "value": "os.system('x')"}, {"value": "qty"}]})
    assert junk.encoding == Profile().encoding
    assert [c.value for c in junk.columns] == ["qty"]


def test_file_names_are_always_safe():
    from cutlist.export.rows import safe_stem
    assert safe_stem("Família Souza - MDF Branco 15") == \
        "Familia_Souza_-_MDF_Branco_15"
    assert safe_stem('a/b:c*?"<>|  d') == "abc_d"
    assert safe_stem("   ") == "cut_list"


def test_values_are_tidied_and_text_options_apply():
    cl, parts = cut(("a", "  Prateleira   do  meio ", 0.6, 0.3, 0.015,
                     {"default": "Família ç"}, None))
    p = Profile(columns=(
        col("A", "name"),
        col("B", "material", text=("ascii", "upper", "underscores")),
        col("C", "material", text=("underscores",))))
    ex = make_rows(cl, parts, Library(), p)
    assert [c.text for c in ex.files[0].rows[0]] == \
        ["Prateleira do meio", "FAMILIA_C", "Família_ç"]
    assert Profile.from_dict(p.to_dict()) == p


def test_boards_can_be_left_out_of_one_export():
    from cutlist.export.rows import board_key, boards
    cl, parts = cut(
        ("a", "Side", 0.6, 0.3, 0.015, {"default": "Branco"}, None),
        ("b", "Back", 0.6, 0.3, 0.006, {"default": "Branco"}, None),
        ("c", "Door", 0.6, 0.3, 0.018, {"default": "Freijo"}, None))
    assert [(m, round(t * 1000), n) for _k, m, t, n in boards(cl)] == \
        [("Branco", 6, 1), ("Branco", 15, 1), ("Freijo", 18, 1)]
    p = Profile(split="board", filename="{material} {thickness}",
                columns=(col("Name", "name"),))
    ex = make_rows(cl, parts, LIB, p,
                   skip_boards={board_key("Branco", 0.006)})
    assert [f.name for f in ex.files] == ["Branco_15.csv", "Freijo_18.csv"]
