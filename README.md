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

- **Feed**: Alpaca's free `indicative` options feed and `iex` stock feed. Quotes
  are indicative, not exact NBBO. Fine for daily snapshots; worth stating in any
  write-up.
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
- [ ] ~40 trading days accumulated (late October)
- [ ] Realized-vs-implied analysis
- [ ] Write-up (February 2027)
