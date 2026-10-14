# lab/ Plan 3: Margin, the Leak Map and the Stress Lab Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Put every monthly straddle through Cboe customer margin with daily marking (Santa-Clara &
Saretto's mechanic), attribute the gap between paper and kept returns to four frictions by Shapley
values (the Leak Map), and stress the kept returns with a stationary bootstrap. Then judge
predictions P1 and P2.

**Architecture:** Three pure modules, each proved on known answers:
- `lab/margin_path.py`: one month under margin;
- `lab/leakmap.py`: the 16 friction combinations and the Shapley attribution;
- `lab/stress.py`: Patton-Politis-White block length, the stationary bootstrap, tail statistics.

`lab/run_leak.py` rebuilds each month from the bought OPRA files:
- entry chain at 14:30, or 11:30 on a half-day;
- daily marks from real OPRA quotes at 15:55 in stress months, otherwise Black-76 at the fund's
  own index level on the raw close.

It then prints aggregates.

**Tech Stack:** Python 3.14 stdlib; the lab modules from Plans 1-2.

**Spec:** sections 6 and 8, and 11 (Q1, Q4, Q5; P1, P2). **Registration:** `lab/REGISTRATION.md`.

## Global Constraints

- Python: `/Library/Frameworks/Python.framework/Versions/3.14/bin/python3` with `FRED_KEY=use-cache`.
- Exploratory; no registered file changes; no FRED data (r = 0 throughout).
- Aggregates only on screen; per-month rows go to `~/Documents/volrec-licensed/lab-out/`.
- Every printout ends with the Databento credit line.
- Push only when `tools/audit.py` reads N of N.

## File Structure

| File | Responsibility |
|---|---|
| `lab/margin_path.py` | `simulate(month, w, frictions, a, b)`: one month's return on $1 of capital, effective weight, liquidations |
| `lab/leakmap.py` | `FRICTIONS`, `shapley(value)`: Shapley shares, min/max across the 24 orders |
| `lab/stress.py` | `ppw_block(x)`, `stationary_paths(x, b, n_paths, length, seed)`, `max_drawdown`, `expected_shortfall`, `ruin_prob` |
| `lab/run_leak.py` | builds months from the files, runs the 16 combinations per fund, the margin table, the Leak Map, the stress table, P1/P2 |
| `lab/test_lab.py` | known-answer tests |
| `tools/audit.py` | mutants lab-shapley-single-order, lab-bootstrap-iid |

---

### Task 1: Choices logged before any margin or stress number is computed

- [ ] **Step 1: Append to `lab/REGISTRATION.md`'s Log**

```markdown
- 2026-10-14, before any margin, Leak Map or stress number is computed - Plan 3 choices:
  - One month = one R0 ATM straddle, held to expiry. Capital $1 at entry, r = 0. Premium written at mid
    = target weight w (2.5/5/10/20%), so n = w / mid straddle per share.
  - Frictions (each on or off; 16 combinations): **spreads** - sold at mid minus 80% of the quoted
    half-spread (retail), and every later trade pays the same per-share cost; **margin limits** - at
    entry n is cut so the margin due n x (requirement - proceeds) <= 0.9 of capital; **forced
    liquidation** - each trading day, if cash < n x requirement (Cboe: 100% of market value + a x S -
    OTM, minimum b), the position is bought back at mark (+ cost), then reopened on the same strike
    with n' = min(n, 0.9 x wealth / (requirement - proceeds)); **commissions** - $0.65 per contract per
    leg per trade on a $100,000 account (0.0065 x n per $1 per leg).
  - Daily marks: in the registered stress months, real OPRA quotes at 15:55 New York (12:55 on a
    half-day), mid of the trade's strike and expiry, with the chain's implied forward as S; on every
    other day, Black-76 (r = 0) at that day's raw close with volatility = the fund's own Cboe index
    close / 100. The model marks miss the smile and are stated as an approximation; the stress
    months, where margin calls cluster, use real quotes.
  - Margin rates as registered (SPY/QQQ/IWM 15%/10%; GLD/USO 20%/10%); the broker variant 40%/35%
    reported beside it.
  - Leak Map at w = 5%: paper = all off; kept = all on; each friction's leak is its Shapley value
    over the 24 orders, with min and max across orders; cents kept = mean(kept) / mean(paper),
    undefined when mean(paper) <= 0.
  - Stress: monthly kept returns (all on, w = 5%) per fund; stationary bootstrap, 10,000 paths of
    120 months, block length by Patton-Politis-White (sensitivity 1/3/6/12); max drawdown median /
    95th / 99th percentile, expected shortfall 95% / 99% of a month, probability equity falls below
    $0.50 within ten years. Replays: each stress month's kept return, and the worst month x 1.5.
    Seed 20261014.
  - August 2015 is dropped from the replays: the fund closes begin 4 Jan 2016, so its trade cannot
    be built. (Its OPRA marks were bought before this was seen; ~$0.10.)
  - Every table is printed for the registered months and, beside it, with the tradeable excluded
    months added back (Plan 2's sensitivity).
```

- [ ] **Step 2: Commit** (`git add lab/REGISTRATION.md`; message "lab/: Plan 3 choices logged before
  any margin, Leak Map or stress number is computed").

---

### Task 2: One month under margin (`margin_path.py`)

**Interfaces:**
- Consumes: `margin.short_straddle(C, P, S, Kc, Kp, a, b)`, `costs.COST_CASES`.
- Produces: `simulate(month: dict, w: float, frictions: set[str], a: float, b: float) -> dict` with
  keys `ret`, `w_eff`, `liquidations`. `month` keys: `K`, `C0`, `P0` (entry mids), `half0` (sum of
  the two legs' quoted half-spreads), `S0`, `days` (list of `(S, C, P)` daily marks before expiry),
  `settle` (`|S_exp - K|`). Friction names: `"spreads"`, `"limits"`, `"liquidation"`,
  `"commissions"`.

- [ ] **Step 1: Append the failing tests**

```python
mp = load("margin_path")
print("\n=== margin path ===")
_m = {"K": 100.0, "C0": 3.0, "P0": 3.0, "half0": 0.10, "S0": 100.0, "days": [(100.0, 3.0, 3.0)] * 3, "settle": 0.0}
r0 = mp.simulate(_m, 0.05, set(), 0.15, 0.10)
check(f"no frictions, expires worthless: keeps the whole 5% premium ({r0})", abs(r0["ret"] - 0.05) < 1e-12 and r0["liquidations"] == 0)
r1 = mp.simulate(dict(_m, settle=12.0), 0.05, set(), 0.15, 0.10)
check(f"no frictions, settles 12 on 6 of premium: loses 5% x (6-12)/6 = -5% ({r1['ret']:+.4f})", abs(r1["ret"] + 0.05) < 1e-12)
rs = mp.simulate(_m, 0.05, {"spreads"}, 0.15, 0.10)
check(f"spreads: sells 0.08 under mid on n = 0.05/6, so 5% - 0.08 x n ({rs['ret']:.6f})",
      abs(rs["ret"] - (0.05 - 0.08 * 0.05 / 6)) < 1e-12)
rc = mp.simulate(_m, 0.05, {"commissions"}, 0.15, 0.10)
check(f"commissions: 2 legs x 0.0065 x n ({rc['ret']:.6f})", abs(rc["ret"] - (0.05 - 2 * 0.0065 * 0.05 / 6)) < 1e-12)
big = mp.simulate(_m, 2.0, {"limits"}, 0.15, 0.10)
req = mg.short_straddle(3.0, 3.0, 100.0, 100.0, 100.0, 0.15, 0.10)
check(f"limits cut a 200% target to margin due <= 90% of capital (w_eff {big['w_eff']:.3f})",
      abs(big["w_eff"] - 6.0 * 0.9 / (req - 6.0)) < 1e-9)
crash = dict(_m, days=[(100.0, 3.0, 3.0), (60.0, 0.0, 40.0), (60.0, 0.0, 40.0)], settle=40.0)
nl = mp.simulate(crash, 0.20, {"limits"}, 0.15, 0.10)
lq = mp.simulate(crash, 0.20, {"limits", "liquidation"}, 0.15, 0.10)
check(f"a 40% crash triggers a margin call and a forced liquidation ({lq['liquidations']})", lq["liquidations"] >= 1 and nl["liquidations"] == 0)
check("with no call, the month's loss is the settlement loss", abs(nl["ret"] - nl["w_eff"] * (6.0 - 40.0) / 6.0) < 1e-9)
calm = mp.simulate(_m, 0.05, {"limits", "liquidation"}, 0.15, 0.10)
check("a quiet month at 5% never calls", calm["liquidations"] == 0 and abs(calm["ret"] - 0.05) < 1e-12)
```

- [ ] **Step 2: Run, confirm `FileNotFoundError` for `lab/margin_path.py`.** (`mg` is the margin
  module, already loaded earlier in `test_lab.py`.)

- [ ] **Step 3: Write `lab/margin_path.py`**

```python
"""lab/ - one month of a short ATM straddle under Cboe customer margin (EXPLORATORY).
Santa-Clara & Saretto (2009)'s mechanic: $1 of capital, premium written = target weight, margin
calls met from cash, forced liquidation when cash cannot cover the requirement, then reopening at
margin due <= 90% of wealth. Per-share prices; r = 0. Frictions switch on independently so the Leak
Map can attribute the losses (lab/leakmap.py)."""
import importlib.util as _iu
from pathlib import Path

_L = Path(__file__).resolve().parent


def _load(name):
    s = _iu.spec_from_file_location(name, _L / f"{name}.py")
    m = _iu.module_from_spec(s)
    s.loader.exec_module(m)
    return m


margin, costs = _load("margin"), _load("costs")
FRICTIONS = ("spreads", "limits", "liquidation", "commissions")
COMMISSION_PER_LEG = 0.0065          # $0.65 a contract on $100,000: per $1 of capital per share of n


def simulate(month, w, frictions, a, b):
    K, mid0 = month["K"], month["C0"] + month["P0"]
    cost = costs.COST_CASES["retail"] * month["half0"] if "spreads" in frictions else 0.0
    comm = 2 * COMMISSION_PER_LEG if "commissions" in frictions else 0.0
    n = w / mid0
    sold = mid0 - cost
    if "limits" in frictions:
        req0 = margin.short_straddle(month["C0"], month["P0"], month["S0"], K, K, a, b)
        if req0 > sold:
            n = min(n, 0.9 / (req0 - sold))
    w_eff = n * mid0
    cash = 1.0 + n * sold - n * comm
    calls = 0
    if "liquidation" in frictions:
        for S, C, P in month["days"]:
            V = C + P
            req = margin.short_straddle(C, P, S, K, K, a, b)
            if n > 0 and cash < n * req:
                calls += 1
                cash -= n * (V + cost) + n * comm          # buy back at mark plus the same cost
                n = 0.0
                sold_now = V - cost
                if cash > 0 and req > sold_now and sold_now > 0:
                    n = min(w / mid0, 0.9 * cash / (req - sold_now))
                    cash += n * sold_now - n * comm
    cash -= n * month["settle"]
    return {"ret": cash - 1.0, "w_eff": w_eff, "liquidations": calls}
```

- [ ] **Step 4: Run; all PASS. Commit** ("lab/: one month under Cboe customer margin with daily
  marking and forced liquidation, frictions switchable").

---

### Task 3: The Leak Map's attribution (`leakmap.py`)

**Interfaces:**
- Produces: `shapley(value: Callable[[frozenset], float], players=FRICTIONS) -> dict[str, tuple[float, float, float]]`
  (player -> (Shapley leak, min over orders, max over orders)), where leak = value(before) -
  value(after adding the player).

- [ ] **Step 1: Append the failing tests**

```python
lm = load("leakmap")
print("\n=== Leak Map attribution ===")
_add = {"spreads": 1.0, "limits": 2.0, "liquidation": 3.0, "commissions": 0.5}
v_add = lambda s: 10.0 - sum(_add[p] for p in s)
sh = lm.shapley(v_add)
check(f"additive frictions: each leak is its own effect, the same in every order ({sh})",
      all(abs(sh[p][0] - _add[p]) < 1e-12 and abs(sh[p][1] - sh[p][2]) < 1e-12 for p in _add))
v_int = lambda s: 10.0 - (4.0 if {"spreads", "liquidation"} <= s else 0.0)
si = lm.shapley(v_int)
check(f"an interaction is split evenly between the two, 2 and 2 ({si['spreads'][0]}, {si['liquidation'][0]})",
      abs(si["spreads"][0] - 2.0) < 1e-12 and abs(si["liquidation"][0] - 2.0) < 1e-12)
check("...and its range across orders is 0 to 4", si["spreads"][1] == 0.0 and si["spreads"][2] == 4.0)
check("a friction that changes nothing gets zero", si["commissions"][0] == 0.0 and si["limits"][0] == 0.0)
check("the leaks sum to paper minus kept", abs(sum(v[0] for v in sh.values()) - (v_add(frozenset()) - v_add(frozenset(_add)))) < 1e-12)
```

- [ ] **Step 2: Confirm failure; Step 3: write `lab/leakmap.py`**

```python
"""lab/ - the Leak Map's attribution (EXPLORATORY). Each friction's leak depends on the order the
frictions are added, so it is credited its Shapley value - the average over all orders - with the
minimum and maximum across orders reported beside it (as the main paper treats its decomposition)."""
from itertools import permutations

FRICTIONS = ("spreads", "limits", "liquidation", "commissions")


def shapley(value, players=FRICTIONS):
    leaks = {p: [] for p in players}
    for order in permutations(players):
        on = frozenset()
        for p in order:
            nxt = on | {p}
            leaks[p].append(value(on) - value(nxt))
            on = nxt
    return {p: (sum(v) / len(v), min(v), max(v)) for p, v in leaks.items()}
```

- [ ] **Step 4: All PASS. Commit** ("lab/: Leak Map attribution - Shapley values over the 24 orders, with the range").

---

### Task 4: The stress lab (`stress.py`)

**Interfaces:**
- Produces: `ppw_block(x) -> float`; `stationary_paths(x, b, n_paths, length, seed) -> list[list[float]]`;
  `max_drawdown(rets) -> float` (fraction of peak lost, compounding 1 + r, floored at a total loss);
  `expected_shortfall(x, level) -> float` (mean of the worst (1-level) share);
  `ruin_prob(paths, floor=0.5) -> float`.

- [ ] **Step 1: Append the failing tests**

```python
sx = load("stress")
print("\n=== stress lab ===")
import random as _r        # noqa: E402
_g = _r.Random(1)
_wn = [_g.gauss(0, 1) for _ in range(600)]
_ar, _p = [], 0.0
for _ in range(600):
    _p = 0.5 * _p + _g.gauss(0, 1); _ar.append(_p)
bw, ba = sx.ppw_block(_wn), sx.ppw_block(_ar)
check(f"PPW block length: white noise near 1 ({bw:.2f}), AR(1) rho=0.5 clearly longer ({ba:.2f})", bw < 2.0 and ba > 3.0)
_paths = sx.stationary_paths(_wn, 3.0, 4000, 120, 7)
_m = sum(sum(p) / len(p) for p in _paths) / len(_paths)
check(f"the bootstrap preserves the sample mean ({_m:+.4f} vs {sum(_wn) / len(_wn):+.4f})", abs(_m - sum(_wn) / len(_wn)) < 0.02)
check("paths have the requested length and are reproducible from the seed",
      all(len(p) == 120 for p in _paths[:5]) and sx.stationary_paths(_wn, 3.0, 3, 10, 7) == sx.stationary_paths(_wn, 3.0, 3, 10, 7))
_bl = sx.stationary_paths(list(range(100)), 50.0, 200, 20, 3)
_runs = sum(1 for p in _bl for i in range(1, len(p)) if p[i] == (p[i - 1] + 1) % 100) / sum(len(p) - 1 for p in _bl)
check(f"blocks keep neighbours together: with mean block 50, ~98% of steps continue a block ({_runs:.2f})", _runs > 0.9)
check("max drawdown of +10%, -50%, +20% is 50%", abs(sx.max_drawdown([0.10, -0.50, 0.20]) - 0.50) < 1e-12)
check("expected shortfall at 90% of 1..10 is the worst one, 1", sx.expected_shortfall(list(range(1, 11)), 0.90) == 1)
check("ruin: a path that halves counts, one that does not, does not",
      sx.ruin_prob([[-0.6], [0.1, -0.2]], 0.5) == 0.5)
```

- [ ] **Step 2: Confirm failure; Step 3: write `lab/stress.py`**

```python
"""lab/ - the stress lab (EXPLORATORY). Stationary bootstrap (Politis & Romano 1994) with the
Patton-Politis-White (2009) automatic block length; tail statistics on the resampled decades. A
bootstrap cannot draw a month worse than history's worst, so the replays in run_leak.py add the
worst month x 1.5, and every ruin probability is conditional on this sample's crashes."""
import math
import random


def _acov(xc, k):
    n = len(xc)
    return sum(xc[i] * xc[i + k] for i in range(n - k)) / n


def ppw_block(x):
    n = len(x)
    m = sum(x) / n
    xc = [v - m for v in x]
    g0 = _acov(xc, 0)
    if g0 <= 0:
        return 1.0
    kn = max(5, int(math.sqrt(math.log10(n))))
    c = 2.0 * math.sqrt(math.log10(n) / n)
    mmax = int(math.ceil(math.sqrt(n))) + kn
    rho = lambda k: _acov(xc, k) / g0 if k < n else 0.0
    mhat = next((mm for mm in range(0, mmax) if all(abs(rho(mm + k)) < c for k in range(1, kn + 1))), mmax)
    M = min(2 * mhat, mmax)
    lam = lambda t: 1.0 if abs(t) <= 0.5 else (2.0 * (1.0 - abs(t)) if abs(t) <= 1.0 else 0.0)
    if M == 0:
        return 1.0
    G = sum(lam(k / M) * abs(k) * _acov(xc, abs(k)) for k in range(-M, M + 1))
    g = sum(lam(k / M) * _acov(xc, abs(k)) for k in range(-M, M + 1))
    D = 2.0 * g * g
    b = (2.0 * G * G / D) ** (1 / 3) * n ** (1 / 3) if D > 0 else 1.0
    return min(max(b, 1.0), math.ceil(min(3 * math.sqrt(n), n / 3)))


def stationary_paths(x, b, n_paths, length, seed):
    rnd, n, p = random.Random(seed), len(x), 1.0 / max(b, 1.0)
    out = []
    for _ in range(n_paths):
        i, path = rnd.randrange(n), []
        while len(path) < length:
            path.append(x[i])
            i = rnd.randrange(n) if rnd.random() < p else (i + 1) % n
        out.append(path)
    return out


def max_drawdown(rets):
    eq = peak = 1.0
    worst = 0.0
    for r in rets:
        eq = max(eq * (1 + r), 0.0)
        peak = max(peak, eq)
        worst = max(worst, 1 - eq / peak if peak > 0 else 1.0)
    return worst


def expected_shortfall(x, level):
    s = sorted(x)
    k = max(1, int(round(len(s) * (1 - level))))
    return sum(s[:k]) / k


def ruin_prob(paths, floor=0.5):
    def ruined(p):
        eq = 1.0
        for r in p:
            eq *= 1 + r
            if eq < floor:
                return True
        return False
    return sum(1 for p in paths if ruined(p)) / len(paths)
```

- [ ] **Step 4: All PASS. Commit** ("lab/: stress lab - PPW block length, stationary bootstrap, drawdown, expected shortfall, ruin").

---

### Task 5: Safeguards

- [ ] **Step 1: Add to `tools/audit.py` after `lab-cost-roundtrip-charged`**

```python
    ("lab-shapley-single-order", "the Leak Map credits each friction from one order only",
     lambda w: _sub(w / "lab/leakmap.py", "    for order in permutations(players):", "    for order in [tuple(players)]:"),
     "lab/ tests pass"),
    ("lab-bootstrap-iid", "the bootstrap draws months independently, breaking up crash clusters",
     lambda w: _sub(w / "lab/stress.py", "    rnd, n, p = random.Random(seed), len(x), 1.0 / max(b, 1.0)", "    rnd, n, p = random.Random(seed), len(x), 1.0"),
     "lab/ tests pass"),
```

- [ ] **Step 2: Commit, run the auditor; expected `RESULT: 75 of 75`. Push.**

---

### Task 6: The run (`run_leak.py`)

**Interfaces:**
- Consumes: the bought files; `bars.load`, `tradecal.entries/slot/stress_days/STRESS_MONTHS`,
  `fetch_lab.LAB_DIR/lab_stem/def_stem/ny_minute`, `integrity.chain_at/check_chain/forward/listed_strikes`,
  `trades.nearest_strike/INDEX/settle`, `margin.RATES/BROKER`, `margin_path.simulate`,
  `leakmap.shapley/FRICTIONS`, `stress.*`, `costs.half_spread`, `iv_convention.black76`,
  `data/market_vol.json`.
- Produces: `~/Documents/volrec-licensed/lab-out/leak_months.csv` and a printed report: margin
  table (Q4), Leak Map (Q1, P1, P2), stress table (Q5), each beside its added-back sensitivity.

- [ ] **Step 1: Write `lab/run_leak.py`**

```python
#!/usr/bin/env python3
"""lab/ - margin, the Leak Map and the stress lab on every monthly straddle (EXPLORATORY).
Aggregates on screen; per-month rows to the private folder.

  FRED_KEY=use-cache python lab/run_leak.py
"""
import csv
import importlib.util as iu
import json
import statistics as st
import sys
from datetime import date
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "tools"), str(ROOT / "lab")]
import opra_reference as ore               # noqa: E402
from iv_convention import black76          # noqa: E402


def _load(name):
    s = iu.spec_from_file_location(name, ROOT / "lab" / f"{name}.py")
    m = iu.module_from_spec(s)
    s.loader.exec_module(m)
    return m


bars_m, cal, fl, integ, tr, mg, mp, lm, sx, costs = (_load(n) for n in (
    "bars", "tradecal", "fetch_lab", "integrity", "trades", "margin", "margin_path", "leakmap", "stress", "costs"))
FUNDS = ("SPY", "QQQ", "IWM", "GLD", "USO")
WEIGHTS = (0.025, 0.05, 0.10, 0.20)
SEED, PATHS, YEARS = 20261014, 10000, 10
OUT = fl.PRIVATE / "lab-out" / "leak_months.csv"


def real_mark(sym, day, expiry, K):
    hhmm = cal.slot(day, "15:55")
    p = fl.LAB_DIR / f"{fl.lab_stem(sym, day, hhmm)}.csv"
    if not p.exists():
        return None
    ch = integ.chain_at(ore.load_opra(p), expiry, fl.ny_minute(day, hhmm))
    q = ch.get(K)
    F = integ.forward(ch)
    if not q or "C" not in q or "P" not in q or F is None:
        return None
    mid = lambda x: ((x[0] or 0.0) + x[1]) / 2
    return (F, mid(q["C"]), mid(q["P"]))


def model_mark(S, K, T, vol):
    return (S, black76("C", S, K, T, 0.0, vol), black76("P", S, K, T, 0.0, vol))


def months_for(sym, bars, vol, stress):
    out = []
    days_all = sorted(bars[sym])
    for entry, expiry in cal.entries(sorted(bars["SPY"])):
        hhmm = cal.slot(entry, "14:30")
        p = fl.LAB_DIR / f"{fl.lab_stem(sym, entry, hhmm)}.csv"
        d = fl.LAB_DIR / f"{fl.def_stem(sym, entry)}.csv"
        if not (p.exists() and d.exists()):
            continue
        ch = integ.chain_at(ore.load_opra(p), expiry, fl.ny_minute(entry, hhmm))
        ok_, _det = integ.check_chain(ch, integ.listed_strikes(d, expiry))
        F = integ.forward(ch)
        K = tr.nearest_strike(ch, F) if F else None
        if K is None:
            continue
        c, pq = ch[K]["C"], ch[K]["P"]
        mid = lambda x: ((x[0] or 0.0) + x[1]) / 2
        hc, hp = costs.half_spread(*c), costs.half_spread(*pq)
        if hc is None or hp is None:
            continue
        idx = vol[tr.INDEX[sym]]
        marks, real_days = [], 0
        for day in (x for x in days_all if entry < x < expiry):
            m = real_mark(sym, day, expiry, K) if day in stress else None
            if m:
                real_days += 1
            else:
                lvl = idx.get(day)
                if lvl is None:
                    continue
                T = (date.fromisoformat(expiry) - date.fromisoformat(day)).days / 365.0
                m = model_mark(bars[sym][day][0], K, T, lvl / 100.0)
            marks.append(m)
        out.append({"entry": entry, "registered": ok_, "K": K, "C0": mid(c), "P0": mid(pq), "half0": hc + hp,
                    "S0": F, "days": marks, "real_days": real_days, "settle": abs(tr.settle(bars, sym, expiry) - K)})
    return out


def combos():
    return [frozenset(c) for r in range(5) for c in combinations(mp.FRICTIONS, r)]


def table(months, a, b):
    """{(w, frozenset): [monthly returns]}, plus liquidation counts and effective weights at w."""
    res, eff, liq = {}, {}, {}
    for w in WEIGHTS:
        for fs in combos():
            sims = [mp.simulate(m, w, fs, a, b) for m in months]
            res[(w, fs)] = [s["ret"] for s in sims]
            if fs == frozenset(mp.FRICTIONS):
                eff[w] = st.mean(s["w_eff"] for s in sims)
                liq[w] = sum(1 for s in sims if s["liquidations"])
    return res, eff, liq


def main():
    bars = bars_m.load()
    vol = json.load(open(ROOT / "data" / "market_vol.json"))
    stress = set(cal.stress_days(sorted(bars["SPY"])))
    print("lab/ margin, Leak Map, stress (EXPLORATORY). Short ATM straddle (R0), held to expiry.\n")
    rows, kept_series = [], {}
    for sym in FUNDS:
        allm = months_for(sym, bars, vol, stress)
        a, b = mg.RATES[sym]
        for label, ms in (("registered", [m for m in allm if m["registered"]]), ("added back", allm)):
            res, eff, liq = table(ms, a, b)
            paper, kept = st.mean(res[(0.05, frozenset())]), st.mean(res[(0.05, frozenset(mp.FRICTIONS))])
            sh = lm.shapley(lambda s: st.mean(res[(0.05, s)]))
            cents = f"{100 * kept / paper:5.1f} cents per $1" if paper > 0 else "  not defined (paper <= 0)"
            top = max(sh, key=lambda p: sh[p][0])
            print(f"{sym} [{label}] n={len(ms)}  paper {100 * paper:+.3f}%/mo  kept {100 * kept:+.3f}%/mo  -> {cents};"
                  f"  largest leak: {top}")
            for p in mp.FRICTIONS:
                print(f"      {p:12s} {100 * sh[p][0]:+.4f}%/mo  (orders: {100 * sh[p][1]:+.4f} to {100 * sh[p][2]:+.4f})")
            print("      margin: " + "  ".join(f"w {int(1000 * w) / 10:g}%: eff {100 * eff[w]:.2f}%, called in {liq[w]}"
                                                for w in WEIGHTS))
            if label == "registered":
                kept_series[sym] = res[(0.05, frozenset(mp.FRICTIONS))]
                bres, _e, bliq = table(ms, *mg.BROKER)
                print(f"      broker 40%/35%: kept {100 * st.mean(bres[(0.05, frozenset(mp.FRICTIONS))]):+.3f}%/mo, "
                      f"called in {bliq[0.05]} at w 5%")
                rows += [{"symbol": sym, "entry": m["entry"], "kept_5": r, "real_mark_days": m["real_days"]}
                         for m, r in zip(ms, kept_series[sym])]
        print()
    print("== stress lab: kept monthly returns at w = 5%, stationary bootstrap, 10,000 ten-year paths ==")
    for sym in FUNDS:
        x = kept_series[sym]
        b = sx.ppw_block(x)
        paths = sx.stationary_paths(x, b, PATHS, 12 * YEARS, SEED)
        dd = sorted(sx.max_drawdown(p) for p in paths)
        q = lambda f: dd[min(len(dd) - 1, int(f * len(dd)))]
        sens = "  ".join(f"b{bb}: ruin {100 * sx.ruin_prob(sx.stationary_paths(x, bb, 2000, 12 * YEARS, SEED)):.1f}%"
                         for bb in (1, 3, 6, 12))
        worst = min(x)
        print(f"  {sym} block {b:.1f}  maxDD median {100 * q(0.5):.1f}% p95 {100 * q(0.95):.1f}% p99 {100 * q(0.99):.1f}%"
              f"  ES95 {100 * sx.expected_shortfall(x, 0.95):+.2f}%  ES99 {100 * sx.expected_shortfall(x, 0.99):+.2f}%"
              f"  ruin(<$0.50) {100 * sx.ruin_prob(paths):.1f}%  worst month {100 * worst:+.2f}% (x1.5: {150 * worst:+.2f}%)")
        print(f"       block sensitivity: {sens}")
    print("\n== crash replays: kept return at w = 5% in each stress month's trade ==")
    by = {(r["symbol"], r["entry"][:7]): r["kept_5"] for r in rows}
    for mth in cal.STRESS_MONTHS[1:]:
        cells = [f"{s} {100 * by[(s, mth)]:+.2f}%" for s in FUNDS if (s, mth) in by]
        print(f"  {mth}: " + "  ".join(cells))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0]))
        wr.writeheader()
        wr.writerows(rows)
    print(f"\n{ore.ATTRIBUTION} Cboe index levels: Cboe Global Markets. Ruin odds are conditional on "
          f"2016-2026's crashes.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run** (after the stress-month marks are on disk):
  `FRED_KEY=use-cache /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 lab/run_leak.py 2>&1 | tee ~/Documents/volrec-licensed/lab-out/report-plan3.txt`.
  Read it before believing it: paper returns at w = 5% must equal 5% x Plan 2's straddle mid
  return; if not, stop and find why.

- [ ] **Step 3: Log the results** (AFTER data) in `lab/REGISTRATION.md`, with P1 and P2 judged as
  written, then commit, audit and push.
