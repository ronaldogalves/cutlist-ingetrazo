# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Ronaldo Alves and CutList contributors.
"""The cut list as rows of text, the way one profile wants them (D-009).

Nothing here writes a file: :func:`make_rows` returns the files to write
(their name and rows) and the **problems** that must be solved first — a
material with no supplier code, a character the encoding cannot hold.
An export with problems is not written; nothing is ever left blank
silently.
"""
from __future__ import annotations

import re
import string
import unicodedata
from dataclasses import dataclass, field
from decimal import ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP, Decimal

from ..model.grouping import CutList, CutListLine, _natural
from ..model.materials import Library
from ..model.parts import Part
from ..model.text import tidy
from .profile import FIELDS, FLAG_FIELDS, LENGTH_FIELDS, Column, Numbers, Profile

_UNITS = {"mm": Decimal("0.001"), "cm": Decimal("0.01"), "m": Decimal("1"),
          "in": Decimal("0.0254")}
_ROUNDING = {"nearest": ROUND_HALF_UP, "up": ROUND_CEILING,
             "down": ROUND_FLOOR}


@dataclass(frozen=True)
class Cell:
    text: str
    #: The number behind a length or a quantity (for spreadsheet cells).
    number: float | None = None


@dataclass
class OutFile:
    name: str                               # file name, extension included
    header: list[str] | None
    rows: list[list[Cell]] = field(default_factory=list)


@dataclass
class Problem:
    kind: str                               # material_code, band_code, …
    value: str
    count: int = 1


@dataclass
class Export:
    files: list[OutFile] = field(default_factory=list)
    problems: list[Problem] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.problems


# ---------------------------------------------------------------------------
# Numbers
# ---------------------------------------------------------------------------

def number_value(metres: float, numbers: Numbers) -> Decimal:
    per = _UNITS.get(numbers.unit, _UNITS["mm"])
    q = Decimal(1).scaleb(-numbers.decimals)
    return (Decimal(repr(float(metres))) / per).quantize(
        q, rounding=_ROUNDING.get(numbers.rounding, ROUND_HALF_UP))


def format_length(metres: float, numbers: Numbers) -> Cell:
    """A length as the profile writes it: unit, decimals, rounding, decimal
    separator, trailing zeros, optional unit."""
    value = number_value(metres, numbers)
    text = f"{value:f}"
    if numbers.strip_zeros and "." in text:
        text = text.rstrip("0").rstrip(".")
    if text in ("-0", ""):
        text = "0"
    text = text.replace(".", numbers.decimal_sep)
    if numbers.suffix:
        text += f" {numbers.unit}"
    return Cell(text, float(value))


# ---------------------------------------------------------------------------
# Text
# ---------------------------------------------------------------------------

def no_accents(text: str) -> str:
    """"Família Souza" → "Familia Souza"; "ç" → "c"."""
    return "".join(ch for ch in unicodedata.normalize("NFKD", text)
                   if not unicodedata.combining(ch))


def apply_text(text: str, options) -> str:
    """A column's text options: accents off, UPPERCASE, spaces → "_"."""
    if "ascii" in options:
        text = no_accents(text)
    if "upper" in options:
        text = text.upper()
    if "underscores" in options:
        text = re.sub(r"\s+", "_", text)
    return text


def safe_stem(text: str) -> str:
    """A file name every system and upload form takes (always, D-009):
    no accents, spaces → "_", only letters, digits and ``_ - . ( )``."""
    text = re.sub(r"\s+", "_", no_accents(tidy(text)))
    text = re.sub(r"[^A-Za-z0-9_\-.()]", "", text)
    text = re.sub(r"_{2,}", "_", text).strip("._-")
    return text or "cut_list"


# ---------------------------------------------------------------------------
# Templates: placeholders only
# ---------------------------------------------------------------------------

class _SafeFormatter(string.Formatter):
    """``{name}`` placeholders and nothing else: no attributes, no
    indexing, no conversions — a template can never reach into objects."""

    def get_field(self, field_name, args, kwargs):
        if not re.fullmatch(r"[\w ]+", field_name or ""):
            raise KeyError(field_name)
        return kwargs.get(field_name, ""), field_name

    def convert_field(self, value, conversion):
        return value

    def format_field(self, value, format_spec):
        return str(value)


_FORMATTER = _SafeFormatter()


def placeholders(template: str) -> list[str]:
    """The ``{names}`` a template uses."""
    try:
        return [name for _lit, name, _spec, _conv
                in string.Formatter().parse(template or "") if name]
    except ValueError:
        return []


def fill(template: str, values: dict) -> str:
    try:
        return _FORMATTER.vformat(template, (), values)
    except (KeyError, ValueError, IndexError):
        return template


# ---------------------------------------------------------------------------
# Rows
# ---------------------------------------------------------------------------

@dataclass
class _Piece:
    line: CutListLine
    line_no: int
    part: Part
    fields: dict


def effective_grain(part: Part, library: Library) -> str:
    """"length", "width" or "none": the part's own, else its material's."""
    if part.grain is not None:
        return part.grain
    spec = library.get(part.core)
    return "length" if spec is not None and spec.grain else "none"


def _bands(part: Part, swapped: bool) -> dict:
    l1, l2, w1, w2 = part.edges
    c = (w1, w2) if swapped else (l1, l2)
    lw = (l1, l2) if swapped else (w1, w2)
    return {"c1": c[0], "c2": c[1], "l1": lw[0], "l2": lw[1]}


def _unique(values) -> list[str]:
    out: list[str] = []
    for v in values:
        if v and v not in out:
            out.append(v)
    return out


def make_rows(cut_list: CutList, parts: dict[str, Part], library: Library,
              profile: Profile, *, part_fields: dict | None = None,
              context: dict | None = None) -> Export:
    """``parts`` by uid; ``part_fields`` uid → custom field values;
    ``context`` holds model-wide values (``model``, ``date``…)."""
    part_fields = part_fields or {}
    context = dict(context or {})
    out = Export()
    problems: dict = {}

    def problem(kind: str, value: str) -> None:
        key = (kind, value)
        if key in problems:
            problems[key].count += 1
        else:
            problems[key] = Problem(kind, value)

    # Every piece, in cut-list order, tagged with its line.
    pieces: list[_Piece] = []
    line_no = 0
    for section in cut_list.sections:
        if profile.materials and section.material not in profile.materials:
            continue
        for line in section.lines:
            line_no += 1
            for uid in line.uids:
                if uid in parts:
                    pieces.append(_Piece(line, line_no, parts[uid],
                                         part_fields.get(uid, {})))
    for p in pieces:
        if p.part.core is None:
            problem("no_material", p.part.name)

    # Files: one, per board, or per value of a custom field.
    def file_key(p: _Piece):
        if profile.split == "board":
            return (p.line.core or "", p.line.thickness)
        if profile.split.startswith("field:"):
            return p.fields.get(profile.split[6:], "")
        return ""

    groups: dict = {}
    for p in pieces:
        groups.setdefault(file_key(p), []).append(p)

    visible = [c for c in profile.columns if not c.hidden]
    header = [c.header for c in visible] if profile.header else None
    used_names: set[str] = set()

    for key, group in groups.items():
        # Rows: merged (one per cut-list line within this file) or per piece.
        if profile.rows == "per_piece":
            units = [[p] for p in group]
        else:
            by_line: dict = {}
            for p in group:
                by_line.setdefault(id(p.line), []).append(p)
            units = list(by_line.values())
        f = OutFile(_file_name(profile, key, group, context, used_names),
                    header)
        for unit in units:
            f.rows.append([_cell(c, unit, profile, library, context, problem)
                           for c in visible])
        out.files.append(f)

    out.problems = list(problems.values())
    return out


def _file_name(profile: Profile, key, group, context, used: set) -> str:
    values = dict(context)
    first = group[0] if group else None
    if first is not None:
        values["material"] = first.line.core or ""
        values["thickness"] = format_length(first.line.thickness,
                                            profile.numbers).text
        values.update(first.fields)
    if profile.split.startswith("field:"):
        values["value"] = str(key)
    stem = safe_stem(fill(profile.filename or "{model}", values))
    ext = safe_stem(profile.extension.lstrip(".")) or "csv"
    name = f"{stem}.{ext}"
    n = 2
    while name.lower() in used:
        name = f"{stem}_({n}).{ext}"
        n += 1
    used.add(name.lower())
    return name


def _cell(col: Column, unit: list[_Piece], profile: Profile,
          library: Library, context: dict, problem) -> Cell:
    """A column's value, tidied and with its text options applied."""
    cell = _raw_cell(col, unit, profile, library, context, problem)
    text = apply_text(tidy(cell.text), col.text)
    return cell if text == cell.text else Cell(text, cell.number)


def _raw_cell(col: Column, unit: list[_Piece], profile: Profile,
              library: Library, context: dict, problem) -> Cell:
    if col.kind == "text":
        return Cell(col.value)
    first = unit[0]
    if col.kind == "template":
        # Only the placeholders the template uses: a template that never
        # mentions a supplier code must not report one as missing.
        values: dict = {}
        for name in placeholders(col.value):
            if name in FIELDS:
                got = _values(unit, profile, library, context, problem,
                              numbers=col.numbers or profile.numbers,
                              only=name, yes=col.yes, no=col.no)
                values[name] = got.get(name, Cell("")).text
            elif name in first.fields:
                values[name] = str(first.fields[name])
            elif name in context:
                values[name] = str(context[name])
        return Cell(fill(col.value, values))
    values = _values(unit, profile, library, context, problem,
                     numbers=col.numbers or profile.numbers,
                     only=col.value, yes=col.yes, no=col.no)
    if col.value in values:
        return values[col.value]
    if col.value.startswith("field:"):
        return Cell(first.fields.get(col.value[6:], ""))
    return Cell("")


def _values(unit, profile, library, context, problem, *, numbers,
            only=None, yes="1", no="0") -> dict:
    """The value of field ``only`` — or, with ``only=None``, of every
    field (for previews and tests)."""
    first = unit[0]
    part, line = first.part, first.line
    grain = effective_grain(part, library)
    swapped = profile.grain_first and grain == "width"
    length, width = (line.width, line.length) if swapped else \
        (line.length, line.width)
    bands = _bands(part, swapped)
    want = (lambda k: True) if only is None else (lambda k: k == only)
    v: dict = {}

    def put(key, cell):
        if want(key):
            v[key] = cell

    if want("qty"):
        put("qty", Cell(str(len(unit)), float(len(unit))))
    for key, metres in (("length", length), ("width", width),
                        ("thickness", line.thickness)):
        if want(key):
            put(key, format_length(metres, numbers))
    if want("name"):
        names = _unique(p.part.name for p in unit)
        names.sort(key=_natural)
        put("name", Cell(" / ".join(names)))
    put("number", Cell(str(first.line_no), float(first.line_no)))
    put("material", Cell(line.core or ""))
    for key, sub in (("material_code", "code"),
                     ("material_supplier", "supplier")):
        if want(key):
            entry = profile.material_codes.get(line.core or "", {})
            text = entry.get(sub, "")
            if not text:
                problem(key, line.core or "")
            put(key, Cell(text))
    for edge in ("c1", "c2", "l1", "l2"):
        band = bands[edge]
        put(f"band_{edge}", Cell(band or ""))
        put(f"band_{edge}_flag", Cell(yes if band else no))
        if want(f"band_{edge}_code"):
            text = ""
            if band:
                text = profile.band_codes.get(band, {}).get("code", "")
                if not text:
                    problem("band_code", band)
            put(f"band_{edge}_code", Cell(text))
    rotate = grain == "none" or part.can_rotate is True
    put("grain", Cell(yes if grain != "none" else no))
    put("rotate", Cell(yes if rotate else no))
    put("note", Cell(" / ".join(_unique(p.part.note for p in unit))))
    put("tag", Cell(" / ".join(_unique(p.part.tag for p in unit))))
    put("model", Cell(str(context.get("model", ""))))
    put("face1", Cell(part.face1 or ""))
    put("face2", Cell(part.face2 or ""))
    if only is None:
        for k, val in context.items():
            v.setdefault(k, Cell(str(val)))
        for k, val in first.fields.items():
            v.setdefault(k, Cell(str(val)))
    return v


__all__ = ["Cell", "Export", "OutFile", "Problem", "effective_grain",
           "fill", "format_length", "make_rows", "number_value",
           "FLAG_FIELDS", "LENGTH_FIELDS"]
