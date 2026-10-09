# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Ronaldo Alves and CutList contributors.
"""An export profile: every rule for one output, under the user's name.

A profile is plain data (dataclasses ↔ JSON-safe dicts): it is stored in
the user's defaults, exported to a file and shared. It holds **no code**
(D-009): columns are fields, fixed text or fill-in templates.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields, replace

#: What a column can show. Lengths are written with the number options;
#: ``*_code``/``*_supplier`` go through the profile's code table; yes/no
#: fields use the column's yes/no words. Bands are named looking at face 1,
#: grain first: C1/C2 along the "comprimento", L1/L2 along the "largura".
FIELDS = (
    "qty", "length", "width", "thickness", "name", "number",
    "material", "material_code", "material_supplier",
    "band_c1", "band_c2", "band_l1", "band_l2",
    "band_c1_code", "band_c2_code", "band_l1_code", "band_l2_code",
    "band_c1_flag", "band_c2_flag", "band_l1_flag", "band_l2_flag",
    "grain", "rotate", "note", "tag", "model", "face1", "face2",
)
LENGTH_FIELDS = ("length", "width", "thickness")
#: Text options a column can apply, in this order: accents removed,
#: UPPERCASE, spaces → underscores (for systems that want them).
TEXT_OPTIONS = ("ascii", "upper", "underscores")

FLAG_FIELDS = ("grain", "rotate", "band_c1_flag", "band_c2_flag",
               "band_l1_flag", "band_l2_flag")

#: Encodings offered: Excel-friendly UTF-8 (BOM), plain UTF-8, and the
#: Windows code page older supplier systems expect.
ENCODINGS = ("utf-8", "utf-8-sig", "cp1252")
NEWLINES = {"crlf": "\r\n", "lf": "\n"}


@dataclass(frozen=True)
class Numbers:
    """How a length is written. Whole millimetres by default: no supplier
    takes fractions of a millimetre."""

    unit: str = "mm"                    # mm, cm, m, in
    decimals: int = 0
    decimal_sep: str = ","
    rounding: str = "nearest"           # nearest, up, down
    strip_zeros: bool = True            # 18,50 → 18,5
    suffix: bool = False                # "600 mm"


@dataclass(frozen=True)
class Column:
    header: str = ""
    kind: str = "field"                 # field, text, template
    value: str = ""                     # field name, fixed text or template
    hidden: bool = False
    numbers: Numbers | None = None      # None: the profile's
    yes: str = "1"
    no: str = "0"
    #: Any of :data:`TEXT_OPTIONS`.
    text: tuple[str, ...] = ()


@dataclass(frozen=True)
class Profile:
    name: str = "Simple CSV"
    format: str = "text"                # text, xlsx, clipboard
    extension: str = "csv"
    separator: str = ";"
    encoding: str = "utf-8-sig"
    newline: str = "crlf"
    quoting: str = "minimal"            # minimal, all, none
    trailing_separator: bool = False
    header: bool = True
    rows: str = "merged"                # merged, per_piece
    split: str = "none"                 # none, board, field:<name>
    filename: str = "{model}"
    #: Materials to export (empty: every board).
    materials: tuple[str, ...] = ()
    grain_first: bool = True
    numbers: Numbers = field(default_factory=Numbers)
    columns: tuple[Column, ...] = ()
    #: name → {"code": …, "supplier": …} for materials and bands.
    material_codes: dict = field(default_factory=dict)
    band_codes: dict = field(default_factory=dict)

    # ---- (de)serialisation ------------------------------------------------
    def to_dict(self) -> dict:
        d = asdict(self)
        d["materials"] = list(self.materials)
        for c in d["columns"]:
            c["text"] = list(c["text"])
        d["schema"] = 1
        return d

    @classmethod
    def from_dict(cls, d) -> Profile:
        """Lenient: unknown keys ignored, bad values fall back."""
        if not isinstance(d, dict):
            return cls()
        base = cls()
        kw: dict = {}
        for f in fields(cls):
            if f.name not in d:
                continue
            v = d[f.name]
            default = getattr(base, f.name)
            if f.name == "numbers":
                kw[f.name] = _numbers(v) or default
            elif f.name == "columns":
                kw[f.name] = tuple(c for c in (_column(x) for x in v or ())
                                   if c is not None)
            elif f.name == "materials":
                kw[f.name] = tuple(str(m) for m in v or ())
            elif f.name in ("material_codes", "band_codes"):
                kw[f.name] = _codes(v)
            elif isinstance(default, bool):
                kw[f.name] = bool(v)
            elif isinstance(default, str):
                kw[f.name] = str(v)
        p = replace(base, **kw)
        if p.encoding not in ENCODINGS:
            p = replace(p, encoding=base.encoding)
        if p.newline not in NEWLINES:
            p = replace(p, newline=base.newline)
        return p


def _numbers(d) -> Numbers | None:
    if not isinstance(d, dict):
        return None
    n = Numbers()
    try:
        return replace(
            n, unit=str(d.get("unit", n.unit)),
            decimals=max(0, min(6, int(d.get("decimals", n.decimals)))),
            decimal_sep=str(d.get("decimal_sep", n.decimal_sep))[:1] or ",",
            rounding=d.get("rounding") if d.get("rounding") in
            ("nearest", "up", "down") else n.rounding,
            strip_zeros=bool(d.get("strip_zeros", n.strip_zeros)),
            suffix=bool(d.get("suffix", n.suffix)))
    except (TypeError, ValueError):
        return n


def _column(d) -> Column | None:
    if not isinstance(d, dict):
        return None
    kind = d.get("kind", "field")
    if kind not in ("field", "text", "template"):
        return None
    return Column(header=str(d.get("header", "")), kind=kind,
                  value=str(d.get("value", "")),
                  hidden=bool(d.get("hidden", False)),
                  numbers=_numbers(d.get("numbers")),
                  yes=str(d.get("yes", "1")), no=str(d.get("no", "0")),
                  text=tuple(t for t in TEXT_OPTIONS
                             if t in (d.get("text") or ())))


def _codes(d) -> dict:
    out = {}
    for name, v in (d or {}).items() if isinstance(d, dict) else ():
        if isinstance(v, dict):
            out[str(name)] = {"code": str(v.get("code", "")),
                              "supplier": str(v.get("supplier", ""))}
        elif isinstance(v, str):
            out[str(name)] = {"code": v, "supplier": ""}
    return out


def generic() -> Profile:
    """The one profile that ships: a plain, readable cut list."""
    f = Column
    return Profile(columns=(
        f("Qty", value="qty"), f("Name", value="name"),
        f("Length", value="length"), f("Width", value="width"),
        f("Thickness", value="thickness"), f("Material", value="material"),
        f("Band L1", value="band_c1"), f("Band L2", value="band_c2"),
        f("Band W1", value="band_l1"), f("Band W2", value="band_l2"),
        f("Note", value="note"),
    ))
