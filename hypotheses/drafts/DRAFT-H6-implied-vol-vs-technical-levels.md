# DRAFT H6 — Implied volatility forecasts next-day trading range better than a technical-levels rule

> **DRAFT, 8 Oct 2026. NOT REGISTERED.** Written by Claude for Gabriel's review. Nothing here
> is frozen until Gabriel approves it and it is committed under `hypotheses/` without the
> DRAFT prefix; the commit date is the registration. No join has been run.
> (The number H6 was earmarked for Kalshi, which is parked; renumber if Kalshi returns.)

## Why this hypothesis exists

Raised by Gabriel 6 Sep 2026 (HANDOFF 17, "Parked for late October"): a technical-levels
scanner's "resistance" and "max" columns are a forecast of how far price will travel. Implied
volatility is also a forecast of travel, priced by people with capital at risk. The question is
which forecasts the realised range better. It is a test **between two methods**, not a search
for a signal, which is why it fits a project that "is not a search for alpha" (HANDOFF 1).

## A conflict to resolve before registering - Gabriel decides

The parked plan ran this on the live 109-ticker panel after ~40 trading days. CLAUDE.md says:
**"Never fit or evaluate any forecaster on data/iv_history.csv alone. The live panel has too
few independent episodes."** A range forecast is a forecaster, and 40 days of one market
factor is roughly two independent episodes. So this draft makes the **long sample primary**:

- **Sample A (primary, the test):** the Cboe index / ETF pairs H1 already uses (VIX/SPY,
  VXN/QQQ, RVX/IWM, VXD/DIA, OVX/USO, GVZ/GLD, VXSLV/SLV, VXEEM/EEM, EVZ/FXE), daily, 2016-01-04
  to the latest complete day. Cboe's free index history plus the ETFs' daily bars from Alpaca
  (the source `build_sample_a.py` uses; Alpaca's bars carry high and low, but
  `analyze.fetch_closes` keeps only the close today, so it needs a small extension). ~2,600 days per pair.
- **Sample B (secondary, descriptive only):** the live panel's ATM IV against the same tickers'
  next-day range, reported beside, never tested.

## The hypothesis, stated before any join

**H6a.** Over Sample A, the implied-volatility forecast of the next trading day's high-low range
has a lower mean squared log error than the technical-levels forecast, in at least 7 of the 9
pairs, and the pooled difference is significant under the test below.
**H6b.** The advantage is larger in the 21 days after a volatility-index spike (index above its
own 252-day 90th percentile) than in calm days - implied volatility reprices immediately; a
trailing range rule lags.

## Specification — to be frozen at registration

- **Target:** next trading day's range, ln(H/L), from daily OHLC.
- **IV forecast:** the index close / 100, converted to an expected one-day range by the
  Parkinson (1980) relation E[ln(H/L)] = sqrt(8/pi) * sigma * sqrt(1/252). Fixed constant,
  nothing fitted.
- **Technical-levels forecast:** the 14-day Average True Range (Wilder 1978) divided by the
  close - the standard volatility-of-range measure behind "resistance/support" level spacing.
  The rule and its 14-day length are fixed here, not tuned. (Pivot-point R1-S1 equals the prior
  day's high-low and is reported as a second, equally fixed, benchmark.)
- **Loss:** squared error of the log of each forecast against the log of the realised range.
- **Test:** Diebold-Mariano (1995) with the Harvey-Leybourne-Newbold (1997) small-sample
  correction on the daily loss differential per pair, Newey-West lag 5; across pairs, the count
  in H6a and Benjamini-Hochberg with Benjamini-Yekutieli beside it (as H1 since 8 Oct).
- **Gaps:** a day missing either forecast or the realised range is dropped; discontinued
  indices (VXGDX, VXXLE stopped Feb 2022) are excluded up front, as H1 found them fragmented.

## What would falsify it

ATR (or the pivot range) wins or ties in 3 or more of the 9 pairs, or the pooled DM test is not
significant at 5%. Either is reported as the result.

## Explicitly NOT in this hypothesis

Intraday data, entries/exits, any trading rule or P&L, small caps, tuning the ATR length or the
range constant, and any claim from Sample B.

## Open choices for Gabriel before registering

1. Long sample primary (this draft) vs the parked live-panel plan (conflicts with CLAUDE.md).
2. ATR(14) as the "technical levels" rule - or name the scanner rule you have in mind.
3. Register now (it needs no new data, so the 11 Nov rule allows it) or late October as parked.

## Adjustment log

(empty - nothing registered)
