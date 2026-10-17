"""Independent rebuild of the lab's straddle trades from the raw OPRA files (registration text + docstrings)."""
import os as _os, sys as _sys
from pathlib import Path as _P
ROOT = str(_P(__file__).resolve().parents[2])                       # the volrec repo
WORK = _os.environ.get("RECHECK_WORK", _os.path.expanduser("~/volrec-recheck"))   # downloaded public data, outside the repo
import csv, os, statistics as st
from datetime import datetime, date, timezone, timedelta
from collections import defaultdict

L = os.path.expanduser("~/Documents/volrec-licensed")
EARLY = {"2016-11-25", "2017-07-03", "2017-11-24", "2018-07-03", "2018-11-23", "2018-12-24", "2019-07-03", "2019-11-29",
         "2019-12-24", "2020-11-27", "2020-12-24", "2021-11-26", "2022-11-25", "2023-07-03", "2023-11-24", "2024-07-03",
         "2024-11-29", "2024-12-24", "2025-07-03", "2025-11-28", "2025-12-24"}


def ny_to_utc(d, hh, mm):
    """New York wall time -> UTC (US DST rules since 2007)."""
    y = d.year
    def sunday(m, n):
        x = date(y, m, 1); return x + timedelta(days=(6 - x.weekday()) % 7, weeks=n - 1)
    dst = sunday(3, 2) <= d < sunday(11, 1)
    return datetime(d.year, d.month, d.day, hh + (4 if dst else 5), mm, tzinfo=timezone.utc)


def ts(s):
    a, b = s.rstrip("Z").split(".")
    return datetime.strptime(a, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)


def fnum(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def chain(path, when, expiry):
    best = {}
    for r in csv.DictReader(open(path)):
        sym = r["symbol"]; rest = sym[6:]
        if datetime.strptime(rest[:6], "%y%m%d").date().isoformat() != expiry:
            continue
        g = abs((ts(r["ts_recv"]) - when).total_seconds())
        if g <= 120 and (sym not in best or g < best[sym][0]):
            best[sym] = (g, rest[6], int(rest[7:]) / 1000, fnum(r["bid_px_00"]), fnum(r["ask_px_00"]))
    out = defaultdict(dict)
    for g, t, k, b, a in best.values():
        out[k][t] = (b, a)
    return out


trades = list(csv.DictReader(open(f"{L}/lab-out/trades.csv")))
fdiff, kd, rows = [], 0, []
for tr in trades:
    if tr["registered"] != "1":
        continue
    e, x, sym = tr["entry"], tr["expiry"], tr["symbol"]
    hh, mm = (11, 30) if e in EARLY else (14, 30)
    p = f"{L}/opra-lab/OPRA_LAB_{sym}_{e}_{hh:02d}{mm:02d}.csv"
    if not os.path.exists(p):
        rows.append((tr, None, "no file")); continue
    ch = chain(p, ny_to_utc(date.fromisoformat(e), hh, mm), x)
    mids = {k: ((q["C"][0] or 0) + q["C"][1]) / 2 - ((q["P"][0] or 0) + q["P"][1]) / 2
            for k, q in ch.items() if "C" in q and "P" in q and q["C"][1] and q["P"][1]
            and (q["C"][0] or 0) <= q["C"][1] and (q["P"][0] or 0) <= q["P"][1]}
    kf = min(mids, key=lambda k: abs(mids[k]))
    F = kf + mids[kf]
    fdiff.append(abs(F - float(tr["F"])))
    ok = [k for k, q in ch.items() if "C" in q and "P" in q and all(q[t][0] and q[t][0] > 0 and q[t][1] and q[t][0] <= q[t][1] for t in "CP")]
    K = min(ok, key=lambda k: abs(k - F))
    (cb, ca), (pb, pa) = ch[K]["C"], ch[K]["P"]
    prem = (cb + ca) / 2 + (pb + pa) / 2
    hs = (ca - cb) / 2 + (pa - pb) / 2
    intr = abs(float(tr["S_exp"]) - K)
    rows.append((tr, {"mid": (prem - intr) / prem, "retail": (prem - 0.8 * hs - intr) / prem, "K": K}, ""))
cmp = [(tr, v) for tr, v, why in rows if v]
print(f"registered trades {sum(1 for t in trades if t['registered'] == '1')}; rebuilt {len(cmp)}; forward |diff| max {max(fdiff):.4f}")
for key, col in (("mid", "straddle_mid_ret"), ("retail", "straddle_retail_ret")):
    d = [abs(v[key] - float(tr[col])) for tr, v in cmp]
    print(f"straddle {key:6}: largest |diff| {max(d):.2e}; agree within 1e-9 on {sum(x < 1e-9 for x in d)} of {len(d)}")
by = defaultdict(list)
for tr, v in cmp:
    by[tr["symbol"]].append((v["mid"], v["retail"]))
for s, xs in sorted(by.items()):
    m, r_ = st.mean(a for a, _ in xs), st.mean(b for _, b in xs)
    print(f"  {s}: n={len(xs)} mean mid {m:+.3f}, retail {r_:+.3f}, kept {r_ / m:.2f}" if m > 0 else f"  {s}: n={len(xs)} mean mid {m:+.3f}, retail {r_:+.3f}")
ratio = defaultdict(list)
for tr in trades:
    if tr["registered"] == "1" and fnum(tr["atm_cost_pts"]) and fnum(tr["strip_cost_pts"]):
        ratio[tr["symbol"]].append(float(tr["strip_cost_pts"]) / float(tr["atm_cost_pts"]))
print("P3 strip/ATM medians from the trade log:", {s: round(st.median(v), 2) for s, v in sorted(ratio.items())})
