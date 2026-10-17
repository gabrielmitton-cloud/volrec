"""Independent H1 from the registration text, on Yahoo adjusted closes (not Alpaca) and Cboe/FRED index closes."""
import os as _os, sys as _sys
from pathlib import Path as _P
ROOT = str(_P(__file__).resolve().parents[2])                       # the volrec repo
WORK = _os.environ.get("RECHECK_WORK", _os.path.expanduser("~/volrec-recheck"))   # downloaded public data, outside the repo
import json, math
from datetime import date

px, iv = json.load(open(WORK + "/yahoo.json")), json.load(open(WORK + "/iv.json"))
PAIRS = [("VIX", "SPY", "eq"), ("VXN", "QQQ", "eq"), ("RVX", "IWM", "eq"), ("VXD", "DIA", "eq"), ("OVX", "USO", "com"),
         ("GVZ", "GLD", "com"), ("VXSLV", "SLV", "com"), ("VXGDX", "GDX", "sector"), ("VXXLE", "XLE", "sector"),
         ("VXEEM", "EEM", "intl"), ("EVZ", "FXE", "fx")]
START, END, H, SPAN = "2016-01-01", "2026-09-04", 21, 45


def c4(n):
    """E[sqrt(mean r^2)]/sigma for n zero-mean normal returns: a chi law with n degrees of freedom (the
    estimator is NOT demeaned, so the textbook n-1 factor is the wrong one - corrected 17 Oct)."""
    return math.sqrt(2 / n) * math.exp(math.lgamma((n + 1) / 2) - math.lgamma(n / 2))


def rv(closes):
    r = [math.log(b / a) for a, b in zip(closes, closes[1:])]
    return math.sqrt(252 * sum(x * x for x in r) / len(r)) / c4(len(r))


def betai(a, b, x):
    """Regularised incomplete beta, Lentz continued fraction."""
    if x <= 0 or x >= 1:
        return 0.0 if x <= 0 else 1.0
    lbeta = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log(1 - x)
    if x > (a + 1) / (a + b + 2):
        return 1 - betai(b, a, 1 - x)
    f, c, d = 1.0, 1.0, 0.0
    for i in range(400):
        m = i // 2
        num = 1.0 if i == 0 else (m * (b - m) * x / ((a + 2 * m - 1) * (a + 2 * m)) if i % 2 == 0
                                  else -((a + m) * (a + b + m) * x) / ((a + 2 * m) * (a + 2 * m + 1)))
        d = 1 + num * d; d = 1 / d if abs(d) > 1e-30 else 1e30
        c = 1 + num / c if abs(c) > 1e-30 else 1e30
        f *= c * d
        if abs(c * d - 1) < 1e-14:
            break
    return math.exp(lbeta) * (f - 1) / a


def ttest(x):
    n = len(x); m = sum(x) / n; sd = math.sqrt(sum((v - m) ** 2 for v in x) / (n - 1)); t = m / (sd / math.sqrt(n))
    return m, t, betai((n - 1) / 2, 0.5, (n - 1) / (n - 1 + t * t))


res, cls, vix_obs = {}, {}, []
for idx, sym, k in PAIRS:
    cl = {d: v for d, v in px[sym]["adj"].items() if START <= d <= END}
    dates = sorted(cl); s = iv[idx]; obs = []; i = 0
    while i + H < len(dates):
        t = dates[i]
        if t not in s:
            i += 1; continue
        w = dates[i:i + H + 1]
        if (date.fromisoformat(w[-1]) - date.fromisoformat(t)).days > SPAN:
            i += 1; continue
        obs.append((t, s[t] / 100 - rv([cl[d] for d in w])))
        i += H
    prem = [o[1] for o in obs]
    m, t, p = ttest(prem)
    res[f"{idx}/{sym}"] = (len(prem), m * 100, t, p, sum(v > 0 for v in prem) / len(prem))
    cls.setdefault(k, []).extend(prem)
    if idx == "VIX":
        vix_obs = obs
print(f"{'pair':12}{'N':>5}{'mean':>8}{'t':>7}{'p':>9}{'pos':>6}")
for k, (n, m, t, p, pos) in res.items():
    print(f"{k:12}{n:5}{m:+8.2f}{t:7.2f}{p:9.4f}{pos:6.0%}")
sig = [k for k, v in res.items() if v[3] < 0.05 and v[1] > 0]
print("significant at 0.05:", len(sig), "of", len(res))
ps = sorted((v[3], k) for k, v in res.items()); m_ = len(ps)
bh = max([i + 1 for i, (p, _) in enumerate(ps) if p <= (i + 1) / m_ * 0.05] or [0])
cm = sum(1 / j for j in range(1, m_ + 1))
by = max([i + 1 for i, (p, _) in enumerate(ps) if p <= (i + 1) / (m_ * cm) * 0.05] or [0])
print(f"BH survivors {bh}, BY survivors {by}")
for k in ("eq", "com", "fx"):
    m, t, p = ttest(cls[k]); print(f"class {k}: mean {m*100:+.2f} (t {t:.2f}, n {len(cls[k])})")
cf = cls["com"] + cls["fx"]; print(f"commodity+currency {sum(cf)/len(cf)*100:+.2f}")
# H1c: slope VIX3M - VIX9D on trading days in the window
days = [d for d in sorted(px["SPY"]["adj"]) if "2016-01-04" <= d <= END and d in iv["VIX3M"] and d in iv["VIX9D"]]
sl = [iv["VIX3M"][d] - iv["VIX9D"][d] for d in days]
print(f"H1c: slope positive on {sum(x > 0 for x in sl)/len(sl):.1%} of {len(sl)} days, mean {sum(sl)/len(sl):+.2f}")
norm = [p for t, p in vix_obs if t in iv["VIX3M"] and t in iv["VIX9D"] and iv["VIX3M"][t] - iv["VIX9D"][t] > 0]
inv = [p for t, p in vix_obs if t in iv["VIX3M"] and t in iv["VIX9D"] and iv["VIX3M"][t] - iv["VIX9D"][t] <= 0]
print(f"     VIX/SPY normal {sum(norm)/len(norm)*100:+.2f} (n {len(norm)}), inverted {sum(inv)/len(inv)*100:+.2f} (n {len(inv)})")
