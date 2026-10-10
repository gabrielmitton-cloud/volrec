"""Unit tests for H8's instrument (tools/h8_quotes.py). No network, no licensed data: synthetic data
written in the providers' REAL formats (Databento's header, padded OSI symbols, a BLANK for no bid;
the free surface's own columns). python tools/test_h8.py
"""
import importlib.util as iu
import math
import random
import sys
import tempfile
from datetime import date
from pathlib import Path

R = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(R), str(R / "tools")]
_s = iu.spec_from_file_location("h8", R / "tools/h8_quotes.py")
h8 = iu.module_from_spec(_s); _s.loader.exec_module(h8)
from calibrate import black76                      # noqa: E402
fails = []


def check(name, cond):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}")
    if not cond:
        fails.append(name)


print("=== the arithmetic, against hand-computed answers ===")
check("ar1 of an alternating series is strongly negative (1,-1,... -> -(n-1)/n)",
      abs(h8.ar1([1, -1, 1, -1, 1, -1]) - (-5 / 6)) < 1e-12)
check("ar1 of a straight line, 1..5: lag-1 autocovariance 2 over variance 10 = +0.4",
      abs(h8.ar1([1, 2, 3, 4, 5]) - 0.4) < 1e-12)
check("n_eff at T=40, rho=0.9 is 40*0.1/1.9 = 2.105 (the methods report's example)",
      abs(h8.n_eff(40, 0.9) - 40 * 0.1 / 1.9) < 1e-12)
check("n_eff gives no credit for negative rho (T=20, rho=-0.3 -> 20)", h8.n_eff(20, -0.3) == 20)
check("n_eff never falls below 1", h8.n_eff(3, 0.99) == 1.0)
check("MDE at sd=1, n_eff=10 is 2.8/sqrt(10) = 0.885 (the report's example)",
      abs(h8.mde(1.0, 10) - 2.8 / math.sqrt(10)) < 1e-12)

print("\n=== the equivalence test ===")
rng = random.Random(7)
near0 = [rng.gauss(0.0, 0.05) for _ in range(40)]
mu, se, plo, phi, eq = h8.tost(near0, 0.25, 3)
check(f"gaps around 0 (sd 0.05) are equivalent within +/-0.25 (p {plo:.2g}, {phi:.2g})", eq)
far = [v + 0.40 for v in near0]
check("the same gaps shifted to +0.40 are NOT equivalent within +/-0.25", not h8.tost(far, 0.25, 3)[4])
neg = [v - 0.40 for v in near0]
check("...nor shifted to -0.40 (both one-sided tests are live)", not h8.tost(neg, 0.25, 3)[4])
noisy = [rng.gauss(0.0, 1.0) for _ in range(12)]
check("12 days of sd-1.0 noise cannot show equivalence within +/-0.25 (absence of evidence)",
      not h8.tost(noisy, 0.25, 3)[4])
check("a constant series has no standard error and is never declared equivalent",
      h8.tost([0.1] * 10, 0.25, 3)[4] is False)

print("\n=== one fund, one day, from files in the providers' real formats ===")
D = "2026-10-09"
E1, E2 = date(2026, 10, 23), date(2026, 11, 20)
S, SIG = 100.0, 0.30


def rows_and_opra(shift_mid=0.0, blank_far_bids=True):
    rows, lines = [], ["ts_recv,ts_event,rtype,publisher_id,instrument_id,side,price,size,flags,"
                       "bid_px_00,ask_px_00,bid_sz_00,ask_sz_00,bid_pb_00,ask_pb_00,symbol"]
    for e, dte in ((E1, 14), (E2, 42)):
        T = dte / 365.0
        for K in range(70, 131, 5):
            for k in "CP":
                p = black76(k, S, float(K), T, 0.0, SIG)
                b, a = (round(p * 0.98, 4), round(p * 1.02, 4)) if p > 0.05 else (0.0, 0.05)
                osi = f"XYZ{e:%y%m%d}{k}{K * 1000:08d}"
                rows.append({"date": D, "symbol": "XYZ", "spot": str(S), "quote_time": f"{D}T18:42:10Z",
                             "expiration": e.isoformat(), "dte": str(dte), "type": k, "strike": str(float(K)),
                             "option_symbol": osi, "bid": str(b), "ask": str(a), "mid": str((b + a) / 2)})
                ob, oa = b + shift_mid, a + shift_mid
                bb = "" if (b == 0 and blank_far_bids) else f"{ob:.4f}"   # Databento: no bid -> BLANK
                occ = f"XYZ   {e:%y%m%d}{k}{K * 1000:08d}"
                for mm in ("41", "42", "43", "44"):
                    lines.append(f"{D}T18:{mm}:00.000000000Z,,193,30,1,N,,0,0,{bb},{oa:.4f},1,1,1,1,{occ}")
    tmp = Path(tempfile.mkdtemp()) / f"OPRA_XYZ_{D}.csv"
    tmp.write_text("\n".join(lines) + "\n")
    return rows, h8.ore.load_opra(tmp), tmp


rows, opra, path = rows_and_opra()
x = h8.day_pair(rows, opra, 0.0)
check("the fixture's OPRA file really carries BLANK bids (the case real files have)",
      ",0,0,,0.0500," in path.read_text())
check(f"every contract matches within 120 s ({x['n_match']} of {x['n_band']})", x["n_match"] == x["n_band"])
check(f"identical quotes on both feeds give a gap of exactly 0 ({x['S0m']:.6f} vs {x['S1']:.6f})",
      x["S0m"] is not None and abs(x["S0m"] - x["S1"]) < 1e-12)
check(f"the estimate reads near the chain's 30% ({x['S1']:.2f})", abs(x["S1"] - 30.0) < 2.0)
check("an unchanged next minute gives a noise floor of exactly 0", abs(x["S1n"] - x["S1b"]) < 1e-12)
rows2, opra2, _ = rows_and_opra(shift_mid=0.02)
y = h8.day_pair(rows2, opra2, 0.0)
check(f"OPRA quoting 2 cents higher everywhere reads HIGHER, so free - OPRA < 0 ({y['S0m'] - y['S1']:+.3f})",
      y["S0m"] - y["S1"] < 0)
stale = [dict(r, quote_time=f"{D}T15:02:00Z") if i % 4 == 0 else r for i, r in enumerate(rows)]
z = h8.day_pair(stale, opra, 0.0)
check(f"a free quote hours older than every OPRA record is excluded, not matched ({z['n_match']} of {z['n_band']})",
      z["n_match"] == len(rows) - len(rows[::4]))
check("excluded contracts leave the free-only estimate S0 on the full band", z["S0"] == x["S0"])
check("an empty band gives no reading", h8.day_pair([], opra, 0.0) is None)

print(f"\n{len(fails)} failure(s)")
sys.exit(1 if fails else 0)
