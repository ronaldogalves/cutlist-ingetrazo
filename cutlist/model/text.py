# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Ronaldo Alves and CutList contributors.
"""Lengths typed in dialogs: ``"15; 18"``, ``"2750 x 1840"``, ``"3,5"``.

Settings dialogs show board sizes in millimetres (or inches): small
numbers people type by hand. These helpers read them forgivingly — comma
or dot for decimals, ``x``/``×``/``*`` between sheet sides, ``;``, ``/``
or new lines between items — and write them back the same way. Sheet
sizes are typed in a table (``ui.dialogs.SheetsEditor``), not here.
"""
from __future__ import annotations

import re

MM = 0.001
INCH = 0.0254

_ITEM_SPLIT = re.compile(r"[;/\n|]+")


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


def fmt_number(value: float) -> str:
    """3.5 → "3.5"; 18.0 → "18" (no trailing zeros)."""
    text = f"{value:.4f}".rstrip("0").rstrip(".")
    return text or "0"


def fmt_length(value: float | None, unit: float = MM) -> str:
    return "" if value is None else fmt_number(value / unit)


def fmt_lengths(values, unit: float = MM) -> str:
    return "; ".join(fmt_length(v, unit) for v in values)
