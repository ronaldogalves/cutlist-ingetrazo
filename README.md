# Cut List for IngeTrazo

*Working name.* An extension for [IngeTrazo](https://github.com/ingelibre/ingetrazo),
the free push-pull 3D modeler, that turns a furniture model into a **cut
list** (every part with its size, material and quantity) and **cutting
diagrams** (how the parts fit on the stock sheets you will buy, with kerf
and trim accounted for), with CSV, SVG and PDF exports.

Free software under the GPL-3.0-or-later. English, Português (Brasil) and
Español from the start.

## Status

**Early development — the cut list works, cutting diagrams do not exist
yet.** No release has been published; to try it, follow *Trying it*
below. Milestone M1 (the cut list) is built:

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
  or the clipboard; grain-first sizes, supplier codes, live preview;
- English, Português (Brasil) and Español.

Next: cutting diagrams (M2–M3). See [docs/ROADMAP.md](docs/ROADMAP.md)
and [docs/BRIEF.md](docs/BRIEF.md).

**Known limitations**

- Dragging columns in the export window works but the drop position can
  be unclear; Move up / Move down are exact.
- `.skp` files arrive in IngeTrazo without their group hierarchy (an
  IngeTrazo import limitation): tag the boards, or check the "several
  solids" warnings.

Tested with **IngeTrazo 0.5.7**.

## Trying it (developers)

The `cutlist/` folder is the extension. IngeTrazo loads it from its
per-user plugins folder:

- Windows: `%APPDATA%\ingetrazo\plugins\`
- Linux: `~/.local/share/ingetrazo/plugins/`

(**Extensions ▸ Open plugins folder** in IngeTrazo opens it.) Copy or link
`cutlist/` there and restart IngeTrazo: *Cut List* appears in the
Extensions menu and as a tab in the side tray.

To work on the code, see the development setup in [CLAUDE.md](CLAUDE.md).

## Relationship to OpenCutList

[OpenCutList](https://github.com/lairdubois/lairdubois-opencutlist-sketchup-extension)
for SketchUp is our benchmark for features and output quality. This is
an independent implementation built on IngeTrazo's own architecture, not
a port.

## License

GPL-3.0-or-later — see [LICENSE](LICENSE).
