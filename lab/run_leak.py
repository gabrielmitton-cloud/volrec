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
        out.append({"entry": entry, "expiry": expiry, "registered": ok_, "K": K, "C0": mid(c), "P0": mid(pq), "half0": hc + hp,
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
            for w in (0.025, 0.10, 0.20):       # the appendix sizes (registered: the Leak Map is drawn at 5%)
                pw, kw = st.mean(res[(w, frozenset())]), st.mean(res[(w, frozenset(mp.FRICTIONS))])
                shw = lm.shapley(lambda s, w=w: st.mean(res[(w, s)]))
                print(f"      at w {100 * w:g}%: paper {100 * pw:+.3f} kept {100 * kw:+.3f}%/mo; leaks " + ", ".join(
                    f"{p} {100 * shw[p][0]:+.4f} ({100 * shw[p][1]:+.4f}..{100 * shw[p][2]:+.4f})" for p in mp.FRICTIONS))
            print("      margin: " + "  ".join(f"w {int(1000 * w) / 10:g}%: eff {100 * eff[w]:.2f}%, called in {liq[w]}"
                                                for w in WEIGHTS))
            if label == "registered":
                kept_series[sym] = res[(0.05, frozenset(mp.FRICTIONS))]
                bres, _e, bliq = table(ms, *mg.BROKER)
                print(f"      broker 40%/35%: kept {100 * st.mean(bres[(0.05, frozenset(mp.FRICTIONS))]):+.3f}%/mo, "
                      f"called in {bliq[0.05]} at w 5%")
                rows += [{"symbol": sym, "entry": m["entry"], "expiry": m["expiry"], "kept_5": r, "real_mark_days": m["real_days"]}
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
    print("\n== crash replays: kept return at w = 5% of every trade HELD during a stress month ==")
    # 14 Oct: keyed by holding period, not entry month - the COVID trade entered 24 Feb 2020 and
    # expired 20 Mar 2020, so an entry-month key hid it from the March 2020 row.
    for mth in cal.STRESS_MONTHS[1:]:
        held = [r for r in rows if r["entry"][:7] <= mth <= r["expiry"][:7]]
        cells = [f"{r['symbol']} {r['entry'][5:]}->{r['expiry'][5:]} {100 * r['kept_5']:+.2f}%" for r in held]
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
