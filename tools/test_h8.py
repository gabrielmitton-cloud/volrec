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
Q = 4000   # the tail-wiring checks run on 4,000 draws for speed; the registered count is h8.H8_REPS (below)
rng = random.Random(7)
near0 = [rng.gauss(0.0, 0.05) for _ in range(40)]
mu, se, plo, phi, eq, ptlo, pthi = h8.tost(near0, 0.25, 3, Q)
check(f"gaps around 0 (sd 0.05) are equivalent within +/-0.25 (p {plo:.2g}, {phi:.2g})", eq)
far = [v + 0.40 for v in near0]
check("the same gaps shifted to +0.40 are NOT equivalent within +/-0.25", not h8.tost(far, 0.25, 3, Q)[4])
neg = [v - 0.40 for v in near0]
check("...nor shifted to -0.40 (both one-sided tests are live)", not h8.tost(neg, 0.25, 3, Q)[4])
noisy = [rng.gauss(0.0, 1.0) for _ in range(12)]
check("12 days of sd-1.0 noise cannot show equivalence within +/-0.25 (absence of evidence)",
      not h8.tost(noisy, 0.25, 3, Q)[4])
check("a constant series has no standard error and is never declared equivalent",
      h8.tost([0.1] * 10, 0.25, 3, Q)[4] is False and len(h8.tost([0.1] * 10, 0.25, 3, Q)) == 7)

print("\n=== the registered choices (4 Nov 2026): the lag rule and fixed-b p-values ===")
check("the lag is the whole number nearest 1.3*sqrt(T): 8 at 41 days (8.32), 8 at 36 (7.80), 7 at 30 (7.12)",
      (h8.lag_for(41), h8.lag_for(36), h8.lag_for(30), h8.lag_for(1)) == (8, 8, 7, 1))


def at(d, lag, t_lo, t_hi):
    """d moved and a bound chosen so tost's two statistics are exactly t_lo and t_hi."""
    m = sum(d) / len(d)
    se = h8.newey_west([v - m for v in d], lag)[1]
    return [v - m + (t_lo + t_hi) / 2 * se for v in d], (t_lo - t_hi) / 2 * se


base = [rng.gauss(0.0, 1.0) for _ in range(41)]
# Lag 0: Newey-West divides by T, so its t is sqrt(T/(T-1)) times Student's t(T-1). At T = 41 the one-sided
# 5% point is therefore t(40)'s 1.68385 * sqrt(41/40) = 1.70477, and the simulated null must say p ~ 0.05.
d0, b0 = at(base, 0, 1.70477, -9.0)
r0 = h8.tost(d0, b0, 0, Q)
check(f"lag 0, T = 41: the fixed-b p at 1.70477 is ~0.05, the exact answer, within 4,000 draws' error "
      f"({r0[2]:.4f}); t(40)'s p beside it is exact ({r0[5]:.4f})",
      abs(r0[2] - 0.05) < 0.012 and abs(r0[5] - 0.04800) < 1e-4 and r0[3] == 0.0)
null8 = sorted(h8.fixed_b_null(41, 8))
q95 = null8[int(0.95 * len(null8))]
# 200,000 draws put this point at ~2.11 (checked 4 Nov 2026); 4,000 seeded draws carry about +/-0.06 here.
check(f"lag 8, T = 41: the fixed-b one-sided 5% point ({q95:.3f}) sits well above t(40)'s 1.684",
      1.95 < q95 < 2.45)
d1, b1 = at(base, 8, 1.9, -1.9)
r1 = h8.tost(d1, b1, 8, Q)
check(f"a gap 1.9 standard errors inside each bound: t(40) would call it equivalent (p {r1[5]:.3f}, "
      f"{r1[6]:.3f}), fixed-b does not ({r1[2]:.3f}, {r1[3]:.3f})",
      r1[5] < 0.05 and r1[6] < 0.05 and r1[2] > 0.05 and r1[3] > 0.05 and r1[4] is False)
q97 = null8[int(0.97 * len(null8))]
d2, b2 = at(base, 8, q97, -9.0)
r2 = h8.tost(d2, b2, 8, Q)
check(f"the lower test is ONE-sided: at the null's 97th percentile p is ~0.03 ({r2[2]:.4f}), not the "
      f"two-sided ~0.06, and the gap is equivalent", 0.02 < r2[2] < 0.04 and r2[4] is True)
d3, b3 = at(base, 8, 9.0, -q97)
r3 = h8.tost(d3, b3, 8, Q)
check(f"...and so is the upper test, in its own direction ({r3[3]:.4f}): the gaps sit near the upper bound",
      0.02 < r3[3] < 0.04 and r3[2] < 1e-3 and r3[4] is True)

print("\n=== H8's draw count, and the tie and threshold rules, on a null fixed by hand ===")
seen = []
_fbn, _nw = h8.fixed_b_null, h8.newey_west
try:
    # mean 0 and standard error 1 exactly, so the two statistics are +bound and -bound
    h8.newey_west = lambda d, lag: (0.0, 1.0, float("nan"), float("nan"))
    h8.fixed_b_null = lambda T, lag, reps=4000: seen.append((T, lag, reps)) or [0.0] * 19 + [1.0]
    tie_lo = h8.tost([0.0] * 20, 1.0, 2)
    past = h8.tost([0.0] * 20, 1.0 + 1e-9, 2)
    h8.fixed_b_null = lambda T, lag, reps=4000: [0.0] * 19 + [-1.0]
    tie_hi = h8.tost([0.0] * 20, 1.0, 2)
finally:
    h8.fixed_b_null, h8.newey_west = _fbn, _nw
check("tost reads H8's own 200,000 draws by default and passes the count to the shared null",
      h8.H8_REPS == 200_000 and seen[:1] == [(20, 2, 200_000)])
check("a draw equal to the statistic counts as 'at or beyond' (p 1 in 20 = 0.05), and 0.05 is not below 0.05: "
      "not equivalent", (tie_lo[2], tie_lo[3], tie_lo[4]) == (0.05, 0.0, False))
check("...the same in the upper test's own direction", (tie_hi[2], tie_hi[3], tie_hi[4]) == (0.0, 0.05, False))
check("a hair past the tie, no draw is at or beyond either statistic: equivalent", (past[2], past[3], past[4])
      == (0.0, 0.0, True))

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
check("at the snapshot minute, identical quotes also give a gap of exactly 0",
      x["S0s"] is not None and abs(x["S0s"] - x["S1s"]) < 1e-12 and x["n_snap"] == x["n_band"])
check("a stale free quote is KEPT at the snapshot minute (the user's view) though dropped by the quote-time match",
      z["n_snap"] == len(rows) and z["n_match"] < len(rows))

print("\n=== the purchase trim keeps exactly what H8 reads ===")
ore = h8.ore
raw = path.read_text()
keep = {ore.compact(r["option_symbol"]) for r in rows[:10]}
tr = ore.h8_trim(raw, keep)
check("the trimmed file keeps Databento's header line", tr.splitlines()[0] == raw.splitlines()[0])
check("it keeps every line of the kept contracts and no other",
      len(tr.splitlines()) - 1 == sum(1 for ln in raw.splitlines()[1:] if ore.compact(ln.rsplit(",", 1)[-1]) in keep))
tmp2 = path.with_name("OPRA_XYZ_trim.csv"); tmp2.write_text(tr)
o2 = ore.load_opra(tmp2)
check("kept contracts read back identically (blank bids still blank -> zero)",
      all(o2[k] == opra[k] for k in keep) and any(rec[1] is None for k in keep for rec in o2[k]))
check("the full-chain funds are not trimmed while H7's window runs, and are after it",
      not ore.h8_trims("2026-10-20", "USO") and ore.h8_trims("2026-11-12", "USO") and ore.h8_trims("2026-10-20", "SPY"))

print(f"\n{len(fails)} failure(s)")
sys.exit(1 if fails else 0)
