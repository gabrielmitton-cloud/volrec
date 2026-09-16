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

## The Bloomberg cross-check, 15 September 2026 - one matched day

The calibration above measures the free-data estimate against Cboe. It cannot say
whether the residual is bad quotes or a different calculation, because Cboe publishes
one number per underlying, not the contracts behind it. Bloomberg can, and on 15
September the two sides were captured 14 minutes apart on the same 16 October expiry:
the recorder at 19:10 UTC, the terminal export pulled at 18:57.

Matched contract by contract, with `tools/bloomberg_compare.py`:

| | matched | IV gap, vol pts | mid gap | mid gap / spread | volume, free vs Bloomberg |
|---|---|---|---|---|---|
| TSLA | 78 | +1.84 | +0.27% | 0.42 | 40,479 vs 39,231 |
| USO | 40 | +1.74 | +0.07% | 0.64 | 13,418 vs 13,198 |
| SPY | 14 | +0.55 | +0.45% | 1.06 | 17,658 vs 17,408 |

IV gap is the free feed minus Bloomberg's IVM, in volatility points, at the median.

**The prices agree; the implied volatilities do not.** Mid prices sit within half a
percent, and on TSLA within half of the quoted bid-ask spread. Volumes agree to within
3%. Yet the free feed's implied volatility reads one to two points above Bloomberg's on
both single names. Two feeds cannot disagree on volatility while agreeing on price
unless they are inverting those prices differently, so the gap is a **convention
difference, not a quote-quality difference**. Bloomberg prints its own implied forward
on every block - 358.17 against a 357.04 spot on TSLA - and the free feed's greeks come
from Alpaca's own model with its own forward, rate and dividend assumptions.

**Why this matters for H3.** `modelfree.py` integrates out-of-the-money *prices*, never
implied volatilities. An implied-volatility convention gap therefore does not enter the
model-free estimate at all, and the 0.59-point residual against Cboe at +/-30% cannot be
explained by it. It also means the ATM panel's `iv` column carries a vendor convention
that the model-free series does not, and the two should not be mixed in one comparison.

**Honest limits of this cross-check.**

- One day, three underlyings, one expiry. This is a cross-check, not a test.
- The SPY export matched only 14 contracts, because 40 strikes a dollar apart spans
  2.6% of spot. Its numbers are at-the-money only and its price gate failed at 1.06 of
  a spread. Treat SPY as unmeasured until a wider export exists.
- USO also failed the price gate at 0.64 of a spread, on 40 contracts. TSLA, the only
  name with a wide strike range and a passing gate, is the one to lean on.
- Bloomberg's licence restricts redistribution. The exports live outside this repository
  and only aggregates are recorded here. Any published use needs the attribution
  "Source: Bloomberg Finance L.P." and the open question in HANDOFF section 16.

## The convention test, 16 September 2026 - and what it refuted

The paragraph above predicted that re-inverting the free feed's own mids with
Bloomberg's printed forward and rate would collapse the gap. **It did not, and the
prediction is recorded here as wrong rather than quietly dropped.**

`tools/iv_convention.py`, out-of-the-money contracts only, medians in vol points:

| | n | Alpaca IV minus Bloomberg | ours from Alpaca's mid | difference |
|---|---|---|---|---|
| TSLA | 40 | +1.73 | +1.75 | +0.00 |
| USO | 20 | +1.81 | +1.86 | +0.01 |

Our Black-76 inversion reproduces Alpaca's implied volatility to two decimals from the
same mid. The forward and the rate were never the disagreement.

The decisive test was to invert **Bloomberg's own quotes** with the same model:

| price inverted | TSLA, median gap to Bloomberg's IVM | USO |
|---|---|---|
| Bloomberg's bid | +1.63 | +1.14 |
| Bloomberg's mid | +1.80 | +2.21 |
| Bloomberg's ask | +1.91 | +3.04 |
| the free feed's mid | +1.75 | +1.86 |

Feeding Bloomberg's own prices into this project's model still lands about 1.7 points
above the number Bloomberg prints beside them. **The gap is between the two models, not
between the two data sources.** The split by side and moneyness rules out the obvious
model explanations: TSLA calls +1.76 against puts +1.51, near the money +1.62 against
the wings +1.89. Early exercise would hit puts alone; a skew-fitting difference would
not be this flat.

**What this settles, and what it does not.** It settles the question this cross-check
existed to answer: the free feed's quotes are as good as Bloomberg's, to within half a
bid-ask spread, and every remaining difference is downstream of the prices. It does not
identify which model assumption differs. Candidates still open: an American binomial
against this European forward model, a different day count, or a volatility surface
fitted across strikes rather than inverted contract by contract.

**Why H3 survives it.** `modelfree.py` integrates out-of-the-money *prices*. Nothing in
it reads an implied volatility, from either source, so a model gap of this size cannot
reach the 0.59-point residual against Cboe. The exposure is elsewhere: `hedged.py` uses
the vendor's *delta*, which is model-derived in exactly the way this test found wanting,
so H4's hedge ratios inherit an unquantified model difference. Say so in any write-up.

Bloomberg figures throughout: Source: Bloomberg Finance L.P.

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
