#!/usr/bin/env python3
"""lab/ - recompute the lab's key numbers by an independent route (EXPLORATORY; 14 Oct 2026 audit).
Aggregates only. Does not trust the lab's own code where it can avoid it:

1. Settlement closes (Alpaca, raw) against OPRA's put-call-implied forward at 15:55 on expiry days in
   the stress months (5 minutes before the close; near expiry the forward is the spot).
2. The COVID trade (SPY, 24 Feb -> 20 Mar 2020) rebuilt from the raw CSV with the csv module only,
   against Plan 2's per-trade row.
3. The Black-76 model marks against the real OPRA marks in the stress months (the spec asked for this
   gap to be reported; the 14 Oct audit found it had not been).
4. The Leak Map arithmetic: the Shapley leaks must sum exactly to paper minus kept.

  FRED_KEY=use-cache python lab/audit_numbers.py
"""
import csv
import importlib.util as iu
import json
import statistics as st
import sys
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "tools"), str(ROOT / "lab")]
import opra_reference as ore               # noqa: E402


def _load(name):
    s = iu.spec_from_file_location(name, ROOT / "lab" / f"{name}.py")
    m = iu.module_from_spec(s)
    s.loader.exec_module(m)
    return m


bars_m, cal, fl, integ, tr, rl = (_load(n) for n in ("bars", "tradecal", "fetch_lab", "integrity", "trades", "run_leak"))
FUNDS = ("SPY", "QQQ", "IWM", "GLD", "USO")


def check_settlement(bars):
    print("1. Settlement closes vs OPRA's implied forward at 15:55 on expiry days (stress months)")
    days = sorted(bars["SPY"])
    exps = sorted({e for _x, e in cal.entries(days)} & set(cal.stress_days(days)))
    gaps = []
    for e in exps:
        hh = cal.slot(e, "15:55")
        for s in FUNDS:
            p = fl.LAB_DIR / f"{fl.lab_stem(s, e, hh)}.csv"
            if not p.exists():
                continue
            F = integ.forward(integ.chain_at(ore.load_opra(p), e, fl.ny_minute(e, hh)))
            if F and e in bars[s]:
                g = (bars[s][e][0] / F - 1) * 100
                gaps.append((abs(g), s, e, g))
    gaps.sort(reverse=True)
    print(f"   {len(gaps)} fund-expiries; median |close / forward - 1| {st.median(g[0] for g in gaps):.3f}%; "
          f"largest {gaps[0][1]} {gaps[0][2]} {gaps[0][3]:+.3f}%")
    return gaps


def covid_trade(bars):
    print("2. The COVID trade rebuilt from the raw file (csv module only)")
    p = fl.LAB_DIR / "OPRA_LAB_SPY_2020-02-24_1430.csv"
    when = datetime(2020, 2, 24, 19, 30, tzinfo=timezone.utc)          # 14:30 New York, EST
    best = {}
    with p.open(newline="") as f:
        rd = csv.DictReader(f)
        for r in rd:
            sym = "".join(r["symbol"].split())
            if "200320" not in sym or not r["ask_px_00"]:
                continue
            t = ore.parse_ts(r["ts_recv"])
            d = abs((t - when).total_seconds())
            if d <= 120 and (sym not in best or d < best[sym][0]):
                best[sym] = (d, float(r["bid_px_00"] or 0), float(r["ask_px_00"]))
    mids = {}
    for sym, (_d, b, a) in best.items():
        k, kind = int(sym[-8:]) / 1000, sym[-9]
        mids.setdefault(k, {})[kind] = (b + a) / 2
    K = min((k for k, v in mids.items() if "C" in v and "P" in v), key=lambda k: abs(mids[k]["C"] - mids[k]["P"]))
    prem = mids[K]["C"] + mids[K]["P"]
    S = bars["SPY"]["2020-03-20"][0]
    ret = (prem - abs(S - K)) / prem
    row = next(r for r in csv.DictReader(open(fl.PRIVATE / "lab-out" / "trades.csv")) if r["symbol"] == "SPY" and r["entry"] == "2020-02-24")
    print(f"   strike {K:g}, premium {prem:.2f}, settle {S:.2f}: return per $1 of premium {ret:+.4f}; "
          f"Plan 2's row {float(row['straddle_mid_ret']):+.4f} -> {'MATCH' if abs(ret - float(row['straddle_mid_ret'])) < 0.005 else 'DIFFERENT'}")
    return ret, float(row["straddle_mid_ret"])


def model_vs_real(bars, vol):
    print("3. Model marks (Black-76 at the fund's own index) vs real OPRA marks, stress months")
    stress = set(cal.stress_days(sorted(bars["SPY"])))
    for s in FUNDS:
        idx, errs = vol[tr.INDEX[s]], []
        for m in rl.months_for(s, bars, vol, set()):
            for day in (d for d in sorted(bars[s]) if m["entry"] < d < m["expiry"] and d in stress):
                rm, lvl = rl.real_mark(s, day, m["expiry"], m["K"]), idx.get(day)
                if not rm or lvl is None:
                    continue
                T = (date.fromisoformat(m["expiry"]) - date.fromisoformat(day)).days / 365.0
                mm = rl.model_mark(bars[s][day][0], m["K"], T, lvl / 100.0)
                real_v, model_v = rm[1] + rm[2], mm[1] + mm[2]
                if real_v > 0:
                    errs.append((model_v - real_v) / real_v * 100)
        if errs:
            print(f"   {s}: {len(errs)} day-marks; model - real, median {st.median(errs):+.1f}% of the straddle's value, "
                  f"median |error| {st.median(abs(e) for e in errs):.1f}%")


def leak_sums():
    print("4. Leak Map arithmetic: Shapley leaks sum to paper - kept")
    d = json.load(open(fl.PRIVATE / "lab-out" / "leak_summary.json"))
    worst = max(abs(v["paper"] - v["kept"] - sum(x[0] for x in v["leaks"].values()))
                for f in d.values() for v in f["weights"].values())
    print(f"   largest discrepancy over 5 funds x 4 sizes: {worst:.2e} -> {'EXACT' if worst < 1e-12 else 'CHECK'}")
    return worst


def main():
    bars = bars_m.load()
    vol = json.load(open(ROOT / "data" / "market_vol.json"))
    check_settlement(bars)
    covid_trade(bars)
    model_vs_real(bars, vol)
    leak_sums()
    print(f"\n{ore.ATTRIBUTION}")


if __name__ == "__main__":
    main()
