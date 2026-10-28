"""Known-answer tests for the frozen H3 scorer (tools/h3_scorer.py). Synthetic readings only.

  python tools/test_h3_scorer.py
"""
import math
import random
import sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(R), str(R / "tools")]
import h3_scorer as H   # noqa: E402

fails = []


def check(name, cond):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}")
    if not cond:
        fails.append(name)


print("=== parsing modelfree's REGISTERED rows ===")
out = """risk-free (DGS1MO): 3.910%

date        sym       ours    cboe     gap      legs    n
----------------------------------------------------------
2026-09-14  GLD      21.50   21.40   +0.10     16/23   80
2026-09-14  USO      40.00   42.00   -2.00     16/23   80
2026-09-14  TSLA     55.00     n/a              16/23   80
2026-09-15  SPY      15.00   15.20   -0.20     16/23   80
2026-09-15  QQQ      -             too thin
2026-09-28  dropped - recorded after the close (23 Sep rule, applied 30 Sep)
2026-11-12  IWM      20.00   21.00   -1.00     16/23   80
"""
rows = H.parse(out)
check("only the five benchmarked underlyings with a Cboe close, to 11 Nov (TSLA, n/a, too thin, dropped, 12 Nov out)",
      rows == [("2026-09-14", "GLD", 21.40, 0.10), ("2026-09-14", "USO", 42.00, -2.00), ("2026-09-15", "SPY", 15.20, -0.20)])
try:
    H.parse(out + "\n-- gap of the WIDE SENSITIVITY against Cboe - NOT H3a's registered gap\n")
    check("--wide output is refused (H3 is scored on the registered estimate)", False)
except SystemExit:
    check("--wide output is refused (H3 is scored on the registered estimate)", True)

print("\n=== the registered statistics, by hand ===")
sc = H.score(rows)
check("H3a pooled mean |gap| = (0.10 + 2.00 + 0.20) / 3 = 0.7667 -> HOLDS (under 1.0)",
      abs(sc["h3a_mean_abs"] - 2.30 / 3) < 1e-12 and sc["h3a"] == "HOLDS")
check("H3b pooled mean gap = (0.10 - 2.00 - 0.20) / 3 = -0.70 -> HOLDS (negative)",
      abs(sc["h3b_mean"] + 0.70) < 1e-12 and sc["h3b"] == "HOLDS")
check("H3a FAILS at exactly 1.0 ('under 1.0' is strict)",
      H.score([("2026-09-14", "GLD", 20.0, 1.0), ("2026-09-15", "GLD", 21.0, -1.0)])["h3a"] == "FAILS")
b, a0, e = H.ols([1, 2, 3, 4], [2, 4, 6, 8])
check("OLS on y = 2x: slope 2, intercept 0, zero residuals", abs(b - 2) < 1e-12 and abs(a0) < 1e-12 and max(map(abs, e)) < 1e-12)

print("\n=== the wild cluster bootstrap (Webb, enumerated) ===")
rng = random.Random(3)
rows_pos, rows_null = [], []
for k, sym in enumerate(H.BENCH):
    for d in range(30):
        lvl = 15 + 8 * k + rng.gauss(0, 2)
        rows_pos.append((f"2026-10-{d+1:02d}", sym, lvl, 0.05 * lvl + rng.gauss(0, 0.2)))
        rows_null.append((f"2026-10-{d+1:02d}", sym, lvl, 0.8 + rng.gauss(0, 0.2)))
sp, sn = H.score(rows_pos), H.score(rows_null)
check(f"a true slope of +0.05 per point is found: positive, p < 0.05 (p {sp['h3c_p']:.4f})",
      sp["h3c_slope"] > 0 and sp["h3c_p"] < 0.05 and sp["h3c"] == "HOLDS")
check(f"no relation: not significant (p {sn['h3c_p']:.3f})", sn["h3c_p"] > 0.05 and sn["h3c"] == "FAILS")
rows_neg = [(d, sym, lvl, max(0.0, 3.0 - 0.05 * lvl)) for d, sym, lvl, _g in rows_pos]
sneg = H.score(rows_neg)
check(f"one-sided: a clearly NEGATIVE slope gets p near 1, never a small p (p {sneg['h3c_p']:.4f})",
      sneg["h3c_slope"] < 0 and sneg["h3c_p"] > 0.95 and sneg["h3c"] == "FAILS")
check("every one of the 6^5 = 7,776 Webb weight vectors is enumerated (exact, no seed)", sp["h3c_draws"] == 7776)
check("deterministic: the same readings give the same p twice", H.score(rows_pos)["h3c_p"] == sp["h3c_p"])
check("Webb's six points: +/-sqrt(1.5), +/-1, +/-sqrt(0.5), mean 0, variance 1",
      abs(sum(H.WEBB)) < 1e-12 and abs(sum(w * w for w in H.WEBB) / 6 - 1) < 1e-12)

print("\n=== per-underlying tests and Benjamini-Hochberg ===")
check("every underlying gets a Newey-West p for H3a and H3c", all(sp["per"][s] and sp["per"][s]["p_h3a"] is not None
                                                                   for s in H.BENCH))
check("BH counts are integers within 0..5", 0 <= sp["bh_h3a_k"] <= 5 and 0 <= sp["bh_h3c_k"] <= 5)
small = [(f"2026-10-0{d}", "GLD", 20.0 + d, 0.3) for d in range(1, 3)]
check("an underlying with fewer than 3 readings is reported as such, not tested", H.score(small)["per"]["GLD"] is None)
check("the scorer's labels say it was specified before the reading of record", "before the reading of record" in H.LABEL)

print("\n=== guards added 28 Oct 2026 (outside review R1, R3, R4) ===")
_prec = """--precise: per-day estimates and gaps printed to 6 decimals.

risk-free (DGS1MO): 3.910%
2026-10-27  GLD       22.091578   22.58    -0.488422   24d/31d  176
2026-10-27  IWM       21.446475   20.84    +0.606475   24d/31d  152
"""
check("R3: modelfree --precise rows parse at full precision (6 decimals)",
      H.parse(_prec) == [("2026-10-27", "GLD", 22.58, -0.488422), ("2026-10-27", "IWM", 20.84, 0.606475)])
# R4 through score() itself (Astra, 28 Oct): one testable pair whose per-underlying p is exactly 0.02675 and four
# untestable ones. Scored against a family of five it must NOT be rejected; a family of one would reject it.
_orig_describe = H.describe
H.describe = lambda xs, bar, side: {"mean": sum(xs) / len(xs), "p_bar": 0.02675}
try:
    _sb = H.score([(f"2026-10-{d:02d}", "GLD", 20.0 + d, 0.5 + 0.01 * (d % 3)) for d in range(1, 13)]
                  + [(f"2026-10-0{d}", s_, 20.0, 0.3) for s_ in ("IWM", "QQQ", "SPY", "USO") for d in (1, 2)])
finally:
    H.describe = _orig_describe
check("R4: score() keeps the family of five - GLD at p 0.02675 is not rejected (adjusted 0.134), count 0 of 5",
      _sb["per"]["GLD"]["p_h3a_bh"] is False and _sb["bh_h3a_k"] == 0)
# R1: an exact fit has zero residuals, so the cluster standard error is 0 and t is undefined. It once compared as
# p = 0 and read HOLDS. Now: UNSCORED, never a verdict.
exact = [(f"2026-10-{d:02d}", sym, lvl + d, (lvl + d) / 16.0) for sym, lvl in zip(H.BENCH, (25, 20, 21, 16, 58))
         for d in range(1, 4)]
se = H.score(exact)
check(f"R1: an exact fit (undefined t) is UNSCORED, not HOLDS (t {se['h3c_t']}, p {se['h3c_p']})",
      se["h3c"] == H.UNSCORED and not math.isfinite(se["h3c_t"]))
const_x = [(f"2026-10-{d:02d}", sym, 20.0, 0.1 * d) for sym in H.BENCH for d in range(1, 4)]
check("R1: a constant index level (undefined slope) is UNSCORED", H.score(const_x)["h3c"] == H.UNSCORED)
# R3: a printed gap is within 0.005 of the true one. True |gap| 0.996 prints as 1.00: the printed mean 1.0 must not
# read FAILS (the truth is under the bar) nor HOLDS (the print cannot show it) - UNRESOLVED.
near = [(f"2026-10-{d:02d}", sym, 20.0 + d, -1.00) for sym in H.BENCH for d in range(1, 4)]
check("R3: a printed mean of exactly 1.00 is UNRESOLVED at display precision",
      H.score(near, half_ulp=0.005)["h3a"] == H.UNRESOLVED)
check("R3: the same rows read as exact values still FAIL at 1.0 (strict bar unchanged)",
      H.score(near)["h3a"] == "FAILS")
check("R3: far from the bar, display rounding cannot matter (0.52 HOLDS, 1.10 FAILS)",
      H.score([(d, s, c, 0.52) for d, s, c, _ in near], half_ulp=0.005)["h3a"] == "HOLDS"
      and H.score([(d, s, c, 1.10) for d, s, c, _ in near], half_ulp=0.005)["h3a"] == "FAILS")
check("R3: a printed mean gap of -0.00 (H3b) is UNRESOLVED, -0.30 HOLDS",
      H.score([(d, s, c, 0.0) for d, s, c, _ in near], half_ulp=0.005)["h3b"] == H.UNRESOLVED
      and H.score([(d, s, c, -0.30) for d, s, c, _ in near], half_ulp=0.005)["h3b"] == "HOLDS")
check("R3: the real-sized positive slope still HOLDS with the rounding slack", H.score(rows_pos, half_ulp=0.005)["h3c"] == "HOLDS")
# R4: the registered BH family is five. One testable pair with p = 0.02675 and four untestable ones: a family of one
# would reject it; the family of five (adjusted 0.134) must not.
fam_rows = [(f"2026-10-{d:02d}", "GLD", 20.0 + d, g) for d, g in zip(range(1, 41), [0.5 + 0.01 * (k % 7) for k in range(40)])]
fam_rows += [(f"2026-10-0{d}", s, 20.0, 0.3) for s in ("IWM", "QQQ", "SPY", "USO") for d in (1, 2)]
sf = H.score(fam_rows)
fam = H.bh_family(sf["per"], "p_h3a")
check("R4: untestable pairs stay in the family of five at p = 1 (never rejected)",
      sf["n_syms"] == 1 and sf["per"]["IWM"] is None and sorted(fam) == sorted(H.BENCH)
      and all(fam[s] == 1.0 for s in ("IWM", "QQQ", "SPY", "USO")))
import analyze as _an   # noqa: E402
_rej, _adj = _an.benjamini_hochberg({"GLD": 0.02675, "IWM": 1.0, "QQQ": 1.0, "SPY": 1.0, "USO": 1.0}, 0.05)
check(f"R4: BH over five with one p = 0.02675 adjusts it to {_adj['GLD']:.5f} and does not reject",
      abs(_adj["GLD"] - 0.13375) < 1e-9 and "GLD" not in _rej)

print(f"\n{len(fails)} failure(s)")
sys.exit(1 if fails else 0)
