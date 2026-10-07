# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Ronaldo Alves and CutList contributors.
"""M0 spike — THROWAWAY. What would count as a part in a real model?

Loads .igz or .skp files headless and prints, for each one:

1. the container tree as IngeTrazo holds it (name, component or group,
   own faces, children, layer, material, size);
2. the parts the DRAFT rule of D-006 would find, and the lines they merge
   into, with the flags it would raise.

Draft rule (to be confirmed or changed by what this shows):
- a part is a LEAF container: a group or component instance with faces of
  its own and no child containers;
- component instances sharing one prototype mesh are one part × qty;
- a container that has child containers AND faces of its own is flagged
  ("loose geometry beside parts");
- thinner than 0.5 mm → surface, listed apart;
- hidden things are left out.

Usage (from the project root, in the dev venv):
    python spikes/part_detection.py ingetrazo/examples/*.igz samples/*.skp
"""
from __future__ import annotations

import os
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(os.environ.get("INGETRAZO_SRC") or ROOT / "ingetrazo")))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

_app = QApplication.instance() or QApplication(sys.argv[:1])

from core.parts import is_surface, part_material, part_points, part_size  # noqa: E402
from core.scene import Scene  # noqa: E402


def load(path: Path) -> Scene:
    scene = Scene()
    if path.suffix.lower() == ".skp":
        from formats.skp import load_skp
        load_skp(scene, path)
    else:
        from formats.igz import load_into
        load_into(scene, path)
    return scene


def mm(size) -> str:
    return " × ".join(f"{d * 1000:.1f}" for d in size)


def kind(g) -> str:
    if g.is_component():
        return "component"
    return "group" if g.xform is None else "group*"   # * carries a matrix


def visible(scene, g) -> bool:
    return scene.entity_visible(g) and not getattr(g, "hidden", False)


def walk(scene, g, depth, out, counters):
    own = len(g.mesh.faces)
    kids = [c for c in (g.children or []) if visible(scene, c)]
    size = part_size(part_points(g)) if (own or kids) else (0, 0, 0)
    flags = []
    if kids and own:
        flags.append("LOOSE FACES BESIDE PARTS")
    if not kids and own and is_surface(size):
        flags.append("surface")
    counters["containers"] += 1
    print(f"{'  ' * depth}- {g.name!r} [{kind(g)}] faces={own} "
          f"children={len(kids)} layer={g.layer!r} "
          f"mat={part_material(g)!r} size={mm(size)} mm"
          + (f"  ⚠ {', '.join(flags)}" if flags else ""))
    if not kids:
        if own:
            out.append((g, size, flags))
        else:
            counters["empty"] += 1
    for c in kids:
        walk(scene, c, depth + 1, out, counters)


def report(path: Path) -> None:
    print("=" * 78)
    print(path.name)
    print("=" * 78)
    try:
        scene = load(path)
    except Exception as exc:                        # noqa: BLE001 — a spike
        print(f"  could not load: {type(exc).__name__}: {exc}")
        return
    loose = len(scene.loose_mesh.faces) if scene.loose_mesh else 0
    print(f"loose faces at top level (outside any container): {loose}")
    parts: list = []
    counters: dict = defaultdict(int)
    for g in scene.groups:
        if visible(scene, g):
            walk(scene, g, 0, parts, counters)

    # Merge by what was MEASURED (size to 1 mm + material), whatever the
    # structure: a group and a component of the same board are one line —
    # the examples have exactly that (a 500 mm cube as both).
    lines: dict = {}
    for g, size, flags in parts:
        key = (part_material(g), tuple(round(d * 1000) for d in size))
        line = lines.setdefault(key, {"names": [], "size": size,
                                      "mat": part_material(g),
                                      "flags": set(flags), "kinds": set()})
        line["names"].append(g.name)
        line["kinds"].add(kind(g))
    print(f"\n{counters['containers']} containers, {len(parts)} leaf parts, "
          f"{counters['empty']} empty leaves → {len(lines)} lines")
    for line in sorted(lines.values(), key=lambda ln: -ln["size"][0]):
        names = sorted(set(line["names"]))
        shown = ", ".join(names[:3]) + (" …" if len(names) > 3 else "")
        print(f"  {len(line['names']):>3} × {mm(line['size']):>24}  "
              f"{line['mat'][:22]:<22} {'+'.join(sorted(line['kinds'])):<15} {shown}"
              + (f"  ⚠ {', '.join(sorted(line['flags']))}"
                 if line["flags"] else ""))
    print()


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        report(Path(arg))
