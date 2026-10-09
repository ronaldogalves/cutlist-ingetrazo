# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Ronaldo Alves and CutList contributors.
"""Rows to bytes: delimited text, Excel ``.xlsx``, clipboard text (D-009).

"CSV" is not one format: separator, encoding, line endings, quoting, a
separator after the last field, a header or not — each supplier wants its
own, and getting one wrong is what sends people to a spreadsheet to fix
files by hand. Every one of those is the profile's to choose here.

``.xlsx`` is written with ``zipfile`` and plain XML: the smallest workbook
Excel, LibreOffice and web importers accept — no dependency (CLAUDE.md).
"""
from __future__ import annotations

import io
import zipfile
from xml.sax.saxutils import escape

from .profile import NEWLINES, Profile
from .rows import Cell, OutFile, Problem


def _quote(text: str, profile: Profile) -> str:
    sep = profile.separator
    needs = (sep and sep in text) or '"' in text or "\n" in text \
        or "\r" in text
    if profile.quoting == "all" or (profile.quoting == "minimal" and needs):
        return '"' + text.replace('"', '""') + '"'
    return text


def text_lines(f: OutFile, profile: Profile) -> list[str]:
    """The lines of a delimited file, before encoding."""
    lines = []
    rows = ([[Cell(h) for h in f.header]] if f.header is not None else []) \
        + f.rows
    for row in rows:
        line = profile.separator.join(_quote(c.text, profile) for c in row)
        if profile.trailing_separator:
            line += profile.separator
        lines.append(line)
    return lines


def unencodable(f: OutFile, profile: Profile) -> list[Problem]:
    """Characters this encoding cannot hold (a "≥" in a part name, in a
    Windows-1252 file): reported, never replaced silently."""
    bad: dict[str, Problem] = {}
    for line in text_lines(f, profile):
        for ch in line:
            try:
                ch.encode(profile.encoding)
            except UnicodeEncodeError:
                if ch in bad:
                    bad[ch].count += 1
                else:
                    bad[ch] = Problem("encoding", ch)
    return list(bad.values())


def text_bytes(f: OutFile, profile: Profile) -> bytes:
    newline = NEWLINES.get(profile.newline, "\r\n")
    text = newline.join(text_lines(f, profile)) + newline
    return text.encode(profile.encoding)


def clipboard_text(files: list[OutFile], profile: Profile) -> str:
    """Tab-separated text for pasting into a spreadsheet or a web form:
    one header (if the profile has one), then every row of every file."""
    rows: list[list[str]] = []
    if files and files[0].header is not None:
        rows.append(list(files[0].header))
    for f in files:
        rows.extend([c.text.replace("\t", " ").replace("\n", " ")
                     for c in row] for row in f.rows)
    return "\n".join("\t".join(r) for r in rows) + "\n"


# ---------------------------------------------------------------------------
# .xlsx
# ---------------------------------------------------------------------------

def _col_name(i: int) -> str:
    name = ""
    i += 1
    while i:
        i, r = divmod(i - 1, 26)
        name = chr(65 + r) + name
    return name


def xlsx_bytes(f: OutFile, sheet: str = "Cut list",
               numbers_as_numbers: bool = True) -> bytes:
    """A one-sheet workbook. Lengths and quantities are real numbers (so a
    spreadsheet can sum them) unless ``numbers_as_numbers`` is False."""
    rows = ([[Cell(h) for h in f.header]] if f.header is not None else []) \
        + f.rows
    xml_rows = []
    for r, row in enumerate(rows, start=1):
        cells = []
        for c, cell in enumerate(row):
            ref = f"{_col_name(c)}{r}"
            if numbers_as_numbers and cell.number is not None:
                cells.append(f'<c r="{ref}"><v>{cell.number:g}</v></c>')
            elif cell.text:
                cells.append(f'<c r="{ref}" t="inlineStr"><is><t xml:space='
                             f'"preserve">{escape(cell.text)}</t></is></c>')
        xml_rows.append(f'<row r="{r}">{"".join(cells)}</row>')
    sheet_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/'
        'spreadsheetml/2006/main"><sheetData>'
        + "".join(xml_rows) + "</sheetData></worksheet>")
    parts = {
        "[Content_Types].xml": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/'
            'content-types"><Default Extension="rels" ContentType="'
            'application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/'
            'vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"'
            '/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="'
            'application/vnd.openxmlformats-officedocument.spreadsheetml.'
            'worksheet+xml"/></Types>'),
        "_rels/.rels": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/'
            '2006/relationships"><Relationship Id="rId1" Type="http://'
            'schemas.openxmlformats.org/officeDocument/2006/relationships/'
            'officeDocument" Target="xl/workbook.xml"/></Relationships>'),
        "xl/workbook.xml": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml'
            '/2006/main" xmlns:r="http://schemas.openxmlformats.org/'
            'officeDocument/2006/relationships"><sheets><sheet name="'
            + escape(sheet[:31], {'"': "&quot;"}) +
            '" sheetId="1" r:id="rId1"/></sheets></workbook>'),
        "xl/_rels/workbook.xml.rels": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/'
            '2006/relationships"><Relationship Id="rId1" Type="http://'
            'schemas.openxmlformats.org/officeDocument/2006/relationships/'
            'worksheet" Target="worksheets/sheet1.xml"/></Relationships>'),
        "xl/worksheets/sheet1.xml": sheet_xml,
    }
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, xml in parts.items():
            z.writestr(name, xml.encode("utf-8"))
    return buf.getvalue()


def file_bytes(f: OutFile, profile: Profile) -> bytes:
    if profile.format == "xlsx":
        return xlsx_bytes(f)
    return text_bytes(f, profile)
