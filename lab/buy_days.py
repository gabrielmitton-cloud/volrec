#!/usr/bin/env python3
"""lab/ - buy every monthly entry day's quotes and listings for the five funds (EXPLORATORY).
Priced first, the lab's own cap, nothing bought twice, one ledger commit at the end.

  FRED_KEY=use-cache python lab/buy_days.py --dry-run
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


bars, cal, fl = _load("bars"), _load("tradecal"), _load("fetch_lab")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--max-cost", type=float, default=ore.DEFAULT_MAX_COST)
    a = ap.parse_args()
    key = ore.api_key()
    days = sorted(bars.load()["SPY"])
    pairs = cal.entries(days)
    print(f"{len(pairs)} entry days, {pairs[0][0]} to {pairs[-1][0]}")
    if not a.dry_run:
        fl.sync_ledger()
    paid = []
    for entry, _exp in pairs:
        for sym in bars.FUNDS:
            paid.append(fl.fetch(entry, sym, key, a.max_cost, a.dry_run))
            paid.append(fl.fetch_listings(entry, sym, key, a.max_cost, a.dry_run))
    n, usd = sum(1 for p in paid if p > 0), sum(paid)
    if n:
        fl.commit_ledger(n, usd)
    print(f"\n{n} file(s) bought, ${usd:.4f}. {ore.ATTRIBUTION}")


if __name__ == "__main__":
    main()
