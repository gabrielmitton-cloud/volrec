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
    # (hc + hp) / (vc + vp): the two legs' halves and vegas both double, so no factor of 2 (14 Oct fix)
    cost_raw = RETAIL * cost if cost is not None else None
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
