# Cut List for IngeTrazo — user guide

*Also in [Português (Brasil)](user-guide.pt-BR.md) and
[Español](user-guide.es.md).* For version 0.1.0, IngeTrazo 0.5.9.

Cut List turns a furniture model into the list of parts to cut, sends it
to the supplier who cuts your boards, and draws the cutting diagrams for
your own saw.

![A cutting diagram](images/cutting-diagram.png)

## 1. Install

1. Download `cutlist-0.1.0.zip` from the
   [Releases](https://github.com/ronaldogalves/cutlist-ingetrazo/releases)
   page — or install **Cut List** from IngeTrazo's Extension manager.
2. By hand: in IngeTrazo, **Extensions ▸ Open plugins folder**, unzip
   there so the folder holds `cutlist/__init__.py`, and restart IngeTrazo.

Cut List appears as a tab in the side tray and in **Extensions ▸ Cut
List**.

## 2. How to model for a cut list

- **One part, one group or component.** Each board you cut is a group or
  a component of its own. A cabinet can be a group holding its boards;
  Cut List reads the boards inside (the innermost groups are the parts).
- **Name your parts.** The name is what the shop sees. Parts without a
  name are listed as "Group #1", "Group #2"… and keep their number.
- **Paint faces, not just parts.** Cut List reads the model the way
  woodworkers paint it: the material on the large faces is the board,
  a different material on one face is a laminate or veneer, a material on
  a narrow edge is an edge band.
- **Tags** can keep things out of the list (walls, appliances): use the
  **Tags** button in the panel.

## 3. First use: what goes in the list

The first time you press **Refresh**, Cut List asks what to read: the
selection or the whole model, plain groups too or components only, and
which tags to leave out. Tick "don't show again" and it remembers; change
it later in **Settings…**.

## 4. Materials: say once what each one is

Open **Materials…**. On the left, every material found on your parts;
on the right, what it is:

| What it is | Means |
|---|---|
| **Board** | the sheet that gets cut (MDF, plywood, MDP…) |
| **Covering** | laminate, HPL or veneer glued on a face |
| **Edge band** | banding on an edge |
| **Appearance only** | a texture that only shows something (a plywood edge) |
| **Ignore** | not cut: glass, hardware, walls |

For a **board** you can also set:

- **Thicknesses** it comes in (e.g. `15; 18`): a part modelled 14 mm thick
  on a 15 mm board is then flagged *odd thickness*.
- **Sheets it comes in**: the real sheet size, not a trimmed one. A size
  only for some thicknesses goes in the last column (e.g. `3; 6`).
  **Templates ▾** saves sizes under a name and applies them to several
  materials at once — select them with Ctrl+click first.
- **Kerf** and **trim**, when this board needs others than the defaults.
- **Cut oversize**: every part of this board is cut this much bigger, to
  be brought to size later. The model keeps the finished size.

For an **edge band**:

- **Thickness** and **width** (e.g. 0.45 and 22 mm), and the **room to
  finish it** (2 mm by default, both sides together): a part thicker than
  width − room is flagged *band too narrow* — a 22 mm band fits up to
  20 mm. Make one band per width you use (22, 30…) and paint the right
  one.
- **Oversize** per banded edge (the overhang trimmed after gluing),
  **waste %**, and a **roll length** if you buy it in rolls — all
  optional.
- **Cut the board shorter by the band thickness**: for thick bands; the
  saw gets the smaller size, the list keeps the finished one.

"Also use these materials in my other models" (ticked) puts them in your
library: every model with a material of the same name starts from it. In
the list, *my library* and *this model only* say where each setup comes
from; *not set up* is a material still to decide.

## 5. Reading the list

Parts are grouped by **board and thickness**; identical parts are one
line with a quantity. Columns: **Part** (the letter, the same as on the
diagrams), name, quantity, length, width, thickness, banded **edges**
(L1/L2 the long ones, W1/W2 the short ones, seen from face 1), **faces**
(coverings), and **notes**.

**Needs a look** lists what Cut List will not guess: parts that are not
rectangular, several boards merged in one group, parts with no material,
finishes not set up, odd thicknesses. Nothing is dropped silently;
**Excluded** lists what you or a material left out.

**Edge bands** at the end: the metres of each band to buy, how many
edges, and rolls when set.

Click a line to see its parts highlighted in the model.

## 6. Part settings

Right-click a line (or parts in the model) ▸ **Part settings…**: grain
along the length or the width, may rotate on the sheet, leave out of the
cut list, flip face 1, a note, the part's own **cut oversize** and its
custom field values. Every change is one undo step.

**Custom fields** (client, room…) are defined in **Settings…**: a value
for the model, rules by tag, or a value per part.

## 7. Export for a supplier

**Export…** writes the list the way your supplier wants it. A **profile**
holds every rule: columns and their order, header, separator, encoding,
units, rounding, file names. Ready profiles:

- **CorteCloud** — copy to the clipboard and paste in CorteCloud's import
  window (or open the Excel file and paste from there).
- **Leo Madeiras** — a CSV for Leo's website import.
- **Simple CSV** — for anything else.

Change a profile and **Save**, or **Save as…** a new one; **Import…**
takes several profile files at once, **Export profile…** shares one. The
preview shows exactly what will be written; problems (a missing supplier
code, a character the file's encoding cannot hold) are listed and stop
the export until fixed. Untick boards to leave them out of this export.
"Also a file with the edge bands to buy" writes the band totals beside
the list.

## 8. Cutting diagrams

**Diagrams…** lays every board out on its sheets for a panel or table
saw. Boards with no sheet size are asked once (Cancel stops).

- **Boards** on the left, with sheets and how much is used.
- **The saw**: first cuts lengthwise, crosswise (easier when you cut
  alone) or the better of both; 2, 3 or 4 cutting stages; kerf; trim on
  all four edges or two. **Redo the layout** applies them.
- **Leftovers from the shop**: pieces you already have, used before full
  sheets and never trimmed.

On the sheets:

- **Hover a part**: its size and the cuts that free it, each with the
  distance to set on the fence; it lights up in the model too. Parts you
  select in the model light up on the diagram.
- **Hover a cut**: its stage, fence distance and length. A first cut runs
  across the whole sheet, so any of them can go first — to split a big
  sheet in two before the rest.
- **Right-click a part**: switch its grain (all copies, or only this
  one), allow or forbid rotation, part settings, leave it out of this
  layout, show it in the model. A change to the part is one undo step,
  and the layout is redone for the same parts.

## 9. Print

Choose the paper (A4, Letter), the text size (**Large**, or **Compact**
for fewer pages), whether identical sheets appear once (×n), a totals
page, cut positions along the edge, the cuts in order under each sheet
("1 Rip 645 · 2 Crosscut 1982…": where to set the fence, from the edge
of the piece being cut); then **PDF…** or **SVG…**. Every page
says "Page n of N" with the model, board and date, so scattered pages can
be put back in order at the shop.

## 10. Labels

**Labels…** (in the panel, or in the diagrams window) makes a sticker for
every piece. Choose the sticker sheet (Pimaco and Avery sheets in A4 or
Letter, or **Custom sheet…** with its sizes), and **Start at label** on a
sheet you already used. Each label says the part's letter, name and
size, material and thickness, the model and your custom fields, "3 of
4", and a small drawing with the banded edges and the grain. From the
diagrams the labels come sorted by sheet and say which sheet each piece
is cut from. **Outline each label** prints the frames, to test on plain
paper first.

## 11. Save a layout

**Save layout…** keeps the layout in the model (saved with the file).
**Saved layouts ▾** reopens it exactly as it was — even if the packing
would come out differently today. If the model changed since, the window
says which parts changed size or are gone, and **Redo the layout for
these parts** lays them out again.

## 12. Good to know

- Lengths in the dialogs are typed in millimetres; the list follows the
  model's units unless set in **Settings…**.
- Solid wood is listed but not laid out yet; layouts are for a saw, not
  CNC nesting.
- `.skp` files arrive in IngeTrazo without their group hierarchy, and
  groups and components do not stay apart: check *Needs a look*.
- Questions, bugs and profiles for other suppliers:
  [github.com/ronaldogalves/cutlist-ingetrazo](https://github.com/ronaldogalves/cutlist-ingetrazo/issues).
