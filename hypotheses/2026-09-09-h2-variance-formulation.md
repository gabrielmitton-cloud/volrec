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
