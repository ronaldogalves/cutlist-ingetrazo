# Changelog

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
