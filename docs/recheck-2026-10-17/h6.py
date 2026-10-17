"""Independent H6 from the registration + its 9 Oct details, on Yahoo OHLC (dividend-adjusted like Alpaca's
adjustment=all by scaling each bar by adjclose/close) and Cboe/FRED index closes."""
import os as _os, sys as _sys
from pathlib import Path as _P
ROOT = str(_P(__file__).resolve().parents[2])                       # the volrec repo
WORK = _os.environ.get("RECHECK_WORK", _os.path.expanduser("~/volrec-recheck"))   # downloaded public data, outside the repo
import json, math
from datetime import date

px, iv = json.load(open(WORK + "/yahoo.json")), json.load(open(WORK + "/iv.json"))
PAIRS = [("VIX", "SPY"), ("VXN", "QQQ"), ("RVX", "IWM"), ("VXD", "DIA"), ("OVX", "USO"), ("GVZ", "GLD"),
         ("VXSLV", "SLV"), ("VXEEM", "EEM"), ("EVZ", "FXE")]
START, END = "2016-01-04", "2026-10-08"
K = math.sqrt(8 / math.pi) * math.sqrt(1 / 252)


def nw_dm(d, lag=5):
    T = len(d); m = sum(d) / T; e = [x - m for x in d]
    v = sum(x * x for x in e) / T
    for k in range(1, lag + 1):
        v += 2 * (1 - k / (lag + 1)) * sum(e[t] * e[t - k] for t in range(k, T)) / T
    return m, m / math.sqrt(v / T) * math.sqrt((T - 1) / T), T


per, pooled_d, spikes_by_pair = {}, {}, {}
for idx, sym in PAIRS:
    y = px[sym]
    days = sorted(d for d in y["adj"] if d in y["high"] and d in y["low"] and d in y["close"] and START <= d <= END)
    f = {d: y["adj"][d] / y["close"][d] for d in days}
    bars = [(d, y["high"][d] * f[d], y["low"][d] * f[d], y["adj"][d]) for d in days]
    # Wilder ATR(14), seeded with the mean of the first 14 true ranges (first bar has no TR)
    atr, trs, A = {}, [], None
    for i in range(1, len(bars)):
        d, h, l, _ = bars[i]; pc = bars[i - 1][3]
        tr = max(h, pc) - min(l, pc)
        if A is None:
            trs.append(tr)
            if len(trs) == 14:
                A = sum(trs) / 14; atr[d] = A
        else:
            A = (13 * A + tr) / 14; atr[d] = A
    s = iv[idx]
    # spike flags on index days: I_s > 90th percentile of previous 252 closes; "after" = spike in last 21 index days
    idays = sorted(s)
    spike = {}
    for j, dd in enumerate(idays):
        if j >= 252:
            prev = sorted(s[x] for x in idays[j - 252:j])
            p90 = prev[int(math.ceil(0.9 * 252)) - 1]
            spike[dd] = s[dd] > p90
    after = {}
    for j, dd in enumerate(idays):
        after[dd] = any(spike.get(x, False) for x in idays[max(0, j - 20):j + 1])
    spikes_by_pair[idx] = after
    d_list = []
    for i in range(len(bars) - 1):
        t, h, l, c = bars[i]; t1, h1, l1, _ = bars[i + 1]
        if (date.fromisoformat(t1) - date.fromisoformat(t)).days > 5 or t not in s or t not in atr or h1 <= l1:
            continue
        target = math.log(math.log(h1 / l1))
        li = (math.log(K * s[t] / 100) - target) ** 2
        la = (math.log(atr[t] / c) - target) ** 2
        d_list.append((t, li, la, li - la))
        pooled_d.setdefault(t, []).append((idx, li - la))
    m, dm, T = nw_dm([x[3] for x in d_list])
    per[f"{idx}/{sym}"] = (T, sum(x[1] for x in d_list) / T, sum(x[2] for x in d_list) / T, m, dm)
print(f"{'pair':12}{'N':>6}{'MSLE IV':>9}{'MSLE ATR':>9}{'mean d':>9}{'DM-HLN':>8}")
for k, (T, a, b, m, dm) in per.items():
    print(f"{k:12}{T:6}{a:9.4f}{b:9.4f}{m:+9.4f}{dm:8.2f}")
print("IV lower in", sum(1 for v in per.values() if v[3] < 0), "of 9")
dates = sorted(pooled_d)
series = [sum(v for _, v in pooled_d[t]) / len(pooled_d[t]) for t in dates]
m, dm, T = nw_dm(series)
print(f"pooled: {T} dates, mean d {m:+.4f}, DM-HLN {dm:.2f}")
aft = [x for t, x in zip(dates, series) if any(spikes_by_pair[i].get(t, False) for i, _ in pooled_d[t])]
calm = [x for t, x in zip(dates, series) if not any(spikes_by_pair[i].get(t, False) for i, _ in pooled_d[t])]
ma, mc = sum(aft) / len(aft), sum(calm) / len(calm)
va = sum((x - ma) ** 2 for x in aft) / (len(aft) - 1); vc = sum((x - mc) ** 2 for x in calm) / (len(calm) - 1)
print(f"H6b: after spike {ma:+.4f} ({len(aft)} dates), calm {mc:+.4f} ({len(calm)}); diff {ma - mc:+.4f}, Welch t {(ma - mc) / math.sqrt(va / len(aft) + vc / len(calm)):.2f}")
