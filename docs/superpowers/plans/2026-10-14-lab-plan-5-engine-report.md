# lab/ Plan 5: The Trust Engine and the Report Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish the side project:
- the trust engine, which reads a free option chain and says how far to trust it and what it would
  cost to trade;
- one private HTML report with the two charts (the Leak Map, the Break-Even curve);
- P5 judged;
- the paper section;
- the closing registration entry.

**Architecture:**
- `lab/engine.py` (pure, tested) uses the registered estimator on the free feed, H8's pilot
  calibration for the error bar and the free/OPRA spread ratio, and the recorder's own history for
  the "wide" flag.
- `run_leak.py` and `run_breakeven.py` also write JSON summaries.
- `lab/report.py` turns those into `~/Documents/volrec-licensed/lab-out/report.html`, with inline
  SVG and no external code. It stays private until Cboe replies.

**Tech Stack:** Python 3.14 stdlib.

## Global Constraints

- Python: `/Library/Frameworks/Python.framework/Versions/3.14/bin/python3`, `FRED_KEY=use-cache`.
- Exploratory; no registered file changes; r = 0 in lab/ (no FRED data).
- The engine's calibration constants are H8's PILOT aggregates (17 Sep - 9 Oct 2026, already
  published in H8-DRAFT.md); labelled as such, to be replaced by H8's registered window.
- The report is aggregates only, kept private; credit lines on every page.
- Push only when `tools/audit.py` reads N of N.

---

### Task 1: The trust engine (`engine.py`)

**Interfaces:**
- Produces: `PILOT` (`fund -> (mean |free - OPRA|, OPRA floor, free/OPRA half-spread ratio)`);
  `read(day_rows, history_rows) -> dict` with keys `vol`, `err`, `flags` (list of str),
  `cost_raw`, `cost_corrected` (volatility points, retail case), `n_rows`;
  `atm_halfspread_pts(rows) -> float|None`.

- [ ] **Step 1: Append the failing tests** (fixture in the recorder's format)

```python
eng = load("engine")
print("\n=== trust engine ===")
check("pilot calibration carried from H8-DRAFT (SPY gap 0.055, floor 0.010, ratio 2.07)", eng.PILOT["SPY"] == (0.055, 0.010, 2.07))


def _chain(day="2026-10-13", S=100.0, sig=0.25, frac=0.02, zero_wings=False, stale=False, step=2):
    rows = []
    for e, dte in (("2026-11-06", 24), ("2026-11-20", 38)):
        for K in range(70, 131, step):
            for k in "CP":
                p = black76(k, S, float(K), dte / 365.0, 0.0, sig)
                b, a = max(p * (1 - frac), 0.01), p * (1 + frac) + 0.02
                if zero_wings and abs(K - S) >= 20:
                    b = 0.0
                qt = "2026-10-13T15:02:00Z" if (stale and K % 10 == 0) else "2026-10-13T18:40:00Z"
                rows.append({"date": day, "symbol": "SPY", "spot": str(S), "quote_time": qt, "expiration": e,
                             "dte": str(dte), "type": k, "strike": str(float(K)), "moneyness": str(K / S),
                             "option_symbol": f"SPY{e[2:4]}{e[5:7]}{e[8:]}{k}{K * 1000:08d}",
                             "bid": f"{b:.4f}", "ask": f"{a:.4f}", "mid": f"{(a + b) / 2:.4f}", "vega": ""})
    return rows


hist = [r for d in ("2026-10-08", "2026-10-09") for r in _chain(day=d)]
g = eng.read(_chain(), hist)
check(f"a clean chain reads near its 25% and raises no flags ({g['vol']:.2f}, {g['flags']})", abs(g["vol"] - 25.0) < 1.5 and g["flags"] == [])
check(f"the error bar is SPY's pilot gap plus floor, 0.065 ({g['err']})", abs(g["err"] - 0.065) < 1e-12)
check("the corrected cost is the raw cost over SPY's free/OPRA ratio", abs(g["cost_corrected"] - g["cost_raw"] / 2.07) < 1e-12)
check("zero-bid wings are flagged", "zero-bid wings" in eng.read(_chain(zero_wings=True), hist)["flags"])
check("stale quotes are flagged", "stale quotes" in eng.read(_chain(stale=True), hist)["flags"])
check("a thin chain is flagged", "thin chain" in eng.read(_chain(step=15), hist)["flags"])
check("spreads wider than this fund's 90th percentile are flagged", "wide spreads" in eng.read(_chain(frac=0.10), hist)["flags"])
check("an empty chain reads nothing", eng.read([], hist)["vol"] is None)
```

- [ ] **Step 2: Confirm failure; Step 3: write `lab/engine.py`**

```python
#!/usr/bin/env python3
"""lab/ - the trust engine (EXPLORATORY). Feed it one fund's free option chain (the recorder's
format); it returns the 30-day volatility reading (the registered estimator, r = 0), an error bar,
trust flags, and the retail cost of trading the at-the-money straddle - raw, and corrected for the
free feed's wider quotes. Calibration constants are H8's PILOT readings (17 Sep - 9 Oct 2026,
H8-DRAFT.md), to be replaced by H8's registered window. Personal, non-commercial use only.

  FRED_KEY=use-cache python lab/engine.py            # the latest recorded day, all eight funds
"""
import csv
import statistics as st
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "tools")]
import modelfree                           # noqa: E402
from iv_convention import implied_vol, black76  # noqa: E402,F401

# fund: (mean |free - OPRA| at the snapshot minute, OPRA one-minute floor, free/OPRA ATM half-spread)
PILOT = {"SPY": (0.055, 0.010, 2.07), "QQQ": (0.038, 0.009, 1.31), "IWM": (0.092, 0.007, 1.27),
         "GLD": (0.024, 0.004, 0.98), "USO": (0.047, 0.051, 1.03), "TSLA": (0.056, 0.015, 1.22),
         "NVDA": (0.078, 0.014, 1.03), "AAPL": (0.021, 0.016, 0.99)}
RETAIL = 0.80
ZERO_BID_SHARE, STALE_SHARE, STALE_S, MIN_STRIKES, WIDE_PCT = 0.10, 0.10, 120, 10, 0.90


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _ts(s):
    import opra_reference
    return opra_reference.parse_ts(s)              # the project's tested parser (23 Sep 2026 lesson)


def atm_halfspread_pts(rows):
    """Median quoted half-spread / Black-76 vega (r = 0) of contracts within 2% of spot, 20-45 days."""
    out = []
    for r in rows:
        S, K, dte = _f(r["spot"]), _f(r["strike"]), _f(r["dte"])
        b, a = _f(r["bid"]) or 0.0, _f(r["ask"])
        if not (S and K and dte and a) or abs(K / S - 1) > 0.02 or not 20 <= dte <= 45 or a < b:
            continue
        T, mid = dte / 365.0, (a + b) / 2
        iv = implied_vol(r["type"], mid, S, K, T, 0.0)
        if not iv:
            continue
        v = iv * T ** 0.5
        d1 = (__import__("math").log(S / K) + v * v / 2) / v
        vega = S * T ** 0.5 * __import__("math").exp(-d1 * d1 / 2) / (2 * 3.141592653589793) ** 0.5 / 100
        if vega > 0:
            out.append((a - b) / 2 / vega)
    return st.median(out) if out else None


def read(day_rows, history_rows):
    if not day_rows:
        return {"vol": None, "err": None, "flags": ["no data"], "cost_raw": None, "cost_corrected": None, "n_rows": 0}
    sym = day_rows[0]["symbol"]
    got = modelfree.model_free_30d(day_rows, 0.0)
    vol = got[0] if got else None
    gap, floor, ratio = PILOT.get(sym, (None, None, None))
    flags = []
    bids = [_f(r["bid"]) or 0.0 for r in day_rows]
    if sum(1 for b in bids if b <= 0) / len(bids) > ZERO_BID_SHARE:
        flags.append("zero-bid wings")
    ts = sorted(_ts(r["quote_time"]) for r in day_rows if r.get("quote_time"))
    if ts:
        med = ts[len(ts) // 2]
        if sum(1 for t in ts if (med - t).total_seconds() > STALE_S) / len(ts) > STALE_SHARE:
            flags.append("stale quotes")
    near = min(day_rows, key=lambda r: abs(_f(r["dte"]) - 30))["expiration"]
    S = _f(day_rows[0]["spot"])
    strikes = {_f(r["strike"]) for r in day_rows if r["expiration"] == near and abs(_f(r["strike"]) / S - 1) <= 0.10}
    if len(strikes) < MIN_STRIKES:
        flags.append("thin chain")
    cost = atm_halfspread_pts(day_rows)
    past = {}
    for r in history_rows:
        if r["symbol"] == sym and r["date"] < day_rows[0]["date"]:
            past.setdefault(r["date"], []).append(r)
    hist = sorted(x for x in (atm_halfspread_pts(v) for v in past.values()) if x is not None)
    if cost is not None and len(hist) >= 2 and cost > hist[min(len(hist) - 1, int(WIDE_PCT * len(hist)))]:
        flags.append("wide spreads")
    cost_raw = 2 * RETAIL * cost if cost is not None else None
    return {"vol": vol, "err": (gap + floor) if gap is not None else None, "flags": flags, "cost_raw": cost_raw,
            "cost_corrected": cost_raw / ratio if (cost_raw is not None and ratio) else None, "n_rows": len(day_rows)}


def main():
    rows = list(csv.DictReader(open(ROOT / "data" / "surface.csv", newline="")))
    day = max(r["date"] for r in rows)
    print(f"lab/ trust engine (EXPLORATORY) - free feed, {day}. Error bars and the cost correction are H8's pilot "
          f"calibration (17 Sep - 9 Oct 2026).\n")
    for sym in PILOT:
        g = read([r for r in rows if r["symbol"] == sym and r["date"] == day], rows)
        if g["vol"] is None:
            print(f"  {sym:5s} no reading")
            continue
        c = f"{g['cost_raw']:.3f} raw / {g['cost_corrected']:.3f} corrected" if g["cost_raw"] is not None else "n/a"
        print(f"  {sym:5s} 30-day vol {g['vol']:6.2f} +/- {g['err']:.3f}   straddle cost {c} vol pts   "
              f"{'TRUST' if not g['flags'] else 'CHECK: ' + ', '.join(g['flags'])}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: All PASS; commit** ("lab/: the trust engine - reading, error bar, flags, cost").

---

### Task 2: JSON summaries for the report

- [ ] **Step 1:** In `lab/run_leak.py`, collect per fund (registered) `{w: {"paper", "kept", "leaks": {p: [v, lo, hi]}}}` for all four weights, plus the stress line (`block`, `dd50`, `dd95`, `ruin`); write `lab-out/leak_summary.json`. In `lab/run_breakeven.py`, collect per fund `{"index", "net_bins", "cost_bins", "crossing", "ci", "out", "p4"}`; write `lab-out/breakeven_summary.json`.
- [ ] **Step 2:** Re-run both; confirm the printed numbers are unchanged from the logged results.
- [ ] **Step 3:** Commit ("lab/: run scripts also write JSON summaries for the report").

---

### Task 3: The report (`report.py`)

- [ ] **Step 1:** Write `lab/report.py`: read both JSON files, render `lab-out/report.html` with:
  1. the question and a three-line answer;
  2. a Leak Map chart, cents kept per $1 by fund at 5% and 20%, the leaks stacked in their Shapley
     shares;
  3. a Break-Even chart per fund: net volatility points by index quintile, the retail cost
     beside it;
  4. the stress table;
  5. the predictions (P1-P5) as recorded;
  6. limitations and credit lines.

  The report is inline SVG, with tokens for light and dark, and readable at phone width.
- [ ] **Step 2:** Open it in the browser pane and check both charts read correctly at desktop and phone width.
- [ ] **Step 3:** Commit `lab/report.py` (the HTML stays in the private folder).

---

### Task 4: Close out

- [ ] **Step 1:** Judge P5 ("retention highest on SPY and lowest on USO") from the Leak Map as written and log it with a closing summary in `lab/REGISTRATION.md`.
- [ ] **Step 2:** Add the paper section to `PAPER-OUTLINE.md` (a new section 6, "What the data gap costs a retail investor", with the numbers and the limits).
- [ ] **Step 3:** HANDOFF and memory: the side project is complete; what stays private until Cboe replies.
- [ ] **Step 4:** Full suite, auditor N of N, push. Draft the resume bullets for Gabriel in chat.
