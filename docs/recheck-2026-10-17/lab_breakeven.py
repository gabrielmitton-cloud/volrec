"""Independent Break-Even VIX point estimates (monthly net in vol points on the fund's own index) from the registration."""
import os as _os, sys as _sys
from pathlib import Path as _P
ROOT = str(_P(__file__).resolve().parents[2])                       # the volrec repo
WORK = _os.environ.get("RECHECK_WORK", _os.path.expanduser("~/volrec-recheck"))   # downloaded public data, outside the repo
import csv, json, math, os, sys
from datetime import date
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "lab_leak.py")).read().split("bars = defaultdict(dict)")[0])

phi = lambda x: math.exp(-x * x / 2) / math.sqrt(2 * math.pi)


def implied(price, F, K, T, cp):
    lo, hi = 1e-4, 5.0
    for _ in range(200):
        m = (lo + hi) / 2
        if b76(F, K, T, m, cp) > price:
            hi = m
        else:
            lo = m
    return (lo + hi) / 2


def vega(F, K, T, v):
    d1 = (math.log(F / K) + v * v * T / 2) / (v * math.sqrt(T))
    return F * phi(d1) * math.sqrt(T) / 100


rec = json.load(open(f"{LIC}/lab-out/breakeven_summary.json"))
by = defaultdict(list)
for tr in csv.DictReader(open(f"{LIC}/lab-out/trades.csv")):
    if tr["registered"] != "1":
        continue
    sym, e, x = tr["symbol"], tr["entry"], tr["expiry"]
    hh, mm = (11, 30) if e in EARLY else (14, 30)
    ch = chain(f"{L}/OPRA_LAB_{sym}_{e}_{hh:02d}{mm:02d}.csv", ny_utc(date.fromisoformat(e), hh, mm), x)
    F = float(tr["F"])
    ok = sorted(k for k, q in ch.items() if "C" in q and "P" in q and all(q[t][0] and q[t][0] > 0 and q[t][1] and q[t][0] <= q[t][1] for t in "CP"))
    K = min(ok, key=lambda k: (abs(k - F), k))
    (cb, ca), (pb, pa) = ch[K]["C"], ch[K]["P"]
    C, P = (cb + ca) / 2, (pb + pa) / 2
    T = (date.fromisoformat(x) - date.fromisoformat(e)).days / 365
    vg = vega(F, K, T, implied(C, F, K, T, "C")) + vega(F, K, T, implied(P, F, K, T, "P"))
    net = (C + P - abs(float(tr["S_exp"]) - K)) / vg - 0.8 * ((ca - cb) / 2 + (pa - pb) / 2) / vg
    idx = IV[INDEX[sym]]; prevd = max(d for d in idx if d < e)
    by[sym].append((idx[prevd], net))
for sym, pts in sorted(by.items()):
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    n = len(xs); mx, my = sum(xs) / n, sum(ys) / n
    b = sum((a - mx) * (c - my) for a, c in zip(xs, ys)) / sum((a - mx) ** 2 for a in xs); a0 = my - b * mx
    cross = -a0 / b
    srt = sorted(pts); q = [srt[round(i * n / 5):round((i + 1) * n / 5)] for i in range(5)]
    bins = [(round(sum(p[0] for p in g) / len(g), 2), round(sum(p[1] for p in g) / len(g), 3), len(g)) for g in q]
    rb = [(round(x_, 2), round(y_, 3), c_) for x_, y_, c_ in rec[sym]["net_bins"]]
    print(f"{sym}: n={n} crossing {cross:.2f} (lab {rec[sym]['crossing']:.2f}); slope {b:+.4f}")
    print(f"     bins mine {bins}\n     bins lab  {rb}")
