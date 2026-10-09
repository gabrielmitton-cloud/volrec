"""Unit tests for H6's pure pieces (samples/long/h6_range.py). No network, no keys.
Every case is hand-computable.   python tools/test_h6.py
"""
import importlib.util as iu
import random
import sys
from math import log, pi, sqrt
from pathlib import Path

R = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R))
_s = iu.spec_from_file_location("h6", R / "samples/long/h6_range.py")
h6 = iu.module_from_spec(_s); _s.loader.exec_module(h6)
fails = []


def check(name, cond):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}")
    if not cond:
        fails.append(name)


print("=== Wilder ATR ===")
bars = [("2026-01-%02d" % (i + 1), 101.0, 99.0, 100.0) for i in range(20)]   # TR = 2 every day
atr = h6.wilder_atr(bars)
check("first ATR appears after 14 true ranges (bar 15)", min(atr) == "2026-01-15")
check("constant true range 2 gives ATR 2 throughout", all(abs(v - 2.0) < 1e-12 for v in atr.values()))
gap = [("d0", 10, 9, 9.5), ("d1", 12, 11, 11.5)] + [("d%02d" % i, 12, 11, 11.5) for i in range(2, 16)]
check("true range uses the previous close when it gaps (12 - 9.5 = 2.5)",
      abs(h6.wilder_atr(gap, n=1)["d1"] - 2.5) < 1e-12)
seq = [("a", 0, 0, 10)] + [(f"b{i}", 11, 9, 10) for i in range(14)] + [("c", 14, 10, 12)]
a = h6.wilder_atr(seq)
check("Wilder smoothing: (13 x 2 + 4) / 14 after a TR of 4", abs(a["c"] - (13 * 2 + 4) / 14) < 1e-12)

print("\n=== forecasts and target ===")
check("IV -> range constant is sqrt(8/pi)/sqrt(252)", abs(h6.IV_TO_RANGE - sqrt(8 / pi) / sqrt(252)) < 1e-15)
ic = {b[0]: 20.0 for b in bars}
rows = h6.rows_for_pair(ic, bars)
r0 = rows[0]
check("the first row is the first day with an ATR, forecasting the NEXT bar", r0[0] == "2026-01-15")
check("target is ln(H/L) of the next bar", abs(r0[1] - log(101 / 99)) < 1e-12)
check("IV forecast = constant x level/100", abs(r0[2] - h6.IV_TO_RANGE * 0.20) < 1e-12)
check("ATR forecast = ATR / close", abs(r0[3] - 2.0 / 100.0) < 1e-12)
check("pivot forecast = (H - L) / close of day t", abs(r0[4] - 2.0 / 100.0) < 1e-12)
check("the last bar yields no row (no next day)", rows[-1][0] == bars[-2][0])
gapbars = bars[:16] + [("2026-02-20", 101.0, 99.0, 100.0)]
check("a next bar more than 5 calendar days away is a gap, not a forecast",
      all(r[0] != "2026-01-16" for r in h6.rows_for_pair(ic, gapbars)))
check("a missing index level drops the day",
      len(h6.rows_for_pair({k: v for k, v in ic.items() if k != "2026-01-15"}, bars)) == len(rows) - 1)
# No look-ahead: day t's row must carry day t+1's range. Bars whose ranges differ every day make
# "same day" and "next day" distinguishable (the auditor found the constant-range case could not).
vb = [("2026-03-%02d" % (i + 1), 100.0 + (i + 1), 100.0 - (i + 1) * 0.5, 100.0) for i in range(20)]
vr = h6.rows_for_pair({b[0]: 20.0 for b in vb}, vb)
i0 = [b[0] for b in vb].index(vr[0][0])
check("the target is the NEXT day's range, never the same day's (no look-ahead)",
      abs(vr[0][1] - log(vb[i0 + 1][1] / vb[i0 + 1][2])) < 1e-12
      and abs(vr[0][1] - log(vb[i0][1] / vb[i0][2])) > 1e-6)
check("loss is the squared log error", abs(h6.loss(0.02, 0.01) - log(2) ** 2) < 1e-12)

print("\n=== Diebold-Mariano with HLN ===")
random.seed(3)
noise = [random.gauss(0, 1) for _ in range(500)]
mu, stat, p = h6.dm_hln(noise, lag=0)
import analyze
_, _, t0, _ = analyze.newey_west(noise, 0)
check("HLN factor is sqrt((T-1)/T) on the Newey-West t", abs(stat - t0 * sqrt(499 / 500)) < 1e-12)
check("a pure-noise differential is not significant here", p > 0.05)
mu2, stat2, p2 = h6.dm_hln([x - 0.5 for x in noise], lag=5)
check("a clear negative differential is significant and negative", stat2 < 0 and p2 < 1e-6)

print("\n=== spikes ===")
seq = {f"d{i:04d}": 15.0 for i in range(300)}
seq["d0280"] = 40.0
f = h6.spike_flags(seq)
check("no spike can be flagged before 252 prior closes", not any(f[f"d{i:04d}"] for i in range(252)))
check("the spike day itself is flagged", f["d0280"])
check("the 20 days after it stay flagged (21-day window)", f["d0300"] if "d0300" in f else all(f[f"d{i:04d}"] for i in range(280, 300)))
check("the day before the spike is calm", not f["d0279"])
seq2 = {f"d{i:04d}": 15.0 for i in range(330)}; seq2["d0280"] = 40.0
f2 = h6.spike_flags(seq2)
check("21 trading days after the spike it is calm again (window = spike day + 20)", f2["d0300"] and not f2["d0301"])

print("\n=== Welch ===")
d_, t_, p_ = h6.welch([1.0, 2.0, 3.0, 4.0], [1.0, 2.0, 3.0, 4.0])
check("identical samples: difference 0, p 1", abs(d_) < 1e-12 and abs(p_ - 1) < 1e-9)
d_, t_, p_ = h6.welch([0.0, 0.1, -0.1] * 20, [5.0, 5.1, 4.9] * 20)
check("well-separated samples: negative difference, tiny p", d_ < 0 and p_ < 1e-10)

print("\n" + "=" * 52)
print(f"RESULT: {len(fails)} failure(s)" + (f": {fails}" if fails else ""))
sys.exit(1 if fails else 0)
