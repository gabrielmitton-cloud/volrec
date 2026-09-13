# volrec

Measuring the volatility risk premium with data I collect myself.

## The question

Options are priced off an implied volatility — the market's forecast of how much
a stock will move. There's a well-documented finding in the literature that
implied volatility systematically *exceeds* the volatility that subsequently
shows up, meaning options tend to be expensive. That gap is called the
volatility risk premium.

I wanted to test whether it appears in data I gathered myself, rather than take
it on authority.

## Why collect rather than buy

Historical options data with a full implied-volatility surface is the expensive,
gated part of options research. Vendors like OptionMetrics and ORATS price it for
institutions. Live quotes, by contrast, are close to free.

So this trades time for money: record a daily snapshot, and after six months I
own six months of proprietary history for a fixed universe. Started 4 September
2026.

## Method

`record.py` runs every weekday at 8:30am Pacific via GitHub Actions. For each of
109 tickers it:

1. Fetches the underlying's spot price
2. Pulls the option chain filtered to strikes within ±8% of spot and expiries
   21–45 days out
3. Selects the call closest to 30 days to expiry, then closest to at-the-money
4. Records spot, strike, expiry, bid/ask, implied volatility, and greeks

One row per ticker per day, appended to `data/iv_history.csv`. Same-day reruns
are deduplicated, and weekends and exchange holidays are skipped outright
(checked against the market calendar), so no row is written for a day the
market never traded.

At-the-money and ~30 days is deliberate: that's where gamma is highest and where
implied volatility is most reliably quoted, which keeps snapshots comparable as
contracts roll.

## The universe

109 tickers chosen for *spread*, not count — 109 correlated tech names would be
one observation repeated 109 times. Started at 52; expanded to 109 on 5
September 2026, one day into collection, when the cost of uneven history was a
single day. Candidates were screened live against the API and kept only if
implied volatility, all five greeks and a two-sided quote came back with a
spread under 60% of mid.

| group | why |
|---|---|
| Index ETFs (SPY, DIA, QQQ, IWM, MDY) | Baseline, ascending volatility by market cap |
| Non-equity (GLD, SLV, TLT, IEF, USO, UNG, FXE, EEM, EFA) | Volatility driven by different forces — tests whether the premium is equity-specific |
| Sector ETFs (10) | Regime coverage without single-name earnings noise |
| Mega-cap tech (5) | The liquid, heavily-traded middle |
| High-vol growth (NVDA, TSLA, AMD, PLTR, COIN, MSTR, SMCI) | Top of the volatility range |
| Defensives (JNJ, PG, KO, PEP, WMT, MCD, VZ) | Anchors the bottom — without these everything clusters 20–45% |
| Financials, energy, industrials | Sector variety |

First run confirmed the spread is real: implied vol ranged from 4.2% (FXE) and
5.1% (IEF) at the low end up to 72.1% (MSTR). The expansion widened it further,
adding LQD at 4.9% and MARA at 82%.

## The analysis (from ~November 2026)

For each snapshot, compare the implied volatility recorded that day against the
volatility the underlying actually delivered over the following 30 days.

If realized consistently comes in below implied, the premium is present. The
questions worth asking:

- Does it hold across asset classes, or only in equities?
- Is it larger for index ETFs than for single names? The literature says yes,
  and attributes the gap to a correlation risk premium.
- Does it scale with the volatility level, or is it flat?
- Is it large enough to survive bid-ask costs? (The `bid`/`ask` columns exist
  precisely so this can be answered rather than assumed.)

A null result is a real result. If the premium doesn't clear costs in this
sample, that is worth writing up as it stands.

One caution that shapes the whole analysis: sampling daily while looking forward
30 days means consecutive observations share almost the same realized path, and
all 109 tickers on a given day share a market factor. A pooled t-test across
every row would report significance on pure noise — simulated at 65–89% false
positives against this exact design. The effective sample size is roughly the
number of *non-overlapping* windows, not the number of rows. `HANDOFF.md` §4
carries the corrected method.

## Companion tool

`gamma-lab.html` is a delta-hedging simulator built alongside this. It shows why
the question matters: a long option, delta-hedged, profits when realized
volatility exceeds implied. Version 2 adds transaction costs, stochastic implied
vol, and jumps, and sweeps rebalance frequency to find where net profit peaks.

## Data notes and limitations

- **Feed**: Alpaca's free `indicative` options feed for quotes, and the `sip`
  consolidated tape for stock closes. Options quotes are indicative, not exact
  NBBO. Fine for daily snapshots; worth stating in any write-up. Stock closes
  moved from `iex` to `sip` on 7 Sep 2026: `iex` is a single venue carrying a
  low single-digit share of volume, so its close is not the official closing
  print, and its free history is both shallower and ragged.
- **Snapshot timing**: one reading per day at a fixed time, so intraday
  volatility is invisible. The schedule is fixed at 15:30 UTC, which is
  11:30am ET while daylight saving is in effect but 10:30am ET once it ends
  on 1 November 2026. Snapshots from November onward therefore sit an hour
  earlier in the session than those before it — worth controlling for, since
  implied vol is not flat across the trading day.
- **Expiry drift**: MDY and FXE lack weekly options and fall back to ~42-day
  expiries. The `dte` column records this so it can be controlled for.
- **Wide quotes on FXE and XLU**: on day one FXE quoted 0.63/1.27 and XLU
  0.45/0.79 — spreads of 67% and 55% of the mid respectively. Wide enough that
  the mid is unreliable for both. Under review.
- **Survivorship**: the universe is fixed as of Sept 2026 and doesn't adjust for
  future delistings or index changes.
- **Vendor-computed IV**: implied volatility and greeks are calculated by Alpaca
  from its free *indicative* feed rather than from exact NBBO quotes, using a
  documented Black–Scholes solver but an undocumented risk-free rate and
  dividend treatment. Levels should be read as approximate.
- **At-the-money only, and calls only**: implied vol varies by strike, and that
  shape carries information this dataset doesn't capture. An ATM Black–Scholes
  IV also approximates the *volatility* swap rate rather than the model-free
  variance swap rate that VIX-style measures use — which understates the
  premium, and understates it more for index ETFs than for single names.

## Two samples, one codebase

The binding constraint here is not data, it is **independent observations**. By
late October there will be ~40 trading days but only about six independent
episodes of the market factor, because most days move together. `analyze.py
--simulate` demonstrates the consequence: under a true null with zero premium
by construction, a pooled test across tickers rejects 63.8% of the time, while
a non-overlapping test sits near its nominal 5%.

No additional column fixes that. Only additional observations do. So there are
two samples running **identical code**:

- **Sample A** (`samples/long/`) uses free Cboe volatility indices as the
  implied-vol measure, 2016-2026, ~127 non-overlapping episodes per pair. This
  is where the method is validated. Tested 7 Sep 2026: the premium is
  significantly positive on **9 of 11** underlyings, VIX/SPY at +3.52
  volatility points, t = 5.14.
- **Sample B** (`samples/panel/`) is `data/iv_history.csv`, N ≈ 6. The same
  frozen code runs on it and the result is reported with its sample size
  stated.

Sample A is a **different estimand** and is never presented as a result about
the collected panel: Cboe's indices are variance-swap-style and integrate the
whole strike surface, while this project records at-the-money implied vol. The
measured gap across four matched pairs on 4 Sep 2026 was 3.61 volatility
points, and that gap is the skew premium.

## The strike surface, and what free data actually costs

Recording at-the-money implied volatility answers how large the premium is. It
cannot answer **where in the strike surface it sits**, which needs the whole
smile and, to say anything about liquidity, the volume at each strike.

From 14 September 2026 a second recorder captures that: eight underlyings, two
expiries, forty strikes spanning +/-30% of spot, with **bid, ask, implied
volatility, all five greeks, volume and open interest per contract**. It costs
no additional API calls, because the original recorder was already fetching
those strikes and discarding all but one.

**The measurement question this makes possible.** Cboe publishes the
authoritative model-free volatility index for five of those underlyings
(SPY/VIX, QQQ/VXN, IWM/RVX, GLD/GVZ, USO/OVX). So a model-free estimate built
from a *free, indicative, non-OPRA* feed can be checked against the
authoritative number, same underlying, same day. Nobody with a research budget
measures what free data costs, because they buy OptionMetrics instead.

Calibrated 11 September 2026, implementing Cboe's own methodology:

| strike band | mean absolute gap vs Cboe | worst |
|---|---|---|
| +/-10% x 20 strikes | 3.97 vol pts | -12.37 |
| +/-20% x 30 strikes | 1.31 | -4.39 |
| **+/-30% x 40 strikes** | **0.59** | **-1.84** |

At the widest band **SPY comes in at 15.83 against a published VIX of 15.84.**

The gap was never data quality. It was strike truncation, and it bites hardest
where volatility is highest: a fixed +/-10% band spans about 2.2 standard
deviations on a 16-vol name but only 0.6 on 59-vol crude oil, which is why USO
was twelve points light. **Any study using a fixed percentage strike band is
therefore most biased on exactly the high-volatility names most likely to be
interesting.**

### Measuring the premium across strikes, without cancelling it

The obvious approach does not work, and the arithmetic is worth stating. If the
premium at strike K is `IV(K)^2 - RV` and `RV` is one number shared by every
strike that day, then differencing two strikes cancels the realised term
exactly and leaves the shape of the implied volatility surface, which is the
volatility smile, which Bollen & Whaley published in 2004.

So the outcome here is **strike-specific**: the delta-hedged gain of Bakshi &
Kapadia (2003). Buy the option, short delta shares, rebalance daily, see what is
left. The hedging path depends on the contract's own gamma, so it does not
cancel. A negative hedged gain means the buyer paid for more movement than
arrived, which is a positive variance risk premium.

### Repo structure

```
record.py                  the daily ATM recorder, 109 tickers
surface.py                 the daily strike-surface recorder, 8 underlyings
analyze.py                 shared estimators, used by both samples
modelfree.py               Cboe's variance methodology, and the gap against it
hedged.py                  per-contract delta-hedged P&L
data/iv_history.csv        the ATM panel, append-only, never written elsewhere
data/iv_history.pre-17col.csv   one-time migration backup, immutable
data/surface.csv           the strike surface
hypotheses/                pre-registered, dated, committed BEFORE the test
samples/long/              Sample A
samples/panel/             Sample B
tools/pressure_test.py     49 read-only integrity checks
tools/test_hedged.py       18 hand-computed cases for the hedging math
```

The rule that holds the rest together: **nothing becomes a model variable
without a hypothesis in `hypotheses/` dated before the join that tests it.**

## Running it

```bash
pip install requests
export ALPACA_KEY="..."
export ALPACA_SECRET="..."
python record.py
```

`python record.py --probe SPY` dumps a raw API response for debugging.

Automated via `.github/workflows/record.yml`; keys live in repository secrets.

## Status

- [x] Recorder built and running daily
- [x] Universe selected, first clean run 2026-09-04
- [x] Schema migrated 17 -> 32 columns, first full 109-ticker run 2026-09-08
- [x] Sample A built and H1 tested, 9 of 11 pairs significant
- [x] Strike surface recording, with volume and open interest, from 2026-09-14
- [x] Model-free estimator matching the published VIX to 0.01 vol points
- [x] Delta-hedged P&L estimator, 18 unit tests
- [ ] ~40 trading days accumulated (late October)
- [ ] Realized-vs-implied analysis
- [ ] Write-up (February 2027)
