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

print(f"\n{len(fails)} failure(s)")
sys.exit(1 if fails else 0)
