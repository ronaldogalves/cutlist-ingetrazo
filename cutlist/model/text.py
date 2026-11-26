# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Ronaldo Alves and CutList contributors.
"""Lengths typed in dialogs: ``"15; 18"``, ``"3,5"``, ``"23 9/16\""``.

Dialogs show sizes in millimetres in a metric model and in inches in an
imperial one (issue #1): small numbers people type by hand. These helpers
read them forgivingly — comma or dot for decimals, ``;`` or new lines
between items (``/`` too in millimetres; in inches it makes a fraction),
and a unit typed by hand always wins (``18mm`` in an inch model, ``3/4"``
or ``8'`` in a metric one) — and write them back the same way. Sheet
sizes are typed in a table (``ui.dialogs.SheetsEditor``), not here.

The unit comes from the host (:func:`set_unit_source`), the way
:mod:`..i18n` gets the language: this module stays pure.
"""
from __future__ import annotations

import re
from collections.abc import Callable

MM = 0.001
INCH = 0.0254
FOOT = 0.3048

_ITEM_SPLIT = re.compile(r"[;/\n|]+")
#: In inches ``/`` belongs to fractions: items split on ``;`` and lines.
_ITEM_SPLIT_INCH = re.compile(r"[;\n|]+")
_METRIC = {"mm": MM, "cm": 0.01, "m": 1.0}
#: 18, 3.5, 3,5, 3/4, 1 1/2, 1-1/2.
_AMOUNT = re.compile(r"^(?:(\d+(?:[.,]\d+)?)(?:[ -]+(\d+)/(\d+))?|(\d+)/(\d+))$")


def _mm_unit() -> str:
    return "mm"


_unit_source: Callable[[], str] = _mm_unit


def set_unit_source(fn: Callable[[], str] | None) -> None:
    """``fn()`` → ``"mm"`` or ``"in"``: the unit dialogs type sizes in.
    ``None`` puts millimetres back."""
    global _unit_source
    _unit_source = fn or _mm_unit


def input_unit() -> str:
    """``"in"`` or ``"mm"``; a host that fails is read as millimetres."""
    try:
        return "in" if _unit_source() == "in" else "mm"
    except Exception:                                # noqa: BLE001
        return "mm"


def _default_unit() -> float:
    return INCH if input_unit() == "in" else MM


def tidy(text: str) -> str:
    """Spaces trimmed at both ends and runs of spaces made one — always
    (D-010): an invisible trailing space is the classic reason a name
    "does not match" (model D: "GAB MONT INT " beside "GAB MONT INT"),
    and nobody types one on purpose."""
    return re.sub(r"[ \t]{2,}", " ", (text or "").strip())


def parse_number(text: str) -> float | None:
    """``"3,5"`` → 3.5; ``""`` → None; anything else unreadable → None."""
    t = (text or "").strip().replace(",", ".")
    if not t:
        return None
    try:
        v = float(t)
    except ValueError:
        return None
    return v if v >= 0 else None


def _amount(text: str) -> float | None:
    """18, 3,5, 3/4, 1 1/2 or 1-1/2 → a number; None when unreadable."""
    m = _AMOUNT.match(text.strip())
    if not m:
        return None
    whole, num, den, fnum, fden = m.groups()
    if fnum is not None:
        whole, num, den = "0", fnum, fden
    value = float(whole.replace(",", "."))
    if num is not None:
        if int(den) == 0:
            return None
        value += int(num) / int(den)
    return value


def parse_length(text: str, unit: float | None = None) -> float | None:
    """A length in metres. Bare numbers are in ``unit`` (by default the
    dialogs' unit: millimetres, or inches in an imperial model); a unit
    typed by hand wins: ``18mm``, ``1.8 cm``, ``3/4"``, ``8'``,
    ``4' 1/2"``, ``2 in``, ``1 ft``."""
    t = (text or "").strip().lower().replace("″", '"').replace("′", "'")
    if not t:
        return None
    unit = _default_unit() if unit is None else unit
    m = re.fullmatch(r"(.+?)\s*(mm|cm|m)", t)
    if m:
        v = parse_number(m.group(1))
        return None if v is None else v * _METRIC[m.group(2)]
    m = re.fullmatch(r"(.+?)\s*(?:'|ft)\s*-?\s*(.*)", t)
    if m:                                           # feet, maybe inches
        feet = _amount(m.group(1))
        rest = re.sub(r'\s*(?:"|in)$', "", m.group(2)).strip()
        inches = _amount(rest) if rest else 0.0
        if feet is None or inches is None:
            return None
        return feet * FOOT + inches * INCH
    m = re.fullmatch(r'(.+?)\s*(?:"|in|\'\')', t)
    if m:
        v = _amount(m.group(1))
        return None if v is None else v * INCH
    v = _amount(t)
    return None if v is None else v * unit


def parse_lengths(text: str, unit: float | None = None) -> tuple[float, ...]:
    """``"15; 18"`` → (0.015, 0.018); ``"3/4; 1/2"`` in inches; unreadable
    items are skipped."""
    inches = (unit or _default_unit()) == INCH
    out = []
    for item in (_ITEM_SPLIT_INCH if inches else _ITEM_SPLIT).split(
            text or ""):
        v = parse_length(item, unit)
        if v:
            out.append(v)
    return tuple(out)


def fmt_number(value: float) -> str:
    """3.5 → "3.5"; 18.0 → "18" (no trailing zeros)."""
    text = f"{value:.4f}".rstrip("0").rstrip(".")
    return text or "0"


def _fmt_inches(inches: float) -> str:
    """0.75 → "3/4", 18.5 → "18 1/2" when on a 1/64 step; else a
    decimal (a 3 mm kerf is "0.1181")."""
    steps = round(inches * 64)
    if abs(inches * 64 - steps) > 1e-3:
        return fmt_number(inches)
    whole, part = divmod(steps, 64)
    if not part:
        return str(whole)
    den = 64
    while part % 2 == 0:
        part, den = part // 2, den // 2
    return f"{whole} {part}/{den}" if whole else f"{part}/{den}"


def fmt_length(value: float | None, unit: float | None = None) -> str:
    """Written back as it is typed: millimetres, or inches with
    fractions in an imperial model."""
    if value is None:
        return ""
    unit = _default_unit() if unit is None else unit
    if unit == INCH:
        return _fmt_inches(value / INCH)
    return fmt_number(value / unit)


def fmt_lengths(values, unit: float | None = None) -> str:
    return "; ".join(fmt_length(v, unit) for v in values)


def with_unit(title: str) -> str:
    """``"Kerf"`` → ``"Kerf (mm)"`` or ``"Kerf (in)"``: the unit the box
    takes. ``title`` is already translated."""
    from ..i18n import tr
    return tr("{title} ({unit})", title=title, unit=input_unit())
