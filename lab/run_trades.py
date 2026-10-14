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


bars_m, cal, fl, integ, tr, costs = (_load(n) for n in ("bars", "tradecal", "fetch_lab", "integrity", "trades", "costs"))
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
        hhmm = cal.slot(entry, "14:30")                 # 11:30 on a half-day (24 Dec 2018)
        when = fl.ny_minute(entry, hhmm)
        for sym in bars_m.FUNDS:
            p = fl.LAB_DIR / f"{fl.lab_stem(sym, entry, hhmm)}.csv"
            d = fl.LAB_DIR / f"{fl.def_stem(sym, entry)}.csv"
            if not (p.exists() and d.exists()):
                excluded.append((entry, sym, "no file"))
                continue
            opra = ore.load_opra(p)
            ch = integ.chain_at(opra, expiry, when)
            ok_, det = integ.check_chain(ch, integ.listed_strikes(d, expiry))
            if not ok_:
                excluded.append((entry, sym, "; ".join(f"{k}: {v[1]}" for k, v in det.items() if not v[0])))
            F = integ.forward(ch)
            if F is None:
                continue
            # Sensitivity (added 14 Oct AFTER the first run): an excluded month that can still be
            # traded is priced too, flagged registered=0, so the report shows what exclusion does.
            S_exp = tr.settle(bars, sym, expiry)
            T = (date.fromisoformat(expiry) - date.fromisoformat(entry)).days / 365.0
            idx = prev_day(vol[tr.INDEX[sym]], entry)
            w = tr.rule_weights(idx, rv21({k: v[1] for k, v in bars[sym].items()}, entry),
                                prev_day(vol["VIX"], entry), prev_day(vol["VIX3M"], entry))
            row = {"entry": entry, "expiry": expiry, "symbol": sym, "registered": 1 if ok_ else 0,
                   "F": F, "S_exp": S_exp, "index": idx, **w}
            for kind in ("straddle", "strangle"):
                for case in CASES:
                    pos = tr.position(ch, F, S_exp, case, kind)
                    row[f"{kind}_{case}_ret"] = pos["ret"] if pos else None
            K = tr.nearest_strike(ch, F)
            if K is None:
                continue
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


def report(out_all, excluded):
    out = [r for r in out_all if r["registered"]]
    print(f"lab/ trades (EXPLORATORY): {len(out)} fund-months pass every check; {len(excluded)} excluded\n")
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
    print("\n== sensitivity: the excluded months that can still be traded, added back (straddle) ==")
    for sym in ("SPY", "QQQ", "IWM", "GLD", "USO"):
        reg = [r for r in out if r["symbol"] == sym and r["straddle_mid_ret"] is not None]
        allr = [r for r in out_all if r["symbol"] == sym and r["straddle_mid_ret"] is not None]
        if len(allr) > len(reg):
            f = lambda rs, c: st.mean(r[f"straddle_{c}_ret"] for r in rs)
            print(f"  {sym:4s} registered n={len(reg):3d} mid {f(reg, 'mid'):+.3f} retail {f(reg, 'retail'):+.3f}"
                  f"  |  with added-back n={len(allr):3d} mid {f(allr, 'mid'):+.3f} retail {f(allr, 'retail'):+.3f}")
        else:
            print(f"  {sym:4s} nothing excluded is tradeable")
    if excluded:
        print("\nexcluded fund-days:")
        for e in excluded:
            print(f"  {e[0]} {e[1]}: {e[2]}")
    print(f"\n{ore.ATTRIBUTION} Cboe index levels: Cboe Global Markets.")


if __name__ == "__main__":
    main()
