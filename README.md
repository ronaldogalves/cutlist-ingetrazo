# Cut List for IngeTrazo

*Working name.* An extension for [IngeTrazo](https://github.com/ingelibre/ingetrazo),
the free push-pull 3D modeler, that turns a furniture model into a **cut
list** (every part with its size, material and quantity) and **cutting
diagrams** (how the parts fit on the stock sheets you will buy, with kerf
and trim accounted for), with CSV, SVG and PDF exports.

Free software under the GPL-3.0-or-later. English, Português (Brasil) and
Español from the start.

## Status

**Early development, not usable yet.** We are at milestone M0
(foundations): the extension loads and shows an empty *Cut List* tab. See
[docs/ROADMAP.md](docs/ROADMAP.md) for what comes next and
[docs/BRIEF.md](docs/BRIEF.md) for the goals and the scope of v0.1.

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
