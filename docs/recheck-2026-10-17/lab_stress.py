"""Independent stress lab: monthly kept returns (w = 5%, all frictions) -> PPW block length, stationary
bootstrap of 10,000 ten-year paths, drawdowns, shortfall, ruin probability; plus the crash replays."""
import os as _os, sys as _sys
from pathlib import Path as _P
ROOT = str(_P(__file__).resolve().parents[2])                       # the volrec repo
WORK = _os.environ.get("RECHECK_WORK", _os.path.expanduser("~/volrec-recheck"))   # downloaded public data, outside the repo
import math, os, random, statistics as st
HERE = os.path.dirname(os.path.abspath(__file__))
src = open(f"{HERE}/lab_leak.py").read()
exec(src.split("FR = [")[0])
FR = {"spreads", "limits", "liquidation", "commissions"}
entries = {}
for tr in csv.DictReader(open(f"{LIC}/lab-out/trades.csv")):
    if tr["registered"] == "1":
        entries.setdefault(tr["symbol"], []).append((tr["entry"], tr["expiry"]))


def ppw_block(x):
    """Politis & White (2004) with Patton, Politis & White (2009): stationary-bootstrap block length."""
    n = len(x); m = sum(x) / n; d = [v - m for v in x]; g0 = sum(v * v for v in d) / n
    R = lambda k: sum(d[t] * d[t - k] for t in range(k, n)) / n
    rho = [R(k) / g0 for k in range(0, n // 2)]
    Kn = max(5, int(math.sqrt(math.log10(n)))); c = 2 * math.sqrt(math.log10(n) / n)
    mhat = None
    for k in range(1, len(rho) - Kn):
        if all(abs(rho[k + j]) < c for j in range(Kn)):
            mhat = k - 1; break
    mhat = mhat if mhat is not None else len(rho) - 1
    M = 2 * mhat
    lam = lambda s: 1.0 if abs(s) <= 0.5 else (2 * (1 - abs(s)) if abs(s) <= 1 else 0.0)
    if M == 0:
        return 1.0
    G = sum(lam(k / M) * abs(k) * R(abs(k)) for k in range(-M, M + 1))
    g = sum(lam(k / M) * R(abs(k)) for k in range(-M, M + 1))
    b = (2 * G * G / (2 * g * g)) ** (1 / 3) * n ** (1 / 3) if g else 1.0
    return max(1.0, min(b, n / 3))


for sym, ms in months.items():
    a, b = AB[sym]
    rets = [simulate(m, 0.05, FR, a, b)[0] for m in ms]
    ent = entries[sym]
    blk = ppw_block(rets)
    rng = random.Random(20261014); p = 1 / blk; n = len(rets)
    mdd, ruin, months_all = [], 0, []
    for _ in range(10000):
        eq, peak, dd, low = 1.0, 1.0, 0.0, 1.0
        i = rng.randrange(n)
        for t in range(120):
            if t and rng.random() < p:
                i = rng.randrange(n)
            r_ = rets[i]; months_all.append(r_)
            eq *= 1 + r_; peak = max(peak, eq); dd = max(dd, 1 - eq / peak); low = min(low, eq)
            i = (i + 1) % n
        mdd.append(dd); ruin += low < 0.5
    mdd.sort(); months_all.sort()
    es = lambda q: -sum(months_all[:int(len(months_all) * (1 - q))]) / int(len(months_all) * (1 - q))
    covid = [r_ for r_, (e, x) in zip(rets, ent) if e <= "2020-03-20" <= x]
    feb18 = [r_ for r_, (e, x) in zip(rets, ent) if e <= "2018-02-05" <= x]
    print(f"{sym}: block {blk:.1f}; max drawdown median {100*mdd[5000]:.1f}% p95 {100*mdd[9500]:.1f}% p99 {100*mdd[9900]:.1f}%; "
          f"ES95 {100*es(0.95):.2f}% ES99 {100*es(0.99):.2f}%; P(equity<0.5) {100*ruin/10000:.1f}%; "
          f"COVID trade {100*covid[0]:+.1f}%; Feb 2018 {100*feb18[0]:+.1f}%")
