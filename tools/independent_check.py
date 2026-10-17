#!/usr/bin/env python3
"""Do two implementations, written apart, agree? (17 Oct 2026, Gabriel asked for it to be kept.)

Compares, value by value at FULL precision, the project's own readers with tools/independent_replica.py
(standard library only, written from the method text without reading the estimator code):

  H3 / H5e   modelfree.model_free_30d on every recorded band day - the registered band reading, the band
             under Cboe's zero-bid rule, and (wide days) the wide reading under the registered rule, H5e's
             skip rule and Cboe's rule. These are every number in `modelfree.py --wide`'s tables.
  H7         tools/h7_reader.day_reading - free and OPRA replicas - when OPRA_M files are on disk
             (VOLREC_DATABENTO_DIR, or --opra DIR). Licensed: this prints counts and differences only.

Agreement = within TOL (0.01 vol points, half the last printed digit's step). Inputs (the frozen rate,
the recorded quotes) are shared on purpose; the arithmetic is what is being checked.

  FRED_KEY=use-cache python tools/independent_check.py [--through YYYY-MM-DD] [--opra DIR]
Exit 0 when every value agrees, 1 otherwise. Data provided by Databento (OPRA consolidated NBBO) for H7.
"""
import argparse
import os
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "tools")]
os.environ.setdefault("FRED_KEY", "use-cache")

import independent_replica as IR                    # noqa: E402  (the independent side)
import modelfree as M                               # noqa: E402  (the project's side)

TOL = 0.01


def compare(pairs):
    """pairs: [(label, project, independent)] -> (n, agreeing, largest |diff|, [disagreements])."""
    n, agree, worst, bad = 0, 0, 0.0, []
    for label, a, b in pairs:
        n += 1
        if a is None and b is None:
            agree += 1
            continue
        if a is None or b is None:
            bad.append((label, "one side gave no value"))
            continue
        d = abs(a - b)
        worst = max(worst, d)
        if d <= TOL:
            agree += 1
        else:
            bad.append((label, f"differs by {d:.4f}"))
    return n, agree, worst, bad


def h3_pairs(r, through=None):
    import csv
    band, wide = defaultdict(list), defaultdict(list)
    for x in csv.DictReader((ROOT / "data/surface.csv").open(newline="")):
        if not through or x["date"] <= through:
            band[(x["date"], x["symbol"])].append(x)
    if (ROOT / "data/surface_wide.csv").exists():
        for x in csv.DictReader((ROOT / "data/surface_wide.csv").open(newline="")):
            if not through or x["date"] <= through:
                wide[(x["date"], x["symbol"])].append(x)
    mine = IR.h3_all(r, through)

    def proj(rows, rule):
        got = M.model_free_30d(rows, r, rule)
        return got[0] if got else None

    fam = defaultdict(list)
    for key, inner in sorted(band.items()):
        lab = " ".join(key)
        fam["band, registered rule"].append((lab, proj(inner, False), mine[key]["reg"]))
        fam["band, Cboe zero-bid rule"].append((lab, proj(inner, True), mine[key]["reg_cboe"]))
        if wide.get(key):
            rows = inner + wide[key]
            fam["wide, registered rule (H3 lift)"].append((lab, proj(rows, False), mine[key]["wide_reg"]))
            fam["wide, Cboe zero-bid rule (H3 lift)"].append((lab, proj(rows, True), mine[key]["wide_cboe"]))
            fam["wide, skip rule (H5e)"].append((lab, proj(rows, "skip"), mine[key]["wide_skip"]))
    return fam


def h7_pairs(r_bey, opra_dir, through=None):
    import h7_reader as H
    import ovx_replicate as O
    R_proj, R_mine = O.bey_to_continuous(r_bey), IR.bey_to_continuous(r_bey)
    fam = defaultdict(list)
    for (d, s), (fv, ov) in IR.h7_all(opra_dir, R_mine, through).items():
        x = H.day_reading(d, s, R_proj, opra_dir)
        fam["H7 free replica"].append((f"{d} {s}", x["free"] if x else None, fv))
        if x and (x["opra"] is not None or ov is not None):
            fam["H7 OPRA replica"].append((f"{d} {s}", x["opra"], ov))
    return fam


def main(argv=None):
    ap = argparse.ArgumentParser(description="the project's readers against an independent implementation")
    ap.add_argument("--through", help="only days on or before this date")
    ap.add_argument("--opra", default=os.environ.get("VOLREC_DATABENTO_DIR"), help="OPRA files (licensed) for H7")
    a = ap.parse_args(argv)
    r = M.risk_free()
    print(f"Independent re-implementation check - r = {r * 100:.3f}%, agreement within {TOL} points")
    if abs(r * 100 - IR.FROZEN_RATE_PCT) > 0.0005:
        print(f"  NOTE: the rate is not the frozen {IR.FROZEN_RATE_PCT}% - both sides still use the same input")
    fams = h3_pairs(r, a.through)
    if a.opra and Path(a.opra).is_dir():
        fams.update(h7_pairs(r, a.opra, a.through))
    else:
        print("  (H7 skipped: no OPRA directory - licensed files live in volrec-licensed)")
    total = agreed = 0
    print()
    for name, pairs in fams.items():
        n, ok, worst, bad = compare(pairs)
        total, agreed = total + n, agreed + ok
        print(f"  {name:<36} {ok:4} of {n:4} agree   largest difference {worst:.5f}")
        for lab, why in bad:
            print(f"      DISAGREES  {lab}: {why}")
    print(f"\nRESULT: {agreed} of {total} values agree")
    if any("H7" in k for k in fams):
        print("Data provided by Databento (OPRA consolidated NBBO). Aggregates only.")
    return 0 if agreed == total else 1


if __name__ == "__main__":
    sys.exit(main())
