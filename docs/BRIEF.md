# Project brief — CutList for IngeTrazo

*Working name. Debrief prepared 2026-10-06 from an exploratory session; this
is the starting point for development in Claude Code.*

## 1. Vision

A woodworker designs a cabinet, a bench or a shelf in IngeTrazo and, with
one click, gets what they need to go to the workshop or the panel shop:

- a **cut list** — every part with its size, material and quantity;
- **cutting diagrams** — how those parts fit on the stock sheets they will
  buy, with kerf and trim accounted for;
- exports they can print, send to a panel-cutting service or open in a
  spreadsheet.

Free and open source (GPL-3.0-or-later), Linux-first like IngeTrazo,
translated into Portuguese and Spanish from the start, and sustained by
voluntary donations later on.

## 2. Who it is for

- **Hobby and small-shop woodworkers** who model furniture and today use
  SketchUp + OpenCutList, or draw cut lists by hand.
- **Joiners and cabinet makers** in Latin America (IngeTrazo's core
  audience) who order cut sheets from panel suppliers.
- **Teachers and students** of furniture design.

## 3. Background and context

**IngeTrazo** (https://github.com/ingelibre/ingetrazo) is a free 3D modeler
with SketchUp-style push/pull modeling, written in Python + PySide6 (Qt),
GPL-3.0-or-later, at version 0.5.x. It reads `.skp` files from 2013–2026.
From the user's side it feels like SketchUp; inside, it is a different
system — Python instead of Ruby, its own mesh/group/component model, Qt
widgets instead of HTML dialogs.

It has an extension API (`docs/plugins.md`, API version 2) with side-tray
panels, menus, context menus, viewport overlays, per-document data and
per-group data. It is explicitly unstable during 0.x. There is no plugin
store or plugin manager yet (on their roadmap, after the API stabilises).

IngeTrazo **already has the seed of a cut list**: `core/parts.py` measures
each part of a container as length × width × thickness (along its own axes
when that is much tighter — a splayed leg measures as the stick it is),
finds its dominant material, merges identical parts into lines with a
quantity, and the Parts tray can copy that as tab-separated text. What it
does not have: material types, stock sizes, grain, kerf, cutting diagrams,
exports, or settings that persist.

**OpenCutList** (https://github.com/lairdubois/lairdubois-opencutlist-sketchup-extension)
is the mature reference: cut lists, 1D/2D cutting diagrams, edge banding,
veneers, labels, cost estimates, part drawings, multi-language. It is
~91k lines of Ruby tied to the SketchUp API, a ~21k-line JavaScript/Twig
HTML UI, and ~23k lines of C++ (Clipper2 + the "Packy" nesting engine).
We assessed a direct port and rejected it (see D-001): we use OpenCutList
as a **feature and quality benchmark**, and build our own implementation.

## 4. Scope

### MVP — v0.1

1. **Part detection.** From the selection, or the whole model when nothing
   is selected, find the parts: the leaf groups and component instances
   (containers with no child containers). Identical component instances
   and identical parts count as quantity. Parts without thickness
   (`core.parts.is_surface`) are listed apart, not as boards.
2. **Measurement.** Length × width × thickness via `core.parts.part_size`.
   Non-rectangular parts use their bounding box and are flagged.
3. **Woodworking materials.** For each IngeTrazo material used by parts,
   the user sets a type:
   - *Sheet goods* (plywood, MDF, particle board): thickness(es), stock
     sheet sizes, grain yes/no;
   - *Solid wood*: listed only in the MVP (1D/rough stock comes later);
   - *Ignore* (hardware, glass, things not cut from wood).
   Stored in our document data, keyed by material name.
4. **Per-part overrides.** Grain direction (along length / along width /
   none), "may rotate", exclude from list, notes. Stored in
   `group.ext["cutlist"]`.
5. **Cut list panel.** A tray tab listing lines grouped by material and
   thickness: quantity, names, length, width, thickness, flags. Clicking a
   line highlights its parts in the viewport.
6. **2D cutting diagrams** for sheet goods: guillotine layouts with kerf,
   sheet trim margins, grain constraints, multiple stock sizes; per sheet:
   placed parts with labels, waste %, number of sheets. Shown in a
   separate window.
7. **Exports.** Cut list as CSV (UTF-8, `;` or `,` selectable — Brazilian
   Excel uses `;`); diagrams as SVG (written with the stdlib) and PDF (Qt's
   QPdfWriter, which IngeTrazo already uses) — no new dependency.
8. **i18n.** English source, pt-BR and es catalogs complete at release.
9. **Units.** Everything internal in metres; display in the model's units
   (`core.units.fmt_len_fine`).

### Explicitly not in v0.1

1D diagrams for solid wood and dimensional lumber, edge banding, veneers,
labels, cost estimates, XLSX export, part drawings (DXF/SVG per part),
interactive "smart" tools (OpenCutList's Smart Axes / Paint / Draw), an
outliner, importing cut lists, cloud sync, optimizing across several
models, and **donations** (planned for v0.2 — see §7).

### Candidates after v0.1 (order to be decided with users)

1D cutting diagrams; edge banding and its length totals; part labels
(printable, with part IDs matching the diagrams); cost estimate from
stock prices; DXF export of diagrams and parts via ezdxf (already bundled
with IngeTrazo); panel-supplier import formats (e.g. CSV layouts used by
Brazilian panel cutters); XLSX if a dependency-free writer proves worth it.

## 5. Architecture overview

Three layers (rule in `CLAUDE.md`):

- **host/** — the only code that imports IngeTrazo. `extract.py` turns
  the scene into `Part` records (via `core.parts`), `store.py` reads and
  writes document data and `group.ext`, `highlight.py` draws the overlay.
- **model/** and **packing/** — pure Python + NumPy, unit-tested without
  Qt or IngeTrazo. Core types:
  - `Part(id, name, length, width, thickness, material, grain, can_rotate, qty, source_ids, flags)`
  - `MaterialSpec(name, kind, thicknesses, stock_sheets, grain, kerf, trim)`
  - `CutListLine` (grouped parts), `Sheet`, `Placement`, `Layout`
  - `Packer` protocol: `pack(parts, stocks, settings) -> Layout`
- **ui/** — Qt: the tray panel, the diagram window (QPainter rendering
  shared by screen and PDF; SVG is written by `export/svg.py`), material and part settings dialogs.

Data flow: scene → `host.extract` → `[Part]` → `model.grouping` →
`[CutListLine]` → panel; sheet-goods lines → `packing` → `Layout` →
diagram window → export.

Recompute is on demand (a Refresh button and on panel show), not on every
edit; `on_document_changed` only marks the list stale.

### Stored data (versioned from day one)

```jsonc
// app.document_data()  — one value for the whole document
{ "schema": 1,
  "materials": { "MDF 18": { "kind": "sheet", "thicknesses": [0.018],
                             "stocks": [[2.75, 1.84]], "grain": false,
                             "kerf": 0.004, "trim": 0.01 } },
  "settings": { "csv_separator": ";", "group_by": "material+thickness" } }

// group.ext["cutlist"]  — per part
{ "schema": 1, "grain": "length", "can_rotate": false,
  "exclude": false, "note": "" }
```

## 6. The packer (decision D-003)

Our own pure-Python **guillotine** packer first, behind the `Packer`
protocol:

- guillotine cuts only (what panel saws and most shops actually do);
- kerf between parts, trim margin around the sheet;
- grain: parts with grain keep orientation relative to the sheet's grain;
  others may rotate;
- several stock sizes; choose the combination that uses fewest sheets,
  then least waste;
- heuristics: first-fit decreasing with best-area / best-short-side fit,
  several orderings tried, best kept (multi-start), bounded by a time
  budget so the UI stays responsive (run in a worker thread);
- deterministic for a given input (seeded), so tests and diagrams are
  reproducible.

Quality bar: within ~5–10 % of OpenCutList's sheet count/waste on the
benchmark set (built in M2). If we cannot get there, the protocol lets us
add a second backend (e.g. OpenCutList's C++ Packy via ctypes) without
touching the UI — that would need per-platform native builds, which is why
it is not the first choice.

## 7. Open source and donations

- License GPL-3.0-or-later, public repository from day one.
- Donations arrive in v0.2, done respectfully (D-005): a "Support CutList"
  entry in our submenu and a small section in the About dialog; links open
  in the browser via `QDesktopServices.openUrl`; optionally a PIX QR code
  for Brazilian users. No pop-ups, no nag screens, no network calls made by
  the plugin itself.
- Repository-level: a `.github/FUNDING.yml` once the platform is chosen
  (candidates: GitHub Sponsors, Open Collective — which OpenCutList uses —,
  Liberapay, Ko-fi, plus PIX).
- Paid distribution was considered and set aside: as GPL software, anyone
  who receives it may share it, and IngeTrazo has no store.

## 8. Relationship with IngeTrazo

- Open a discussion/issue with the IngeTrazo maintainers early (M0/M1):
  introduce the project, avoid duplicating their Parts tray, ask about
  the part-detection rule and whether woodworking material attributes
  belong in core.
- Upstream fixes and small API needs as separate PRs to IngeTrazo rather
  than monkey-patching it.
- Their docs say features only some users need belong in extensions,
  and they list community extensions (Niveles, Windowizer) — being listed
  is the best route to users (and to donors).
- Do not use "IngeTrazo" or "Inge-" in the product name without asking.

## 9. Risks

| Risk | Mitigation |
|---|---|
| IngeTrazo API changes (0.x) | Adapter layer; pin tested version; CI against their main |
| Part detection disagrees with how people model | Spike in M0 on real models; per-part exclude; maintainer input |
| Packer quality below expectations | Benchmark set in M2; `Packer` protocol allows a second backend |
| Users expect OpenCutList parity | Clear v0.1 scope in README; public roadmap |
| Single maintainer | Small, tested, documented code; contributor guide |

## 10. Open questions

1. **Final name** (and whether "IngeTrazo" may appear in it).
2. **Repository owner/host** (personal GitHub account or an organization).
3. **Part detection rule** — leaf containers only? What about a part
   modelled as loose faces inside a cabinet group? Settle in M0.
4. **Minimum IngeTrazo version** to support.
5. **Donation platform(s)** — decide before v0.2.
6. **Release channel** — GitHub release zip only, or also ask to be
   listed under IngeTrazo's example extensions.
