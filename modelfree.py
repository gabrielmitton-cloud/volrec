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

WHICH two expiries: the pair `surface.py` picked, by the same rule (`pick_pair`) -
the last at or under 30 days and the first over it. That is Cboe's near/next rule
for weekly listings. It is NOT "the shortest and longest present": `surface.py`
carries yesterday's contracts forward for H4's continuity, so on about three days
in five a third, shorter expiry sits in the file. Integrating that one broke Cboe's
23-day near-term floor and left `--wide` measuring a leg the wide pass never
extended. Changed 18 Sep 2026, before any affected day had a Cboe close; see H3's
adjustment log.

--wide (a SENSITIVITY, never the registered estimate) adds `surface_wide.csv` and
reports the LIFT, wide minus registered, per day, which is how H3's 17 Sep
prediction is tested. It also reports the lift under Cboe's zero-bid rule. A
known-answer test (H3, 18 Sep) found the two bracket the truth: counting zero-bid
quotes at half the ask reads high, Cboe's rule reads low.

HONEST LIMITS, state these in any write-up
------------------------------------------
- Strike coverage stops at +/-30% of spot (widened from +/-10% on 12 Sep; --wide
  reaches further on high-volatility names). Cboe integrates until it sees two
  consecutive zero bids, which reaches much further into the tails. The tails
  carry real weight in the integral, so this estimator is expected to sit BELOW
  Cboe's, and that bias is a measured quantity here rather than a flaw to hide.
- Quotes are Alpaca's free indicative feed, not consolidated OPRA.
- The discount factor uses a single 1-month rate for both expiries.

Run:  ALPACA_KEY=... ALPACA_SECRET=... FRED_KEY=... python modelfree.py
"""
import csv
import sys
from math import exp, sqrt
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "tools"))

import analyze                                    # noqa: E402
SURF = HERE / "data" / "surface.csv"
# The wide band (added 17 Sep 2026): contracts beyond +/-30% on high-volatility
# names, in a separate file. Used ONLY with --wide, to test H3c directly. H3's
# registered numbers come from SURF alone and are unchanged by its existence.
SURF_WIDE = HERE / "data" / "surface_wide.csv"

# Underlying -> the Cboe index published against it.
BENCH = {"SPY": "VIX", "QQQ": "VXN", "IWM": "RVX", "GLD": "GVZ", "USO": "OVX"}
TARGET_DAYS = 30

# H3's falsifiable prediction for --wide, registered 17 Sep 2026 BEFORE any wide data
# existed. Never change these to suit a result.
PREDICTED_LIFT = {"USO": (1.4, 3.2)}
# Registered 18 Sep 2026, also before any wide data. GLD and AAPL are widened only to
# 33%, and every smile fitted to their own 14-17 Sep quotes predicts a lift of 0.03 to
# 0.14. The limit adds the +0.14 that counting zero-bid quotes was measured to add
# in the known-answer test, then rounds: a control over 0.3 means the pipeline is
# making lift that is not tail variance. See H3, "How the prediction is tested".
NULL_CONTROLS = ("GLD", "AAPL")
NULL_LIFT_MAX = 0.3
FIRST_READING_DAYS = 3
# H5e, registered 23 Sep 2026 before that day's run: see hypotheses/...-h5-wing-quote-
# quality.md. Out of sample from H5E_START only. The bar is half of H3a's 1.0-point
# budget, the same share calibrate.py allows method error. Never change these.
H5E_SYMBOL = "USO"
H5E_START = "2026-09-23"
H5E_MAX_ABS_GAP = 0.5
H5E_MIN_DAYS = 10


def _num(v):
    try:
        f = float(v)
        return f if f == f else None
    except (TypeError, ValueError):
        return None


def variance_one_expiry(rows, r_annual, zero_bid_rule=False):
    """Cboe's sigma^2 for a single expiry. Returns (sigma2, T, n_used) or None.

    `rows` are every recorded contract at one expiry for one underlying on one
    day, both types.

    zero_bid_rule (off by default, and off for every registered H3 number):
      True    Cboe's rule on the out-of-the-money strikes - walking outward from K0,
              skip any zero bid and stop after two consecutive zero bids.
      "skip"  skip every zero bid and never stop. Registered as H5e on 23 Sep
              2026: on 22 Sep USO carried one-sided stub quotes (no bid, ~$3 ask)
              on odd strikes only 15-20% from the money, and Cboe's stop rule cut
              the put wing there, inside the registered band.
    Used only by the --wide sensitivity and H5, where the far wings are thin.
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
    if zero_bid_rule:
        bids = {}
        for row in rows:
            k, b = _num(row["strike"]), _num(row.get("bid"))
            if k is not None:
                bids[(k, row["type"])] = b
        stop = zero_bid_rule != "skip"
        for side, walk in (("P", sorted((k for k in q if k < K0), reverse=True)),
                           ("C", sorted(k for k in q if k > K0))):
            zeros = 0
            for k in walk:
                if stop and zeros >= 2:
                    del q[k]                  # Cboe: nothing past two consecutive zero bids
                elif not bids.get((k, side)):
                    zeros += 1
                    del q[k]
                else:
                    zeros = 0
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


def pick_pair(dtes):
    """The two expiries to interpolate: surface.py's own pick rule, verbatim - the
    last at or under TARGET_DAYS and the first over it, else the two nearest.

    Kept identical to rows_for() in surface.py on purpose (that function is frozen
    and cannot be imported without the network stack). pressure_test.py checks the
    two agree on a full calendar and that the wide pass extends every leg this
    picks, so neither can drift alone.
    """
    d = sorted(set(dtes))
    below = [x for x in d if x <= TARGET_DAYS]
    above = [x for x in d if x > TARGET_DAYS]
    if below and above:
        return [below[-1], above[0]]
    return sorted(sorted(d, key=lambda x: abs(x - TARGET_DAYS))[:2])


def leg_weights(pair):
    """Share of the interpolated 30-day total variance each leg carries, under a flat
    forward variance. A leg with weight 0 does not move the estimate at all."""
    if len(pair) == 1 or not (pair[0] <= TARGET_DAYS <= pair[-1]):
        return {min(pair, key=lambda x: abs(x - TARGET_DAYS)): 1.0}
    d1, d2 = pair
    w = (d2 - TARGET_DAYS) / (d2 - d1)
    a, b = d1 * w, d2 * (1 - w)
    return {d1: a / (a + b), d2: b / (a + b)}


def model_free_30d(day_rows, r_annual, zero_bid_rule=False):
    """Interpolate the picked pair to a constant 30 days. Returns vol in points."""
    by_exp = {}
    for row in day_rows:
        by_exp.setdefault(row["expiration"], []).append(row)
    legs = []
    for exp_date, rows in by_exp.items():
        got = variance_one_expiry(rows, r_annual, zero_bid_rule)
        if got:
            legs.append((int(rows[0]["dte"]), got[0], got[1], got[2]))
    if not legs:
        return None
    pair = pick_pair([x[0] for x in legs])
    legs = sorted(x for x in legs if x[0] in pair)

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
    registered, extra = rows, []
    # --wide adds the contracts beyond the registered band. The integral then
    # reaches further into the tails, which is exactly what H3c predicts should
    # close the gap on high-volatility names. Without the flag, nothing changes:
    # this is a sensitivity, never a replacement for the frozen specification.
    if "--wide" in sys.argv:
        if SURF_WIDE.exists():
            extra = list(csv.DictReader(SURF_WIDE.open(newline="")))
            rows = rows + extra
            print(f"--wide: adding {len(extra)} contracts beyond the registered "
                  f"+/-30% band. SENSITIVITY ONLY - not H3's registered estimate.\n")
        else:
            print("--wide: no surface_wide.csv yet; it starts with the next "
                  "surface run. Showing the registered estimate.\n")

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
        if extra:
            # 23 Sep 2026: this summary read "USO max +12.00" and was nearly taken for
            # H3a's own series. In --wide mode it scores the SENSITIVITY estimate.
            print("\n-- gap of the WIDE SENSITIVITY against Cboe - NOT H3a's registered gap")
            print("   (run without --wide for H3a). Zero bids count at half the ask here,")
            print("   so the wings inflate it; see the LIFT and H5e blocks below.\n")
        else:
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

    if extra:
        wide_lift_report(registered, extra, r)
        h5e_report(registered, extra, r, vol)


def h5e_report(registered, extra, r, vol):
    """H5e, registered 23 Sep 2026 BEFORE that day's data: USO's wide estimate with
    zero-bid quotes skipped (never stopped) tracks OVX. Judged only from H5E_START on;
    earlier days are printed as the in-sample evidence that motivated it, never counted."""
    idx = BENCH[H5E_SYMBOL]
    print(f"\n-- H5e: {H5E_SYMBOL}, wide strikes, zero bids SKIPPED, against {idx} "
          f"(registered 23 Sep; judged from {H5E_START})")
    print(f"   {'date':<12}{idx:>7}{'registered':>12}{'gap':>8}{'wide skip':>11}{'gap':>8}  counted")
    judged = []
    for d in sorted({x["date"] for x in extra if x["symbol"] == H5E_SYMBOL}):
        cb = (vol.get(idx) or {}).get(d)
        inner = [x for x in registered if x["date"] == d and x["symbol"] == H5E_SYMBOL]
        outer = [x for x in extra if x["date"] == d and x["symbol"] == H5E_SYMBOL]
        a, b = model_free_30d(inner, r), model_free_30d(inner + outer, r, "skip")
        if not (cb and a and b):
            print(f"   {d:<12}{'n/a' if not cb else '':>7}  (no {idx} close yet, or too thin)")
            continue
        counted = d >= H5E_START
        if counted:
            judged.append((a[0] - cb, b[0] - cb))
        print(f"   {d:<12}{cb:>7.2f}{a[0]:>12.2f}{a[0] - cb:>+8.2f}{b[0]:>11.2f}{b[0] - cb:>+8.2f}  "
              + ("yes" if counted else "no - in-sample, before registration"))
    if not judged:
        print(f"   no counted day yet; H5e needs {H5E_MIN_DAYS}")
        return
    mae = sum(abs(g) for _, g in judged) / len(judged)
    closer = sum(abs(g) < abs(r_) for r_, g in judged)
    verdict = (f"mean |gap| {mae:.2f} against {H5E_MAX_ABS_GAP} "
               f"({'under' if mae < H5E_MAX_ABS_GAP else 'OVER'}); closer than registered on "
               f"{closer} of {len(judged)} days ({'majority' if closer > len(judged) / 2 else 'NOT a majority'})")
    if len(judged) < H5E_MIN_DAYS:
        verdict += f" - {len(judged)} of {H5E_MIN_DAYS} days, not a verdict yet"
    print(f"   {verdict}")


def wide_lift_report(registered, extra, r):
    """H3's 17 Sep prediction, tested exactly as pre-registered on 18 Sep: the lift
    is --wide minus registered, same day, same legs. See H3, "How the prediction
    is tested"."""
    print("\n-- the LIFT: wide minus registered, same day, same legs (vol points)")
    print("   'as reg' counts a zero-bid quote at half its ask, as the registered")
    print("   estimator does; 'zero-bid' applies Cboe's rule. A known-answer test found")
    print("   the first reads high and the second low, so the truth lies between.\n")
    print(f"   {'date':<12}{'sym':<6}{'reg':>7}{'wide':>7}{'as reg':>8}{'zero-bid':>9}"
          f"{'wide rows':>10}{'0-bid':>6}  legs")
    lifts = {}
    for d in sorted({x["date"] for x in extra}):
        for sym in sorted({x["symbol"] for x in extra if x["date"] == d}):
            inner = [x for x in registered if x["date"] == d and x["symbol"] == sym]
            outer = [x for x in extra if x["date"] == d and x["symbol"] == sym]
            if not inner:
                continue
            # Coverage: every leg that carries weight must have wide rows, or the lift
            # is diluted. Pre-registered: such a day is shown, flagged, and excluded.
            dte_of = {x["expiration"]: int(x["dte"]) for x in inner}
            pair = pick_pair(dte_of.values())
            widened = {int(x["dte"]) for x in outer}
            short = [d_ for d_, w in leg_weights(pair).items() if w > 0 and d_ not in widened]
            got = [model_free_30d(inner, r), model_free_30d(inner + outer, r),
                   model_free_30d(inner, r, True), model_free_30d(inner + outer, r, True)]
            zb = sum(1 for x in outer if not _num(x.get("bid")))
            legs = "/".join(f"{x}d" for x in pair) + (f"  UNCOVERED {short}, excluded" if short else "")
            if not all(got):
                print(f"   {d:<12}{sym:<6}{'too thin':>7}")
                continue
            a, b, za, zbw = (g[0] for g in got)
            print(f"   {d:<12}{sym:<6}{a:>7.2f}{b:>7.2f}{b - a:>+8.2f}{zbw - za:>+9.2f}"
                  f"{len(outer):>10}{zb:>6}  {legs}")
            if not short:
                lifts.setdefault(sym, []).append((b - a, zbw - za))

    if not lifts:
        return
    print(f"\n   {'sym':<6}{'days':>5}{'mean as reg':>13}{'mean zero-bid':>15}   reading")
    for sym in sorted(lifts, key=lambda s: -sum(x[0] for x in lifts[s]) / len(lifts[s])):
        v = lifts[sym]
        m1 = sum(x[0] for x in v) / len(v)
        m2 = sum(x[1] for x in v) / len(v)
        note = ""
        if sym in PREDICTED_LIFT:
            lo, hi = PREDICTED_LIFT[sym]
            note = (f"registered bracket {lo:.1f} to {hi:.1f}: "
                    + ("INSIDE" if lo <= m1 <= hi else "OUTSIDE"))
            if len(v) < FIRST_READING_DAYS:
                note += f" (only {len(v)} day(s); first reading at {FIRST_READING_DAYS})"
        elif sym in NULL_CONTROLS:
            note = (f"null control, must stay under {NULL_LIFT_MAX}: "
                    + ("ok" if m1 < NULL_LIFT_MAX else "FAILED - lift that is not tail variance"))
        print(f"   {sym:<6}{len(v):>5}{m1:>+13.2f}{m2:>+15.2f}   {note}")
    print("\n   Pre-registered in H3 on 18 Sep: USO's reading is the as-registered mean over")
    print("   every covered wide day, never a subset. SPY is never widened, so its half of")
    print("   the prediction holds by construction and is not evidence either way.")


if __name__ == "__main__":
    main()
