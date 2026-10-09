# Decisions

Short records of choices that are hard to reverse. Newest last. To change
one, add a new entry that supersedes it; do not edit history.

## D-001 — Build our own; OpenCutList is a benchmark, not a port

*2026-10-06 · accepted*

OpenCutList is ~91k lines of Ruby bound to the SketchUp API (106 files use
`Sketchup::`/`Geom::` types), with a ~21k-line JS/Twig HTML UI that would
need QtWebEngine, which IngeTrazo does not bundle. A port was estimated at
9–12+ person-months with permanent drift on both sides. IngeTrazo already
has part measurement and a basic cut list (`core/parts.py`). We build a
native IngeTrazo extension and use OpenCutList for feature ideas and as a
quality benchmark.

## D-002 — Python + Qt widgets, only IngeTrazo's bundled dependencies

*2026-10-06 · accepted*

Extensions run inside IngeTrazo's bundled Python (Flatpak, AppImage,
installers) and cannot install packages. We use PySide6, NumPy, ezdxf and
the stdlib only. Qt widgets, not HTML.

## D-003 — Own pure-Python guillotine packer first

*2026-10-06 · accepted*

Pure Python/NumPy guillotine packer behind a `Packer` protocol. Easy to
ship (no per-platform native builds), easy to test, matches how panel saws
cut. Quality is measured against OpenCutList on a benchmark set (M2); if it
falls short, OpenCutList's C++ Packy can be added as a second backend via
ctypes without UI changes.

## D-004 — English source with pt-BR and es from day one

*2026-10-06 · accepted*

Code, identifiers and docs in English. UI strings use English as the key
(IngeTrazo's convention) with our own JSON catalogs for pt-BR and es,
following IngeTrazo's current language.

## D-005 — Open source (GPL-3.0-or-later), funded by voluntary donations

*2026-10-06 · accepted*

GPL-3.0-or-later is required in practice (in-process extension importing
GPL modules) and wanted. No paid tier. Donations from v0.2: links opened
on click from a menu entry and the About dialog, optional PIX QR; no
pop-ups, nag screens or telemetry.

## D-006 — Part detection rule

*2026-10-07 · accepted · evidence: `docs/spikes/M0-part-detection.md`*

1. **Scope** — the selection; nothing selected → the whole model. Then a
   **tag filter**: tags to include or exclude, remembered (user default +
   per model). Hidden objects and hidden tags are left out.
2. **A part** is a **leaf container**: a group or component instance with
   faces of its own and no child containers. Containers above it (a
   cabinet group) give it context, not a line.
3. **Groups count.** Plain groups are parts like components. A first-run
   option can restrict to components only; the default includes groups.
4. **Merge by measurement**: parts with the same material, and the same
   L × W × T within the size tolerance (default 1 mm), are one line with a
   quantity — whether they are components, groups or a mix.
5. **A part's materials** are read face by face through material
   **roles** — see D-007. (Not the largest total area, as
   `core.parts.part_material` does: on a thin stick that picks the edge
   material.)
6. **Materials decide the type**: *sheet*, *solid*, or *ignore* (hardware,
   glass, "not cut"). A part on an *ignore* material is left out of the
   cut list but listed in an "Excluded" section with the reason.
7. **Never silent.** Things we cannot classify are listed with a flag:
   - a container with faces of its own **and** child containers
     ("loose geometry beside parts");
   - a part thinner than 0.5 mm (a surface — `core.parts.is_surface`);
   - a part with no material;
   - a part that is not a rectangular board (bounding box used);
   - a part made of several disconnected solids (likely boards merged into
     one group — e.g. untagged boards in a cabinet after a `.skp` import,
     which flattens the hierarchy).
8. **Names**: the part's name from the model; when it has none, or only
   IngeTrazo's automatic `Group N`, it is shown as **"Group #n"**, where *n*
   is our own number, stored in `group.ext["cutlist"]` and so stable across
   saves, shared by the cut list, the diagrams and the 3D highlight.

Rejected: "a part is a direct child of a selected container" (IngeTrazo's
Parts tray rule) — it needs a cabinet container to select, and there
often is none: some designers model flat and organise by tags, and every
`.skp` import arrives flat whatever the designer did (IngeTrazo flattens
the hierarchy on import). Designers' practices vary; the leaf rule works
for flat and nested models alike.

## D-007 — Part anatomy, material roles and size compensation

*2026-10-07 · accepted · from the M0 spike (model D's plywood baguettes)
and Ronaldo's modelling practice*

Woodworkers model the finished **look**, not the bill of materials: one
solid per part, faces painted to show laminate, veneer, edge banding or a
raw edge. Nobody models a 0.5 mm edge band as a solid. The plugin reads
the bill of materials out of that painted model.

1. **Anatomy.** Every sheet part is a **core** (the board that is cut)
   with two **faces** (perpendicular to its thickness) and four **edges**
   (two along its length, two along its width), told apart by the part's
   own axes. **Each edge is banded or raw on its own** — any combination
   of the four, each with its own band material.
2. **Face 1 and face 2.** The two faces are numbered, because supplier
   files, edge-band flags, grain and labels are all read *looking at
   face 1*. Face 1 is the **decorative** face: the face with a face
   covering, or with the more specific finish when the two differ (a
   board decorative on one side, plain white on the other); when both are
   alike, a fixed default by the part's own axes. The user can **flip** it
   per part, and the plugin shows which face is face 1 in 3D. Edges are
   then named relative to face 1 (e.g. length-1, length-2, width-1,
   width-2 — the exact convention is fixed when the export is designed).
   Mirrored parts (a left and a right side) keep their own face 1, so
   their band flags come out mirrored as they should.
3. **Material roles.** Every material has one role, set once in the
   material library (user default, overridable per model):
   - **Board** — *sheet* or *solid*; the core, cut list + diagrams. May
     be **pre-finished** (melamine MDF): no covering needed. May have
     grain (woodgrain melamine, plywood, veneered boards).
   - **Face covering** — laminate, HPL (Formica), veneer: thickness,
     **its own stock sizes** (veneer is narrower than boards), oversize;
     optionally the board it is applied over.
   - **Edge band** — thickness, width, length oversize, whether its
     thickness is deducted from the cut size.
   - **Appearance only** — a texture that shows something real but is not
     a material to order (model D's plywood-edge texture `*`).
   - **Ignore** — glass, hardware, "not cut".
4. **Reading a part.** Each face's material, through its role, says what
   is there: the core is the Board-role material; face coverings and edge
   bands are placed on their faces/edges. No Board material on any face →
   the covering's "applied over" board, else a flag.
5. **Size convention, per model** (user default): *finished* (coverings
   included — the core is derived by subtracting covering and, when
   deducted, band thicknesses) or *core* (the model is the board;
   coverings add on top). Either way the derived core thickness is
   checked against the board's nominal thickness(es); a mismatch is
   flagged, not corrected.
6. **Settings cascade.** Every setting resolves **user default → model →
   material → part**; the most specific wins (as a face's own paint wins
   over its component's in SketchUp and IngeTrazo). Band deduction and
   oversizes (coverings: per side; bands: per edge length) are set per
   material and overridable per part.
7. **Solid wood is a different anatomy**, designed separately (with 1D
   cutting, after v0.1): rough vs finished stock, thickness classes,
   length allowances, grain always along the length — not faces and
   coverings. The Board role's *solid* kind marks those parts now so
   nothing has to be re-modelled later.
8. **Scope.** The data model holds all of the above from v0.1. Which
   computations v0.1 performs (covering diagrams, band totals, deductions,
   oversizes) is decided when M1 and M2 are planned.

Benchmark note: OpenCutList has edge-banding and veneer material types and
band-thickness deduction; *Appearance only*, the per-model size
convention and the cascade are ours.

## D-008 — "Group #n" numbers live in the document, keyed by part uid

*2026-10-08 · accepted · supersedes the storage part of D-006 §8*

D-006 put a part's "Group #n" number in `group.ext["cutlist"]`. But
`group.ext` travels with copies, so a copied part would carry the same
number as its original. Numbers are kept instead in the document's
extension data under `cutlist.numbers`, as `{uid: n}`: a copy has a new
uid and gets its own number. Handing out a number is bookkeeping, not an
edit: it is written without an undo step and without marking the
document unsaved, and is saved with the next save. Numbers are given in
model order and never reused.

## D-009 — Export: named profiles, plain options instead of formulas

*2026-10-09 · accepted · from Ronaldo's supplier templates (a paste-from-
Excel layout with named bands; a strict layout with supplier codes, no
header, Windows-1252, a separator after the last field) and a reading of
OpenCutList's export*

**What OpenCutList does:** an editable list of columns (field, custom
header, hidden, order), three sources (summary, cut list, one row per
instance), presets — and Ruby **formulas** per column, run with `eval`
behind a blocklist. We keep the first three and **replace formulas with
plain options**: no programming needed, and a shared profile file can
never carry code.

1. **Profiles.** A profile is every rule for one output, under a name the
   user chooses (a supplier, or an internal workflow). The export window
   has a combo box of profiles; Save, Save as new, Rename, Delete, Export
   to file, Import from file; a `*` shows unsaved changes. Profiles live
   in the user's defaults. **No supplier-named profiles ship with the
   extension** (public wording stays neutral): one generic profile ships,
   and the real templates are reproduced exactly in our tests.
2. **The file.** Formats: delimited text (`.csv`/`.txt`), Excel `.xlsx`
   (written with the stdlib: `zipfile` + XML — no dependency), and
   **copy to clipboard** for pasting into a spreadsheet or a web form;
   `.ods` later. Text options: separator (`;` `,` tab `|` or any),
   encoding (UTF-8, UTF-8 with BOM, Windows-1252), line endings (CRLF/LF),
   quoting (as needed / always / never), separator after the last field,
   header row or data only.
3. **Splitting.** One file, or one file per board (material + thickness —
   another thickness is another board), or per value of a custom field;
   file names from a pattern of fill-in fields (`{model} - {material}
   {thickness}`).
4. **Rows.** One per cut-list line with a quantity, or **one per piece**;
   which materials go in; sort order.
5. **Columns.** An ordered list; each has a header text and a value: a
   **field** (qty, length, width, thickness, name, number, material,
   material code, band on C1/C2/L1/L2, grain, may rotate, note, tag,
   model, custom fields…), **fixed text**, or a **fill-in template**
   (`{name} - {tag}`: placeholders only, never code). Columns can be
   hidden and reordered.
6. **Numbers.** Whole millimetres by default (no supplier takes fractions
   of a millimetre); decimals, decimal separator, rounding (nearest, up,
   down), unit suffix or bare, no trailing zeros. Per profile, overridable
   per column.
7. **Grain first.** "Comprimento" is the side along the grain. When a
   grained part's grain runs across its longest side, length and width —
   and the bands with them — are swapped on export. Parts set to "No
   grain" are never swapped, and are flagged as free to rotate.
8. **Supplier language.** Yes/no values as `1/0`, `S/N`, `X/empty` or any
   pair. A **code table per profile** maps the user's material and band
   names to the supplier's codes or names — the matching step suppliers'
   sites make you repeat, done once. A value with no code **stops the
   export and names it**; nothing is written blank silently.
9. **Live preview** of the first rows exactly as they will be written.
10. **Custom fields** (client, room/"Ambiente"…) are defined in Settings,
    not in the export: a model value, optional tag rules (parts with a tag
    get a value), per-part overrides in Part settings (in bulk, one undo
    step). Profiles only use them — as columns, to split files, in names.
