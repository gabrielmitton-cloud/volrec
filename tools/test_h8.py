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


def rows_and_opra(shift_mid=0.0, blank_far_bids=True, side="CP"):
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
                ob, oa = (b + shift_mid, a + shift_mid) if k in side else (b, a)   # `side`: which OPRA quotes move
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
check("the reading carries the snapshot minute it priced at (tools/h8_index.py reads the index there)",
      x["T"] == h8.ore.snapshot_minute(rows) and x["T"] is not None)
check("at the snapshot minute, identical quotes also give a gap of exactly 0",
      x["S0s"] is not None and abs(x["S0s"] - x["S1s"]) < 1e-12 and x["n_snap"] == x["n_band"])
check("a stale free quote is KEPT at the snapshot minute (the user's view) though dropped by the quote-time match",
      z["n_snap"] == len(rows) and z["n_match"] < len(rows))

print("\n=== item 7: the snapshot gap split by side (descriptive; H8-DRAFT, 5 Nov 2026) ===")
check("identical quotes on both feeds give both mixed estimates equal to S0s and S1s",
      all(abs(x[k] - x["S0s"]) < 1e-12 for k in ("MPs", "MCs", "S1s")))
yp = h8.day_pair(*rows_and_opra(shift_mid=0.02, side="P")[:2], 0.0)
gp = yp["S0s"] - yp["S1s"]
check(f"OPRA's PUTS 2 cents higher, calls the same: the gap ({gp:+.4f}) is all put part in both orders "
      f"(puts first {yp['S0s'] - yp['MPs']:+.4f}, calls first {yp['MCs'] - yp['S1s']:+.4f}), call part 0",
      gp < 0 and abs((yp["S0s"] - yp["MPs"]) - gp) < 1e-12 and abs((yp["MCs"] - yp["S1s"]) - gp) < 1e-12
      and abs(yp["MPs"] - yp["S1s"]) < 1e-12 and abs(yp["S0s"] - yp["MCs"]) < 1e-12)
yc = h8.day_pair(*rows_and_opra(shift_mid=0.02, side="C")[:2], 0.0)
gc = yc["S0s"] - yc["S1s"]
check(f"OPRA's CALLS 2 cents higher, puts the same: the gap ({gc:+.4f}) is all call part in both orders, put part 0",
      gc < 0 and abs((yc["S0s"] - yc["MCs"]) - gc) < 1e-12 and abs((yc["MPs"] - yc["S1s"]) - gc) < 1e-12
      and abs(yc["MCs"] - yc["S1s"]) < 1e-12 and abs(yc["S0s"] - yc["MPs"]) < 1e-12)
check(f"both sides 2 cents higher: each order's two parts add up to the gap ({y['S0s'] - y['S1s']:+.4f}), and "
      "both sides carry some of it", all(abs((y["S0s"] - m) + (m - y["S1s"]) - (y["S0s"] - y["S1s"])) < 1e-12
                                         for m in (y["MPs"], y["MCs"]))
      and y["S0s"] - y["MPs"] < 0 and y["MPs"] - y["S1s"] < 0)
fake = [{"S0s": 20.0, "S1s": 19.0, "MPs": 19.75, "MCs": 19.125},     # gap  1.0: puts first .25/.75, calls first .875/.125
        {"S0s": 18.0, "S1s": 18.5, "MPs": 18.375, "MCs": 17.75},     # gap -0.5: -.375/-.125, .25/-.75
        {"S0s": 21.0, "S1s": 20.0, "MPs": 20.0, "MCs": 21.0},        # gap  1.0: 1/0, 0/1
        {"S0s": 20.0, "S1s": None, "MPs": 19.0, "MCs": 19.0},        # left out: an estimate missing
        {"S0s": float("nan"), "S1s": 19.0, "MPs": 19.0, "MCs": 19.0},  # left out: not finite
        {"S0s": 20.0, "S1s": 19.0, "MPs": float("inf"), "MCs": 19.0},
        {"S0s": 20.0, "S1s": 19.0, "MPs": 19.5}]                      # left out: no MCs at all
sd7 = h8.sides(fake)
want = {"gap": (1.5 / 3, 2.5 / 3), ("puts_first", "put"): (0.875 / 3, 1.625 / 3),
        ("puts_first", "call"): (0.625 / 3, 0.875 / 3), ("calls_first", "call"): (1.125 / 3, 1.125 / 3),
        ("calls_first", "put"): (0.375 / 3, 1.875 / 3)}
got7 = {k: (sd7[k] if k == "gap" else sd7[k[0]][k[1]]) for k in want}
check("the split's means and mean absolutes match hand-computed answers, on the 3 of 7 days with all four "
      "estimates finite", sd7["n"] == 3 and all(abs(a - b) < 1e-12 for k in want for a, b in zip(got7[k], want[k])))
import contextlib, io
days7 = [dict(f, n_match=10, n_band=10, S0m=f["S0s"], S1=f["S1s"], S1n=1.0, S1b=1.0) for f in fake[:3]]
with contextlib.redirect_stdout(io.StringIO()) as out7:
    h8.summarise("XYZ", days7, 1)
line7 = [ln for ln in out7.getvalue().splitlines() if "by side" in ln]
check("the report prints the split beside the gap, both orders, labelled descriptive",
      len(line7) == 1 and "item 7, descriptive" in line7[0] and "puts first - put +0.292 (|.| 0.542), call +0.208 "
      "(|.| 0.292); calls first - call +0.375 (|.| 0.375), put +0.125 (|.| 0.625); gap +0.500  (3 days)" in line7[0])


def report_of(days):
    with contextlib.redirect_stdout(io.StringIO()) as o:
        h8.summarise("XYZ", days, 1)
    return o.getvalue()


sparse = [dict(d, n_match=0, S0m=None, S1=None, S1n=None, S1b=None) for d in days7]   # no quote-time pair at all
r7 = report_of(sparse)
check("the split is reported on its own sample even when the fund has too few quote-time pairs (Astra, 5 Nov)",
      "too few to summarise" in r7 and "call +0.375 (|.| 0.375), put +0.125 (|.| 0.625); gap +0.500  (3 days)" in r7)
check("...with no minimum of its own: one eligible fund-day is reported, as one day",
      "puts first - put +0.250 (|.| 0.250), call +0.750 (|.| 0.750); calls first - call +0.875 (|.| 0.875), "
      "put +0.125 (|.| 0.125); gap +1.000  (1 days)" in report_of(sparse[:1] + [dict(sparse[0], MCs=None)]))
check("...and a fund with no eligible fund-day says so instead of printing numbers",
      "by side (item 7, descriptive): no fund-day with all four estimates finite" in report_of([dict(sparse[0], MPs=None)]))


def rows_and_opra_snap(put_snap, call_snap):
    """Item 7's harder fixture (Astra, 5 Nov). Free quotes stamped 18:42:40, so the quote-time match takes OPRA's
    18:43 record and the snapshot minute (18:42, the median quote time) its own. Only OPRA's 18:42 quotes move,
    by side. Every 4th free quote is stale (15:02: matched only at the snapshot minute). The 125-strike contracts
    are quoted by OPRA only at 18:44:30 - inside 120 s of their quote time, outside 120 s of the snapshot
    minute - so they are in the quote-time set and not the snapshot set."""
    rows, lines = [], ["ts_recv,ts_event,rtype,publisher_id,instrument_id,side,price,size,flags,"
                       "bid_px_00,ask_px_00,bid_sz_00,ask_sz_00,bid_pb_00,ask_pb_00,symbol"]
    snapq = {}
    for e, dte in ((E1, 14), (E2, 42)):
        for K in range(70, 131, 5):
            for k in "CP":
                p = black76(k, S, float(K), dte / 365.0, 0.0, SIG)
                b, a = (round(p * 0.98, 4), round(p * 1.02, 4)) if p > 0.05 else (0.0, 0.05)
                osi = f"XYZ{e:%y%m%d}{k}{K * 1000:08d}"
                qt = f"{D}T15:02:00Z" if len(rows) % 4 == 0 else f"{D}T18:42:40Z"
                rows.append({"date": D, "symbol": "XYZ", "spot": str(S), "quote_time": qt, "expiration": e.isoformat(),
                             "dte": str(dte), "type": k, "strike": str(float(K)), "option_symbol": osi,
                             "bid": str(b), "ask": str(a), "mid": str((b + a) / 2)})
                occ = f"XYZ   {e:%y%m%d}{k}{K * 1000:08d}"
                sh = put_snap if k == "P" else call_snap
                at_min = {mm: (b + (sh if mm == "42" else 0.0), a + (sh if mm == "42" else 0.0))
                          for mm in ("41", "42", "43", "44")} if K != 125 else {"44:30": (b, a)}
                for mm, (ob, oa) in at_min.items():
                    stamp = f"18:{mm}.000000000Z" if ":" in mm else f"18:{mm}:00.000000000Z"
                    lines.append(f"{D}T{stamp},,193,30,1,N,,0,0,{'' if b == 0 else f'{ob:.4f}'},{oa:.4f},1,1,1,1,{occ}")
                if K != 125:                       # OPRA's snapshot-minute quote, as the file will read back
                    ob, oa = at_min["42"]
                    bb = 0.0 if b == 0 else float(f"{ob:.4f}")
                    snapq[osi] = dict(rows[-1], bid=str(bb), ask=str(float(f"{oa:.4f}")),
                                      mid=str((bb + float(f"{oa:.4f}")) / 2.0))
    tmp = Path(tempfile.mkdtemp()) / f"OPRA_XYZ_{D}.csv"
    tmp.write_text("\n".join(lines) + "\n")
    return rows, h8.ore.load_opra(tmp), snapq


rs, os_, snapq = rows_and_opra_snap(0.02, 0.03)
xs = h8.day_pair(rs, os_, 0.0)
v7 = lambda rows: h8.modelfree.model_free_30d(rows, 0.0)[0]
in_s = [r for r in rs if r["option_symbol"] in snapq]           # the snapshot set, assembled by hand
check(f"the harder fixture's sets are as built: the quote-time set skips the stale quotes ({xs['n_match']}), the "
      f"snapshot set skips the 125-strike contracts and keeps the stale ones ({xs['n_snap']})",
      xs["T"].minute == 42 and xs["n_match"] == sum(r["quote_time"].endswith("18:42:40Z") for r in rs)
      and xs["n_snap"] == len(in_s) == len(rs) - 4)
check("both mixes equal the estimator on inputs assembled by hand: the snapshot set, OPRA's 18:42 quote on the "
      "one side, the free quote on the other (so not the quote-time set, nor OPRA's 18:43 quotes)",
      abs(xs["MPs"] - v7([snapq[r["option_symbol"]] if r["type"] != "C" else r for r in in_s])) < 1e-12
      and abs(xs["MCs"] - v7([snapq[r["option_symbol"]] if r["type"] == "C" else r for r in in_s])) < 1e-12
      and abs(xs["S1s"] - v7([snapq[r["option_symbol"]] for r in in_s])) < 1e-12 and abs(xs["S0s"] - v7(in_s)) < 1e-12)
pf7, cf7 = xs["S0s"] - xs["MPs"], xs["MCs"] - xs["S1s"]
check(f"with both sides moved, the order matters (put part {pf7:+.4f} puts first, {cf7:+.4f} calls first) and each "
      "order still adds up to the gap", abs(pf7 - cf7) > 1e-6
      and all(abs((xs["S0s"] - m) + (m - xs["S1s"]) - (xs["S0s"] - xs["S1s"])) < 1e-12 for m in (xs["MPs"], xs["MCs"])))

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
