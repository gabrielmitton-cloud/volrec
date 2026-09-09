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

## H2a — HOLDS, but with a result that was not anticipated

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
