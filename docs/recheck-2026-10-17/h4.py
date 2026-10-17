"""Independent H4 (strike2) from the registration + hedged.py's docstrings (conventions only)."""
import os as _os, sys as _sys
from pathlib import Path as _P
ROOT = str(_P(__file__).resolve().parents[2])                       # the volrec repo
WORK = _os.environ.get("RECHECK_WORK", _os.path.expanduser("~/volrec-recheck"))   # downloaded public data, outside the repo
import csv, math, statistics as st
from collections import defaultdict
from datetime import date, timedelta

ROOT = ROOT
R = 0.0391
DROPPED = {"2026-09-28"}
HOLIDAYS = {date(2026, 11, 26), date(2026, 12, 25), date(2026, 9, 7)}   # NYSE closures near the window


def trading_between(a, b):
    d = a + timedelta(days=1)
    while d < b:
        if d.weekday() < 5 and d not in HOLIDAYS:
            return True
        d += timedelta(days=1)
    return False


def f(v):
    try:
        x = float(v)
        return x if x == x else None
    except (TypeError, ValueError):
        return None


divs = defaultdict(list)
for r in csv.DictReader(open(f"{ROOT}/data/dividends.csv")):
    divs[r["symbol"]].append((date.fromisoformat(r["ex_date"]), float(r["amount"])))


def adj_spot(sym, S, on, expiry):
    pv = sum(a * math.exp(-R * (ex - on).days / 365) for ex, a in divs[sym] if on < ex <= expiry)
    return S - pv


by = defaultdict(list)
for r in csv.DictReader(open(f"{ROOT}/data/surface.csv")):
    if r["date"] in DROPPED:
        continue
    by[(r["symbol"], r["option_symbol"])].append(r)

runs = []
for (sym, osym), rows in by.items():
    rows.sort(key=lambda r: r["date"])
    cur = [rows[0]]
    for r in rows[1:]:
        if trading_between(date.fromisoformat(cur[-1]["date"]), date.fromisoformat(r["date"])):
            runs.append(cur); cur = [r]
        else:
            cur.append(r)
    runs.append(cur)

res = []
for run in runs:
    if len(run) < 2:
        continue
    sym = run[0]["symbol"]; exp_ = date.fromisoformat(run[0]["expiration"])
    C = [f(r["mid"]) for r in run]; D = [f(r["delta"]) for r in run]; S = [f(r["spot"]) for r in run]
    if any(v is None for v in C + D + S):
        continue
    days = [date.fromisoformat(r["date"]) for r in run]
    St = [adj_spot(sym, s, d, exp_) for s, d in zip(S, days)]
    pi = C[-1] - C[0]
    for n in range(len(run) - 1):
        pi -= D[n] * (St[n + 1] - St[n])
        pi -= R * (C[n] - D[n] * St[n]) * (days[n + 1] - days[n]).days / 365
    m = f(run[0]["moneyness"]) or float(run[0]["strike"]) / S[0]
    res.append({"bp": pi / S[0] * 1e4, "m": m, "vol": f(run[0]["volume"]) or 0.0, "sym": sym, "d0": run[0]["date"]})


def tstat(x):
    m = sum(x) / len(x); sd = st.stdev(x); return m, m / (sd / math.sqrt(len(x)))


print(f"runs {len(res)} across {len({(r['sym']) for r in res})} underlyings")
B = [("deep OTM put", -1, 0.90), ("OTM put", 0.90, 0.97), ("at the money", 0.97, 1.03), ("OTM call", 1.03, 1.10), ("deep OTM call", 1.10, 99)]
for name, lo, hi in B:
    x = [r["bp"] for r in res if lo <= r["m"] < hi]
    m, t = tstat(x); print(f"  {name:14} n={len(x):5} mean {m:+.2f}bp t {t:.2f} neg {sum(v < 0 for v in x)/len(x):.0%}")
m, t = tstat([r["bp"] for r in res]); print(f"pooled n={len(res)} mean {m:+.2f}bp t {t:.2f}")
ud = defaultdict(list); dd = defaultdict(list)
for r in res:
    ud[(r["sym"], r["d0"])].append(r["bp"]); dd[r["d0"]].append(r["bp"])
m, t = tstat([sum(v) / len(v) for v in ud.values()]); print(f"underlying-day n={len(ud)} mean {m:+.2f} t {t:.2f}")
m, t = tstat([sum(v) / len(v) for v in dd.values()]); print(f"date n={len(dd)} mean {m:+.2f} t {t:.2f}")
