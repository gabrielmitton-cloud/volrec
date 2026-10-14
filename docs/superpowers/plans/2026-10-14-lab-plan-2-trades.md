# lab/ Plan 2: The Trades Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Price every monthly short straddle and 5% strangle on the five funds from January 2016 to
August 2026 on real OPRA quotes, settle each on the fund's raw close, and print the first results:
paper returns, retention under the four cost cases, rules R0-R3, and strip cost over ATM cost.

**Architecture:** Five small modules in `lab/`:
- `bars.py`: daily closes, fetched by a manual GitHub workflow so the Alpaca keys stay in
  GitHub's secrets;
- `calendar.py`: monthly expiries and entry days;
- `trades.py`: strike choice, settlement, P&L, rules, vega;
- `buy_days.py`: the batch purchase;
- `run_trades.py`: the run and the aggregate report.

Raw quotes and per-trade rows stay in the private folder; only aggregates are printed. Margin, the
Leak Map and the stress lab are Plan 3.

**Tech Stack:** Python 3.14 stdlib + `requests`; GitHub Actions (`workflow_dispatch`); `gh`;
Databento via `lab/fetch_lab.py`.

**Spec:** `docs/superpowers/specs/2026-10-12-retail-vrp-audit-design.md`, sections 3-5 and 11 (Q1 in
part, Q3). **Registration:** `lab/REGISTRATION.md`.

## Global Constraints

- Python: `/Library/Frameworks/Python.framework/Versions/3.14/bin/python3` with `FRED_KEY=use-cache`.
- Exploratory; no registered file changes.
- **No FRED data in `lab/`** (FRED's terms bar AI-related use). The risk-free rate in the lab is 0
  for the strip comparison, where it cancels.
- Lab dates: nothing bought or read after **2026-08-31**, so the last trade must expire by then:
  entries 2016-01-19 to 2026-07-20.
- Lab cap $90; every OPRA purchase via `fetch_lab` (priced first, ledger in the private repo).
- Alpaca daily closes are fetched only inside GitHub Actions (secrets `ALPACA_KEY`,
  `ALPACA_SECRET`). The artifact is kept 1 day and downloaded to
  `~/Documents/volrec-licensed/lab-bars/`, never committed.
- Index levels and realised volatility used by rules are taken from the **previous trading day's
  close** (the entry is at 14:30, before that day's close).
- Every OPRA-derived printout ends with "Data provided by Databento (OPRA consolidated NBBO).
  Aggregates only."
- Push only when `tools/audit.py` reads N of N.

## File Structure

| File | Responsibility |
|---|---|
| `lab/bars.py` | fetch raw + adjusted daily closes (in CI), write and load `bars.csv` |
| `.github/workflows/lab_bars.yml` | manual workflow: run `bars.py` with the secrets, 1-day artifact |
| `lab/calendar.py` | third Fridays, monthly expiries on the trading calendar, entry/expiry pairs |
| `lab/trades.py` | strike choice, raw-close settlement, per-leg P&L by cost case, rules R0-R3, Black-76 vega |
| `lab/buy_days.py` | buy every entry day's quotes and listings in one batch, one ledger commit |
| `lab/run_trades.py` | integrity per day, trades, per-trade rows (private), aggregate report |
| `lab/test_lab.py` | new known-answer tests for all of the above |
| `tools/pressure_test.py`, `tools/audit.py` | the new workflow registered; mutants lab-raw-prices-dropped, lab-cost-roundtrip-charged |

---

### Task 1: Decisions logged before any trade is computed

**Files:**
- Modify: `lab/REGISTRATION.md` (Log)

- [ ] **Step 1: Append to the Log**

```markdown
- 2026-10-14, before any trade is computed - implementation choices for Plan 2:
  - Daily closes from Alpaca `sip` (raw for settlement, adjusted for realised volatility), which
    starts 4 Jan 2016. So the first entry is 19 Jan 2016, and the Aug 2015 replay (Plan 3) needs
    another price source or is dropped, stated then.
  - The last trade must expire by 31 Aug 2026, so the last entry is 20 Jul 2026 (expiry 21 Aug).
  - Rules read the previous trading day's closes (index, VIX, VIX3M, realised volatility); the
    entry at 14:30 precedes that day's close. R1 needs 21 prior returns; before they exist R1 does
    not trade.
  - R2's weight is 20 / index (the index in points; 20 is a fixed reference, not fitted).
  - ATM = the listed strike nearest the implied forward at 14:30; the strangle = the listed strikes
    nearest 0.95 and 1.05 x forward. Only two-sided strikes are eligible.
  - Returns are per dollar of mid premium; P&L = (mid - charged half-spread) - intrinsic at expiry.
  - The risk-free rate is 0 in the strip comparison (it enters mid and bid alike) and in vega;
    no FRED data is used in lab/.
  - A day failing the integrity checks is excluded for that fund and listed in the report.
  - Correction to the registration's "28-35 days out": entering on the trading day AFTER an
    expiry, the hold to the next monthly is 24-32 calendar days (the 28- or 35-day cycle less the
    days to the next session). The calendar rule itself is unchanged.
```

- [ ] **Step 2: Commit**

```bash
git add lab/REGISTRATION.md
git commit -m "lab/: Plan 2 implementation choices logged before any trade is computed

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Daily closes (`bars.py` and its workflow)

**Files:**
- Create: `lab/bars.py`
- Create: `.github/workflows/lab_bars.yml`
- Modify: `lab/test_lab.py` (append before the summary lines)
- Modify: `tools/pressure_test.py` (register the workflow; see Step 6)

**Interfaces:**
- Produces: `FUNDS = ("SPY", "QQQ", "IWM", "GLD", "USO")`, `BARS_FILE: Path`,
  `write_csv(path, raw: dict, adj: dict) -> int` (rows written),
  `load(path=BARS_FILE) -> dict[str, dict[str, tuple[float, float]]]` (`sym -> date -> (raw, adj)`),
  `fetch(symbols, start, end, adjustment, key, secret, feed="sip") -> dict[str, dict[str, float]]`.

- [ ] **Step 1: Append the failing tests**

```python
bars = load("bars")
print("\n=== bars ===")
check("the five funds", bars.FUNDS == ("SPY", "QQQ", "IWM", "GLD", "USO"))
_bp = Path(__import__("tempfile").mkdtemp()) / "bars.csv"
n = bars.write_csv(_bp, {"USO": {"2020-04-28": 2.14, "2020-04-29": 18.01}},
                         {"USO": {"2020-04-28": 17.12, "2020-04-29": 18.01}})
check("two rows written", n == 2)
_b = bars.load(_bp)
check("raw and adjusted read back separately (USO's 1-for-8 split, 29 Apr 2020)",
      _b["USO"]["2020-04-28"] == (2.14, 17.12) and _b["USO"]["2020-04-29"] == (18.01, 18.01))
check("the bars file lives outside the public repo", not ore.inside_repo(bars.BARS_FILE))
```

- [ ] **Step 2: Run and confirm failure**

Run: `FRED_KEY=use-cache /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 lab/test_lab.py 2>&1 | tail -1`
Expected: `FileNotFoundError` for `lab/bars.py`.

- [ ] **Step 3: Write `lab/bars.py`**

```python
#!/usr/bin/env python3
"""lab/ - daily closes for the five funds (EXPLORATORY). RAW closes settle options (listed strikes
are never back-adjusted: USO's 1-for-8 reverse split on 29 Apr 2020); ADJUSTED closes give realised
volatility, as analyze.py does. Fetched only inside GitHub Actions (.github/workflows/lab_bars.yml)
so the Alpaca keys stay in GitHub's secrets; the CSV is kept outside every repository.

  python lab/bars.py --start 2016-01-01 --end 2026-08-31 --out lab_bars.csv     (CI only)
"""
import argparse
import csv
import os
import sys
from pathlib import Path

FUNDS = ("SPY", "QQQ", "IWM", "GLD", "USO")
BARS_FILE = Path(os.environ.get("VOLREC_LAB_BARS") or
                 Path.home() / "Documents" / "volrec-licensed" / "lab-bars" / "lab_bars.csv")
DATA_URL = "https://data.alpaca.markets"


def fetch(symbols, start, end, adjustment, key, secret, feed="sip"):
    import requests
    s = requests.Session()
    s.headers.update({"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret, "accept": "application/json"})
    out, token = {x: {} for x in symbols}, None
    while True:
        p = dict(symbols=",".join(symbols), timeframe="1Day", feed=feed, start=start, end=end,
                 limit=10000, adjustment=adjustment)
        if token:
            p["page_token"] = token
        r = s.get(f"{DATA_URL}/v2/stocks/bars", params=p, timeout=30)
        r.raise_for_status()
        j = r.json()
        for sym, bs in (j.get("bars") or {}).items():
            for b in bs:
                out[sym][b["t"][:10]] = b["c"]
        token = j.get("next_page_token")
        if not token:
            return out


def write_csv(path, raw, adj):
    rows = sorted((d, sym, raw[sym][d], adj[sym].get(d)) for sym in raw for d in raw[sym])
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "symbol", "raw_close", "adj_close"])
        w.writerows(rows)
    return len(rows)


def load(path=BARS_FILE):
    out = {}
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            out.setdefault(r["symbol"], {})[r["date"]] = (float(r["raw_close"]), float(r["adj_close"]))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    key, sec = os.environ.get("ALPACA_KEY"), os.environ.get("ALPACA_SECRET")
    if not key or not sec:
        sys.exit("ALPACA_KEY / ALPACA_SECRET not set")
    raw = fetch(list(FUNDS), a.start, a.end, "raw", key, sec)
    adj = fetch(list(FUNDS), a.start, a.end, "all", key, sec)
    n = write_csv(a.out, raw, adj)
    print(f"{n} rows; first/last per fund: " + "; ".join(
        f"{s} {min(raw[s])}..{max(raw[s])} ({len(raw[s])})" for s in FUNDS if raw[s]))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Write `.github/workflows/lab_bars.yml`**

```yaml
# lab/ (EXPLORATORY side project, 14 Oct 2026): the five funds' daily closes, raw and adjusted,
# for the retail implementation audit. Manual only, no schedule; commits nothing. The artifact is
# kept one day, downloaded to Gabriel's Mac outside every repository, and never published.
name: lab-bars
on:
  workflow_dispatch:
permissions:
  contents: read
jobs:
  bars:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v5
      - uses: actions/setup-python@v6
        with:
          python-version: "3.12"
      - run: pip install requests
      - name: Daily closes, 2016-01-01 to 2026-08-31
        env:
          ALPACA_KEY: ${{ secrets.ALPACA_KEY }}
          ALPACA_SECRET: ${{ secrets.ALPACA_SECRET }}
        run: python lab/bars.py --start 2016-01-01 --end 2026-08-31 --out lab_bars.csv
      - uses: actions/upload-artifact@v4
        with:
          name: lab-bars
          path: lab_bars.csv
          retention-days: 1
```

- [ ] **Step 5: Run the tests and confirm they pass**

Run: `FRED_KEY=use-cache /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 lab/test_lab.py 2>&1 | tail -1`
Expected: `0 failure(s)`.

- [ ] **Step 6: Register the workflow in the pressure test**

Run: `grep -n "_ANALYSIS_WF" tools/pressure_test.py | head -3`. Add `"lab_bars.yml"` to that tuple
or list beside `"opra_probe.yml"`, using the same quoting the file uses. Then run
`FRED_KEY=use-cache /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 tools/pressure_test.py 2>&1 | tail -1`.
Expected: `RESULT: 0 fail, 3 warn`.

- [ ] **Step 7: Commit, push, run the workflow, download the closes**

```bash
git add lab/bars.py lab/test_lab.py .github/workflows/lab_bars.yml tools/pressure_test.py
git commit -m "lab/: daily closes (raw for settlement, adjusted for realised volatility) via a manual workflow; keys stay in GitHub secrets

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
FRED_KEY=use-cache /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 tools/audit.py 2>&1 | tail -1
git push
gh workflow run lab_bars.yml
```
Then, once `gh run list --workflow lab_bars.yml -L 1` shows `completed success`:
```bash
mkdir -p ~/Documents/volrec-licensed/lab-bars
gh run download "$(gh run list --workflow lab_bars.yml -L 1 --json databaseId -q '.[0].databaseId')" -n lab-bars -D ~/Documents/volrec-licensed/lab-bars
grep -qx "lab-bars/" ~/Documents/volrec-licensed/.git/info/exclude || echo "lab-bars/" >> ~/Documents/volrec-licensed/.git/info/exclude
head -3 ~/Documents/volrec-licensed/lab-bars/lab_bars.csv; wc -l ~/Documents/volrec-licensed/lab-bars/lab_bars.csv
```
Expected: the header and 2016 rows; about 13,400 lines (5 funds x ~2,680 days). The run log
shows each fund starting 2016-01-04.

---

### Task 3: The calendar

**Files:**
- Create: `lab/calendar.py`
- Modify: `lab/test_lab.py`

**Interfaces:**
- Produces: `FIRST_ENTRY = "2016-01-19"`, `LAST_EXPIRY = "2026-08-31"`,
  `third_friday(y: int, m: int) -> date`,
  `monthly_expiry(y: int, m: int, trading: set[str]) -> str` (third Friday, else the latest
  trading day before it),
  `entries(trading_days: list[str]) -> list[tuple[str, str]]` (entry, expiry).

- [ ] **Step 1: Append the failing tests**

```python
cal = load("calendar")
print("\n=== calendar ===")
from datetime import date as _d, timedelta as _td   # noqa: E402
_days = [(_d(2016, 1, 4) + _td(i)).isoformat() for i in range(0, 3900)
         if (_d(2016, 1, 4) + _td(i)).weekday() < 5]
_hol = {"2016-01-18", "2016-02-15", "2019-04-19", "2026-07-03"}  # MLK, Presidents' Day, Good Friday, July 4th observed
_trd = [x for x in _days if x not in _hol and x <= "2026-08-31"]
check("third Friday of Jan 2016 is the 15th", cal.third_friday(2016, 1) == _d(2016, 1, 15))
check("April 2019 expiry moves to Thursday the 18th (Good Friday)", cal.monthly_expiry(2019, 4, set(_trd)) == "2019-04-18")
_e = cal.entries(_trd)
check(f"first pair: enter 19 Jan 2016 (after MLK Day), expire 19 Feb ({_e[0]})", _e[0] == ("2016-01-19", "2016-02-19"))
check(f"last pair ends by 31 Aug 2026: enter 20 Jul, expire 21 Aug ({_e[-1]})", _e[-1] == ("2026-07-20", "2026-08-21"))
_g = [(_d.fromisoformat(b) - _d.fromisoformat(a)).days for a, b in _e]
check(f"every holding period is 24-32 days ({min(_g)}-{max(_g)})", min(_g) >= 24 and max(_g) <= 32)
check(f"about 127 trades ({len(_e)})", 125 <= len(_e) <= 128)
check("pairs never overlap", all(_e[i][1] < _e[i + 1][0] for i in range(len(_e) - 1)))
```

- [ ] **Step 2: Run and confirm failure** (`FileNotFoundError` for `lab/calendar.py`)

- [ ] **Step 3: Write `lab/calendar.py`**

```python
"""lab/ - the trade calendar (EXPLORATORY). Standard monthly options expire on the third Friday,
or the trading day before it when that Friday is a holiday (Good Friday). Each trade enters on the
first trading day after a monthly expiry and holds to the next one."""
from datetime import date, timedelta

FIRST_ENTRY, LAST_EXPIRY = "2016-01-19", "2026-08-31"


def third_friday(y, m):
    d = date(y, m, 1)
    d += timedelta((4 - d.weekday()) % 7)
    return d + timedelta(14)


def monthly_expiry(y, m, trading):
    d = third_friday(y, m)
    while d.isoformat() not in trading:
        d -= timedelta(1)
    return d.isoformat()


def entries(trading_days):
    trading = set(trading_days)
    days = sorted(trading)
    out = []
    y, m = int(days[0][:4]), int(days[0][5:7])
    while True:
        e0 = monthly_expiry(y, m, trading) if third_friday(y, m).isoformat() >= days[0] else None
        y2, m2 = (y + 1, 1) if m == 12 else (y, m + 1)
        if third_friday(y2, m2).isoformat() > days[-1]:
            return out
        if e0:
            nxt = [x for x in days if x > e0]
            e1 = monthly_expiry(y2, m2, trading)
            if nxt and nxt[0] >= FIRST_ENTRY and e1 <= LAST_EXPIRY:
                out.append((nxt[0], e1))
        y, m = y2, m2
```

- [ ] **Step 4: Run the tests; all PASS** (if the "24-32 days" case fails, print `_g` with its
  pairs and read why before changing anything; any holiday-shifted outlier is logged in the
  registration, not hidden).

- [ ] **Step 5: Commit**

```bash
git add lab/calendar.py lab/test_lab.py
git commit -m "lab/: the trade calendar - monthly expiries on the trading calendar, entry after each, 2016-01-19 to 2026-07-20

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Trades, settlement, rules, vega

**Files:**
- Create: `lab/trades.py`
- Modify: `lab/test_lab.py`

**Interfaces:**
- Consumes: `costs.half_spread`, `costs.charged`; `iv_convention.black76(kind, f, k, t, r, vol)`,
  `implied_vol(kind, price, f, k, t, r)`.
- Produces:
  - `INDEX = {"SPY": "VIX", "QQQ": "VXN", "IWM": "RVX", "GLD": "GVZ", "USO": "OVX"}`, `R2_REF = 20.0`;
  - `nearest_strike(chain, target) -> float|None` (two-sided strikes only);
  - `settle(bars, symbol, day) -> float` (the RAW close);
  - `intrinsic(kind, K, S) -> float`;
  - `leg(bid, ask, kind, K, S, case) -> tuple[float, float]` (mid premium, P&L per share);
  - `position(chain, F, S_exp, case, kind="straddle") -> dict|None`, keys `K_put`, `K_call`,
    `premium`, `pnl`, `ret`;
  - `vega76(F, K, T, vol) -> float` (per volatility point);
  - `rule_weights(index_prev, rv_prev, vix_prev, vix3m_prev) -> dict[str, float]` (keys R0..R3).

- [ ] **Step 1: Append the failing tests**

```python
tr = load("trades")
print("\n=== trades ===")
check("index pairs", tr.INDEX == {"SPY": "VIX", "QQQ": "VXN", "IWM": "RVX", "GLD": "GVZ", "USO": "OVX"} and tr.R2_REF == 20.0)
_bars = {"USO": {"2020-04-28": (2.14, 17.12)}}
check("settlement uses the RAW close (2.14), never the split-adjusted one", tr.settle(_bars, "USO", "2020-04-28") == 2.14)
check("call intrinsic", tr.intrinsic("C", 100, 104) == 4 and tr.intrinsic("C", 100, 96) == 0)
check("put intrinsic", tr.intrinsic("P", 100, 96) == 4 and tr.intrinsic("P", 100, 104) == 0)
prem, pnl = tr.leg(2.00, 2.20, "C", 100, 103, "mid")
check(f"short call at mid 2.10, expires 3 in the money: P&L -0.90 ({pnl:.2f})", abs(prem - 2.10) < 1e-12 and abs(pnl + 0.90) < 1e-12)
_, pnlr = tr.leg(2.00, 2.20, "C", 100, 103, "retail")
check(f"retail sells 0.08 below mid: P&L -0.98 ({pnlr:.2f})", abs(pnlr + 0.98) < 1e-12)
_ch = {95.0: {"C": (6.0, 6.2), "P": (1.0, 1.1)}, 100.0: {"C": (3.0, 3.2), "P": (2.9, 3.1)},
       105.0: {"C": (1.0, 1.1), "P": (5.9, 6.1)}, 101.0: {"C": (2.5, 2.6)}}
check("ATM picks the nearest TWO-SIDED strike (101 has no put)", tr.nearest_strike(_ch, 100.9) == 100.0)
st_ = tr.position(_ch, 100.0, 100.0, "mid")
check(f"straddle at 100 settling at 100: premium 6.10, keeps it all ({st_})",
      abs(st_["premium"] - 6.10) < 1e-12 and abs(st_["pnl"] - 6.10) < 1e-12 and abs(st_["ret"] - 1.0) < 1e-12)
sg = tr.position(_ch, 100.0, 90.0, "mid", kind="strangle")
check(f"strangle 95/105 settling at 90: premium 2.10, loses 5 on the put ({sg})",
      sg["K_put"] == 95.0 and sg["K_call"] == 105.0 and abs(sg["pnl"] - (2.10 - 5.0)) < 1e-12)
_F, _K, _T, _v = 100.0, 100.0, 30 / 365, 0.25
_num = (black76("C", _F, _K, _T, 0.0, _v + 1e-4) - black76("C", _F, _K, _T, 0.0, _v - 1e-4)) / 2e-4 / 100
check(f"vega per point matches the numerical derivative ({tr.vega76(_F, _K, _T, _v):.5f} vs {_num:.5f})",
      abs(tr.vega76(_F, _K, _T, _v) - _num) < 1e-6)
w = tr.rule_weights(25.0, 15.0, 22.0, 24.0)
check(f"rules, calm contango, index above realised: all trade, R2 = 20/25 ({w})", w == {"R0": 1.0, "R1": 1.0, "R2": 0.8, "R3": 1.0})
w2 = tr.rule_weights(25.0, 30.0, 30.0, 27.0)
check(f"index below realised and inverted VIX: R1 and R3 stand aside ({w2})", w2["R1"] == 0.0 and w2["R3"] == 0.0 and w2["R0"] == 1.0)
check("no realised volatility yet: R1 does not trade", tr.rule_weights(25.0, None, 22.0, 24.0)["R1"] == 0.0)
```

- [ ] **Step 2: Run and confirm failure** (`FileNotFoundError` for `lab/trades.py`)

- [ ] **Step 3: Write `lab/trades.py`**

```python
"""lab/ - the trades (EXPLORATORY). Short ATM straddle and 5% OTM strangle, entered at 14:30 New
York, held to expiry, settled at intrinsic on the fund's RAW close. Per-share figures; returns are
per dollar of mid premium. Rules read the previous trading day's closes."""
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "tools"), str(ROOT / "lab")]
import importlib.util as _iu               # noqa: E402

_s = _iu.spec_from_file_location("costs", ROOT / "lab" / "costs.py")
costs = _iu.module_from_spec(_s)
_s.loader.exec_module(costs)

INDEX = {"SPY": "VIX", "QQQ": "VXN", "IWM": "RVX", "GLD": "GVZ", "USO": "OVX"}
R2_REF = 20.0


def nearest_strike(chain, target):
    two = [k for k, q in chain.items() if "C" in q and "P" in q and q["C"][1] > 0 and q["P"][1] > 0]
    return min(two, key=lambda k: (abs(k - target), k)) if two else None


def settle(bars, symbol, day):
    return bars[symbol][day][0]


def intrinsic(kind, K, S):
    return max(S - K, 0.0) if kind == "C" else max(K - S, 0.0)


def leg(bid, ask, kind, K, S, case):
    mid = ((bid or 0.0) + ask) / 2.0
    sold = mid - costs.charged(costs.half_spread(bid, ask), case)
    return mid, sold - intrinsic(kind, K, S)


def position(chain, F, S_exp, case, kind="straddle"):
    if kind == "straddle":
        kp = kc = nearest_strike(chain, F)
    else:
        kp, kc = nearest_strike(chain, 0.95 * F), nearest_strike(chain, 1.05 * F)
    if kp is None or kc is None:
        return None
    pm, pp = leg(*chain[kp]["P"], "P", kp, S_exp, case)
    cm, cp = leg(*chain[kc]["C"], "C", kc, S_exp, case)
    prem = pm + cm
    return {"K_put": kp, "K_call": kc, "premium": prem, "pnl": pp + cp, "ret": (pp + cp) / prem if prem > 0 else None}


def vega76(F, K, T, vol):
    """Black-76 vega with r = 0, per volatility POINT."""
    v = vol * math.sqrt(T)
    d1 = (math.log(F / K) + v * v / 2) / v
    return F * math.sqrt(T) * math.exp(-d1 * d1 / 2) / math.sqrt(2 * math.pi) / 100.0


def rule_weights(index_prev, rv_prev, vix_prev, vix3m_prev):
    return {"R0": 1.0,
            "R1": 1.0 if (rv_prev is not None and index_prev > rv_prev) else 0.0,
            "R2": R2_REF / index_prev,
            "R3": 0.0 if (vix3m_prev is not None and vix_prev is not None and vix3m_prev < vix_prev) else 1.0}
```

- [ ] **Step 4: Run the tests; all PASS.**

- [ ] **Step 5: Commit**

```bash
git add lab/trades.py lab/test_lab.py
git commit -m "lab/: trades - strike choice, raw-close settlement, P&L by cost case, rules R0-R3, Black-76 vega

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Safeguards for Plan 2

**Files:**
- Modify: `tools/audit.py` (after the `lab-margin-ignores-otm` tuple)

- [ ] **Step 1: Add the mutants**

```python
    ("lab-raw-prices-dropped", "options settle on split-adjusted closes instead of raw ones",
     lambda w: _sub(w / "lab/trades.py", "    return bars[symbol][day][0]", "    return bars[symbol][day][1]"),
     "lab/ tests pass"),
    ("lab-cost-roundtrip-charged", "a held-to-expiry trade is charged a round trip",
     lambda w: _sub(w / "lab/costs.py", "    return half * COST_CASES[case]", "    return 2 * half * COST_CASES[case]"),
     "lab/ tests pass"),
```

- [ ] **Step 2: Commit, then run the auditor**

```bash
git add tools/audit.py
git commit -m "Auditor: lab/ settles on raw closes and charges entry only (73 safeguards)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
FRED_KEY=use-cache /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 tools/audit.py 2>&1 | grep -E "lab-|RESULT"
```
Expected: five `KILLED lab-...` lines and `RESULT: 73 of 73 safeguards proven to fail when broken`.

- [ ] **Step 3: Push** (`git push`; the hook prints `RESULT: 0 fail, 3 warn`).

---

### Task 6: Buy every entry day

**Files:**
- Create: `lab/buy_days.py`

**Interfaces:**
- Consumes: `bars.load`, `calendar.entries`, `fetch_lab.fetch`, `fetch_lab.fetch_listings`,
  `fetch_lab.sync_ledger`, `fetch_lab.commit_ledger`, `opra_reference.api_key`.
- Produces: CLI `--dry-run` / real; prints the total and makes one ledger commit.

- [ ] **Step 1: Write `lab/buy_days.py`**

```python
#!/usr/bin/env python3
"""lab/ - buy every monthly entry day's quotes and listings for the five funds (EXPLORATORY).
Priced first, the lab's own cap, nothing bought twice, one ledger commit at the end.

  FRED_KEY=use-cache python lab/buy_days.py --dry-run
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


bars, cal, fl = _load("bars"), _load("calendar"), _load("fetch_lab")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--max-cost", type=float, default=ore.DEFAULT_MAX_COST)
    a = ap.parse_args()
    key = ore.api_key()
    days = sorted(bars.load()["SPY"])
    pairs = cal.entries(days)
    print(f"{len(pairs)} entry days, {pairs[0][0]} to {pairs[-1][0]}")
    if not a.dry_run:
        fl.sync_ledger()
    paid = []
    for entry, _exp in pairs:
        for sym in bars.FUNDS:
            paid.append(fl.fetch(entry, sym, key, a.max_cost, a.dry_run))
            paid.append(fl.fetch_listings(entry, sym, key, a.max_cost, a.dry_run))
    n, usd = sum(1 for p in paid if p > 0), sum(paid)
    if n:
        fl.commit_ledger(n, usd)
    print(f"\n{n} file(s) bought, ${usd:.4f}. {ore.ATTRIBUTION}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Dry run** (prices nothing it hasn't priced before; spends nothing)

Run: `FRED_KEY=use-cache /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 lab/buy_days.py --dry-run 2>&1 | tail -3`
Expected: the entry count (about 127) and every line "within the lab's cap". Add up the printed
costs with
`FRED_KEY=use-cache /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 lab/buy_days.py --dry-run 2>&1 | grep -o 'costs \$[0-9.]*' | awk -F'$' '{s+=$2} END {printf "total $%.2f\n", s}'`
Expected: roughly $8-12. If above $20, stop and report before buying.

- [ ] **Step 3: Buy** (run in the background; about 1,270 requests)

Run: `FRED_KEY=use-cache /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 lab/buy_days.py > ~/Documents/volrec-licensed/lab-buy-entries.log 2>&1`
Expected: the final line "N file(s) bought, $X"; the private repo's last commit is
"spend: lab/ purchases, ...". Check `tail -2 ~/Documents/volrec-licensed/lab-buy-entries.log` and
`git -C ~/Documents/volrec-licensed log --oneline -1`.

- [ ] **Step 4: Commit the script**

```bash
git add lab/buy_days.py
git commit -m "lab/: buy every monthly entry day (quotes + listings), priced first, one ledger commit

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Run the trades and print the first results

**Files:**
- Create: `lab/run_trades.py`
- Modify: `lab/REGISTRATION.md` (Log, AFTER data)

**Interfaces:**
- Consumes: everything above; `data/market_vol.json` (`{index: {date: level}}`);
  `analyze.realized_vol`, `analyze.log_returns`; `integrity.chain_at`, `check_chain`, `forward`,
  `listed_strikes`; `costs.strip_cost`, `costs.straddle_cost`; `iv_convention.implied_vol`.
- Produces: `~/Documents/volrec-licensed/lab-out/trades.csv` (private, one row per fund x entry)
  and a printed aggregate report.

- [ ] **Step 1: Write `lab/run_trades.py`**

```python
#!/usr/bin/env python3
"""lab/ - run every monthly trade and print aggregates (EXPLORATORY). Per-trade rows carry option
prices, so they go to the private folder; the screen shows aggregates only.

  FRED_KEY=use-cache python lab/run_trades.py
"""
import csv
import importlib.util as iu
import json
import statistics as st
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "tools"), str(ROOT / "lab")]
import analyze                             # noqa: E402
import opra_reference as ore               # noqa: E402
from iv_convention import implied_vol      # noqa: E402


def _load(name):
    s = iu.spec_from_file_location(name, ROOT / "lab" / f"{name}.py")
    m = iu.module_from_spec(s)
    s.loader.exec_module(m)
    return m


bars_m, cal, fl, integ, tr, costs = (_load(n) for n in ("bars", "calendar", "fetch_lab", "integrity", "trades", "costs"))
OUT = fl.PRIVATE / "lab-out" / "trades.csv"
CASES = ("mid", "timed", "retail", "quoted")


def prev_day(series, day):
    ks = [d for d in series if d < day]
    return series[max(ks)] if ks else None


def rv21(adj, day):
    ds = sorted(d for d in adj if d < day)[-22:]
    if len(ds) < 22:
        return None
    return 100.0 * analyze.realized_vol(analyze.log_returns([adj[d] for d in ds]))


def chain_rows(opra, when, day, sym, F):
    """Every expiry 7-60 days out in the recorder's row format, for the registered estimator."""
    rows = []
    exps = sorted({p[1] for p in map(integ.parse_osi, opra) if p})
    for e in exps:
        dte = (date.fromisoformat(e) - date.fromisoformat(day)).days
        if not 7 <= dte <= 60:
            continue
        for k, q in integ.chain_at(opra, e, when).items():
            for t, (b, a) in q.items():
                rows.append({"date": day, "symbol": sym, "spot": str(F), "expiration": e, "dte": str(dte),
                             "type": t, "strike": str(k), "bid": str(b), "ask": str(a), "mid": str((b + a) / 2)})
    return rows


def main():
    bars = bars_m.load()
    vol = json.load(open(ROOT / "data" / "market_vol.json"))
    pairs = cal.entries(sorted(bars["SPY"]))
    out, excluded = [], []
    for entry, expiry in pairs:
        when = fl.ny_minute(entry)
        for sym in bars_m.FUNDS:
            p = fl.LAB_DIR / f"{fl.lab_stem(sym, entry, '14:30')}.csv"
            d = fl.LAB_DIR / f"{fl.def_stem(sym, entry)}.csv"
            if not (p.exists() and d.exists()):
                excluded.append((entry, sym, "no file"))
                continue
            opra = ore.load_opra(p)
            ch = integ.chain_at(opra, expiry, when)
            ok_, det = integ.check_chain(ch, integ.listed_strikes(d, expiry))
            if not ok_:
                excluded.append((entry, sym, "; ".join(f"{k}: {v[1]}" for k, v in det.items() if not v[0])))
                continue
            F = integ.forward(ch)
            S_exp = tr.settle(bars, sym, expiry)
            T = (date.fromisoformat(expiry) - date.fromisoformat(entry)).days / 365.0
            idx = prev_day(vol[tr.INDEX[sym]], entry)
            w = tr.rule_weights(idx, rv21({k: v[1] for k, v in bars[sym].items()}, entry),
                                prev_day(vol["VIX"], entry), prev_day(vol["VIX3M"], entry))
            row = {"entry": entry, "expiry": expiry, "symbol": sym, "F": F, "S_exp": S_exp, "index": idx, **w}
            for kind in ("straddle", "strangle"):
                for case in CASES:
                    pos = tr.position(ch, F, S_exp, case, kind)
                    row[f"{kind}_{case}_ret"] = pos["ret"] if pos else None
            K = tr.nearest_strike(ch, F)
            c, pq = ch[K]["C"], ch[K]["P"]
            ivc = implied_vol("C", (c[0] + c[1]) / 2, F, K, T, 0.0)
            ivp = implied_vol("P", (pq[0] + pq[1]) / 2, F, K, T, 0.0)
            atm = None
            if ivc and ivp:
                atm = costs.vol_points(costs.straddle_cost(c, pq, "quoted"),
                                       tr.vega76(F, K, T, ivc) + tr.vega76(F, K, T, ivp))
            row["atm_cost_pts"] = atm
            row["strip_cost_pts"] = costs.strip_cost(chain_rows(opra, when, entry, sym, F), 0.0)
            out.append(row)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=list(out[0]))
        wr.writeheader()
        wr.writerows(out)
    report(out, excluded)


def report(out, excluded):
    print(f"lab/ trades (EXPLORATORY): {len(out)} fund-months; {len(excluded)} excluded\n")
    for kind in ("straddle", "strangle"):
        print(f"== short {kind}, mean return per $1 of mid premium; kept = case mean / mid mean ==")
        for sym in ("SPY", "QQQ", "IWM", "GLD", "USO"):
            rs = [r for r in out if r["symbol"] == sym and r[f"{kind}_mid_ret"] is not None]
            if not rs:
                continue
            mid = st.mean(r[f"{kind}_mid_ret"] for r in rs)
            parts = []
            for case in ("timed", "retail", "quoted"):
                m = st.mean(r[f"{kind}_{case}_ret"] for r in rs)
                parts.append(f"{case} {m:+.3f} (kept {m / mid:.2f})" if mid > 0 else f"{case} {m:+.3f}")
            worst = min(r[f"{kind}_mid_ret"] for r in rs)
            print(f"  {sym:4s} n={len(rs):3d}  mid {mid:+.3f}  " + "  ".join(parts) + f"  worst {worst:+.2f}")
        print()
    print("== rules, short straddle, retail case: weighted mean return per $1 of premium ==")
    for sym in ("SPY", "QQQ", "IWM", "GLD", "USO"):
        rs = [r for r in out if r["symbol"] == sym and r["straddle_retail_ret"] is not None]
        cells = []
        for rule in ("R0", "R1", "R2", "R3"):
            ws = [(r[rule], r["straddle_retail_ret"]) for r in rs if r[rule] > 0]
            tot = sum(w for w, _ in ws)
            cells.append(f"{rule} {sum(w * x for w, x in ws) / tot:+.3f} (n={len(ws)})" if tot else f"{rule} n=0")
        print(f"  {sym:4s} " + "  ".join(cells))
    print("\n== Q3: strip cost over ATM cost (quoted half-spread, volatility points), median ==")
    for sym in ("SPY", "QQQ", "IWM", "GLD", "USO"):
        xs = [r["strip_cost_pts"] / r["atm_cost_pts"] for r in out
              if r["symbol"] == sym and r["strip_cost_pts"] and r["atm_cost_pts"]]
        if xs:
            print(f"  {sym:4s} n={len(xs):3d}  ratio median {st.median(xs):.2f}  (P3 predicts >= 2)")
    if excluded:
        print("\nexcluded fund-days:")
        for e in excluded:
            print(f"  {e[0]} {e[1]}: {e[2]}")
    print(f"\n{ore.ATTRIBUTION} Cboe index levels: Cboe Global Markets.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run it**

Run: `FRED_KEY=use-cache /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 lab/run_trades.py 2>&1 | tee ~/Documents/volrec-licensed/lab-out/report-plan2.txt`
Expected: about 635 fund-months (5 x ~127) less any excluded; the three tables; the exclusion
list. If it crashes, fix the cause with a new test first; never hide a crash.

- [ ] **Step 3: Log the first results in `lab/REGISTRATION.md`** (AFTER data): copy each table's
  numbers, and P3's verdict (ratio >= 2 on how many funds), into a dated Log entry. P1, P2, P4
  and P5 wait for Plan 3, since they need margin and the Leak Map.

- [ ] **Step 4: Commit and push**

```bash
git add lab/run_trades.py lab/REGISTRATION.md
git commit -m "lab/: every monthly trade 2016-2026 run on real OPRA quotes - first aggregates logged (exploratory)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
FRED_KEY=use-cache /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 tools/audit.py 2>&1 | tail -1
git push
```
