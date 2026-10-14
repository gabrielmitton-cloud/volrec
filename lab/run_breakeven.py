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
