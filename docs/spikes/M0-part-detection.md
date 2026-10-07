# M0 spike — part detection

*2026-10-07. Script: `spikes/part_detection.py`. Inputs: IngeTrazo's four
`examples/*.igz` (architecture, not furniture) and three real furniture
jobs in SketchUp format from `samples/private/` (client work: named here
only as models A, B and C).*

## What loaded

| Model | Source | Result |
|---|---|---|
| IngeTrazo examples ×4 | `.igz` | loaded; 9–60 containers each |
| A — office furniture (has OpenCutList diagrams) | `.skp`, SketchUp 2020 | **does not open**: OpenSKP `no reader for class CCustomLineStyle` (custom dashed line styles) |
| B — furniture | `.skp`, SketchUp 2020 | **does not open**: OpenSKP `back-ref to unwalked slot` |
| C — whole-apartment joinery | `.skp` | loaded: 399 containers, 391 leaf parts → 208 lines |

A and B fail inside OpenSKP, IngeTrazo's `.skp` reader; IngeTrazo swallows
the exception and reports "no pure SKP backend". To report upstream (the
files themselves are private). Workaround to try: re-save in SketchUp
2021+.

## What model C shows

- **The model is flat.** 391 of 399 containers sit at the top level; the
  only nesting is a hardware component (a castor) holding a sub-part.
  Parts are organised by **tags**, not by cabinet containers.
- **Tags carry the meaning.** `00 AS_BUILT` (the room: walls, existing
  objects — 6 m "parts" with no wood material), `20 … FASE 1`,
  `22 … FASE 2`, `25 … CORTE EXTRA`, `26 … PRAT`, `30/31 … P`,
  `32 … FUNDOS`, **`50 … FORA DO CORTE`** (114 containers explicitly *not*
  to be cut) and **`59 XTRAS / FERRAGENS`** (hardware). Scope by tag is not
  a nice-to-have: without it the room and the "not cut" parts pollute the
  list.
- **A material can also mean "exclude"**: `MDF Branco TX (fora do corte)`.
  This is the *Ignore* material type of the brief.
- **One material, several thicknesses**: `MDF Branco TX` at 6, 15 and
  18 mm. Grouping by material **and** thickness is essential (OpenCutList's
  diagrams for model A are per material + thickness too).
- **Names are meaningful** (`GR LAT ESQ`, `COZ PIA GAVETÃO FRENTE`) and
  prefixed by piece of furniture (`GR` wardrobe, `COZ` kitchen, `QTO`
  bedroom…). Unnamed parts arrive as SketchUp's `Group#24` — stable,
  because they come from the file.
- **Both components and plain groups are used**, often for identical
  boards (`PAINEL`: 1 component + 2 groups, same size and material).
  Merging must go by **measurement**, not by structure.
- **Components are used for unique parts too** (most component lines have
  qty 1), so "component" does not mean "repeated".
- **Every part measured as a clean board** (L × W × T, thickness 6/15/18).
  No surface parts; nothing non-rectangular among the wood parts.

## Round 2 (same day): four more models, one built nested

| Model | Parts → lines | Note |
|---|---|---|
| D — kitchen (has OpenCutList diagrams) | 87 → 55 | compared below |
| E — built **nested** on purpose | 115 → 58 | arrived flat |
| F, G — furniture | 49 → 23, 153 → 69 | |

All four are SketchUp 2020 files and all opened (so 2020 is not the cause
of the failures above).

### IngeTrazo flattens the `.skp` hierarchy

`formats/skp_openskp.py` turns each **top-level** instance into one group
with its whole subtree merged into it ("reference geometry"); the only
exception is a nested instance carrying its **own tag**, which becomes a
separate top-level group. Model E's boards are tagged, so they came out as
115 separate parts — and the cabinets that held them are gone, names
included. **Consequences:**

- After a `.skp` import there is no cabinet → board hierarchy to use. A
  "module" column cannot come from the parent container for imported
  models (it can for models built in IngeTrazo).
- An **untagged** board nested in a cabinet is **merged into the cabinet**:
  the cut list would show one big "part". Defence: flag a leaf whose
  geometry is several disconnected solids ("looks like several boards in
  one group").
- Worth raising upstream: keep the instance tree on `.skp` import.

### Model D against OpenCutList (the M1 acceptance test, early)

OpenCutList's diagrams list 86 sheet parts in four material/thickness
groups. Ours, per group:

| Group | OpenCutList | Ours |
|---|---|---|
| MDF Verde Jade 15 | 14 | **14, every line identical** |
| MDF Branco 6 | 7 | **7, every line identical** |
| MDF Branco 15 | 32 | **32, every line identical** |
| Compensado naval 15 | 33 | 30 + 3 under material `*` |
| MDF Branco 18 | — (no PDF) | 1 (`GAB ESQ PRAT`) |

Sizes agree to the millimetre, quantities exactly. The 3 differences are
15 × 15 mm baguettes: their 2 main faces are compensado, their 4 edge
faces a material named `*`. IngeTrazo's `part_material` takes the largest
*total* area, and on a 15 × 15 stick the edges win by a hair. OpenCutList
reads the material of the instance. **Rule for us: a board's material is
the material of its two main faces (perpendicular to its thickness);
other materials on its edges are edge information (edge banding — later)**.

## What the IngeTrazo examples show

- IngeTrazo's own automatic names (`Group 31`) are **not stable**: the same
  group was `Group 31` in one run and `Group 6` in the next. Our "Group #n"
  numbering must be ours, stored with the part (`group.ext`), keyed by
  `group.uid`.
- Material names can be meaningless (`928cd77719565dde-sumari`).

## Related upstream (IngeTrazo issues)

- **#309** — feature request: a cut list and cutting optimizer, citing
  OpenCutList. The natural place to introduce this project.
- **#199** — per-copy instance names, carried to the cut list; a Brazilian
  user's workflow into **Corte Certo** (`nr;nome;compr;larg;espes`, one
  line per piece, whole mm, L ≥ W ≥ T).
- **#239** — the extensions catalog (ingetrazo.com/extensiones): a `.zip`
  holding one folder with `__init__.py` is accepted — our release format.

## Proposal

See D-006 in `docs/DECISIONS.md`.
