# Changelog

## Unreleased

**Edge bands** (D-017).

- An **Edge bands** section in the Cut List panel: metres of each band to
  buy, the number of banded edges, rolls when the band has a roll length.
- A band's **oversize per edge** (the overhang trimmed after gluing) and
  **waste %** are added to the total; both start at 0.
- A band can have a **width** and a **room to finish it** (2 mm by
  default): a part too thick for its band is flagged "band too narrow" —
  a 22 mm band fits up to 20 mm.
- "Cut the board shorter by the band thickness" now works, per band: the
  saw gets the smaller size, the list keeps the finished one and shows
  "cut −0.9 / −0.9".
- Exports can add a file with the edge bands to buy; the printed plan's
  totals page lists them.

## 0.1.0 — 2026-10-21

**Cutting diagrams** (M2–M3).

- **Diagrams…** lays every board out on its sheets: guillotine cuts as a
  panel or table saw makes them (2, 3 or 4 stages), blade kerf, trim on
  four or two edges, grain kept, first cuts lengthwise, crosswise or the
  better of both, several sheet sizes, leftovers from the shop used
  first. On Cozinha 03 it needs the same sheets as OpenCutList.
- The sheets answer the mouse: a part shows the cuts that free it with
  their fence distances; a cut shows its stage, fence and length.
- Right-click a part to switch its grain, allow rotation, change its
  settings or leave it out; the layout is redone for the same parts.
- The printed plan (PDF, or SVG pages): a page per sheet with letters and
  sizes, the parts table, identical sheets once "×3", "Page n of N" on
  every page, Large or Compact text, an optional totals page.
- Layouts can be saved in the model and reopened exactly as they were,
  with what changed since.
- Part letters A, B… AA in the cut list and on the diagrams.
- Materials: sheet sizes in a table, sizes for some thicknesses only,
  size templates applied to several materials at once, oversize per
  board. Parts: their own oversize; the list shows "cut +20 / +5", the
  saw gets the cut size, exports choose finished or cut size.
- A part not as thick as its board comes is flagged.
- Save windows open in the model's folder, the last one used, or
  Documents — never IngeTrazo's program folder.

## 0.0.1 — pre-release, 2026-10-20

The first public version: the **cut list and its exports**. Cutting
diagrams come later (M2–M3). For woodworkers who order pre-cut boards,
the supplier makes the cutting plan, so this is already the whole job.

Tested with IngeTrazo 0.5.9 on Windows.

- **Cut List tab**: the parts of the selection or the whole model,
  grouped by board and thickness, identical parts merged by measurement.
  Unnamed groups show as "Group #n", and keep that number.
- **Needs a look**: parts that are not rectangular, several boards merged
  into one group, parts with no material, finishes not set up yet, and
  parts not as thick as their board comes (when the board's thicknesses
  are set up). Nothing is dropped silently.
- **Materials** with roles: board, laminate/veneer, edge band, appearance
  only, ignore. Read face by face and edge by edge from how the model is
  painted. Set up once in your library, or for one model only.
- **Part settings**: grain, may rotate, exclude, note, face 1, and custom
  fields such as client or room. Each change is one undo step.
- **Exports** through named profiles: CSV/TXT with every option suppliers
  differ on (separator, encoding, line endings, quotes, header, rounding,
  decimal comma), Excel `.xlsx`, or the clipboard. One file per board or
  per custom field, boards left out per export, live preview, and safe
  file names.
- **Profiles that ship**: Simple CSV, **CorteCloud** (paste from Excel)
  and **Leo Madeiras** (web import). Both supplier layouts were accepted
  by the supplier's site, edge bands included. Import several profiles
  at once, export one to share it.
- English, Português (Brasil) and Español.

Known limitations: see the README.
