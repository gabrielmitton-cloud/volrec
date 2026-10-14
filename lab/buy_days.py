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
    ap.add_argument("--kind", default="all", choices=("entries", "stress", "weekly", "all"),
                    help="entries (14:30 NY), stress-month daily marks (15:55 NY), weekly Wednesdays (14:30 NY)")
    ap.add_argument("--workers", type=int, default=15)
    a = ap.parse_args()
    key = ore.api_key()
    days = sorted(bars.load()["SPY"])
    plan = []                               # (day, time NY), in priority order: entries first
    if a.kind in ("entries", "all"):
        plan += [(e, cal.slot(e, "14:30")) for e, _x in cal.entries(days)]
    if a.kind in ("stress", "all"):
        plan += [(d, cal.slot(d, "15:55")) for d in cal.stress_days(days)]
    if a.kind in ("weekly", "all"):
        plan += [(d, cal.slot(d, "14:30")) for d in cal.weekly_days(days)]
    print(f"{len(plan)} day-times ({a.kind}), {a.workers} requests at a time")
    if not a.dry_run:
        fl.sync_ledger()
    # The five funds in parallel (14 Oct: one at a time took ~40 s a request, ~13 hours in all).
    # Ledger writes are serialised by fetch_lab.LEDGER_LOCK; each cap check reads the ledger first,
    # so in-flight requests can overshoot a cap by at most one per worker (about $0.05).
    from concurrent.futures import ThreadPoolExecutor

    def one(job):
        day, hhmm, sym = job
        return [fl.fetch(day, sym, key, a.max_cost, a.dry_run, hhmm),
                fl.fetch_listings(day, sym, key, a.max_cost, a.dry_run)]

    jobs = [(day, hhmm, sym) for day, hhmm in plan for sym in bars.FUNDS]
    with ThreadPoolExecutor(max_workers=a.workers) as pool:
        paid = [x for pair in pool.map(one, jobs) for x in pair]
    n, usd = sum(1 for p in paid if p > 0), sum(paid)
    if n:
        fl.commit_ledger(n, usd)
    print(f"\n{n} file(s) bought, ${usd:.4f}. {ore.ATTRIBUTION}")


if __name__ == "__main__":
    main()
