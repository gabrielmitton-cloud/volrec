# H3 — A model-free variance estimate built from free retail-grade option data reproduces the published Cboe index

**Registered:** 2026-09-12, after the estimator was built and before any series
exists to test it on. The single-day calibration below is reported honestly as
calibration, not as a test of the hypothesis.
**Status:** registered. Calibrated on one day. **The series began 14 Sep and has
3 days as of 17 Sep** - see "The series so far". Not yet long enough to test H3a.
Cross-checked against Bloomberg 15-16 Sep; the volatility gap is identified
as a day-count convention and does not touch the estimator. **Bloomberg stated
ACT/252 in writing on 23 Sep; at 21 months a one-point gap remains that is not the
clock** - see "The day count, stated by Bloomberg and tested at 21 months". **H3c's
mechanism is Jiang & Tian's (2007)** - see the prior-art section of 23 Sep. **The test of the wide
prediction was fixed and pre-registered on 18 Sep, before any wide data** - see
"How the prediction is tested".
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

## The series so far, 17 September 2026 - first run on accumulated data

`modelfree.py` had not been run since the 11 September calibration. Run on the
three recorded days (14, 15, 17 Sep; 16 Sep was lost to a dropped scheduled run):

| underlying | n | mean gap | min | max |
|---|---|---|---|---|
| GLD | 2 | +0.04 | -0.19 | +0.26 |
| IWM | 2 | +0.32 | +0.27 | +0.38 |
| QQQ | 2 | -0.18 | -0.21 | -0.16 |
| SPY | 2 | -0.10 | -0.18 | -0.01 |
| **USO** | 2 | **-2.93** | **-3.56** | -2.31 |

Pooled mean gap **-0.57** volatility points over n=10. **Mean absolute gap 0.75**,
against H3a's registered threshold of 1.0. 17 September computed on our side but
Cboe had not published that day's closes at the time of the run, so it contributes
no gap yet; AAPL, NVDA and TSLA have no Cboe index and never will.

**H3a is passing, and one underlying is carrying it.** USO contributes 5.87 of the
7.53 total absolute gap - **78% of the error from one of five underlyings** - and
it is getting worse: -1.84 at calibration, then -2.31, then -3.56.

**This is H3c happening in real time, and it is a risk to H3a.** A fixed +/-30%
band is not a fixed amount of information. Measured on 17 September, in units of
each underlying's own 30-day standard deviation:

| underlying | ATM IV | 30d 1-sigma | sigmas covered, down / up |
|---|---|---|---|
| SPY | 13.1% | 3.2% | 11.0 / 8.1 |
| QQQ | 16.9% | 4.2% | 8.4 / 6.3 |
| IWM | 17.3% | 4.2% | 7.9 / 6.1 |
| GLD | 22.7% | 5.6% | 6.3 / 4.6 |
| AAPL | 23.3% | 5.7% | 6.2 / 4.5 |
| NVDA | 31.2% | 7.7% | 4.5 / 3.4 |
| TSLA | 42.3% | 10.4% | 3.3 / 2.5 |
| **USO** | **50.8%** | **12.5%** | **2.8 / 2.0** |

Cboe integrates until it observes two consecutive zero bids, which is effectively
the whole listed chain. This project truncates USO at **two standard deviations on
the upside** and SPY at eight. That is exactly the mechanism H3c predicts, and the
gap column above is what it costs.

**Nothing has been changed in response.** The +/-30% x 40 grid is the frozen
specification and it stays frozen; this is recorded as a measurement, not as a
reason to re-cut anything mid-series. The open question - whether to *record* a
volatility-scaled band while continuing to *analyse* the frozen one - is put to
Gabriel in the session notes and is not decided here.

**Why it cannot wait indefinitely.** Cboe's index history is retrievable back to
1990 from the same CDN, so the benchmark side of any missed day can be backfilled.
Alpaca's free feed serves only the present. **Every day recorded at +/-30% is
permanently a +/-30% day**, so if H3c is ever to be tested rather than asserted,
the wider data has to be recorded while the days are happening.

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
  "Source: Bloomberg Finance L.P." *[Settled 17 Sep 2026: derived figures may be
  published with that attribution; raw Bloomberg data may not enter an open repository.
  See HANDOFF section 17.]*

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

## The day count, reviewed against the literature 16 September 2026 — NOT a discovery

A commissioned research pass was run specifically to ask whether the day-count
result is novel. **It is not, and the framing above is corrected here rather than
left standing.** This section supersedes any reading of the two sections above as
a finding.

### What the literature says, and it is decisive on novelty

Trading-time against calendar-time annualisation of option volatility is textbook
material, not a discovery:

- **French (1984)**, "The weekend effect on the distribution of stock prices,"
  *JFE* — the seminal treatment: variance accrues in trading time while interest
  accrues in calendar time.
- **Hull**, *Options, Futures and Other Derivatives*, and **Natenberg**, *Option
  Volatility and Pricing* — both state the distinction directly. Natenberg
  annualises daily volatility by sqrt(252).
- **Cboe's own methodologies disagree with each other on purpose.** VIX uses
  calendar minutes over 525,600 (= 365 x 24 x 60). **VIX1D uses business time**,
  and Cboe documents that as a deliberate departure.
- **Albers & Kestner (2024)**, *Finance Research Letters* — names the divide
  outright, attributing the VIX day-of-week bias to "the mismatch between the
  options' time to maturity calculated using the market convention (business days,
  i.e. 252 days) and Cboe's method for those indices (calendar days, i.e. 365)."
- **OCC filing SR-OCC-2024-016** (approved SEC Release 34-102203, Jan 2025) — a
  clearinghouse discovered it was running a calendar-day clock for price smoothing
  and a trading-day clock for implied volatility simulation, and filed to align
  them. A regulator treated exactly this mismatch as material.

**So the mechanism is documented at textbook, peer-reviewed and regulatory level.
Do not write this up as a finding.** The correct framing is a *reconciliation
note*: two specific feeds disagree, here is the arithmetic that closes it, here is
why anyone comparing vendor implied volatilities should check the clock first.

*Provenance: these citations come from a commissioned research pass on 16 Sep 2026.
French, Hull, Natenberg and the VIX calendar-minute convention I can confirm
independently. Albers & Kestner, the OCC filing numbers and the VIX1D business-time
claim are* **not independently verified** *and must be checked before any of them
is cited in print.*

### The arithmetic challenge, and why it does not survive

The same research pass argued the magnitude was impossible: a clean 252-vs-365
difference at 30 days gives only about 0.2 volatility points, roughly eight times
smaller than observed, so something other than a day count must be at work.

**That argument rests on a rule of thumb, and the rule of thumb is wrong for these
windows.** It assumes 30 calendar days contain about 21 trading days - the average
density, 30 x 252/365 = 20.7. The windows actually measured contain **22 and 23**,
because of where the weekends fall. One trading day is about 4.5% of T and 2.3% of
volatility, which at TSLA's 43.6 IV is roughly a full point:

| window | T_cal | T_bus | predicted gap at IVM 43.6 |
|---|---|---|---|
| 30 cal / **21** bus (the rule of thumb) | 0.08219 | 0.08333 | +0.30 |
| 30 cal / **22** bus (actual, 16 Sep) | 0.08219 | 0.08730 | **+1.33** |
| 31 cal / **23** bus (actual, 15 Sep) | 0.08493 | 0.09127 | **+1.60** |

*Bloomberg figures: Source: Bloomberg Finance L.P.*

### The test that settles it, with no fitted parameter

Matching one price under two time bases forces
`sigma_365 / sigma_252 = sqrt(T_bus / T_cal)`, so the gap in points is predicted by

    IVM * ( sqrt(T_bus / T_cal) - 1 )

using **each window's own trading-day count**. Nothing here is fitted. Regressing
the observed gap on that prediction across all ten blocks:

| | |
|---|---|
| slope | **1.013** (se 0.131) |
| t against the predicted 1.000 | **+0.10** |
| intercept | +0.08 |
| R-squared | **0.881** |
| mean absolute residual | **0.13** volatility points |

Ten blocks, three symbols, two days, implied volatility from 13.5 to 54.8, maturity
30 to 66 days. The clock alone explains 88% of the variation in the gap with no
free parameter, and the slope is indistinguishable from one.

**This meets the research pass's own stated falsification criterion** - that the gap
must scale with tenor as sqrt(T) to be a clock artifact rather than something else.
It does. `tools/model_gap.py` prints this test on every run.

*Bloomberg figures: Source: Bloomberg Finance L.P.*

### What is still NOT established, and must not be asserted

- **Bloomberg does not publish IVM's day-count basis.** 252 is *inferred from
  prices here*, and no Bloomberg document has been found stating it. The research
  pass found the opposite-leaning observable: an OVME ticket displaying a
  calendar-day "Time to Expiry" counter. A displayed tenor is not the same thing as
  an annualisation basis, but it is a real reason for caution.
- **The Help Desk reply is the missing primary source.** It is asked for in the
  email sent to Marc Vinyard on 16 Sep and is ask 3 in `BLOOMBERG-MONDAY.md`.
  Until it arrives, every statement about Bloomberg's convention is an inference.
- **Every block is 30 to 66 days.** The long-dated pull is still the test that can
  break this, because the two clocks converge as maturity grows.

### One correction to the record

An earlier proposal in this session was to promote "convention, not quality" to a
co-headline of the project. **That proposal is withdrawn.** It was made before this
literature review and it is wrong: the mechanism is textbook. The measurement
stands, the framing does not, and H3's actual claim - that a model-free estimate
built from free data tracks the published Cboe index - is untouched either way,
because `modelfree.py` integrates prices and never reads an implied volatility.

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

## Calibration, 17 September 2026 - the estimator is sound; USO's gap is its wings

`tools/calibrate.py` feeds every instrument an input whose correct answer is known in
advance. The one that matters for H3 is the model-free estimator itself.

**The method is well calibrated.** Priced under a constant volatility, the model-free
variance has a known answer - it IS sigma^2 (Carr & Madan 1998; Demeterfi, Derman, Kamal
& Zou 1999). On the recorder's own +/-30% x 40 grid:

| true vol | error at +/-30% | error at +/-60% |
|---|---|---|
| 13% | +0.19 | +0.18 |
| 23% | +0.11 | +0.10 |
| 42% | -0.00 | +0.06 |
| 51% | **-0.20** | +0.05 |

At most 0.20 points, under half of H3a's 1.0-point budget. So **method error cannot
explain USO's -2.93 gap.** Under a lognormal, truncating a 51% vol name at +/-30% costs
two tenths of a point, because out-of-the-money option prices decay fast.

**What does explain it is USO's actual smile.** The free feed's own recorded implied
volatilities on 17 September show both wings elevated - far downside ~59%, far upside
~64%, against 51% at the money. A smile puts real variance in the tails, and a +/-30%
band cuts it off. Recomputing the estimator on USO's own fitted smile:

| wing assumption beyond the recorded range | variance +/-30% misses |
|---|---|
| flat wings (conservative) | **-1.37** points |
| linear wings, continuing the edge slope, bounded by Lee's moment formula | **-3.24** points |
| **USO's observed gap to Cboe OVX** | **-2.93** (worst -3.56) |

**The observed gap sits inside the bracket.** USO's shortfall against Cboe is the
variance in its wings beyond +/-30%, not poor quotes. A quadratic fit to the smile was
tried first and rejected: it extrapolates to 139% implied volatility at 0.45
moneyness, which is the known failure of quadratic smiles in the wings.

**A falsifiable prediction, stated before the data exists.** When `surface_wide.csv`
has accumulated, `modelfree.py --wide` should move USO's estimate UP by between 1.4 and
3.2 points and leave SPY's essentially unchanged. If it does not, the gap is not tail
truncation and this section is wrong. That is the test the wide band was built for.

## How the prediction is tested — registered 18 September 2026, before any wide data

Written in the early hours of 18 September UTC, when `data/surface_wide.csv` did not
yet exist; the first wide pass fires with the 14:57 UTC surface run that day. Three
defects in the test design were found while preparing it. Each was attacked several
ways, on synthetic worlds with a known answer and on the +/-30% data already recorded.
**No wide quote was looked at**: Alpaca's chain could have been queried that night
for USO's closing quotes out to +/-60%, which would have previewed the result and
made every choice below data-informed. **Nothing here changes the 1.4 to 3.2 bar.**

### 1. The legs: the test was measuring the wrong expiry, and so was H3a

`modelfree.py` interpolated the OUTERMOST expiries present. `surface.py` carries
yesterday's contracts forward for H4, so on 23 of the 39 trading days from 18 Sep to
11 Nov a third, shorter expiry sits in the file. Integrating it broke Cboe's own rule
that the near-term expiry be over 23 days, and the wide pass, which extended the two
expiries nearest 30 days, left a leg the estimate weighted unwidened.

**Coverage**, the share of the 30-day variance on legs the wide pass extended, 18 Sep
to 11 Nov (Friday listings, as all eight names showed on 17 Sep):

| estimate integrates | wide pass: nearest two (was) | wide pass: same rule as estimate (now) | wide pass: every expiry |
|---|---|---|---|
| outermost (was) | 16 of 39 days full, worst 38% | 16 of 39, worst 62% | 39 of 39 |
| **the recorder's own pair (now)** | 39 of 39 | **39 of 39** | 39 of 39 |

**Known-answer test**, through the real `surface.wide_select` and `modelfree` code on
a synthetic USO whose true lift is 1.93-1.94. Measured lift on the weekly cycle:

| layout (days) | 21/28/35 | 25/32 | 24/31 | 23/30/37 | 22/29/36 | worst error |
|---|---|---|---|---|---|---|
| as it was | +1.62 | +1.94 | +1.94 | **+0.63** | +1.51 | **1.30** |
| **as it is now** | +1.94 | +1.94 | +1.94 | +1.93 | +1.93 | **0.000** |

Every Wednesday a true 1.9-point lift would have read 0.63. The defect alone could
have decided the test.

**Interpolation error against a known 30-day variance** (mean over the weekly cycle,
vol points): outermost 0.18 against 0.04 for the recorder's pair on a sloped term
structure; 0.40 against 0.15 with one event day at 3x a normal day's variance; 1.27
against 0.47 at earnings size. The coded rule broke Cboe's 23-day floor on 23 of 39
days; nearest-two in the estimate would break it on 8; the recorder's pair and
Cboe's strict 23-37 day window never do and are identical on every layout here.

**Adopted: one rule in two places.** `modelfree.pick_pair` is `rows_for`'s own pick
(last expiry at or under 30 days, first over it) and `surface.wide_expiries` applies
the same rule to the same expiries. Changing only `modelfree` was tried first. It was
exact through 11 Nov but not on Wed 25 Nov, when the Christmas expiry moves to
Thursday and the file holds 23/29/37 days: the nearest-two tie between 23 and 37 went
to 23, leaving the 37-day leg (15% of the estimate) unwidened. It also left 2 of 39
days short (worst 81%) if an underlying lists month-end expiries. Keeping the
outermost rule and widening every expiry was also rejected: it measures the lift to
within 0.07, but it keeps the Cboe violation and three to five times the interpolation
error, and it needs a recorder change anyway.

**Effect on registered numbers: none on the gap series.** 14 and 15 September hold
exactly two expiries per symbol, so both rules pick the same pair; 17 September had
no Cboe close when this was changed, so no recorded gap moved. `modelfree.py`'s
output was diffed before and after: only the 17 September estimates change - USO
52.51 to 52.82, SPY 15.49 to 15.53, QQQ 20.08 to 19.96, IWM 19.50 to 19.49, GLD 24.66
to 24.69 (and TSLA 46.19 to 44.60, which has no index).

**Guards.** `tools/calibrate.py` checks the measured lift equals the lift with every
expiry widened, to float precision, running the recorder's own `wide_rows_for`. Under
the old rule it fails (Wednesday: +0.089 against +0.626). `pressure_test.py` replays
every trading day to 31 Dec through the frozen `rows_for` and the real
`wide_rows_for`, and checks the two rules agree on all 15,250 layouts of two to four
expiries the window allows.

### 2. The bracket: not reproducible, and the bar stands

The computation behind 1.37 (flat wings) and 3.24 (linear wings) was not committed.
Repeated here by the method described above - each day's own USO smile, priced with
this project's Black-76, integrated with `variance_one_expiry`, 30-day interpolation on
the recorder's pair, lift to the 60% cap | lift to the full tail:

| wings beyond the recorded range | 14 Sep | 15 Sep | 17 Sep |
|---|---|---|---|
| flat | +1.38 \| +1.41 | +1.47 \| +1.50 | +0.93 \| +0.95 |
| linear in vol, edge slope from 3 points | +3.91 \| +46.0 | +2.44 \| +6.47 | +2.03 \| +4.80 |
| linear in vol, 4 points | +2.40 \| +3.14 | +2.08 \| +3.64 | +2.15 \| +8.95 |
| linear in vol, 6 points | +2.25 \| +2.72 | +2.23 \| +2.48 | +1.55 \| +1.78 |
| linear in total variance | +2.23 \| +2.57 | +1.99 \| +2.13 | +1.77 \| +1.99 |
| SVI (Gatheral), Lee-bounded | +2.73 \| +3.84 | +2.39 \| +2.64 | +1.91 \| +4.53 |
| quadratic (rejected above) | +4.10 \| +431 | +4.85 \| +437 | +3.03 \| +430 |

No setup reproduces the registered pair. Flat wings on 17 Sep give 0.56 to 1.12
depending on the expiry used, not 1.37; the nearest to 1.37 is linear total-variance
wings on the old 22/36 pair, and nothing tried gives 3.24. What the capped band can deliver on a fitted
smile runs from 0.93 to about 2.7, central near 2.0. The cap matters little for flat
wings and a great deal for the steeper ones: the full tail on a linear-wing smile is
not identified by the data at all, which is why the wide band has a cap.

**How a reading will be interpreted, stated now:**

| USO mean lift | reading |
|---|---|
| under 0.5 | what a lognormal with no smile gives (+0.25, per `calibrate.py`): the wings carry nothing extra, tail truncation is not the mechanism. **Fail.** |
| 0.5 to 1.4 | **fail against the registered bar.** Consistent with flat-wing truncation on some days, and that is said beside it - the bar is not moved |
| 1.4 to 3.2 | **pass** |
| 2.7 to 3.2 | a pass, but above anything the capped band delivered on a fitted smile: check the zero-bid column before believing it |
| over 3.2 | **fail**, most likely quote contamination in the thin wings rather than variance |

### 3. How the lift is measured

- **Primary, the registered reading.** `modelfree.py --wide` prints the lift for each
  day: wide estimate minus registered estimate, same day, same legs. USO's reading is
  the **mean over every covered wide day from 18 September, never a subset.** First
  reading once three wide days exist (after the Tue 22 Sep run). Every later reading
  uses all days; **the one written up is the reading after the last day of the
  40-day window, Wed 11 Nov.** Stopping early on a good number is not available.
- **Coverage exclusion.** A day where a leg the estimate weights has no wide rows is
  printed, flagged `UNCOVERED` and excluded. The design above makes that count zero;
  if it is not zero, that is itself a finding.
- **The zero-bid sensitivity is a reading aid, not a second hypothesis.** The
  known-answer test found that counting a zero-bid quote at half its ask, as the
  registered estimator does, reads **+0.14 (median spreads) to +0.47 (90th-percentile
  spreads) high**, while Cboe's zero-bid rule reads **0.36 to 0.56 low**, with 6-8 of
  19 wide strikes on a zero bid. The truth lies between the two columns. If 1.4
  falls between them, say the reading straddles the bar.
- **Null controls: GLD and AAPL.** Both are widened only to 33%, and every smile
  fitted to their own quotes predicts a lift of 0.03 to 0.14. **Each must stay under
  0.3** (largest prediction plus the +0.14 zero-bid inflation, rounded). A control
  over 0.3 means the pipeline makes lift that is not tail variance, and USO's reading
  cannot be taken at face value whatever it is.
- **Dose ordering.** Mean lift ordered {USO, TSLA} above NVDA above {AAPL, GLD}. Every
  fitted smile agrees on this. USO against TSLA flips with the smile method, so it is
  not predicted.

Predicted lift at each name's own band, 17 Sep, flat / linear total variance / SVI:
USO +0.93/+1.77/+1.91, TSLA +0.52/+1.31/+2.49, NVDA +0.27/+0.85/+1.50, AAPL
+0.03/+0.07/+0.05, GLD +0.04/+0.05/+0.05.

### 4. SPY's half of the prediction holds by construction

SPY's band is max(30%, 5 sigma) and 5 sigma is about 19%, so SPY is never widened and
its `--wide` estimate is identical to its registered one. "Leave SPY essentially
unchanged" cannot fail and is **not evidence either way**. Recording SPY wide as a
proper control was assessed and rejected: SPY's own smile predicts +0.07 to +0.24 at a
45% band, because its put skew holds real variance beyond -30%, so it would not be a
clean null, and it would need a recorder change. GLD and AAPL do the job instead.

## The first wide day, and the wings against Bloomberg — 18 September 2026, AFTER data

Everything in this section was seen after the first wide file landed. **It changes
nothing registered above.** One wide day is not a reading; the first reading is at
three.

**The series with 17 September.** Cboe published 17 Sep after the leg rule changed, so
that day entered on the new pair. USO read **+0.71**, its first positive gap, after
-2.31 and -3.56 (the old 22/36 pair would have read +0.40). GLD -0.29, IWM +0.28, QQQ
+0.00, SPY +0.09. Over n=15 the mean absolute gap is **0.59** against H3a's 1.0, USO
carrying 74% of it. The premise that USO reads low because of its wings did not hold
on 17 Sep.

**`modelfree.py --wide`, day one** (28d/35d, fully covered): USO +5.25 as registered,
+0.84 under Cboe's zero-bid rule; TSLA +1.66 on both; NVDA +0.76 on both; AAPL +0.02
(null control, under 0.3). GLD recorded no wide rows: its band barely clears 30%, so
that control will be intermittent. Only USO's two columns differ, because only USO
has zero bids in its wings (21 of 82 wide rows).

**The wings against Bloomberg.** USO OMON pulled 18:25 UTC, 30 minutes after the
recorder's 17:55 snapshot, 16 Oct expiry, 144 strikes from 0.03x to 2.04x spot.
`tools/bloomberg_compare.py` now matches the wide file too:

| | n | mid gap, fraction of a spread | zero bid on both | on one feed only |
|---|---|---|---|---|
| registered band, 108-200 | 97 | 0.25 | - | - |
| put wing, 64-105 | 18 | **0.07** | 13 | 1 (Bloomberg) |
| call wing, 205-245 | 9 | **0.40** | 0 | 0 |

**The free feed's wing quotes are as good as Bloomberg's**, including where the
quotes are empty: 13 of 18 far puts had no bid on either feed. This is the first
measurement of feed quality in the tails, and the first day USO passes the price
gate (it failed at 0.64 on 15 Sep).

**The lift for this expiry alone, from each vendor's own prices on the same strikes:**

| | free feed | Bloomberg | Bloomberg's whole chain beyond the cap |
|---|---|---|---|
| as registered (zero bid counted at half the ask) | +5.28 | +4.91 | +65.9 |
| Cboe zero-bid rule | +0.94 | +0.85 | +0.27 |

Both vendors show it, so **the contamination is the estimator's, not the feed's.** Far
puts with no bid carry asks of up to about two dollars on options worth pennies, and
the registered estimator counts half of that ask as the price, at the low strikes the
1/K^2 weight favours most.

**A correction to this morning's section.** The known-answer test put the
as-registered inflation at +0.14 to +0.47. On real USO wing quotes it is about **+4.1
to +4.3**. The simulation's quote model (half-spread 0.05 plus 2.5% of price) badly
understated real far-OTM asks. The direction it predicted held; the size did not.
This is recorded as wrong rather than quietly dropped.

**What it does and does not change.** The primary reading stays as registered. The
interpretation grid registered this morning already covers this case - over 3.2
reads "fail, most likely quote contamination; check the zero-bid column" - and day
one is exactly that. On the same grid, the zero-bid column would sit in the 0.5-1.4
band. **H3a's registered estimate is not affected**: applying the zero-bid rule
inside +/-30% moves every benchmarked gap on every day by 0.03 points or less.

**Also from the pull.** A third day of the day count: business divisor **252.0**, gap
+0.82 on 365 and +0.00 on 252. Volume on matched contracts, free 18,112 against
Bloomberg 25,614; on 15 Sep they agreed within 3%. A 30-minute gap explains some of
that and probably not all; not investigated.

*Bloomberg figures: Source: Bloomberg Finance L.P.*

## The first registered reading of the wide prediction — 23 September 2026

Read exactly as pre-registered: USO's as-registered lift, mean over every covered wide
day (18, 21, 22 Sep; all three covered, no `UNCOVERED` day).

| | 18 Sep | 21 Sep | 22 Sep | mean | reading |
|---|---|---|---|---|---|
| USO, as registered | +5.25 | +9.96 | +13.01 | **+9.41** | **OUTSIDE 1.4-3.2: over 3.2, "fail, most likely quote contamination"** |
| USO, Cboe zero-bid rule | +0.84 | +0.92 | +1.26 | +1.00 | the other side of the bracket; 0.5-1.4 band |
| TSLA | +1.66 | +1.63 | +1.66 | +1.65 | no zero bids, both columns equal |
| NVDA | +0.76 | +0.69 | +0.78 | +0.75 | |
| AAPL (null control) | +0.02 | +0.09 | +0.02 | +0.05 | **under 0.3: ok** |

GLD recorded no wide rows on any day, so the GLD control has not run. The dose ordering
{USO, TSLA} > NVDA > {AAPL, GLD} holds on both columns. **This is the first reading,
not the written-up one**, which is the reading after Wed 11 Nov.

**What it says.** The contamination the grid anticipated is the whole story of the
as-registered column, and it is growing (5, 10, 13) while the zero-bid count stays at
21-22, so the size of the stub asks matters, not only their number. The zero-bid
column is not clean either: on 22 Sep Cboe's stop rule truncated USO *inside* the
registered band at one-sided stubs (H5, "The second wide pull"). A variant that skips
zero bids without stopping closes USO's gap to OVX on all three days; it was defined
after seeing them, so it is registered as H5e and judged only from 23 Sep.

**H3a's own series, now 30 readings over six days:** mean absolute gap **0.53**
against the 1.0 bar, pooled mean -0.25, USO carrying 61% of the error. USO's registered
gap has settled at -1.18, -1.09, -1.00 since 18 Sep. **IWM reads positive on all six
days** (mean +0.42), against H3b's predicted negative sign - worth watching, since H3b
fails on a positive mean gap.

## The day count, stated by Bloomberg and tested at 21 months — 23 September 2026

**Stated in writing.** Asked through Live Help on 23 Sep, Bloomberg's help desk
replied that OMON's IVM solves on business time annualised **ACT/252**, with
weekends and exchange holidays excluded, intraday precision to expiry, and no
setting to change it in OMON. The calendar ACT/365 convention applies in OVME and in
OVDV's BVOL surfaces instead, which is why those can disagree with OMON on the same
contract. Documented at `LPHP OMON:0:1 4373105` ("Migration to Business Day
Convention", which dates OMON's move to business days to **June 2023**) and in
`HELP OMON`. **252 is no longer an inference from prices.** Two consequences worth
keeping: an OMON implied volatility from before mid-2023 is on a different clock, and
an OVME or OVDV number is on this project's clock, not OMON's.

**Tested at 21 months, the pull that could falsify it.** TSLA OMON on 23 Sep, three
expiries, `tools/model_gap.py` (out-of-the-money contracts, gaps ours minus IVM):

| expiry | calendar / business days | n | gap on 365 | gap on 252 | business-day divisor | American (CRR) |
|---|---|---|---|---|---|---|
| 23 Oct 2026 | 30 / 22 | 72 | +1.58 | **+0.08** | 251.2 | |
| 30 Oct 2026 | 37 / 27 | 75 | +1.60 | **+0.23** | 249.7 | |
| 16 Jun 2028 | 632 / 436 | 94 | +0.94 | **+0.95** | **241.2** | +0.90 |

(USO on the two October expiries agrees: -0.43 and -0.07 on 252.)

**Read as the rule written before the pull said to** (`BLOOMBERG-MONDAY.md`, ask 1:
at long maturity the two clocks converge, so the gap "should nearly vanish. If it
does not, the day count is not the whole story"): **at 21 months it does not vanish.**
The clocks converge exactly as predicted (+0.94 against +0.95), but a gap of about
one point remains that is not the clock. Early exercise is not it (+0.90). So:

- **At the recorder's maturities (21-45 days) the day count is the whole story**, and
  now documented: the solved time reproduces Bloomberg to a fraction of a day (22.1
  business days against 22; 27.2 against 27).
- **At long maturity it is not.** Something that grows with maturity also separates
  the two - the forward, rate or borrow inputs inside Bloomberg's solve are the
  candidates; not identified here.

**After the fact, labelled, and not a conclusion.** Bloomberg's solved time on the
2028 contract is 455.6 business days against 436 trading days, and would sit close to
452 plain weekdays (holidays not removed). But the same contract on the thin 14 Sep
export implied 523 days, and no day count can move 68 days in nine; and the desk says
holidays are excluded. The holiday reading is therefore not supported. The next
bounded step is a question, not a search: ask the desk which forward, rate and borrow
IVM uses on a long-dated TSLA contract.

**Consequence for H3: none.** `modelfree.py` integrates prices, never an implied
volatility, and every expiry it uses is inside 45 days.

**The desk's second reply, 24 Sep 2026** (Bloomberg Support, London, by email, to the
four-part question in `BLOOMBERG-MONDAY.md` ask 3). Paraphrased:

- **Forward:** IVM uses the market-implied forward from put-call parity, the IFwd in the
  expiry header, carrying the rate plus implied carry (dividends, borrow). **This is the
  forward `model_gap.py` already uses**, so the forward is not the residual.
- **Rate:** R is the rate for that expiry, interpolated from the curve in `OPDF`, not one
  flat rate. **`model_gap.py` uses each block's own R**, so the rate is not it either.
- **Model:** European-style options on Black-Scholes; **American-style on a
  finite-difference model with early exercise.** TSLA's options are American (**confirmed
  24 Sep in OMON's `XTyp` column**). `model_gap.py --american` approximates this with a
  300-step tree and moved the 21-month gap by 0.04, so a model difference is narrowed
  but not ruled out: a finite-difference solver and a tree on a carry backed out of IFwd
  can differ at 21 months.
- **Day count:** business time, weekends and market holidays excluded, but **the desk
  could not confirm that 2027-28 holidays are populated**, and pointed to `GIV`
  (Actions, View Calc Inputs), which shows the exact time to expiry used for one contract.

**What this leaves.** Two candidates: the time to expiry Bloomberg actually uses (the
solve implies 455.6 business days against 436 trading days) and the American solver.
`GIV` shows both for one contract, so the next step is to read one screen, not to infer:
TSLA 16-Jun-28 C380 and P300, time to expiry, rate, carry and model as shown.

**The GIV screen, read 24 Sep - and where this stops.** Gabriel photographed GIV's
calculation-inputs panel for the 16-Jun-28 C380 (a call on a stock with no dividend,
so early exercise cannot matter and it isolates forward and clock). It labels the model
Black-Scholes and prints time to expiry in CALENDAR days and hours, to the 16:00 close.
Its printed inputs do NOT reproduce its own implied volatility under Black-Scholes or
Black-76, on calendar or ACT/252 time: its printed forward and underlying imply a carry
above its printed rate, while it prints zero dividend and borrow. On the documented
convention the residual on that one contract is about one point, the same as the
export's. (Raw panel values stay outside the repository.)

A test on the 94 contracts of 23 Sep then separates the two remaining causes, because a
forward error moves calls and puts in OPPOSITE directions and a clock error moves them
the same way. At 21 months, on 252: **calls +0.92 (n=58), puts +1.47 (n=36) - the same
sign.** Moving the forward to cancel the median makes the split worse (calls -0.24, puts
+2.25). At one month both types sit near zero (23 Oct +0.04 / +0.15; 30 Oct +0.31 / -0.17).

**Conclusion, after the fact and bounded:** the long-maturity residual is not the
forward and not the rate (both confirmed to be Bloomberg's own); it acts like a time or
volatility-scale difference common to every option, with about 0.5 more on puts - the
direction early exercise would push, though a 300-step tree did not reproduce it. It is
**not identified**, and this project stops here: the terminal's own screen is
internally inconsistent, nothing registered depends on it (the estimator uses prices,
never an implied volatility, and no expiry past 45 days), and chasing it further would be
searching. Stated in any write-up as an open reconciliation item at long maturity.

*Bloomberg figures: Source: Bloomberg Finance L.P.*

*Bloomberg figures: Source: Bloomberg Finance L.P.*

## Prior art, read 23 September 2026 — H3c's mechanism is Jiang & Tian's, NOT new

Jiang & Tian (2007), "Extracting Model-Free Volatility from Option Prices: An
Examination of the VIX Index", *Journal of Derivatives* 14(3), 35-60, read via
Pepperdine interlibrary loan (a private-study copy, kept outside this repository).
The same check that corrected the day count applies here, and it lands the same way.

- **Truncation bias that grows with volatility is their result.** With a fixed strike
  range, their simulated error rises steeply as volatility rises, almost all of it
  truncation, and they give a rule of thumb (from Jiang & Tian 2005): truncation is
  negligible once the range reaches **three standard deviations** either side of spot.
  That is H3c's mechanism, and the "reusable finding" under "Why this is worth doing"
  and on the public site. It must be credited as theirs.
- **Their errors have a sign each:** truncation biases the estimate down, a coarse
  strike grid (discretization) biases it up, and truncation dominates in practice (SPX,
  1996-2004). H3b's predicted negative gap is the truncation side of that.
- **This project's calibration agrees with them and adds nothing new to the theory:**
  a lognormal truncated at 2.4 sigma costs 0.20 points here, small as their simulation
  says; USO's gap is its smile, and they note that flat extrapolation beyond the listed
  strikes understates a smile for the same reason.
- By their rule, at 30 days the registered +/-30% band covers three standard deviations
  only up to about 35 volatility points, and the +/-60% wide band up to about 70
  (computed here from their rule, not stated by them). USO and TSLA sit near 50.

**What remains this project's:** the measurement - a free, indicative feed against the
published index, per underlying, day by day - and H3c as a test of their mechanism on
that data, not as a discovery. H3c stays registered exactly as written.

## Adjustment log

- **2026-09-18, before any wide data existed — the pair of expiries integrated, and the
  pair widened.** `modelfree.py` now integrates the pair the recorder picked
  (`pick_pair`, `rows_for`'s rule) instead of the outermost expiries present, and
  `surface.py`'s wide pass extends exactly that pair (`wide_expiries`). This conforms
  the code to the frozen specification ("Cboe's variance calculation", "two expiries
  per day"): the outermost rule broke Cboe's 23-day near-term floor on 23 of 39 days.
  No gap in the series moved; see "How the prediction is tested", part 1. The
  registered recording path (`rows_for`, `chain`, `append`, `open_interest`) is
  unchanged, compared as syntax trees against the previous commit.

- **2026-09-17, after three days of the series existed — a RECORDING change, not an
  analysis change.** High-volatility names are now ALSO recorded beyond +/-30%, into a
  separate file, `data/surface_wide.csv`. **H3's registered specification is untouched**:
  the estimator still integrates +/-30% x 40 from `data/surface.csv`, and every H3 number
  is reproduced byte-for-byte - verified by diffing `modelfree.py`'s output before and
  after the change.

  *Why.* On three days USO carried 78% of H3's absolute error and was worsening (-1.84,
  -2.31, -3.56). Measured in each underlying's own 30-day standard deviation, the fixed
  band covered SPY's downside to 9.5 sigma and USO's to 2.4. Downside is what matters: the
  model-free integrand weights each strike by 1/K^2, so low strikes dominate. And it could
  not wait - Cboe's index history is retrievable back to 1990, but Alpaca's free feed
  serves only the present, so a day recorded at +/-30% is permanently a +/-30% day.

  *Correction, the same day, after calibrating.* The sigma-coverage argument above is
  **incomplete, and on its own would have been wrong.** Under a lognormal, truncating at
  2.4 sigma costs only 0.20 points - see "Calibration" above - so low sigma coverage does
  not by itself produce a 3-point gap. What does is USO's **smile**: its wings carry real
  variance that a lognormal does not have. The decision stands and is now better
  justified - the variance beyond +/-30% on USO's own smile is 1.37 to 3.24 points,
  bracketing the observed 2.93 - but the reason is the shape of the distribution, not the
  sigma count. The sigma heuristic pointed the right way for the wrong reason.

  *The rule.* Band = max(30%, 5 sigma of the 30-day move), capped at 60%. Five sigma is
  where the names that already track Cboe sit (SPY, QQQ, IWM, GLD all within 0.35 points).
  Sigma is on the 30-day horizon because that is what the estimate and the index target;
  a first attempt sized it on the longest expiry present, which included stale expiries
  brought in by carry-forward, and inflated every band. After the change every name's
  downside is at least 6 sigma:

  | | band | downside before | after |
  |---|---|---|---|
  | USO | 60% | 2.4 sd | 6.3 sd |
  | TSLA | 60% | 2.9 sd | 7.5 sd |
  | NVDA | 45% | 4.0 sd | 6.6 sd |
  | GLD, AAPL | 33% | ~5.4 sd | 6.1 sd |
  | SPY, QQQ, IWM | 30% | 7.2-9.5 sd | unchanged |

  *What it enables.* `python modelfree.py --wide` integrates both files. **H3c - that
  truncation bias scales with volatility - becomes testable directly:** if widening closes
  USO's gap and leaves SPY's alone, the mechanism is shown rather than inferred. That
  comparison is a sensitivity and is labelled as one; it never replaces the registered
  estimate, and H3a is still judged on +/-30%.

  *How the registered surface is protected.* The wide pass runs only after `surface.csv`
  is written to disk. Its fetch and row-building are duplicated rather than shared, so the
  registered functions are byte-identical (checked by comparing their syntax trees). It
  catches every exception including `SystemExit`, because a non-zero exit would skip the
  workflow's commit step and lose `surface.csv` with it. `pressure_test.py` asserts all of
  this, plus that the two files never overlap: `surface.csv` holds nothing beyond +/-30%,
  `surface_wide.csv` nothing inside it.

- **2026-09-12, before any series existed.** Strike band widened from +/-10% x
  20 to +/-30% x 40 on the calibration above. Recorded rather than silently
  applied: the advised configuration was +/-10%, and it was changed because it
  was measured to be badly truncated, not because a result was disliked.
