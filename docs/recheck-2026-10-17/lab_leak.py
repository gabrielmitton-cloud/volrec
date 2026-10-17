"""Independent rebuild of the lab's Leak Map (Plan 3) from the registration's mechanics."""
import os as _os, sys as _sys
from pathlib import Path as _P
ROOT = str(_P(__file__).resolve().parents[2])                       # the volrec repo
WORK = _os.environ.get("RECHECK_WORK", _os.path.expanduser("~/volrec-recheck"))   # downloaded public data, outside the repo
import csv, json, math, os, glob, itertools, statistics as st
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

LIC = os.path.expanduser("~/Documents/volrec-licensed")
L = f"{LIC}/opra-lab"
HERE = os.path.dirname(os.path.abspath(__file__))
IV = json.load(open(WORK + "/iv.json"))
INDEX = {"SPY": "VIX", "QQQ": "VXN", "IWM": "RVX", "GLD": "GVZ", "USO": "OVX"}
AB = {"SPY": (0.15, 0.10), "QQQ": (0.15, 0.10), "IWM": (0.15, 0.10), "GLD": (0.20, 0.10), "USO": (0.20, 0.10)}
EARLY = {"2016-11-25", "2017-07-03", "2017-11-24", "2018-07-03", "2018-11-23", "2018-12-24", "2019-07-03", "2019-11-29",
         "2019-12-24", "2020-11-27", "2020-12-24", "2021-11-26", "2022-11-25", "2023-07-03", "2023-11-24", "2024-07-03",
         "2024-11-29", "2024-12-24", "2025-07-03", "2025-11-28", "2025-12-24"}
N = lambda x: 0.5 * (1 + math.erf(x / math.sqrt(2)))


def ny_utc(d, hh, mm):
    def sunday(m, n):
        x = date(d.year, m, 1); return x + timedelta(days=(6 - x.weekday()) % 7, weeks=n - 1)
    return datetime(d.year, d.month, d.day, hh + (4 if sunday(3, 2) <= d < sunday(11, 1) else 5), mm, tzinfo=timezone.utc)


def fnum(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def chain(path, when, expiry):
    best = {}
    for r in csv.DictReader(open(path)):
        s = r["symbol"]; rest = s[6:]
        if datetime.strptime(rest[:6], "%y%m%d").date().isoformat() != expiry:
            continue
        g = abs((datetime.strptime(r["ts_recv"][:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc) - when).total_seconds())
        if g <= 120 and (s not in best or g < best[s][0]):
            best[s] = (g, rest[6], int(rest[7:]) / 1000, fnum(r["bid_px_00"]), fnum(r["ask_px_00"]))
    out = defaultdict(dict)
    for g, t, k, b, a in best.values():
        out[k][t] = (b, a)
    return out


def mid(q):
    return ((q[0] or 0) + q[1]) / 2


def b76(F, K, T, v, cp):
    if T <= 0 or v <= 0:
        return max(F - K, 0) if cp == "C" else max(K - F, 0)
    d1 = (math.log(F / K) + v * v * T / 2) / (v * math.sqrt(T)); d2 = d1 - v * math.sqrt(T)
    return F * N(d1) - K * N(d2) if cp == "C" else K * N(-d2) - F * N(-d1)


def req(C, P, S, K, a, b):
    rc = max(C + a * S - max(K - S, 0), C + b * S)
    rp = max(P + a * S - max(S - K, 0), P + b * K)
    return rc + P if rc >= rp else rp + C


bars = defaultdict(dict)
for r in csv.DictReader(open(f"{LIC}/lab-bars/lab_bars.csv")):
    bars[r["symbol"]][r["date"]] = float(r["raw_close"])

months = defaultdict(list)
for tr in csv.DictReader(open(f"{LIC}/lab-out/trades.csv")):
    if tr["registered"] != "1":
        continue
    sym, e, x = tr["symbol"], tr["entry"], tr["expiry"]
    hh, mm = (11, 30) if e in EARLY else (14, 30)
    ch = chain(f"{L}/OPRA_LAB_{sym}_{e}_{hh:02d}{mm:02d}.csv", ny_utc(date.fromisoformat(e), hh, mm), x)
    F = float(tr["F"])
    ok = sorted(k for k, q in ch.items() if "C" in q and "P" in q and all(q[t][0] and q[t][0] > 0 and q[t][1] and q[t][0] <= q[t][1] for t in "CP"))
    K = min(ok, key=lambda k: (abs(k - F), k))                     # ties -> the lower strike (the lab's convention)
    (cb, ca), (pb, pa) = ch[K]["C"], ch[K]["P"]
    path = []
    days = sorted(d for d in bars[sym] if e < d < x)
    for d in days:
        S = bars[sym][d]; T = (date.fromisoformat(x) - date.fromisoformat(d)).days / 365
        rp = glob.glob(f"{L}/OPRA_LAB_{sym}_{d}_1555.csv") + glob.glob(f"{L}/OPRA_LAB_{sym}_{d}_1255.csv")
        mark = None
        if rp:
            hh2, mm2 = (12, 55) if rp[0].endswith("_1255.csv") else (15, 55)
            c2 = chain(rp[0], ny_utc(date.fromisoformat(d), hh2, mm2), x)
            two = {k: q for k, q in c2.items() if "C" in q and "P" in q and q["C"][1] and q["P"][1]}
            if K in two and two:
                kf = min(two, key=lambda k: abs(mid(two[k]["C"]) - mid(two[k]["P"])))
                S = kf + mid(two[kf]["C"]) - mid(two[kf]["P"])
                mark = (mid(two[K]["C"]), mid(two[K]["P"]))
        if mark is None:
            v = IV[INDEX[sym]].get(d)
            if v is None:
                continue
            mark = (b76(S, K, T, v / 100, "C"), b76(S, K, T, v / 100, "P"))
        path.append((S, mark[0], mark[1]))
    months[sym].append({"K": K, "C": mid(ch[K]["C"]), "P": mid(ch[K]["P"]), "cost": 0.8 * ((ca - cb) / 2 + (pa - pb) / 2), "F": F,
                        "S_exp": float(tr["S_exp"]), "path": path})


def simulate(m, w, fr, a, b):
    """The registration's mechanics: limits cut n at ENTRY; a forced liquidation buys back at mark (+cost) and
    reopens under the 90%-of-wealth rule, which belongs to the liquidation mechanic (registered text)."""
    prem = m["C"] + m["P"]; cost = m["cost"] if "spreads" in fr else 0.0
    com = 0.0065 * 2 if "commissions" in fr else 0.0
    n0 = n = w / prem
    sold = prem - cost
    if "limits" in fr:
        due = req(m["C"], m["P"], m["F"], m["K"], a, b) - sold
        if due > 0:
            n = min(n, 0.9 / due)
    cash = 1 + n * sold - n * com; called = 0
    if "liquidation" in fr:
        for S, C, P in m["path"]:
            M = C + P; rq = req(C, P, S, m["K"], a, b)
            if n > 0 and cash < n * rq:
                called = 1
                cash -= n * (M + cost) + n * com
                n = 0.0
                now = M - cost
                if cash > 0 and rq > now > 0:
                    n = min(n0, 0.9 * cash / (rq - now))
                    cash += n * now - n * com
    cash -= n * abs(m["S_exp"] - m["K"])
    return cash - 1, called


FR = ["spreads", "limits", "liquidation", "commissions"]
mine = {}
for sym, ms in months.items():
    a, b = AB[sym]; mine[sym] = {}
    for w in (0.025, 0.05, 0.10, 0.20):
        val, calls = {}, 0
        for k in range(5):
            for S_ in itertools.combinations(FR, k):
                rs = [simulate(m, w, set(S_), a, b) for m in ms]
                val[frozenset(S_)] = sum(r for r, _ in rs) / len(rs)
                if len(S_) == 4:
                    calls = sum(c for _, c in rs)
        leaks = {}
        for f in FR:
            margins = []
            for order in itertools.permutations(FR):
                before = frozenset(order[:order.index(f)])
                margins.append(val[before] - val[before | {f}])
            leaks[f] = (sum(margins) / len(margins), min(margins), max(margins))
        mine[sym][w] = {"paper": val[frozenset()], "kept": val[frozenset(FR)], "leaks": leaks, "called": calls}
json.dump({s: {str(w): v for w, v in d.items()} for s, d in mine.items()}, open(WORK + "/leak_mine.json", "w"), default=list)
rec = json.load(open(f"{LIC}/lab-out/leak_summary.json"))
for sym in ("SPY", "QQQ", "IWM", "GLD", "USO"):
    for w in ("0.05", "0.2"):
        m_, r_ = mine[sym][float(w)], rec[sym]["weights"][w]
        ck = lambda d: f"{100 * d['kept'] / d['paper']:.1f}" if d["paper"] > 0 else "undef"
        print(f"{sym} w={w:4}: paper {m_['paper']*100:+.3f}% vs {r_['paper']*100:+.3f}% | kept {m_['kept']*100:+.3f}% vs {r_['kept']*100:+.3f}% | "
              f"cents {ck(m_)} vs {ck(r_)} | called {m_['called']} vs {r_['called']}")
        for f in FR:
            print(f"      {f:12} mine {m_['leaks'][f][0]*100:+.4f} [{m_['leaks'][f][1]*100:+.4f}, {m_['leaks'][f][2]*100:+.4f}]   lab {r_['leaks'][f][0]*100:+.4f} [{r_['leaks'][f][1]*100:+.4f}, {r_['leaks'][f][2]*100:+.4f}]")
