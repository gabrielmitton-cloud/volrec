# lab/ Plan 4: The Break-Even VIX Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** For each fund, find the level of its own volatility index above (or below) which a retail
seller's trading cost eats the straddle's premium. Judge prediction P4.

**Architecture:**
- `lab/breakeven.py` holds the pure statistics, proved on known answers: quintile bins, ordinary
  least squares with a Newey-West slope interval, the crossing restricted to the observed range,
  and a stationary-bootstrap interval for the crossing.
- `lab/run_breakeven.py` builds the two curves and prints them:
  - **the weekly cost curve:** every Wednesday at 14:30 New York, the ATM straddle on the standard
    monthly expiry nearest 30 days, 20-45 days out;
  - **the monthly premium curve:** Plan 2's trades, in volatility points.

**Tech Stack:** Python 3.14 stdlib; lab modules from Plans 1-3.

**Spec:** section 7; Q2; P4. **Registration:** `lab/REGISTRATION.md`.

## Global Constraints

- Python: `/Library/Frameworks/Python.framework/Versions/3.14/bin/python3`, `FRED_KEY=use-cache`.
- Exploratory; no registered file changes; r = 0; no FRED data; aggregates only on screen.
- No extrapolation: a crossing outside the observed index range is reported as "none in range".
- Push only when `tools/audit.py` reads N of N.

---

### Task 1: Definitions logged before the weekly data is read

- [ ] **Step 1: Append to `lab/REGISTRATION.md`'s Log, then commit**

```markdown
- 2026-10-14, before any weekly sample is read - Plan 4 definitions:
  - Weekly sample: each Wednesday 14:30 New York (11:30 on a half-day), per fund, the standard
    monthly expiry with 20-45 days left that is nearest 30 days; ATM = the sellable strike nearest
    the implied forward; the day must pass the registered integrity checks for that expiry.
  - Cost (volatility points) = 0.80 x (call + put quoted half-spreads) / (call + put Black-76 vega,
    r = 0, at each leg's own implied volatility). Cost fraction = 0.80 x (half-spreads) / straddle mid.
  - Premium (volatility points), from Plan 2's monthly trades = straddle P&L at mid per share /
    entry straddle vega. Net = premium - cost (both per trade, in volatility points).
  - x-axis: the fund's own index at the previous trading day's close (VIX, VXN, RVX, GVZ, OVX); VIX
    for all five shown beside it.
  - Break-even: OLS of net on x; the crossing x* = -a / b, reported only if inside the observed
    range of x, else "none in range" with the direction of the sign. 90% interval from 2,000
    stationary-bootstrap resamples of the months (block length by PPW), seed 20261014; resamples
    whose crossing is out of range are counted and reported, not dropped silently. Quintile bins of x
    (mean x, mean net, count) printed for every fund.
  - P4 ("the retail cost as a fraction of the premium rises with the index level on at least 4 of 5
    funds"): premium = the straddle's mid price at entry; "rises" = OLS slope of the weekly cost
    fraction on x positive with its 95% Newey-West interval (lag 4 weeks) above zero.
```

---

### Task 2: The statistics (`breakeven.py`)

**Interfaces:**
- Produces: `bins(x, y, q=5) -> list[tuple[float, float, int]]`;
  `ols(x, y) -> tuple[float, float]` (intercept, slope);
  `slope_ci(x, y, lag, z=1.96) -> tuple[float, float, float]` (slope, low, high; Bartlett Newey-West);
  `crossing(a, b, lo, hi) -> float|None`;
  `boot_crossing(x, y, block, n, seed, lo, hi) -> tuple[list[float], int]` (in-range crossings, count out of range).

- [ ] **Step 1: Append the failing tests to `lab/test_lab.py`**

```python
be = load("breakeven")
print("\n=== Break-Even VIX statistics ===")
_x = [float(v) for v in range(10, 41)]
_y = [0.2 * v - 4.0 for v in _x]                       # crosses zero at 20
a_, b_ = be.ols(_x, _y)
check(f"OLS recovers an exact line: intercept -4, slope 0.2 ({a_:.6f}, {b_:.6f})", abs(a_ + 4) < 1e-9 and abs(b_ - 0.2) < 1e-9)
check("the crossing of that line is at 20", abs(be.crossing(a_, b_, 10, 40) - 20.0) < 1e-9)
check("a crossing outside the observed range is not reported", be.crossing(a_, b_, 25, 40) is None)
check("a flat line has no crossing", be.crossing(1.0, 0.0, 10, 40) is None)
bb = be.bins(list(range(10)), [2 * v for v in range(10)], 5)
check(f"quintile bins of 10 points: 5 bins of 2, means right ({bb})", len(bb) == 5 and all(c == 2 for *_, c in bb) and bb[0][:2] == (0.5, 1.0))
_g2 = _r.Random(5)
_yn = [0.2 * v - 4.0 + _g2.gauss(0, 0.5) for v in _x * 4]
s_, lo_, hi_ = be.slope_ci(_x * 4, _yn, 4)
check(f"a real positive slope has an interval above zero ({lo_:.3f}..{hi_:.3f})", lo_ > 0 and lo_ < s_ < hi_)
_flat = [_g2.gauss(0, 1) for _ in _x * 4]
s2, lo2, hi2 = be.slope_ci(_x * 4, _flat, 4)
check(f"pure noise: the interval covers zero ({lo2:.3f}..{hi2:.3f})", lo2 < 0 < hi2)
cr, out_ = be.boot_crossing(_x * 4, _yn, 1.0, 300, 11, 10, 40)
cr.sort()
check(f"bootstrapped crossings cluster at 20 (median {cr[len(cr) // 2]:.2f}, {out_} out of range)",
      abs(cr[len(cr) // 2] - 20.0) < 1.0 and out_ == 0)
```

- [ ] **Step 2: Confirm failure; Step 3: write `lab/breakeven.py`**

```python
"""lab/ - Break-Even VIX statistics (EXPLORATORY): quintile bins, OLS with a Newey-West slope
interval, the crossing restricted to the observed range (no extrapolation), and a stationary
bootstrap interval for the crossing."""
import importlib.util as _iu
import random
from pathlib import Path

_s = _iu.spec_from_file_location("stress", Path(__file__).resolve().parent / "stress.py")
stress = _iu.module_from_spec(_s)
_s.loader.exec_module(stress)


def bins(x, y, q=5):
    pts = sorted(zip(x, y))
    n, out = len(pts), []
    for i in range(q):
        part = pts[i * n // q:(i + 1) * n // q]
        if part:
            out.append((sum(p[0] for p in part) / len(part), sum(p[1] for p in part) / len(part), len(part)))
    return out


def ols(x, y):
    n = len(x)
    mx, my = sum(x) / n, sum(y) / n
    sxx = sum((v - mx) ** 2 for v in x)
    b = sum((u - mx) * (v - my) for u, v in zip(x, y)) / sxx if sxx > 0 else 0.0
    return my - b * mx, b


def slope_ci(x, y, lag, z=1.96):
    """Slope with a Bartlett Newey-West standard error (series in time order)."""
    a, b = ols(x, y)
    n = len(x)
    mx = sum(x) / n
    u = [(xi - mx) * (yi - a - b * xi) for xi, yi in zip(x, y)]
    s = sum(v * v for v in u)
    for k in range(1, lag + 1):
        s += 2 * (1 - k / (lag + 1)) * sum(u[t] * u[t - k] for t in range(k, n))
    sxx = sum((xi - mx) ** 2 for xi in x)
    se = (s ** 0.5) / sxx if sxx > 0 else float("inf")
    return b, b - z * se, b + z * se


def crossing(a, b, lo, hi):
    if b == 0:
        return None
    x = -a / b
    return x if lo <= x <= hi else None


def boot_crossing(x, y, block, n, seed, lo, hi):
    idx = list(range(len(x)))
    got, out = [], 0
    for path in stress.stationary_paths(idx, block, n, len(idx), seed):
        a, b = ols([x[i] for i in path], [y[i] for i in path])
        c = crossing(a, b, lo, hi)
        if c is None:
            out += 1
        else:
            got.append(c)
    return got, out
```

- [ ] **Step 4: All PASS. Commit** ("lab/: Break-Even statistics - bins, OLS with a Newey-West slope interval, in-range crossing, bootstrap interval").

---

### Task 3: Safeguard

- [ ] **Step 1: Add to `tools/audit.py` after `lab-bootstrap-iid`**

```python
    ("lab-breakeven-extrapolates", "the Break-Even VIX reports a crossing outside the observed range",
     lambda w: _sub(w / "lab/breakeven.py", "    return x if lo <= x <= hi else None", "    return x"),
     "lab/ tests pass"),
```

- [ ] **Step 2: Commit; auditor `RESULT: 76 of 76`; push.**

---

### Task 4: The run (`run_breakeven.py`)

- [ ] **Step 1: Write `lab/run_breakeven.py`**

```python
#!/usr/bin/env python3
"""lab/ - the Break-Even VIX (EXPLORATORY). Weekly cost curve and monthly premium curve against each
fund's own volatility index; aggregates only.

  FRED_KEY=use-cache python lab/run_breakeven.py
"""
import importlib.util as iu
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "tools"), str(ROOT / "lab")]
import opra_reference as ore               # noqa: E402
from iv_convention import implied_vol      # noqa: E402


def _load(name):
    s = iu.spec_from_file_location(name, ROOT / "lab" / f"{name}.py")
    m = iu.module_from_spec(s)
    s.loader.exec_module(m)
    return m


bars_m, cal, fl, integ, tr, costs, be, sx = (_load(n) for n in (
    "bars", "tradecal", "fetch_lab", "integrity", "trades", "costs", "breakeven", "stress"))
FUNDS = ("SPY", "QQQ", "IWM", "GLD", "USO")
SEED = 20261014


def prev(series, day):
    ks = [d for d in series if d < day]
    return series[max(ks)] if ks else None


def atm(ch, F, T):
    """(cost in vol points, cost fraction of premium, straddle vega, straddle mid) or None."""
    K = tr.nearest_strike(ch, F)
    if K is None:
        return None
    c, p = ch[K]["C"], ch[K]["P"]
    mid = lambda q: ((q[0] or 0.0) + q[1]) / 2
    ivc, ivp = implied_vol("C", mid(c), F, K, T, 0.0), implied_vol("P", mid(p), F, K, T, 0.0)
    hc, hp = costs.half_spread(*c), costs.half_spread(*p)
    if not (ivc and ivp) or hc is None or hp is None:
        return None
    vega = tr.vega76(F, K, T, ivc) + tr.vega76(F, K, T, ivp)
    cost = costs.COST_CASES["retail"] * (hc + hp)
    prem = mid(c) + mid(p)
    return cost / vega, cost / prem, vega, prem, K


def monthly_expiries(day, trading):
    y, m = int(day[:4]), int(day[5:7])
    out = []
    for k in range(3):
        yy, mm = y + (m + k - 1) // 12, (m + k - 1) % 12 + 1
        out.append(cal.monthly_expiry(yy, mm, trading))
    return out


def weekly(sym, bars, vol, trading):
    rows = []
    for day in cal.weekly_days(sorted(trading)):
        exps = [e for e in monthly_expiries(day, trading)
                if 20 <= (date.fromisoformat(e) - date.fromisoformat(day)).days <= 45]
        if not exps:
            continue
        e = min(exps, key=lambda x: abs((date.fromisoformat(x) - date.fromisoformat(day)).days - 30))
        hhmm = cal.slot(day, "14:30")
        p, d = fl.LAB_DIR / f"{fl.lab_stem(sym, day, hhmm)}.csv", fl.LAB_DIR / f"{fl.def_stem(sym, day)}.csv"
        if not (p.exists() and d.exists()):
            continue
        ch = integ.chain_at(ore.load_opra(p), e, fl.ny_minute(day, hhmm))
        if not integ.check_chain(ch, integ.listed_strikes(d, e))[0]:
            continue
        F = integ.forward(ch)
        got = atm(ch, F, (date.fromisoformat(e) - date.fromisoformat(day)).days / 365.0) if F else None
        x = prev(vol[tr.INDEX[sym]], day)
        if got and x:
            rows.append({"day": day, "x": x, "vix": prev(vol["VIX"], day), "cost_pts": got[0], "cost_frac": got[1]})
    return rows


def monthly(sym, bars, vol, trading):
    rows = []
    for entry, expiry in cal.entries(sorted(trading)):
        hhmm = cal.slot(entry, "14:30")
        p, d = fl.LAB_DIR / f"{fl.lab_stem(sym, entry, hhmm)}.csv", fl.LAB_DIR / f"{fl.def_stem(sym, entry)}.csv"
        if not (p.exists() and d.exists()):
            continue
        ch = integ.chain_at(ore.load_opra(p), expiry, fl.ny_minute(entry, hhmm))
        if not integ.check_chain(ch, integ.listed_strikes(d, expiry))[0]:
            continue
        F = integ.forward(ch)
        got = atm(ch, F, (date.fromisoformat(expiry) - date.fromisoformat(entry)).days / 365.0) if F else None
        x = prev(vol[tr.INDEX[sym]], entry)
        if not (got and x):
            continue
        cost_pts, _f, vega, prem, K = got
        pnl = prem - abs(tr.settle(bars, sym, expiry) - K)
        rows.append({"day": entry, "x": x, "vix": prev(vol["VIX"], entry), "net": pnl / vega - cost_pts})
    return rows


def main():
    bars = bars_m.load()
    vol = json.load(open(ROOT / "data" / "market_vol.json"))
    trading = set(bars["SPY"])
    print("lab/ Break-Even VIX (EXPLORATORY). Net = straddle P&L at mid / vega - retail cost, volatility points.\n")
    p4 = 0
    for sym in FUNDS:
        w, m = weekly(sym, bars, vol, trading), monthly(sym, bars, vol, trading)
        xs, ys = [r["x"] for r in m], [r["net"] for r in m]
        lo, hi = min(xs), max(xs)
        a, b = be.ols(xs, ys)
        cx = be.crossing(a, b, lo, hi)
        blk = sx.ppw_block(ys)
        boots, out_ = be.boot_crossing(xs, ys, blk, 2000, SEED, lo, hi)
        boots.sort()
        ci = (f"90% {boots[int(0.05 * len(boots))]:.1f}..{boots[int(0.95 * len(boots)) - 1]:.1f}" if len(boots) > 20 else "too few")
        idx = tr.INDEX[sym]
        if cx is not None:
            head = f"break-even {idx} {cx:.1f} ({ci}; {out_} of 2000 resamples out of range)"
        else:
            sign = "positive" if a + b * hi > 0 else "negative"
            head = f"no break-even in {idx} {lo:.1f}..{hi:.1f}: net is {sign} across the range ({out_} of 2000 resamples out of range)"
        print(f"{sym}: monthly n={len(m)}, net = {a:+.3f} {b:+.4f} x {idx}; {head}")
        print("   quintiles (mean " + idx + ", mean net pts, n): " + "  ".join(f"{bx:.1f}: {by:+.2f} ({bn})" for bx, by, bn in be.bins(xs, ys)))
        wx, wf = [r["x"] for r in w], [r["cost_frac"] for r in w]
        s_, l_, h_ = be.slope_ci(wx, wf, 4)
        rises = l_ > 0
        p4 += rises
        print(f"   weekly n={len(w)}: retail cost / premium vs {idx}: slope {s_:+.5f} (95% {l_:+.5f}..{h_:+.5f}) -> "
              f"{'RISES' if rises else 'does not rise'}; cost in vol points by quintile: "
              + "  ".join(f"{bx:.1f}: {by:.3f}" for bx, by, _n in be.bins(wx, [r['cost_pts'] for r in w])))
        print()
    print(f"P4 (cost / premium rises with the index on >= 4 of 5): {p4} of 5 -> {'HOLDS' if p4 >= 4 else 'FAILS'}")
    print(f"\n{ore.ATTRIBUTION} Cboe index levels: Cboe Global Markets.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run when `lab/buy_days.py` has finished** (the weekly files):
  `FRED_KEY=use-cache /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 lab/run_breakeven.py 2>&1 | tee ~/Documents/volrec-licensed/lab-out/report-plan4.txt`.

- [ ] **Step 3: Log the results AFTER data in `lab/REGISTRATION.md` (P4 judged as written); commit; audit; push.**
