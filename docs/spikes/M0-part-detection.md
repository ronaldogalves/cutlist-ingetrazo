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
