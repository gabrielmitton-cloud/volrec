# H1 — The volatility risk premium is positive on the Cboe index family, 1990-2026

**Registered:** 2026-09-06 (before any join was run; commit date is the evidence)
**Status:** registered, BLOCKED on the open dependency in §5, not yet tested
**Sample:** A (long validation). Not `data/iv_history.csv`.

## Why this hypothesis exists

The binding constraint on this project is not data availability, it is
independent observations: roughly six episodes of the market factor by late
October 2026. `analyze.py --simulate` shows what that does - under a **true
null** with zero premium by construction, the pooled test rejects 63.8% of the
time (93.0% with a market factor at rho=0.5) while the non-overlapping test
sits near its nominal 5%.

No additional column fixes that. Only additional *observations* do, and the only
free source that lengthens the dependent variable is the Cboe volatility index
family, which reaches back to 1990.

The purpose of H1 is therefore **method validation, not discovery**. The VRP is
a documented phenomenon. If the code cannot find it in 36 years of index data,
the code is wrong, and nothing it reports about six episodes is worth reading.

The sentence this is meant to earn: *"my method finds the known result on
decades of history, and here is what the same frozen code finds on the data I
collected myself."*

## The hypothesis, stated before the join

**H1a.** Mean `IV(t) - RV(t, t+21)` is **positive** across the index family,
on non-overlapping 21-trading-day observations.

**H1b.** The premium is **larger for equity indices** (VIX/SPX, VXN/NDX,
RVX/RUT, VXD/DJIA) than for commodity and FX underlyings (OVX/USO, GVZ/GLD,
EVZ/FXE). Directional prediction, made in advance.

**H1c.** The term-structure slope `VIX3M - VIX9D` is **positive on average**
and **negative in stressed periods**, and periods of inversion are followed by a
*smaller* premium. This is the same variable `record.py` captures with its far
leg, and it is the tightest link between the two samples.

## Specification — frozen here, changes logged below

- `IV(t)` = Cboe index close on date t, divided by 100.
- `RV(t, t+21)` = annualised close-to-close realised volatility of the
  underlying over the next 21 **trading** days: `sqrt(252 / 21) * std(log
  returns)`, sample standard deviation, no mean adjustment.
- **Non-overlapping sampling.** Take every 21st trading day. Overlapping daily
  windows are the failure mode section 4.2(a) names; they are not used for the
  headline test. An overlapping version may be reported *alongside*, labelled as
  such, never instead.
- **Test:** one-sample t-test on the non-overlapping series, per pair. No
  pooling across pairs for the headline number. If pooled at all, demean the
  cross-section by date and cluster standard errors on date.
- **Pairs (underlying in brackets):** VIX[SPX], VXN[NDX], RVX[RUT], VXD[DJIA],
  OVX[USO], GVZ[GLD], VXEEM[EEM], VXSLV[SLV], VXGDX[GDX], EVZ[FXE], VXXLE[XLE].
- **Gapped series.** VXSLV and VXGDX were discontinued 2022-02-11 and relaunched
  (2025-05-15 and 2025-09-16). Treat pre-gap and post-gap as **separate
  segments**; never compute a return across the gap. A relaunched index may not
  share methodology with its predecessor - state this rather than splicing.

## What would falsify it

- H1a fails if the mean premium is **not significantly positive** on the equity
  index pairs. That is a red flag on the *implementation*, not a discovery,
  because the premium is well documented on exactly this data.
- H1b fails if commodity/FX premia match or exceed equity premia.
- H1c fails if slope has no relationship to the subsequent premium.

**A failure here stops the project's headline claim.** If the method cannot
recover a known result with hundreds of observations, no result it produces on
six episodes may be reported as evidence of anything.

## Explicitly NOT in this hypothesis

- No media, sentiment, news, EMV, EPU, COT or attention variable. Those are
  separate hypotheses, registered separately, tested only after H1 passes.
- No claim that Sample A results describe `data/iv_history.csv`. **Different
  estimand:** Cboe indices are variance-swap-style and integrate the whole
  strike surface; this project records ATM implied volatility. The measured gap
  on 4 Sep 2026 was +3.61 vol points across four matched pairs (HANDOFF §6).
  That gap is the skew premium, and it must be stated, not smoothed over.

## Open dependency — this hypothesis cannot be tested until it is resolved

`RV` requires **daily closes of the underlyings, back to each index's start
date**. The research brief catalogues thirteen sources and **none of them
supplies this.** It is the critical path for Sample A.

Candidates, in preference order:

1. **Alpaca** - key already held, already used by `analyze.py:fetch_closes`, no
   new dependency. *Free-plan history depth is unverified and is believed to
   start around 2016 (IEX).* Settle with one call. If it reaches only 2016 it
   still covers ~10 years, which is far more than six episodes.
2. **Tiingo / Alpha Vantage free tier** - registered key, deep EOD history,
   small daily quotas that a once-per-analysis batch fits inside.
3. **Stooq** - REJECTED 2026-09-06. Now serves a JavaScript proof-of-work bot
   challenge. A pipeline that depends on defeating bot protection is fragile and
   not defensible in an interview.

**Fallback if no source reaches 1990:** shorten Sample A to whatever the price
history supports and say so. Ten years of non-overlapping monthly observations
is ~120 episodes against six. The validation argument survives a shorter window
intact; it does not survive a fabricated one.

## Adjustment log

Any change to a threshold, window, or pair set goes here with a date and a
reason. Three or more adjustments = abandon H1 and report the abandonment.

- *(none yet)*
