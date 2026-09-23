"""Unit tests for the delta-hedged P&L estimator. No network, no API keys.

Every case here is hand-computable, which is the point: the sign convention on
a delta-hedged gain is easy to get backwards, and getting it backwards would
flip the reported direction of the variance risk premium without anything
looking obviously wrong.

  python tools/test_hedged.py
"""
import importlib.util as iu
import sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R))
_s = iu.spec_from_file_location("h", R / "hedged.py")
h = iu.module_from_spec(_s); _s.loader.exec_module(h)

fails = []


def row(d, osym="X", spot=100.0, mid=5.0, delta=0.5, mny=1.0, strike=100.0,
        sym="TST", typ="C", iv="0.2", vol="10", oi="100"):
    return {"date": d, "symbol": sym, "option_symbol": osym, "type": typ,
            "spot": str(spot), "mid": str(mid), "delta": str(delta),
            "moneyness": str(mny), "strike": str(strike), "iv": iv,
            "volume": vol, "open_interest": oi}


def check(name, got, want, tol=1e-9):
    ok = got is not None and abs(got - want) < tol
    print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    if not ok:
        fails.append(name)


def istrue(name, cond):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}")
    if not cond:
        fails.append(name)


print("=== hedge identity: option moves exactly delta x spot, r=0 => P&L 0 ===")
check("perfect hedge nets to zero",
      h.hedged_gain([row("2026-01-05", spot=100, mid=5.0, delta=0.5),
                     row("2026-01-06", spot=102, mid=6.0, delta=0.5)], 0.0)["pnl"], 0.0)

print("\n=== sign convention: decay beyond the hedge is a LOSS to the buyer ===")
check("pnl = -0.5 when the option gives up 0.5 beyond delta",
      h.hedged_gain([row("2026-01-05", spot=100, mid=5.0, delta=0.5),
                     row("2026-01-06", spot=102, mid=5.5, delta=0.5)], 0.0)["pnl"], -0.5)
print("        negative gain == positive variance risk premium (Bakshi & Kapadia)")

print("\n=== financing: long call plus short delta shares is net cash positive ===")
check("credit of r*(delta*S - C)/365",
      h.hedged_gain([row("2026-01-05", spot=100, mid=5.0, delta=0.5),
                     row("2026-01-06", spot=102, mid=6.0, delta=0.5)], 0.05)["pnl"],
      0.05 * 45 / 365)

print("\n=== multi-day path ===")
g = h.hedged_gain([row("2026-01-05", spot=100, mid=5.0, delta=0.5),
                   row("2026-01-06", spot=101, mid=5.5, delta=0.6),
                   row("2026-01-07", spot=103, mid=6.7, delta=0.6)], 0.0)
check("three observations, hedge rebalanced, nets to zero", g["pnl"], 0.0)
check("day count is intervals not observations", float(g["days"]), 2.0)

print("\n=== scaling ===")
check("scaled == pnl / S0",
      h.hedged_gain([row("2026-01-05", spot=200, mid=5.0, delta=0.5),
                     row("2026-01-06", spot=202, mid=5.5, delta=0.5)], 0.0)["scaled"],
      -0.5 / 200)

print("\n=== run splitting ===")
istrue("Friday to Monday is one run, not two",
       len(h.runs_for_contract([row("2026-01-09"), row("2026-01-12"),
                                row("2026-01-13")])) == 1)
istrue("a two-week gap splits the run",
       len(h.runs_for_contract([row("2026-01-05"), row("2026-01-06"),
                                row("2026-01-20"), row("2026-01-21")])) == 2)
istrue("a lone observation yields no run",
       h.runs_for_contract([row("2026-01-05")]) == [])
# 23 Sep 2026: a missed SESSION must split a run even inside four calendar days;
# the old calendar proxy spliced 15 -> 17 Sep across the lost 16 Sep.
istrue("a missed trading day splits the run (Tue -> Thu)",
       len(h.runs_for_contract([row("2026-09-14"), row("2026-09-15"),
                                row("2026-09-17"), row("2026-09-18")])) == 2)
istrue("a holiday weekend joins (Fri 4 Sep -> Tue 8 Sep, Labor Day between)",
       len(h.runs_for_contract([row("2026-09-03"), row("2026-09-04"),
                                row("2026-09-08")])) == 1)
istrue("a Thanksgiving gap joins (Wed 25 Nov -> Fri 27 Nov)",
       len(h.runs_for_contract([row("2026-11-24"), row("2026-11-25"),
                                row("2026-11-27")])) == 1)

print("\n=== bad data is rejected rather than silently treated as zero ===")
for bad, label in [({"mid": "0"}, "zero mid"), ({"delta": ""}, "missing delta"),
                   ({"spot": "0"}, "zero spot"), ({"mid": "abc"}, "non-numeric mid")]:
    r2 = row("2026-01-06"); r2.update(bad)
    istrue(f"{label} rejects the run",
           h.hedged_gain([row("2026-01-05"), r2], 0.0) is None)

print("\n=== moneyness buckets ===")
for m, want in [(0.85, "deep OTM put"), (0.95, "OTM put"), (1.00, "at the money"),
                (1.05, "OTM call"), (1.20, "deep OTM call")]:
    istrue(f"{m} -> {want}", h.bucket_of(m) == want)

print("\n" + "=" * 52)
print(f"RESULT: {len(fails)} failure(s)" + (f": {fails}" if fails else ""))
sys.exit(1 if fails else 0)
