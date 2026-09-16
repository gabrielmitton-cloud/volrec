# H4 — Delta-hedged gains are negative, vary across the strike surface, and relate to where volume sits

**Registered:** 2026-09-13, **before `data/surface.csv` contains a single row.**
The surface begins recording on 2026-09-14. This file exists specifically so
that the predictions below are on record before any of the data that tests them
exists, which is the only thing separating a prediction from a description.
**Status:** registered 2026-09-13. **First run 2026-09-16 on the 14-15 September
pair - see "First run" below. One overnight period: descriptive, not a test.**
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

**This is one overnight period.** Every run shares the same two dates, so the pooled t
of 4.23 is descriptive and nothing more, exactly as the file said before the data
existed. A single night of TSLA moving is enough to flip every sign here. No adjustment
has been made to any threshold or bucket definition, and none should be until the
series is long enough for the date-clustered test in HANDOFF 14.3.

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
