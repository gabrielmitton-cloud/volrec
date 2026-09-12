# H3 — A model-free variance estimate built from free retail-grade option data reproduces the published Cboe index

**Registered:** 2026-09-12, after the estimator was built and before any series
exists to test it on. The single-day calibration below is reported honestly as
calibration, not as a test of the hypothesis.
**Status:** registered. Calibrated on one day. Not yet tested on a series.
**Sample:** the strike surface in `data/surface.csv`, which begins accumulating
on the first weekday run after 2026-09-12.

## Where this came from, including what it replaced

Two prior ideas died on 11-12 September and this is what survived them.

The Bloomberg route died on a 90-day data wall. OptionMetrics died on Pepperdine
restricting WRDS to faculty, staff and doctoral students. And a proposed
within-day cross-strike design died on arithmetic: differencing two strikes
against a common realised variance cancels the realised term exactly and leaves
the shape of the implied volatility surface, which is the volatility smile,
which Bollen & Whaley published in 2004. See HANDOFF section 14.

What remains is the constraint itself, turned into the subject. This project
runs on a free, indicative, non-OPRA feed because it has no budget. That is the
position most people outside a funded institution are in, and nobody with a
research budget bothers to measure what it costs, because they simply buy
OptionMetrics instead.

**Cboe publishes the authoritative model-free number for five underlyings this
project records: SPY/VIX, QQQ/VXN, IWM/RVX, GLD/GVZ, USO/OVX.** So the free-data
estimate can be checked against the authoritative one, on the same underlying,
on the same day, every day.

## The hypothesis

**H3a.** A model-free variance estimate computed from the free indicative feed,
using Cboe's own methodology, tracks the published index with a mean absolute
gap **under 1.0 volatility points**, across the five benchmarked underlyings,
over the collected series.

**H3b.** The residual gap is **negative on average** (the estimate reads low),
because strike coverage is truncated relative to Cboe's, which integrates until
it observes two consecutive zero bids.

**H3c — the interesting one.** The truncation bias **scales with the volatility
of the underlying**, because a fixed percentage strike band spans fewer standard
deviations when volatility is higher. Prediction: regressing the absolute gap on
the Cboe index level gives a **positive, significant** slope.

## Specification — frozen here

- Estimator: Cboe's variance calculation per expiry, implemented in
  `modelfree.py`. Forward from put-call parity at the strike where call and put
  mid quotes agree most closely; `K0` the largest strike at or below the
  forward; out-of-the-money contracts only, averaging call and put at `K0`;
  `dK` the centred difference, one-sided at the ends; discount factor from the
  1-month Treasury (FRED `DGS1MO`).
- Two expiries per day, interpolated to a constant 30 days, so no maturity
  mismatch enters the comparison.
- Strike grid: 40 targets spanning +/-30% of spot, nearest available strike to
  each. See the calibration below for why the band is 30% and not the 10% that
  was originally advised.
- Benchmark: the Cboe index close for the same date, from the same CDN feed
  `analyze.py` already uses.
- Gap is defined as **ours minus Cboe**, in volatility points. Negative means
  the free-data estimate reads lower.

## Calibration, 2026-09-11 — one day, reported as calibration not as evidence

| band x strikes | mean abs gap | worst | rows/day | MB/yr |
|---|---|---|---|---|
| +/-10% x 20 | 3.97 | -12.37 | 532 | 23 |
| +/-20% x 30 | 1.31 | -4.39 | 846 | 36 |
| **+/-30% x 40** | **0.59** | **-1.84** | 1158 | 50 |

At +/-30%, per underlying: SPY 15.83 against 15.84 (**-0.01**), QQQ 20.79
against 21.02 (-0.23), GLD 25.36 against 25.68 (-0.32), IWM 20.51 against 19.98
(**+0.53**), USO 57.08 against 58.92 (-1.84).

**This is one day and five underlyings. It sets the configuration; it does not
test H3.** A single day cannot distinguish a method that works from a method
that happened to land. The hypothesis is tested on the accumulated series.

## What would falsify it

- H3a fails if the mean absolute gap over the series exceeds 1.0 points.
- H3b fails if the mean gap is positive, which would mean something other than
  truncation dominates and the explanation is wrong.
- H3c fails if the gap has no relationship to the volatility level. Note IWM
  came in **positive** on the calibration day, which already shows the bias is
  not uniformly negative and that H3b may not survive.

## Why this is worth doing

It converts the project's binding limitation into its subject. The question
"how much precision does free options data actually cost you, and where does
the loss come from" has a real answer, is useful to everyone who also cannot
afford OptionMetrics, and can only be asked by someone holding both the
constraint and the benchmark at once.

It also produces a reusable finding: **the truncation bias is not a fixed
penalty, it scales with volatility**, so any study using a fixed percentage
strike band is biased hardest on exactly the high-volatility names most likely
to be interesting.

## NOT in this hypothesis

- No claim about the volatility risk premium itself. This is a measurement
  study about the instrument, not a finding about the market.
- No claim that the free feed equals OPRA. The comparison is against Cboe's
  published index, which is computed from consolidated quotes, so feed quality
  is one of several components inside the residual gap and is not separately
  identified here.

## Adjustment log

- **2026-09-12, before any series existed.** Strike band widened from +/-10% x
  20 to +/-30% x 40 on the calibration above. Recorded rather than silently
  applied: the advised configuration was +/-10%, and it was changed because it
  was measured to be badly truncated, not because a result was disliked.
