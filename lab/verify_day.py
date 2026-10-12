#!/usr/bin/env python3
"""lab/ - run the registered integrity checks on a day the lab bought (EXPLORATORY).
Aggregates only.

  FRED_KEY=use-cache python lab/verify_day.py --day 2018-02-05 --expiries 2018-02-16,2018-03-16
"""
import argparse
import importlib.util as iu
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "tools"), str(ROOT / "lab")]
import opra_reference as ore               # noqa: E402


def _load(name):
    s = iu.spec_from_file_location(name, ROOT / "lab" / f"{name}.py")
    m = iu.module_from_spec(s)
    s.loader.exec_module(m)
    return m


fl, integ = _load("fetch_lab"), _load("integrity")


def verify(day, symbols, expiries, hhmm="14:30"):
    when, out = fl.ny_minute(day, hhmm), {}
    for sym in symbols:
        p = fl.LAB_DIR / f"{fl.lab_stem(sym, day, hhmm)}.csv"
        if not p.exists():
            print(f"  {sym:4s} no file on disk ({p.name})")
            out[sym] = False
            continue
        opra = ore.load_opra(p)
        good = True
        for e in expiries:
            ch = integ.chain_at(opra, e, when)
            passed, det = integ.check_chain(ch)
            good &= passed
            F = integ.forward(ch)
            fs = f"{F:.2f}" if F else "n/a"
            print(f"  {sym:4s} {e}  forward {fs:>8s}  {'PASS' if passed else 'FAIL'}  "
                  + "; ".join(f"{k}: {v[1]}" for k, v in det.items()))
        out[sym] = good
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--day", required=True)
    ap.add_argument("--expiries", required=True)
    ap.add_argument("--symbols", default="SPY,QQQ,IWM,GLD,USO")
    ap.add_argument("--at", default="14:30")
    a = ap.parse_args()
    res = verify(a.day, a.symbols.split(","), a.expiries.split(","), a.at)
    print(f"\n{sum(res.values())} of {len(res)} funds pass every check. {ore.ATTRIBUTION}")
    sys.exit(0 if all(res.values()) else 1)


if __name__ == "__main__":
    main()
