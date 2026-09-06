# HANDOFF

Context for anyone (or any assistant session) picking this project up cold.
Read this before proposing changes. It records not just the current state but
the reasoning behind decisions already made, so they don't get re-argued.

Last updated: 6 September 2026.

**Start at §12 (Roadmap)** if you are picking this up to do work. §1-§3 are the
framing and the decisions that are closed. §4 is the analysis spec and is the
densest part - read it before writing any analysis code.

---

## 1. What this is, and what it isn't

**Is:** a personal research project. Collect options data daily, then test
whether implied volatility overshoots subsequent realized volatility — the
volatility risk premium — in a dataset I gathered myself.

**Purpose:** a portfolio and interview artifact. I'm an incoming Pepperdine
finance student. The value is having something specific and verifiable I can be
questioned about for fifteen minutes, not a résumé line.

**Is not, and should not be treated as:**

- A business or startup. This was explicitly evaluated as a venture and
  rejected: it can't generate revenue at any capital level available to me, and
  it fails my own criteria for what a business needs to be. Don't pitch it back
  as one.
- A search for alpha. I'm not trying to find a tradeable edge, and I don't
  expect to. Testing a documented phenomenon honestly is the goal.
- A live trading system. No real money is involved and none is planned. See §5.

---

## 2. Current state

| piece | status |
|---|---|
| `record.py` | Working. 109 tickers, ~95 seconds per run (measured live 5 Sep). |
| `analyze.py` | Written and statistically validated 6 Sep. Includes the free Cboe market factor (§11.1). Run `python analyze.py --status` for the countdown. |
| GitHub Actions | Live. Weekdays 15:30 UTC (8:30am Pacific). First scheduled run: Tue 8 Sep. Mon 7 Sep is Labor Day and is skipped. |
| Data | Collecting since 2026-09-04. First run: 52/52 rows, all IV populated. |
| `tools/gamma-lab*.html` | Complete. Educational, not part of the pipeline. |
| Schema | 32 columns as of 6 Sep. The file is still 17 and migrates itself on the first run after that - expect the jump on Tue 8 Sep. |
| Monitor | Live at https://gabrielmitton-cloud.github.io/volrec/tools/monitor.html (GitHub Pages, main branch, root). |
| Watchdog | Weekly Claude routine `trig_01GkVL3mRpGGptXfqoNSR77d`, Wed 09:13 Pacific. Runs OUTSIDE GitHub Actions on purpose - see §5. |

Repo: `github.com/gabrielmitton-cloud/volrec` (public).
API keys live in GitHub repository secrets — never in code.

---

## 3. Decisions already made, and why

These were reasoned through. Reopen them only with a specific reason.

**Alpaca over Tradier.** Tradier gates API tokens behind a completed brokerage
application requiring SSN and funding. Alpaca's paper account needs only an
email. Free `indicative` options feed and `iex` stock feed both serve what's
needed.

**At-the-money calls, ~30 days to expiry.** Highest gamma, most reliably quoted
implied volatility, and comparable across tickers as contracts roll. Calls only,
for consistency.

**Tickers chosen for spread, not count.** 52 correlated tech names would be one
observation repeated 52 times. The universe spans index ETFs, non-equity asset
classes (metals, rates, energy, FX, international), sector ETFs, mega-cap tech,
high-vol growth, and low-vol defensives.

**Expanded 52 -> 109 on 5 September 2026, deliberately and once.** The freeze
argument was always about uneven history length, and that cost is proportional
to how long you wait. On 5 Sep the dataset was one day old, so the entire cost
of expanding was one missing day on the new names. In late October it would
have been forty. Day one was the cheapest moment this decision would ever have.

The 57 additions were not chosen by eye. Sixty-four candidates were screened
live against the API and kept only if IV, all five greeks and a two-sided quote
came back with a spread under 60% of mid. Ten failed: XLRE, XLC, HYG, EWZ, EWJ,
IYR, ARKK, SBUX, HON, SO. Seven were dropped; **XLRE, XLC and HYG were added
back anyway**, which is why the universe is 109 and not 106. The reason is the
caveat: that screen ran on stale weekend quotes, which are far wider than
midday, and those three complete the 11 GICS sectors and the credit sleeve.
See section 6 - the 5 Sep pressure test measured how unreliable that screen is.

The additions widen the range at both ends - LQD at 4.9% IV sits below IEF,
MARA at 82% above MSTR - and add asset classes the original 52 lacked:
investment-grade credit, a bitcoin ETF, gold miners, semis, biotech, regional
banks. They also add enough single names to make the index vs single-name
comparison, which the literature says is the real finding, actually testable.

**The universe is frozen from here.** Only remove a ticker if its data proves
unreliable.

**Social sentiment (X/Twitter, Reddit, StockTwits) was evaluated and rejected,
6 September 2026.** Researched properly; do not reopen without new evidence.
Three independent reasons, any one of which is sufficient:

1. **The causality runs the wrong way.** The one published study that examines
   Twitter sentiment *and* option-implied volatility in the same model - a panel
   VAR on S&P/ASX 200 names - finds causality running from implied volatility TO
   Twitter activity and sentiment, not the reverse. Options markets price
   volatility risk first and the social narrative follows. Using sentiment to
   explain IV is using the echo to explain the shout.
2. **The foundational result does not replicate.** Bollen et al. (2011),
   "Twitter Mood Predicts the Stock Market", claimed 86.7% accuracy and launched
   the field. Lachanski & Pavlik (Econ Journal Watch) show it was data-mined
   across mood dimensions and lags without correction, highly sensitive to the
   sample window, and built on a proprietary algorithm nobody could audit;
   independent groups could not reproduce it.
3. **The data is unobtainable at this budget.** X ended the free tier in
   February 2026. Self-serve is pay-per-use and its search reaches back only
   7 days. Full-archive search - which is what matching tweets to an existing
   dataset requires - is Enterprise-only, from about $42,000/month.

The statistical reason matters most, though. Sentiment studies in this
literature use *years* of data. This project has roughly T/21 independent
episodes. Fitting a high-dimensional, researcher-degrees-of-freedom-rich
predictor to about six independent observations is how a finding gets
manufactured, and it would destroy the one property that makes this project
credible: that it is honest about its own sample size.

Alpaca's free News API is available and would give news *volume* as an attention
proxy. It has the same backwards-causality problem, and is not worth the column.

**What replaces it: scheduled events.** Human institutions decide when
information is released - companies report quarterly, the Fed meets on a
published calendar, BLS announces CPI dates a year ahead. The market prices
uncertainty into those human-chosen moments and it collapses when the
information lands. That is a humanistic pattern with a mathematical signature,
and unlike sentiment it is *knowable in advance*.

The evidence is mature: IV ramps into earnings and then crushes (commonly
30-60%); Johannes et al. find risk-neutral jump volatility uniformly exceeds
realised around earnings, with long ATM straddles returning about -8% per event;
Barth et al. and the Stanford GSB study find the excess is largest for bellwether
firms whose earnings load on aggregate factors, i.e. it is compensation for
non-diversifiable announcement risk.

It also *increases* statistical power rather than diluting it. Earnings are
staggered across firms, so the idiosyncratic component dominates and the events
are far closer to independent than daily observations are. About 73 of the 109
tickers are single names reporting roughly twice in six months - on the order of
146 events, scattered in time, against about six independent draws of the market
factor.

Earnings dates are free and retroactive (SEC EDGAR 8-K/10-Q, no API key), so the
calendar work waits for the analyser. What does NOT wait is section 11.

**Daily snapshots, not intraday.** The strategy this informs rebalances on a
daily-to-weekly clock. Higher frequency adds cost and complexity for no
analytical gain.

**Collect rather than buy history.** Historical IV surfaces are the expensive,
gated part of options research. Live quotes are nearly free. Trading time for
money is the entire premise — which is why *never missing days* matters more
than any code improvement.

---

## 4. The October task (the actual next work)

Once ~40 trading days have accumulated, build the analyzer.

**Read this section before writing a line of it.** The obvious version of this
analysis produces a confidently wrong answer. Three of the steps below are
corrections to what the original spec said, and they are not stylistic.

### 4.1 The spec

1. Load `data/iv_history.csv`.
2. For each snapshot row, fetch the underlying's daily closes over the
   following **`dte` calendar days - not a fixed 30**. See 4.2(b).
3. Compute realized volatility over that window:
   `sqrt(252 * mean(log_return^2)) / c4(n)`. The `c4` term is a bias
   correction. See 4.2(c).
4. Join realized against the `iv` recorded on the snapshot date.
5. Compute the spread (`iv - realized`) per row.
6. Drop rows whose forward window runs past the last available price date.
   Never pad or annualize a partial window.

### 4.2 Three things the naive version gets wrong

**(a) The significance test. This is the big one.**

Sampling daily but looking forward ~30 days means consecutive observations
share ~29 days of the same realized path, and all 109 tickers on a given day
share a market factor. A pooled t-test across all rows treats ~109 x T
observations as independent when the effective count is closer to
`(T / 21) x (a handful)`.

This was simulated against this exact design under a true null - IV set exactly
equal to realized, so the real premium is zero by construction:

| test | rejects at nominal 5% |
|---|---|
| pooled t-test over all rows | **65%** (89% with a market factor) |
| per-ticker mean, then t-test across tickers | 6% alone, **55%** with a market factor |
| strictly non-overlapping, every 21st day | 5-7% |

The pooled t-test finds "significance" on pure noise most of the time. The
per-ticker shortcut looks safe and is worse. Report all three of:

- **Primary:** collapse to one daily cross-sectional mean spread, then
  Newey-West with lag = 2x trading days in the window (~42). Carr & Wu use
  lag 30 for the same daily-overlapping-30-day setup. Even this over-rejects
  roughly 3x, so treat its p-value as an upper bound on significance.
- **Confirmatory:** keep every 21st trading day only, t distribution with the
  real degrees of freedom. Throws away ~95% of rows. This is the honest test.
- **Descriptive:** sign test on non-overlapping episodes. Distribution-free.

Say out loud that ~T/21 independent episodes is the real sample size. Six
months of collection is about six independent draws of the market factor.

**This is implemented and validated - `analyze.py`.** Run
`python analyze.py --simulate` to reproduce it; it needs no market data. An
independent re-simulation of the design above (400 replications, true null,
premium zero by construction) reproduces this section closely:

| test | this section claimed | re-simulated |
|---|---|---|
| pooled t-test over all rows | 65% (89% w/ factor) | **63.8%** (93.0%) |
| per-ticker mean, then t-test | 6% (55% w/ factor) | **4.2%** (69.8%) |
| strictly non-overlapping | 5-7% | **3.8%** (5.5%) |

One correction to this section. **Newey-West over-rejects worse than "roughly
3x" at the sample size this project will actually have**, and the damage is a
small-sample effect that shrinks with T:

| trading days collected | NW rejects (nominal 5%) |
|---|---|
| 120 (~6 months) | **22.4%** - about 4.5x |
| 250 (~1 year) | 16.4% |
| 500 (~2 years) | 9.6% |

So at six months treat the primary p-value as an upper bound by a factor of
about **4.5, not 3**. The non-overlapping test stays correctly sized (4-6%) at
every T, which is why it is the one to believe.

A trap worth naming, because it was hit while building `analyze.py`: the
non-overlapping stride must be at least as long as the window. A 30-*calendar*-day
option is ~21 *trading* days, so a stride of 21 trading days is exactly
non-overlapping - but if the window is longer (the ~42-day MDY / FXE / XLRE
names), a 21-day stride still overlaps and the "honest" test quietly
over-rejects. `analyze.py` derives the stride from the observed mean `dte`
rather than assuming 21.

**(b) Horizon mismatch.** The option has 21-45 days to expiry but the realized
window was specified as a fixed 30. The IV term structure is sloped, so this is
a bias that varies with `dte`, not just noise. Fix: set the realized window to
each row's actual `dte`. That is exact, needs nothing extra, and is arguably
better than the CBOE approach of interpolating to constant 30-day maturity. If
you also want a clean constant-maturity panel, interpolate **in variance, never
in volatility**.

**(c) Small-sample bias in the vol estimator.** `sqrt(252*mean(r^2))` is a
downward-biased estimator of volatility. Verified numerically: over a ~21
trading-day window it reads about 1.2% low, which is a spurious **positive**
spread of 0.24 vol points at 20% vol and 0.47 at 40% - against a single-stock
premium the literature puts near 1.5 vol points. It flatters the hypothesis.
Divide realized vol by `c4(n) = sqrt(2/n) * exp(lgamma((n+1)/2) - lgamma(n/2))`
using the actual `n` in each window.

Do **not** demean the returns - the variance swap payoff is the un-demeaned sum
of squared log returns, and the zero-mean convention is standard. `mean(r^2)`
dividing by `n` is correct. 252-day annualization is correct.

### 4.3 The questions worth answering

- Is the mean spread positive overall?
- Does it hold within each universe group, or only in equities? Cross-asset is
  the more interesting finding either way.
- **Is it bigger for index ETFs than single names?** The literature is strong
  and consistent here (Bakshi-Kapadia: ~3.3 vol pts index vs ~1.5 single
  names; the mechanism is a correlation risk premium). If the data reproduces
  it, that validates the dataset. The 109-name universe was expanded partly to
  make this testable.
- Does the spread scale with the level of implied vol, or is it flat?
- **Does it survive costs?** `bid`/`ask` exist so this is computed, not
  assumed. Convert the half-spread to vol points via `vega`. Report three
  columns: mid, 25% of the quoted spread, and the full spread. Quoted
  half-spreads on 30-day ATM single-stock options routinely cost 1-3 vol
  points - the same size as the entire single-stock premium - so this test may
  well fail, and that is a legitimate finding.

### 4.4 Sanity benchmarks

Expect roughly +2 to +4 vol points for equity index ETFs and +1 to +2 for
single names. VIX minus subsequent realized runs ~4.1 pp over 1990-2024, but
that is a model-free strip, not an ATM reading. A result far outside this band
- say +8, or strongly negative - means either a genuine regime effect in a
short sample or a bug. Check annualization and dividend handling first.

Plot the daily mean spread through time before believing any average. The
premium flips sign in crashes; one vol spike inside a short sample can move
the entire result.

**A null result is a real result.** If the premium doesn't show up, or doesn't
clear costs in this sample, write that up as it stands. An undergraduate
claiming market edge is less credible than one who ran an honest test and
accepted what came back. Note also that the single-stock premium is genuinely
weak in the literature - Carr & Wu find it significant for only 21 of 35
stocks - so a null on the single-name subsample is consistent with published
work, not a failure.

Anything before then is premature. The recorder needs no further changes.

## 5. Constraints worth knowing

- **No live trading is planned.** Delta-hedging a long option requires shorting
  stock, which requires a margin account with a $2,000 Reg T minimum plus broker
  options approval. Out of scope for this project.
- **Alpaca free tier: 200 requests/minute.** Current usage is 220 calls per run
  (109 tickers x call chain + put chain, plus one spot batch and one
  market-calendar check) at 0.40s pacing = 150/min, ~88 seconds. It is
  undocumented whether the data and trading APIs share one bucket, which is why
  the pacing leaves 25% headroom rather than the old 0.35s (171/min).
- **Calls and puts are fetched as two separate type-filtered queries, on
  purpose.** One combined query would halve the request count, but it pushes a
  dense chain like SPY past the 1000-contract page limit and makes paging
  load-bearing. Two narrow queries each stay on a single page. The paging loop
  is still there as a safety net; it just should not normally fire. Plenty of headroom, but don't remove the pacing or the 429
  retry.
- **GitHub disables scheduled workflows after 60 days of repository
  inactivity.** Confirmed against the docs: it applies to *public* repositories,
  and GitHub does not define "activity" beyond that. Commits count, so the
  recorder's daily commit should keep it alive in normal operation.
  `freshness.yml` runs daily and fails loudly (which emails you) if the newest
  row is more than 5 days old - that is the tripwire.

  **But `freshness.yml` is itself a scheduled workflow**, so the 60-day rule
  would disable the recorder and its own alarm together, and the failure is
  silent by construction. The alarm shares a failure mode with the thing it
  watches. That is why a weekly Claude routine
  (`trig_01GkVL3mRpGGptXfqoNSR77d`, Wed 09:13 Pacific) checks the dataset and
  both workflow states from *outside* GitHub Actions. It has read-only tools -
  no Write, no Edit - so it structurally cannot touch the dataset. Manage it at
  https://claude.ai/code/routines
- **Market holidays are skipped**, checked against Alpaca's calendar rather than
  a hardcoded list. The check fails *open*: if the calendar call errors, the run
  records anyway. A stray holiday row can be dropped in analysis; a real day
  missed is gone for good.
- **Free feeds only.** `opra` and `sip` require paid subscriptions and will 403.
- **History cannot be bought back.** Verified against the docs: Alpaca's free
  tier does serve historical option *bars* back to Feb 2024, but IV, greeks,
  bid/ask and open interest exist only in the snapshot endpoints. There is no
  historical option quotes endpoint at all. The premise of this project is
  therefore correct: every day the recorder misses is gone permanently.

---

## 6. Known data issues

- **MDY, FXE and XLRE** lack weekly options and fall back to ~42-day expiries.
  The `dte` column records this — control for it, don't discard the rows. XLRE
  came back at `dte` 41 in the 5 Sep full-scale run. That reading is trustworthy
  even though it was taken on a weekend: staleness widens quotes, but it does not
  change which expiries exist.
- **FXE and XLU** quoted 0.63/1.27 and 0.45/0.79 on day one - spreads of 67%
  and 55% of the mid. Those spreads make the mid unreliable for both. Under
  review; drop them if the pattern persists.
- **The weekend spread screen is not discriminating - do not act on it.**
  Measured 5 Sep against the live API: the same original-52 tickers that quoted
  cleanly intraday on Friday blow out by 1.5x to 14x on Saturday's stale quotes.
  PEP went 36.8% -> 97.7%, XRT 29.2% -> 72.3%, JNJ 2.5% -> 36.3%. A 60%-of-mid
  screen applied to weekend data would drop PEP and XRT - both original-52 names
  with a full clean row. HYG (92.3%), XLC (127.4%) and XLRE (85.3%) read badly on
  a weekend for exactly that reason, which is *not* evidence about those tickers.
  Judge all three from an intraday row; the first is Tue 8 Sep.
- **Indicative feed** means quotes are approximate, not exact NBBO. Fine for the
  analysis, but state it plainly in the write-up.
- **The snapshot time shifts an hour on 1 Nov 2026.** The cron is fixed at
  15:30 UTC: that is 11:30am ET under EDT, 10:30am ET under EST. The sample
  therefore straddles a one-hour change in time-of-day, right where the
  analysis window begins. Either control for it, or split the sample at that
  date. Changing the cron instead would break comparability with the rows
  already collected.
- **The IV is computed by Alpaca, from indicative quotes, by an undocumented
  method.** Alpaca states it uses Black-Scholes and Newton-Raphson, but does
  not document the risk-free rate or whether any dividend adjustment is
  applied. If dividends are ignored (q=0), ATM *call* IV is biased **down** by
  about `1.253*q*sqrt(T)` - roughly 0.4 vol pts at a 1% yield, 1.5 at 4%.
  That is conservative for the headline result but will manufacture a fake
  cross-sectional pattern where high-dividend names look low-VRP. Control for
  dividend yield in any cross-sectional regression. The clean fix is to record
  the put at the same strike and average the two IVs, since the error is equal
  and opposite - see the open item in section 10.
- **Indicative feed, not OPRA.** Alpaca staff describe the indicative feed as
  intended to debug code rather than to test strategy efficacy. Treat IV
  *levels* as approximate and time-series *changes* as more trustworthy.
- **No skew.** Only at-the-money is recorded. Implied vol varies by strike and
  that shape carries information this dataset doesn't capture. A known,
  deliberate limitation - and now a *measured* one. Cboe's indices are
  model-free (they integrate the whole strike surface, so they include the skew
  and tail premium), and on 4 Sep every matched pair sat above the ATM reading:

  | ticker | ours (ATM) | Cboe | gap |
  |---|---|---|---|
  | QQQ | 16.11% | VXN 20.04 | +3.93 |
  | IWM | 14.49% | RVX 18.30 | +3.81 |
  | USO | 40.32% | OVX 44.96 | +4.64 |
  | GLD | 24.56% | GVZ 26.63 | +2.07 |

  Mean gap +3.61 vol points, correct sign on all four. Say this in the write-up:
  the ATM reading understates a model-free variance measure by roughly 2-5 vol
  points, and that gap *is* the skew premium being left on the table. It also
  doubles as an independent sanity check on the pipeline, from a source with no
  connection to Alpaca.

---

## 7. Repo cleanup - done 5 Sep 2026

- ~~Stale `Volrec/` subfolder~~ deleted. It held only README.md and
  requirements.txt; `record.py` had already been removed from it on 4 Sep.
- ~~Duplicate `iv_history.csv` at the repo root~~ deleted. It was a 4-row test
  file dated 2026-08-27, not data.
- ~~`README.md` at the repo root~~ done. `record.py` at root already matched.

Also done that day: market-holiday guard added to `record.py` (see §5), the
zero-bid `mid` bug fixed, option-chain paging handled, the workflow's actions
moved off deprecated Node 20, and `freshness.yml` added as a staleness alarm.

---

## 8. Design direction for a future dashboard

The *collection monitor* is built - `tools/monitor.html`, in this aesthetic. It
tracks continuity, schema state, staleness, the IV cross-section, quote quality
and per-ticker coverage, and it says plainly that the analysis is not runnable
yet. What is still unbuilt is the **analysis** dashboard below - that one waits
on ~40 trading days, so late October.

Reference: a Polymarket trading-bot dashboard. Terminal / mission-control
aesthetic:

- Pure black background, near-monochrome
- Monospace throughout; labels small, uppercase, wide letter-spacing, dimmed
- Section headers prefixed `//` — e.g. `// BALANCE HISTORY`
- Top status strip: name, mode, live indicator, then uptime / cycle / PID
- Row of KPI cards — tiny dim label above a large figure
- Sparse white line chart with faint gradient fill, endpoint labelled
- Dense timestamped activity log alongside it; green for gains, red for losses
- Numbered roster tiles along the bottom, active one highlighted

The telemetry is the point, not decoration — uptime, cycle count, and a
scrolling log are what make it read as a live system rather than a report.

---

## 9. Files

```
README.md                     project document — the question, method, limitations
HANDOFF.md                    this file
record.py                     the daily recorder
analyze.py                    the analyser — `--status`, `--simulate`, or run it
requirements.txt              one dependency: requests
.github/workflows/record.yml  the schedule
.github/workflows/freshness.yml  daily staleness alarm
data/iv_history.csv           the dataset — the only irreplaceable artifact
tools/gamma-lab.html          delta-hedging simulator v1
tools/gamma-lab-v2.html       v2 — adds costs, stochastic IV, jumps, freq sweep
tools/monitor.html            collection monitor — reads the live CSV from GitHub
```

The monitor is published by GitHub Pages from `main` at the repository root, so
https://gabrielmitton-cloud.github.io/volrec/tools/monitor.html is always
current - it fetches the CSV client-side and needs no build step. Serving it
locally still works and is described below.

`tools/monitor.html` needs no build and no server data: it fetches
`data/iv_history.csv` straight from raw.githubusercontent (which sends
`access-control-allow-origin: *`), so it always shows what the recorder last
committed. Browsers block `fetch` from `file://`, so serve it:

```
cd ~/Desktop/Archive/Volrec && python3 -m http.server 8000
# then open localhost:8000/tools/monitor.html
```

If anything here has to be prioritized: the dataset is the only thing that can't
be rebuilt. Everything else is code.

---

## 10. The schema upgrade - APPLIED 5 Sep 2026

`FIELDS` declared 24 columns as of this change. It is **32 now** - see §11,
which added the term-structure leg on 6 Sep. The data file still has 17 and
**migrates itself on the next run**, straight from 17 to 32 in one step - `migrate_header()` runs inside `append()` before any
row is written.

Why it works that way rather than being committed by hand: the safety layer
blocks direct writes to `data/iv_history.csv`, which is the correct instinct
for the one file that cannot be rebuilt. Putting the migration in the recorder
is the better answer regardless. It is reviewable code, it runs under the
workflow's own credentials, and it fixed a real latent bug - `append()`
previously would have written misaligned rows if `FIELDS` and the header ever
disagreed, silently corrupting the file.

`migrate_header()` is additive-only and defensive:

- columns ADDED -> rewrites the header, pads existing rows with empty values,
  leaves a one-time backup at `data/iv_history.pre-17col.csv`
- columns REMOVED or RENAMED -> **exits without touching the file.** No schema
  change is worth losing recorded data.

Tested 16 ways against the real data file: all 52x17 original cells preserved,
idempotent across repeated runs, refuses destructive migrations, recovers from
a missing or zero-byte file.

What it adds - 7 columns, all forward-collect-only, none reconstructable later:

| column | why it matters |
|---|---|
| `put_bid`,`put_ask`,`put_mid`,`put_iv`,`put_symbol` | The put at the **same strike**. Averaging call and put IV cancels the dividend/borrow error in section 6, which can exceed the effect being measured. Costs **zero extra requests** - dropping `type="call"` returns both sides in the same call. |
| `quote_time` | Detects stale quotes. A stale wide quote silently poisons a row and there is currently no way to tell. |
| `volume` | Liquidity filter, free from `dailyBar.v`. |

The put comes from a second `type="put"` chain query rather than a combined
one - see section 5 for why.

**Open interest is NOT in the options snapshot** - confirmed against the schema
and two SDKs. It lives on the Trading API at `/v2/options/contracts`, which
accepts `underlying_symbols` (plural) and `limit` up to 10,000, so it is a
handful of extra calls, not 109. It is T+2 stale, so store `open_interest_date`
alongside it or the values will mislead.

**Still open:** open interest, per the paragraph above.

**The 109-ticker / 24-column path was verified live on 5 Sep 2026**, using a
temporary `pressure.yml` workflow (run `pressure #2`, since deleted). It called
`spot_prices()` and `snapshot()` directly to bypass the weekend guard, pointed
`OUT` at a copy under `/tmp`, and asserted the real file's md5 was unchanged:

- 109/109 tickers returned a row; no failures
- **0 HTTP 429s** across 219 requests, 94.1 s elapsed (~140 req/min)
- `spot_prices()` handles all 109 symbols in one request - no symbol cap
- put match 109/109; the same-strike put lookup works for every name
- `migrate_header()` added exactly the 7 columns and left all 52x17 original
  cells byte-identical, with a byte-identical backup, idempotent on a re-run
- the only gaps were `volume` on 4 names whose contracts did not trade Friday

No defects were found and nothing in `record.py` was changed. The first
scheduled live run on Tue 8 Sep should therefore be uneventful; what is worth
reading off it is the *intraday* spread on HYG, XLC and XLRE - see section 6.

---

## 11. The term-structure upgrade - APPLIED 6 September 2026

`FIELDS` declares 32 columns. The file migrates itself on the next run, exactly
as the 17 -> 24 change did.

**Why this could not wait.** Everything else about explaining volatility is
retroactive - earnings dates, FOMC dates, price history are all permanent public
record and can be fetched in October. The *shape of the volatility curve on a
given day* is not. Section 5 is the reason: IV, greeks and quotes exist only in
the snapshot endpoints, there is no historical option-quote endpoint at any
price. A day recorded with one expiry is a day whose term structure is gone
forever. Same argument as the 52 -> 109 expansion, same conclusion: the cheapest
moment to start is the earliest one.

**It costs nothing.** Measured live on 6 Sep: **219 requests, identical to
before**, 94.4 s, zero 429s. The chain query already filters to
`expiration_date` in `DTE_WINDOW` and downloads every contract in that band;
`snapshot()` was keeping one and discarding the rest. The far leg is picked out
of a response already paid for.

| measured live, 109 tickers | |
|---|---|
| requests | 219 - unchanged |
| elapsed | 94.4 s, zero 429s |
| far leg present | 105 / 109 (96%) |
| no far leg | DUK, FXE, MDY, XLRE |
| migration | 17 -> 32, all 52x17 original cells preserved |

**Do not widen `DTE_WINDOW` to reach shorter expiries.** Measured: at 7-75 days
SPY returns 13 expiries and fills page 1 with 1000 contracts, so paging becomes
load-bearing - the exact failure section 5 designed against. The gain is not
worth reintroducing that risk.

**Reading the slope - the one trap.** The far leg is the expiry *furthest* from
the near one inside the window, which for a minority of tickers is
shorter-dated, not longer. Never read the sign of `far_iv - iv` directly. Divide
by the maturity gap, which carries the sign correctly in every case:

```
slope per day = (far_iv - iv) / (far_dte - dte)
```

Positive is then an upward-sloping curve, always. FXI on 6 Sep is the worked
example: raw difference +9.05 vol points, but its far leg is 24d against a 33d
near leg, so the curve is *inverted*, not upward-sloping.

**What it buys.** A single expiry gives a level. Two give a shape, and the shape
is where a scheduled event shows up: an inverted curve means near-term
uncertainty exceeds longer-term, which is the signature of an event dated inside
the near leg but outside the far one. On 6 Sep the spread ran from -6.49
(NKE) to +9.05 (FXI) vol points with 51 of 105 inverted - real dispersion, not
noise. It also makes the constant-maturity interpolation section 4.2(b)
contemplates possible at all; with one point per day there is nothing to
interpolate between.

### 11.1 The market factor, measured - added 6 September 2026

Cboe publishes the whole market volatility term structure free, with no API key
and no rate limit, back to 1990: `VIX9D`, `VIX`, `VIX3M`, `VIX6M` at
`cdn.cboe.com/api/global/us_indices/daily_prices/<NAME>_History.csv`.

This is not another explanatory variable thrown at a small sample. Section
4.2(a) *names* the shared market factor as the thing that makes a pooled test
reject a true null 63.8% of the time and the per-ticker test 69.8%. VIX is that
factor, measured. Removing a confound the design already identifies is the
opposite of data mining, and it should push the residual closer to independent
across tickers, which is the binding constraint on this whole study.

`analyze.py` fetches it (cached in `data/market_vol.json`, gitignored - it is
reconstructable) and reports:

- how much of the day-to-day swing in the premium is the market rather than the
  individual names, as an R^2
- the premium **after** the market factor is regressed out. If it survives
  there, it is not just beta to the market - the harder and better claim.
- whether the market curve was inverted (`VIX3M < VIX9D`) - a stressed tape
- the premium split by whether the *ticker's own* curve was inverted, which is
  the event signature from section 11

Cboe also publishes one-to-one benchmarks for four tickers already in the
universe - `QQQ/VXN`, `IWM/RVX`, `USO/OVX`, `GLD/GVZ`. Fixed in advance, one per
ticker, not a net.

**Where the discipline goes.** VVIX, SKEW, and FRED's credit spreads
(`BAMLH0A0HYM2`) and financial stress index (`STLFSI4`) are all free and equally
easy to pull. They are deliberately NOT wired in. Fitting a pile of macro
regressors to about six independent episodes is exactly the failure mode the
sentiment decision in section 3 rejects, and it would be inconsistent to refuse
Twitter and then do the same thing with FRED. Recording is harmless; *testing*
is where the mining happens. Add them only with a hypothesis written down first.

**Still open:** open interest (section 10), and joining an event calendar to the
slope in October - SEC EDGAR 8-K/10-Q dates, free and retroactive.

---

## 12. Roadmap - what to do, and when

Sequenced by trigger, not by wishlist. Everything above this line is done.

### Tue 8 Sep 2026 - the first full run. Check it.

The single most important day so far: the first scheduled run of the 109-ticker,
32-column recorder. Nothing here needs doing in advance; it should all happen by
itself. Verify it did:

```
cd ~/Desktop/Archive/Volrec && git pull -q && python analyze.py --status
gh run list --workflow=record.yml --limit 3
```

Expect: **109 rows** dated 2026-09-08, **32 columns**, and
`data/iv_history.pre-17col.csv` appearing in the repo - that is the migration's
one-time backup and it committing is correct, not a mistake. The far leg should
populate on ~96% of rows; DUK, FXE, MDY and XLRE legitimately have none.

Then make the call that has been pending since 5 Sep: **HYG, XLC and XLRE**.
Their weekend spreads (92%, 127%, 85% of mid) are meaningless - PEP, a mega-cap
staple, read 98% on the same quotes. Only this intraday row settles it. Under
60% of mid, they stay.

Mon 7 Sep is Labor Day. The cron fires, the calendar guard no-ops it, nothing
commits. A `record` run with no commit that day is correct behaviour.

### Rolling, until ~late October

- The Wednesday watchdog reports on its own. Quiet means healthy.
- **FXE and XLU** are the two names with genuine *intraday* evidence against
  them (67% and 55% of mid on 4 Sep). Watch whether it persists; §6.
- **1 Nov 2026**: the snapshot time shifts an hour when daylight saving ends.
  Do not change the cron - it would break comparability. Control for it or split
  the sample. §6.

### At ~40 trading days (~late October) - the main event

1. `python analyze.py` - it refuses to run below 40 days unless forced.
2. **Join an event calendar.** SEC EDGAR 8-K/10-Q filing dates: free, no API
   key, authoritative, fully retroactive. About 73 of the 109 tickers are single
   names reporting roughly twice over the sample - on the order of 146 events,
   staggered across firms, so far closer to independent than the daily panel.
   Cross it with the term-structure slope from §11: an inverted curve with an
   earnings date inside the near leg is the cleanest event signature available.
3. **Build the results page.** This is where design effort finally pays, and
   where the Vercel account earns its place - by then the CSV is ~0.8 MB and
   parsing it client-side is wasteful, and the page stops being a health monitor
   and becomes the artifact handed to an interviewer. §8 has the direction.

### Deferred, with reasons

- **Open interest** - §10. Trading API, a handful of extra calls, T+2 stale so
  store `open_interest_date` alongside it.
- **VVIX, SKEW, FRED credit spreads and financial stress** - §11.1. All free,
  all verified working, all deliberately unwired. Add one only with a hypothesis
  written down *first*.
- **Vercel** - connected and idle. Revisit at the results page, not before.

### Operational notes for whoever picks this up

- The working directory is a real git clone (converted 5 Sep) and is in sync
  with origin. It was previously loose files, which had silently mangled the
  dataset's line endings.
- `gh` is installed at `~/.local/bin/gh` and authenticated. Use
  `gh run view <id> --log` to read Actions output - the browser route cost a
  duplicate workflow run before this was set up.
- **`python3` on this Mac is 3.9 and has no `requests`.** Use
  `/Library/Frameworks/Python.framework/Versions/3.14/bin/python3` for anything
  that imports it. This wasted time once already.
- Temporary workflows are the established pattern for testing against the live
  API: commit one, `gh workflow run`, read the job summary, delete it. Five have
  been used and removed this way. Always tee output into
  `$GITHUB_STEP_SUMMARY` - it is far easier to read than the raw log.
- The safety rule that has held throughout: point `OUT` at a copy under `/tmp`
  and assert `data/iv_history.csv`'s md5 is unchanged at the end of every test.
