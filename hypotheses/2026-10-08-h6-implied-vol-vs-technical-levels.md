# H6 — Implied volatility forecasts next-day trading range better than a technical-levels rule

**Registered:** 2026-10-08 (before any join; the commit date is proof). Approved by Gabriel 8 Oct.
**Status:** registered
**Sample:** A (long validation) primary; B (own panel) descriptive only
(H6 had been earmarked for Kalshi, which is parked; Kalshi takes the next free number if it returns.)

## Why this hypothesis exists

Raised by Gabriel 6 Sep 2026 (HANDOFF 17, "Parked for late October"): a technical-levels
scanner's "resistance" and "max" columns are a forecast of how far price will travel. Implied
volatility is also a forecast of travel, priced by people with capital at risk. The question is
which forecasts the realised range better. It is a test **between two methods**, not a search
for a signal, which is why it fits a project that "is not a search for alpha" (HANDOFF 1).

## Why the long sample is primary (resolved at registration)

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

## Decided at registration (Gabriel, 8 Oct 2026)

Long sample primary (the CLAUDE.md rule); ATR(14) as the technical-levels rule with the pivot
range as the second fixed benchmark; registered now - it needs no new data, so the 11 Nov rule
allows it. Not yet implemented: the join is built and tested AFTER this commit.

## Adjustment log

- **2026-10-09 — implementation details fixed BEFORE any data was fetched or joined (not a
  strike; no output exists).** The registered text left these open; they are fixed here, and the
  commit is timestamped before the first run:
  1. **Pairs:** VIX/SPY, VXN/QQQ, RVX/IWM, VXD/DIA, OVX/USO, GVZ/GLD, VXSLV/SLV, VXEEM/EEM, EVZ/FXE.
  2. **Data:** Cboe index closes (`analyze.fetch_market_vol`); Alpaca daily bars, sip feed,
     `adjustment=all` (`analyze.fetch_ohlc`). Day t needs the index close and the ETF's bar at t and
     the ETF's NEXT bar; a next bar more than 5 calendar days later is a gap and the day is dropped.
     Start 2016-01-04; end the last complete day at run time.
  3. **Forecasts of day t+1's range, all known at t's close:** IV = sqrt(8/pi) x I_t/100 x
     sqrt(1/252); ATR = Wilder's ATR(14) at t / C_t, Wilder smoothing (ATR_t = (13 ATR_{t-1} + TR_t)
     / 14, seeded with the mean of the first 14 true ranges); pivot = (H_t - L_t) / C_t.
     Target: ln(H_{t+1} / L_{t+1}); days with H = L dropped. Loss: (ln forecast - ln target)^2.
  4. **Per pair:** d_t = loss(IV) - loss(ATR). IV "has the lower error" when mean d < 0. Diebold-
     Mariano statistic with Newey-West lag 5, times the Harvey-Leybourne-Newbold factor
     sqrt((T-1)/T) for h = 1, against Student t(T-1), two-sided; those p-values feed BH and BY.
  5. **Pooled (H6a's significance):** per date, the mean of d across the pairs present that day;
     the same DM-HLN test on that series, two-sided at 5%.
  6. **H6b:** a spike day s has I_s above the 90th percentile of the index's previous 252 closes;
     day t is "after a spike" if a spike day falls in the 21 index days ending at t. H6b holds if
     the pooled date-level mean d is lower (more negative) after spikes than on calm days, Welch
     two-sided p < 0.05.
  7. **The pivot forecast** is reported with the same statistics, as a second benchmark; H6a and
     H6b are judged against ATR only.
- **2026-10-09 — EVZ's source, fixed BEFORE any H6 output existed (not a strike).** The first run
  stopped before computing anything: Cboe's EVZ file now returns 403 (access denied). Cboe
  discontinued EVZ in March 2025 (its ETF methodology notes decommissioning, 10 Feb 2025; FRED's
  EVZCLS ends 11 Mar 2025). EVZ/FXE is a registered pair, so it stays, read from FRED's EVZCLS -
  FRED republishes Cboe's closes, and on GVZ the two sources agree on all 2,704 common days since
  2016 (largest difference 0.00). Its window is therefore 2016-01-04 to 2025-03-11; every other
  pair runs to the last complete day. Unlike VXGDX and VXXLE (excluded up front: fragmented, ended
  2022) it has over nine years. Also fixed: the workflow reported success when the script crashed
  (`| tee` without pipefail) - it now fails as it should.
