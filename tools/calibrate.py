#!/usr/bin/env python3
"""Is every measuring instrument in this project calibrated?

WHAT CALIBRATED MEANS HERE
--------------------------
A measurement is calibrated when its output matches a KNOWN reference truth. Each
instrument below is fed an input whose correct answer is known in advance, and the
output is compared to that answer. Nothing here reads a market price to decide
what "right" is - that would be checking the data against itself.

    instrument                  reference truth
    --------------------------  ---------------------------------------------------
    Black-76 pricer             put-call parity, an arbitrage identity (exact)
    implied-vol inversion       invertibility: price -> vol -> price is identity
    model-free variance         Carr & Madan (1998): under a constant vol the
                                model-free variance IS sigma^2
    the --wide lift (H3)        the lift with EVERY expiry widened: what the
                                recorder widens must reproduce it exactly
    realised-vol estimator      a simulated path with a known sigma
    the significance tests      a simulated world with NO premium, where a 5%
                                test must reject about 5% of the time
    risk-free input             today's date (is the rate current?)

TOLERANCES ARE ARGUED, NOT TUNED
--------------------------------
Every threshold is set from something outside the measurement it judges, so a
check cannot be made to pass by loosening it after the fact:

- Parity and round-trip: floating-point precision. These are identities.
- The --wide lift: floating-point precision. It is an identity once every leg the
  estimate weights has been widened; any shortfall is a leg the recorder skipped.
- Model-free method error: HALF of H3a's registered 1.0-point budget. Method error
  may not consume more than half the tolerance the hypothesis is judged on,
  otherwise H3a could pass or fail on the estimator rather than the data.
- Realised vol: +/-0.5% relative, with a fixed seed so the result is deterministic.
- Test size: [2%, 9%] at 200 replications - the binomial 2.5-sigma band around 5%.

WHAT IT FOUND, 17 September 2026 - read before trusting H3
----------------------------------------------------------
Every instrument calibrates. And one result reframes H3: the model-free METHOD
loses at most 0.20 points on a flat 51% vol, so USO's observed -2.93 gap is not
method error. On USO's own recorded smile, the variance lying beyond +/-30% is
-1.37 points with flat wings and -3.24 with linear wings - the observed gap sits
inside that bracket. USO's gap is its fat wings, not bad data. See H3's
adjustment log.

    python3 tools/calibrate.py            # ~20 seconds, no network, no keys
"""
import json
import math
import random
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import analyze                                              # noqa: E402
import modelfree                                            # noqa: E402
from iv_convention import black76, implied_vol              # noqa: E402

H3A_BUDGET = 1.0            # H3a's registered threshold, in volatility points
fails = []


def check(ok, name, detail):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    print(f"        {detail}")
    if not ok:
        fails.append(name)


def black76_identities():
    print("\n-- Black-76 pricer and inversion")
    worst_parity = worst_trip = 0.0
    for F, K, T, r, s in [(100, 80, 30 / 365, 0.04, 0.5), (100, 100, 0.25, 0.039, 0.15),
                          (360, 450, 66 / 365, 0.0426, 0.45), (760, 700, 22 / 365, 0.039, 0.13)]:
        c, p = black76("C", F, K, T, r, s), black76("P", F, K, T, r, s)
        worst_parity = max(worst_parity, abs((c - p) - math.exp(-r * T) * (F - K)))
        for kind, px in (("C", c), ("P", p)):
            iv = implied_vol(kind, px, F, K, T, r)
            if iv is not None:
                worst_trip = max(worst_trip, abs(black76(kind, F, K, T, r, iv) - px))
    check(worst_parity < 1e-9, "put-call parity: C - P = e^(-rT)(F - K)",
          f"worst violation {worst_parity:.2e} across four contracts")
    check(worst_trip < 1e-7, "inversion round-trip: price -> vol -> price",
          f"worst price error {worst_trip:.2e}")


def modelfree_method():
    print("\n-- model-free variance against a KNOWN volatility (Carr & Madan 1998)")
    worst = 0.0
    parts = []
    for sigma in (0.13, 0.23, 0.42, 0.51):
        S, r, dte = 100.0, 0.039, 30
        T = dte / 365
        F = S * math.exp(r * T)
        rows = []
        for i in range(40):                      # the recorder's own +/-30% x 40 grid
            K = round(S * (0.70 + i * 0.60 / 39), 4)
            for kind in ("C", "P"):
                rows.append({"dte": str(dte), "strike": str(K), "type": kind,
                             "mid": str(black76(kind, F, K, T, r, sigma))})
        s2, _, _ = modelfree.variance_one_expiry(rows, r)
        err = math.sqrt(s2) * 100 - sigma * 100
        worst = max(worst, abs(err))
        parts.append(f"{sigma * 100:.0f}% -> {err:+.2f}")
    check(worst <= H3A_BUDGET / 2,
          f"method error at +/-30% stays under half of H3a's {H3A_BUDGET:.1f}-point budget",
          f"error by true vol: {', '.join(parts)} pts; worst {worst:.2f}")


def realised_vol():
    print("\n-- realised-vol estimator against a KNOWN volatility")
    rng = random.Random(20260917)
    worst = 0.0
    parts = []
    for sigma in (0.15, 0.30, 0.55):
        sd = sigma / math.sqrt(analyze.TRADING_DAYS)
        est = [analyze.realized_vol([rng.gauss(0, sd) for _ in range(21)])
               for _ in range(8000)]
        bias = 100 * (sum(est) / len(est) / sigma - 1)
        worst = max(worst, abs(bias))
        parts.append(f"{sigma * 100:.0f}% -> {bias:+.2f}%")
    check(worst <= 0.5, "c4 correction removes the small-sample bias",
          f"relative bias after c4(21)={analyze.c4(21):.5f}: {', '.join(parts)}")


def test_size():
    print("\n-- the significance tests, in a world with NO premium")
    a = analyze.simulate(reps=200, rho=0.0, seed=7)
    check(2.0 <= a["non-overlap"] <= 9.0,
          "ATM panel: the non-overlapping test rejects near its nominal 5%",
          f"{a['non-overlap']:.1f}% (pooled, for contrast: {a['pooled']:.1f}% - "
          f"the reason it is never quoted)")
    b = analyze.simulate_surface(reps=200, days=40, rho_market=0.3, seed=7)
    check(2.0 <= b["date"] <= 9.0,
          "surface: the date-clustered test rejects near its nominal 5%",
          f"{b['date']:.1f}% (per underlying-day, for contrast: {b['underlying-day']:.1f}%)")
    check(2.0 <= b["contrast"] <= 9.0,
          "surface: the within-day volume contrast rejects near its nominal 5%",
          f"{b['contrast']:.1f}%")


def risk_free_input():
    print("\n-- the risk-free input")
    cache = ROOT / "data" / "fred_cache.json"
    if not cache.exists():
        print("  INFO  no FRED cache here; the rate is fetched live when FRED_KEY is set")
        return
    obs = json.loads(cache.read_text()).get("DGS1MO||") or {}
    if not obs:
        return
    last = max(obs)
    age = (date.today() - date.fromisoformat(last)).days
    # A 10bp rate error moves one run's scaled hedged gain by about 0.013bp, against
    # a smallest detectable H4 effect of 0.56bp. So staleness is reported, not failed,
    # until it is large enough to matter: a full month.
    print(f"  {'INFO' if age <= 31 else 'WARN'}  DGS1MO cached through {last} "
          f"({age} days old), {obs[last]:.2f}%.")
    print("        Immaterial to H4 below a month: 10bp moves a hedged gain ~0.013bp,")
    print("        against a smallest detectable effect of 0.56bp.")


def wide_lift_identity():
    """H3's --wide prediction is a LIFT: the 30-day estimate with the wide strikes
    minus without. Until 18 Sep 2026 the estimate integrated the outermost expiries
    present, while the recorder widened the two nearest 30 days, so on three days in
    five a weighted leg was never widened and a known 1.93-point lift read as 0.63.

    The reference truth is the lift with EVERY expiry widened. The measured lift runs
    the recorder's own wide pass (surface.wide_rows_for, network replaced by a fake
    chain) and modelfree's own estimator. They must agree to float precision on
    every expiry layout the weekly calendar produces, carry-forward included."""
    print("\n-- the --wide lift against the lift with every expiry widened (H3)")
    import surface
    from datetime import date as _d, timedelta
    S, r, iv0, today = 150.0, 0.039, 0.51, _d(2026, 9, 18)

    def smile(k):                        # fat-winged and USO-like; any smile will do
        return iv0 * (1 + 0.8 * k * k)

    def row(exp, K, kind, extra=None):
        T = (exp - today).days / 365
        F = S * math.exp(r * T)
        p = black76(kind, F, K, T, r, smile(math.log(K / F)))
        return {"date": today.isoformat(), "symbol": "USO", "expiration": exp.isoformat(),
                "dte": str((exp - today).days), "type": kind, "strike": str(K),
                "moneyness": str(K / S), "mid": str(p), "bid": str(p),
                "iv": str(iv0), **(extra or {})}

    band = surface.wide_band(iv0, surface.TARGET_DTE)
    ladder = sorted({round(S * m, 3) for m in surface.wide_targets(band)})   # OCC: 1/1000
    worst, parts = 0.0, []
    saved = surface.wide_chain, surface.PACE
    try:
        surface.PACE = 0
        for layout in ([21, 28, 35], [25, 32], [24, 31], [23, 30, 37], [22, 29, 36]):
            exps = [today + timedelta(d) for d in layout]
            inner = [row(e, round(S * m, 4), k) for e in exps
                     for m in surface.MONEYNESS_GRID for k in ("C", "P")]

            def fake_chain(s, symbol, spot, day, kind, bnd, _e=exps):
                return {f"USO{e:%y%m%d}{kind[0].upper()}{int(round(K * 1000)):08d}":
                        {"latestQuote": {"bp": 0.0, "ap": 0.0}} for e in _e for K in ladder}
            surface.wide_chain = fake_chain
            got, _ = surface.wide_rows_for(None, "USO", S, today, inner)
            # re-price what the recorder chose, exactly: the fake chain carries no quotes
            wide = [row(_d.fromisoformat(x["expiration"]), float(x["strike"]), x["type"])
                    for x in got]
            every = [row(e, K, k) for e in exps for K in ladder for k in ("C", "P")]
            base = modelfree.model_free_30d(inner, r)[0]
            measured = modelfree.model_free_30d(inner + wide, r)[0] - base
            truth = modelfree.model_free_30d(inner + every, r)[0] - base
            worst = max(worst, abs(measured - truth))
            parts.append(f"{layout}: {measured:+.3f} vs {truth:+.3f}")
    finally:
        surface.wide_chain, surface.PACE = saved
    check(worst < 1e-9, "the --wide lift equals the lift with every expiry widened",
          f"{'; '.join(parts)}; worst {worst:.1e}")


def main():
    print("Calibration: every instrument against a known reference truth.")
    black76_identities()
    modelfree_method()
    wide_lift_identity()
    realised_vol()
    test_size()
    risk_free_input()
    print("\n" + "=" * 60)
    print(f"RESULT: {len(fails)} uncalibrated instrument(s)"
          + (f": {fails}" if fails else " - all calibrated"))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
