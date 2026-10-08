# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Ronaldo Alves and CutList contributors.
"""Lengths typed in dialogs: ``"15; 18"``, ``"2750 x 1840"``, ``"3,5"``.

Settings dialogs show board sizes in millimetres (or inches): small
numbers people type by hand. These helpers read them forgivingly — comma
or dot for decimals, ``x``/``×``/``*`` between sheet sides, ``;``, ``/``
or new lines between items — and write them back the same way.
"""
from __future__ import annotations

import re

MM = 0.001
INCH = 0.0254

_ITEM_SPLIT = re.compile(r"[;/\n|]+")
_SIDE_SPLIT = re.compile(r"\s*[x×X*]\s*")


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


def parse_length(text: str, unit: float = MM) -> float | None:
    v = parse_number(text)
    return None if v is None else v * unit


def parse_lengths(text: str, unit: float = MM) -> tuple[float, ...]:
    """``"15; 18"`` → (0.015, 0.018); unreadable items are skipped."""
    out = []
    for item in _ITEM_SPLIT.split(text or ""):
        v = parse_length(item, unit)
        if v:
            out.append(v)
    return tuple(out)


def parse_sheets(text: str, unit: float = MM) -> tuple[tuple[float, float], ...]:
    """``"2750 x 1840; 2440 x 1220"`` → ((2.75, 1.84), (2.44, 1.22)), each
    as (longer, shorter)."""
    out = []
    for item in _ITEM_SPLIT.split(text or ""):
        sides = [s for s in _SIDE_SPLIT.split(item.strip()) if s]
        if len(sides) != 2:
            continue
        a, b = parse_length(sides[0], unit), parse_length(sides[1], unit)
        if a and b:
            out.append((max(a, b), min(a, b)))
    return tuple(out)


def fmt_number(value: float) -> str:
    """3.5 → "3.5"; 18.0 → "18" (no trailing zeros)."""
    text = f"{value:.4f}".rstrip("0").rstrip(".")
    return text or "0"


def fmt_length(value: float | None, unit: float = MM) -> str:
    return "" if value is None else fmt_number(value / unit)


def fmt_lengths(values, unit: float = MM) -> str:
    return "; ".join(fmt_length(v, unit) for v in values)


def fmt_sheets(sheets, unit: float = MM) -> str:
    return "; ".join(f"{fmt_length(a, unit)} x {fmt_length(b, unit)}"
                     for a, b in sheets)
