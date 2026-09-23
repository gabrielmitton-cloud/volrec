#!/usr/bin/env python3
"""Everything a Bloomberg session needs, for one date, in one printout.

WHY THIS EXISTS
---------------
On 18 and 22 Sep 2026 the terminal instructions were worked out by hand: which two
expiries the recorder would pick, what strike range covers the wide band, when the
snapshot would land, what to write down. That arithmetic is where a session goes
wrong - on 18 and 22 Sep only one of the two expiries was pulled, and on 22 Sep a
24-minute gap was long enough for TSLA to move 0.14% and fail the price gate.

It reads the repository and prints; it fetches nothing, writes nothing, and never
touches the exports folder. Operations only (OPS-AGENT.md, item 1).

USAGE
-----
  python3 tools/bloomberg_prep.py                     # the next trading day
  python3 tools/bloomberg_prep.py --date 2026-09-22
  python3 tools/bloomberg_prep.py --date 2026-09-22 --symbols USO TSLA SPY
"""
import argparse
import csv
import math
import statistics as st
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "tools")]
from panel_health import US_MARKET_HOLIDAYS                  # noqa: E402  one list, owned there
import modelfree                                              # noqa: E402

DTE_WINDOW = (21, 45)          # surface.py's window; pressure_test.py checks they agree
WIDE_CAP = 0.60                # surface.py's cap on the wide band
GAP_LIMIT_MIN = 30             # bloomberg_compare.py's gate
FAST_MOVERS = {"TSLA": 10, "NVDA": 10}   # minutes; 22 Sep: TSLA moved 0.14% in 24
CRON_SINCE = "2026-09-16"      # the recorders moved to 14:47/14:57 UTC that day


def trading_day(d):
    return d.weekday() < 5 and d not in US_MARKET_HOLIDAYS


def listed_expiries(d):
    """Friday expiries inside the DTE window; a Friday holiday expires Thursday.
    This is what all eight names listed in the window on every day recorded so far."""
    out = []
    for n in range(DTE_WINDOW[0], DTE_WINDOW[1] + 7):
        e = d + timedelta(n)
        if e.weekday() != 4:
            continue
        if e in US_MARKET_HOLIDAYS:
            e -= timedelta(1)
        if DTE_WINDOW[0] <= (e - d).days <= DTE_WINDOW[1]:
            out.append(e)
    return out


def bbg_label(e):
    return f"{e.day:d}-{e:%b}-{e:%y}"


def last_spots(before):
    """The most recent recorded spot per symbol strictly before `before`."""
    path = ROOT / "data" / "surface.csv"
    best = {}
    for r in csv.DictReader(path.open(newline="")):
        if r["date"] < before.isoformat() and r.get("spot"):
            if r["symbol"] not in best or r["date"] > best[r["symbol"]][0]:
                best[r["symbol"]] = (r["date"], float(r["spot"]))
    return best


def landings(n=10):
    """Median quote time of each of the last n surface days since the cron moved, in
    minutes after 00:00 UTC. Days before CRON_SINCE ran on a different cron."""
    by_day = {}
    for r in csv.DictReader((ROOT / "data" / "surface.csv").open(newline="")):
        t = r.get("quote_time", "")
        if len(t) >= 16 and r["date"] >= CRON_SINCE:
            by_day.setdefault(r["date"], []).append(int(t[11:13]) * 60 + int(t[14:16]))
    days = sorted(by_day)[-n:]
    return {d: sorted(by_day[d])[len(by_day[d]) // 2] for d in days}


def pacific_offset(d):
    """Hours from UTC to US Pacific: -7 under DST (2nd Sun of March to 1st Sun of Nov)."""
    def nth_sunday(y, m, k):
        first = date(y, m, 1)
        return first + timedelta((6 - first.weekday()) % 7 + 7 * (k - 1))
    return -7 if nth_sunday(d.year, 3, 2) <= d < nth_sunday(d.year, 11, 1) else -8


def hhmm(m):
    m %= 24 * 60
    return f"{m // 60:02d}:{m % 60:02d}"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--date", help="the pull date, YYYY-MM-DD; default the next trading day")
    ap.add_argument("--symbols", nargs="+", default=["USO", "TSLA"])
    a = ap.parse_args()

    d = date.fromisoformat(a.date) if a.date else datetime.now(timezone.utc).date()
    if not a.date:
        while not trading_day(d):
            d += timedelta(1)
    print(f"Bloomberg session prep for {d:%a %d %b %Y}\n")
    if not trading_day(d):
        print("  NOT a trading day - the recorder will not run, so nothing can be matched.")
        return 1

    lst = listed_expiries(d)
    pair = modelfree.pick_pair([(e - d).days for e in lst])
    exps = [e for e in lst if (e - d).days in pair]
    print("1. EXPIRIES - the pair the recorder integrates. Pull BOTH (18 and 22 Sep pulled one).")
    for e in exps:
        print(f"     Exp = {bbg_label(e):<10} ({(e - d).days} days)")
    print("   Assumes Friday listings in the 21-45 day window, as on every day recorded.\n")

    spots = last_spots(d)
    print(f"2. STRIKES - set Exp FIRST, then Strikes 200 (or the maximum). The wide band is "
          f"+/-{WIDE_CAP:.0%}, so check the ladder reaches:")
    for s in a.symbols:
        if s not in spots:
            print(f"     {s:<5} no recorded spot yet")
            continue
        day, sp = spots[s]
        print(f"     {s:<5} low <= ${math.floor(sp * (1 - WIDE_CAP)):,}   "
              f"high >= ${math.ceil(sp * (1 + WIDE_CAP)):,}"
              f"   (spot ${sp:,.2f} on {day}; if spot has moved, use 0.4x and 1.6x the screen)")
    print()

    land = landings()
    off = pacific_offset(d)
    if land:
        lo, hi, med = min(land.values()), max(land.values()), int(st.median(land.values()))
        print(f"3. TIMING - the last {len(land)} surface snapshots landed {hhmm(lo)}-{hhmm(hi)} UTC, "
              f"median {hhmm(med)}")
        print(f"     = {hhmm(lo + 60 * off)}-{hhmm(hi + 60 * off)} Pacific, median "
              f"{hhmm(med + 60 * off)} (UTC{off:+d} on this date)")
    print("   Do NOT pull until the run has landed:")
    print("     python3 tools/panel_health.py     ->  'newest " + d.isoformat() + "' and a 'wide band' line")
    print(f"   Then pull within {GAP_LIMIT_MIN} minutes of the landed time"
          + "".join(f"; {s} within {m}" for s, m in FAST_MOVERS.items() if s in a.symbols)
          + " (fast movers first).")
    print(f"   Nothing by {hhmm(19 * 60 + 25 + 60 * off)} Pacific: gh workflow run record.yml, then "
          f"surface.yml, then re-check.\n")

    print("4. SAVE to ~/Documents/volrec-bloomberg/  (never inside the repository)")
    for s in a.symbols:
        print(f"     {s}_OMON_{d.isoformat()}.xlsx")
    print("   One file per symbol holding both expiry blocks; if they export separately, add")
    print("   _" + "/_".join(f"{e.day}{e:%b}" for e in exps) + " to the name.\n")

    print("5. WRITE DOWN and send back")
    print("     - the pull time, to the minute, in UTC (Pacific " + f"{-off:+d}".replace("+", "+ ") + " h)")
    print("     - the landed time panel_health printed")
    print("     - IFwd, R and IBrw from EVERY expiry block header")
    print("     - the lowest and highest strike each export reached")
    print("   Then: python3 tools/bloomberg_compare.py --date " + d.isoformat() + " --pull-time HH:MM")
    return 0


if __name__ == "__main__":
    sys.exit(main())
