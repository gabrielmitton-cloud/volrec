"""Independent rebuild of H8-DRAFT's pilot figures: calibration gaps and the ATM half-spread yardstick."""
import os as _os, sys as _sys
from pathlib import Path as _P
ROOT = str(_P(__file__).resolve().parents[2])                       # the volrec repo
WORK = _os.environ.get("RECHECK_WORK", _os.path.expanduser("~/volrec-recheck"))   # downloaded public data, outside the repo
import csv, os, sys, statistics as st
from collections import defaultdict
from datetime import datetime, timezone
sys.path.insert(0, ROOT + "/tools")
import independent_replica as IR

ROOT = ROOT
OP = os.path.expanduser("~/Documents/volrec-licensed/opra")
FUNDS = ["SPY", "QQQ", "IWM", "GLD", "USO", "TSLA", "NVDA", "AAPL"]
R = 0.0391


def ts(s):
    s = s.strip().rstrip("Z")
    if "+" in s[10:]:
        s = s[:s.rindex("+")]
    a, _, b = s.partition(".")
    return datetime.strptime(a, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc) if not b else \
        datetime.strptime(a + "." + b[:6], "%Y-%m-%dT%H:%M:%S.%f").replace(tzinfo=timezone.utc)


def f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


band = defaultdict(list)
for r in csv.DictReader(open(f"{ROOT}/data/surface.csv")):
    band[(r["date"], r["symbol"])].append(r)

gaps, gaps_s, yard = defaultdict(list), defaultdict(list), defaultdict(lambda: {"opra": [], "free": []})
for sym in FUNDS:
    for d in sorted({k[0] for k in band if k[1] == sym}):
        if not ("2026-09-17" <= d <= "2026-10-09") or d == "2026-09-28":
            continue
        p = f"{OP}/OPRA_{sym}_{d}.csv"
        if not os.path.exists(p):
            continue
        recs = defaultdict(list)
        for r in csv.DictReader(open(p)):
            recs["".join(r["symbol"].split())].append((ts(r["ts_recv"]), f(r["bid_px_00"]), f(r["ask_px_00"])))
        rows = band[(d, sym)]
        tq = sorted(ts(r["quote_time"]) for r in rows if r["quote_time"])
        snap = tq[len(tq) // 2].replace(second=0, microsecond=0)
        def at(r, when):
            rr = recs.get("".join(r["option_symbol"].split()))
            if not rr or when is None:
                return None
            g, x = min(((abs((y[0] - when).total_seconds()), y) for y in rr), key=lambda z: z[0])
            return x if g <= 120 else None
        for label, store, timer in (("own", gaps, lambda r: ts(r["quote_time"]) if r["quote_time"] else None), ("snap", gaps_s, lambda r: snap)):
            free_rows, opra_rows = [], []
            for r in rows:
                x = at(r, timer(r))
                if x is None or x[2] is None:
                    continue
                free_rows.append(r); opra_rows.append(dict(r, bid=str(x[1] or 0.0), ask=str(x[2])))
            if len(d) and free_rows:
                a = IR.h3_day(free_rows, [], R)["reg"]; b = IR.h3_day(opra_rows, [], R)["reg"]
                if a is not None and b is not None:
                    store[sym].append(a - b)
        if d <= "2026-10-09":
            for r in rows:
                m, dte, vg = f(r["moneyness"]), int(r["dte"]), f(r["vega"])
                if m is None or not vg or vg <= 0 or not (0.98 <= m <= 1.02) or not (20 <= dte <= 45):
                    continue
                fb, fa = f(r["bid"]) or 0.0, f(r["ask"])
                x = at(r, snap)
                if fa is None or x is None or x[2] is None:
                    continue
                yard[sym]["free"].append((fa - fb) / 2 / vg)
                yard[sym]["opra"].append((x[2] - (x[1] or 0.0)) / 2 / vg)

print("calibration, mean free - OPRA / mean |gap| (OPRA at each free quote's own time | at the snapshot minute):")
for s in FUNDS:
    g, h = gaps[s], gaps_s[s]
    print(f"  {s:5} days {len(g):2}: {st.mean(g):+.3f} / {st.mean(abs(x) for x in g):.3f}   | {st.mean(h):+.3f} / {st.mean(abs(x) for x in h):.3f}")
print("yardstick, median ATM half-spread / vega: OPRA | free | ratio | contracts")
for s in FUNDS:
    o, fr = st.median(yard[s]["opra"]), st.median(yard[s]["free"])
    print(f"  {s:5} {o:.3f} | {fr:.3f} | {fr / o:.2f} | {len(yard[s]['opra'])}")
