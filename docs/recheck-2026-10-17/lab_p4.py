"""Independent rebuild of the lab's P4 (weekly retail cost fraction vs the fund's own index) from the registration."""
import os as _os, sys as _sys
from pathlib import Path as _P
ROOT = str(_P(__file__).resolve().parents[2])                       # the volrec repo
WORK = _os.environ.get("RECHECK_WORK", _os.path.expanduser("~/volrec-recheck"))   # downloaded public data, outside the repo
import csv, glob, json, math, os, statistics as st
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

L = os.path.expanduser("~/Documents/volrec-licensed/opra-lab")
IV = json.load(open(WORK + "/iv.json"))
INDEX = {"SPY": "VIX", "QQQ": "VXN", "IWM": "RVX", "GLD": "GVZ", "USO": "OVX"}
GOOD_FRIDAYS = {"2016-03-25", "2017-04-14", "2018-03-30", "2019-04-19", "2020-04-10", "2021-04-02", "2022-04-15",
                "2023-04-07", "2024-03-29", "2025-04-18", "2026-04-03"}


def ny_utc(d, hh, mm):
    def sunday(m, n):
        x = date(d.year, m, 1); return x + timedelta(days=(6 - x.weekday()) % 7, weeks=n - 1)
    return datetime(d.year, d.month, d.day, hh + (4 if sunday(3, 2) <= d < sunday(11, 1) else 5), mm, tzinfo=timezone.utc)


def monthly_expiry(y, m):
    d = date(y, m, 1); d += timedelta(days=(4 - d.weekday()) % 7 + 14)
    return d - timedelta(days=1) if d.isoformat() in GOOD_FRIDAYS else d


def fnum(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def ts(s):
    return datetime.strptime(s[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)


def load(path, when):
    best = {}
    for r in csv.DictReader(open(path)):
        g = abs((ts(r["ts_recv"]) - when).total_seconds())
        s = r["symbol"]
        if g <= 120 and (s not in best or g < best[s][0]):
            best[s] = (g, fnum(r["bid_px_00"]), fnum(r["ask_px_00"]))
    out = defaultdict(lambda: defaultdict(dict))
    for s, (g, b, a) in best.items():
        rest = s[6:]
        out[datetime.strptime(rest[:6], "%y%m%d").date()][int(rest[7:]) / 1000][rest[6]] = (b, a)
    return out


def listed(path, expiry):
    ks = set()
    for r in csv.DictReader(open(path)):
        rest = r["raw_symbol"][6:]
        if len(rest) >= 15 and datetime.strptime(rest[:6], "%y%m%d").date() == expiry:
            ks.add(int(rest[7:]) / 1000)
    return ks


def mid(q):
    b, a = q
    return ((b or 0.0) + a) / 2 if a else None


def integrity(ch, F, lst):
    band10 = [k for k in lst if abs(k / F - 1) <= 0.10 + 1e-9]
    if len(band10) < 3:
        return False
    for k in band10:
        q = ch.get(k, {})
        if not all(t in q and q[t][1] and q[t][1] > 0 for t in "CP"):
            return False
    qs = [ch[k][t] for k in band10 for t in "CP"]
    sane = sum(1 for b, a in qs if 0 <= (b or 0) <= a and a - (b or 0) <= max(((b or 0) + a) / 2, 0.10)) / len(qs)
    if sane < 0.95:
        return False
    band5 = [k for k in ch if abs(k / F - 1) <= 0.05 + 1e-9 and all(t in ch[k] and ch[k][t][1] for t in "CP")]
    if not band5:
        return False
    imp = {k: mid(ch[k]["C"]) - mid(ch[k]["P"]) + k for k in band5}
    med = st.median(imp.values())
    hs = {k: (ch[k]["C"][1] - (ch[k]["C"][0] or 0)) / 2 + (ch[k]["P"][1] - (ch[k]["P"][0] or 0)) / 2 for k in band5}
    return sum(1 for k in band5 if abs(imp[k] - med) <= hs[k] + 0.005 * F) / len(band5) >= 0.90


res = defaultdict(list)
for sym, idx in INDEX.items():
    files = sorted(glob.glob(f"{L}/OPRA_LAB_{sym}_*_1430.csv") + glob.glob(f"{L}/OPRA_LAB_{sym}_*_1130.csv"))
    for p in files:
        d = date.fromisoformat(os.path.basename(p).split("_")[3])
        if d.weekday() != 2:
            continue
        hh = 11 if p.endswith("_1130.csv") else 14
        exps = []
        for k in range(0, 3):
            y, m = d.year + (d.month - 1 + k) // 12, (d.month - 1 + k) % 12 + 1
            e = monthly_expiry(y, m)
            if 20 <= (e - d).days <= 45:
                exps.append(e)
        if not exps:
            continue
        e = min(exps, key=lambda x: abs((x - d).days - 30))
        ch = load(p, ny_utc(d, hh, 30)).get(e, {})
        two = {k: q for k, q in ch.items() if "C" in q and "P" in q and q["C"][1] and q["P"][1]}
        if not two:
            continue
        kf = min(two, key=lambda k: abs(mid(two[k]["C"]) - mid(two[k]["P"])))
        F = kf + mid(two[kf]["C"]) - mid(two[kf]["P"])
        dp = f"{L}/DEF_LAB_{sym}_{d.isoformat()}.csv"
        if not os.path.exists(dp) or not integrity(ch, F, listed(dp, e)):
            continue
        sell = [k for k, q in two.items() if all(q[t][0] and q[t][0] > 0 and q[t][0] <= q[t][1] for t in "CP")]
        if not sell:
            continue
        K = min(sell, key=lambda k: abs(k - F))
        (cb, ca), (pb, pa) = ch[K]["C"], ch[K]["P"]
        frac = 0.80 * ((ca - cb) / 2 + (pa - pb) / 2) / ((cb + ca) / 2 + (pb + pa) / 2)
        prev = max(x for x in IV[idx] if x < d.isoformat())
        res[sym].append((d, IV[idx][prev], frac))


def ols_nw(x, y, lag=4):
    n = len(x); mx, my = sum(x) / n, sum(y) / n
    sxx = sum((a - mx) ** 2 for a in x); b = sum((a - mx) * (c - my) for a, c in zip(x, y)) / sxx
    u = [c - my - b * (a - mx) for a, c in zip(x, y)]; z = [(a - mx) * e for a, e in zip(x, u)]
    s = sum(v * v for v in z)
    for l in range(1, lag + 1):
        s += 2 * (1 - l / (lag + 1)) * sum(z[t] * z[t - l] for t in range(l, n))
    se = math.sqrt(s) / sxx
    return b, b - 1.96 * se, b + 1.96 * se


rises = 0
for sym, rows in res.items():
    rows.sort()
    b, lo, hi = ols_nw([r[1] for r in rows], [r[2] for r in rows])
    up = lo > 0; rises += up
    print(f"{sym}: {len(rows)} weekly samples; slope {b:+.5f} (95% NW {lo:+.5f}..{hi:+.5f}) -> {'RISES' if up else 'flat/falls'}")
print(f"P4: rises on {rises} of 5 (registered: at least 4) -> {'HOLDS' if rises >= 4 else 'FAILS'}")
