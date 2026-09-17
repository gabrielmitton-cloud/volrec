# H4 — Delta-hedged gains are negative, vary across the strike surface, and relate to where volume sits

**Registered:** 2026-09-13, **before `data/surface.csv` contains a single row.**
The surface begins recording on 2026-09-14. This file exists specifically so
that the predictions below are on record before any of the data that tests them
exists, which is the only thing separating a prediction from a description.
**Status:** registered 2026-09-13. **First run 2026-09-16 on the 14-15 September
pair - see "First run" below. One overnight period: descriptive, not a test.**
The hedge ratio's model dependence was measured on 2026-09-16; every direction
survives, see "The delta is the vendor's".
**Sample:** `data/surface.csv`, via `hedged.py`.

## Why this is registered now rather than after the first run

`hedged.py` already prints delta-hedged gains broken out by moneyness bucket and
by volume tercile. Those breakdowns answer a question. Running them first and
writing the hypothesis afterwards would make this file a summary of results
dressed as a prediction, which is precisely what `hypotheses/README.md` exists
to prevent. So the predictions go down first, with their directions, while the
file they apply to is empty.

## Honest position relative to the literature

**This is close to a replication, and should be described that way.** The
novelty is the data, not the question: a single name, own-collected, at zero
budget, with volume and open interest per contract. The findings below are all
predicted *from published work*, so confirming them is a validation of the
pipeline more than a discovery, and failing to confirm them is more likely to
indicate a problem here than a new fact about markets.

- Bakshi & Kapadia (2003, RFS 16(2) 527-566): delta-hedged gains on index
  options are significantly negative, and the underperformance is **smaller
  away from the money**.
- Bollen & Whaley (2004, JF 59(2) 711-753): delta-neutral writing abnormal
  returns **decrease monotonically across exercise prices**.
- Yuan, Liu, Chen & Hu (2024, *NAJEF* 74, 102233): option trading volume
  **negatively and significantly predicts** the cross-section of delta-hedged
  option returns, across moneyness and maturity.

## The predictions

**H4a — the baseline.** Mean delta-hedged gain, scaled by spot, is **negative**
across the pooled sample. Under this project's convention a negative hedged gain
means the option buyer lost, which is a positive variance risk premium.

**H4b — shape across the surface.** The gain is **most negative at the money**
and **less negative in both wings**, following Bakshi & Kapadia. Stated as an
ordering: `at the money` is more negative than both `OTM put` and `OTM call`,
which are in turn more negative than the two deep buckets.

**H4c — volume.** The **high-volume tercile shows a more negative mean hedged
gain than the low-volume tercile**, following Yuan et al. Directional, stated in
advance.

**H4d — the one that is actually mine.** Because this project records volume and
open interest per contract, the two can be separated. **Prediction: volume
carries the relationship in H4c and open interest adds little once volume is
controlled for**, because volume is flow, meaning active demand, while open
interest is an accumulated stock that includes stale positions. I have found no
published work separating them this way and am not claiming it is unexplored,
only that I have not found it.

## First run, 16 September 2026 - one overnight period

`hedged.py` on the only consecutive pair that exists, 14 to 15 September. 1,138
contracts on the first day, 1,602 on the second, 1,120 carried over, 98% retained.
998 hedged runs across 8 underlyings. Risk-free 3.910% (DGS1MO).

| bucket | n | mean scaled | t | % negative |
|---|---|---|---|---|
| deep OTM put | 310 | +2.13bp | 2.07 | 55% |
| OTM put | 144 | +3.45bp | 3.30 | 49% |
| at the money | 124 | +1.79bp | 1.89 | 48% |
| OTM call | 136 | +3.03bp | 3.58 | 34% |
| deep OTM call | 284 | +1.44bp | 1.19 | 40% |

| volume tercile | n | mean scaled | t | median volume |
|---|---|---|---|---|
| low | 340 | +4.43bp | 3.77 | 1 |
| mid | 328 | +1.87bp | 2.13 | 23 |
| high | 330 | +0.24bp | 0.50 | 475 |

Pooled: n=998, mean +2.21bp of spot, t=4.23.

**Read against the predictions, and most of them are on the wrong side.**

- **H4a predicted negative hedged gains.** The sign is positive: the option buyer
  gained over this one night, which is a *negative* variance premium. Contradicted on
  this pair.
- **H4b predicted the most negative gains at the money, less negative in the wings.**
  The ordering is not there either.
- **H4c predicted high-volume contracts more negative than low-volume.** This is the
  one that holds directionally: +0.24bp against +4.43bp, a monotone fall across the
  three terciles, and the only tercile whose t-statistic is not distinguishable from
  zero is the high-volume one.
- **H4d, volume against open interest, is untouched** until there are enough days to
  control one for the other.

**The next pair does not exist.** Both recorders were dropped on 16 September, so the
series runs 14, 15, then a hole. Everything below still rests on that single pair.

**This is one overnight period.** Every run shares the same two dates, so the pooled t
of 4.23 is descriptive and nothing more, exactly as the file said before the data
existed. A single night of TSLA moving is enough to flip every sign here. No adjustment
has been made to any threshold or bucket definition, and none should be until the
series is long enough for the date-clustered test in HANDOFF 14.3.

## The delta is the vendor's: what that costs, 16 September 2026

H3 flagged the exposure and HANDOFF 17 made measuring it a bounded action.
`hedged.py` shorts `delta` shares, `delta` is whatever the free feed recorded, and
the free feed's greeks come from a model this project does not control. So the same
998 runs were re-hedged with a delta from this project's own model -
`tools/delta_model.py`, Black-76 on a put-call-parity forward, which is
`modelfree.py`'s convention and therefore the one already frozen in H3.

**First, what the vendor's model actually is.** Forcing the forward to `S e^{rT}` -
no dividend, no borrow - reproduces the vendor's delta to a median of 0.0000 at every
one of the eight underlyings and a mean absolute difference of 0.0007, against 0.0067
for the parity forward. That identifies the assumption rather than guessing at it:
**the free feed's greeks carry no dividend and no borrow.** It is why the whole
disagreement sits on the payers - SPY -0.017, IWM -0.019, QQQ -0.004 at the median -
and vanishes on GLD, USO, TSLA and NVDA, which pay nothing. SPY goes ex-dividend on
18 September, inside both recorded expiries.

**Second, what it does to the buckets.** 970 of the 998 runs price under both deltas;
the rest are excluded so that only the delta differs.

| bucket | n | vendor | ours | shift | t vendor | t ours |
|---|---|---|---|---|---|---|
| deep OTM put | 296 | +2.00bp | +1.94bp | -0.06 | 2.00 | 1.88 |
| OTM put | 144 | +3.45bp | +3.09bp | -0.36 | 3.30 | 2.94 |
| at the money | 124 | +1.79bp | +1.37bp | -0.41 | 1.89 | 1.45 |
| OTM call | 133 | +2.69bp | +2.17bp | -0.52 | 3.22 | 2.71 |
| deep OTM call | 273 | +0.52bp | +0.21bp | -0.30 | 0.43 | 0.18 |

| volume tercile | n | vendor | ours | shift | t vendor | t ours |
|---|---|---|---|---|---|---|
| low | 342 | +3.67bp | +3.28bp | -0.39 | 3.21 | 2.82 |
| mid | 305 | +1.82bp | +1.48bp | -0.34 | 2.13 | 1.73 |
| high | 323 | -0.00bp | -0.11bp | -0.11 | -0.01 | -0.25 |

Pooled: +1.87bp at t=3.67 on the vendor's delta, +1.58bp at t=3.08 on ours.

`--forward regress`, which fits the parity line across the near-the-money strikes
instead of trusting the single best-agreeing one, is reported as a sensitivity
because the +/-30% x 40 grid steps about 12 dollars on SPY and one noisy `C-P`
then moves the forward. It agrees: 989 common runs, shifts between -0.53 and
+0.12bp, pooled +2.08bp to +1.90bp.

**Read against the three predictions, nothing changes.**

- **H4a** was contradicted on the vendor's delta and is contradicted on ours. The
  pooled mean stays positive, +1.58bp, and no bucket changes sign.
- **H4b's** ordering was absent and stays absent. Every bucket moves the same way
  and by a similar amount, which is what a hedge-ratio change should do.
- **H4c** holds directionally under both deltas: the fall across terciles stays
  monotone, and the high-volume tercile is still the only one not distinguishable
  from zero.

**So the first run's reading is not an artifact of the vendor's delta - but the
model dependence is real and belongs in any write-up.** The shifts run to 0.52bp
against bucket means of 0 to 3.5bp, so on the order of 10 to 25% of the effect size,
concentrated on the dividend-paying ETFs. Two statements follow, and both should be
made rather than one: the direction of every H4 result survives the swap, and no H4
number is good to better than roughly half a basis point until the hedge ratio is
computed rather than recorded.

Nothing here adjusts a threshold, a bucket boundary, or a tercile rule.
`hedged.py`'s own output is unchanged: `hedged_gain` gained an optional
`delta_of` argument that defaults to the recorded delta.

## What the tests are worth, 16 September 2026

`analyze.py --simulate-surface` does for H4 what `--simulate` already did for H1:
builds a world where the hedged gain is zero by construction and counts how often
each accept criterion rejects anyway. Calibrated on the 14-15 September pair -
contract noise sd 16.30bp within an underlying-day, the shared underlying-day shock
sd 3.83bp, intraclass correlation 0.052.

False rejections at a nominal 5%, 400 replications:

| day pairs | pooled over contracts | per underlying-day | per date | tercile contrast |
|---|---|---|---|---|
| 1 | 47.8% / 67.5% | 3.5% / 26.0% | n/a | 5.2% / 5.2% |
| 5 | 45.0% / 69.2% | 4.0% / 24.0% | 3.5% / 5.0% | 3.8% / 3.8% |
| 20 | 46.5% / 73.2% | 4.5% / 30.0% | 4.2% / 4.0% | 3.5% / 3.5% |
| 40 | 45.8% / 64.0% | 3.5% / 23.2% | 3.8% / 4.0% | 3.8% / 3.8% |

Each cell is `rho_market = 0` / `rho_market = 0.3`, where rho is how much of a day's
shock is common to all eight underlyings. One day-pair cannot estimate it, so it is
swept rather than assumed.

**Three things follow, and the first is the one that matters.**

1. **The pooled t over contracts is not a test and never becomes one.** It rejects a
   true null about half the time with no market factor and two thirds of the time
   with one, and *more days make it worse*, because they add correlated rows rather
   than independent ones. The first run's t=4.23 was already labelled descriptive;
   this puts a number on how descriptive.
2. **Clustering on the underlying-day is not enough either.** It looks honest at 3.5%
   when underlyings are independent and fails at 23-30% once they are not, which they
   are. Only clustering on date holds across the sweep. That rules out the tempting
   shortcut and confirms HANDOFF 14.3's prescription rather than assuming it.
3. **The contrast is honest at any length**, 3.5-5.2% everywhere, because the shared
   shock cancels inside a difference taken within a day.

**Smallest true effect found 80% of the time:**

| day pairs | H4a level | H4c contrast |
|---|---|---|
| 5 | 4.01bp | 1.63bp |
| 20 | 1.59bp | 0.77bp |
| **40** | **1.04bp** | **0.56bp** |
| 60 | 0.87bp | 0.45bp |

At 40 day pairs, against the one quantity that is assumed:

| rho_market | H4a level | H4c contrast |
|---|---|---|
| 0.0 | 0.66bp | 0.56bp |
| 0.3 | 1.04bp | 0.56bp |
| 0.6 | 1.37bp | 0.56bp |
| 0.9 | 1.61bp | 0.56bp |

**So roughly 40 day pairs is enough for both claims, which is worth knowing before
spending them.** A level effect the size of the one observed (+2.31bp as the mean of
the eight underlyings) would be found most of the time; half that size would not, and
the level test degrades as the market factor rises while the contrast is untouched by
it. The contrast is the cheaper claim by about a factor of two.

**The first run re-read at the honest units.** `hedged.py` now prints these beside the
registered tables:

| unit | n | mean scaled | t | p |
|---|---|---|---|---|
| contract | 998 | +2.21bp | 4.23 | 0.0000 |
| underlying-day | 8 | +2.31bp | 1.49 | 0.1806 |
| date | 1 | — | — | needs >= 2 dates |
| volume contrast, high minus low | 8 | -2.81bp | -1.17 | 0.2819 |

The pooled t of 4.23 is t=1.49 at the underlying and not distinguishable from zero.
**H4c's contrast is on the predicted side - negative - and also not distinguishable
from zero.** Both readings are what one overnight period should look like. Neither
changes a registered threshold, and the registered tables above are untouched.

## Multiple testing, pre-registered 2026-09-16 — before the series is long enough

Registered before H4 has the day pairs to test anything, which is the strong form
and the same reason this file was written before `surface.csv` had a row.

Not every claim here is a count, and the correction applies only where one is:

- **H4b is an ordering across five buckets, not five tests.** It is judged by
  whether the predicted ordering appears, so no FDR control applies to the
  ordering itself.
- **H4a and H4c are each a single directional test.** Nothing to correct.
- **But the per-bucket t-statistics `hedged.py` prints are five tests**, and any
  sentence of the form "the premium is significant in k of the five buckets" is a
  count. **Registered now:** that sentence, if it is ever written, carries
  Benjamini-Hochberg control at q=0.05 across the five buckets, on the
  date-clustered p-values and not the contract-level ones, which
  `analyze.py --simulate-surface` showed reject a true null 46-73% of the time.

The order matters: cluster first, then correct. Correcting a family of statistics
that are each individually wrong produces a corrected family that is still wrong.

## What would falsify each

- **H4a** fails if the pooled mean gain is positive. That would most likely mean
  a sign error in `hedged.py`, not a market finding, and the first response
  should be to re-run `tools/test_hedged.py` rather than to write it up.
- **H4b** fails if the ordering is absent or reversed.
- **H4c** fails if high-volume contracts show gains equal to or less negative
  than low-volume ones.
- **H4d** fails if open interest predicts as well as or better than volume.

## Specification — frozen here

- Outcome: `hedged.py`'s scaled delta-hedged gain, P&L divided by the spot at
  run start, reported in basis points of spot.
- A run is one contract observed on consecutive trading days, gaps over four
  calendar days breaking the run so a holiday weekend is not spliced.
- Buckets: deep OTM put below 0.90 moneyness, OTM put 0.90-0.97, at the money
  0.97-1.03, OTM call 1.03-1.10, deep OTM call above 1.10.
- Volume terciles computed within the pooled sample, on contract volume at run
  start.
- Both the volatility and the log-variance formulations from H2 remain available
  but are **not** used here. This hypothesis is about hedged gains, which is a
  strike-specific outcome, and that is the whole point per HANDOFF 14.2.

## The inference limit, stated before any number is seen

Runs overlap in calendar time and share underlyings. **They are not independent
observations**, and the pooled t-statistic `hedged.py` prints is descriptive
only. `hedged.py` says so in its own output and `tools/pressure_test.py` asserts
that the warning is present.

Any inferential claim requires demeaning the cross-section by date and
clustering standard errors on date, per HANDOFF 14.3. **Until that is
implemented, H4 results are reported as descriptive patterns and nothing is
called significant.**

## Adjustment log

- *(none yet)*
