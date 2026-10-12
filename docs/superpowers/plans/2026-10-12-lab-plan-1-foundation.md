# lab/ Plan 1: Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Lay the lab's foundation: its registration committed before any purchase, the pure cost,
integrity and margin functions proved on known answers, a capped purchasing tool, and the
5 Feb 2018 test day bought and verified.

**Architecture:** A new top-level `lab/` folder of small stdlib modules. They import the registered
code read-only (`modelfree`, `tools/opra_reference`, `tools/iv_convention`) and never modify it. Tests
follow the repository's own style: a script that prints PASS/FAIL per case and exits non-zero on
any failure (as `tools/test_h8.py`), wired into `tools/pressure_test.py`, with auditor mutants in
`tools/audit.py` proving the guards fail when broken.

**Tech Stack:** Python 3.14 (framework install), stdlib + `requests`; Databento HTTP API via
`tools/opra_reference.call`; git for the private ledger.

**Spec:** `docs/superpowers/specs/2026-10-12-retail-vrp-audit-design.md` (rev 2). Later plans:
Plan 2, trades + Leak Map + stress; Plan 3, Break-Even VIX; Plan 4, the trust engine and the
report.

## Global Constraints

- Python: `/Library/Frameworks/Python.framework/Versions/3.14/bin/python3`, always with
  `FRED_KEY=use-cache` (CLAUDE.md). Never bare `python3`.
- Exploratory: nothing in `lab/` edits a registered file, verdict, threshold or reader.
- Lab budget: own cap **$75** (`LAB_BUDGET_USD = 75.00`), ledger tag `-lab`; the $100 lifetime cap
  (`opra_reference.LIFETIME_CAP_USD`) also applies. Every request is priced first.
- Lab dates: nothing bought or read dated after **2026-08-31** (`LAB_END`); nothing before
  **2015-08-01** (`LAB_START`, for the Aug 2015 crash replay).
- Licensed data never enters the public repo. Lab files live in
  `~/Documents/volrec-licensed/opra-lab/`, excluded from the private repo's git. The ledger is the
  private repo's `opra/spend.csv`, committed and pushed there after each purchase batch.
- Every OPRA-derived printout carries "Data provided by Databento (OPRA consolidated NBBO).
  Aggregates only."
- Margin rates, from the Cboe Margin Manual (30 Nov 2021), customer margin account, short options:
  ETF tracking a broad-based index 15% / minimum 10%; equity and other ETFs 20% / minimum 10%; a
  short put plus short call on the same underlying is the greater requirement plus the other
  side's proceeds.
- Push only when `tools/audit.py` reads N of N. Commits end with
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- In zsh, never put a multi-word command in a variable.

## File Structure

| File | Responsibility |
|---|---|
| `lab/REGISTRATION.md` | the rules, cases, margin values, thresholds, questions and predictions, committed before any purchase |
| `lab/costs.py` | half-spreads, the four cost cases, straddle cost, volatility-point conversion, strip cost |
| `lab/integrity.py` | OSI parsing, one expiry's chain at one moment, the implied forward, the three integrity checks |
| `lab/margin.py` | Cboe customer margin for a short put, short call and short straddle |
| `lab/fetch_lab.py` | capped, dated, priced-first OPRA purchases into `opra-lab/`, ledger in the private repo |
| `lab/verify_day.py` | runs the integrity checks on a bought day and prints aggregates |
| `lab/test_lab.py` | known-answer tests for all of the above |
| `tools/pressure_test.py` | new checks: lab tests pass, the cap, the dates, the data folder outside the repo |
| `tools/audit.py` | new mutants: lab-cap-ignored, lab-date-range-ignored, lab-margin-ignores-otm |

---

### Task 1: The registration, committed before anything is bought

**Files:**
- Create: `lab/REGISTRATION.md`

**Interfaces:**
- Produces: the constants later tasks copy verbatim: `COST_CASES`, `COMMISSIONS`, `RATES`,
  `BROKER`, `LAB_BUDGET_USD`, `LAB_START`, `LAB_END`, and the integrity thresholds (`BAND`,
  `PARITY_BAND`, `MIN_STRIKES`, `SANE_SHARE`, `PARITY_SHARE`, `DIV_ALLOW`).

- [ ] **Step 1: Write `lab/REGISTRATION.md`**

```markdown
# lab/ registration - the retail implementation audit (EXPLORATORY)

**Committed 12 Oct 2026, before any lab purchase or backtest.** The commit date is the evidence.
Design: `docs/superpowers/specs/2026-10-12-retail-vrp-audit-design.md` (rev 2). This is not a
registered hypothesis of the main project; it changes no registered file, number or verdict.

## What is fixed here, before any data
- **Funds:** SPY, QQQ, IWM, GLD, USO.
- **Dates:** trades and samples 4 Jan 2016 - 31 Aug 2026. Nothing bought or read after
  31 Aug 2026 (clear of H5e from 23 Sep, H7 from 9 Oct, H8 from 1 Dec 2026). The one earlier
  purchase is August 2015's daily marks, for a crash replay only.
- **Trades:** entry the first trading day after each standard monthly expiry, 14:30 New York;
  the next standard monthly expiry, 28-35 days out; held to expiry, settled at intrinsic on the
  fund's RAW close. Primary: short ATM straddle. Secondary: short 5% OTM strangle. Cross-check:
  synthetic 30-day variance swap on the Cboe indices.
- **Rules:** R0 always sell. R1 sell only when the fund's index exceeds its trailing 21-day
  realised volatility. R2 size inversely to the index level. R3 skip the month for all five funds
  when VIX3M < VIX.
- **Cost cases** (fraction of the quoted half-spread, entry only): mid 0, timed 0.30,
  retail 0.80 (headline), quoted 1.00. Commissions $0 and $0.65 per contract; the Leak Map uses
  $0.65.
- **Margin** (Cboe Margin Manual, 30 Nov 2021, customer margin account): SPY, QQQ, IWM a = 15%,
  b = 10%; GLD, USO a = 20%, b = 10%. Short put M = max(P + aS - OTM, P + bK); short call
  M = max(C + aS - OTM, C + bS); straddle = the greater side's requirement plus the other side's
  proceeds. Broker variant a = 40%, b = 35% (Santa-Clara & Saretto's E-Trade example).
  Liquidation mechanic as Santa-Clara & Saretto (2009): $1 a month, target weights 2.5/5/10/20%,
  calls met from cash, liquidation at the close when cash runs out, reopen at margin <= 90% of
  wealth.
- **Integrity, every day bought** (fails the day if any check fails):
  1. completeness: within +/-10% of the implied forward, at least 10 strikes, and every strike
     present in the file for that expiry has both a call and a put quoted (ask > 0) within 120 s
     of the minute;
  2. sane spreads: at least 95% of those quotes have 0 <= bid <= ask and ask - bid <= max(mid,
     $0.10);
  3. put-call parity: within +/-5% of the forward, at least 90% of strikes have
     |(C_mid - P_mid + K) - median| <= (call half-spread + put half-spread) + 0.005 x forward.
- **Budget:** lab cap $75, inside the $100 lifetime cap; priced first; never bought twice.
- **Leak Map:** R0 ATM straddle, 5% target weight, retail case; leaks in the order spreads,
  margin limits, forced liquidation, commissions; each leak credited its Shapley value over all
  24 orders, with the min and max across orders; cents kept per $1 undefined when the paper mean
  is not positive. The free-data estimate error is a separate bar, 2026 only, never subtracted.
- **Break-Even VIX:** weekly Wednesday 14:30 New York cost samples; premium from the monthly
  trades (headline) and weekly entries (robustness, Newey-West); index quintile bins with a linear
  fit; stationary-bootstrap interval; no extrapolation beyond the highest index level observed.
- **Stress:** stationary bootstrap, 10,000 ten-year paths, Patton-Politis-White block length
  with 1/3/6/12-month sensitivity; replays of Aug 2015, Feb 2018, Dec 2018, Mar 2020, Jun 2022,
  Aug 2024, Apr 2025, and the worst month x 1.5.
- **Deliberately not run:** the Cboe-method replica against GVZ/OVX on historical OPRA.

## Questions
Q1 the Leak Map; Q2 the Break-Even VIX; Q3 strip cost over ATM cost; Q4 effective weight and
liquidations under margin; Q5 bootstrap tails; Q6 the free-data estimate error (pilot seen
12 Oct 2026, measured, not predicted).

## Predictions (made before any lab data is bought)
- P1: at the retail case the straddle keeps under 50 cents per $1 on at least 3 of 5 funds.
- P2: spreads are the largest leak by Shapley share on at least 3 of 5 funds.
- P3: the strip costs at least twice the ATM estimate.
- P4: the retail cost as a fraction of the premium rises with the index level on at least 4 of
  5 funds.
- P5: retention is highest on SPY and lowest on USO.

## Log (dated; marked before or after any lab data)
- 2026-10-12, before any data: registered.
```

- [ ] **Step 2: Commit**

```bash
cd /Users/gabrielmitton/Desktop/Archive/Volrec
git add lab/REGISTRATION.md
git commit -m "lab/: registration - rules, cost cases, margin values, integrity thresholds, questions and predictions, committed before any purchase (exploratory)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Costs

**Files:**
- Create: `lab/costs.py`
- Create: `lab/test_lab.py`

**Interfaces:**
- Consumes: `modelfree.model_free_30d(rows, r)`, which returns a sequence whose `[0]` is the 30-day
  volatility in points, or a falsy value. It reads each row's `mid` (and `bid` only under
  `zero_bid_rule`).
- Produces: `COST_CASES: dict[str, float]`, `COMMISSIONS: tuple[float, float]`,
  `half_spread(bid: float|None, ask: float|None) -> float|None`,
  `charged(half: float, case: str) -> float`,
  `straddle_cost(call_q: tuple, put_q: tuple, case: str) -> float|None`,
  `vol_points(cost_per_share: float, vega_per_point: float) -> float|None`,
  `commission(contracts: float, per_contract: float) -> float`,
  `strip_cost(rows: list[dict], r: float) -> float|None`.

- [ ] **Step 1: Write the failing tests in `lab/test_lab.py`**

```python
"""Known-answer tests for lab/ (the retail implementation audit, EXPLORATORY). No network, no
licensed data: fixtures in the providers' real formats. Run with the framework python:
    FRED_KEY=use-cache python lab/test_lab.py
"""
import importlib.util as iu
import math
import sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(R), str(R / "tools"), str(R / "lab")]
fails = []


def check(name, cond):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}")
    if not cond:
        fails.append(name)


def load(name):
    s = iu.spec_from_file_location(name, R / "lab" / f"{name}.py")
    m = iu.module_from_spec(s)
    s.loader.exec_module(m)
    return m


from iv_convention import black76          # noqa: E402

costs = load("costs")
print("=== costs ===")
check("the four cost cases are exactly as registered",
      costs.COST_CASES == {"mid": 0.0, "timed": 0.30, "retail": 0.80, "quoted": 1.00})
check("commissions are $0 and $0.65", costs.COMMISSIONS == (0.0, 0.65))
check("half-spread of 1.00 / 1.20 is 0.10", abs(costs.half_spread(1.00, 1.20) - 0.10) < 1e-12)
check("a blank bid is a zero bid: None / 0.10 -> 0.05", abs(costs.half_spread(None, 0.10) - 0.05) < 1e-12)
check("no ask is no quote", costs.half_spread(1.0, None) is None)
check("a crossed quote is no quote", costs.half_spread(1.2, 1.0) is None)
check("retail pays 80% of 0.10 = 0.08", abs(costs.charged(0.10, "retail") - 0.08) < 1e-12)
check("mid pays nothing", costs.charged(0.10, "mid") == 0.0)
check("straddle at quoted: call 2.00/2.10 + put 1.90/2.06 -> 0.05 + 0.08 = 0.13",
      abs(costs.straddle_cost((2.00, 2.10), (1.90, 2.06), "quoted") - 0.13) < 1e-12)
check("straddle with an unquoted leg is None", costs.straddle_cost((2.0, None), (1.9, 2.0), "quoted") is None)
check("0.13 per share over vega 0.26 per point = 0.5 points", abs(costs.vol_points(0.13, 0.26) - 0.5) < 1e-12)
check("zero vega gives no conversion", costs.vol_points(0.13, 0.0) is None)
check("3 contracts at $0.65 = $1.95", abs(costs.commission(3, 0.65) - 1.95) < 1e-12)

# A chain in the recorder's own format (as tools/test_h8.py builds it): two expiries, flat 30% vol.
D, S, SIG = "2018-02-05", 100.0, 0.30


def chain(spread_frac):
    rows = []
    for exp, dte in (("2018-03-02", 25), ("2018-03-30", 53)):          # bracket 30 days, as Cboe needs
        for K in range(70, 131, 5):
            for k in "CP":
                p = black76(k, S, float(K), dte / 365.0, 0.0, SIG)
                if p < 0.05:
                    continue
                b, a = p * (1 - spread_frac), p * (1 + spread_frac)
                rows.append({"date": D, "symbol": "XYZ", "spot": str(S), "expiration": exp, "dte": str(dte),
                             "type": k, "strike": str(float(K)), "option_symbol": f"XYZ{exp[2:4]}{exp[5:7]}{exp[8:]}{k}{K * 1000:08d}",
                             "bid": f"{b:.6f}", "ask": f"{a:.6f}", "mid": f"{(a + b) / 2:.6f}"})
    return rows


z = costs.strip_cost(chain(0.0), 0.0)
check(f"a zero spread costs the strip nothing ({z})", z is not None and abs(z) < 1e-9)
w = costs.strip_cost(chain(0.04), 0.0)
check(f"a 4% spread costs the strip a positive number of points ({w:.3f})", w is not None and w > 0)
check("a wider spread costs more", costs.strip_cost(chain(0.08), 0.0) > w)

print(f"\n{len(fails)} failure(s)")
sys.exit(1 if fails else 0)
```

- [ ] **Step 2: Run it and confirm it fails**

Run: `cd /Users/gabrielmitton/Desktop/Archive/Volrec && FRED_KEY=use-cache /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 lab/test_lab.py`
Expected: a `FileNotFoundError` for `lab/costs.py`.

- [ ] **Step 3: Write `lab/costs.py`**

```python
"""lab/ - the retail implementation audit (EXPLORATORY; docs/superpowers/specs/
2026-10-12-retail-vrp-audit-design.md). What a seller pays to trade, in dollars and in volatility
points. Pure functions; lab/test_lab.py checks each against a hand-worked answer.

Held to expiry, so only the ENTRY half-spread is charged (Santa-Clara & Saretto 2009, footnote 7;
Muravyev & Pearson 2020's convention). The fractions are Muravyev & Pearson's published figures
for single-stock options, 2004-2015 - assumptions here, not findings about fund options.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "tools")]

COST_CASES = {"mid": 0.0, "timed": 0.30, "retail": 0.80, "quoted": 1.00}   # fraction of the quoted half-spread
COMMISSIONS = (0.0, 0.65)                                                   # dollars per contract


def half_spread(bid, ask):
    """Quoted half-spread per share. A missing bid is a zero bid (Databento writes a blank, the
    free feed a 0); no ask, or a crossed quote, is no quote."""
    if ask is None:
        return None
    b = bid or 0.0
    if ask < b:
        return None
    return (ask - b) / 2.0


def charged(half, case):
    """Per-share cost of one entry under a registered cost case."""
    return half * COST_CASES[case]


def straddle_cost(call_q, put_q, case):
    """call_q, put_q: (bid, ask). Per-share cost of selling one straddle, or None."""
    hc, hp = half_spread(*call_q), half_spread(*put_q)
    if hc is None or hp is None:
        return None
    return charged(hc, case) + charged(hp, case)


def vol_points(cost_per_share, vega_per_point):
    """A per-share dollar cost expressed in volatility points of the position."""
    return cost_per_share / vega_per_point if vega_per_point > 0 else None


def commission(contracts, per_contract):
    return contracts * per_contract


def strip_cost(rows, r):
    """Cost of SELLING the variance strip, in volatility points: the registered estimator on mids
    minus the same estimator on bids, over contracts with a positive bid (a zero-bid wing cannot
    be sold, so it is left out of both runs and the comparison stays like for like)."""
    import modelfree
    live = [x for x in rows if float(x.get("bid") or 0) > 0]
    if not live:
        return None
    at_mid = modelfree.model_free_30d(live, r)
    at_bid = modelfree.model_free_30d([dict(x, mid=x["bid"]) for x in live], r)
    if not at_mid or not at_bid:
        return None
    return at_mid[0] - at_bid[0]
```

- [ ] **Step 4: Run the tests and confirm they pass**

Run: `cd /Users/gabrielmitton/Desktop/Archive/Volrec && FRED_KEY=use-cache /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 lab/test_lab.py`
Expected: every line PASS, ending `0 failure(s)`. If the strip-cost cases fail because
`model_free_30d` needs a field the fixture lacks, read `modelfree.variance_one_expiry` and
`modelfree.model_free_30d`, add that field to the fixture rows (never change `modelfree.py`), and
re-run.

- [ ] **Step 5: Commit**

```bash
git add lab/costs.py lab/test_lab.py
git commit -m "lab/: costs - half-spreads, the four registered cost cases, straddle and strip cost, with known-answer tests

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Integrity checks

**Files:**
- Create: `lab/integrity.py`
- Modify: `lab/test_lab.py` (append before the final summary lines)

**Interfaces:**
- Consumes: `opra_reference.nearest(records, when, tol)` -> `(ts, bid, ask)` or None;
  `opra_reference.load_opra(path)` -> `{compact_symbol: [(ts, bid, ask), ...]}`.
- Produces: `BAND, PARITY_BAND, MIN_STRIKES, SANE_SHARE, PARITY_SHARE, DIV_ALLOW` (floats/ints),
  `parse_osi(sym: str) -> tuple[str, str, str, float]|None` (root, 'YYYY-MM-DD', 'C'|'P', strike),
  `chain_at(opra: dict, expiry: str, when: datetime, tol: int = 120) -> dict[float, dict[str, tuple]]`,
  `forward(chain: dict) -> float|None`,
  `check_chain(chain: dict) -> tuple[bool, dict[str, tuple[bool, str]]]`.

- [ ] **Step 1: Append the failing tests to `lab/test_lab.py`** (insert above
  `print(f"\n{len(fails)} failure(s)")`)

```python
integ = load("integrity")
from datetime import datetime, timezone    # noqa: E402
import opra_reference as ore               # noqa: E402
print("\n=== integrity ===")
check("registered thresholds", (integ.BAND, integ.PARITY_BAND, integ.MIN_STRIKES, integ.SANE_SHARE,
                                integ.PARITY_SHARE, integ.DIV_ALLOW) == (0.10, 0.05, 10, 0.95, 0.90, 0.005))
check("OSI with Databento's padding parses", integ.parse_osi("SPY   180216P00265000") == ("SPY", "2018-02-16", "P", 265.0))
check("OSI compact parses", integ.parse_osi("USO180316C00012500") == ("USO", "2018-03-16", "C", 12.5))
check("garbage is not an OSI symbol", integ.parse_osi("SPY") is None)

WHEN = datetime(2018, 2, 5, 19, 30, tzinfo=timezone.utc)


def opra_file(F=100.0, shift_call=0.0, drop=None, rel=0.02):
    """A Databento cbbo-1m CSV for one expiry, 39 days out, around the minute."""
    lines = ["ts_recv,ts_event,rtype,publisher_id,instrument_id,side,price,size,flags,"
             "bid_px_00,ask_px_00,bid_sz_00,ask_sz_00,bid_pb_00,ask_pb_00,symbol"]
    for K in range(80, 121):
        for k in "CP":
            if drop and (K, k) == drop:
                continue
            p = black76(k, F, float(K), 39 / 365.0, 0.0, 0.25) + (shift_call if k == "C" else 0.0)
            b, a = max(p * (1 - rel), 0.0), p * (1 + rel) + 0.01
            bb = "" if b < 0.01 else f"{b:.4f}"            # Databento: no bid -> BLANK
            for mm in ("29", "30", "31"):
                lines.append(f"2018-02-05T19:{mm}:00.000000000Z,,193,30,1,N,,0,0,{bb},{a:.4f},1,1,1,1,"
                             f"XYZ   180316{k}{K * 1000:08d}")
    p = Path(__import__("tempfile").mkdtemp()) / "OPRA_LAB_XYZ_2018-02-05.csv"
    p.write_text("\n".join(lines) + "\n")
    return ore.load_opra(p)


ch = integ.chain_at(opra_file(), "2018-03-16", WHEN)
check(f"the chain holds 41 strikes with both sides ({len(ch)})", len(ch) == 41 and all(len(v) == 2 for v in ch.values()))
F = integ.forward(ch)
check(f"the implied forward is 100 to within a cent ({F:.4f})", abs(F - 100.0) < 0.01)
okd, det = integ.check_chain(ch)
check(f"a consistent chain passes all three checks ({det})", okd)
okd2, det2 = integ.check_chain(integ.chain_at(opra_file(shift_call=0.50), "2018-03-16", WHEN))
check("a uniform 50-cent shift on every call moves the implied forward, not parity (still passes)", okd2)
bad = opra_file()
for s in list(bad):                                       # make every other call $1.50 rich
    p = integ.parse_osi(s)
    if p and p[2] == "C" and int(p[3]) % 2 == 0:
        bad[s] = [(t, (b or 0) + 1.5, a + 1.5) for t, b, a in bad[s]]
okd3, det3 = integ.check_chain(integ.chain_at(bad, "2018-03-16", WHEN))
check(f"a chain with alternate calls $1.50 rich fails parity ({det3.get('parity')})", not okd3 and not det3["parity"][0])
okd4, det4 = integ.check_chain(integ.chain_at(opra_file(drop=(100, "P")), "2018-03-16", WHEN))
check(f"a missing ATM put fails completeness ({det4.get('complete')})", not okd4 and not det4["complete"][0])
thin = {k: v for k, v in ch.items() if 97 <= k <= 103}
check("fewer than 10 strikes in the band fails completeness", not integ.check_chain(thin)[1]["complete"][0])
check("an empty chain fails", integ.check_chain({})[0] is False)
```

- [ ] **Step 2: Run and confirm the new cases fail**

Run: `FRED_KEY=use-cache /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 lab/test_lab.py`
Expected: `FileNotFoundError` for `lab/integrity.py`.

- [ ] **Step 3: Write `lab/integrity.py`**

```python
"""lab/ - integrity checks on every OPRA day the lab buys (EXPLORATORY). Thresholds are fixed in
lab/REGISTRATION.md before any purchase. A day failing any check is not used.

1. completeness: within +/-BAND of the implied forward, at least MIN_STRIKES strikes, and every
   strike the file carries for that expiry has a call and a put quoted (ask > 0);
2. sane spreads: at least SANE_SHARE of those quotes have 0 <= bid <= ask and
   ask - bid <= max(mid, $0.10);
3. put-call parity: within +/-PARITY_BAND, at least PARITY_SHARE of strikes have
   |(C_mid - P_mid + K) - median| <= the two half-spreads + DIV_ALLOW x forward
   (American fund options: dividends and early exercise loosen parity a little).
"""
import re
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "tools")]
import opra_reference as ore               # noqa: E402

BAND, PARITY_BAND, MIN_STRIKES = 0.10, 0.05, 10
SANE_SHARE, PARITY_SHARE, DIV_ALLOW = 0.95, 0.90, 0.005
OSI = re.compile(r"^(.+?)(\d{6})([CP])(\d{8})$")


def parse_osi(sym):
    m = OSI.match("".join(str(sym).split()))
    if not m:
        return None
    root, ymd, kind, k = m.groups()
    return root, f"20{ymd[:2]}-{ymd[2:4]}-{ymd[4:]}", kind, int(k) / 1000.0


def chain_at(opra, expiry, when, tol=120):
    """{strike: {'C': (bid, ask), 'P': (bid, ask)}} for one expiry, at the record nearest `when`."""
    out = {}
    for sym, recs in opra.items():
        p = parse_osi(sym)
        if not p or p[1] != expiry:
            continue
        hit = ore.nearest(recs, when, tol)
        if hit and hit[2] is not None:
            out.setdefault(p[3], {})[p[2]] = (hit[1] or 0.0, hit[2])
    return out


def _mid(q):
    return (q[0] + q[1]) / 2.0


def forward(chain):
    """F ~ K + C_mid - P_mid at the strike where the call and put mids are closest."""
    both = [(k, q) for k, q in chain.items() if "C" in q and "P" in q]
    if not both:
        return None
    k, q = min(both, key=lambda kq: abs(_mid(kq[1]["C"]) - _mid(kq[1]["P"])))
    return k + _mid(q["C"]) - _mid(q["P"])


def check_chain(chain):
    """(passed, {'complete': (ok, detail), 'sane': (ok, detail), 'parity': (ok, detail)})."""
    F = forward(chain)
    if F is None:
        return False, {"forward": (False, "no strike with both a call and a put")}
    band = sorted(k for k in chain if abs(k / F - 1) <= BAND)
    full = [k for k in band if all(t in chain[k] and chain[k][t][1] > 0 for t in "CP")]
    complete = (len(band) >= MIN_STRIKES and len(full) == len(band),
                f"{len(full)} of {len(band)} strikes two-sided (need all, and >= {MIN_STRIKES})")
    quotes = [chain[k][t] for k in band for t in "CP" if t in chain[k]]
    good = [q for q in quotes if 0 <= q[0] <= q[1] and q[1] - q[0] <= max(_mid(q), 0.10)]
    share = len(good) / len(quotes) if quotes else 0.0
    sane = (share >= SANE_SHARE, f"{share:.0%} of {len(quotes)} quotes sane (need {SANE_SHARE:.0%})")
    near = [k for k in full if abs(k / F - 1) <= PARITY_BAND]
    x = {k: _mid(chain[k]["C"]) - _mid(chain[k]["P"]) + k for k in near}
    if x:
        med = st.median(x.values())
        tol = {k: (chain[k]["C"][1] - chain[k]["C"][0]) / 2 + (chain[k]["P"][1] - chain[k]["P"][0]) / 2
               + DIV_ALLOW * F for k in near}
        inside = sum(1 for k in near if abs(x[k] - med) <= tol[k])
        pshare = inside / len(near)
    else:
        pshare = 0.0
    parity = (pshare >= PARITY_SHARE, f"{pshare:.0%} of {len(near)} strikes within parity (need {PARITY_SHARE:.0%})")
    det = {"complete": complete, "sane": sane, "parity": parity}
    return all(v[0] for v in det.values()), det
```

- [ ] **Step 4: Run the tests and confirm they pass**

Run: `FRED_KEY=use-cache /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 lab/test_lab.py`
Expected: all PASS, `0 failure(s)`.

- [ ] **Step 5: Commit**

```bash
git add lab/integrity.py lab/test_lab.py
git commit -m "lab/: integrity checks (completeness, sane spreads, put-call parity) on Databento-format fixtures

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Cboe customer margin

**Files:**
- Create: `lab/margin.py`
- Modify: `lab/test_lab.py` (append before the final summary lines)

**Interfaces:**
- Produces: `RATES: dict[str, tuple[float, float]]`, `BROKER: tuple[float, float]`,
  `short_put(P, S, K, a, b) -> float`, `short_call(C, S, K, a, b) -> float`,
  `short_straddle(C, P, S, Kc, Kp, a, b) -> float` (all per share; x100 per contract).
  Plan 2's liquidation mechanic consumes these.

- [ ] **Step 1: Append the failing tests** (the Cboe manual's own worked examples, plus
  Santa-Clara & Saretto's)

```python
mg = load("margin")
print("\n=== margin (Cboe Margin Manual, 30 Nov 2021, worked examples) ===")
check("registered rates", mg.RATES == {"SPY": (0.15, 0.10), "QQQ": (0.15, 0.10), "IWM": (0.15, 0.10),
                                       "GLD": (0.20, 0.10), "USO": (0.20, 0.10)} and mg.BROKER == (0.40, 0.35))
check("short Sep 80 put at 2, underlying 95, 20%/10%: $1,000.00",
      abs(mg.short_put(2.00, 95.0, 80.0, 0.20, 0.10) * 100 - 1000.00) < 0.005)
check("short Jan 20 put at 1.50, underlying 19.50: $540.00",
      abs(mg.short_put(1.50, 19.50, 20.0, 0.20, 0.10) * 100 - 540.00) < 0.005)
check("short Oct 410 put at .10, broad index 445.35, 15%/10%: $4,110.00",
      abs(mg.short_put(0.10, 445.35, 410.0, 0.15, 0.10) * 100 - 4110.00) < 0.005)
check("short Nov 120 call at 8.40, underlying 128.50: $3,410.00",
      abs(mg.short_call(8.40, 128.50, 120.0, 0.20, 0.10) * 100 - 3410.00) < 0.005)
check("short Feb 30 call at .05, underlying 26.38: $268.80",
      abs(mg.short_call(0.05, 26.38, 30.0, 0.20, 0.10) * 100 - 268.80) < 0.005)
check("short Dec 90 call at 7 + put at 3.70, underlying 92.63: $2,922.60",
      abs(mg.short_straddle(7.00, 3.70, 92.63, 90.0, 90.0, 0.20, 0.10) * 100 - 2922.60) < 0.005)
check("short Nov 435 put at 7.20 + call at 5.50, broad index 433.35: $7,770.25",
      abs(mg.short_straddle(5.50, 7.20, 433.35, 435.0, 435.0, 0.15, 0.10) * 100 - 7770.25) < 0.005)
P45 = black76("P", 100.0, 100.0, 45 / 365.0, 0.05, 0.20)
check(f"Santa-Clara & Saretto: ATM 45-day put, S=100, 20% vol, 5% rate -> $17.80 ({mg.short_put(P45, 100.0, 100.0, 0.15, 0.10):.2f})",
      abs(mg.short_put(P45, 100.0, 100.0, 0.15, 0.10) - 17.80) < 0.03)
```

- [ ] **Step 2: Run and confirm the new cases fail**

Run: `FRED_KEY=use-cache /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 lab/test_lab.py`
Expected: `FileNotFoundError` for `lab/margin.py`.

- [ ] **Step 3: Write `lab/margin.py`**

```python
"""lab/ - Cboe customer margin for short options (EXPLORATORY). Source: Cboe Margin Manual,
30 November 2021, customer margin account, initial requirement. Percentages unchanged since
6 Jun 1988, so one rule covers 2015-2026. Per share; x100 per contract.

  short put:  max(P + a*S - OTM amount, P + b*K)
  short call: max(C + a*S - OTM amount, C + b*S)
  short put + short call, same underlying: the greater requirement plus the other side's proceeds
  a = 15%, b = 10% for an ETF tracking a broad-based index; 20% / 10% for equity and other ETFs.
"""
RATES = {"SPY": (0.15, 0.10), "QQQ": (0.15, 0.10), "IWM": (0.15, 0.10),
         "GLD": (0.20, 0.10), "USO": (0.20, 0.10)}
BROKER = (0.40, 0.35)                     # Santa-Clara & Saretto (2009): E-Trade's house rate


def short_put(P, S, K, a, b):
    otm = max(S - K, 0.0)
    return max(P + a * S - otm, P + b * K)


def short_call(C, S, K, a, b):
    otm = max(K - S, 0.0)
    return max(C + a * S - otm, C + b * S)


def short_straddle(C, P, S, Kc, Kp, a, b):
    mc, mp = short_call(C, S, Kc, a, b), short_put(P, S, Kp, a, b)
    return mc + P if mc >= mp else mp + C
```

- [ ] **Step 4: Run the tests and confirm they pass**

Run: `FRED_KEY=use-cache /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 lab/test_lab.py`
Expected: all PASS, `0 failure(s)`.

- [ ] **Step 5: Commit**

```bash
git add lab/margin.py lab/test_lab.py
git commit -m "lab/: Cboe customer margin (short put, call, straddle), proved on the manual's seven worked examples and Santa-Clara & Saretto's

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: The purchasing tool

**Files:**
- Create: `lab/fetch_lab.py`
- Modify: `lab/test_lab.py` (append before the final summary lines)
- One-time setup: `~/Documents/volrec-licensed/.git/info/exclude` gains `opra-lab/`

**Interfaces:**
- Consumes: `opra_reference.call`, `request_params(symbol, minute) -> dict`, `budget_ok(cost,
  max_cost, spent) -> (bool, str)`, `inside_repo(path) -> bool`, `NotYetHistorical`,
  `DEFAULT_MAX_COST`, `ATTRIBUTION`.
- Produces: `LAB_BUDGET_USD = 75.00`, `LAB_START = "2015-08-01"`, `LAB_END = "2026-08-31"`,
  `LAB_TAG = "-lab"`, `PRIVATE: Path`, `LAB_DIR: Path`, `LEDGER: Path`,
  `date_ok(day: str) -> bool`, `ny_minute(day: str, hhmm: str = "14:30") -> datetime` (UTC),
  `lab_stem(symbol, day, hhmm) -> str`, `ledger_rows() -> list[dict]`,
  `spent_all(rows) -> float`, `spent_lab(rows) -> float`,
  `lab_budget_ok(cost: float, spent: float) -> tuple[bool, str]`,
  `fetch(day, symbol, key, max_cost, dry, hhmm="14:30") -> float` (dollars charged, 0 if none).
  CLI: `--day D --symbols A,B [--at HH:MM] [--dry-run] [--max-cost X]`.

- [ ] **Step 1: Exclude the lab folder from the private repo's git (one time)**

```bash
grep -qx "opra-lab/" ~/Documents/volrec-licensed/.git/info/exclude || echo "opra-lab/" >> ~/Documents/volrec-licensed/.git/info/exclude
tail -2 ~/Documents/volrec-licensed/.git/info/exclude
```
Expected: the last line is `opra-lab/`.

- [ ] **Step 2: Append the failing tests**

```python
fl = load("fetch_lab")
print("\n=== fetch_lab (no network) ===")
check("registered cap, tag and dates", (fl.LAB_BUDGET_USD, fl.LAB_TAG, fl.LAB_START, fl.LAB_END)
      == (75.00, "-lab", "2015-08-01", "2026-08-31"))
check("31 Aug 2026 is allowed, 1 Sep 2026 is not", fl.date_ok("2026-08-31") and not fl.date_ok("2026-09-01"))
check("1 Aug 2015 is allowed, 31 Jul 2015 is not", fl.date_ok("2015-08-01") and not fl.date_ok("2015-07-31"))
check("H7's window (9 Oct 2026) is refused", not fl.date_ok("2026-10-09"))
check("14:30 New York in winter is 19:30 UTC (5 Feb 2018)",
      fl.ny_minute("2018-02-05").isoformat() == "2018-02-05T19:30:00+00:00")
check("14:30 New York in summer is 18:30 UTC (5 Aug 2024)",
      fl.ny_minute("2024-08-05").isoformat() == "2024-08-05T18:30:00+00:00")
check("file stem", fl.lab_stem("SPY", "2018-02-05", "14:30") == "OPRA_LAB_SPY_2018-02-05_1430")
rows = [{"symbol": "SPY", "usd": "0.50"}, {"symbol": "SPY-h8", "usd": "0.25"}, {"symbol": "USO-lab", "usd": "1.25"}]
check("lifetime spend counts every row", abs(fl.spent_all(rows) - 2.00) < 1e-12)
check("lab spend counts only -lab rows", abs(fl.spent_lab(rows) - 1.25) < 1e-12)
check("within the lab cap", fl.lab_budget_ok(0.20, 74.70)[0])
check("over the lab cap is refused", not fl.lab_budget_ok(0.20, 74.90)[0])
check("the lab's data folder is outside the public repo", not ore.inside_repo(fl.LAB_DIR))
```

- [ ] **Step 3: Run and confirm the new cases fail**

Run: `FRED_KEY=use-cache /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 lab/test_lab.py`
Expected: `FileNotFoundError` for `lab/fetch_lab.py`.

- [ ] **Step 4: Write `lab/fetch_lab.py`**

```python
#!/usr/bin/env python3
"""lab/ - OPRA purchases for the retail implementation audit (EXPLORATORY).

Priced first with Databento's get_cost; refused past the per-request cap, the $100 lifetime cap,
or the lab's own $75 cap (LAB_BUDGET_USD); refused for any day outside LAB_START..LAB_END, which
keeps the lab clear of every registered window. Files go to the private repo's checkout under
opra-lab/ (git-excluded there, never in the public repo). The ledger is the private repo's
opra/spend.csv, the same one the cloud's daily run checks, so it is pulled before buying and
committed and pushed after.

  FRED_KEY=use-cache python lab/fetch_lab.py --day 2018-02-05 --symbols SPY,QQQ,IWM,GLD,USO --dry-run
"""
import argparse
import csv
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "tools")]
os.environ.setdefault("FRED_KEY", "use-cache")
import opra_reference as ore               # noqa: E402

LAB_BUDGET_USD = 75.00
LAB_START, LAB_END = "2015-08-01", "2026-08-31"
LAB_TAG = "-lab"
PRIVATE = Path(os.environ.get("VOLREC_LICENSED_DIR") or Path.home() / "Documents" / "volrec-licensed")
LAB_DIR = PRIVATE / "opra-lab"
LEDGER = PRIVATE / "opra" / "spend.csv"


def date_ok(day):
    return LAB_START <= day <= LAB_END


def ny_minute(day, hhmm="14:30"):
    h, m = map(int, hhmm.split(":"))
    local = datetime.fromisoformat(day).replace(hour=h, minute=m, tzinfo=ZoneInfo("America/New_York"))
    return local.astimezone(timezone.utc)


def lab_stem(symbol, day, hhmm):
    return f"OPRA_LAB_{symbol}_{day}_{hhmm.replace(':', '')}"


def ledger_rows():
    if not LEDGER.exists():
        return []
    with LEDGER.open(newline="") as f:
        return list(csv.DictReader(f))


def spent_all(rows):
    return sum(float(r["usd"]) for r in rows if r.get("usd"))


def spent_lab(rows):
    return sum(float(r["usd"]) for r in rows if r.get("usd") and r.get("symbol", "").endswith(LAB_TAG))


def lab_budget_ok(cost, spent):
    """(allowed, reason). Pure, so the cap is tested without spending anything."""
    if spent + cost > LAB_BUDGET_USD:
        return False, f"would take lab spend to ${spent + cost:.2f}, past its ${LAB_BUDGET_USD:.2f} cap"
    return True, "within the lab's cap"


def git(*args):
    return subprocess.run(["git", "-C", str(PRIVATE), *args], capture_output=True, text=True)


def sync_ledger():
    r = git("pull", "--ff-only", "-q")
    if r.returncode != 0:
        sys.exit(f"Could not update the private repo's ledger first: {r.stderr.strip()}")


def commit_ledger(n, usd):
    git("add", "opra/spend.csv")
    c = git("commit", "-q", "-m", f"spend: lab/ purchases, {n} file(s), ${usd:.4f}")
    if c.returncode != 0:
        return
    if git("pull", "--rebase", "-q").returncode != 0 or git("push", "-q").returncode != 0:
        print("  WARNING: the ledger commit is local only - push the private repo by hand")


def fetch(day, symbol, key, max_cost, dry, hhmm="14:30"):
    if not date_ok(day):
        sys.exit(f"{day} is outside the lab's dates ({LAB_START} to {LAB_END}); refused")
    if ore.inside_repo(LAB_DIR):
        sys.exit("Refusing a lab data folder inside the public repository.")
    out = LAB_DIR / f"{lab_stem(symbol, day, hhmm)}.csv"
    if out.exists():
        print(f"  {symbol} {day} {hhmm}: already on disk - skipped, nothing charged")
        return 0.0
    params = ore.request_params(symbol, ny_minute(day, hhmm))
    cost = float(ore.call("metadata.get_cost", params, key).json())
    rows = ledger_rows()
    allowed, why = ore.budget_ok(cost, max_cost, spent_all(rows))
    if allowed:
        allowed, why = lab_budget_ok(cost, spent_lab(rows))
    print(f"  {symbol} {day} {hhmm} NY: costs ${cost:.4f}; lab spent ${spent_lab(rows):.2f} of "
          f"${LAB_BUDGET_USD:.0f}; lifetime ${spent_all(rows):.2f}: {why}")
    if dry or not allowed:
        return 0.0
    body = dict(params, encoding="csv", compression="none", pretty_px="true",
                pretty_ts="true", map_symbols="true")
    try:
        r = ore.call("timeseries.get_range", body, key)
    except ore.NotYetHistorical as e:
        print(f"    not yet historical ({e}); nothing charged")
        return 0.0
    LAB_DIR.mkdir(parents=True, exist_ok=True)
    out.write_bytes(r.content)
    with LEDGER.open("a", newline="") as f:
        csv.writer(f).writerow([datetime.now(timezone.utc).isoformat(timespec="seconds"), day,
                                symbol + LAB_TAG, f"{cost:.6f}"])
    print(f"    fetched {len(r.content):,} bytes -> {out}")
    return cost


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--day", required=True)
    ap.add_argument("--symbols", default="SPY,QQQ,IWM,GLD,USO")
    ap.add_argument("--at", default="14:30", help="New York time, HH:MM")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--max-cost", type=float, default=ore.DEFAULT_MAX_COST)
    a = ap.parse_args()
    key = ore.api_key()
    if not key:
        sys.exit("No Databento key (DATABENTO_API_KEY or ~/.config/volrec/databento.key)")
    if not a.dry_run:
        sync_ledger()
    paid = [fetch(a.day, s.strip(), key, a.max_cost, a.dry_run, a.at) for s in a.symbols.split(",")]
    n, usd = sum(1 for p in paid if p > 0), sum(paid)
    if n:
        commit_ledger(n, usd)
    print(f"\n{n} file(s) bought, ${usd:.4f}. {ore.ATTRIBUTION}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run the tests and confirm they pass**

Run: `FRED_KEY=use-cache /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 lab/test_lab.py`
Expected: all PASS, `0 failure(s)`.

- [ ] **Step 6: Dry run against the real API (prices only, spends nothing)**

Run: `FRED_KEY=use-cache /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 lab/fetch_lab.py --day 2018-02-05 --dry-run`
Expected: five lines, each with a price between $0.002 and $0.03, each "within the lab's cap";
`0 file(s) bought, $0.0000`. Then
`FRED_KEY=use-cache /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 lab/fetch_lab.py --day 2026-10-09 --dry-run`
Expected: exits with "outside the lab's dates ... refused".

- [ ] **Step 7: Commit**

```bash
git add lab/fetch_lab.py lab/test_lab.py
git commit -m "lab/: purchasing tool - priced first, own \$75 cap, dates 1 Aug 2015 to 31 Aug 2026 only, files outside the repo, ledger in the private repo

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Safeguards in the pressure test and the auditor

**Files:**
- Modify: `tools/pressure_test.py` (after the H8 instrument-test check, the block ending
  `"H8's instrument tests pass ..."`)
- Modify: `tools/audit.py` (the mutant list, after the `h8-trim-drops-header` entry)

**Interfaces:**
- Consumes: `lab/test_lab.py` (exit code, PASS/FAIL lines), `lab/fetch_lab.py` constants and
  `lab_budget_ok`, `date_ok`, `LAB_DIR`.
- Produces: three pressure-test lines whose text the mutants match:
  "lab/ tests pass", "lab/ OPRA purchases stop at their own $75 cap",
  "lab/ purchases refused outside 1 Aug 2015 - 31 Aug 2026".

- [ ] **Step 1: Add the checks to `tools/pressure_test.py`** directly after the line
  `ok(_t8.returncode == 0 and _n8f == 0 and _n8p >= 26, f"H8's instrument tests pass ({_n8p} cases, {_n8f} failures)")`

```python
# lab/ (EXPLORATORY side project, 12 Oct 2026): known answers for costs, integrity and margin; its
# own purchase cap; its dates (never inside a registered window); its data folder outside this repo.
_tl = _sp.run([sys.executable, str(R / "lab/test_lab.py")], capture_output=True, text=True)
_nlf = sum(1 for _ln in _tl.stdout.splitlines() if _ln.strip().startswith("FAIL"))
_nlp = sum(1 for _ln in _tl.stdout.splitlines() if _ln.strip().startswith("PASS"))
ok(_tl.returncode == 0 and _nlf == 0 and _nlp >= 49, f"lab/ tests pass ({_nlp} cases, {_nlf} failures)")
_fls = _iu.spec_from_file_location("fetch_lab", R / "lab/fetch_lab.py")
_flm = _iu.module_from_spec(_fls)
_fls.loader.exec_module(_flm)
ok(_flm.lab_budget_ok(0.20, 74.70)[0] and not _flm.lab_budget_ok(0.20, 74.90)[0] and _flm.LAB_BUDGET_USD == 75.00,
   "lab/ OPRA purchases stop at their own $75 cap")
ok(_flm.date_ok("2026-08-31") and not _flm.date_ok("2026-09-01") and not _flm.date_ok("2015-07-31")
   and (_flm.LAB_START, _flm.LAB_END) == ("2015-08-01", "2026-08-31"),
   "lab/ purchases refused outside 1 Aug 2015 - 31 Aug 2026 (clear of every registered window)")
ok(not _opm.inside_repo(_flm.LAB_DIR), "lab/ OPRA files live outside this repository")
```

(`_sp`, `_iu`, `_opm`, `ok`, `R` already exist in `pressure_test.py`; confirm with
`grep -n "^import subprocess as _sp\|_iu =\|import importlib.util as _iu\|_opm =" tools/pressure_test.py`
and use the names found there.)

- [ ] **Step 2: Add the mutants to `tools/audit.py`** after the `h8-trim-drops-header` tuple

```python
    ("lab-cap-ignored", "the lab's own spending cap stops being applied",
     lambda w: _sub(w / "lab/fetch_lab.py", "    if spent + cost > LAB_BUDGET_USD:", "    if False:"),
     "lab/ OPRA purchases stop at their own"),
    ("lab-date-range-ignored", "the lab may buy days inside a registered window",
     lambda w: _sub(w / "lab/fetch_lab.py", "    return LAB_START <= day <= LAB_END", "    return True"),
     "lab/ purchases refused outside"),
    ("lab-margin-ignores-otm", "the margin rule forgets to subtract the out-of-the-money amount",
     lambda w: _sub(w / "lab/margin.py", "    otm = max(S - K, 0.0)", "    otm = 0.0"),
     "lab/ tests pass"),
```

- [ ] **Step 3: Run the pressure test**

Run: `FRED_KEY=use-cache /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 tools/pressure_test.py 2>&1 | grep -E "lab/|RESULT"`
Expected: four `PASS ... lab/` lines; `RESULT: 0 fail, 3 warn`.

- [ ] **Step 4: Run the auditor**

Run: `FRED_KEY=use-cache /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 tools/audit.py 2>&1 | grep -E "lab-|RESULT"`
Expected: `KILLED lab-cap-ignored`, `KILLED lab-date-range-ignored`, `KILLED lab-margin-ignores-otm`;
`RESULT: 71 of 71 safeguards proven to fail when broken`.

- [ ] **Step 5: Commit and push** (push only because the auditor reads N of N)

```bash
git add tools/pressure_test.py tools/audit.py
git commit -m "Pressure test and auditor cover lab/: its tests, its \$75 cap, its dates, its data outside the repo (71 safeguards)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push
```
Expected: the pre-push hook prints `RESULT: 0 fail, 3 warn` and the push succeeds.

---

### Task 7: Buy and verify the test day, 5 Feb 2018

**Files:**
- Create: `lab/verify_day.py`
- Modify: `lab/REGISTRATION.md` (the Log)

**Interfaces:**
- Consumes: `fetch_lab.LAB_DIR`, `fetch_lab.lab_stem`, `fetch_lab.ny_minute`,
  `integrity.chain_at`, `integrity.check_chain`, `opra_reference.load_opra`, `ATTRIBUTION`.
- Produces: `verify(day, symbols, expiries, hhmm="14:30") -> dict[str, bool]` and a CLI
  `--day D --expiries E1,E2 [--symbols ...]` printing per fund and expiry the three checks'
  details (aggregates only); exit 0 only if every fund passes on every expiry.

- [ ] **Step 1: Write `lab/verify_day.py`**

```python
#!/usr/bin/env python3
"""lab/ - run the registered integrity checks on a day the lab bought (EXPLORATORY).
Aggregates only.

  FRED_KEY=use-cache python lab/verify_day.py --day 2018-02-05 --expiries 2018-02-16,2018-03-16
"""
import argparse
import importlib.util as iu
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "tools"), str(ROOT / "lab")]
import opra_reference as ore               # noqa: E402


def _load(name):
    s = iu.spec_from_file_location(name, ROOT / "lab" / f"{name}.py")
    m = iu.module_from_spec(s)
    s.loader.exec_module(m)
    return m


fl, integ = _load("fetch_lab"), _load("integrity")


def verify(day, symbols, expiries, hhmm="14:30"):
    when, out = fl.ny_minute(day, hhmm), {}
    for sym in symbols:
        p = fl.LAB_DIR / f"{fl.lab_stem(sym, day, hhmm)}.csv"
        if not p.exists():
            print(f"  {sym:4s} no file on disk ({p.name})")
            out[sym] = False
            continue
        opra = ore.load_opra(p)
        good = True
        for e in expiries:
            ch = integ.chain_at(opra, e, when)
            passed, det = integ.check_chain(ch)
            good &= passed
            F = integ.forward(ch)
            fs = f"{F:.2f}" if F else "n/a"
            print(f"  {sym:4s} {e}  forward {fs:>8s}  {'PASS' if passed else 'FAIL'}  "
                  + "; ".join(f"{k}: {v[1]}" for k, v in det.items()))
        out[sym] = good
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--day", required=True)
    ap.add_argument("--expiries", required=True)
    ap.add_argument("--symbols", default="SPY,QQQ,IWM,GLD,USO")
    ap.add_argument("--at", default="14:30")
    a = ap.parse_args()
    res = verify(a.day, a.symbols.split(","), a.expiries.split(","), a.at)
    print(f"\n{sum(res.values())} of {len(res)} funds pass every check. {ore.ATTRIBUTION}")
    sys.exit(0 if all(res.values()) else 1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Buy the test day** (about $0.04; five files)

Run: `FRED_KEY=use-cache /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 lab/fetch_lab.py --day 2018-02-05`
Expected: five "fetched ... bytes" lines; `5 file(s) bought, $0.04xx`; the private repo shows a
new commit "spend: lab/ purchases, 5 file(s), ...". Check with
`git -C ~/Documents/volrec-licensed log --oneline -1` and
`git -C ~/Documents/volrec-licensed status --short` (expected: clean; `opra-lab/` not listed).

- [ ] **Step 3: Verify it**

Run: `FRED_KEY=use-cache /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 lab/verify_day.py --day 2018-02-05 --expiries 2018-02-16,2018-03-16`
Expected: one line per fund and expiry with the three checks' details, and a final count.
- If all five pass: the archive is sound for 2018; Plan 2 proceeds on real straddles.
- If any fails: read its detail. If the cause is the data (for example, missing strikes), the
  spec's fallback applies: report it and stop for Gabriel's decision. If the cause is a check
  that is wrong, fix it only with a new known-answer test, and log the change as AFTER data in
  REGISTRATION.md. Thresholds are not loosened to make the day pass.

- [ ] **Step 4: Log the outcome in `lab/REGISTRATION.md`** under "## Log", for example:

```markdown
- 2026-10-12, AFTER the test day: 5 Feb 2018 bought ($0.0xx, 5 files) and checked. Result per
  fund (completeness / sane spreads / parity): SPY ..., QQQ ..., IWM ..., GLD ..., USO ....
  Decision: proceed to Plan 2 on real straddles | fall back to the synthetic variance swap.
```
(Fill in the measured values, copied from Step 3's output.)

- [ ] **Step 5: Commit and push**

```bash
git add lab/verify_day.py lab/REGISTRATION.md
git commit -m "lab/: the 5 Feb 2018 test day bought and checked (integrity results logged)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
FRED_KEY=use-cache /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 tools/audit.py 2>&1 | tail -1
git push
```
Expected: auditor `71 of 71`, then the push succeeds.
