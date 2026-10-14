#!/usr/bin/env python3
"""lab/ data put to work for the MAIN project (EXPLORATORY; 14 Oct 2026 audit). Aggregates only.
Touches no registered window (all days 2016 - Aug 2026) and no Cboe index comparison (kept clean for
a possible registered test).

(a) Timing: on Wednesdays in the stress months the lab holds OPRA at 14:30 AND 15:55 New York. The
    registered estimator (modelfree.model_free_30d, r = 0) at both times measures how far a 30-day
    model-free volatility moves between the project's snapshot time and near the close - the effect
    LSEG intraday data was wanted for. Stress months, so read as an upper range.
(b) H8's trading-cost yardstick over ten years: the OPRA at-the-money half-spread in volatility
    points from the weekly samples, 2016-2026, and 2026 alone, beside H8-DRAFT's 3-week pilot.

  FRED_KEY=use-cache python lab/main_links.py
"""
import importlib.util as iu
import json
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "tools"), str(ROOT / "lab")]
import modelfree                           # noqa: E402
import opra_reference as ore               # noqa: E402
from datetime import date                  # noqa: E402


def _load(name):
    s = iu.spec_from_file_location(name, ROOT / "lab" / f"{name}.py")
    m = iu.module_from_spec(s)
    s.loader.exec_module(m)
    return m


bars_m, cal, fl, integ, rt, rb = (_load(n) for n in ("bars", "tradecal", "fetch_lab", "integrity", "run_trades", "run_breakeven"))
FUNDS = ("SPY", "QQQ", "IWM", "GLD", "USO")
H8_PILOT_OPRA = {"SPY": 0.034, "QQQ": 0.066, "IWM": 0.102, "GLD": 0.315, "USO": 1.331}   # H8-DRAFT, 17 Sep - 9 Oct 2026


def estimate(sym, day, hhmm):
    p = fl.LAB_DIR / f"{fl.lab_stem(sym, day, hhmm)}.csv"
    if not p.exists():
        return None
    opra, when = ore.load_opra(p), fl.ny_minute(day, hhmm)
    exps = sorted({x[1] for x in map(integ.parse_osi, opra) if x and 20 <= (date.fromisoformat(x[1]) - date.fromisoformat(day)).days <= 45})
    F = integ.forward(integ.chain_at(opra, exps[0], when)) if exps else None
    if not F:
        return None
    got = modelfree.model_free_30d(rt.chain_rows(opra, when, day, sym, F), 0.0)
    return got[0] if got else None


def main():
    bars = bars_m.load()
    days = sorted(bars["SPY"])
    weds = [d for d in cal.weekly_days(days) if d in set(cal.stress_days(days)) and d not in cal.EARLY_CLOSES]
    print("(a) 30-day model-free volatility, 15:55 minus 14:30 New York, same day (stress-month Wednesdays)")
    allm = []
    for s in FUNDS:
        moves = []
        for d in weds:
            a, b = estimate(s, d, "14:30"), estimate(s, d, "15:55")
            if a is not None and b is not None:
                moves.append(b - a)
        allm += moves
        if moves:
            print(f"   {s}: {len(moves)} days; median move {st.median(moves):+.2f} pts, median |move| {st.median(abs(x) for x in moves):.2f}, "
                  f"largest |move| {max(abs(x) for x in moves):.2f}")
    print(f"   all funds: median |move| {st.median(abs(x) for x in allm):.2f} pts over ~85 minutes, in stress months\n")
    print("(b) OPRA at-the-money half-spread in volatility points (weekly samples) vs H8-DRAFT's 3-week pilot")
    vol = json.load(open(ROOT / "data" / "market_vol.json"))
    for s in FUNDS:
        w = rb.weekly(s, bars, vol, set(days))
        hs = [r["cost_pts"] / 0.8 for r in w]
        h26 = [r["cost_pts"] / 0.8 for r in w if r["day"] >= "2026-01-01"]
        print(f"   {s}: 2016-2026 median {st.median(hs):.3f} (n={len(hs)}); 2026 median {st.median(h26):.3f} (n={len(h26)}); "
              f"H8 pilot {H8_PILOT_OPRA[s]:.3f}")
    print(f"\n{ore.ATTRIBUTION}")


if __name__ == "__main__":
    main()
