"""Model-free variance from a recorded strike surface, and the gap against Cboe.

WHAT THIS IS FOR
----------------
`data/iv_history.csv` records at-the-money implied volatility. Cboe's published
indices (VIX, VXN, RVX, GVZ, OVX) are model-free: they integrate the whole strike
surface rather than reading one point on it. Measured on 4 Sep 2026 across four
matched pairs, the ATM reading sat 3.61 volatility points BELOW the Cboe index,
same sign every time.

That gap has at least four components tangled together:

  1. at-the-money versus the whole surface (the skew premium)
  2. a free indicative feed versus consolidated OPRA quotes
  3. limited strike coverage (+/-10%) versus Cboe's full tail
  4. a maturity mismatch, if one side is not at a constant 30 days

`surface.py` now records enough of the surface, at two expiries, to build the
model-free number directly. Comparing it against Cboe for the same underlying on
the same day turns that 3.61-point gap from a single observation into a series
that can be decomposed. Component 4 is removed by construction here, since both
sides are interpolated to 30 days.

METHOD
------
Cboe's variance calculation, applied per expiry:

    sigma^2 = (2/T) * SUM_i [ (dK_i / K_i^2) * e^(RT) * Q(K_i) ]  -  (1/T) * (F/K0 - 1)^2

    F   forward, from put-call parity at the strike where |C - P| is smallest
    K0  the largest strike at or below F
    Q   the mid quote of the OUT-of-the-money option at that strike
        (puts below K0, calls above K0, the average of both at K0)
    dK  (K_{i+1} - K_{i-1}) / 2, one-sided at the ends
    R   risk-free rate, 1-month Treasury from FRED (DGS1MO)

then interpolate the two expiries to a constant 30 days and take the square root.

HONEST LIMITS, state these in any write-up
------------------------------------------
- Strike coverage stops at +/-10% of spot. Cboe integrates until it sees two
  consecutive zero bids, which reaches much further into the tails. The tails
  carry real weight in the integral, so this estimator is expected to sit BELOW
  Cboe's, and that bias is a measured quantity here rather than a flaw to hide.
- Quotes are Alpaca's free indicative feed, not consolidated OPRA.
- The discount factor uses a single 1-month rate for both expiries.

Run:  ALPACA_KEY=... ALPACA_SECRET=... FRED_KEY=... python modelfree.py
"""
import csv
import sys
from datetime import date
from math import exp, sqrt
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "tools"))

import analyze                                    # noqa: E402
SURF = HERE / "data" / "surface.csv"

# Underlying -> the Cboe index published against it.
BENCH = {"SPY": "VIX", "QQQ": "VXN", "IWM": "RVX", "GLD": "GVZ", "USO": "OVX"}
TARGET_DAYS = 30


def _num(v):
    try:
        f = float(v)
        return f if f == f else None
    except (TypeError, ValueError):
        return None


def variance_one_expiry(rows, r_annual):
    """Cboe's sigma^2 for a single expiry. Returns (sigma2, T, n_used) or None.

    `rows` are every recorded contract at one expiry for one underlying on one
    day, both types.
    """
    if not rows:
        return None
    T = int(rows[0]["dte"]) / 365.0
    if T <= 0:
        return None

    calls, puts = {}, {}
    for row in rows:
        mid = _num(row["mid"])
        if mid is None or mid <= 0:
            continue                       # a zero or missing quote carries no info
        k = _num(row["strike"])
        if k is None:
            continue
        (calls if row["type"] == "C" else puts)[k] = mid

    both = sorted(set(calls) & set(puts))
    if len(both) < 3:
        return None                        # too thin to integrate

    disc = exp(r_annual * T)

    # Forward from put-call parity at the strike where call and put agree most.
    k_star = min(both, key=lambda k: abs(calls[k] - puts[k]))
    F = k_star + disc * (calls[k_star] - puts[k_star])

    at_or_below = [k for k in sorted(set(calls) | set(puts)) if k <= F]
    if not at_or_below:
        return None
    K0 = at_or_below[-1]

    # Out-of-the-money only: puts below K0, calls above, the average at K0.
    q = {}
    for k in sorted(set(calls) | set(puts)):
        if k < K0 and k in puts:
            q[k] = puts[k]
        elif k > K0 and k in calls:
            q[k] = calls[k]
        elif k == K0 and k in calls and k in puts:
            q[k] = (calls[k] + puts[k]) / 2.0
    ks = sorted(q)
    if len(ks) < 3:
        return None

    total = 0.0
    for i, k in enumerate(ks):
        if i == 0:
            dK = ks[1] - ks[0]
        elif i == len(ks) - 1:
            dK = ks[-1] - ks[-2]
        else:
            dK = (ks[i + 1] - ks[i - 1]) / 2.0
        total += (dK / (k * k)) * disc * q[k]

    sigma2 = (2.0 / T) * total - (1.0 / T) * ((F / K0 - 1.0) ** 2)
    return (sigma2, T, len(ks))


def model_free_30d(day_rows, r_annual):
    """Interpolate the two expiries to a constant 30 days. Returns vol in points."""
    by_exp = {}
    for row in day_rows:
        by_exp.setdefault(row["expiration"], []).append(row)
    legs = []
    for exp_date, rows in by_exp.items():
        got = variance_one_expiry(rows, r_annual)
        if got:
            legs.append((int(rows[0]["dte"]), got[0], got[1], got[2]))
    if not legs:
        return None
    legs.sort()

    if len(legs) == 1 or not (legs[0][0] <= TARGET_DAYS <= legs[-1][0]):
        # No bracket: use the nearest expiry and scale. Flagged in the output,
        # because this is weaker than a true interpolation.
        d, s2, T, n = min(legs, key=lambda x: abs(x[0] - TARGET_DAYS))
        if s2 <= 0:
            return None
        return (100.0 * sqrt(s2), n, f"single {d}d")

    (d1, s1, T1, n1), (d2, s2, T2, n2) = legs[0], legs[-1]
    w = (d2 - TARGET_DAYS) / (d2 - d1)
    blended = (T1 * s1 * w + T2 * s2 * (1 - w)) * (365.0 / TARGET_DAYS)
    if blended <= 0:
        return None
    return (100.0 * sqrt(blended), n1 + n2, f"{d1}d/{d2}d")


def risk_free():
    """1-month Treasury, annualised decimal. Falls back to 0 if FRED is absent.

    The key is checked up front rather than relied on to raise: `fred._key()`
    calls `sys.exit()`, which raises SystemExit, which does NOT inherit from
    Exception and would therefore sail straight through a bare `except
    Exception` and kill the run. The discount rate is a refinement, never a
    reason to lose a day's analysis.
    """
    import os
    if not os.environ.get("FRED_KEY"):
        print("  (FRED_KEY not set; using r=0. The discount term is small at "
              "30 days but this is a real approximation, not a no-op.)")
        return 0.0
    try:
        import fred
        obs = fred.series("DGS1MO")
        if obs:
            return obs[max(obs)] / 100.0
        print("  (FRED returned no observations; using r=0)")
    except (Exception, SystemExit) as e:
        print(f"  (FRED unavailable: {type(e).__name__}; using r=0)")
    return 0.0


def main():
    if not SURF.exists():
        sys.exit(f"No {SURF.name} yet. It starts collecting on the first "
                 f"weekday run of the surface workflow.")
    rows = list(csv.DictReader(SURF.open(newline="")))
    if not rows:
        sys.exit("surface.csv is empty.")

    r = risk_free()
    print(f"risk-free (DGS1MO): {r*100:.3f}%\n")
    vol = analyze.fetch_market_vol(sorted(set(BENCH.values())))

    days = sorted({x["date"] for x in rows})
    print(f"{'date':<12}{'sym':<6}{'ours':>8}{'cboe':>8}{'gap':>8}"
          f"{'legs':>10}{'n':>5}")
    print("-" * 58)
    gaps = {}
    for d in days:
        for sym in sorted({x["symbol"] for x in rows if x["date"] == d}):
            sub = [x for x in rows if x["date"] == d and x["symbol"] == sym]
            got = model_free_30d(sub, r)
            if not got:
                print(f"{d:<12}{sym:<6}{'-':>8}{'':>8}{'':>8}{'too thin':>10}")
                continue
            ours, n, legs = got
            idx = BENCH.get(sym)
            cb = (vol.get(idx) or {}).get(d) if idx else None
            if cb:
                gap = ours - cb
                gaps.setdefault(sym, []).append(gap)
                print(f"{d:<12}{sym:<6}{ours:>8.2f}{cb:>8.2f}{gap:>+8.2f}"
                      f"{legs:>10}{n:>5}")
            else:
                print(f"{d:<12}{sym:<6}{ours:>8.2f}{'n/a':>8}{'':>8}{legs:>10}{n:>5}")

    if gaps:
        print("\n-- gap against the published Cboe index, in volatility points")
        print("   negative = ours reads lower, which is the expected direction")
        print("   given truncated strike coverage\n")
        allg = []
        for sym in sorted(gaps):
            g = gaps[sym]
            allg += g
            mu, se, t, p = analyze.plain_t(g) if len(g) > 1 else (g[0], 0, 0, 1)
            print(f"   {sym:<5} n={len(g):>3}  mean {mu:>+7.2f}  "
                  f"min {min(g):>+6.2f}  max {max(g):>+6.2f}")
        mu, se, t, p = analyze.plain_t(allg) if len(allg) > 1 else (allg[0], 0, 0, 1)
        print(f"\n   pooled n={len(allg)}  mean gap {mu:+.2f} vol points")
        print(f"   for reference, the 4 Sep ATM-vs-Cboe gap was -3.61")


if __name__ == "__main__":
    main()
