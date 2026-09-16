# H3 — A model-free variance estimate built from free retail-grade option data reproduces the published Cboe index

**Registered:** 2026-09-12, after the estimator was built and before any series
exists to test it on. The single-day calibration below is reported honestly as
calibration, not as a test of the hypothesis.
**Status:** registered. Calibrated on one day. Not yet tested on a series.
Cross-checked against Bloomberg 15-16 Sep; the volatility gap is identified
as a day-count convention and does not touch the estimator.
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

## The day count, 16 September 2026 - the gap identified

The section above left three candidates open and named the bounded test: price a
contract under a binomial and see whether 1.7 points closes. It does not. The answer
is the fourth input, the one never printed as a year fraction.

`tools/model_gap.py` inverts the question. Rather than asking what volatility
reproduces Bloomberg's price, it asks what TIME reproduces Bloomberg's own printed
volatility from Bloomberg's own printed price, and then reports that time as an
annualisation divisor two ways. A convention shows up as a divisor that holds across
maturities; anything that drifts with maturity is not the explanation.

| | cal d | bus d | n | IVM | gap at 365 | gap at 252 | gap at 252 + parity F | cal divisor | bus divisor |
|---|---|---|---|---|---|---|---|---|---|
| SPY 16-Oct | 31 | 23 | 40 | 13.5 | +0.60 | +0.08 | +0.08 | 336.3 | 249.5 |
| SPY 30-Oct | 45 | 33 | 40 | 13.9 | +0.61 | +0.13 | +0.16 | 338.0 | 247.9 |
| TSLA 16-Oct | 31 | 23 | 40 | 42.1 | **+1.80** | **+0.08** | **+0.04** | 338.4 | 251.1 |
| TSLA 20-Nov | 66 | 48 | 40 | 44.7 | +1.29 | +0.13 | +0.11 | 344.5 | 250.6 |
| USO 16-Oct | 31 | 23 | 40 | 54.8 | +2.21 | -0.07 | +0.06 | 341.7 | 253.5 |
| USO 20-Nov | 66 | 48 | 40 | 53.6 | +1.01 | -0.38 | -0.25 | 351.9 | 255.9 |

Gaps are medians in volatility points, ours minus Bloomberg's IVM, out-of-the-money
contracts only.

**The business-day divisor holds and the calendar-day divisor does not.** Across six
blocks the business divisor sits between 247.9 and 255.9 with no maturity trend,
while the calendar divisor climbs from 336 at one month to 352 at two. No fixed
calendar divisor fits both maturities; 252 business days fits all six. Re-inverting
on that clock collapses TSLA's gap from +1.80 to +0.08 volatility points, and every
other block with it.

**Bloomberg's IVM is on a 252 business-day clock. Alpaca's, and therefore this
project's, is on a 365 calendar-day clock.** At 31 calendar days those are 23/252 =
0.0913 against 31/365 = 0.0849, a 7.5% larger variance-time, and a volatility
inverted on the smaller one has to read about 3.7% higher to reach the same price.
Neither convention is wrong. The whole 1.7 points is the distance between them.

Three things corroborate it rather than just fitting it:

- **It scales with the volatility level, which a multiplicative time difference must
  and an additive error would not.** At the same 31 days the gap is +0.60 on SPY at
  an IVM of 13.5, +1.80 on TSLA at 42.1, and +2.21 on USO at 54.8.
- **It shrinks with maturity in the right way.** 23/252 against 31/365 is a 7.5%
  difference; 48/252 against 66/365 is 5.3%; the measured gaps fall from +1.80 to
  +1.29 on TSLA and +2.21 to +1.01 on USO.
- **The binomial does nothing**, which is the test HANDOFF 17 asked for. `--american`
  prices a Cox-Ross-Rubinstein tree on spot with the carry the printed forward
  implies, and moves TSLA's one-month gap from +1.80 to +1.80. It must: an American
  call on a name paying no dividend is a European call, and the gap was never
  larger on puts.

The printed forward is a second-order refinement, not the story. Swapping IFwd for
the forward implied by Bloomberg's own call and put mids mostly removes the
call-against-put asymmetry (on USO's October block, calls +0.94 and puts -1.01
become +0.38 and -0.24) and barely moves the pooled median.

**SPY is measurable here although it was not before.** The cross-check above could
match only 14 SPY contracts because the free feed's strike grid and Bloomberg's do
not overlap on a dollar-spaced name. This test never leaves the export: it compares
Bloomberg's IVM to Bloomberg's own bid and ask, so all 40 out-of-the-money contracts
count, on two expiries.

**Honest limits.** Three symbols, two expiries each, one day. 252 is estimated from
the data, not read off a Bloomberg document, and the estimate spans 248 to 256. The
claim is that the divisor is stable on business days and unstable on calendar days,
and that 252 is squarely inside the estimated range - not that the vendor's source
code has been read. A longer-dated pull would sharpen it: the two clocks converge as
maturity grows, so a two-year expiry is the place the explanation could fail.

**What it changes for H3: nothing, and that is the point.** `modelfree.py` integrates
out-of-the-money prices and never reads an implied volatility, so a volatility clock
cannot reach the 0.59-point residual against Cboe. What it does change is what may be
said about the `iv` column: it is not wrong, it is on a calendar clock, and it must
never be compared to a business-clock number without converting one of them.

Bloomberg figures: Source: Bloomberg Finance L.P.

## The day count replicated on a second day, 16 September 2026

A second export set (SPY, TSLA, USO) was pulled at 19:00 UTC on 16 September. It
is an independent day, and **SPY carries 221 strikes** rather than the 40 that
made it unmeasurable before.

| | cal | bus | n | IVM | gap 365 | gap 252 | cal div | bus div |
|---|---|---|---|---|---|---|---|---|
| SPY 16-Oct | 30 | 22 | 133 | 16.2 | +0.63 | +0.06 | 341.7 | 250.6 |
| TSLA 16-Oct | 30 | 22 | 50 | 43.6 | +1.55 | -0.08 | 344.8 | 252.9 |
| TSLA 20-Nov | 65 | 47 | 50 | 45.3 | +0.99 | -0.14 | 350.6 | 253.5 |
| USO 16-Oct | 30 | 22 | 75 | 53.6 | +1.90 | +0.25 | 340.5 | 249.7 |

**Pooled over both days: 10 blocks, 546 out-of-the-money contracts, 3 symbols.**
Median gap **+1.15** volatility points on a 365 calendar clock, **+0.07** on a 252
business clock.

The discriminant is now a regression rather than an eyeball down a column. **A
convention is a constant**, so whichever divisor moves with maturity is the
artefact:

| divisor | median | distance from its nominal | slope per day of maturity | t | verdict |
|---|---|---|---|---|---|
| calendar | 341.7 | **-23.3 from 365** | +0.2307 | **+3.09** | drifts; not a constant |
| business | 250.8 | **-1.2 from 252** | +0.0561 | +1.19 | flat; consistent with a convention |

The calendar divisor drifts significantly with maturity and lands 23 points away
from 365. The business divisor is flat within noise and lands 1.2 points from 252.
That is as clean a separation as this data can produce.

**What it does not settle.** Every block is still 30 to 66 days. The two clocks
converge as maturity grows, so the long-dated pull remains the test that could
break this, and it remains the first ask in `BLOOMBERG-MONDAY.md`. The thin 14 Sep
export reached 858 days on five strikes and did *not* show the gap vanishing; that
is not evidence, and it is not resolved.

**A cost worth recording.** The recorder did not run on 16 September - the
scheduled trigger was dropped - so there is no free-feed snapshot for that day and
**the 221-strike SPY export could not be matched contract by contract.** SPY's feed
quality is therefore *still* unmeasured, which is exactly what that pull was for.
The day-count test survived only because it is internal to the export and needs no
free-feed data. `panel_health.py` now fails on a missed trading day so this is
caught the same day rather than discovered later.

Bloomberg figures: Source: Bloomberg Finance L.P.

## Multiple testing, pre-registered 2026-09-16 — before the series exists

H1 had FDR control added *after* it was tested, which is logged there and is the
weaker form. H3 has no series yet, so the correction goes on record first.

H3a is a claim about a **family**: the mean absolute gap across five benchmarked
underlyings. H3c regresses the gap on the volatility level, again across five. Any
report of the form "the estimate tracks the index on k of the five" is a count over
five tests, and a per-test threshold does not protect a count.

**Registered now:** when H3 is tested, per-underlying p-values are reported with
**Benjamini-Hochberg FDR control at q=0.05** across the five pairs
(`analyze.benjamini_hochberg`), beside the raw values, and the corrected count is
the one quoted. Five is a small family and the correction will be mild; that is
not the point. The point is that it is on record before the numbers are, so it
cannot be chosen to suit them.

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
