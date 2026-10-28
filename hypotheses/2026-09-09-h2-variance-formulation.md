# H2 — The premium is better measured in variance than in volatility, following Carr & Wu (2009)

**Registered:** 2026-09-09, before any variance-form premium was computed
**Status:** registered, NOT tested. Pending confirmation at the 11 Sep meeting.
**Sample:** A first, then B

## Where this came from

Marc Vinyard (Pepperdine business librarian) sent Carr & Wu (2009), *"Variance
Risk Premiums,"* Review of Financial Studies 22(3), 1311-1341, as methodology
guidance, alongside confirmation that Bloomberg is the available data route and
that Pepperdine has no OptionMetrics.

This was already Friday question 1. The paper answers most of it, so Friday
becomes confirmation rather than an open question.

## What the paper does

- Defines the premium in **variance**, not volatility.
- Uses the **variance swap rate** as the risk-neutral expected variance, and
  shows it can be synthesised from a portfolio of options across strikes.
- Defines the premium as **realised variance minus the swap rate**, so their
  premium is **negative** when the insurance was overpriced.
- Finds premiums **strongly negative for the S&P 500, S&P 100 and Dow**, with
  **large cross-sectional variation across individual stocks**.
- Introduces a **variance beta**: regress each stock's return variance on the
  index's return variance. Premiums are **more negative for stocks with higher
  variance beta**, which is evidence for a common priced variance risk factor.
- Notes that in dollar terms the premium is correlated with the swap rate, but
  **in log terms it is closer to an independent series**.
- Checks robustness against **bid, mid and ask** option prices. The index result
  survives all three.

## SIGN CONVENTION — the easiest way to introduce a silent bug

| | definition | overpriced insurance shows as |
|---|---|---|
| this project | `IV - RV` | **positive** |
| Carr & Wu | `RV - SW` | **negative** |

Same phenomenon, opposite sign. **Never quote a Carr & Wu number next to one of
ours without converting.** Any comparison must state which convention is in use.

## The hypothesis

**H2a.** Measured in variance terms, the premium is positive under this
project's convention (`IV^2 - RV^2`) and significant on the equity index pairs
of Sample A, consistent with Carr & Wu finding it strongly negative under
theirs.

**H2b.** The **log** formulation, `ln(IV^2) - ln(RV^2)`, produces a series with
**lower autocorrelation** than the level formulation. If it does, it partially
addresses this project's binding constraint, which is dependence between
observations rather than data volume.

**H2c.** Following the variance-beta result: estimating a variance beta per
ticker by regressing its realised variance on the index's, the premium is
**larger for higher-beta tickers**. This is a cross-sectional prediction and is
testable on Sample B despite its small N, because it compares tickers rather
than time periods.

## Why Sample A can implement this almost exactly

Carr & Wu synthesise the variance swap rate from options across all strikes.
This project records only at-the-money, so it **cannot** replicate that from its
own panel.

**But the paper states that VIX approximates the 30-day variance swap rate on
the S&P 500** (citing Carr and Wu 2006). Sample A already uses the Cboe index
family. So `VIX^2` can stand in for the swap rate directly, and Sample A becomes
a close replication of a landmark paper rather than a loose analogue.

That is a much stronger thing to be able to say, and it costs no new data.

## What would falsify it

- H2a fails if the variance-form premium is insignificant on equity indices
  where Carr & Wu found it strongly significant. That would indicate an
  implementation error, not a discovery.
- H2b fails if log and level formulations have similar autocorrelation. Then the
  log form is a presentational choice, not a fix for anything, and should be
  described as such.
- H2c fails if variance beta has no relationship to premium size.

## NOT in this hypothesis

- No claim that this project computes a true variance swap rate. It does not,
  and cannot, from at-the-money data.
- No change to `data/iv_history.csv`. The recorder is unaffected: the variance
  form is computed from columns already recorded.

## Before this is tested

**Confirm at the 11 Sep meeting**, since the paper came from a librarian rather
than the volatility specialist, and since the ATM limitation above means the
replication is close but not exact. Ask whether `VIX^2` as the swap rate proxy
is acceptable, and whether the log form is the right response to dependence.

## Adjustment log

- *(none yet)*

---

# Result — tested 2026-09-09, same day as registration, before the meeting

Run: `samples/long/test_h2_variance.py` via a temporary workflow. Sample A,
2016-2026, 21-day non-overlapping windows. Dataset untouched.

Equity indices pooled (n=508). Positive = insurance overpriced, our convention.

| formulation | mean | t | p |
|---|---|---|---|
| `IV - RV` volatility, current | 3.14 vol pts | **9.28** | 5.1e-19 |
| `IV^2 - RV^2` variance, raw | 62.16 | **2.14** | 3.3e-02 |
| `ln(IV^2) - ln(RV^2)` log variance | 47.94 | **16.26** | 3.6e-48 |

**Reproduced 9 October 2026** (Actions run 37990784842, `--end 2026-09-06`): log variance t = **16.26**,
volatility t = 9.28, variance t = 2.14 on the equity indices, exactly as recorded. EVZ and VXXLE now come
from FRED (Cboe withdrew the files); their rows move slightly, for the reason given in H1's note.

## H2a — HOLDS, but with a result that was not anticipated

*Robustness, 17 Oct 2026 - added after the verdict; the verdict is unchanged.* An independent
re-implementation (written from this file, sharing no code) run on a SECOND price source - Yahoo Finance
adjusted closes instead of Alpaca's - matches the project's own code number for number on that data, and
reproduces every count and conclusion of H1 and of H2's log and volatility forms (log variance t 16.11,
volatility t 8.91). The raw-variance form does not survive the change of vendor: **t 1.79, p 0.074**
(Alpaca: 2.14, 0.033). A few spike windows carry it, as the paragraph below already says. Quote the
raw-variance significance as vendor-sensitive, never on its own.

The variance form is significant, so the direction agrees with Carr & Wu. But
**raw variance is by far the weakest of the three** (t = 2.14 against 9.28 for
plain volatility), and **log variance is by far the strongest** (t = 16.26).

The reason is visible per pair. Squaring amplifies the tails, so a handful of
volatility spikes dominate the mean and inflate the dispersion. OVX/USO shows a
large raw-variance mean of 304.8 at t = 1.94, which is a big number carrying
almost no statistical weight. Worse, **VXGDX/GDX flips sign** under raw
variance, -336.0, while remaining positive under both volatility (+0.15) and log
variance (+13.8). A single formulation choice reversing the sign on a pair is
exactly the kind of fragility worth knowing about before building on it.

So "move to variance" is too coarse an instruction. **In levels it is worse than
what this project already does. In logs it is much better.**

## H2b — NOT SUPPORTED, and the reason is informative

Predicted: the log form would be less correlated with the volatility level.

| form | corr(premium, IV level) | lag-1 autocorrelation |
|---|---|---|
| vol | 0.044 | 0.147 |
| var | -0.048 | 0.101 |
| logvar | -0.063 | 0.154 |

All three correlations are tiny and the log form is marginally the *largest* in
absolute terms. **H2b is not supported on this sample.**

The likely reason is worth stating rather than hiding: Carr & Wu's observation
concerns dollar-denominated premiums on overlapping data. This project already
samples **non-overlapping** 21-day windows, so the dependence the log form was
meant to reduce has largely been removed by the sampling design before the
formulation ever gets a chance to matter. There is nothing left for it to fix.

That is a mildly reassuring null: it suggests the existing non-overlapping
design is already doing the job the log transform was proposed for.

**H2b therefore does not rescue the discarded 95% of rows.** That remains open,
and it remains Friday question 2.

## H2c — not tested

Variance beta needs a longer cross-section than Sample B currently has.

## What this changes, and what it does not

**Does not change anything yet.** H2 remains registered and unadopted. Nothing
in `analyze.py` or `build_sample_a.py` was modified; the test computes the three
forms alongside each other and reports.

**Changes the Friday question.** It is no longer "should I use variance." It is:

> *"I tested three formulations. Raw variance is outlier-dominated and barely
> significant, t = 2.1, and it flips the sign on one pair. Log variance is much
> stronger than plain volatility, t = 16.3 against 9.3. Is the log form what you
> would use, and does raw variance being that weak suggest I have made an error
> somewhere?"*

That last clause matters. The raw-variance weakness could equally mean the
implementation is wrong, and it should be offered as a possibility rather than
presented as a finding.

## Companion reading, 28 October 2026 - an outside review (M01, M05, M10); descriptive, the verdicts above stand

An outside review (a second AI model, verified against the code by Vega) found three things, all confirmed:
**(M05)** the pooled H2a t above treats the equity indices' windows as independent, but VIX, VXN, RVX and VXD share
market episodes - and this project's own rule 5 (hypotheses/README.md) requires a pooled test to cluster on date;
**(M10)** H2b was registered as LOWER AUTOCORRELATION of the log form, but the verdict line in `test_h2_variance.py`
compares correlation with the IV level, and its autocorrelation runs across the boundaries of concatenated pairs;
**(M01)** `realized_vol` divides by c4(n), so RV^2 carries 1/c4^2 (about 2.4% at n = 21), not Carr & Wu's raw sum of
squares. A companion was added to `test_h2_variance.py` and run on the registered sample in the manual read-only
`sample_a.yml` (Actions run 40720872275, closes to 6 Sep 2026; the registered lines reproduced exactly: var t 2.14,
logvar 16.26, vol 9.28):

| equity pairs, one mean per window date (219 dates) | mean | t | p |
|---|---|---|---|
| volatility, IV - RV | 3.17 pts | 5.99 | 9e-9 |
| variance, IV^2 - RV^2 (as registered) | 63.1 | **1.34** | **0.18** |
| variance, raw sum of squares (no c4) | 73.6 | 1.60 | 0.11 |
| log variance | 46.2 | 10.99 | 1e-22 |

- **H2a, read with the dependence handled as rule 5 requires, is NOT significant** (t 1.34; 1.60 with raw squares).
  The verdict above stays as recorded - registered verdicts are never rewritten - but it is **not robust**: it rests on
  a pooled t that overstates the evidence, and on 17 Oct it already failed to survive a change of price vendor. The
  write-up reports H2a as "holds as recorded; not robust to date clustering or to the price source". The volatility and
  log forms remain strongly significant under the same clustering.
- **H2b on its registered statistic** - lag-1 autocorrelation within each pair - the log form is lower on **3 of 11**
  pairs. "Not supported" stands, now on the question it was registered to answer.
- The falsification line "insignificant ... would indicate an implementation error, not a discovery" overstates what a
  replication can show (review M09): samples, instruments, periods and power differ, so a weak result can be either.

*Changes the Friday question's answer: raw variance is not merely weak, it is not significant once shared market episodes
are accounted for; log variance is.*
