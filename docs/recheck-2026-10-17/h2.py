"""Independent H2 (variance formulation), on the same inputs as h1.py: H2a equity-pooled t-tests of the volatility,
raw-variance and log-variance premia; H2b pooled over ALL pairs (the reader's definition)."""
import math, os
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "h1.py")).read().split("res, cls, vix_obs")[0])
from datetime import date
def series(idx, sym):
    cl = {d: v for d, v in px[sym]["adj"].items() if START <= d <= END}; dates = sorted(cl); s = iv[idx]; out = []; i = 0
    while i + H < len(dates):
        t = dates[i]
        if t not in s: i += 1; continue
        w = dates[i:i + H + 1]
        if (date.fromisoformat(w[-1]) - date.fromisoformat(t)).days > SPAN: i += 1; continue
        out.append((s[t] / 100, rv([cl[d] for d in w]))); i += H
    return out
forms = {"vol": lambda a, b: (a - b) * 100, "var": lambda a, b: (a * a - b * b) * 1e4, "logvar": lambda a, b: (math.log(a * a) - math.log(b * b)) * 100}
eq, allp = [], []
for idx, sym, k in PAIRS:
    s_ = series(idx, sym); allp += s_
    if k == "eq": eq += s_
for k, f in forms.items():
    x = [f(a, b) for a, b in eq]; m, t, p = ttest(x); print(f"H2a equity n={len(x)} {k:7} mean {m:8.2f} t {t:6.2f} p {p:.2e}")
def corr(x, y):
    mx, my = sum(x) / len(x), sum(y) / len(y)
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / math.sqrt(sum((a - mx) ** 2 for a in x) * sum((b - my) ** 2 for b in y))
def ac(x):
    m = sum(x) / len(x); d = [v - m for v in x]; return sum(d[t] * d[t - 1] for t in range(1, len(d))) / sum(v * v for v in d)
for k, f in forms.items():
    x = [f(a, b) for a, b in allp]; print(f"H2b all pairs {k:7} corr(premium, IV) {corr(x, [a for a, b in allp]):+.3f}  lag-1 {ac(x):+.3f}")
