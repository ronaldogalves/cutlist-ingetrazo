# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Ronaldo Alves and CutList contributors.
"""Benchmark the saw packer (M2): sheets, efficiency, cuts and time per job,
against OpenCutList's result where we have it.

Cases are JSON files: ``benchmarks/cases/*.json`` (synthetic, public) and
``samples/private/benchmarks/*.json`` (real client jobs: never published).

    python benchmarks/run.py [--stages 3]

A case::

    {"name": "…", "stocks": [{"length": 2.75, "width": 1.84}],
     "settings": {"kerf": 0.005, "trim": 0.01, "first_cut": "best"},
     "pieces": [["A", 0.738, 0.297, 2, true], …],      # key, L, W, qty, rotate
     "reference": {"sheets": 1, "efficiency": 0.7402,
                   "source": "OpenCutList 2023-09-11, Medium"}}
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cutlist.packing.base import Piece, SawSettings, Stock  # noqa: E402
from cutlist.packing.guillotine import pack  # noqa: E402

FOLDERS = (ROOT / "benchmarks" / "cases",
           ROOT / "samples" / "private" / "benchmarks")


def cases():
    for folder in FOLDERS:
        yield from sorted(folder.glob("*.json"))


def run(path: Path, stages: int | None) -> dict:
    case = json.loads(path.read_text(encoding="utf-8"))
    settings = SawSettings(**case.get("settings", {}))
    if stages:
        settings = SawSettings(**{**case.get("settings", {}),
                                  "stages": stages})
    pieces = [Piece(k, ln, w, q, r) for k, ln, w, q, r in case["pieces"]]
    stocks = [Stock(**s) for s in case["stocks"]]
    start = time.perf_counter()
    layout = pack(pieces, stocks, settings)
    seconds = time.perf_counter() - start
    ref = case.get("reference") or {}
    # No layout can use fewer sheets than the parts' area needs.
    usable = min((s.length - 2 * settings.trim) * (s.width - 2 * settings.trim)
                 for s in stocks)
    bound = math.ceil(sum(p.length * p.width * p.qty for p in pieces)
                      / usable - 1e-9)
    return {"name": case.get("name", path.stem), "bound": bound,
            "parts": sum(p.qty for p in pieces),
            "sheets": len(layout.sheets), "eff": layout.efficiency,
            "cuts": layout.cut_count, "unplaced": layout.unplaced,
            "seconds": seconds, "ref_sheets": ref.get("sheets"),
            "ref_eff": ref.get("efficiency"), "ref_cuts": ref.get("cuts")}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--stages", type=int)
    args = ap.parse_args(argv)
    rows = [run(p, args.stages) for p in cases()]
    print(f"{'job':34} {'parts':>5} {'min':>4} {'sheets':>6} {'OCL':>4} {'eff':>6} "
          f"{'OCL':>6} {'cuts':>5} {'OCL':>4} {'time':>6}")
    worse = 0
    for r in rows:
        ref = r["ref_sheets"]
        if ref is not None and r["sheets"] > ref + 1:
            worse += 1
        print(f"{r['name'][:34]:34} {r['parts']:5} {r['bound']:4} {r['sheets']:6} "
              f"{ref if ref is not None else '-':>4} {r['eff']:6.1%} "
              f"{(format(r['ref_eff'], '.1%') if r['ref_eff'] else '-'):>6} "
              f"{r['cuts']:5} {r['ref_cuts'] or '-':>4} "
              f"{r['seconds']:5.2f}s"
              + (f"  UNPLACED {r['unplaced']}" if r["unplaced"] else ""))
    print(f"\n{len(rows)} jobs; more than one sheet worse than OpenCutList: "
          f"{worse}")
    return 1 if worse else 0


if __name__ == "__main__":
    sys.exit(main())
