# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Ronaldo Alves and CutList contributors.
"""A plan page as SVG, with the stdlib only: IngeTrazo builds are not sure
to ship QtSvg (CLAUDE.md). Millimetres in, millimetres out."""
from __future__ import annotations

from xml.sax.saxutils import escape

from .plan import PAGES, STYLES, Page

_ANCHOR = {"left": "start", "center": "middle", "right": "end"}


def _n(v: float) -> str:
    return f"{v:.2f}".rstrip("0").rstrip(".")


def page_svg(page: Page, size: str = "A4") -> str:
    pw, ph = PAGES.get(size, PAGES["A4"])
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" '
           f'width="{_n(pw)}mm" height="{_n(ph)}mm" '
           f'viewBox="0 0 {_n(pw)} {_n(ph)}" '
           f'font-family="Segoe UI, Arial, Helvetica, sans-serif">',
           f'<rect width="{_n(pw)}" height="{_n(ph)}" fill="#ffffff"/>']
    for s in page.shapes:
        st = STYLES.get(s.style, {})
        if s.kind == "rect":
            out.append(f'<rect x="{_n(s.x)}" y="{_n(s.y)}" '
                       f'width="{_n(s.w)}" height="{_n(s.h)}" '
                       f'fill="{st.get("fill", "none")}" '
                       f'stroke="{st.get("stroke", "none")}" '
                       f'stroke-width="{_n(st.get("width", 0.2))}"/>')
        elif s.kind == "line":
            out.append(f'<line x1="{_n(s.x)}" y1="{_n(s.y)}" '
                       f'x2="{_n(s.x + s.w)}" y2="{_n(s.y + s.h)}" '
                       f'stroke="{st.get("stroke", "#000")}" '
                       f'stroke-width="{_n(st.get("width", 0.2))}"/>')
            if s.style == "grain":
                tip = s.x + s.w
                out.append(f'<path d="M{_n(tip)} {_n(s.y)} l-2 -1 v2 z" '
                           f'fill="{st.get("stroke", "#000")}"/>')
        elif s.kind == "text" and s.text:
            x = {"left": s.x, "center": s.x + s.w / 2,
                 "right": s.x + s.w}[s.align]
            y = s.y + s.h / 2 + s.size * 0.35
            weight = ' font-weight="bold"' if st.get("bold") else ""
            out.append(f'<text x="{_n(x)}" y="{_n(y)}" '
                       f'font-size="{_n(s.size)}" '
                       f'text-anchor="{_ANCHOR[s.align]}" '
                       f'fill="{st.get("color", "#000")}"{weight}>'
                       f'{escape(s.text)}</text>')
    out.append("</svg>")
    return "\n".join(out) + "\n"
