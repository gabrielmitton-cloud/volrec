#!/usr/bin/env python3
"""What does hedging with the VENDOR's delta do to H4's numbers?

THE EXPOSURE THIS MEASURES
--------------------------
`hedged.py` shorts `delta` shares against each option, and `delta` is whatever the
free feed recorded. That number is model-derived, and `tools/iv_convention.py` and
`tools/model_gap.py` established that the vendor's model and this project's differ.
So H4's hedge ratios carry a model dependence that nobody has quantified. H3 says
so in as many words and HANDOFF 17 makes quantifying it the second bounded action.

The test is the obvious one: recompute the identical runs with a delta from this
project's own model, and see whether the buckets move.

THIS PROJECT'S DELTA
--------------------
Black-76 on a forward from put-call parity, which is exactly `modelfree.py`'s
convention (HANDOFF 4, and H3's frozen specification), so "our model" means the one
already in the repository rather than a new one invented for this test:

    F     = K* + e^{rT}(C(K*) - P(K*)),  K* the strike where call and put mids agree
    sigma = the Black-76 inversion of this contract's own mid at that F
    dC/dS = (F/S) e^{-rT} N(d1)      for a call,  the put being the N(-d1) mirror

`(F/S) e^{-rT}` is `e^{-qT}`, the carry the forward implies, so the chain rule from
the forward back to the spot `hedged.py` actually trades is carried properly rather
than dropped.

WHY THERE IS MORE THAN ONE FORWARD
----------------------------------
`K*` is the single strike whose call and put agree most closely. That is the right
heuristic when strikes are dense, and a fragile one when they are not: `surface.py`
lays 40 strikes across +/-30% of spot, which on SPY is a step of about 12 dollars,
so `K*` can sit six dollars from the forward and the quote noise in one C-P
difference becomes a forward error worth two delta points. `--forward regress`
instead fits C - P = e^{-rT}(F - K) by least squares across the near-the-money
strikes and reads F off the fit. It is reported as a SENSITIVITY, not as a change
to H3's frozen specification, which stays as it is.

`--forward nodiv` is the third, and it is a diagnostic rather than a candidate:
F = S e^{rT}, the forward of an underlying that pays nothing and costs nothing to
borrow. Run on 16 September 2026 it reproduced the vendor's delta to 0.0007 on
average and 0.0003 at every symbol's median, against 0.0067 for the parity forward.
That identifies the vendor's assumption: its greeks carry no dividend and no borrow.
It is why the whole delta difference sits on SPY, QQQ and IWM, which pay, and
vanishes on GLD, USO and TSLA, which do not - SPY going ex-dividend on 18 September
falls inside both recorded expiries.

THE SAMPLE IS HELD FIXED
------------------------
Only runs that both deltas can price are reported, so the comparison is the delta
and nothing else. The count of runs the model delta could have added, and the
vendor could not, is reported separately and left out of the tables.

USAGE
-----
  FRED_KEY=... python3 tools/delta_model.py
  FRED_KEY=... python3 tools/delta_model.py --forward regress
"""
import argparse
import csv
import math
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import analyze                                              # noqa: E402
import hedged                                               # noqa: E402
import modelfree                                            # noqa: E402
from iv_convention import implied_vol, norm_cdf             # noqa: E402

NEAR_BAND = 0.10        # +/-10% of the forward hint: the strikes a parity fit may use
MIN_FIT = 3             # strikes needed before a least-squares forward means anything


def forwards(rows, r, how):
    """{(date, symbol, expiration): (F, T)} under one of the two conventions."""
    groups = defaultdict(list)
    for row in rows:
        groups[(row["date"], row["symbol"], row["expiration"])].append(row)

    out = {}
    for key, rs in groups.items():
        t = int(rs[0]["dte"]) / 365.0
        if t <= 0:
            continue
        calls, puts = {}, {}
        for row in rs:
            mid, k = hedged._f(row["mid"]), hedged._f(row["strike"])
            if mid is None or mid <= 0 or k is None:
                continue
            (calls if row["type"] == "C" else puts)[k] = mid
        both = sorted(set(calls) & set(puts))
        if len(both) < MIN_FIT:
            continue
        disc = math.exp(r * t)

        if how == "nodiv":
            # No dividend, no borrow: the forward the vendor's greeks imply.
            out[key] = (hedged._f(rs[0]["spot"]) * disc, t)
            continue

        # modelfree.py's convention, verbatim: the single best-agreeing strike.
        k_star = min(both, key=lambda k: abs(calls[k] - puts[k]))
        f_parity = k_star + disc * (calls[k_star] - puts[k_star])

        if how == "parity":
            out[key] = (f_parity, t)
            continue

        # C - P = e^{-rT}(F - K) is a straight line in K with slope -e^{-rT}.
        # Fitting it uses every near-the-money strike instead of betting on one.
        pts = [(k, calls[k] - puts[k]) for k in both
               if abs(k - f_parity) / f_parity <= NEAR_BAND]
        if len(pts) < MIN_FIT:
            out[key] = (f_parity, t)
            continue
        n = len(pts)
        mx = sum(k for k, _ in pts) / n
        my = sum(y for _, y in pts) / n
        sxx = sum((k - mx) ** 2 for k, _ in pts)
        sxy = sum((k - mx) * (y - my) for k, y in pts)
        if sxx <= 0 or sxy >= 0:
            out[key] = (f_parity, t)
            continue
        slope = sxy / sxx                       # should land near -e^{-rT}
        out[key] = (mx - my / slope, t)         # the K where the fitted C - P is zero
    return out


def delta_fn(fwd, r):
    """row -> this project's own spot delta, or None when it cannot be computed."""
    def of(row):
        key = (row["date"], row["symbol"], row["expiration"])
        if key not in fwd:
            return None
        f, t = fwd[key]
        s, k, mid = (hedged._f(row["spot"]), hedged._f(row["strike"]),
                     hedged._f(row["mid"]))
        if None in (s, k, mid) or min(s, k, mid) <= 0 or f <= 0:
            return None
        iv = implied_vol(row["type"], mid, f, k, t, r)
        if iv is None:
            return None
        v = iv * math.sqrt(t)
        d1 = (math.log(f / k) + v * v / 2) / v
        carry = (f / s) * math.exp(-r * t)                  # = e^{-qT}
        return carry * norm_cdf(d1) if row["type"] == "C" else -carry * norm_cdf(-d1)
    return of


def run_all(rows, r, delta_of):
    """hedged.py's own pipeline, keyed so two passes can be matched run for run."""
    by_contract = defaultdict(list)
    for row in rows:
        by_contract[row["option_symbol"]].append(row)
    out = {}
    for osym, obs in by_contract.items():
        obs.sort(key=lambda x: x["date"])
        for run in hedged.runs_for_contract(obs):
            g = hedged.hedged_gain(run, r, delta_of=delta_of)
            if g:
                out[(osym, g["start"], g["end"])] = g
    return out


def stat(v):
    x = [q["scaled"] * 10000 for q in v]
    mu, _, t, _ = analyze.plain_t(x) if len(x) > 1 else (x[0], 0, 0, 1)
    return mu, t, 100.0 * sum(1 for q in x if q < 0) / len(x)


def side_by_side(title, groups, a, b):
    print(f"\n-- {title}")
    print(f"   {'group':<16}{'n':>5}{'vendor':>11}{'ours':>11}{'shift':>9}"
          f"{'t vendor':>10}{'t ours':>9}{'%neg v':>8}{'%neg o':>8}")
    for name in groups:
        ka, kb = a.get(name), b.get(name)
        if not ka:
            continue
        ma, ta, na = stat(ka)
        mb, tb, nb = stat(kb)
        print(f"   {name:<16}{len(ka):>5}{ma:>9.2f}bp{mb:>9.2f}bp{mb-ma:>+8.2f}bp"
              f"{ta:>10.2f}{tb:>9.2f}{na:>7.0f}%{nb:>7.0f}%")


def terciles(results):
    """hedged.py's tercile rule, verbatim, so the cut points cannot drift."""
    vols = sorted(r["volume"] for r in results)
    lo, hi = vols[len(vols) // 3], vols[2 * len(vols) // 3]
    out = defaultdict(list)
    for r in results:
        out["low volume" if r["volume"] <= lo
            else "high volume" if r["volume"] > hi else "mid volume"].append(r)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--forward", choices=("parity", "regress", "nodiv"),
                    default="parity",
                    help="parity = modelfree.py's convention (default); "
                         "regress = least squares across near-the-money strikes; "
                         "nodiv = S*exp(rT), the diagnostic for the vendor's own "
                         "assumption")
    a = ap.parse_args()

    surf = ROOT / "data" / "surface.csv"
    if not surf.exists():
        sys.exit("No data/surface.csv yet.")
    rows = list(csv.DictReader(surf.open(newline="")))
    if not rows:
        sys.exit("surface.csv is empty.")

    r = modelfree.risk_free()
    print(f"risk-free (DGS1MO): {r*100:.3f}%   forward: {a.forward}\n")

    fwd = forwards(rows, r, a.forward)
    ours_of = delta_fn(fwd, r)

    vendor = run_all(rows, r, None)
    ours = run_all(rows, r, ours_of)
    keys = sorted(set(vendor) & set(ours))
    print(f"runs: {len(vendor)} on the vendor delta, {len(ours)} on ours, "
          f"{len(keys)} in common")
    print(f"   {len(set(ours) - set(vendor))} run(s) our model could price and the "
          f"vendor could not are EXCLUDED, so only the delta differs.\n")

    va = [vendor[k] for k in keys]
    ob = [ours[k] for k in keys]

    # How far apart are the two deltas, before asking what they do?
    diffs = defaultdict(list)
    for k in keys:
        row = next(x for x in rows
                   if x["option_symbol"] == k[0] and x["date"] == k[1])
        d0, d1 = hedged._f(row["delta"]), ours_of(row)
        if None not in (d0, d1):
            diffs[row["symbol"]].append(d1 - d0)
    print("-- the deltas themselves, ours minus the vendor's, at each run's start")
    print(f"   {'symbol':<10}{'n':>5}{'median':>10}{'mean':>10}{'p10':>10}{'p90':>10}")
    allv = []
    for s in sorted(diffs) + ["ALL"]:
        v = sorted(diffs[s]) if s != "ALL" else sorted(allv)
        if s != "ALL":
            allv += diffs[s]
        if not v:
            continue
        n = len(v)
        print(f"   {s:<10}{n:>5}{v[n//2]:>+10.4f}{sum(v)/n:>+10.4f}"
              f"{v[int(.1*n)]:>+10.4f}{v[int(.9*n)]:>+10.4f}")

    ba = defaultdict(list)
    bb = defaultdict(list)
    for x, y in zip(va, ob):
        if x["moneyness"] is not None:
            ba[hedged.bucket_of(x["moneyness"])].append(x)
            bb[hedged.bucket_of(y["moneyness"])].append(y)
    side_by_side("delta-hedged gain by moneyness bucket",
                 [n for n, _, _ in hedged.MONEYNESS_BUCKETS], ba, bb)

    side_by_side("by volume tercile (cut points from the vendor pass, held fixed)",
                 ["low volume", "mid volume", "high volume"],
                 terciles(va), {k: [ours[(q["option_symbol"], q["start"], q["end"])]
                                    for q in v]
                                for k, v in terciles(va).items()})

    print("\n-- pooled")
    for name, v in (("vendor delta", va), ("our delta", ob)):
        x = [q["scaled"] * 10000 for q in v]
        mu, _, t, p = analyze.plain_t(x)
        print(f"   {name:<14}n={len(x)}  mean {mu:+.2f}bp of spot  t={t:.2f}  p={p:.4f}")

    print("\n   The caution on hedged.py applies unchanged: these runs overlap in")
    print("   calendar time and share underlyings, so every t above is descriptive.")
    print("   No threshold or bucket definition is touched by this file.")


if __name__ == "__main__":
    main()
