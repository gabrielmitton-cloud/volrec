"""Known-answer tests for tools/describe.py (descriptive statistics beside the verdicts).
Synthetic series only - the real H5e/H7 series are read once, after the verdicts.

  python tools/test_describe.py
"""
import math
import random
import sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(R), str(R / "tools")]
import describe as D   # noqa: E402

fails = []


def check(name, cond):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}")
    if not cond:
        fails.append(name)


print("=== pieces, by hand ===")
check("lag rule: floor(1.3 sqrt(T)) -> T=36 gives 7, T=10 gives 4, never below 1",
      D.lag_rule(36) == 7 and D.lag_rule(10) == 4 and D.lag_rule(2) == 1)
check("quantile picks the ceil(qn)-th smallest", D.quantile(list(range(1, 101)), 0.95) == 95)
check("Holm by hand: p = 0.01, 0.04, 0.03 -> 0.03, 0.06, 0.06 (step-down, kept monotone)",
      all(abs(a - b) < 1e-12 for a, b in zip(D.holm([0.01, 0.04, 0.03]), [0.03, 0.06, 0.06])))
check("Holm caps at 1 and passes None through",
      D.holm([0.6, None, 0.9]) == [1.0, None, 1.0])
check("Holm with one test leaves p unchanged", D.holm([0.2]) == [0.2])
check("Holm: a NaN p is not a test - it passes through as None and does not disturb the others",
      D.holm([0.01, float("nan"), 0.04]) == [0.02, None, 0.04])
import analyze as _A  # noqa: E402
check("the descriptive null is the registered readers' own (analyze.fixed_b_null), sorted",
      D.fixed_b_null(15, 3, reps=300) == sorted(_A.fixed_b_null(15, 3, 300, D.SEED)))

print("\n=== the fixed-b critical value is the house method's ===")
null0 = D.fixed_b_null(250, 0, reps=4000)
c0 = D.quantile(sorted(abs(v) for v in null0), 0.95)
check(f"lag 0, T=250 -> about 1.97, t(249)'s value (got {c0:.2f})", abs(c0 - 1.97) < 0.08)
nullb = D.fixed_b_null(40, 8, reps=4000)
cb = D.quantile(sorted(abs(v) for v in nullb), 0.95)
check(f"b = 0.2 (T=40, lag 8) -> wider than t's 2.02 (got {cb:.2f})", cb > 2.2)
check("seeded: the same null twice", D.fixed_b_null(20, 3, reps=200) == D.fixed_b_null(20, 3, reps=200))

print("\n=== describe() on series with known truth ===")
rng = random.Random(1)
iid = [0.3 + rng.gauss(0, 0.1) for _ in range(40)]
d = D.describe(iid, 0.5, "below", reps=2000)
check("iid around 0.3: interval contains 0.3 and excludes the 0.5 bar", d["lo"] < 0.3 < d["hi"] and d["hi"] < 0.5)
check("iid: n_eff close to T (rho near 0)", d["n_eff"] > 25)
check("iid mean 0.3 vs bar 0.5, claim 'below': one-sided p tiny", d["p_bar"] < 0.01)
x = 0.0
ar = []
for _ in range(40):
    x = 0.9 * x + rng.gauss(0, 0.1)
    ar.append(0.45 + x)
da = D.describe(ar, 0.5, "below", reps=2000)
check(f"AR(1) rho 0.9: n_eff small, as PROTOCOL warns (T=40, rho {da['rho']:.2f} -> n_eff {da['n_eff']:.1f})",
      da["n_eff"] < 10)
check("AR(1): the interval is wider than the iid one at the same T", (da["hi"] - da["lo"]) > (d["hi"] - d["lo"]))
check("constant series above the bar: claim 'below' gets p near 1",
      D.describe([0.7 + 1e-6 * i for i in range(20)], 0.5, "below", reps=500)["p_bar"] > 0.95)
check("side 'above' mirrors 'below'", abs(D.describe(iid, 0.5, "above", reps=2000)["p_bar"] - (1 - d["p_bar"])) < 1e-9)
check("two-sided descriptive (no bar) has no p", "p_bar" not in D.describe(iid, None, None, reps=200))
check("fewer than 3 days: no interval, said plainly", D.describe([1.0, 2.0])["enough"] is False)

print("\n=== adapters read the registered readers' own printed rows ===")
mf = """-- H5e: USO, wide strikes, zero bids SKIPPED, against OVX (registered 23 Sep; judged from 2026-09-23)
   date            OVX  registered     gap  wide skip     gap  counted
   2026-09-22    51.89       50.89   -1.00      51.89   -0.00  no - in-sample, before registration
   2026-09-23    53.24       53.40   +0.16      54.55   +1.31  yes
   2026-09-24    54.45       53.47   -0.98      55.76   +1.31  yes
   2026-09-28   dropped - recorded after the close (23 Sep rule, applied 30 Sep)
   2026-09-29    53.74       52.92   -0.82      54.01   +0.27  yes
   mean |gap| 0.96 against 0.5 (OVER); closer than registered on 1 of 3 days (NOT a majority)
"""
days, gaps, closer = D.h5e_series(mf)
check("H5e: only counted days from 23 Sep (the in-sample 22 Sep and the dropped day excluded)",
      days == ["2026-09-23", "2026-09-24", "2026-09-29"])
check("H5e: |gap| of the wide-skip estimate", gaps == [1.31, 1.31, 0.27])
check("H5e: closer = |skip gap| < |registered gap| -> 0, 0, 1", closer == [0.0, 0.0, 1.0])
check("H5e: the series' mean equals the tally modelfree prints (0.96)", abs(sum(gaps) / 3 - 0.963) < 0.01)
h7 = """date       sym      free    OPRA   close  free-OPRA free-close  legs
2026-10-09 USO     48.90   48.75   48.90      +0.15      +0.00  [7, 42]
2026-10-09 GLD     21.10   21.00   21.30      +0.10      -0.20  [7, 42]
2026-10-12 USO     48.10     n/a   48.52        n/a      -0.42  [4, 39]
2026-10-12 GLD     21.40   21.30     n/a      +0.10        n/a  [4, 39]
"""
s = D.h7_series(h7)
check("H7: USO_a takes |free-OPRA| and skips n/a", s["USO_a"] == [0.15])
check("H7: GLD_b is |free - GVZ| (absolute)", s["GLD_b"] == [0.2])
check("H7: USO_c keeps the sign (descriptive bias)", s["USO_c"] == [0.0])
check("H7 (review M04, 28 Oct): a day lacking OPRA or the close counts in NO series, as in h7_reader.summarise",
      s["USO_c"] == [0.0] and s["GLD_a"] == [0.1] and len(s["GLD_b"]) == 1)
check("H7: GLD_a", s["GLD_a"] == [0.1])

print("\n=== discipline ===")
src = (R / "tools" / "describe.py").read_text()
check("every printed result carries the 'added after registration, descriptive' label", "LABEL" in src and "added after registration, descriptive" in src)
check("the tool never writes a file (it only reads the readers' output)", "write_text" not in src and "open(" not in src)
check("bars come from the registered constants, not typed in", "rv.H5E_BAR" in src and "rv.H7_BAR_A" in src and "rv.H7_BAR_B" in src)

print(f"\n{len(fails)} failure(s)")
sys.exit(1 if fails else 0)
