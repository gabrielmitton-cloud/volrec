# H1 — The volatility risk premium is positive on the Cboe index family, 2016-2026

**Registered:** 2026-09-06 (before any join was run; commit date is the evidence)
**Status:** registered 2026-09-06, dependency resolved 2026-09-07, specification
amended (see the adjustment log; no data had been observed at the time of the
amendments). **TESTED 2026-09-07 - see Result below.**
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
- `RV(t, t+21)` = **`analyze.py:realized_vol`**, applied to the log returns of
  the underlying over the next 21 **trading** days. That estimator is
  un-demeaned and divided by the `c4(n)` bias factor, which corrects a ~1.2%
  low bias over a 21-day window. Sample A **imports it from `analyze.py`**
  rather than reimplementing it. This is not a detail: the whole claim of the
  two-sample design is that the *same frozen code* runs on both, and a
  re-implemented estimator would quietly break that.
- **Non-overlapping sampling.** Take every 21st trading day. Overlapping daily
  windows are the failure mode section 4.2(a) names; they are not used for the
  headline test. An overlapping version may be reported *alongside*, labelled as
  such, never instead.
- **Test:** one-sample t-test on the non-overlapping series, per pair. No
  pooling across pairs for the headline number. If pooled at all, demean the
  cross-section by date and cluster standard errors on date.
- **Pairs (underlying in brackets):** VIX[SPY], VXN[QQQ], RVX[IWM], VXD[DIA],
  OVX[USO], GVZ[GLD], VXEEM[EEM], VXSLV[SLV], VXGDX[GDX], EVZ[FXE], VXXLE[XLE].
- **Index vs ETF proxy.** VIX, VXN, RVX and VXD are computed on the *indices*
  (SPX, NDX, RUT, DJIA); the price data available is for the *tracking ETFs*
  (SPY, QQQ, IWM, DIA). Over 21-day windows their realised volatilities are
  near-identical, but they are not the same instrument: the ETFs pay dividends
  and carry small tracking error. State this in the write-up; do not silently
  treat SPY as SPX. The remaining seven pairs are ETF-on-ETF and have no such gap.
- **Price feed:** Alpaca `sip`. Verified 2026-09-07: `sip` reaches 2016-01-04
  uniformly across all 11 underlyings, while `iex` is both shallower and ragged
  (SPY 2018-11-01, USO 2020-04-21, the rest 2020-07-27).
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

## Open dependency — RESOLVED 2026-09-07

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

**All three entries below were made on 2026-09-07, before any premium was
computed and before any data was observed.** They correct specification errors
and record a pre-registered contingency firing. None was made in response to a
result. The three-strikes rule counts adjustments made *after seeing output*;
these do not count against it, and that distinction is itself recorded here so
a reader can judge it rather than take my word for it.

1. **Sample window 1990-2026 → 2016-2026.** The pre-registered fallback firing
   after the price dependency was probed. Not discretionary.
2. **RV estimator corrected.** The original text specified a demeaned sample
   standard deviation. That was simply wrong: it must be `analyze.py`'s
   un-demeaned, `c4`-corrected `realized_vol`, because Sample B uses it and the
   entire two-sample argument rests on both samples running identical code.
3. **Underlyings named as ETFs, not indices,** with the proxy caveat stated
   explicitly. The original text named SPX/NDX/RUT/DJIA, which are not
   obtainable; the tracking ETFs are.


---

# Result — tested 2026-09-07

Run: `samples/long/build_sample_a.py`, via a temporary workflow against the live
API, dataset md5 asserted unchanged. Window 2016-01-04 to 2026-07-16 (the last
usable observation is 21 trading days before the data ends, by construction).

| pair | N | mean premium | t | p | positive |
|---|---|---|---|---|---|
| VIX/SPY | 127 | **+3.52** | 5.14 | 0.0000 | 83% |
| VXN/QQQ | 127 | +2.70 | 3.68 | 0.0003 | 79% |
| RVX/IWM | 127 | +3.07 | 4.80 | 0.0000 | 78% |
| VXD/DIA | 127 | +3.26 | 5.02 | 0.0000 | 83% |
| OVX/USO | 127 | +5.24 | 4.40 | 0.0000 | 76% |
| GVZ/GLD | 127 | +1.80 | 3.97 | 0.0001 | 76% |
| VXEEM/EEM | 127 | +3.38 | 5.43 | 0.0000 | 79% |
| VXSLV/SLV | 89 | +3.14 | 2.46 | 0.0159 | 81% |
| EVZ/FXE | 110 | +0.83 | 5.63 | 0.0000 | 75% |
| VXXLE/XLE | 74 | +1.80 | 1.32 | 0.1904 | 72% |
| VXGDX/GDX | 85 | +0.15 | 0.08 | 0.9347 | 72% |

Premium in annualised volatility points.

**H1a — HOLDS.** 9 of 11 pairs significantly positive at p<0.05. The two that
fail are the sector ETFs whose indices were discontinued in Feb 2022, and which
therefore have the fewest and most fragmented observations. This is the
documented volatility risk premium, recovered by this project's own estimators
on ~127 non-overlapping episodes per pair. **The method works.**

**H1b — HOLDS ON THE STATED TEST, BUT THE PICTURE IS MIXED. Report it that way.**
The prediction was that equity indices carry a larger premium than commodity and
FX underlyings. Combined, they do: equity index +3.14 vs commodity-and-currency
+2.79. But that comparison only survives because currency (+0.83, n=110) drags
the combined average down. **Commodity alone is +3.42, which EXCEEDS equity
index at +3.14.** Oil is the largest premium in the whole table at +5.24.

So the honest statement is: the premium is large and positive nearly everywhere,
FX is distinctly smaller, and there is no clean equity-over-commodity ordering.
The automated verdict prints HOLDS; a reader who only saw that word would be
misled, and an interviewer would find this in about a minute. **Do not quote the
verdict without the breakdown.**

**H1c — HOLDS.** The market term structure was positive on 87.3% of 2,684 days,
mean +2.83 points. Splitting VIX/SPY observations by the slope at entry: normal
curve +3.87 (n=110), inverted +1.22 (n=17). The premium is roughly a third as
large when the curve is inverted, in the predicted direction. Small n on the
inverted leg; treat as suggestive, not established.

## What this licenses, and what it does not

**Licensed:** "My method recovers the known volatility risk premium on ten years
of index data, 9 of 11 underlyings, and here is what the same frozen code finds
on the data I collected myself."

**Not licensed:** any claim that these numbers describe `data/iv_history.csv`.
Different estimand (variance-swap-style vs at-the-money), different underlyings,
different period. The measured gap on four matched pairs was +3.61 vol points.

**Also not licensed:** treating +3.52 as a prediction of what Sample B will show.
Sample A is a validation of the *machinery*, not a prior for the panel.
