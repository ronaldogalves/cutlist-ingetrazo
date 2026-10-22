# Cut List for IngeTrazo

*Working name.* An extension for [IngeTrazo](https://github.com/ingelibre/ingetrazo),
the free push-pull 3D modeler, that turns a furniture model into a **cut
list** (every part with its size, material and quantity) and **cutting
diagrams** (how the parts fit on the stock sheets you will buy, with kerf
and trim accounted for), with CSV, SVG and PDF exports.

Free software under the GPL-3.0-or-later. English, Português (Brasil) and
Español from the start.

![A cutting diagram: one 2750 × 1840 sheet, parts lettered with their
sizes, leftovers faded with theirs](docs/images/cutting-diagram.png)

## Status

**0.1.0 — the cut list, supplier exports and cutting diagrams.** What
is in it (see [CHANGELOG.md](CHANGELOG.md)):

- a **Cut List** tab that reads the selection or the whole model and
  groups parts by board and thickness, merging identical parts by
  measurement; flags what needs a look (non-rectangular parts, boards
  merged into one group, materials not set up) instead of guessing;
- **materials with roles** (board, laminate/veneer, edge band,
  appearance only, ignore), read face by face and edge by edge from the
  way the model is painted;
- **part settings** (grain, may rotate, exclude, note, face 1, custom
  fields such as client or room), each change one undo step;
- **exports** through named profiles you build once per supplier or
  workflow: CSV/TXT with every option suppliers differ on, Excel `.xlsx`,
  or the clipboard; grain-first sizes, supplier codes, live preview.
  Ready profiles for **CorteCloud** and **Leo Madeiras**, both checked
  against files the supplier accepted — profiles for other suppliers are
  welcome;
- **cutting diagrams** for a panel or table saw: guillotine cuts in 2–4
  stages, kerf, trim, grain, first cuts lengthwise or crosswise, several
  sheet sizes, leftovers from the shop used first. Hover a part for the
  cuts that free it and their fence distances; right-click it to switch
  its grain and lay out again. Printed as PDF or SVG: a page per sheet,
  part letters and sizes, identical sheets once, "Page n of N". Layouts
  can be saved in the model;
- English, Português (Brasil) and Español.

See [docs/ROADMAP.md](docs/ROADMAP.md) and [docs/BRIEF.md](docs/BRIEF.md).

**Known limitations**

- Solid wood is listed but not laid out (1D diagrams come later), and
  CNC nesting (free placement) is not there yet: the layouts are for a
  saw.
- Tested on Windows with the installed IngeTrazo; on Linux by the test
  suite only.

- Dragging columns in the export window shows a line where the row will
  land, but the other rows do not slide apart yet; Move up / Move down
  are there too.
- `.skp` files arrive in IngeTrazo without their group hierarchy (an
  IngeTrazo import limitation): tag the boards, or check the "several
  solids" warnings.
- In a `.skp` import, SketchUp's groups and components do not stay apart
  (some components arrive as plain groups and the other way round), so
  "components only" cannot leave out a fridge or a wall modelled as a
  group. They land under *Needs a look* (no material): exclude them
  there, or paint them with a material set to *Ignore*.

Tested with **IngeTrazo 0.5.9**.

## User guide

How to model, set up materials, export to a supplier and print cutting
diagrams: [English](docs/user-guide.md) ·
[Português (Brasil)](docs/user-guide.pt-BR.md) ·
[Español](docs/user-guide.es.md).

## Installing

1. Download `cutlist-0.1.0.zip` from the
   [Releases](https://github.com/ronaldogalves/cutlist-ingetrazo/releases)
   page.
2. In IngeTrazo, **Extensions ▸ Open plugins folder**
   (Windows: `%APPDATA%\ingetrazo\plugins\`, Linux:
   `~/.local/share/ingetrazo/plugins/`).
3. Unzip there, so the folder holds `cutlist\__init__.py`.
4. Restart IngeTrazo: *Cut List* appears in the Extensions menu and as a
   tab in the side tray.

To work on the code, link the `cutlist/` folder of a checkout into the
plugins folder instead; see the development setup in
[CLAUDE.md](CLAUDE.md). `python tools/build_release.py` builds the zip.

## Relationship to OpenCutList

[OpenCutList](https://github.com/lairdubois/lairdubois-opencutlist-sketchup-extension)
for SketchUp is our benchmark for features and output quality. This is
an independent implementation built on IngeTrazo's own architecture, not
a port.

## License

GPL-3.0-or-later — see [LICENSE](LICENSE).
