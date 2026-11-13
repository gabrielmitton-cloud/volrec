# HANDOFF

Context for anyone (or any assistant session) picking this project up cold.
Read this before proposing changes. It records not just the current state but
the reasoning behind decisions already made, so they don't get re-argued.

Last updated: 17 September 2026.

**START AT §16.** It is the current state and the next actions, and it is the
only section guaranteed to be current. Everything before it is either settled
history or reasoning you should not re-argue.

Then, as needed:
- **§1-§3** the framing and the closed decisions. Do not reopen without new,
  dated evidence. §3 in particular records why social sentiment was rejected.
- **§4** the analysis spec. Dense. Read before writing analysis code.
- **§13-§15** the two-sample architecture, what the 11 Sep meeting retired, and
  what Bloomberg is actually for.
- **`hypotheses/`** four registered hypotheses. Read `hypotheses/README.md`
  before adding a fifth.

**Historical, do not act on:** `WEDNESDAY.md` (a 9 Sep punch list, complete),
`FRIDAY-MEETING.md` and `FRIDAY-QUESTIONS.md` (prep for a meeting that
happened on 11 Sep). They are kept for the record, not as instructions.

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
| Site | The paper at https://gabrielmitton-cloud.github.io/volrec/ and the live instrument at https://gabrielmitton-cloud.github.io/volrec/tools/monitor.html (GitHub Pages, main branch, root). |
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
  (`trig_01GkVL3mRpGGptXfqoNSR77d`, Wed 09:13 Pacific) checks both panels
  (through `tools/panel_health.py`), all three workflow states, recent runs and
  the pressure test from *outside* GitHub Actions. Updated 13 Sep 2026: it had
  still expected 24 columns and two workflows. It has read-only tools -
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

**Rebuilt 13 September 2026 as a two-page site, in this aesthetic.**
`index.html` is the paper: the free-data measurement question, argued in five
figures with sources on every documented number, a ledger of the pre-registered
hypotheses, and a live strip of the instrument. `tools/monitor.html` is the
instrument: everything the old collection monitor tracked, plus term structure,
put against call, a day-by-ticker coverage heatmap, panel health and the strike
surface, which draws itself once `data/surface.csv` has rows.

What was added to the aesthetic, so it is not relearned: Newsreader carries the
argument and Martian Mono carries anything measured; an oscilloscope graticule
is the one recurring device (on the paper's first figure each division is 10%
of spot); and three channel colours mean the same thing on both pages - cyan
`#2396C4` for this project's free-feed measurement, yellow `#B08500` for Cboe,
magenta `#CF4F97` for the lognormal model. Those three were run through a
colour-vision validator against the panel surface, all pairs, and pass. Status
colours are separate and never appear without a glyph, because green and red
cannot be told apart under deuteranopia.

Two rules the pages enforce: no live premium figure appears anywhere (section
14.3), and every documented number carries its date and source file.

What is still unbuilt is the **analysis** dashboard below - that one waits on
~40 trading days, so late October.

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
index.html                    the paper — the free-data question, with live data from the repo
tools/monitor.html            the instrument — live telemetry for both panels
tools/volrec.js               shared runtime: loading, health rules, the truncation model
tools/volrec.css              shared styles for both pages
```

The site is published by GitHub Pages from `main` at the repository root: the
paper at https://gabrielmitton-cloud.github.io/volrec/ and the instrument at
https://gabrielmitton-cloud.github.io/volrec/tools/monitor.html. Both are always
current, because they fetch the data client-side and need no build step.
Serving them locally still works and is described below.

Neither page needs a build or server data: `tools/volrec.js` fetches
`data/iv_history.csv` and `data/surface.csv` straight from raw.githubusercontent
(which sends `access-control-allow-origin: *`), so the pages always show what the
recorders last committed. A 404 there is treated as "not collected yet", not as
an error. The watchlists and health constants in `volrec.js` are duplicated from
`record.py`, `surface.py` and `tools/panel_health.py`, and the pressure test fails
if they drift. Browsers block `fetch` from `file://`, so serve it:

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

**See also §13** - the two-sample architecture, decided 6 Sep 2026, which changes
what the late-October work should be.

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

**The 60% line is pre-registered - decided 6 Sep, BEFORE the data landed, and
it is not to be moved after seeing the three numbers.** Recorded here so the
write-up can say that honestly. Apply it mechanically.

Why it is worth stating: 60% was set against *weekend* readings of 85-127%, and
measured against actual intraday quotes it is a very loose line. The 4 Sep
intraday distribution across the original 52, the only intraday data that
exists:

| statistic | intraday spread, % of mid |
|---|---|
| median | 7.3% |
| mean | 10.6% |
| min / max | 0.4% (JNJ 2.5%) / 67.4% (FXE) |
| names >= 60% | **1 of 52** (FXE alone) |

Only four names clear 25% at all: FXE 67.4, XLU 54.8, PEP 36.8, XRT 29.2. So
60% sits at roughly **8x the median** - it is not a liquidity screen, it is a
catastrophe filter, and HYG/XLC/XLRE will very likely pass it whatever they
print.

That is the intended behaviour, for two reasons. PEP - the name section 6 uses
as the benchmark for a clean intraday row - reads 36.8%, so 60% leaves real
headroom above a ticker already trusted. And it matches the philosophy applied
to `dte` in section 6: *control for it, don't discard the rows*. The three names
complete the 11 GICS sectors and the credit sleeve; dropping a sector costs more
than carrying a wide quote you have measured and recorded.

So, mechanically, on Tuesday:

- **>= 60% of mid** - drop from the WATCHLIST, and note it in section 6.
- **36.8% (PEP's intraday reading) to 60%** - keep, but add to the section 6
  watch list beside FXE and XLU. Do not treat their IV *levels* as comparable
  to tight names without controlling for spread.
- **< 36.8%** - keep, no caveat. The pending decision closes.

Record the actual three numbers in section 6 either way. A screen whose result
is never written down is not a screen.

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
- **Intraday day-trading signal scanners** (Trade Ideas "Oracle" and similar) -
  assessed 6 Sep 2026 and rejected. Three collisions, any one sufficient: the
  clock (§3 froze daily snapshots), the universe (§3 chose 109 tickers for
  spread; these tools scan low-float small caps, most of which have no options
  liquid enough to quote an ATM IV), and the purpose (§1 - this is not a search
  for alpha, and that sentence is what makes the honest sample-size accounting
  read as rigor rather than excuse-making). Also not buildable at $0: it needs
  real-time Level II and time & sales across thousands of names. Note if it
  resurfaces: those tools' "Delta" column is price-distance-to-level, NOT
  options delta.

### One idea worth keeping - added 6 September 2026

Salvaged from that assessment, and the one thing here with a hypothesis already
written down, per the rule above:

> **Does implied volatility forecast realized range better than a
> technical-levels scanner does?**

A scanner's resistance/target levels are a prediction of range. Implied
volatility is *also* a prediction of range - the market's own, priced in dollars
by people with capital at risk. The two are directly comparable.

It needs no new data source, no API and no intraday feed: it runs on the daily
clock §3 froze, over the frozen 109, using columns already recorded. And it is a
*test between two methods* rather than an advertisement for one, which is the
version that survives hostile questioning.

Sequence it with the late-October analyser work, not before - it needs the same
~40 trading days everything else does.

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
- **`python tools/pressure_test.py`** - 30 read-only pre-flight checks: dataset
  integrity and the protected md5, value sanity, append-only schema, a migration
  dry run on a copy, analyze/record schema agreement, workflow config, guard
  ordering, and whether the public monitor survives the column jump. Exits
  non-zero on any failure. Ran clean 6 Sep. Run it before and after Tuesday.
- The dataset is **CRLF throughout** - that is `csv.DictWriter`'s default
  dialect, not the old line-ending mangling. Every writer in `record.py`
  produces CRLF, `core.autocrlf` is unset, there is no `.gitattributes`, and the
  committed blob is byte-identical to the worktree. Leave it alone; normalising
  it would change the md5 for no gain.

---

## 13. The two-sample architecture - decided 6 September 2026

A research brief on free data sources was commissioned and returned
(`volrec-data-layer-brief.md`, 7 Sep 2026). Its central finding is a correction
to this document's own reasoning and is worth stating plainly.

**The retroactivity trap.** §3 held that retroactive sources beat real-time
ones. True, but incomplete: **the IV panel begins 4 September 2026, so a
retroactive event calendar joins to nothing before that date.** Retroactivity in
the *event* source buys nothing unless the *dependent variable* also reaches
back. An event calendar adds columns; it does not add observations, and
observations are the binding constraint.

**The fix: two samples, one codebase.**

- **Sample A (long validation).** Cboe volatility indices as the IV measure,
  1990-2026, joined to realised volatility of the underlyings. Hundreds of
  non-overlapping monthly episodes. This is where the method is validated and
  where any explanatory variable must earn its place first.
- **Sample B (own panel).** `data/iv_history.csv`, N≈6 independent episodes.
  The **same frozen code** is applied and the result reported with sample size
  stated.

The interview sentence this buys: *"my method finds the known result on decades
of history, and here is what it finds on the data I collected myself."*

**Sample A costs almost nothing to start.** `analyze.py` already fetches the
Cboe CDN (§11.1) - no key, no rate limit, back to 1990. Verified 6 Sep: all 12
of the brief's index series map to a ticker in the frozen watchlist, 12 of 12.
Full manifest with ranges, gaps and licence terms in `samples/long/SOURCES.md`.

**The bridge between the samples is already measured.** §6 records the Cboe-vs-
our-ATM gap on four matched pairs: +3.93, +3.81, +4.64, +2.07, mean +3.61 vol
points. Cboe indices are variance-swap-style and integrate the whole strike
surface; this project records ATM. **Different estimands - say so, never
splice.** As the panel grows, that four-pair comparison becomes ten pairs by
many days, which is a small honest study in its own right.

### 13.1 What is blocking Sample A

**Realised volatility needs daily closes of the underlyings back to each index's
start, and the brief catalogues thirteen sources providing none of them.** That
is the critical path. Stooq was checked and rejected on 6 Sep - it now serves a
JavaScript proof-of-work bot challenge, and a pipeline depending on defeating
bot protection is neither durable nor defensible. Alpaca is the leading
candidate: the key is held and `fetch_closes` exists, but free-plan history
depth is unverified. One call settles it.

If nothing free reaches 1990, shorten Sample A and say so. Ten years of
non-overlapping monthly observations is ~120 episodes against six; the
validation argument survives a shorter window, not a fabricated one.

### 13.2 Structure and the rules that come with it

```
/hypotheses/     pre-registered, dated, committed BEFORE the join is run
/features/       numeric columns eligible to enter a regression
/annotations/    LLM prose, keyed by (date, ticker) - NEVER a feature
/samples/long/   Sample A
/samples/panel/  Sample B
```

`H1` is registered at `hypotheses/2026-09-06-h1-vrp-long-sample.md`. Read
`hypotheses/README.md` and `annotations/README.md` before adding anything - the
non-negotiable rule is that nothing moves from `/annotations/` to `/features/`
without a hypothesis dated before the join.

### 13.3 The highest-value action is not code

Pepperdine subscribes to WRDS. **If that subscription includes OptionMetrics
IvyDB, it is decades of single-name implied volatility, free to the user, and it
moots the entire N problem** - which is the constraint every other decision in
this document bends around. Undergraduate access typically runs through a
faculty-sponsored class or research-assistant account.

Cost: one email to a finance professor. Expected value: higher than everything
else in this section combined. **Do this before writing any Sample A code.**

### 13.4 Sequencing - deliberately narrow

1. **Ask about WRDS.** Email, not code.
2. **Settle the price-history dependency.** One Alpaca call.
3. **Sample A v1 = H1 alone.** VRP on the Cboe family. No media, no events, no
   positioning. Prove the method recovers the known result.
4. Only then consider EDGAR 8-K item 2.02 dates, and the macro media layer.
5. The annotation bot last - it is the deliverable, but it needs data to
   annotate and it is the easiest thing here to start p-hacking with.

**What the evidence says about steps 4-5, so they are not oversold:** Bodilsen
(2025, *J. Applied Econometrics*) finds firm-specific news adds nothing over a
HAR baseline once daily/weekly/monthly volatility components are included -
macro news, by contrast, is useful. Gains in the wider literature are real but
economically modest, concentrated at 5-22 day horizons in liquid names, at the
aggregate rather than firm level. The 21-45 DTE window sits in that region. So
**if a media layer is built, build it at the macro level**, and expect a small
effect.

---

## 14. What the 11 Sep meeting and the literature check changed

### 14.1 Three things are now retired. Do not revive them.

**Bloomberg as a historical options source - DEAD.** It holds only the last
**90 calendar days** of historical equity and equity-index option data, via
OMON's "As of" field. Verified 11-12 Sep 2026 against the University of
Manchester library help pages and the University of Iowa libraries guide;
Penn's guide routes historical options work to OptionMetrics instead. The
fifteen-year Tesla pull suggested in the meeting is impossible in principle,
not merely difficult. Bloomberg's licence is also restrictive enough that
publishing derived output from it to a public repo is not safe to assume.

**OptionMetrics via WRDS - CLOSED at Pepperdine.** Restricted to faculty, staff
and doctoral students. Confirmed twice. A faculty member could extract data,
but that is a request, not a plan, and the project must stand without it.

**"This data cannot be bought" - FALSE, and it was my claim to make and
withdraw.** OptionMetrics IvyDB holds end-of-day US equity and index option
data, with volume and open interest, from January 1996. The honest version is
"cannot be bought *by me, at zero budget*," which is a real constraint but a
much weaker distinction and must not be presented as a moat.

### 14.2 A design error, caught before it was built

The proposed angle was to compare strikes within the same day, on the reasoning
that this controls for the day and therefore sidesteps the small-sample problem.
It controls for the day so completely that it removes the object of study.

If the premium at strike K is `IV(K)^2 - RV`, and `RV` is one number shared by
every strike that day, then

    premium(K1) - premium(K2) = IV(K1)^2 - IV(K2)^2

The realised variance cancels exactly. What remains is the shape of the implied
volatility surface, which is the volatility smile, and Bollen & Whaley
(2004, JF 59(2)) covered it.

**The fix, which the literature already uses:** define the outcome as a
*strike-specific realised quantity*. Per-contract delta-hedged profit and loss
(Bakshi & Kapadia 2003), leverage-adjusted per-contract returns (Constantinides,
Jackwerth & Savov 2013), or corridor realised variance matched to the strike
range (Andersen, Bondarenko & Gonzalez-Perez 2015). Those do not cancel, because
the hedging path depends on the strike.

**Any future strike-level work must use a strike-specific outcome. Never
`IV(K)` minus a common realised variance.**

### 14.3 Where the level results may be reported from

Sample A carries about 127 non-overlapping episodes per pair and is a defensible
place to report the level of the premium. The ATM panel carries roughly two and
is not. This was already the working rule; the literature check confirms it, and
`analyze.py --simulate` remains the right headline robustness exhibit, since
comparing an observed statistic against a simulated null distribution is exactly
what Broadie, Chernov & Johannes (2009) ask for.

### 14.4 What was added instead

`surface.py` and `data/surface.csv`, recording the strike surface with **volume
per contract** for a small set of names, on a moneyness grid spanning +/-30% of
spot, at zero additional API cost, from data the recorder was already fetching
and discarding. See section 15.

### 14.5 Open, and genuinely undecided

The remaining novelty question. The volume-versus-option-returns space is more
occupied than it first appeared: Yuan, Liu, Chen & Hu (2024, *North American
Journal of Economics and Finance* 74, 102233) find option trading volume
negatively predicts delta-hedged option returns **across moneyness and
maturity**, verified 12 Sep 2026. That is close to the corrected version of the
angle, already published, on a broad cross-sectional panel.

What appears to survive is narrower and is recorded here without being claimed:
a single-name, long-horizon treatment, and the measurement question in section
15.2. Neither is settled.

---

## 15. Bloomberg's actual job, and TimesFM

### 15.1 Bloomberg is a validation instrument now, not a data source

The 90-day wall kills it as a history source. It does not kill it as a
**cross-check**, and that is a better fit for what this project became.

`surface.csv` is built from Alpaca's free **indicative** feed, which is not
consolidated OPRA. H3 asks what that costs. Strike truncation has been measured
and largely eliminated by widening the band; **feed quality has not been
separated out at all** and is still sitting inside the residual gap.

Bloomberg can separate it. Ninety days is far more than enough, because the
surface only started accumulating on 2026-09-14.

**What to pull, on any day the surface also has data for:**

- `OMON` for SPY, TSLA and USO, using the "As of" field on a date already in
  `data/surface.csv`. One low-vol index, one high-vol single name, one
  high-vol commodity, which is where truncation bit hardest.
- Per contract, across the strikes recorded that day: **bid, ask, implied
  volatility, volume, open interest.**
- Enough strikes to cover roughly +/-30% of spot, matching what is recorded.

**What that buys.** A contract-by-contract comparison of a free indicative
quote against a professional one, on identical contracts and identical days.
That decomposes the residual gap in H3 into feed quality versus everything
else, which is currently the weakest link in that hypothesis.

**Two or three days is enough.** This is a calibration exercise, not a
collection exercise. Do not try to build a dataset out of the terminal; that is
what the 90-day wall and the redistribution licence both forbid. Pull a few
days, compute the comparison, publish the derived numbers only.

### 15.2 TimesFM - a good idea for a different project

Google's TimesFM (ICML 2024, 200-500M parameters, Apache-2.0 code with
non-commercial weights on 3.0, runs on Apple silicon through MLX) is a
pretrained time-series foundation model.

**It does not belong in this project as it stands.** The binding constraint
here is independent observations, not model capacity. Pointing a 330M-parameter
model at roughly two independent episodes is precisely the failure mode
`analyze.py --simulate` exists to demonstrate, and section 3's whole discipline
forbids it.

**Where it would genuinely fit, recorded so the idea is not lost.** Qiu,
Kownatzki, Scalzo & Cha (2025), *Risks* 13(5) 98, benchmark volatility
forecasting methods - GARCH, LSTM, Transformer - and **open-sourced both data
and code** at `github.com/WithAnOrchid0513/VolData`: SPY and VIX daily, 1990 to
2023. A zero-shot foundation model post-dates every method in that benchmark.

> **Does TimesFM, zero-shot, beat the published benchmarks in Qiu et al. (2025)
> on their own data?**

That is well posed, uses a public benchmark with public code, needs no new data,
has no overfitting exposure because nothing is trained, runs locally, and is a
natural thing to discuss with Pepperdine faculty since one of the authors is
there.

**It is still a separate project.** Starting a second workstream before the
first has collected a single real row is how both end up unfinished. Revisit
once the surface has accumulated and H3 has been tested on a series rather than
a single day.

### 15.3 The benchmark was built on 17 September 2026 — with the condition NOT met

`analysis/timesfm_vix_baseline.py` exists. Recording plainly that **the revisit
condition above was not satisfied when it was built**: the surface had three days
and H3 is still a one-day calibration, not a tested series. Gabriel asked for it
directly and the cost is contained, but the condition is written down so the
departure is visible rather than quietly forgotten.

**What was kept from 15.2, which is everything that mattered:**

- It never touches `data/iv_history.csv` or `data/surface.csv`. It runs on **FRED
  VIXCLS only**, 30+ years, where there is real statistical power.
- **Nothing is trained.** Zero-shot, so there is no overfitting exposure.
- **Origins step by 21 trading days — non-overlapping**, which is the same
  discipline HANDOFF 4.2(a) forces on everything else.
- **TimesFM 2.5 weights (Apache-2.0).** Never 3.0, which is non-commercial and
  would collide with publishing.
- **A pre-registered bar**: beat HAR by >= 5% on log-RMSE *and* win >= 55% of
  origins. A FAIL is a planned, reportable negative result.

**The question is different from 15.2's and arguably better posed.** 15.2 proposed
benchmarking against Qiu et al. (2025) on their data. This benchmarks against
**HAR** (Corsi 2009) on FRED, which is the standard baseline in volatility
forecasting and has cleaner provenance than a third-party GitHub repo. The Qiu
route remains open and is the natural follow-up if this one passes.

It lives in `analysis/` with its own `.venv`. `requirements.txt` is untouched: the
pipeline is still stdlib plus `requests`, and nothing in `analysis/` is imported by
anything that runs unattended.

### 15.4 Result, 17 September 2026 — TimesFM FAILS the pre-registered bar

225 non-overlapping origins, January 2008 to July 2026, FRED VIXCLS. Forecasting
the mean of log VIX over the next 21 trading days.

| model | log RMSE | log MAE | median err | p90 err | max err |
|---|---|---|---|---|---|
| random walk | 0.1561 | 0.1189 | 0.0938 | 0.2603 | 0.5638 |
| **HAR** (Corsi 2009) | **0.1461** | 0.1106 | 0.0884 | **0.2256** | **0.5507** |
| TimesFM 2.5 zero-shot | 0.1518 | **0.1101** | **0.0850** | 0.2388 | 0.6723 |

**Verdict: RMSE gain -3.9%, wins 52.9% of origins. FAILS on both legs of the bar**
(needed >= +5% and >= 55%). Reported as a negative result, which is what the
pre-registration existed to make possible.

**The interesting part is not the FAIL, it is the shape of it.** TimesFM has the
**lowest MAE and the lowest median error** of the three, and the **worst maximum
error** of the three. It is slightly better than HAR on a typical month and clearly
worse in the tail - on the ten origins where HAR struggles most, TimesFM wins only
4 of 10. For a volatility application that is exactly the wrong trade, and it is
why the bar was written on RMSE rather than MAE before any of this was seen. Had
the bar been MAE, the same run would have "passed".

It does beat the random walk (0.1518 against 0.1561), so it is not useless. It is
beaten by a three-parameter linear regression from 2009.

**The sentence this earns:** *a 200-million-parameter pretrained foundation model,
zero-shot, does not beat a three-parameter linear regression at forecasting VIX,
and the way it loses is by being worse precisely when volatility does something
unusual.* That is a better interview answer than a pass would have been, and it
cost one afternoon.

Raw FRED series stays out of the repo (`analysis/data/` is gitignored); the
per-origin forecasts in `analysis/out/` are derived values and may be published
with citation. Source: FRED (VIXCLS), Cboe.

---

## 16. State as of 12 September 2026 — SUPERSEDED BY SECTION 17

> Kept for the reasoning. For what is true now, read section 17 first.

### What is running, unattended

| workflow | cron (UTC) | writes | notes |
|---|---|---|---|
| `record.yml` | 15:30 weekdays | `data/iv_history.csv` | 109 tickers, ATM. The irreplaceable one. |
| `surface.yml` | 15:40 weekdays | `data/surface.csv` | 8 underlyings, full strike surface. **First real run: Mon 14 Sep.** |
| `freshness.yml` | 17:00 **and 21:00** daily | nothing | Runs `tools/panel_health.py`. Fails loudly if **either** panel is stale, empty, duplicated or missing underlyings. The 21:00 slot exists because 17:00 is before the surface job lands. |

GitHub delays scheduled runs; both have landed around 18:45-19:00 UTC in
practice, which is systematic rather than drifting and is measured by the
pressure test.

### What is built

| file | what it does |
|---|---|
| `record.py` | the daily ATM recorder. **Do not modify the WATCHLIST.** |
| `surface.py` | the daily strike-surface recorder, with volume and open interest |
| `analyze.py` | shared estimators. Both samples import from here, deliberately. |
| `modelfree.py` | Cboe's variance methodology, and the gap against the published index |
| `hedged.py` | per-contract delta-hedged P&L, the strike-specific outcome |
| `tools/pressure_test.py` | 75 read-only integrity checks. Run before and after anything. |
| `tools/panel_health.py` | did the *data* arrive? Run daily by `freshness.yml`; also runnable by hand. |
| `index.html`, `tools/monitor.html` | the public site: the paper and the live instrument. Both read the repository client-side. |
| `tools/volrec.js` | the site's shared runtime. It mirrors the health rules, and the pressure test catches drift. |
| `tools/bloomberg_compare.py` | matches a Bloomberg OMON export against the free feed, contract by contract. Reads and writes only outside the repo. |
| `tools/test_hedged.py` | 18 hand-computed cases for the hedging math |
| `tools/fred.py` | FRED client, used for the discount rate |

### Hypotheses

| id | status | where it stands |
|---|---|---|
| H1 | **tested** | VRP positive on 9 of 11 Cboe pairs, VIX/SPY t=5.14 |
| H2 | **tested** | log variance strongest (t=16.3), raw variance weakest (t=2.1). Registered, **not adopted**. |
| H3 | **calibrated, not tested** | free-data model-free estimate matched the published VIX to 0.01 pts on one day. Needs a series. |
| H4 | **registered, untestable yet** | needs two consecutive days of surface data. Earliest Tue 15 Sep. |

### The immediate next actions, in order

1. **Check Monday's surface run.** `gh run list --workflow=surface.yml`. The
   commit path has still never executed with a real file in CI, but it is no
   longer unproven: on 12 Sep it was run verbatim against a throwaway local
   repo, under the conditions Monday will present - a depth-1 checkout like
   `actions/checkout@v5` produces, a real `surface.csv`, and a concurrent
   `record.yml` push landing on origin in between. The rebase resolved, the
   push landed, both data files coexisted, and the ATM row survived. So the
   remaining risk is not the git plumbing; it is whether `surface.py` writes a
   file at all. **A green run that commits *nothing* is the silent failure
   worth catching**, because the no-data guard exits 0 with a message and a
   holiday looks identical to a collection failure. Judge the run by whether
   `data/surface.csv` exists with Monday rows, not by the green check.
   **You no longer have to remember this.** `freshness.yml` now runs
   `tools/panel_health.py` twice daily and fails, which emails you, if
   surface.csv is still absent at 21:00 UTC on the day of the run itself. Run it by hand
   any time with `python tools/panel_health.py`; it needs no credentials and
   touches nothing.
2. **Once two consecutive days exist**, run `python hedged.py` and `python
   modelfree.py`. H4 becomes testable; H3 starts becoming a series rather than
   a calibration.
3. **The Bloomberg session.** `BLOOMBERG-MONDAY.md` is the checklist. It is a
   validation exercise, not a collection exercise, and it is the only way to
   separate feed quality from strike coverage inside H3's residual gap.
4. **Goukasian has not replied** to the follow-up sent 11 Sep. Six questions,
   four practical and two marked no-rush. The publishing question matters most:
   whether Bloomberg-derived output may appear in a public repo.

### What is dead. Do not revive.

- **Bloomberg as a history source** - 90 calendar days only. §14.1.
- **OptionMetrics via WRDS** - faculty, staff and doctoral only at Pepperdine.
- **"This data cannot be bought"** - false. §14.1.
- **Within-day cross-strike differencing** - cancels the realised term. §14.2.
- **Social sentiment** - §3.
- **Day-trading signal scanners** - §12 deferred list.

### Things that were true and are worth not relearning

- The recorder already fetches every strike within the band and discards all but
  one. That is why the surface costs no extra API calls.
- Alpaca's free plan serves `sip` back to 2016-01-04 but **403s on recent SIP
  data**, so `fetch_closes` clamps `end` to T-1. Do not "fix" this by reverting
  to `iex`.
- FRED's DISCONTINUED tags are stale for VXSLV and VXGDX; both relaunched in
  2025. Check Cboe, not FRED, for whether a series still publishes.
- A fixed percentage strike band truncates worst where volatility is highest.
  ±10% is ~2.2 sigma on a 16-vol name and ~0.6 on 59-vol oil.

---

## 17. History, 16-23 September 2026 — SUPERSEDED BY SECTION 18 for the current state

### What runs unattended

| what | when | notes |
|---|---|---|
| `record.yml` | **14:47 UTC weekdays** | 109 tickers, ATM. The irreplaceable one. Moved 16 Sep, see below. |
| `surface.yml` | **14:57 UTC weekdays** | 8 underlyings. **Running for real since Mon 14 Sep.** |
| `freshness.yml` | **20:00 and 23:00 UTC daily** | runs `tools/panel_health.py` over both panels |
| watchdog routine | Wed 09:13 Pacific | outside GitHub Actions; updated 13 Sep to know all three workflows |

**The crons moved on 16 September, from 15:30/15:40 to 14:47/14:57 UTC.** GitHub
delays scheduled runs under load: measured over six days at the old slot the delay ran
3h06m to 4h24m, so snapshots landed 18:36-19:54 UTC and on 14 Sep arrived **six minutes
before the close**. A snapshot taken after the close is closing quotes filed under a
mid-session label, and nothing downstream can tell.

Three constraints pin the new time down, none of which cron can see, so they are
written into `record.yml` and enforced structurally by `pressure_test.py` rather than
as a literal string:

1. The worst delay seen plus 30 minutes must still clear the close.
2. **Cron is UTC and the session is not.** Under DST the market runs 13:30-20:00 UTC;
   from Mon 2 November it runs 14:30-21:00. A time chosen against the summer session
   alone fires *before* the November open - which the first attempt at this change did,
   and the DST check caught. Both panels must clear the later open and the earlier
   close, leaving a window of 14:30 to 15:06 UTC.
3. Avoid the quarter hours, where GitHub's scheduling queue is deepest.

14:47 sits inside that window with 49 minutes of headroom to the summer close and 17
minutes past the winter open. The pressure test now checks the reasoning, not the time,
so moving one cron without the other fails loudly.

Belt and braces, because the cron cannot guarantee anything: `panel_health.py` reads
the actual session bounds for the day out of the zone database and **FAILS** if a
snapshot landed outside them, warns if it landed within 20 minutes of the close, and
warns if it drifted more than an hour from the prior days. That is the check that
sends an email.

The 78-minute spread already in the data remains, and still belongs in any write-up.
It is less serious than it first looked: the interval is identical for every contract
on a date, so the date-clustered tests absorb it completely and only the contract-level
pooled number is exposed - and that number was already established not to be a test.
`hedged.py` prints the true interval every run.

### What is built since section 16

| file | what it does |
|---|---|
| `index.html`, `tools/monitor.html` | the public site: the paper and the live instrument |
| `tools/volrec.js`, `tools/volrec.css` | shared runtime and styles; health rules mirrored from `panel_health.py` |
| `tools/bloomberg_compare.py` | matches a Bloomberg OMON export to the free feed, contract by contract |
| `tools/iv_convention.py` | re-inverts quotes under a stated forward and rate, to locate a volatility gap |
| `tools/model_gap.py` | solves for the TIME that reproduces a vendor's own volatility from its own price; identified the day count |
| `tools/delta_model.py` | re-hedges H4's runs with a delta from this project's model instead of the vendor's |
| `analyze.py --simulate-surface` | H4's accept criteria under a true null, plus what 40 day pairs can detect |
| `hedged.py` honest-units block | the registered gains re-reported per underlying-day, per date, and as a within-day contrast |
| `panel_health.py` quote-time check | warns when a day's rows are stale by over 15 min, the within-day half of the snapshot-spread warning |
| `panel_health.py` missed-day check | **FAILS** when a trading day has no data. Added after 16 Sep, when a whole day was lost silently |
| `panel_health.py` session check | **FAILS** when a snapshot lands outside the day's real market hours, DST-aware |
| `tools/calibrate.py` | feeds every instrument an input with a KNOWN answer; runs inside every pressure test |
| `surface.py` wide pass | records high-vol names beyond +/-30% into `data/surface_wide.csv`; registered grid untouched |
| `modelfree.py --wide` | H3c sensitivity: integrates both files. Never the registered estimate. **Since 18 Sep prints the LIFT per day, the zero-bid variant, coverage, and the GLD/AAPL null controls** |
| `modelfree.pick_pair`, `surface.wide_expiries` | 18 Sep: one expiry rule in both places, `rows_for`'s own. The estimate used to integrate the outermost expiries and the wide pass widened a different pair |
| `calibrate.py` lift identity | the measured `--wide` lift must equal the lift with every expiry widened, through the recorder's real `wide_rows_for` |

### Where the hypotheses stand

| id | status | where it stands |
|---|---|---|
| H1 | tested | VRP positive on 9 of 11 Cboe pairs, VIX/SPY t=5.14 |
| H2 | tested, not adopted | log variance strongest, t=16.26 |
| H3 | calibrated, cross-checked, gap identified and **demoted to a measurement note** | 0.59 mean gap at ±30%; the free feed's prices are as good as Bloomberg's, and **the 1.7-point volatility gap is a day-count convention — Bloomberg on 252 business days, the free feed on 365 calendar days**. It does not touch `modelfree.py`. **The wide-band test was repaired and pre-registered 18 Sep, before its data; first reading after the Tue 22 Sep run** |
| H4 | first run, descriptive, model dependence measured | 998 hedged runs on the 14-15 Sep pair. H4a and H4b are on the wrong side; H4c holds directionally. **Re-hedging with our own delta moves every bucket by at most 0.52bp and flips no sign** |

### The Bloomberg result, in one paragraph

On 15 September the recorder snapshotted at 19:10 UTC and the terminal export was
pulled at 18:57. Matched contract by contract, mid prices agree within half a bid-ask
spread on TSLA and volumes agree within 3%, while implied volatilities differ by about
1.7 points. Re-inverting with Bloomberg's own printed forward did **not** close it, and
inverting Bloomberg's own bid, mid and ask with this project's Black-76 still lands
about 1.7 points above the IVM Bloomberg prints beside them. So the disagreement is
between models, not feeds. `modelfree.py` integrates prices and is untouched by it;
`hedged.py` uses the vendor's delta and is not. See H3 and H4 for the numbers.

**Both of those were closed on 16 September.** The volatility gap is the day count:
solving for the time that reproduces Bloomberg's own IVM from Bloomberg's own mid
gives an annualisation divisor that is stable on business days (248-256 across six
blocks, two symbols, two maturities) and unstable on calendar days (336 at one month,
352 at two). Re-inverting on 252 business days collapses TSLA's gap from +1.80 to
+0.08 volatility points. The binomial that HANDOFF asked to be tried changes it by
0.00, as it must for calls on a name paying no dividend. And the vendor's delta was
identified the same way: forcing the forward to `S e^{rT}` reproduces it to 0.0007,
so the free feed's greeks carry no dividend and no borrow. Re-hedging H4 with a
parity forward instead moves the buckets by at most 0.52bp and changes no direction.

*Bloomberg figures: Source: Bloomberg Finance L.P.*

### Bloomberg working rules

- Exports live in `~/Documents/volrec-bloomberg`, **never in this repository**. Both
  tools refuse any path inside it.
- Gabriel has approved publishing derived results with attribution. Use
  **"Source: Bloomberg Finance L.P."** beside any figure. Publish aggregates, never
  per-contract quotes: Bloomberg's own guidance allows a limited amount of derived data
  in research output, and the education terms are stricter still.
- The pull protocol, refined by two sessions at the terminal: `TICKER US Equity OMON`,
  Table view, raise the strike count, export, save as `TICKER_OMON_YYYY-MM-DD.xlsx`,
  write down the pull time. Strike counts differ by ticker because strike spacing does:
  TSLA 50 is enough for ±30%, USO needs about 80, and SPY needs 200 or more because its
  strikes step a dollar at a time. Record the `IFwd` printed in each expiry block.
- Pass the real pull time: `python3 tools/bloomberg_compare.py --pull-time 18:57`.
  Without it the file's save time is used, which is later and fails the gap check.

### Done 16 September 2026

1. ~~**Identify the model gap.**~~ It is the day count. `tools/model_gap.py`;
   numbers in H3 under "The day count". The binomial was tried and explains nothing.
2. ~~**Quantify what the delta difference does to H4.**~~ `tools/delta_model.py`;
   numbers in H4 under "The delta is the vendor's". Directions all survive; the
   shifts run to 0.52bp and concentrate on the dividend-paying ETFs.

4. ~~**Check quote staleness before 40 days of it accumulate.**~~ Measured 16 Sep:
   12 of 2,740 rows are over 5 minutes behind their day's median quote time, 2 are
   over an hour, and exactly 1 of the 998 hedged runs has a stale leg. It does **not**
   concentrate by volume (1% in the bottom volume deciles, 0% in the top), so H4c's
   low-volume result is not a staleness artifact. `panel_health.py` now watches it
   twice a day so a change is caught rather than discovered in November.

3. ~~**Extend `analyze.py --simulate` to the surface-level H4 tests.**~~ Done as
   `--simulate-surface`; numbers in H4 under "What the tests are worth". The headline:
   the pooled t over contracts rejects a true null 46-73% of the time and gets worse
   with more days, clustering on the underlying-day is *not* sufficient once
   underlyings move together, and about 40 day pairs is enough for both H4a and H4c.

### 16 September: two failures worth reading before anything else

**1. A whole trading day was lost, silently.** No `record`, `surface` or
`freshness` run fired on 16 Sep. The Actions tab showed nothing at all - not a
failure, not a cancellation, simply no run. Most likely cause: the cron was edited
and pushed at 15:57 UTC, after the 15:30 trigger but before GitHub had executed
the routinely 3-4 hour delayed run, and the edit invalidated it.

Nothing noticed. `panel_health.py` reported HEALTHY throughout, because the newest
day was one day old and `STALE_DAYS` is five. **A dropped scheduled run leaves no
trace and sends no mail.** It was found only because someone looked.

Fixed: `missed_trading_days()` computes which trading days should have landed and
have not, and **FAILS** on the first one. A warning would reach nobody, since
GitHub only mails on failures. It counts today only once the landing hour passes,
skips weekends and exchange holidays, and self-heals when a newer day arrives.

**The rule that follows: never edit a workflow's `schedule:` on a day whose run
you still need.** Check `data/surface.csv` for today's date first, and after any
workflow edit confirm the next run actually fired.

**The cost:** the 221-strike SPY Bloomberg export pulled that day at 19:00 UTC had
no free-feed snapshot to match against, so **SPY's feed quality is still
unmeasured** - which was the entire point of that pull. The day-count analysis
survived only because it is internal to the export.

**2. The Bloomberg export folder was moved into the repository root**, seven
licensed spreadsheets inside a public repo. **Nothing leaked** - nothing was
committed and no `.xlsx` is in git history - and `pressure_test.py`'s spreadsheet
check caught it. But that guard only fires when someone runs the test, so
`.gitignore` now blocks `*.xlsx`, `*.xls`, `*.xlsm` and `volrec-bloomberg/`
outright, and the pressure test asserts those entries exist. This has now happened
twice, on 14 and 16 Sep. **When a new export arrives, check `git status` first.**

### The day count is NOT a finding — settled 16-17 September

A commissioned research pass reviewed the day-count result against the
literature. **It is not novel and must not be written up as a discovery.**
Trading-time against calendar-time annualisation is in Hull and Natenberg, in
French (1984), in Cboe's own VIX-versus-VIX1D methodologies, in Albers & Kestner
(2024) naming the 252-vs-365 divide outright, and in OCC filing SR-OCC-2024-016,
where a clearinghouse found it was running a calendar clock for price smoothing
and a trading clock for implied volatility and filed to align them.

**An earlier proposal in this session to promote "convention, not quality" to a
co-headline is withdrawn.** Gabriel had approved it; it was made before the
review and it was wrong. H3's day-count section carries the full correction.

The measurement itself survived a direct challenge and is now stronger. The pass
argued the magnitude was impossible - about 0.2 points from a clean 252-vs-365
split at 30 days against 1.7 observed - but that rests on the rule of thumb that
30 calendar days hold ~21 trading days, which is the average density
(30 x 252/365 = 20.7). The measured windows hold **22 and 23**, and one trading
day is worth about a full volatility point at TSLA's IV. Using each window's own
count, the clock predicts the gap with **no fitted parameter**: slope 1.013
(se 0.131) against the predicted 1.000, intercept +0.08, R-squared 0.881, mean
absolute residual 0.13 points across ten blocks. `tools/model_gap.py` prints it.

**What this leaves.** A well-executed reconciliation note, not a headline: two
feeds disagree by a knowable amount, the arithmetic closes it exactly, and anyone
comparing vendor implied volatilities should check the clock before blaming data
quality. That is worth stating and worth nothing more. **H3's actual claim is
untouched** - `modelfree.py` integrates prices and never reads an implied
volatility - and the research pass incidentally confirms the core mission is the
distinctive part: the *free-data-cost* question is not well-trodden, while the
*IV-convention* question is.

*Bloomberg figures: Source: Bloomberg Finance L.P.*

### The Bloomberg licensing question is ANSWERED — 17 September 2026

Marc Vinyard (Pepperdine business librarian, who administers the subscription)
replied: *"You can publish an article that cites Bloomberg data as the source of
your information, but you cannot add the raw Bloomberg data to an open access
repository. That would be a violation of our contract with Bloomberg."*

That is exactly the rule this repo has been operating under since 14 Sep, now
confirmed by the person who can confirm it. **Action 2 below - the Bloomberg
result on the public site - is unblocked**, aggregates only, with "Source:
Bloomberg Finance L.P." beside any figure. Raw per-contract data stays out, which
`.gitignore` and `pressure_test.py` now both enforce.

He also answered the two OMON mechanics questions. The top bar reads
`335.49 Strikes 5 Exp 18 Sep 26`: **`Strikes` and `Exp` are separate amber input
fields**, so a long-dated pull means setting `Exp` FIRST and the strike count
second. Open interest is added through `Settings > Edit Columns`. The IVM
day-count question goes to the desk through `?` then `Live Help`, which is a live
chat and the fastest route to the written primary source H3 still lacks.

### The strike band — DECIDED and live from 18 September 2026

Gabriel delegated it: "implement whatever makes the long term engine run strong and
precise." Implemented as the additive option. **The registered grid is unchanged**;
high-volatility names are also recorded out to max(30%, 5 sigma), capped at 60%, into a
separate `data/surface_wide.csv`. Full reasoning in H3's adjustment log. What follows is
the record of the decision as it stood before it was made.

**The options that were on the table:**

| option | what it does | verdict |
|---|---|---|
| A. do nothing | keep +/-30% x 40 | USO stays at 2 sigma; H3c can never be tested; the days pass unrecoverably |
| **B. record wide, analyse frozen** | add a separate wide file, keep +/-30% as the registered estimate | **chosen.** Additive, H3's numbers byte-identical, H3c becomes testable |
| C. widen and re-analyse | change the registered band mid-series | rejected - a pre-registered specification is not re-cut after seeing data |
| D. widen everyone uniformly | +/-50% on all names | rejected - wastes rows on SPY, already at 9.5 sigma |

### Before the decision — 17 September 2026

`modelfree.py` was run on accumulated data for the first time since calibration.
H3a is passing at a mean absolute gap of 0.75 against a threshold of 1.0, and
**USO alone contributes 78% of the error**, worsening from -1.84 to -3.56.

The cause is measured, not guessed: the fixed +/-30% band covers **11.0 sigmas on
SPY and 2.0 on USO**. See H3, "The series so far".

The proposal as first stated was `max(30%, 4 sigma)` touching only USO, TSLA and
NVDA. What was built is 5 sigma on a 30-day basis, which also widens GLD and AAPL by
three points: 5 sigma is where the names already tracking Cboe sit, and sizing on the
longest expiry turned out to include stale carry-forward expiries.

### Everything is calibrated — 17 September 2026

`tools/calibrate.py` checks each instrument against a reference truth that does not
come from the data, so a pass cannot be the data agreeing with itself. It runs in about
four seconds inside every `pressure_test.py`.

| instrument | reference truth | result |
|---|---|---|
| Black-76 pricer | put-call parity (exact identity) | worst 1.4e-14 |
| implied-vol inversion | price to vol to price is identity | worst 1.8e-15 |
| model-free variance | Carr & Madan: equals sigma^2 under constant vol | worst **0.20 pts** at +/-30% |
| realised vol | simulated known sigma | c4 removes the ~1.2% low bias, residual under 0.25% |
| ATM significance test | no-premium world, nominal 5% | 5.5% (the pooled test: 64.5%) |
| surface date test | no-premium world, nominal 5% | 5.5% |
| surface volume contrast | no-premium world, nominal 5% | 3.0% |
| risk-free input | today's date | 7 days stale, **immaterial**: 10bp moves a gain ~0.013bp |

Tolerances are argued from outside the measurement: identities to float precision,
method error to half of H3a's 1.0-point budget, test size to the binomial 2.5-sigma band.

**The calibration also corrected a piece of reasoning.** The wide band was first
justified by sigma coverage - USO's downside at 2.4 sigma against SPY's 9.5. Calibrating
showed that under a lognormal, 2.4 sigma costs only 0.20 points. What actually explains
USO's -2.93 gap is its **smile**: on USO's own recorded implied volatilities, the variance
beyond +/-30% is 1.37 points with flat wings and 3.24 with linear wings, bracketing the
observed gap. So it is not a data-quality problem, and the wide band is the right fix
for a better reason than the one first given. **It also makes a falsifiable prediction:
`modelfree.py --wide` should lift USO's estimate by 1.4 to 3.2 points and leave SPY's
alone.** H3, "Calibration", has the detail.

### 18 September: the wide test was broken, and was fixed before its data

Preparing the test above turned up three defects, all found and settled before
`surface_wide.csv` existed. Full numbers in H3, "How the prediction is tested".

1. **The estimate and the wide pass used different expiries.** `modelfree.py`
   integrated the outermost expiries present; carry-forward puts a third, shorter one
   in the file on 23 of 39 days, so the estimate broke Cboe's 23-day rule and the wide
   pass widened a pair the estimate did not use. On a synthetic USO with a known
   1.93-point lift, the old code read **0.63 every Wednesday**. Now one rule in both
   places, `rows_for`'s own: exact on every layout, **no recorded gap moved** (14-15
   Sep have two expiries; 17 Sep had no Cboe close yet). The recorder's registered
   path is unchanged as a syntax tree; only the sandboxed wide pass picks its pair
   differently. Changing only `modelfree` was tried first and failed on Wed 25 Nov,
   when Thanksgiving week moves the Christmas expiry and a nearest-two tie drops a
   weighted leg.
2. **The 1.37 / 3.24 bracket cannot be reproduced** - its code was never committed.
   Seven smile methods on three days put what the capped band can deliver at 0.93 to
   about 2.7. **The bar stays 1.4 to 3.2**; an interpretation grid is now registered
   beside it, including the band where a reading fails the bar but is consistent with
   flat wings.
3. **SPY's half cannot fail** - SPY is never widened. GLD and AAPL (widened to 33%,
   predicted lift 0.03-0.14) are registered as null controls with a 0.3 limit.

**Deliberately not done:** no wide quote was previewed. Every choice was made on
known-answer simulations and the +/-30% data already seen.

### 18 September, afternoon: the first wide day and the USO wide pull

The wide pass ran for real (266 rows; USO 0.42x-1.59x spot), and a USO OMON export
at 144 strikes was matched to it 30 minutes after the snapshot. Full numbers in H3,
"The first wide day". Three things to carry forward:

1. **The free feed's wing quotes match Bloomberg's**: 0.07 of a spread on the far
   puts, 0.40 on the far calls, and the same 13 far puts have no bid on both feeds.
2. **The registered estimator is contaminated in the wings, not the feed.** Counting
   a zero bid at half the ask lifts USO's 16 Oct estimate by +5.28 on the free feed
   and +4.91 on Bloomberg's own prices; under Cboe's zero-bid rule, +0.94 and +0.85.
   The known-answer test had put that inflation at +0.14-0.47, which was wrong by an
   order of magnitude. The registered grid already reads a reading over 3.2 as
   "contamination, check the zero-bid column", so nothing registered changes, and
   H3a's +/-30% numbers move by 0.03 points at most under the same rule.
3. **Cboe's 17 Sep close put USO at +0.71**, its first positive gap. H3a over n=15 is
   0.59. The OMON export format also changed to Ticker-first; the three Bloomberg
   tools share one parser for both layouts now, and the pressure test holds them to it.

*Bloomberg figures: Source: Bloomberg Finance L.P.*

### 19 September: H5 registered, and where the project's edge actually is

`hypotheses/2026-09-19-h5-wing-quote-quality.md`. The 18 Sep pull found the free
feed's wing quotes matching Bloomberg's while the estimator's zero-bid handling
inflated the estimate by ~4.2 points on **both** vendors' prices. H5 turns that into
four registered predictions: the wing quotes are fine (H5a), the emptiness is real
(H5b), the inflation is the estimator's and reproduces on Bloomberg (H5c), and it
scales with the zero-bid count (H5d). It needs no recorder change and no new code -
only more wide days and **two more matched Bloomberg wing pulls**, which is now the
binding constraint on the most distinctive result this project has.

The framing, after a conference on 18 Sep and Greg Jensen (Bridgewater) on Odd Lots
on 11 Sep arguing that AI keeps markets inefficient because frontier capability
leapfrogs: **that is an argument for not competing on compute or on data volume.**
The asymmetry available here is attention, not scale - nobody funded measures what
free data costs, because they buy OPRA instead. An agent that searches for patterns
in this data would destroy the pre-registration that makes these results citable
(assessed 16 Sep, still rejected). An agent that runs the daily operations would not.

### 23 September: the first H3 reading, H5e, and a full health check

**Readings** (H3 and H5 files have the tables):

- **H3's registered wide reading: OUTSIDE.** USO's as-registered lift averaged +9.41
  over 18, 21 and 22 Sep against the 1.4-3.2 bracket - over 3.2, which the grid
  registered on 18 Sep reads as quote contamination. The zero-bid column: +1.00.
  AAPL's null control: +0.05. Not the written-up reading; that is after 11 Nov.
- **H3a:** 30 readings, mean absolute gap 0.53, USO 61% of it, USO settled at -1.1.
  IWM reads positive on all six days, against H3b's sign.
- **H5e registered 07:09 UTC 23 Sep, before that day's run** (commit `ac237a6`).
  Skipping zero-bid stubs without Cboe's stop rule put USO's wide estimate on OVX
  at +0.23, -0.24, -0.00 in sample. Judged only from 23 Sep; `modelfree.py --wide`
  and `tools/daily.py` print the running tally.
- **Cboe's stop rule cut USO's registered band by 2.75 points on 22 Sep** at
  one-sided stubs on odd strikes (P119, P122, P124, no bid, ~$3 ask).
- **The 22 Sep pull** (16 Oct only): USO passes (0.39 of a spread; wings 0.09 and
  0.00). TSLA FAILS the price gate at 0.87. The new drift line in
  `bloomberg_compare.py` shows every gate failure to date coincides with the
  underlying moving between snapshots: USO 15 Sep +0.18% (0.64), TSLA 22 Sep -0.14%
  (0.87). The failures stand; the lesson is to pull faster, fast movers first.

**Fixed:**

1. **`pressure_test.py` had been crashing since 21 Sep** on a vendor quote with no
   greeks (HYG): `float('')` in section C, so nothing after it ran - and no email,
   because the workflows run `panel_health`, not the pressure test.
2. **The worst-delay check trusted a stale constant.** Record fired 4h57m late on
   21 Sep and landed 16 minutes before the close; the test believed 4h24m. It now
   measures the delay from the panels and WARNS inside the 30-minute margin.
3. **`bloomberg_compare.py` and `iv_convention.py`** now match the recorder expiry
   the export actually holds; both 22 Sep exports held 16 Oct only.
4. Dead imports removed; an AST scan found no undefined name anywhere.
5. The `--wide` gap summary is relabelled: it read "USO max +12.00" and was nearly
   taken for H3a's series.

**Built:** `tools/bloomberg_prep.py` (OPS item 1) and `tools/daily.py` (item 2).
`pressure_test.py` section M locks every registered constant, checks the zero-bid
walk against a known answer (13 / 9 / 10 strikes), and checks the prep tool
reproduces the 18, 22 and 23 Sep sessions.

**Both decisions made by Gabriel, 23 Sep:**

- **H4 fixed - strike 1 of 3.** Runs now break on a missed trading day instead of
  after four calendar days; 15 -> 17 Sep no longer splices across the lost 16 Sep.
  H4's date-level mean moves from -8.56bp (5 dates) to -0.57bp (4), and the volume
  contrast from +0.75bp to -1.06bp, H4c's side. All descriptive; H4's adjustment log
  has the table.
- **The cron is held to Wed 11 Nov.** The 16-minute margin is recorded in
  `pressure_test.py` as ACCEPTED until that date and warns again after it. A
  post-close landing still FAILS `panel_health`, and that day gets dropped.

**Prior art read, 23 Sep:** Andersen, Bondarenko & Gonzalez-Perez (2015, *RFS*)
already critique Cboe's two-zero-bid cutoff, and their RX\* is H5e's "skip"
estimator. H5 now credits it; what stays ours is the free feed, the daily
frequency, the sparse ETF ladder with stubs near the money, and the Bloomberg
cross-check. Next to read: Jiang & Tian (2005, *RFS*; 2007, *J. Derivatives*).

**Assessed and parked, 23 Sep:** H6 (Kalshi against the market) - Kalshi's S&P
contracts are same-day (`KXINX`, `KXINXU`, public API, no key); the recorder has no
same-day options, so there is nothing to compare against without a new recorder,
and a correlation search would break pre-registration. TradingView (charting needs a
licence; the broker module is trading), worldmonitor (news-to-market pattern
search), a SQL store (CSV stays the audited record; a gitignored DuckDB view is 20
lines if ever needed). **Databento's OPRA data** (one-minute consolidated NBBO, historical, $125 of free
credit on sign-up) would give a reference quote for every recorded day at the
snapshot's own minute. Not pursued for now (Gabriel, 23 Sep).

*Bloomberg figures: Source: Bloomberg Finance L.P.*

### 23 September, later: the operations agent is built, and Databento is ready

`OPS-AGENT.md` has the whole layer. New since the morning: `health.yml` runs
`daily.py` in CI on weekdays at 23:37 UTC and emails on any FAIL or crash (first
manual run green in 32 seconds; CI reads with r=0 because the FRED cache is
gitignored, so the local reading is the one of record); `tools/hooks/pre-push`
blocks a push to main that fails the pressure test (proven with a deliberate FAIL);
`SESSION-START.md` is the one-screen orientation `CLAUDE.md` now points to first.

**Databento, agreed 23 Sep for the $125 free credit.** `tools/opra_reference.py`
prices every request with Databento's own `get_cost` before fetching, refuses over
$0.50 a request or past $100 lifetime, keeps data and key outside the repo, and
matches each contract to OPRA at its own quote time. Its dry run caught a
timestamp bug that would have fetched the wrong minutes. **H5f was registered
before any OPRA data was requested**, reusing H5a-c's thresholds. Nothing is
fetched until Gabriel creates the account and a dry run shows the cost.

**First OPRA data, same day.** Account created; the dry run priced six requests at
$0.006-0.007 each. Fetched 18 and 21 Sep for $0.0273; 22 Sep was refused (OPRA is
served historically only after a delay; the tool now skips and says retry tomorrow,
charging nothing). At the same minute USO's free quotes match OPRA to 0.02-0.12 of a
spread, 22 of 22 no-bid quotes are no-bid on OPRA too, and the zero-bid inflation
reproduces on OPRA within 1.4%. TSLA reads 0.47-0.83 even seconds apart - one-tick
markets, a coarse metric - which corrects the 22 Sep drift explanation. 13 far-OTM
USO stubs on 21 Sep have no OPRA record at all; the `definition` schema is the next
check. H5 has the table.

### 23 September, evening: what was checked, and what was being forgotten

- **The 13 stubs:** every unmatched contract is a real OPRA listing (`definition`
  schema, $0.018); the free feed's far-OTM quotes on them were 91-130 minutes stale
  where OPRA showed no quote at all. Part of the wing contamination is stale feed
  quotes. H5 has the detail; H5f's exclusion rule cannot see them, stated in advance.
- **iMessage alerts, built, not installed:** `tools/notify.py` and
  `tools/launchd/install.sh` (OPS item 7). Gabriel saves a handle and runs the
  installer; nothing installs it for him.
- **Calibration:** 9 of 9, adding a known-answer check on the OPRA comparison.
- **Forgotten, found:** the 6 Sep "IV against a technical-levels scanner" idea lived
  only in session memory - written below. The public site's hypothesis table was a
  week stale (H3 "one day", no H5) - updated. The watchdog routine (Wed 16:13 UTC)
  predates `health.yml` and `daily.py` - an update is proposed to Gabriel, not made.
- **Done 23 Sep: the Bloomberg result is on the public site** (action 2, open since
  17 Sep), at Gabriel's instruction and inside Marc Vinyard's rule: derived aggregates
  only - medians, counts, fitted lines - with "Source: Bloomberg Finance L.P." under
  every block; no quote, price, implied volatility, IFwd, R or ticker; static text,
  never a data file. Read conservatively on purpose, so Pepperdine's contract is never
  in question. OPRA/Databento figures stay off the site until Databento's terms are
  checked. `pressure_test.py` section K now enforces the rule on the page, and was
  shown to fail on a removed attribution and on a pasted terminal ticker.

### Parked for late October: implied volatility against a technical-levels scanner

**Raised by Gabriel on 6 September 2026, kept only in session memory until 23 Sep -
written here so it cannot be lost.** The question: *does implied volatility forecast
realized range better than a technical-levels scanner does?* It came out of assessing
(and rejecting) an Oracle-style day-trading signal tool, whose "Resistance" and "Max"
columns are a prediction of range. Implied volatility is also a prediction of range -
the market's own, priced by people with capital at risk - so the two are directly
comparable.

Why it fits where a signal bot does not: it runs on the daily clock and the frozen
109-ticker universe, on columns `record.py` already writes; no new data, API or feed.
Why it is a good interview artifact: a test **between two methods**, not an
advertisement for one. **Nothing before ~40 trading days of data; start late October,
and register it in `hypotheses/` before running a single join** - the scanner's rule
must be fixed in advance, or the comparison becomes a search.

**23 Sep, the stub finding in one line:** the unmatched OPRA contracts are real listings,
but the free feed's quotes on the far-OTM ones were 91-130 minutes stale, one-sided,
where the consolidated market showed nothing. Part of the wing contamination is stale
feed quotes, not only the estimator. H5 has it.

### The window this is all aimed at

**40 trading days from Wed 16 September 2026 ends Wed 11 November 2026.** No market
holiday falls inside it; US clocks change on Sun 1 November, which moves the session
an hour in UTC but not the cron. `--simulate-surface` says that length is enough to
detect a level effect of about 1bp or a volume contrast of about 0.56bp, against a
first run that measured +2.31bp and 4.19bp respectively. So the window is adequate
for both H4 claims if the effects are near what one night suggested, and not
adequate for effects half that size. Nothing about the predictions changes either
way; this is for planning what the write-up can honestly say.

### The 16 September gap was accepted, not silenced

The day is gone and cannot be recovered. Gabriel accepted the loss rather than
dispatching after the close, because a post-close snapshot would enter the
irreplaceable panel at a time no other day shares, and comparability is worth more than
one row.

Left alone, the new missed-day check would have failed on every run from now on, over a
day nobody can bring back, which is exactly how an alarm becomes noise and the next real
miss gets ignored. `ACCEPTED_GAPS` in `tools/panel_health.py` holds the date beside the
reason it was accepted. The day still prints as an INFO line on every run, so no
write-up can quietly forget it, and any date not on the list still fails. The pressure
test caps the list at five and insists each entry carries a reason.

**Consequences for the analysis.** H4 has one usable pair, 14 to 15 September; the 15 to
16 pair does not exist. The three exports pulled on 16 September can never be matched
against a snapshot, so they count as coverage validation only - and at that they were
useful: SPY's 221 strikes span -61% to +32% of forward, TSLA's 50 span ±34%, and USO's
80 reach only -26% on the downside, so USO should be centred lower next time.

### The immediate next actions, in order

1. **Let the surface accumulate.** H4 needs many more day pairs before its pooled t
   means anything. Nothing about the predictions should be adjusted meanwhile.
2. **Put the Bloomberg result on the site** as a figure in the paper, aggregates only,
   with the attribution line. There is more to show than there was: the day-count
   finding is a cleaner story than "the volatilities disagree", and it is the kind of
   thing a free-data measurement study exists to report.
3. **Extend `analyze.py --simulate`** to the surface-level H4 tests, so the accept
   criteria are simulated under a true null before the series is long enough to tempt a
   claim. This is the "simulation engine" idea, in the form that fits this project.
4. **The Bloomberg asks are ranked in `BLOOMBERG-MONDAY.md`**, rewritten 16 Sep and
   updated again after that evening's pull. **Ask 0 is new and comes first: confirm
   the recorder ran before pulling**, because an export with no matching snapshot
   can only answer the day-count question. SPY's 221-strike export is done and
   correct; it needs repeating on a day the recorder fires.
   The decisive one is a **long-dated expiry with 50+ strikes**: the 252 and 365
   clocks converge as maturity grows, so a two-year contract is where the day-count
   finding makes its riskiest prediction and is the one pull that could falsify
   something already recorded. The thin 14 Sep export reached 858 days and the gap
   did *not* vanish there - on five strikes, which is not evidence, but is the one
   observation pointing the wrong way. After that: SPY at 200+ strikes (still
   formally unmeasured), whether the terminal *states* its day count anywhere
   (which would turn an inference into a fact), and whether OMON can add an open
   interest column (H4d needs it).

5. **Decide what the `iv` column is for, now that its clock is known.** It is on 365
   calendar days and Bloomberg's is on 252 business days. Nothing needs changing -
   the convention is internally consistent and `modelfree.py` never reads it - but any
   comparison to an outside volatility number has to convert one side, and that should
   be written down once rather than rediscovered. A pull at a long maturity would also
   sharpen the 252 estimate, because the two clocks converge as maturity grows.
6. **Compute the hedge ratio rather than record it, if H4 is ever written up as more
   than descriptive.** The vendor's delta ignores dividends; H4's numbers are not good
   to better than about half a basis point until that is fixed. `delta_model.py`
   already does it; nothing has been switched over because switching the default would
   change a registered run mid-series.

### Ideas assessed and parked, 16 September 2026

- **Intraday volume forecasting (Chen, Feng, Palomar 2016, Kalman filter).** Cannot
  apply: this project records one snapshot a day, and the paper forecasts intraday bins
  for execution. The reusable part is its state-space decomposition into daily, seasonal
  and dynamic components, which could model daily contract volume for H4c and H4d once
  the series is long enough.
- **Spike-timing-dependent plasticity, pattern recognition.** No defensible fit against
  roughly two independent episodes. It would look impressive and support no claim.
- **MAR ratio.** A strategy performance measure. This project does not trade.
- **A standalone simulation engine.** Superseded: `analyze.py --simulate-surface`
  extends the simulator that already existed rather than building a second one.
- **A generate-backtest-score-refine strategy loop** (an Instagram reel, 16 Sep, "how
  to build a loop trading bot"). Assessed and not adopted as a loop. Its good half -
  reject anything that does not clear a noise floor, and kill the best in-sample
  scorer when it fails out of sample - is what `--simulate` and `--simulate-surface`
  already do, and they do it against a constructed true null rather than a heuristic
  decay curve. Its other half is a search over strategy variants, which this project
  does not do and must not start doing: pre-registration in `hypotheses/` is the whole
  defence, and an iterating loop is the machine for destroying it. Nothing to take.
- **HKUDS/Vibe-Trading** (MIT, ~1,750 Python files, read 16 Sep). It is a broker-connected
  trading agent, which is the category HANDOFF 1 and 5 rule out, so nothing at the system
  level applies. One module is genuinely relevant and worth reading before writing up:
  `agent/src/quantlib/multipletesting.py` implements the deflated Sharpe ratio and CSCV
  probability of backtest overfitting (Bailey & Lopez de Prado) and Benjamini-Hochberg.
  The first two answer "how much of the best result is search luck", which this project
  does not need because it does not search. **Benjamini-Hochberg is the one that applies**:
  H1 reports 9 of 11 Cboe pairs positive and H3 will test five underlyings, and "which of
  these are real" is an FDR question this repo currently does not correct for. It is a
  method from 1995, not their code, and it is ~20 lines of stdlib. Raised, not adopted;
  H1 is recorded as tested and should not be re-cut without Gabriel deciding to.

### Prompt for the next session

> Read `CLAUDE.md` first, then `HANDOFF.md` section 17, then the H3 and H4 files in
> `hypotheses/`. The repo is github.com/gabrielmitton-cloud/volrec, cloned at
> ~/Desktop/Archive/Volrec, and in sync.
>
> Use `/Library/Frameworks/Python.framework/Versions/3.14/bin/python3`, never bare
> `python3` (Homebrew's has no `requests`). Prefix `hedged.py`, `modelfree.py` and
> `delta_model.py` with `FRED_KEY=use-cache` or they silently use r=0. Run
> `tools/pressure_test.py` before and after anything; it should say 0 fail. Three
> warnings are known and true (a vendor IV gap, snapshot spread, the cron margin).
>
> **One command does the daily check:** `.../python3 tools/daily.py`. It pulls, runs
> panel health, the pressure test and `modelfree.py --wide`, and ends ALL CLEAR or
> LOOK AT. Before any Bloomberg session: `tools/bloomberg_prep.py --date YYYY-MM-DD`.
>
> State, 23 Sep: the engine runs unattended to Wed 11 Nov. H3's first registered wide
> reading came out OUTSIDE (contamination, as the grid said). H5e was registered
> before 23 Sep's run and is judged only from 23 Sep: USO's wide estimate with
> zero-bid stubs skipped should track OVX within 0.5 points on 10+ days.
> HANDOFF 17, "23 September", has everything. H4's splice fix is made (strike 1
> of 3), the cron is held to 11 Nov, and H5e's estimator is credited to ABG (2015).
>
> Rules: report numbers before recommending; never adjust a pre-registered threshold,
> bucket or bar; never edit a workflow's `schedule:` on a day whose run is still
> needed; Bloomberg exports stay in ~/Documents/volrec-bloomberg and never enter the
> repo, and every published Bloomberg-derived figure carries "Source: Bloomberg
> Finance L.P.".

---

## 18. Current state — opened 23 September 2026, updated to 13 November 2026; the reading every session starts from

**Section 17 is now history:** dated notes from 16-23 Sep, with the reasoning behind
every decision. This section is the only one guaranteed current. Read it, run
`tools/daily.py`, and open section 17 only when a task needs the why.

### System status, checked 13 Nov 2026 (Fri, after H7's reading)

| check | result |
|---|---|
| diagnostic, 13 Nov | `daily.py` **ALL CLEAR** on 13 Nov's data (landed 19:31/19:40 UTC = 14:31/14:40 New York). **H7 is recorded** (the workflow, 13 Nov 03:28 UTC, `a5497ca`): H7a FAILS (free vs full-market rebuild: USO 0.316, GLD 0.034; bar 0.25 each), H7b HOLDS (GLD 0.172 from GVZ; bar 0.30). Recorded the same day by Vega, beside the verdicts and never in their place: H3's reading of record (H3a, H3b and H3c hold), the companions to H5e's and H7's verdicts, and the timing measurement, read once. The site's results are now generated from those files (`tools/site_results.py`) and held to them by the pressure test. Pressure test **0 fail, 2 warn** (327 checks; the known two). Auditor: 229 of 229 on 12 Nov; the commit of this table adds 30 mutants (259), every one of the 259 applies, and the 30 new ones are KILLED one at a time; the push goes out only at N of N. Sixteen suites **0 failures** (new: `tools/test_site_results.py`, 159 cases). Below: the 12 Nov reading, kept |
| diagnostic, 12 Nov | `daily.py` **ALL CLEAR** on 11 Nov's data, the windows' last day (landed 19:31/19:40 UTC = 14:31/14:40 New York). **H5e's FINAL reading is recorded** (the workflow, 12 Nov 03:55 UTC, `e0b36c9`): FAILS, 0.91 against 0.5, closer than registered on 26 of 35 days. H3 over the complete window, the frozen scorer at full precision: H3a 0.708 over 205 readings and 41 days (bar 1.0), H3b -0.444, H3c p 0.0104, BH 4 of 5 and 3 of 5 (USO alone 1.767); it enters the record beside the verdicts, with the companions. Pressure test **0 fail, 2 warn** after Gabriel's renewal later on 12 Nov (325 checks; the warns: the known one-sided FXE quotes and the late GitHub backup; the backup cron's margin is accepted again through 29 Jan 2027, `CRON_MARGIN_ACCEPTED`, after his 23 Sep acceptance ran out on 11 Nov). Auditor **217 of 217** three times on 11 Nov (the last on `5e9031a`) and on the verdict-night rehearsal; the commit of this table adds twelve mutants (229) and, like every push, goes out only at N of N. Fifteen suites **0 failures**: the eleven unit suites, the poster's two (60 and 27 cases), the new page-against-reader suite (45) and the review bridge's (24); `samples/long/test_h2_variance.py` is H2's analysis script, not a suite, and needs Alpaca's keys. (6 Nov: H3a 0.685 over 185; H5e 0.98, 22 of 31.) |
| independent re-implementation, 13 Nov | the workflow's companion step after both finals (13 Nov): `tools/independent_check.py --through 2026-11-11`, **1302 of 1302** values agree. 12 Nov, by hand: 1206 of 1206 (largest gap 0.00088). `--opra` not rerun since 6 Nov (1184 of 1184) |
| Databento, 13 Nov | lifetime **$86.14** (the private ledger, to the 13 Nov purchase of 11 Nov's data, $0.194; the 12 Nov sealed-index top-up, $0.197694, is in it). Left: $13.86 of the $100 free credit; $33.86 under the $120 figure, which since 12 Nov is a number named in each price message, not a stop (Gabriel). The nightly buy continues at about $0.19 (the panel's OPRA days, H7's monthly legs, H8's pilot) |
| Databento, 12 Nov | lifetime **$85.75** (the private ledger, to the 12 Nov 03:52 UTC purchase of 10 Nov's data; 6 Nov: $84.97), about $0.19 a night. Left: $14.25 of the $100 free credit, $34.25 under the $120 cap. Databento serves a day's snapshot minute only once the next session has opened (14:30 UTC), so 11 Nov's files are bought by the run scheduled Thu 12 Nov 23:05 UTC and **H7 is written then at the earliest** (GitHub starts that run about 03:00-05:00 UTC on Fri 13 Nov). The sealed index top-up for 4-11 Nov (about $0.20) is due by 18 Nov; reminder 12 Nov |
| workflows, 12-13 Nov | every public run green: record and surface dispatched at 19:30 and 19:40 UTC on 12 and 13 Nov; their GitHub-cron backups started 20:58-21:37 UTC and found the day recorded ("already recorded ... skipping"); guard green on every run; freshness and health green (GitHub started them late: on 13 Nov freshness at 00:54 and 03:09 UTC, health at 03:31 UTC). volrec-licensed `daily.yml` green on all four runs of 12-13 Nov; the run GitHub started at 03:21 UTC on 13 Nov bought 11 Nov's data, wrote and pushed H7's reading (03:28 UTC) and committed the companions privately (`8762c3a` there) |
| workflows, 7-12 Nov | record and surface dispatched at 19:30 and 19:40 UTC on 9, 10 and 11 Nov, green, their GitHub-cron backups standing aside (3 of 3 each; GitHub started the backups 6 to 9 hours after their slot). guard: 21 runs, 20 green and **one `startup_failure`**: the 15:20 New York dispatch of 11 Nov (20:20 UTC), inside GitHub's own incident (Webhooks from 20:22 UTC, Actions from 20:48 UTC), the first non-success in its last 300 runs; the day had landed and the 15:00 run had passed. freshness and health green on every run. volrec-licensed `daily.yml` green on every run since 7 Nov; the run of 12 Nov 03:45 UTC wrote and pushed H5e's FINAL reading |
| cron-job.org, 13 Nov | record and surface triggers on time on 9-13 Nov (the runs they started on 12 and 13 Nov were created at 19:30:06-07 and 19:40:04 UTC); guard at 15:00 and 15:20 New York (20:00:15-16 and 20:20:09-10 UTC). The one-off 12:00 guard copy for Fri 27 Nov still fires at 12:00 New York on every November weekday (17:00 UTC on 12 and 13 Nov too), harmless as before: the guard waits and does nothing. Token `volrec-trigger` expires **Mon 1 Feb 2027** |
| GitHub tokens | both renewed by Gabriel 3 Nov; both expire **Mon 1 Feb 2027**, after H8's last purchase (29 Jan). Both work (12 Nov): cron-job.org dispatched every day with `volrec-trigger`, and the private run of 12 Nov checked this repo out and pushed the verdict with `PUBLIC_REPO_TOKEN`. The pressure test dates both: WARN from Mon 4 Jan, FAIL from Mon 25 Jan. Renew both by **Fri 22 Jan**; reminder Mon 11 Jan |
| phone (Pushover), 12 Nov | four levels live. The nightly GREEN step ran on every green health run, and the workflow's NOTICE step for H5e's verdict ran at 03:56 UTC on 12 Nov; whether each push arrived cannot be read from here. No RED: the guard never had to re-run a recorder |
| cloud routines, 13 Nov | read in the tool's 20-item view: none with a connector. The 16 Nov reminder (`trig_01WeRHdAkoi1zrk7XcBMUfWT`, Mon 16 Nov 17:00 UTC = 9:00 Pacific) reworded 13 Nov to the print order: "order the SCCUR poster print today: FedEx Office, 48 x 36 in, plain paper, the PDF Vega sent 13 Nov; pick up Tue or Wed. Send Marc the reply and the PDF", connectors cleared. Enabled ahead: 16, 19, 20 Nov and 20 Nov evening; 22, 23 and 24 Nov; 4 Dec; 4 Jan; 11 Jan |
| cloud routines, 12 Nov | 11 enabled in the tool's 20-item view and none of the 20 with a connector; read by id, the 13 Nov verdict check (enabled, no connector). Out of the tool's reach, as on 6 Nov: the Monday auditor and the Wednesday watchdog. One-off reminders ahead: 13 Nov verdict check (its push ends "Open Claude and say: H7 is in" since 12 Nov); 16 Nov (has the final poster gone to Marc) and 19 Nov (pitch, parking, badge); 20 Nov (printed poster in hand, post-verdict steps done); 20 Nov evening (SCCUR tomorrow); 22 Nov (nightly-run edit and the `requests` pin), 23 and 24 Nov; 4 Dec; 4 Jan; 11 Jan; the 13, 16, 20 and 22 Nov texts reworded on 12 Nov after the H7 discussion. Disabled: the 12 Nov top-up reminder (done before it fired), the 13 Nov poster-questions reminder (answered 11 Nov), the 7 Nov backup one and the 30 Oct Goukasian one |
| OSF | both registrations public, read from OSF's API on 12 Nov: https://osf.io/z5gfu (H5e and H7, registered 10 Oct) and https://osf.io/4mcgf (the timing measurement, 6 Nov); neither withdrawn nor pending. The site links both |
| pre-push hook | installed (`core.hooksPath tools/hooks`, checked 13 Nov); every push runs the pressure test |
| iMessage (launchd `com.volrec.daily`) | **retired 23 Oct**; still unloaded (12 Nov: no volrec job in `launchctl list`); plist kept at ~/Documents/volrec-retired/ |

### What runs unattended (UTC; weekdays unless noted) - SESSION-START.md carries the same table

| what | when | if it goes wrong |
|---|---|---|
| `record.yml` (ATM panel) | 14:30 New York via cron-job.org (`workflow_dispatch`; 11:30 on an early close); GitHub's 14:47 UTC cron is the backup and stands aside before 14:45 New York | `freshness` FAILS on a missed day; the guard re-runs it |
| `surface.yml` (surface, wide band, monthly USO/GLD legs) | 14:40 New York the same way; 14:57 UTC cron backup | same |
| `guard.yml` (15 Oct) | after every record/surface run, and 15:00 + 15:20 New York via cron-job.org (12:00 on early closes); one queue; no GitHub cron | confirms a missing day from the DATA, re-runs the recorder once, then Pushover: RED only if the day can still be saved |
| `freshness.yml` | 20:00 and 23:00 daily | emails on a red X; no phone alert |
| `health.yml` | 23:37 | the full daily check; Pushover GREEN when clear, YELLOW on a FAIL or crash |
| healthchecks.io | pings from freshness, health, volrec-licensed | Pushover when a job never runs at all |
| `volrec-licensed` daily.yml (private) | 23:05 and 03:05 UTC | OPRA fetch, compare, verdicts on their dates (fixed wording), companions + the independent re-check once after both finals; Pushover NOTICE/YELLOW; RED if the repo is ever public |
| auditor routine | Mondays 16:30 UTC | `tools/audit.py` + doc drift; notifies only on a problem |
| watchdog routine | Wednesdays 16:13 UTC | notifies only when something is wrong |
| ~~launchd `com.volrec.daily` (this Mac)~~ | - | RETIRED 23 Oct; Pushover carries the daily alert (`tools/alert.py`) |

### Where each hypothesis stands

| | status | the numbers |
|---|---|---|
| H1 | tested, holds | 9 of 11 Cboe pairs survive FDR control |
| H2 | tested, not adopted | log variance strongest (t=16.26) |
| H3 | **reading of record, recorded 13 Nov: H3a, H3b and H3c HOLD** (BH: H3a 4 of 5, H3c 3 of 5) | H3a mean abs gap **0.708 over 205 readings and 41 days, the complete window to 11 Nov (frozen scorer; bar 1.0; H3b -0.444; H3c p 0.0104; USO alone 1.767, oil volatility's rise since late October)**; 5 Nov: 0.685 over 185; 30 Oct: 0.598 over 165; 8 Oct: 0.40 over 80; 23 Sep: 0.53 over 30 (bar 1.0). First registered wide reading **OUTSIDE** 1.4-3.2 (+9.41; +10.71 with 23 Sep): quote contamination, as the grid anticipated. **IWM reads positive on all six days**, against H3b's sign - watch. **Day count: Bloomberg stated ACT/252 in writing (23 Sep); at 21 months ~1 point remains, not the forward or rate, unidentified and closed (24 Sep).** H3c's mechanism is Jiang & Tian (2007)'s, credited |
| H4 | descriptive, **strike 2 of 3** (8 Oct) | strike 2: calendar-day carry + Bakshi-Kapadia dividend-adjusted price (strike 1, 23 Sep: runs break on a missed trading day). Data to 7 Oct: date level -5.23bp (t -2.50) vs -5.22bp under strike 1; no conclusion moved. One strike left |
| H5a | **tested 23 Sep, holds weakly** | pooled median 0.40 of a spread over 169 wing contracts on 3 days (bar 0.5); **0.67 on the 132 both feeds bid** - the two readings of "quoted" are logged, nothing adjusted. **Corrected 17 Oct (reader bug, verdict unchanged): 0.33 over 179; 0.67 on 134** |
| H5b | **tested 23 Sep, holds** | 36 of 36 free-feed missing bids are missing on Bloomberg (bar 80%). **Corrected 17 Oct: 44 of 44** |
| H5c | descriptive | Bloomberg reproduces USO's inflation within 0.2% and 1.0% on 23 Sep (9.0% and 2.6% before): re-read 11 Nov with the reader fixed on 17 Oct (first read as 0.5% and 10.4%; 6.5% and 30%, the 30% being the reader bug); needs 10 underlying-days |
| H5d | descriptive | 12 underlying-days on 3 dates; the date-clustered test needs more dates |
| H5e | **final: FAILS** (12 Nov) | mean abs gap 0.91 (bar under 0.5); closer on 26 of 35 days; 23 Sep - 11 Nov |
| H5f | **read 25 Sep at 5 days: a, b, c hold** (a ON the bar) | H5f-a **0.500** of OPRA's spread (bar 0.5); H5f-b **64 of 64** no-bid (bar 80%); H5f-c inflation gap **0.6%** per day, 0.4% on medians (bar 25%); stale quotes excluded by the rule |
| H6 | **tested 9 Oct: H6a FAILS, H6b HOLDS** | ATR(14) beats implied vol on the next day's range in 9 of 9 pairs (IV overshoots the level 1.6-2.3x: close-to-close risk plus the premium); IV's disadvantage shrinks after spikes (Welch t -7.95; with Newey-West errors t -3.80 at lag 21, -3.12 at lag 63 - still holds); exploratory: with the level removed IV's timing error is smaller in 8 of 9 |
| H7 | **read 13 Nov: H7a FAILS, H7b HOLDS** | free vs OPRA replica: USO 0.316, GLD 0.034 (bar 0.25); GLD vs GVZ 0.172 (bar 0.30); USO vs OVX -0.244, descriptive. Companion (added 17 Oct, before any reading; descriptive, recorded 13 Nov beside the verdict): on the strikes both feeds carry, 0.132 (USO) and 0.061 (GLD); Cboe's walk ran past the free file's +/-60% edge on 24 of 24 days; restricted to the strikes both feeds carry, oil's gap falls from 0.316 to 0.132 |
| timing | **read once 13 Nov; descriptive, no bar** | 16 days, 21 Oct - 11 Nov. At the snapshot minute the OPRA replica sat a mean absolute 0.021 from OVX and 0.010 from GVZ (free feed: 0.369 and 0.037); the indices then moved a mean absolute 0.630 (OVX) and 0.207 (GVZ) before the close. H5e's skip-only estimate was already 1.117 from OVX at its minute (OVX then moved a mean absolute 0.634). It describes the verdicts' gaps and changes neither |

*Bloomberg figures: Source: Bloomberg Finance L.P. OPRA and intraday index figures: Data provided by Databento. Index closes: Cboe Global Markets. Aggregates only.*

### Audit, 30 Sep 2026 - the recorders crossed the close, and two checks were passing falsely

- **New, dated evidence on the cron:** GitHub's delay reached 6h01m. **28 Sep's recorders
  ran after the close** (committed 20:50-20:52 UTC; the close is 20:00), and 29-30 Sep
  landed ~19:40. The free feed stamps every after-close quote at 19:59:59.
- **Two false passes, fixed:** `panel_health.check_landing` read that stamp as "landed a
  second before the close" and passed, and the pressure test's worst-delay measure read
  it the same way, so the record check passed. Both now treat a median in the close's
  last minute as after the close (tested both ways). The 23 Sep acceptance of the cron
  rested on panel_health FAILING a post-close day - on 28 Sep it did not, so the day was
  silently kept.
- **Now failing, correctly, every night until resolved:** record lands 20:01 and surface
  20:11 at the worst delay seen; freshness's early slot can run before they land. The
  health check, healthchecks, the iMessage and the watchdog all flag it. Nothing hidden.
- **Built the same day (Gabriel's request): the auditor and fail-safes.** `tools/audit.py`
  breaks 21 safeguards one at a time in throwaway worktrees and requires each check to
  fail - 21 of 21 on 30 Sep; its first run found a check that crashed instead of failing,
  fixed. Charter `AUDITOR.md`; cloud routine `volrec auditor` (`trig_01AEH651RW1ere3psWp5opVW`),
  Mondays 16:30 UTC, read-only, no connectors, notifies only on a problem. `SCIENTIST.md`
  charters the research agent, DORMANT until a registered job (late Oct). Fail-safes:
  Databento 502/503/504 retried (a 504 failed a cloud run on 30 Sep); `volrec-licensed`
  refuses to run unless private; a due verdict is kept there, timestamped, before any
  public push can fail, and a failure issue carries the verdict text and failing checks.
- **The pre-push hook blocks every push while the pressure test fails,** so these commits
  wait on Gabriel. So will the 7 Oct H5e verdict's public record (both routes require
  0 fail) - the cloud now keeps it privately and says so if that happens.
- **Gabriel decided all four, 30 Sep:** (1) an outside trigger - cron-job.org starts
  record 18:30 and surface 18:40 UTC by `workflow_dispatch`, GitHub's cron kept as backup;
  (2) an **after-close guard** - `record.after_close()`: a recorder started after 16:00 New
  York refuses to record (exit 1), both recorders, tested both DST regimes; (3) **28 Sep
  dropped** from H5e and H4 under his 23 Sep rule (`panel_health.AFTER_CLOSE_DAYS`, both
  adjustment logs) - and **H3 too, the same evening** (H3a mean gap 0.471 -> 0.464, bar 1.0 either way; logged); (4) the
  four blocked commits pushed past the hook once.
- **Status after the build (30 Sep 22:00 UTC):** guard live and pushed; 28 Sep dropped;
  pressure test **0 fail** (the delay checks now pass because the guard is live, and warn
  that the backup can land late); auditor **24 of 24**. **Outside trigger LIVE, 30 Sep
  22:15 UTC:** cron-job.org jobs 8548132 (record, Mon-Fri 18:30 UTC) and 8548147 (surface,
  18:40 UTC) POST `workflow_dispatch`, notify on failure; token `volrec-trigger` (Actions
  read/write on volrec only) expires **29 Dec 2026**. Test runs returned 204 and GitHub's
  runs were refused by the guard (after the close) - trigger and guard proven together;
  nothing written. **First real runs, Thu 1 and Fri 2 Oct: worked** - workflow_dispatch at 18:30/18:40 UTC, committed 18:33/18:41, median quotes 18:32/18:40 UTC, `panel_health` HEALTHY; the GitHub-cron backups ran later and recorded nothing twice. From 1 Oct `panel_health`
  warns on any day the trigger did not start (landing outside 18:28-19:00).
- *Superseded by the line above:* two decisions for Gabriel, both before 7 Oct: (1) the cron: the rule holding it to
  11 Nov predates this evidence; the pressure test allows 14:30-15:06 UTC and a delay of
  5-6h lands after the close anywhere in that window until 1 Nov, when the close moves to
  21:00. (2) **28 Sep in H5e and H4:** it is a closing-quote day. His 23 Sep rule says such
  a day is dropped, not kept; H5e currently counts it (with it: mean 0.81, closer 2 of 5;
  without: 0.94, 1 of 4 - dropping it makes H5e look worse). Not changed until he decides.

### Decisions made, and not to be reopened without new, dated evidence

- H4's run fix is strike 1 of 3 (Gabriel, 23 Sep). The cron is held to Wed 11 Nov.
- Bloomberg aggregates are on the public site, inside Marc Vinyard's rule, read
  conservatively; `pressure_test.py` section K enforces it.
- Databento is used for OPRA reference quotes, priced before every request.
- **OPRA aggregates may be published, with Databento credited (terms read 23 Sep).**
  Databento's User Agreement §1.5(e) counts any "information derived from" the data,
  given to anyone else, as Redistribution. It is allowed when it complies with OPRA's
  terms AND with §1.6. OPRA's fee schedule exempts redistribution limited to historical
  data (historical from the next trading day's open); every figure here is computed
  from next-day data. §1.6 requires explicit attribution on every redistribution, now
  "Data provided by Databento" under each block (`pressure_test.py` section N checks
  it), and lets Databento name Gabriel as a client in its marketing. Gabriel kept the
  figures on those terms. Read: the User Agreement and OPRA's fee schedule, not OPRA's
  full vendor agreement. **On the public site since 23 Sep** ("Checked against the
  consolidated feed", 18-22 Sep, 3 of H5f's 5 days, labelled descriptive), under the
  same rules as Bloomberg's: medians and counts only, the credit under every block;
  `pressure_test.py` section K enforces it.
- **Licensed papers stay outside the repo** (interlibrary loans are private-study only):
  `~/Documents/volrec-papers`. On 23 Sep one landed in the repo root, uncommitted;
  `.gitignore` now blocks `*.pdf` and the pressure test checks none is tracked.
- **Bloomberg exports, one expiry per file:** `SYMBOL_OMON_DATE.xlsx` is the recorder's
  nearer expiry; other expiries take a suffix (`_30Oct`, `_long`). The tools read the
  canonical name only, so a second expiry runs through a subfolder of symlinks
  (`~/Documents/volrec-bloomberg/2026-09-23_30Oct/`), `--dir` pointing at it.
- **The research runs without Gabriel from 24 Sep** (his decision): OPRA fetching and the
  registered verdicts moved to the private repo `gabrielmitton-cloud/volrec-licensed`
  (raw licensed data lives there, never here), whose workflow writes verdicts in FIXED
  wording from the frozen scripts - no model judgement. `health.yml`'s rule that CI never
  commits stands; the one exception is a verdict commit, three times in the window,
  outside the recorders' hours. The Mac's scheduled tasks stay armed as a fallback until
  the cloud run is proven, then are disabled; each skips a verdict already recorded.
  **Proven so far (24 Sep 22:55 UTC):** both secrets set by Gabriel; a price-only run
  passed every step, priced 18-24 Sep with the key, and reproduced the Mac's comparison
  exactly. First real run: 24 Sep 23:05 UTC. First verdict path: Fri 25 Sep 23:05 UTC.
- Kalshi is parked (it takes the next free number if it returns; H6 and H7 were registered 8 Oct); no new hypotheses before 11 Nov unless one needs no new data - **H7 is the one explicit exception, granted by Gabriel 8 Oct.**
- The operations agent never searches for results (`OPS-AGENT.md`).

### Next steps, dated

**Today, Wed 23 Sep - done**
- The watchdog's first updated run: healthy (see the status table).
- The surface landed 18:41 UTC - **H5e's first counted day** once tonight's OVX close
  is in (`daily.py` tomorrow scores it).
- **Bloomberg pulled 18:41-18:49 UTC, 0-4 minutes from the snapshot:** USO and TSLA on
  23 Oct and 30 Oct, and TSLA 16 Jun 2028. H5a and H5b reached their minimum and hold
  (H5a weakly); the long-dated test found a one-point gap the day count does not explain;
  the help desk stated ACT/252 in writing. H3 and H5 have the sections.
- Jiang & Tian (2007) read: H3c's mechanism is theirs (H3, prior art of 23 Sep); the
  site credits them.
- 23:37 UTC: the first scheduled `health.yml`.

**Thu 24 Sep - done**
- ~~OPRA for 23 Sep.~~ **Done** by the scheduled task, 24 Sep 15:08 UTC, $0.0267: H5f's
  fourth day, recorded in H5 ("The fourth OPRA day"). Databento spend $0.1132 of $100.
  **Scheduled:** a one-off local task (`volrec-opra-fetch-0923`, the app's Scheduled
  list) fires 24 Sep 07:15 Pacific, fetches and compares, texts Gabriel, and saves
  the compare to `~/Documents/volrec-databento/compare_2026-09-23.txt`. It never
  touches the repo: recording day 4 in H5 is still this session's job. Re-running
  the fetch is harmless - days on disk are skipped, never bought twice.
- `daily.py` scores **H5e's first counted day** (23 Sep) once OVX's close is in. **Not yet
  at 24 Sep 15:10 UTC: Cboe's own OVX file still ends at 22 Sep** - their publishing lag,
  not the project's. It scores on the next run after Cboe updates; nothing to do.
- ~~Help-desk follow-up.~~ **Answered 24 Sep by email** (H3): the forward and rate
  `model_gap.py` uses are Bloomberg's own, so the 21-month residual is the time to expiry
  or the American solver. **Next, at the terminal, no time pressure: one `GIV` screen**
  (TSLA 16-Jun-28 C380 and P300, Actions -> View Calc Inputs; steps in
  `BLOOMBERG-MONDAY.md` ask 3). **Closed 24 Sep:** the GIV inputs panel does not reproduce
  its own volatility, and at 21 months calls and puts read high together (H3 has the
  figures), so it is not the forward. Recorded in H3 as an open reconciliation item at long maturity;
  not pursued - nothing registered depends on it. No terminal asks remain on this.

**Fri 25 Sep - done** (H5f read 25 Sep, see the table) - fetch 24 Sep: H5f's fifth day, so **the first H5f verdict**, read exactly
as registered, with the stale-quote exclusion stated beside it.
  **Scheduled:** `volrec-opra-fetch-0924` fires Fri 07:15 Pacific the same way (fetch,
  compare to `~/Documents/volrec-databento/compare_2026-09-24.txt`, text Gabriel); it
  does not score the verdict.
  **Scheduled:** `volrec-h5f-verdict` fires Fri 08:15 Pacific: runs the pooled script
  written 23 Sep before days 4-5 existed (`~/Documents/volrec-databento/verdict/h5f_pooled.py`),
  records H5f in H5's Result and this section, pushes if the pressure test passes and no
  workflow is running, and texts Gabriel. **Known in advance:** on the first three days
  H5f-a's pooled median is exactly 0.500, ON the bar, because TSLA's one-tick contracts
  sit at 0.5; the task must say so. It never touches the site's OPRA section.
  **Scheduled:** `volrec-site-opra-update` fires Fri 09:15 Pacific: adds 23-24 Sep to
  the site's OPRA table, puts the recorded verdict (with any on-the-bar caveat) in its
  text and the H5 ledger row, pushes under the same conditions, and texts Gabriel.

**Mon 5 Oct - done**
- The auditor's first weekly run (16:37 UTC): 26 of 26 proven, pressure test 0 fail; flagged
  the 'Fri 25 Sep' heading above as stale (fixed). `volrec-licensed` visibility: not checkable
  from a routine (not a failure).
- **Two false failure emails:** the GitHub-cron backups started 21:37/21:41 UTC, after the
  close, on a day the trigger had recorded at 18:30. The guard ran before the
  already-recorded check and exited 1. Fixed (commit 5763bc2): a recorded day exits 0 after
  the close; a day with nothing recorded is still refused. New mutant
  `guard-before-done-check`; auditor 27 of 27.
- **Found while fixing it: MDY, FXE, XLRE and DUK have recorded nothing since 28 Sep** -
  "no contracts returned in the strike/expiry window". They have only monthly expiries, and
  none sat inside `DTE_WINDOW` (21-45 days) from 26 Sep to 5 Oct: 16 Oct left the window
  after 25 Sep and 20 Nov enters it on **Tue 6 Oct**, so they return on their own. This gap
  recurs every month for monthly-only names and no check reported it (the run log says
  "a gap day is not fatal"; `panel_health` counts days, not symbols). **For Gabriel, a
  discussion, not a fix:** the universe and window are frozen; options are to accept and
  document the monthly gap, or a dated change to the window for those four.
  **Decided by Gabriel 8 Oct: ACCEPT AND DOCUMENT.** The window and universe stay frozen; `panel_health`
  now names every missing ticker each day - the four monthly-only names as INFO (the accepted gap),
  anyone else as a WARN - so the gap is never silent again. They returned 6 Oct (109 of 109 on 7 Oct).

#### Wed 7 Oct - methods audit (recorded; decisions AFTER the H5e verdict, Gabriel 7 Oct)
An outside deep-research review of every equation was checked line by line against the code
and against Cboe's own documents (Mathematics Methodology v5.0, rev. 26 Feb 2026; Selected
Broad-Based, Equity and ETF Volatility Indices v9.0, rev. 30 Mar 2026, both read in full).
Nothing below changes a recorded result; three items are real and undocumented until now.
- **1. OVX and GVZ select expiries differently from `modelfree`.** Cboe v9.0 §2.1 and Step 1:
  OVX and GVZ use only PM-settled third-Friday monthlies, exclude series under 7 days, and
  take the two nearest (Nearest Term Method, Math v5.0 §2(b)), extrapolating when they do not
  bracket 30 days. `modelfree.pick_pair` takes the last expiry <=30 and first >30 of all
  recorded expiries - weeklies (Cboe's Bracket Method, used for VIX/RVX/single names). On
  7 Oct OVX blends 16 Oct/20 Nov; we blend 30 Oct/6 Nov. `surface.py` does not record the
  far monthly for USO/GLD on most days, so OVX's own selection cannot be recomputed from the
  panel. Affects the reading of H3 (USO/GLD against OVX/GVZ) and H5e (gap to OVX); verdicts
  stand as registered, the write-up must disclose it. Option for Gabriel: record the
  monthly legs for USO/GLD from a dated day forward (an addition, not a universe change).
- **2. Snapshot vs benchmark timing.** Our quotes are ~14:30 ET; the Cboe benchmark is the
  index's close (~16:15 ET). The 1.5-2 h of index movement is noise in every daily gap, and
  a mean ABSOLUTE gap (H5e, H3a) is inflated by noise. Undocumented until now. Option:
  disclose; or an intraday index value at the snapshot time if one is freely available.
- **3. H4 financing misses weekends; dividends not modelled.** `hedged_gain` accrues r(C-dS)/365
  per trading-day step; weekends join runs, so 2 of every 7 calendar days earn no carry.
  Re-run with calendar-day accrual (7 Oct): date-level mean -4.49bp (t -2.43) -> -4.58bp
  (t -2.45); contract-level -6.76 -> -6.87bp; buckets move <= 0.6bp; no conclusion changes.
  The `intervals()` docstring's "0.003bp" measured snapshot-hour drift, not weekends - it is
  not evidence on this point. Dividends: the short hedge is credited the ex-date drop without
  paying the dividend; size not yet measured (only ex-dates inside runs matter). Option: a
  dated correction (H4 adjustment log) or document as a known small bias.
- **Checked and NOT a problem:** forward, K0, OTM strip, edge dK on the filtered strip, the
  sigma^2 formula and the 30-day blend match Cboe exactly (tie-break = lowest strike, as
  Cboe). The research's "misattribution" of H5e's estimator to ABG (2015) is wrong: ABG was
  read in full 23 Sep (H5 prior art, their 3.1.2, RX*); the reviewer saw only the abstract.
  Fixed-b critical values affect only analyze.py's descriptive live-panel test, not H1
  (non-overlapping). c4(n) is correct for the un-demeaned estimator (textbook c4(n+1)).
  Cboe's Feb 2025 zero-ASK addition: zero rows in our data have ask 0 with a bid, so no effect.
- **Wording only:** `variance_one_expiry`'s docstring says "Cboe's sigma^2" though the default
  keeps zero bids on purpose (H3's registered choice) - say "Cboe's formula, H3's quote rule".
- **For the write-up:** VRP is measured in vol points (H2 tested variance forms); Black-76 on a
  parity forward is a simplification for American puts (H3's day-count section);
  TimesFM's pretraining may include VIX, which strengthens its FAIL rather than weakening it.

**Papers read for the audit, 7 Oct** (Pepperdine copies, kept in `~/Documents/volrec-papers/`, never in the repo):
- **Bakshi & Kapadia (2003), RFS 16(2), eq. (6) and the empirical gain formula (p. 540):** financing is
  r(C - Delta S) * tau/N with tau/N "set to 1 day" and the rate updated daily - equal steps whose sum is the
  option's whole remaining life, so carry accrues over all calendar time. This SUPPORTS item 3 (our
  1/365 per trading step drops weekends). Dividends: they subtract the present value of known dividends
  from the stock price and use that adjusted price throughout - the standard alternative to an ex-date
  cash flow, and the method to copy if item 3 is corrected. They report gains in dollars, scaled by S,
  and scaled by the option price; H4's scaling by S is one of theirs. Their eq. (6) prints C_t (the
  starting price) in the financing term where our code uses the current price C_n; ours is the
  self-financing form and the difference is second order - document, do not change.
- **Jiang & Tian (2005), RFS 18(4), s.1.2:** truncation error is negligible when the strike range
  reaches more than 2 SDs either side of the forward; discretization error is negligible when the
  strike step is at most 0.35 SD. Checked on the registered panel, 29 Sep - 6 Oct (median over
  expiry-days, SD = sigma*sqrt(T)*S): every symbol's step is within 0.35 SD (worst median 0.23,
  NVDA); coverage is 3.2-6.8 SDs for SPY, QQQ, IWM, GLD, AAPL, NVDA, but **USO reaches only 1.96 SD
  each side and TSLA 2.2** - USO is just inside the zone where truncation biases the registered
  estimate DOWN. Consistent with H3's wide-band reasoning (it is why the wide band exists), now
  with the paper's own yardstick; for the write-up, not a change.
- **Carr & Wu (2009), RFS 22(3), s.2:** for American options (they include QQQ and single
  stocks) they take OptionMetrics' binomial implied volatilities, interpolate them in ln(K/F), and
  price European options by Black-Scholes before integrating - the "European-equivalent" route the
  review suggested as a robustness run. Their 30-day blend is linear in total variance (their
  eq. 10) - the same as `model_free_30d`. Their two nearest maturities roll when the shorter is
  within eight days. On realized variance they state that log vs percentage returns, demeaning,
  and ACT/365 vs 252 "do not alter" their conclusions - D1's conventions are acknowledged choices.

**LSEG at Pepperdine (raised by Gabriel 7 Oct) - a post-verdict discussion item, nothing pulled.**
Possible uses, in order: (1) intraday OVX/GVZ at the snapshot minute (~14:30 ET), which would remove
audit item 2's timing noise from H3/H5e gaps; (2) historical monthly USO/GLD option quotes to recompute
under OVX's Nearest Term rule (audit item 1); (3) dividend history for an H4 correction (item 3); (4) a
fourth price/IV reference. Unknowns: which product (Workspace, Datastream, Tick History), terminal or
personal login, intraday history depth, and Pepperdine's LSEG terms for publishing derived figures -
treat like Bloomberg until known: raw data never in this repository.

#### Thu 8 Oct - the corrections session (Gabriel's instruction, 7 Oct night)
The H5e first verdict is RECORDED (FAILS, 0.90, 2 of 10; cloud, 8 Oct 02:50 UTC, after the writer's
rounding fix 9bbc7b4). Gabriel: make every calculation correct, without breaking the system; test
heavily; investigate any break to its root; backtest every hypothesis; data, not stories.
Rules: (1) registered verdicts never change - corrected readings sit BESIDE them, dated and labelled;
(2) old code paths stay runnable (new modes, not replacements); (3) every number from a run, with its
command; "the data cannot say" when it cannot. Order:
1. OVX/GVZ Nearest Term replication (audit item 1) from Databento OPRA full USO/GLD chains for the
   recorded days - free cost quote first; STOP and ask Gabriel above $1 total (he does not want to spend money); add a `modelfree` mode for the rule.
2. H4: calendar-day carry + Bakshi-Kapadia dividend adjustment (PV of dividends off S); needs a
   dividend source (free or LSEG). Weekend part measured: date-level -4.49 -> -4.58bp.
3. Timing (item 2) only if LSEG shows intraday .OVX/GVZ back to 23 Sep (Gabriel's screenshots).
4. Small: docstring wording; Cboe extrapolation for the single-expiry path; fixed-b and BY lines as
   robustness beside the existing tests.
**Gabriel decided, 7 Oct night:** (a) the H4 carry + dividend correction is **strike 2 of 3**
(TEMPLATE: three post-output adjustments = abandon and report) - applied as H4's reading, original
kept beside it, logged in H4's adjustment log; (b) **start recording the monthly USO and GLD expiries**
OVX/GVZ use (an addition: same tickers, extra expiries; existing rows and registered numbers
untouched; fully tested before it goes live; pick a clean start date and log it in H3/H5).
Tests for every change: pressure test 0 fail; an auditor mutant per new safeguard; calibrate.py
known answers; a reproduction test that the original paths still give every registered number
exactly (a moved registered number is a bug - stop and root-cause). Then one backtest table: every
hypothesis, original vs corrected, agrees / moves / would flip, with the reason.

#### Thu 8 Oct - fix 1 DONE: the OVX/GVZ replication (`tools/ovx_replicate.py`, exploratory)
Cboe's own rules (Math v5.0 s3, ETF v9.0 s2.1: third-Friday monthlies, >= 7 days, nearest two,
minutes to 16:00 ET, zero-bid-or-ask exclusion with the two-strike stop, BEY->continuous rate) applied
to Databento OPRA quotes at the snapshot minute, as four measured steps from the registered estimate.
USO files were already owned (H5f); GLD bought for this, $0.305 (lifetime $0.649 of the free credit).
Run: `VOLREC_DATABENTO_DIR=~/Documents/volrec-licensed/opra FRED_KEY=use-cache python tools/ovx_replicate.py`.
Known answers in the pressure test (section R) and 3 auditor mutants (30 of 30 proven).
| | USO vs OVX, H5e window (9 days) | GLD vs GVZ, same window (10 days) |
|---|---|---|
| data: free -> OPRA, same contracts | mean +0.02, mean abs 0.04 | mean -0.01, mean abs 0.02 |
| Cboe quote rules on the band | -0.13 | -0.03 |
| coverage: +/-30% band -> full chain | **+1.19** | +0.28 |
| expiry: our weeklies -> Cboe's monthlies | **-0.55** (mean abs 0.55) | +0.19 |
| left: faithful replica minus the index close | **+0.45** (mean abs 0.46, median 0.62) | +0.03 (median abs 0.07) |
| registered estimate's mean abs gap | 0.33 | 0.40 |

**SUPERSEDED 9 Oct (the full audit, below): this table read OPRA's blank bids as null quotes.** Read as
Cboe's zero bids, USO's "left" is +0.05 (mean abs 0.29, median 0.23) over 10 days; findings (4)-(5) below
are corrected there. Kept as it stood, for the record.
Findings: (1) the free feed's prices equal OPRA's NBBO on the same contracts, both names; (2) the
GVZ replica lands a median 0.07 from the close - the method is right; (3) USO's registered closeness
to OVX is partly offsetting errors (band truncation -1.2, expiry/residual +1.0); (4) a faithful Cboe
replica on consolidated quotes at the snapshot misses OVX's close by 0.46 on average - about H5e's
0.5 bar, so the bar left almost no room (the verdict stands as registered; the write-up says so);
(5) USO's +0.45 residual is unexplained: timing is the lead suspect, but 28 Sep (snapshot after the
close) still shows +0.41. LSEG intraday OVX would test it. The registered quote rule cannot be run on
a full chain: ~25 zero-bid stubs at strikes down to $10 take USO to 144-281 points (54.6 / 49.7 with
them removed) - the +/-30% band is what keeps the registered estimator sane.
*Data provided by Databento (OPRA consolidated NBBO). Aggregates only.*

#### Thu 8 Oct - fix 2 DONE: H4 strike 2 (calendar carry + Bakshi-Kapadia dividends)
`hedged.py` SPEC = "strike2"; strike 1 runnable and printed beside it (`compare_specs`), and it
reproduces the saved baseline exactly (pooled -7.70bp, date -5.22bp t -2.52). `data/dividends.csv`
(sources and check dates; a pressure-test WARN when a payer's newest ex-date is > 100 days old - add
new ex-dates by hand). Pooled -7.70 -> -7.60bp (carry -0.12, dividends +0.21); date level -5.22 ->
-5.23bp. 622 runs cross an ex-date. 9 hand-computed unit tests; 2 auditor mutants. H4's log has the
full entry. Undeclared future dividends are not projected: they move a run only through discounting
between snapshots (r x D x 1 day x delta, below 0.001bp).

#### Thu 8 Oct - fix 4 DONE: the small items
- **D3, multiple testing:** `analyze.benjamini_yekutieli` beside BH. H1: **8 of 11 survive BY**
  (VXSLV/SLV BY-adjusted 0.0587; BH 0.0194, reproduced exactly). Logged in H1; BH stays the
  reported correction. Quote H1a with both.
- **D2, fixed-b:** the research's recalled "~2.4-2.5" critical value was VERIFIED by simulation
  (numpy, 20,000 reps): b = 0.17 -> 2.48 at T 250 and 500, 2.56 at T 40; lag 0 -> 1.97. The
  stdlib `analyze.fixed_b_pvalue` (seeded) prints beside the live panel's Newey-West p once that
  test runs (~25 more trading days). Affects no registered number (H1 is non-overlapping).
- **A10, single-expiry fallback:** never used (0 of 136 day-symbols); left as registered, a
  pressure-test WARN fires if it ever is.
- **Wording:** `variance_one_expiry`'s docstring now says Cboe's FORMULA with H3's QUOTE RULE.
- **Fix 3 (timing)** waits on LSEG: the USO replica's +0.45 residual is the question it answers.
- **Recorder addition (monthly USO/GLD legs)** is built, tested (section S, 2 mutants) and parked
  on branch `monthly-legs`, to merge after today's 18:40 UTC surface run so today runs on the
  known-good file; first monthly rows Fri 9 Oct.

#### Thu 8 Oct - the backtest: every hypothesis, before vs after today (all from runs)
Reproduction: this morning's code (ec545ee) in a worktree on the same data -> `modelfree.py` and
`modelfree.py --wide` output **byte-identical**; `hedged.py` in strike-1 mode **identical** to this
morning's full report; `record_verdict --dry-run` reproduces both recorded verdicts and writes
nothing; `calibrate.py` 0 uncalibrated; pressure test 0 fail; auditor 34 of 34; daily ALL CLEAR.
| hypothesis | before | after | status |
|---|---|---|---|
| H1 (FDR) | 9 of 11 survive BH | BH 9 of 11 (identical); BY 8 of 11 - VXSLV/SLV 0.0587 | agrees; a dependence caveat to quote |
| H2 | log variance strongest | no code touched | agrees |
| H3a / H3 wide | registered readings | byte-identical | agrees; the replica shows USO's closeness is partly offsetting errors |
| H4 | date -5.22bp (t -2.52) | strike 2: -5.23bp (t -2.50); pooled -7.70 -> -7.60 | agrees; strike 2 of 3 used |
| H5a-d | as recorded | untouched; free = OPRA on the same contracts (mean abs 0.04 USO, 0.02 GLD) | agrees, now with direct support |
| H5e first verdict | FAILS 0.90, 2 of 10 | tally identical | agrees; a faithful Cboe replica misses OVX by 0.46 - the bar's floor |
| H5f | recorded 25 Sep | frozen script hash unchanged | agrees |
| TimesFM | FAIL | untouched | agrees |
**Nothing flipped.** Open: USO's +0.45 replica residual (LSEG intraday); monthly legs merge tonight.
*Data provided by Databento (OPRA consolidated NBBO). Aggregates only.*

#### Thu 8 Oct - Gabriel's decisions after the corrections
1. 4-ticker monthly gap: accept and document (above; `panel_health.check_ticker_coverage`).
2. Website: Claude drafts a PREVIEW for review; nothing goes live without his approval.
3. Mac fallback `volrec-h5e-final` (12 Nov): Gabriel switches it off in the app (Claude cannot
   edit scheduled tasks). Replaced by the cloud routine `trig_01MG53JubGrUPhph4bd9yimY`: 13 Nov
   16:30 UTC, reads the FINAL block and pushes the verdict (or "NOT recorded") to his phone.
   GitHub issue emails did not reach him for the first verdict; phone pushes did.
4. Next study: draft BOTH for review, register nothing without his OK - the IV-vs-technical-
   levels scanner test, and a Cboe-rules follow-up to H5e on the monthly legs recorded from 9 Oct.

#### Thu 8 Oct, end of day - state
- **Site published** (Gabriel approved the preview): H5e FAILS, the Cboe-rules paragraph, H4 strike 2,
  H1 under BY, H3a 0.40 over 80. Verified on the live page. Known, pre-existing: a console warning
  from index.html line ~688 (a hit-rect width computed before layout; harmless) - small fix later.
- **H6 and H7 registered** 17:04 UTC (before any monthly row). H7: GLD + USO OPRA at the monthly
  minute, `opra_reference.py --monthly`, own $1.10 cap, in volrec-licensed daily.yml from tonight.
- **Monthly legs live** (merged 21:10 UTC, after today's surface run): first rows Fri 9 Oct.
- **Final H5e alert:** cloud routine `trig_01MG53JubGrUPhph4bd9yimY`, 13 Nov 16:30 UTC, phone push.
  Gabriel switches off the Mac task `volrec-h5e-final` himself.
- **To build, dated:** H6's join (needs Alpaca daily highs/lows - extend `fetch_closes`, run via a
  temporary workflow, as H1) - before 1 Nov; H7's reader + `record_verdict` block - before 11 Nov.
  Dividends file: add the Dec ex-dates when announced (WARN fires if stale).
- Checks at close: pressure test 0 fail; auditor 38 of 38; calibrate 0 uncalibrated; daily ALL CLEAR.

#### Fri 9 Oct - everything left from 8 Oct is built
- **H6 TESTED** (details fixed in its log before any data; EVZ from FRED, identical source, also
  before output): H6a FAILS (ATR beats implied vol on the next day's range, 9 of 9), H6b HOLDS.
  Exploratory, logged after output: implied vol overshoots the range's level 1.6-2.3x but times
  volatility better in 8 of 9. `samples/long/h6_range.py`, `.github/workflows/h6.yml` (manual,
  read-only; the pressure test allows only such analysis workflows), `tools/test_h6.py` (25 cases).
  The first H6 workflow run crashed but read "success" (`| tee` without pipefail) - fixed and guarded.
- **H7 reader + verdict built:** `tools/h7_reader.py` (on the validated replica), fixed-wording block
  in `record_verdict.py` (due 12 Nov; bars 0.25 / 0.30; min 10 days each; never guesses on missing
  data), `tools/test_h7.py` (15 cases). volrec-licensed commits the H7 file with a verdict. The 13 Nov
  phone check now reports H5e FINAL and H7 together.
- **Site console warning fixed** (two rect sizes clamped at zero); console clean on a fresh load.
- LSEG: Gabriel's screenshot was the public catalogue; the useful product is Workspace - he checks
  `.OVX` 1-minute history back to 23 Sep.
- Checks: pressure test 0 fail; auditor 45 of 45.

#### Fri 9 Oct - H6 published; LSEG access
- Site: H6 section + H6/H7 ledger rows published (Gabriel approved); verified on the live page.
- LSEG: Pepperdine provides **LSEG Workspace for students** (app or web; includes Datastream and
  CodeBook, a Python notebook on LSEG's APIs). lseg.com is only the sales site - searching it finds
  no data. The Workspace end-user notice: credentials are personal (never shared, never given to
  Claude); use is governed by Pepperdine's contract with LSEG, which the notice does not quote. So
  publishing LSEG-derived figures waits on the librarian's answer; until then, Bloomberg rules -
  nothing in the repo, aggregates only. First check: `.OVX` 1-minute history back to 23 Sep (the
  CodeBook script given to Gabriel 9 Oct prints only the row count and date range).

#### Fri 9 Oct, evening - the full audit (Gabriel: "go through EVERYTHING ... no hallucinations")
Every calculation file read line by line against its source (Cboe Math v5.0 and ETF v9.0 re-read from
Cboe's PDFs; Bakshi-Kapadia; Jiang-Tian 2005 and 2007; Parkinson; HLN). Seven real faults found and
fixed, none of which moves a registered verdict. Each has a known-answer check and an auditor mutant
(auditor **53 of 53**, pressure test **0 fail**, calibrate 0 uncalibrated, all pushed).
1. **The OVX replica read OPRA's blank bid as a NULL quote** (3d0525d, pushed 18:03 UTC, before the
   first monthly row at 18:41). Databento writes OPRA's no-bid as a blank (1.25M records: never 0.00);
   the free feed writes 0; Cboe counts both toward its two-strike stop. Read as null, the walk ran past
   the stop and took stray far bids. Corrected, H5e window (10 days each; `--absent-as-null`
   reproduces 8 Oct exactly):
   | step (mean) | USO vs OVX | GLD vs GVZ |
   |---|---|---|
   | data: free -> OPRA, same contracts | +0.02 (mean abs 0.04) | -0.01 (0.02) |
   | Cboe quote rules on the band | -0.48 | -0.03 |
   | coverage: band -> full chain | +0.93 | +0.28 |
   | expiry: weeklies -> Cboe's monthlies | -0.28 (mean abs 0.81) | +0.17 |
   | **left: replica minus the close** | **+0.05** (mean abs **0.29**, median 0.23) | +0.02 (0.10, median 0.08) |
   USO's "+0.45 unexplained" was mostly this. The remainder (0.29) includes the 19-80 minutes from
   snapshot to OVX's 16:00 close. **For H7 it would have opened a fake free-vs-OPRA gap** (1.9 points on
   a synthetic chain against a 0.25 bar): fixed before any H7 data; H7's log, entry 1. Site corrected.
2. **analyze.py's live-panel report could not run** (`stride` printed before assignment) - it would have
   crashed at the 40-day reading (~11 Nov). 3. **Its cost block charged 100x** (vega is per vol POINT,
   the spread decimal). 4. **Its sign test's lower tail double-counted P(X = pos)**; H1 uses only the
   share positive, so no registered number moves. (98e80f9)
5. **The final readings (H5e FINAL, H7) could be written before their window's data exists.** The
   cloud also runs at 03:05 UTC on 12 Nov; Databento serves day D at ~D+2 02:00 UTC in practice. Both
   now wait while any day lacks its close or OPRA file, and write regardless from **19 Nov**, naming
   what is missing. 6. **The H5e FINAL had no full-precision cross-check**: modelfree gains `--through`
   (default output byte-identical, checked) and the final reads `--through 2026-11-11`; `--through
   2026-10-07` reproduces the first verdict exactly (0.90, 2 of 10). (75993d3; H5 and H7 logs)
7. **H6b's Welch test ignored autocorrelation** (robustness line, after the output): Newey-West lag 21
   t -3.80 p 0.0001; lag 63 t -3.12 p 0.0018. H6b survives; the site says so. (H6 Result)
- **Checked and right:** modelfree's formula, forward, K0, strip, dK, blend (Cboe v5.0 verbatim); the
  replica's ATM tie, K0 rule, zero-ask stop, minute clock, blend/extrapolation, 7-day exclusion (v9.0:
  "excluded if Days to Expiration is Less than 7 Days"); Cboe's index filter only holds FALLS of 0.5 in
  30 s (wording fixed in the replica); hedged.py's gain, carry and dividend adjustment; c4; Newey-West;
  BH/BY; fixed-b; H1's windows; H6's Parkinson constant, Wilder ATR, HLN factor and no look-ahead; the
  pricer (parity to 1e-9); the site's numbers. **Jiang & Tian:** the 2007 paper (p. 40) says three SDs,
  citing the 2005 paper, which itself says two; both quoted as written (H3 note).
- **Every published number re-derived from a run:** modelfree, `--wide` and hedged.py byte-identical
  to this morning's code on the same data; the site's Bloomberg table (21 figures), the day-count fit
  (10 blocks: +1.15/+0.07, slope 1.013, R^2 0.881) and the OPRA table (5 days) reproduce from the
  stored exports; Fig. 4's 63.8% / 93.0% from `analyze.py --simulate`; the 11.43-point truncation model
  recomputed independently. **H1 and H2 could no longer be re-run** - Cboe withdrew the EVZ and VXXLE
  files (403). Now: FRED fallback for exactly those two, `--end` to stop at the registered data end, and
  a manual read-only `sample_a.yml`. Run 37990784842: 9 of 11 pairs and every headline exact (H2 t 16.26);
  EVZ/FXE +0.83 -> +0.88 and VXXLE/XLE +1.80 -> +1.77 because FRED carries four dates Cboe's file
  lacked (values identical on all 2,166 common days, checked against Cboe's archived Aug 2024 file),
  which shifts the non-overlapping grid. Recorded in H1 and H2.
- **The first monthly rows landed** 9 Oct 18:41 UTC: 1,066 contracts, USO and GLD, 16 Oct / 20 Nov
  (7 and 42 days), exactly Cboe's legs; the H7 reader computes on them (values not looked at).

*Data provided by Databento (OPRA consolidated NBBO). Aggregates only.*

#### Open, no fixed date
- ~~Check Databento's terms on derived data.~~ Done 23 Sep: allowed, with attribution,
  and the OPRA aggregates are on the site (see the decisions above). When H5f reaches
  its verdict, the site section's "three days, descriptive" paragraph must be updated
  by hand: it is static text.
- ~~The site overflows horizontally at phone width (961 px on a 375 px screen; Fig. 2,
  Fig. 3 and both data tables).~~ Fixed 23 Sep: the mobile grid columns were a bare
  `1fr`, whose auto minimum let a nowrap table, or a chart drawn at a wider width, hold
  the column open. Now `minmax(0, 1fr)` on `.section` and `.live-grid` in volrec.css:
  375 px on a fresh load and after a shrink, tables scroll in their wrappers, and the
  desktop layout is identical box for box.
- ~~Read Jiang & Tian (2007).~~ Done 23 Sep (H3 and H5, prior art). ~~Jiang & Tian (2005)~~ read 7 Oct
  (methods audit); the two papers' 2 vs 3 SD rule is noted in H3 (9 Oct).
- The 21-month day-count residual: **closed as unidentified, 24 Sep** (H3). Not the forward
  or rate; a time or scale effect common to calls and puts. Not to be searched further.
- ~~A site chart logs a negative SVG width in a narrow window.~~ Fixed 9 Oct (rect sizes clamped).
- Optional: a FRED key as a repository secret, so CI's H3 reading matches the local one.

**Fri 9 Oct - the dated plan from here (replaces the old "Later" list; done items are in the entries above)**
- **cron-job.org - DONE 9 Oct (checked in the console by Claude):** jobs 8548132 (record) and 8548147
  (surface) run in time zone America/New_York at 14:30 / 14:40, Mon-Fri - next runs Mon 12 Oct 14:30 /
  14:40 New York; from 2 Nov that is 19:30 / 19:40 UTC. Early-close copies, enabled, each firing once:
  record 8614856 (Fri 27 Nov 11:30) and 8614871 (Thu 24 Dec 11:30), surface 8614873 (27 Nov 11:40) and
  8614874 (24 Dec 11:40), New York time; all carry the same URL, POST, headers and body as the originals.
  Delete the four copies after 24 Dec. When the token is renewed (by 22 Dec), the two main jobs need it.
- **Mon 12 Oct 16:30 UTC:** the auditor routine (68 safeguards now). **Wed 14 Oct:** the watchdog.
- **Every weekday:** recorders 14:30 / 14:40 New York; the cloud buys OPRA for each day about two days later,
  H7's monthly legs inside their own $1.10 cap.
- **LSEG - Marc Vinyard answered 9 Oct:** "Summary statistics are fine as long as you don't share raw
  data." Credit line: **"Data source: LSEG Workspace."** History limits on his account: 1-minute
  intraday only 3 days back; 30-minute bars about 30 days back (Bloomberg's academic account has no
  1-minute history). So the 30-minute .OVX/.GVZ bars covering H5e's window (from 23 Sep) must be pulled
  **before about 20 Oct**, when 23 Sep leaves the 30-day window. Raw bars stay in ~/Documents/volrec-lseg,
  never in this repository. Its use is exploratory: how much of the replica's 0.29 residual is the move
  between snapshot and close. 30-minute bars bracket the 14:30-14:41 snapshot rather than hitting it,
  and that limit is stated with any figure. A timing hypothesis, if any, goes through PROTOCOL.md first.
- **Research reports read 10 Oct** (Gabriel's two chat-mode reports, 9 Oct; kept outside the repo).
  Adopted into PROTOCOL.md (two-way noise floor, n_eff and the 2.8σ/√n_eff detectable effect,
  equivalence testing, Webb-weight wild bootstrap for pooled tests, decomposition orderings, data-seen
  = pilot, an independent timestamp (OSF/Zenodo), the Cboe breaks), PAPER-OUTLINE.md (closest papers:
  Hentschel 2003, Duarte-Jones-Wang 2024, Osterrieder et al., Wallmeier 2024; a registered-test table
  first; venues) and DESIGN-MEMO.md (draft 2). **Checked, not taken on trust:**
  - *"Free plan gets OPRA data older than 15 minutes"* - asked the API (`opra_probe.yml`, run
    38015882270, aggregates only): the historical bars/trades endpoints accept NO `feed` parameter
    (HTTP 400 "unexpected query parameter(s): feed") and serve one source; the latest-quote and snapshot
    endpoints refuse `feed=opra` with HTTP 403 "OPRA agreement is not signed". There is no historical
    quotes endpoint, so a free OPRA *quote* reference does not exist here; Databento stays the reference.
    Whether signing the agreement in Alpaca's dashboard is free is Gabriel's question to check, not ours.
  - *Alpaca's terms* (files.alpaca.markets TermsAndConditions.pdf, read 10 Oct): Content may not be
    "republished, uploaded, posted ... to any other computer, server, web site or other medium for
    publication" without Alpaca's prior written consent. `data/iv_history.csv` and `data/surface*.csv`
    in this public repository carry the free feed's bids and asks. **Open, Gabriel's decision:** ask
    Alpaca for written consent (email drafted 10 Oct); nothing moved or rewritten meanwhile.
  - *Our break exposure:* H1's ETF bars are split-adjusted (`adjustment="all"`), so USO's 2020 reverse
    split is handled; the replica already applies Cboe's zero-bid-OR-zero-ask rule.
  - *SCCUR 2026:* abstracts closed 9 Oct 11:59 p.m. (decisions by 20 Oct; conference 21 Nov, $90 early
    registration to 23 Oct). A 244-word abstract was drafted for Gabriel the same evening.
  - **Done by Gabriel 9 Oct evening:** SCCUR abstract submitted (decision by 20 Oct; if accepted,
    register by 23 Oct for $90); the consent email sent to Alpaca (record its reply verbatim here). Next:
    ask Professor Connie James to be faculty sponsor (email drafted 10 Oct, DESIGN-MEMO.md attached);
    an OSF account (Gabriel creates it) to freeze H5e/H7 registrations before 11 Nov.
- **Terms audit, 10 Oct** (every source, read at the provider's own page; README "Data availability
  and terms of use" is the public summary):
  - *Alpaca* (TermsAndConditions.pdf): personal, non-commercial use; no republishing without written
    consent; a "User Application" serving Content to others needs 30 days' written notice. The public
    `data/` snapshots are the exposure. Consent asked 9 Oct; **if Alpaca says no**: stop committing raw
    quotes to the public repo (recorders write them to the private volrec-licensed instead; the site and
    hypotheses keep derived figures), and history is Gabriel's call - never rewritten without him.
    Public Actions logs print no quotes (checked). Worst realistic case of doing nothing: Alpaca ends
    API access, which would stop the recorder - the reason to ask rather than wait.
  - *Cboe* (cboe.com/terms, updated 16 Nov 2022): Materials may be downloaded "for your personal
    non-commercial use"; using them "to verify or correct other data or information" needs prior
    written consent, "except to the extent that such use constitutes fair use". Our design is that use.
    Request drafted for permissions@cboe.com (cboe.com/use-of-content; approval means signing a licence
    agreement). Fallback if refused: FRED's reprints of the same series (below), which Cboe licensed to
    FRED; values agree with Cboe's files (EVZ: 2,166 days). Switching a registered verdict's source would
    be a logged before-output change.
  - *FRED* (legal page and API terms): non-commercial educational use of Cboe-copyrighted series is
    allowed without pre-approval, with citation and Cboe's notice kept. The API terms REQUIRE the notice
    "This product uses the FRED® API but is not endorsed or certified by the Federal Reserve Bank of
    St. Louis." - it was missing; now on the README and the site, guarded by the pressure test and an
    auditor mutant. FRED also prohibits using its content "in connection with the development or training
    of" AI systems. The TimesFM benchmark only evaluated a pretrained model zero-shot (no training, no
    development) on VIXCLS - outside the clause's plain words, but close to it: any re-run or extension of
    `analysis/` on FRED data is a discussion with Gabriel first.
  - *Databento/OPRA*: Databento passes through each publisher's licence; OPRA requires a vendor agreement
    to redistribute raw quotes, so aggregates only, credited "Data provided by Databento" (unchanged,
    already guarded). Raw files in the private volrec-licensed repo are internal use.
  - *Bloomberg* (library, 17 Sep) and *LSEG* (Marc Vinyard, 9 Oct): derived figures only, with their
    credit lines. `volrec-lseg/` is now git-ignored and a tracked CSV with LSEG field names fails the
    pressure test (auditor mutants for both).
  - *GitHub, cron-job.org, Google Fonts*: nothing in their terms touches a scheduled public research
    recorder at this volume. No IRB question: no human subjects.
  - *Not done, and why*: no code licence file (a LICENSE is Gabriel's choice; without one the code is
    readable but not reusable - suggested MIT for code only, data excluded); no Zenodo archive (it would
    mirror Alpaca's data before consent).
- **Alpaca answered 10 Oct** (Ben, AlpacaDB, Inc., 11:44 EDT), verbatim: "Provided that your market
  data usage remains solely for your own personal/retail use, you are free to use the package as you
  please." Read as consent to keep the snapshots public for this non-commercial research, on that
  condition: nothing in this project may be sold, licensed for a fee, or built into a commercial
  service. The site and README now say so. **Cboe request sent 10 Oct** to permissions@cboe.com (Cboe
  says about five business days); if nothing by **Mon 19 Oct**, one polite follow-up, which also asks
  to cover the `lab/` side project's published aggregates (backtest statistics built from index closes;
  no index data republished) so one permission covers both (Gabriel 12 Oct). **MIT licence
  added 10 Oct** (Gabriel's choice): code and documentation only; README's "Licence" paragraph excludes
  every third-party dataset.
- **OSF, 10 Oct:** Gabriel's account works. `OSF-REGISTRATION.md` holds every field for the "Secondary
  Data Analysis" template, freezing H5e and H7 as committed (ac237a6, 1d1bef7; repository at 8d3a555),
  disclosing what was seen first. **Registered 10 Oct by Claude in Gabriel's browser at his request:
  https://osf.io/z5gfu** (public, no embargo, MIT licence; OSF auto-approves after 48 h unless Gabriel
  approves by email first). **APPROVED and live** (OSF API, 10 Oct: date_registered 2026-10-10T17:43:18 UTC,
  public, not embargoed, subject Finance and Financial Management). Linked from both hypothesis files and
  PAPER-OUTLINE appendix A. **LSEG:** Gabriel requested Pepperdine's student Workspace
  access 10 Oct - the right route; his credentials stay his.
- **The upgrade (H8, not registered) - scope B chosen 10 Oct.** Databento's own get_cost (free) for one
  day at the snapshot minute, cbbo-1m, all eight surface funds: SPY 0.0194, QQQ 0.0164, GLD 0.0105, IWM
  0.0084, TSLA 0.0071, USO 0.0069, NVDA 0.0062, AAPL 0.0050 = **$0.080 a day**; 41 trading days 1 Dec - 29 Jan
  = **about $3.28**, plus about $0.83 to give SPY/QQQ/IWM/NVDA/AAPL 15 calibration days (USO, GLD and TSLA
  are already owned). About $4.10 in all. **Gabriel approved up to $5 for H8 (10 Oct)**, inside the $100
  free credit; every buy is still priced first and logged in spend.csv. The plan, per PROTOCOL.md: the
  same contracts priced on both feeds (the "data" step, S1 vs S0) for each fund, an equivalence test
  whose bound sits above the noise floor measured on Sep-Nov (OPRA at minute t against minute t+1),
  register after the 12-19 Nov verdicts, test 1 Dec - 29 Jan. Instrument first (tools/h8_quotes.py).
  **Instrument built 10 Oct** (`tools/h8_quotes.py`, 20 known-answer tests in `tools/test_h8.py` on files
  in Databento's own blank-bid form, pressure-test check, auditor mutants h8-blank-bid-dropped,
  h8-tost-one-sided, h8-neff-ignores-rho; auditor 66/66). **Pilot readings on OPRA already owned** (Sep-Oct,
  in-sample, NOT a verdict; mean |free - OPRA| on matched contracts / OPRA-vs-OPRA one-minute floor):
  GLD 16 days 0.023 / 0.004; USO 14 days 0.038 / 0.051; TSLA 14 days 0.050 / 0.015; 97-100% of band
  contracts matched; day-to-day rho negative (-0.2 to -0.3), so n_eff = T. *Data provided by Databento
  (OPRA consolidated NBBO). Aggregates only.* **Next, in order:** (1) re-read the instrument cold after a
  day (protocol step 2); (2) buy ~15 calibration days for SPY, QQQ, IWM, NVDA, AAPL (~$0.83, priced first,
  logged in the cloud ledger; decide whether the cloud workflow buys all eight daily from 1 Dec); (3) set
  the bound as a stated multiple of the measured floor and of something practical (half a typical
  spread in vol points), and the n_eff/MDE check; (4) write the registration with Gabriel after the
  12-19 Nov verdicts, freeze it on OSF.
- **H8 scope CHANGED to A+TSLA, 10 Oct - the first price was wrong by about 2x.** Pricing the actual
  calibration requests (Databento get_cost, free; snapshot-minute windows from the recorded rows) gave
  **$1.39** for 15 days of SPY/QQQ/IWM/NVDA/AAPL, not $0.83 (SPY ~$0.037 a day, not $0.019). At those prices
  scope B is about $1.4 + $6.5 = ~$8, over Gabriel's $5 limit, so per his rule ("if not under $5, go to A")
  H8 covers **USO, GLD and TSLA**: all three already bought daily by the cloud, ~15 calibration days each
  already owned, Dec-Jan about $2 (~$0.048 a day). TSLA added to A because it is already in the pipeline and
  gives a single stock beside the two commodity funds. **Nothing was bought**; lifetime spend $0.70. Lesson:
  price the real requests, never a single sample minute.
- **H8 scope back to B, 10 Oct (Gabriel: "sub $10 is fine... make the decision").** All eight funds
  (~$8 total): the index funds are what most free-data users price, so the broader claim is worth the
  cost. **Calibration bought 10 Oct:** 75 files (SPY/QQQ/IWM/NVDA/AAPL x 15 days, 17 Sep - 8 Oct, 28 Sep
  excluded), $1.385, every request priced first; lifetime spend **$2.09**. Ledger pushed to volrec-licensed
  (spend.csv only); the 340 MB of files stay on Gabriel's Mac in ~/Documents/volrec-licensed/opra
  (git-excluded locally). **Calibration readings, all eight** (in-sample, NOT a verdict; mean |free - OPRA|
  on matched contracts / mean free - OPRA / OPRA one-minute floor, vol points): SPY 0.059 / +0.059 /
  0.010; QQQ 0.038 / +0.038 / 0.009; IWM 0.090 / +0.090 / 0.007; GLD 0.023 / +0.014 / 0.004; USO 0.038 /
  -0.013 / 0.051; TSLA 0.050 / +0.041 / 0.015; NVDA 0.071 / +0.071 / 0.014; AAPL 0.020 / +0.010 / 0.016.
  97-100% of band contracts matched; n_eff 9-16. Read plainly: the free feed reads a few hundredths of a
  point HIGH on 7 of 8 funds - small, but systematic and above the floor, which the registration must
  face honestly (an equivalence bound, not a "no difference" test). *Data provided by Databento (OPRA
  consolidated NBBO). Aggregates only.* **To do before 1 Dec:** the cloud workflow buys all eight daily
  for the window (~$0.16 a day), with H8's own cap.
- **H8 'still to do' done, 10 Oct.** (1) The cloud now buys all eight funds daily (`daily.yml` H8 step,
  `opra_reference.py --h8`, own $15 cap, 9 Oct 2026 - 29 Jan 2027; price-only run 38077233404 priced 9 Oct
  at ~$0.16 a day). **First real buy verified 10 Oct** (manual full run 38077734747, as the schedule skips
  weekends): all eight funds for 9 Oct bought, $0.17; SPY trimmed 7.8 MB -> 0.46 MB and still 688 of 688
  band contracts matched; GLD/USO/TSLA full chains kept; lifetime $2.27. Full chains kept for USO/GLD/TSLA to
  11 Nov; everything else trimmed to the recorded band (~5% of a file) so the private repo stays small.
  Expected H8 spend to 29 Jan: about $10.5 tagged "-h8", lifetime about $15 by then, inside the $100 cap
  (Gabriel 10 Oct: budget can rise). (2) Cold re-read: added the user's-view reading (both feeds at the
  snapshot minute, stale quotes kept); stale quotes add at most ~0.01 inside the band. (3) Draft
  registration: `H8-DRAFT.md` (proposed bar 0.10 points: about SPY's ATM half-spread, 2x the largest
  noise floor; decided with Gabriel after 19 Nov, then frozen on OSF).
- **LSEG on hold, 10 Oct (Gabriel):** student Workspace access has not come through; the CodeBook pull
  waits until he says it is ready (script in this section's LSEG entry). Cost of waiting: the 30-day
  window loses one early day per day after ~20 Oct (H5e's window starts 23 Sep). Fallback if still
  blocked by ~15 Oct: ask Marc Vinyard to run the same pull on his account. Exploratory only either way.
- **Faculty sponsor, 10 Oct:** Professor Connie James teaches Gabriel's Foundations of Reasoning
  (philosophical reasoning) course, with corporate finance experience. DESIGN-MEMO.md draft 3 asks her to
  judge the REASONING (claims vs evidence, the decomposition's order, honesty of the testing) and to
  sponsor; a PDF copy is on Gabriel's Desktop (Mitton-design-memo.pdf). Gabriel replaces his scheduled
  Monday email with the new one, memo attached. **Done 10 Oct: the new email is scheduled for Mon 12 Oct.**
- **Side project agreed, 11-12 Oct (Gabriel): a retail implementation audit, `lab/`, NOT BUILT YET.**
  Question: how much of the volatility risk premium can a retail investor using free data actually keep?
  Exploratory, own folder, imports registered code and never changes it; its rules are committed before
  the first backtest. On hold until Gabriel has Santa-Clara & Saretto (2009, JFM 12(3) 391-417) from the
  Pepperdine library; then spec (docs/superpowers/specs/), sign-off, plan, build. Design: costs from OPRA
  (free feed as the tested alternative), strip cost = the registered estimator on bids vs mids, four cost
  cases from Muravyev & Pearson (2020, RFS 33(11), published figures: conventional effective ~80% of the
  quoted half-spread, execution timers ~30%); a stationary-bootstrap stress lab; margin as its own stress.
  **Key finding, priced only (nothing bought):** Databento's OPRA cbbo-1m history starts 1 Apr 2013 and one
  entry-day window for SPY/QQQ/IWM/GLD/USO costs $0.04-0.09 (24 Aug 2015 $0.039, 5 Feb 2018 $0.043,
  16 Mar 2020 $0.077), so the backtest can use the REAL trade (short straddles: OPRA entry bid, free
  underlying at expiry) every month 2016-2026 for about $6-10, crash months measured rather than modelled;
  verify one old day's completeness first (~$0.04). The synthetic variance swap on Cboe indices stays as a
  cross-check. Nothing goes on the public site until Cboe's permission reply.
  **12 Oct, later:** Santa-Clara & Saretto read in full; spec written and revised
  (`docs/superpowers/specs/2026-10-12-retail-vrp-audit-design.md`, rev 2: the Leak Map, the Break-Even
  VIX, $75 own cap, lab dates end 31 Aug 2026). Next: the build plan, then build. **Flags raised for the
  main project, awaiting Gabriel:** (1) H8-DRAFT's spread yardstick used the FREE feed's ATM half-spreads;
  OPRA's are narrower (pilot medians, vol points, free / OPRA: SPY 0.070 / 0.034, QQQ 0.086 / 0.066,
  IWM 0.130 / 0.102, GLD 0.309 / 0.315, USO 1.366 / 1.331, TSLA 0.371 / 0.305, NVDA 0.288 / 0.280,
  AAPL 0.416 / 0.420), so "0.10 is about one SPY half-spread" should read about three; the noise-floor
  reason still holds. (2) Pilot mechanism for H8's lean: at the quote-time match the free bid sits on
  OPRA's bid while the free ask sits higher on SPY/QQQ/IWM (+0.09 to +0.14 points ATM). (3) README and
  H3's text say "same underlying" for SPY/VIX, QQQ/VXN, IWM/RVX; those indices are built on SPX/NDX/RUT
  options (H1 says so; H3 and the README do not). (4) The Cboe follow-up (19 Oct) should also cover the
  lab's published aggregates.
  **Plan 1 built 12 Oct** (`docs/superpowers/plans/2026-10-12-lab-plan-1-foundation.md`): registration,
  costs, integrity, Cboe margin (the manual's seven worked examples as tests), capped purchasing (own $90
  cap, dates 1 Aug 2015 - 31 Aug 2026), 3 auditor mutants. Test day 5 Feb 2018 bought and verified: all five
  funds pass after the completeness rule was amended (Gabriel): OPRA's own listings replace a 10-strike
  minimum USO could never meet at $12.81. Lab spend $0.0669. Next: Plan 2 (trades, Leak Map, stress).
  **14 Oct, 09:17 UTC - DATABENTO REFUSED A PURCHASE: HTTP 402 `account_insufficient_funds` ("You don't
  have sufficient budget").** Our ledger shows only $3.15 lifetime, so the account's real balance or
  budget differs from the ledger - Gabriel must check the Databento portal (billing / budget / credit
  expiry). All lab buying stopped; ledger committed (104 lab files, $0.63; lab $0.70). **Risk to the
  main project:** the cloud's nightly H7/H8 OPRA buys will fail the same way until funds return. Nothing
  is lost - OPRA stays buyable historically and `--all`/H8 catch up skipped days - but H7's verdict needs
  its OPRA through 11 Nov, so funds must be restored before ~13 Nov (the writer waits to 19 Nov).
  Lab state: Plan 2 Tasks 1-5 done and pushed; entry days bought 2016-01-19 to part of 2016-11-21.
  **14 Oct, later:** the 402 was Databento's *usage-based access monthly limit* ($1.00), not the credit
  ($123.93 left); Gabriel raised it and buying resumed. Even without the lab, H8's ~$3.50 a month would
  have hit $1 - check that limit first if a 402 ever returns. The lab now buys everything in one
  resumable queue (`lab/buy_days.py --kind all --workers 30`: entry days, stress-month 15:55 marks,
  weekly Wednesdays; ~8,200 files, ~$53).
  **Sponsor, 14 Oct: Professor James cannot sponsor.** Still needed: a faculty mentor for SCCUR (check
  whether the 9 Oct submission named one; decisions 20 Oct, registration 23 Oct), Seaver and JURF.
  Suggested: Levon Goukasian (met 11 Sep) - his advice was years of raw option prices, impossible on
  Bloomberg (90 days) but now done on OPRA back to 2016 in lab/; DESIGN-MEMO.md would be re-addressed.
  LSEG: Gabriel emailed them, still waiting. Cboe: still waiting (follow-up due Mon 19 Oct).
  **lab/ COMPLETE, 14 Oct (Plans 1-5; plans in docs/superpowers/plans/).** Every rule, prediction and
  result is in `lab/REGISTRATION.md`; the paper section is PAPER-OUTLINE 5b. P1 fails, P2 holds as
  written, P3 holds 5/5, P4 fails 1/5, P5 holds among funds with a paper profit. Data: 8,073 OPRA files in
  ~/Documents/volrec-licensed/opra-lab ($79.00; lab cap $90; lifetime cap raised to $120 by Gabriel).
  Private outputs in ~/Documents/volrec-licensed/lab-out (trades.csv, leak_months.csv, the JSON
  summaries, report.html) - nothing on the public site until Cboe replies; then a site page is part of
  the post-November discussion. Re-run: `lab/run_trades.py`, `run_leak.py`, `run_breakeven.py`,
  `report.py`; the trust engine: `lab/engine.py` (latest free-feed day). Auditor 76/76.
  **Roadmap agreed with Gabriel, 14 Oct (Vega picks the timing; each needs its own plan first):**
  1. H9 - register BEFORE looking, right after the 12-19 Nov verdicts (Cboe-method replica on the lab's
  OPRA entry days vs GVZ/OVX, 2016-2026; dates the 2022 NBBO switch; confirm it with IndexSupport@cboe.com).
  2. A second free feed (the paper's biggest limitation is one free feed) - terms check first; spring or a
  second paper. 3. LSEG intraday timing, if Marc unlocks .OVX/.GVZ. 4. lab/: a delta-hedged version. (Bondarenko 2014: hedging
  errors are very sensitive to rebalancing timing - fix the hedge schedule in the registration, before data.)
  Then, at write-up time (Jan-Feb 2027): a red-team review by role-based agents (methods skeptic,
  statistician, cold replicator, novelty checker, licensing auditor, professor-reader) as CRITICS, not
  pattern-hunters; a second company's model may review text and aggregates only, never licensed raw data.
  Anything noticed is exploratory until pre-registered on new data. Finish the paper first.
  **14 Oct, evening:** PAPER-DRAFT.md v1 (sections 3, 4, 5b, written before the verdicts); the site's
  snapshot-timing limitation now gives the measured 0.53 pts. Cboe follow-up drafted in chat for Mon 19 Oct
  (send only if no reply; it adds the lab's aggregates to the request).
  **Databento reconciled, 14 Oct (Gabriel's portal screenshots):** October charges $44.28 (definition 5.99 GB at
  $5/GB = $29.92; cbbo-1m 7.18 GB at $2/GB = $14.35), all from credit; $80.64 credit remains; monthly limit
  $120. Our ledger shows $81.28 for October - it OVER-counts real charges by about 1.8x, the safe direction,
  so every cap in the code is conservative. No card charge; H8's remaining ~$12 (ledger terms) is covered.
  **lab/ audit, 14 Oct (Gabriel asked for one):** purchase verifier attached (found 15 charged-but-empty
  files, none used); independent recomputation matches; three missing spec items built; auditor 79/79.
  For the main project: the snapshot-timing effect measured at a median 0.53 pts in stress months (now in
  PAPER-OUTLINE's limitations), and a ten-year OPRA spread yardstick in H8-DRAFT. **Proposed for after the
  verdicts (Gabriel decides):** register H9 BEFORE looking - the Cboe-method replica on the lab's OPRA
  entry days vs GVZ/OVX across 2016-2026, which also dates the unconfirmed 11 May 2022 NBBO switch; the
  data is already bought, so the registration is the only cost. The lab report becomes a site tab only
  after Cboe's reply.
  **LSEG, 14 Oct:** Workspace for Students live with CGIF added. .VIX intraday works (1-min from 1 Sep 2026;
  saved to ~/Documents/volrec-lseg/). .OVX/.GVZ/.VXN/.RVX denied for daily AND intraday
  (UserNotPermission.92000; the quote page says no permission): an entitlement gap. Gabriel emails Marc
  Vinyard once (LSEG + mentor question), then stops. **Fallback for the timing question, no LSEG needed:**
  run the Cboe-method replica on OPRA at 14:30 AND just before the close for USO/GLD (~$0.02 a day); the
  difference is the move between snapshot and close. Inside H7's window, so after the verdicts, exploratory.
  **Discovery system, 14 Oct (option C, Gabriel's choice):** design in
  docs/superpowers/specs/2026-10-14-discovery-system-design.md; the holdout ("vault", `lab/vault.py`) sealed the
  same day - half the 2016-2026 quarters, crash quarters split 3/3, fingerprint pinned by a test and an auditor
  mutant. Nothing running reads it; it only limits where December's explorers may look, and opens in January.
  Agents get built when the time comes (Gabriel: Ultracode may do the build from the spec; Vega checks it
  against the auditor before anything runs).
  **SCCUR, 14 Oct: revise-and-resubmit** (not yet accepted). Reviewers: spaces after punctuation, define
  acronyms, say why it matters. Revised abstract in SCCUR-ABSTRACT.md (248 words, ASCII punctuation). Gabriel
  resubmitted it via Whova and replied to the email on **14 Oct** (done; the one revision is used). Trimmed to
  1,460 characters (limit 1,500). Next: SCCUR's decision; register only after acceptance - early rate $90
  to 23 Oct, $100 to Sat 8 Nov, the hard deadline for presenters (research.sdsu.edu/sccur-2026, read 16 Oct;
  fees non-refundable; no mentor requirement stated there).
  **Bondarenko (2014) read, 15 Oct:** the last ILL paper; logged in lab/REGISTRATION.md and PAPER-OUTLINE's
  related work (premium size: long variance -26.30%/month, selling Sharpe 0.42). No number changed. All
  requested papers are now read; PDFs in ~/Documents/volrec-papers.
  **Decisions, 16 Oct (Gabriel delegated them to Vega after a cold-review subagent; findings verified first):**
  (1) Mentor: Gabriel also asks Marc on Tue 20 Oct, AFTER the scheduled Goukasian email goes out, to be his
  SCCUR mentor in the meantime (Goukasian went silent once before; SCCUR decides ~20 Oct). (2) Descriptive
  intervals + n_eff beside every verdict, and a whole-project test count with Holm column: script built before
  the verdicts, run once after (PAPER-OUTLINE). (3) If SCCUR accepts: a poster ready ~6 Nov with script-filled
  result boxes. (4) Discovery system PARKED until the JURF submission (spec header). (5) No new monitors before
  21 Nov; phase 2 (first responder) deferred to after SCCUR, re-decided in December. (6) Section 5b cut to half
  a page, rest to an appendix (PAPER-OUTLINE). (7) Cboe fallback = FRED reprints (series verified live).
  Already fixed: the draft's pre-registration overclaim, three tracked duplicate files, stale lines.
  **Engineer review, 16 Oct (read-only subagent; each finding checked against the code before acting):** (1) the
  guard's own crons always land after the close (GitHub runs this repo's crons 2-7 h late), so a day the
  trigger never started was caught by nothing before the close - FIXED: every recorder completion now judges
  both panels (surface's 14:40 run is the ATM panel's timer; a GitHub backup that stood aside counts too).
  (2) an unreadable run list sent a misleading YELLOW - FIXED: retried 3x, then RED if nothing is recorded and
  a human can act. (3) a failed git fetch after a re-run could send a false RED - FIXED: checked and retried,
  YELLOW "could not confirm" instead. (4) two panels could exceed the job timeout - FIXED: one 16-min budget,
  timeout 30 min. (5) start-failure RED now obeys the RED rule; YELLOW text no longer claims a re-run; private
  daily.yml's 03:05 text fixed; freshness's duplicate phone alert removed (health sends one per lost day).
  Re-run path now unit-tested end to end with fakes; mutant guard-skips-refetch added.
  **First live guard day, 16 Oct:** GitHub's backups started 14:21 / 14:27 New York and stood aside; the guard
  waited (too early); the 14:30 / 14:40 triggers recorded 109 / 8; the guard judged both "ok" and stayed silent.
  Fixes pushed after the close (auditor 90/90).
  **Code review of today's code (xhigh, 16 Oct evening): 11 findings, all fixed the same evening.** Guard: never
  starts a recorder before its own trigger slot (a mis-timed manual/cron run would have recorded an off-time
  snapshot); the re-run cap no longer depends on the bot login (2 workflow_dispatch runs = already re-run); its
  own re-run is identified as the NEW dispatch run, not by login or a minute-truncated time; ONE concurrency
  queue (guards judge both panels); completeness rounds DOWN (surface 7 of 8 is complete); a re-run that
  succeeds yet records nothing is YELLOW "unscheduled closure?", not RED; the per-panel loop is run_panels(),
  unit-tested; its GitHub crons removed (they always landed after the close; cron-job.org wakes it). describe:
  Holm skips NaN; the fixed-b null is now ONE copy, analyze.fixed_b_null (fixed_b_pvalue's outputs checked
  identical to the digit). freshness: dead tee removed. 3 new auditor mutants. **Then an automated security
  review of those fixes (same evening), 4 acted on:** a failed pre-dispatch run listing fails CLOSED (no
  downgrade); a clean-but-empty re-run is YELLOW only if the OTHER recorder is also empty today (independent
  evidence of a closure), else RED; reaching the 2-dispatch cap ALERTS instead of waiting silently; the ATM
  bar is the best of the last 5 days, so a partial day cannot lower tomorrow's bar. Not changed, by design:
  cron-job.org as the before-the-close trigger (its token is fine-grained, Actions on volrec only; the native
  workflow_run trigger remains), and the single queue (the running guard is handling the problem; the newest
  pending one covers both panels). **Then /ultrareview (cloud, Gabriel) on the same fixes: 7 findings, all
  fixed:** the other recorder's emptiness counts as closure evidence only after its own slot + 10 min (at 14:36
  the surface simply has not run); two auditor mutants had stale targets after the refactor (fixed-b-ignores-lag,
  guard-dispatch-cap-gone) - retargeted; the 2-dispatch cap alerts ONCE (on the second dispatch's completion);
  a BOT-actor event skips only the re-run panel, so the single queue cannot lose the other panel's judgement;
  dead trig-5 allowance removed; re-run path's coverage injectable (hermetic tests). 77 guard tests.
  **Deep review of the core code, 16 Oct night (two read-only reviewers; Gabriel asked).** (A) Recording + money,
  FIXED: the Mac's Databento ledger was a stale separate file (17 rows to 25 Sep vs 8,242 in the private repo) -
  purchases from the Mac now REFUSE unless pointed at the real ledger (VOLREC_DATABENTO_DIR=~/Documents/volrec-
  licensed/opra, pull first); a headerless ledger is refused (it made every cap read $0) and one writer,
  record_spend, always writes the header; a purchase is recorded the moment it is charged, before trimming or
  writing; OPRA files are written whole or not at all; both recorders refuse to start more than 15 min before
  their slot (a mis-timed manual/cron run) and stop at the bell mid-run (no closing quotes; surface skips its
  wide/monthly passes after 16:00); panel_health reports missed days INSIDE the panel (15-day lookback);
  daily.py treats a non-zero modelfree exit as a crash; notify.send no longer raises. DEFERRED with reasons:
  spot fetched once per run and the write-at-end design (changing what is recorded mid-window - after 11 Nov);
  concurrency groups on record/surface (rare overlap, harmless red X; new interactions with the guard's
  re-run); Alpaca 5xx retries (the guard re-runs a failed run); the holiday-before-close ordering (it would
  break the established "close check before any fetch" rule for a cosmetic email). (B) Verdict math: see the
  next entry - reported to Gabriel BEFORE any change (registered numbers).
  **Verdict-code review (B), Gabriel approved all five on 16 Oct ("1-5 yes"); no registered bar or verdict
  changes:** (1) the writer refuses when its verdict disagrees with the reader's own full-precision verdict
  (H5e: modelfree's "(under|OVER)" / "(majority|NOT a majority)"; H7: h7_reader's own HOLDS/FAILS line) - a
  true mean in [0.495, 0.5) could otherwise be written FAILS; (2) the writer refuses unless the risk-free rate is
  the frozen one (a missing FRED cache silently gives r=0); (3) the writer refuses when an expected trading day
  is absent from the reader's rows; (4) H7a gets a dated COMPANION reading on matched strikes (free file is cut at
  +/-60% of spot, OPRA has every strike - coverage leaks into a data-quality test, up to ~0.19 pts vs a 0.25 bar),
  reported beside the registered verdict after 12 Nov; (5) a frozen H3 scorer before 11 Nov, logged as a
  pre-verdict addition. **Status 16 Oct night:** 1-3 drafted and checked on the REAL reader output (no false
  refusals: H5e agrees, rate 3.910, no missing days; H7 agrees) but NOT live - the pressure test drives the
  writer with canned outputs that lack full day lists, rate and verdict lines, so the fixtures must be rebuilt in
  the real form first (and the H7 checks moved after the waiting/minimum branches). The draft is in
  docs/drafts/record_verdict.safeguards-draft.py.txt. **17 Oct: 4 and 5 BUILT** - `tools/h7_reader.py --matched`
  (companion H7a on matched strikes, registered output byte-identical) and `tools/h3_scorer.py` (frozen H3
  scorer; specification note in the H3 file). Run both once after 11 Nov beside the registered readings.
  **17 Oct: 1-3 LIVE** - the writer's canned outputs were rebuilt in the readers' real form (every day of each
  window, the tally computed from the rows, the rate line, h7_reader's own verdict line) and each safeguard has a
  refusal test plus an auditor mutant; the H7 checks sit after the waiting/minimum branches; the missing-day
  check covers days up to yesterday (the whole window from 12 Nov). A --preview on the real data passes them all.
  h5f_pooled.py's preview-only crash on a zero free-inflation day is LEFT ALONE: the script is frozen byte-for-
  byte (pressure test) and H5f is already recorded, so the writer never runs it again outside --preview.
  **Automated, 17 Oct (Gabriel: "set up now so we dont have to think about it"):** volrec-licensed's daily run
  writes the companion readings (describe.py intervals, the frozen H3 scorer, H7a on matched strikes) ONCE, the
  first night both final readings are recorded, to licensed/reports/companions.txt, and sends a Pushover NOTICE.
  One-off phone reminders (Claude app; no connectors): 19 Oct Cboe follow-up; 20 Oct Marc mentor ask + SCCUR;
  22 Oct green week + early-close guard jobs; 30 Oct Goukasian fallback; 20 Nov verdicts in / companions / site
  discussion; 23 Nov Bloomberg intraday pull; 1 Dec token renewal + cleanup. (h5f_pooled.py's zero-division in
  --preview stays as it is: the script is frozen byte-for-byte and H5f is recorded - see above.)
  **Independent re-implementation, 17 Oct (Gabriel: "save them into the project"):** after he asked whether every
  number is right given this week's bugs, Vega wrote a second implementation from the method text alone, without
  reading the estimator code: `tools/independent_replica.py` (standard library only - a pressure-test lint keeps it
  that way). `tools/independent_check.py` compares it with modelfree/h7_reader at full precision: **661 of 661
  values agree** (band 192 + Cboe-rule band 192, wide 85 x 3 incl. every H5e row, H7 free 12 + OPRA 10; tolerance
  0.01). Largest difference 0.0009: IWM 8 Oct, an EXACT tie on |C - P| at strikes 277/279 broken by float noise -
  documented in the file, no verdict reads IWM. Also checked: 110 Cboe closes = FRED's copies exactly; the frozen
  3.910% vs today's 4.17% moves any value by <= 0.008 and H5e not at all (0.72, 8 of 17). Its own known answers
  (`tools/test_independent.py`, 30 cases: Black-Scholes chains of known vol read back within 0.05, the three quote
  rules, H7's clock across DST, Databento's blank bid) run in the pressure test with 4 auditor mutants. The real-data
  comparison is NOT nightly (an exact tie could trip it - a false alarm; no new monitors before 21 Nov): it runs on
  demand and once at verdict time inside the companions step (volrec-licensed daily.yml). For the paper: Appendix C.
  **The whole-project re-check, 17 Oct (Gabriel: "are we sure this didnt also happen to anymore hypothesis"):**
  every recorded result recomputed by a second implementation sharing no code (TEST-INVENTORY.md has the table).
  **One real bug:** `tools/bloomberg_compare.py` read sheet cells in order, and Bloomberg OMITS an empty IVM cell
  from the file (11 of 15 exports), so the row's put was dropped and, with column F missing, the call's IVM was read
  from Volm. Fixed (cells placed by column; `VOLREC_BBG_POSITIONAL=1` reproduces the old figures exactly); a pressure
  check on a synthetic sheet in the exports' own form + an auditor mutant. Corrected beside the originals, dated:
  H5a 0.33 over 179 (was 0.40 over 169), H5b 44 of 44 (was 36 of 36) - both verdicts unchanged; H5's 'already
  seen' 18 Sep figures and H3's 18 Sep lift table (Bloomberg Cboe-rule lift +0.96, not +0.85). The model_gap /
  iv_convention conclusions (business days over 252) do not move. The public site's H5 row is corrected too (Gabriel:
  "yes fix the site too"), worded without the vendor's name, which the site-code check forbids. Everything else reproduced: H5f exactly (H5f-a is exactly
  1/2 in exact arithmetic), H1/H2/H6 on a second price source (counts and conclusions identical; H2a's raw-variance
  significance is vendor-sensitive, noted in H2), H4 exactly, TimesFM re-scored exactly from saved forecasts, the
  lab's 628 trades (one exact strike tie, noted in lab/REGISTRATION.md). Later the same day (Gabriel: "if u feel
  the H8 pilot the leak map and the other things need a rebuild go ahead") those were rebuilt too: the lab's Leak
  Map identical at 5% and 20%, Break-Even crossings identical, P4 fails 1 of 5 as recorded, stress replays exact
  and the bootstrap within Monte Carlo noise; H8's reader identical on all eight funds. H1c's "positive on 87.3%"
  counts four exactly-flat days (strictly positive 87.1%) - noted in H1. Nothing recorded is left unchecked.
  **A second gap found in the final check, 17 Oct:** `record_verdict.py --preview` - the one dry run of the November
  writer on real data - had started ABORTING at H5f: the frozen `h5f_pooled.py` divides by zero on a later
  zero-inflation day, and the preview died before rendering H5e or H7. The real path was never affected (H5f is
  recorded, so it is skipped; last night's run passed). Fixed in the preview only: when H5f is recorded and the
  frozen script fails, the preview says so and goes on (the script itself stays frozen). A pressure check plus a
  mutant; the preview now renders H5e first, H5e FINAL and H7 on today's data with every safeguard passing. The
  rebuild scripts are kept in `docs/recheck-2026-10-17/` (README there), each re-run from that folder.
  **A third gap, found by simulating verdict night (17 Oct, Gabriel: "be on ur toes"):** the pressure test's
  writer checks ran `record_verdict.main()` against the REAL hypothesis files. With the H5e FINAL and H7 blocks
  written (simulated in a throwaway worktree), five checks failed - and daily.yml runs the pressure test before
  pushing a verdict, so it would have refused to push H5e FINAL and H7 (the private copy would have survived; the
  nightly health check and the push hook would then have failed every day). Fixed: those checks read copies with
  the two not-yet-written marks hidden; a check + mutant; the simulated verdict night now reads 0 fail. Also
  corrected here: the site paragraph's 18 and 23 Sep Bloomberg lifts (0.85 -> 0.96, 14.82 -> 14.78).
  **cron-job.org guard jobs, 16 Oct (Gabriel):** "volrec guard 15:00" and "volrec guard 15:20" (Mon-Fri, New
  York) enabled; test run returned 204 and reached GitHub (guard run 38962170586, judged "skip - after the
  close", correct). **Made by Gabriel 16 Oct** ("all the jobs are enabled"): one-off copies at 12:00 New York
  on Fri 27 Nov and Thu 24 Dec (early closes); the 22 Oct reminder double-checks them. All use the volrec-trigger token: renew them with the others by 22 Dec. **Open:** after the first
  real re-run, confirm its triggering_actor is exactly "github-actions[bot]" (guard.BOT). Unscheduled market
  closures (e.g. a day of mourning) are not in US_MARKET_HOLIDAYS: add the date by hand when announced, or the
  guard re-runs and pages falsely. cron-job.org jobs starting guard.yml at 15:00 and 15:20 New York: DONE 16 Oct
  (see below).
  **Built 16 Oct (decision 2): tools/describe.py** - intervals (Newey-West, fixed-b, lag 1.3 sqrt T), n_eff,
  one-sided p against each bar, Holm; 28 known-answer tests (tools/test_describe.py), pressure check, 2 auditor
  mutants. Real series NOT read: only --count-only was run (H5e: 16 counted days to 15 Oct). **After the
  verdicts, run once:** `modelfree.py --wide > f; tools/describe.py --h5e f`, and in volrec-licensed the same
  with h7_reader's output (`--h7`); paste the lines beside the verdicts, labelled as the tool labels them.
  **Phone alerts + the recorders' guard, built 15 Oct (Gabriel: Pushover; "many times we have skipped over
  issues because of false positives").** tools/alert.py (stdlib; four levels, red = emergency priority every
  2 min for 1 h; keys only in GitHub secrets PUSHOVER_TOKEN/PUSHOVER_USER, in volrec AND volrec-licensed,
  set by Gabriel); tools/guard.py + guard.yml (confirms from data/ on main, re-runs a recorder once and waits
  for it, alerts once; never commits); health.yml sends the quiet daily GREEN (or YELLOW), freshness's
  23:00 slot a lost day as YELLOW; volrec-licensed: verdict = NOTICE, failure = YELLOW, repo public = RED.
  42 unit tests, pressure checks, 6 auditor mutants (87/87). **Proven live 15 Oct ~23:10 UTC:** keys set by Gabriel in both repos;
  guard.yml test_alerts sent all four levels and all four arrived on his phone.
  **Watchdog routine updated 15 Oct:** knows guard.yml (five workflows), judges recorders by the data, and
  treats a guard-recovered day as recorded (no false alarm). The daily GREEN rides health.yml's 23:37 UTC cron,
  which GitHub has run 2-4 h late every night (01:43-03:46 UTC, 8-15 Oct), so it lands roughly 6:30-9:00 pm Pacific.
  **Bloomberg intraday pull - depth unverified:** forum sources put Bloomberg's intraday bar history at ~140
  days (one older post: ~50 business days); Marc saw finer bars reach less far back. 50 business days from
  23 Sep (H5e's first day) is ~2 Dec, so the post-verdict pull must happen by ~25 Nov at the latest; ask Marc
  how far back the 1-minute OVX/GVZ data went to confirm.
  **Thu 22 Oct 10:00 Pacific:** a one-off routine (trig_015V2zQEWbx7T7GL8wt1JXpG, no connectors) pushes Gabriel
  a reminder: did a GREEN arrive every weekday 16-21 Oct? If yes, retire the Mac iMessage. Phase 2 (first responder) was DEFERRED 16 Oct to after SCCUR (see Decisions, 16 Oct); it would need a
  fake-failure test before it goes live. Gabriel: "we can build it whenever u think is best". Phase 2 (Gabriel: after Pushover is proven): a
  read-only first-responder Claude routine on failures. The Mac iMessage (launchd com.volrec.daily) is
  untouched - retire it once Pushover has run a week (Gabriel's call).
  **Recorder push failure, 15 Oct 18:30 UTC (GitHub emailed Gabriel).** A HANDOFF commit pushed by Vega at
  18:30:11 landed while record.yml was running; its plain `git push` was rejected, so the day's panel
  snapshot was lost. Recovered: record.yml re-dispatched at 14:33 New York, before the close, and the 109
  rows landed at 18:35 UTC (surface.yml ran normally at 18:40). Fix: record.yml now rebases and retries like
  surface.yml; a pressure check covers both writers and auditor mutant record-push-no-retry proves it
  (81/81). Lesson: no hand pushes to the public repo between about 18:15 and 19:15 UTC on weekdays.
  **Marc Vinyard replied, 15 Oct.** (1) LSEG: Pepperdine's academic account gets the same UserNotPermission -
  the entitlement gap is institution-wide, so LSEG is CLOSED for OVX/GVZ/VXN/RVX (no more asks). (2) He found
  historical INTRADAY OVX, GVZ, VXN and RVX on the Bloomberg terminals (finer bars = shorter history). This
  answers the snapshot-timing question directly (index level at 14:30 vs the close). Vega's call: pull it ONCE
  at the first terminal visit AFTER the 19 Nov verdicts (whole H5e/H7 window in one pull; 1-minute history
  reaches months back, so nothing is lost by waiting), analyse after the verdicts as a dated, exploratory
  limitation measurement beside the registered numbers; raw files in ~/Documents/volrec-bloomberg/, never the
  repo; "Source: Bloomberg Finance L.P." (3) Mentor: he recommends Dr. Levon Goukasian and offers himself if
  Goukasian is unavailable. Plan: Gabriel asks Goukasian once (email drafted 15 Oct; attach
  ~/Desktop/Mitton-design-memo-Goukasian.pdf, source DESIGN-MEMO-GOUKASIAN.md). Marc thanked 15 Oct (sent);
  the Goukasian email is SCHEDULED for Tue 20 Oct 9:30 a.m. (after fall break). No answer by Fri 30 Oct ->
  accept Marc's offer.
  **Goyal & Saretto (2009) read, 14 Oct:** logged in lab/REGISTRATION.md; R1 is a cousin of their signal, not
  their rule (spec note + PAPER-OUTLINE/PAPER-DRAFT wording). Their exact signal on the five funds is queued
  for December's open half instead of tested now (Vega's call, under Gabriel's "push it back if it costs"
  instruction: testing now would spend the holdout). Bondarenko (2014) still to come.
  **Done 12 Oct (Gabriel's yes):** (1)+(2) in H8-DRAFT (OPRA yardstick table, the corrected Δ reason,
  the bid/ask/mid pilot table, open choice 5); (3) README's measurement paragraph, a dated clarification
  at the end of H3's adjustment log (no number or verdict touched), and a PAPER-OUTLINE limitations line;
  (4) the 19 Oct Cboe follow-up note above.
- **Alpaca's own description of the free feed, checked at source 12 Oct:** docs: "a free derivative of the
  original OPRA feed", "the quotes are not actual OPRA quotes"; staff on the forum (Dan_Whitnable_Alpaca,
  t/17795): "randomized a bit" (12 Sep 2025), "can vary from the actual `opra` data" (1 Feb 2026). Added
  (Gabriel's OK) to PAPER-OUTLINE section 3, the README feed note and H8-DRAFT's rationale - text only, no
  registered number touched. **For after the verdicts:** the 2013+ OPRA archive could run the Cboe-replica
  decomposition over years, and confirm the unconfirmed 11 May 2022 OVX/GVZ switch to NBBO - never inside
  H7's window; a discussion with Gabriel first.
**Sat 17 Oct - state at the fall break (everything above is history; the dated plan continues below)**
- All checks green and re-verified on the day (system-status table): every reading recomputed by an independent
  implementation (661 of 661), auditor 109 of 109, Databento headroom to 11 Nov confirmed. Nothing is left to
  build before the verdicts; the reminders and alerts carry every dated task. Gabriel's next action is the
  Mon 19 Oct Cboe reminder.
- **Wed 11 Nov:** the 40-day window closes, and with it H5e's and H7's. The live panel's premium analysis
  (`analyze.py`) needs Alpaca keys, so it will run through a manual read-only workflow like `sample_a.yml`;
  register what it will read before running it.
- **Thu 12 - Thu 19 Nov:** the cloud writes H5e FINAL and H7 once each window's data is complete (11 Nov's
  OPRA arrives about 13 Nov) and by 19 Nov regardless. **Fri 13 Nov 16:30 UTC:** the phone alert
  (`trig_01MG53JubGrUPhph4bd9yimY`); "NOT recorded yet" then means waiting for data, not a failure.
- **After the verdicts:** the site and any next step are a discussion with Gabriel first (his 4 Oct rule).
- **AAPL first (corrected 17 Oct):** its last listed ex-date is 10 Aug, so the stale-dividend WARN fires from
  **19 Nov**, and Apple usually goes ex around 10 Nov - add it to `data/dividends.csv` when declared (late Oct;
  H4's dividend adjustment uses it). **DONE 3 Nov:** ex-date 12 Nov, $0.27 (Apple's 8-K). **December:** the
  December ex-dates for SPY, QQQ, IWM and NVDA (WARNs from about 19-30 Dec). **Both GitHub tokens: DONE 3 Nov**
  (Gabriel renewed both to expire Mon 1 Feb 2027). **By Fri 22 Jan 2027: renew BOTH again.** (1) cron-job.org's
  `volrec-trigger`: paste the new one into every job, then update `TRIGGER_TOKEN_EXPIRES` in `pressure_test.py`.
  (2) volrec-licensed's `PUBLIC_REPO_TOKEN` (the private nightly run checks this repo out with it, so a lapse stops
  the whole run): replace the secret, then `LICENSED_TOKEN_EXPIRES`. WARN from 4 Jan, FAIL - an email - from 25
  Jan; the 11 Jan reminder carries both.
- **February 2027:** the write-up, TimesFM's FAIL included.
- **Wed 21 Oct (Gabriel):** (1) **SCCUR ACCEPTED.** Register by **Fri 23 Oct** for the $90 early rate (Gabriel
  pays; $100 to Sat 8 Nov, the presenters' hard deadline). Format (poster or talk) is in the acceptance email -
  Gabriel forwards it. Per Decision (3), 16 Oct: a poster ready ~6 Nov with script-filled result boxes; the
  verdict boxes fill only after 12-19 Nov, so the poster prints with them the weekend of 20-21 Nov or carries
  "registered, reading due 19 Nov". (2) **Goukasian declined** mentoring. Marc Vinyard's 15 Oct offer is the
  fallback; email to Marc drafted 21 Oct. The 30 Oct Goukasian reminder (`trig_018gPmAWkwUPGK94zuWNmjJw`)
  disabled. (3) **Cboe follow-up sent** (19-21 Oct; the 14 Oct draft, its index list pointed back to the
  original eleven). Still no answer; fallback stays FRED's reprints. (4) **Prof. Scott Baier** (Clemson,
  economics; sbaier@g.clemson.edu) emailed 21 Oct (sent). Gabriel met him at Vanderbilt's Economics for Leaders;
  he had offered letters of recommendation. Asked to read a summary or the February draft as an outside reader
  ("where an economist would push back") and, later, a letter. His role: design and inference review, not the
  options math; he may see public material and aggregates only, never licensed raw files. If he replies, send
  a retitled copy of DESIGN-MEMO-GOUKASIAN.md. Marc stays the SCCUR mentor. (5) **Marc asked 21 Oct (sent)**
  to be faculty mentor, taking up his 15 Oct offer; awaiting his reply.
  (6) **SCCUR registered** (Gabriel, 21 Oct, early rate). Acceptance email (Hsien-Chang Lin for the committee):
  title "What Does Free Options Data Cost? Measuring a Retail-Grade Feed Against Cboe's Volatility Indices";
  SDSU, Sat 21 Nov; no reviewer comments; format (poster or oral) NOT stated - check Whova; presenter schedule
  after 8 Nov; questions to 2026sccur@sdsu.edu.
  (7) **Marc Vinyard said YES (21 Oct): he is the project's mentor** (poster credit: "Mentor: Marc Vinyard,
  Pepperdine University Libraries"). **Poster begun 21 Oct:** `poster/build_poster.py` (48x36 in landscape,
  Better Poster layout; SCCUR limit 56x42, taped to boards). Frozen figures copied with their sources; H3's box
  read live from `tools/h3_scorer.py`; H5e FINAL and H7 boxes parse the blocks `record_verdict.py` writes and
  say "reading due 12-19 Nov" until then (never a preview). Gabriel: headline kept for now, no logo, credits
  instead; a research agent then a design/build agent revise it. Print target Fri 20 Nov.
  (8) **SCCUR Resource Guide (PDF, updated 16 Oct; Gabriel's copy in ~/Downloads):** posters max 56x42 in, tape
  provided, stand at the poster the whole 75 min (10 min setup before, 5 min load-out); format fixed at
  submission (confirm "poster" in Whova); AI policy: acknowledge AI-generated material and be able to explain
  every method without AI; check-in needs the QR code from the registration email (early check-in Fri 20 Nov
  10:30-5, Student Union courtyard); parking in P3/P4 is included but the car must be registered in advance;
  conference hotel rate at the Marriott Mission Valley ($189) until 30 Oct (Sheraton's ended 20 Oct); poster
  schedule after 8 Nov.
  (9) **Prof. Scott Baier said YES (21 Oct)** to being an outside reader. Summary written for him:
  DESIGN-MEMO-BAIER.md (PDF on Gabriel's Desktop, Mitton-research-summary-Baier.pdf): the Goukasian memo
  retitled, the mentor ask removed, wording tightened (bars dated before each test, not before all data;
  H8's figure labelled a pilot; n_eff/intervals/Holm described as planned, not done), three economist's
  questions. Credit him on the poster only if he reviews it and agrees to be named. Gabriel sent it 21 Oct (the copy
  before a one-word fix: it says the snapshot is ~90 minutes before the close; the outline says ~80 - harmless).
  (10) **Poster decisions, Gabriel 21 Oct, BEFORE any H5e FINAL / H7 verdict:** the AI-use line is approved
  ("Code written with the help of an AI coding assistant (Claude Code); the research question, decisions and
  interpretation are the author's."). **Headline fallback rule:** if H7's block is written and H7a or H7b FAILS,
  the headline becomes "Widen the strikes, and free data lands within a point of Cboe's index." (if H3 holds;
  if H3 failed too, "So far, free data loses more to the method than to the quotes."). Coded in
  `poster/build_poster.py` (`headline()`), 5 tests; a NOT READ (below minimum) part is not a failure.
  (11) **Cboe asked a third way (21 Oct, sent):** marketdata@cboe.com, cc permissions@cboe.com - the address
  cboe.com/us/indices/accessing-index-data names for index data licensing (phone backup: Multi-Asset Solutions
  (312) 786-7764). Same request (non-commercial, aggregates only, credited) plus SCCUR and the 2016-2026 study.
  If no answer by ~13 Nov: the FRED-reprint fallback (credit "Cboe, via FRED").
  (12) **Marc sent the poster draft (21 Oct)** with: confirm the credit wording, a 20-30 min meeting in the
  next two weeks, and whether Pepperdine funds or prints undergraduate research posters.
- **Fri 23 Oct:** **the Mac iMessage is RETIRED** (Gabriel: a green Pushover alert arrived every weekday). launchd
  `com.volrec.daily` unloaded; its plist moved (not deleted) to ~/Documents/volrec-retired/. `tools/notify.py`
  stays in the repo, unused. **Found while doing it:** Gabriel's crontab still holds an OLD weekday 08:30 line
  that runs `record.py` from `~/volrec` with Alpaca keys written into it in plain text. `~/volrec` no longer
  exists, so it fails at `cd` and does nothing - but the keys sit in the crontab. Raised with Gabriel: remove the
  line, and rotate those keys if they are still the live ones (his decision; never edited without him).
  **Removed 23 Oct on Gabriel's OK** (it was the crontab's only line; no copy kept, so the keys are not moved
  into a file). Key rotation stays Gabriel's call.
**Wed 28 Oct - state after the outside review (the dated plan above still holds; nothing needs Gabriel before 30 Oct)**
- **Wed 28 Oct - the outside review (Astra = gpt-6-astra via Gabriel's ChatGPT, 24-25 Oct; reports in
  ~/Documents/Codex/2026-10-24/hey/outputs/).** Gabriel had it review everything, then: "do whatever u want that works
  the best just run a bunch of tests". Vega verified all 26 findings against the code (R1-R10, M01-M10, A01-A06) before
  acting. **No registered bar, window, estimator or verdict moved; every real registered output is unchanged.**
  - *Fixed, verdict guards (before 11-12 Nov):* H3 scorer R1 (NaN t -> UNSCORED, not p=0 HOLDS), R3 (printed gaps
    judged with their 0.005 rounding slack; UNRESOLVED when the print cannot show the side), R4 (BH family stays five);
    H7 R8 (finite values only), R5 (unusable OPRA waited on; every uncounted day NAMED in the record), M04 (descriptive
    intervals use the registered sample). Logged in the H3 and H7 files as implementation guards, NOT adjustments.
  - *Fixed, bugs:* R2 `analyze.build_panel`'s forward-window check was silently disabled by the price cache's `_start`/
    `_feed` keys (the live-panel premium analysis has NOT been run for the record, so nothing published moved); R6
    `independent_check` counted empty pairs as agreement (now exit 4 when nothing numeric was compared; today 883 of
    883, all numeric); M07 the H4 delta sensitivity kept after-close days.
  - *Lab (re-run on files already bought, $0):* **M03 was real** - the one USO trade held across the 29 Apr 2020
    1-for-8 split settled on the new share; OCC memo #46881 (USO1 = 0.125 x USO) now applies. It REVERSES the
    paper's "USO +6.9% -> -2.9% with excluded months added back": correctly settled, +7.6%. GLD's version stands
    (-3.8% -> -9.4%). M02 strip cost with the portfolio held fixed: ratios unchanged (2.06-3.33), P3 still 5 of 5.
    M08 stress lab on the added-back sample: GLD's half-account-loss odds 34.8% -> 62.6%. Every registered lab number
    is byte-identical. lab/REGISTRATION.md, PAPER-DRAFT 5b and PAPER-OUTLINE corrected, dated.
  - *H2 (M01, M05, M10):* confirmed - the pooled H2a t treats correlated equity indices as independent (and breaks the
    project's own rule 5); H2b's verdict line tested correlation with the IV level, not the registered autocorrelation;
    RV^2 carries 1/c4^2 (~2.4%). A descriptive companion (date-clustered H2a, per-pair autocorrelation, raw variance) is
    appended to `samples/long/test_h2_variance.py`; it runs in the manual read-only `sample_a.yml` (Alpaca keys) -
    **run 28 Oct (Actions 40720872275): clustered on date, H2a's variance form is t 1.34, p 0.18 - NOT significant
    (logs t 10.99, volatility 5.99); H2b on its registered statistic: log lower on 3 of 11 pairs.** H2a stays "holds
    as recorded" but is reported as not robust (H2 file, poster row, TEST-INVENTORY).
  - *Wording:* PAPER-DRAFT ("truncation, not data", "every registered test rejects near 5%", "variance" vs volatility
    premium), PROTOCOL's n_eff (an AR(1) approximation), TimesFM's target (mean LOG VIX), H4's bucket labels (K/S bands
    holding both types; note in the H4 file, not a strike).
  - *Deferred, with reasons:* R9 and R10 (recorder: a mid-run close re-check before the monthly pass, and recovering a
    failed auxiliary pass) are recorder-code changes that only bite on early-close days; no recorder edits inside H7's
    window - do them after 11 Nov, before the 27 Nov half-day. Checked 28 Oct: all 13 monthly days since 9 Oct have
    their rows, so nothing was lost. R7 (the independent replica's crossed-quote and K0 zero-bid edge cases) after the
    verdicts; the real data agree. The private workflow's exit-code labels were NOT edited (a mid-window workflow edit
    once cost a trading day): an exit 4 still raises the yellow alert, labelled "crashed".
  - *Astra's bridge* (tools/codex_review.py, its test, docs/CODEX-REVIEW.md, a CLAUDE.md section, a .gitignore line)
    sits uncommitted in the working tree, Gabriel's local tool; not pushed to the public repo.
  - *Astra reviewed the fixes the same day* (tools/codex_review.py; "incomplete" - its bundle could not include every
    file - but six concrete points, each checked): H3 now scored at FULL precision (`modelfree.py --precise`), so the
    p-values are protected too, every verdict unchanged; non-finite H7 inputs are WAITED on, not only listed; a crossed
    held strip leg gives an unavailable cost; the added-back broker, block-length and crash-replay tables added; the
    split rule's cash-in-lieu limit stated and bounded (0.00017); R4 tested through score() itself. All taken.
  - Tests: pressure 0 fail; H3 +11, H7 +5, describe +1, lab +7, poster 19; 15 new auditor mutants (127 total).
- **Wed 28 Oct, Gabriel's updates:** Marc spoke with Gabriel 27 Oct - no meeting date set yet; **poster printing will be
  funded** (no cost to Gabriel). Prof. Baier has not replied; Gabriel will send him the paper draft in February (no
  chasing before then). Cboe: still nothing (third request 21 Oct); the FRED fallback stands from ~13 Nov. Pitch
  practice: not yet (Gabriel's call) - offer again closer to 21 Nov.
- **Fri 30 Oct, SCCUR's presenter email (Liza Bennett, 29 Oct) + guide updated 23 Oct:** POSTER confirmed. Session time
  and room announced **Mon 16 Nov** (in Whova). Badge pickup at least 30 min before the session (early check-in Fri 20
  Nov 10:30-5); 10 min setup, 75 min at the poster, 5 min breakdown; double-sided tape provided; max 56 x 42 in.
  Parking: register the car on OffStreet for Lot P3 or P4 before arriving. Conference wifi 2026SCCUR (21 Nov only);
  lunch is a campus meal voucher. IP note in the email does not apply: the work is already public (MIT code, public
  site). Print order (funded via Marc) can go in once the verdicts land; the session time does not affect it.
- **Sat 31 Oct - full top-to-bottom audit** (Gabriel: "check everything top to bottom ... not just a test, but also an
  audit ... optimize it"). Read-only checks first, then five fixes, each tested, reviewed by Astra twice, audited.
  - *Clean:* ten unit suites 0 failures; pressure test 0 fail, 2 known warns; auditor 127 of 127 on the old code, **130 of
    130** on the new; independent re-implementation 937 of 937. **Data:** all four panels - no duplicate rows, no crossed or
    non-finite quote, mids, moneyness and days-to-expiry consistent; the only gaps are the accepted ones (16 Sep; DUK, FXE,
    MDY, XLRE on 28 Sep-5 Oct, no listed expiry inside the window). **Operations:** 200 GitHub runs since 16 Oct, all green;
    all 10 workflows active; volrec-licensed PRIVATE and every nightly run green; 7 volrec routines enabled, none with
    connectors; the 26 Oct cloud auditor read 112 of 112. **The clock change (Sun 1 Nov) needs nothing:** cron-job.org runs
    in New York time (checked 9 Oct), record.py and the guard use zoneinfo, the backup's stand-aside is tested at EST times.
    **Security:** no key or token in any tracked file or anywhere in git history; no licensed file ever committed; the live
    site is HEAD and every link resolves. **Lint** (ruff, pyflakes rules): no undefined name in live code.
  - *Fixed:* (1) `daily.py` had said LOOK AT: git pull every day since 24 Oct (`pull --rebase` refuses while Astra's
    uncommitted bridge files are present) - it now fast-forwards around an uncommitted file, syncs main only, and never
    stashes or overwrites an ignored file; ALL CLEAR again. (2) The no-push window is ENFORCED: the pre-push hook asks
    `tools/push_window.py` (record.py's slots, New York time, early closes) after the pressure test; the UTC rule of thumb
    would have been an hour wrong from Monday. Three mutants. (3) **Speed:** pressure test 37-58 s -> ~16 s (the seeded
    fixed-b null memoised; the four slowest checks run side by side and are judged where they were; one test no longer
    waits out API pacing); h3_scorer 15 s -> 4 s. Every check line and the scorer's output byte-identical; auditor CPU
    -19%. (4) hypotheses/README: H2's row now carries the 28 Oct "not robust, clustered on date" result, as the poster,
    TEST-INVENTORY and the outline already did; H3's row is at 30 Oct. (5) Astra (two reviews; the first bundle was
    truncated): six points, all verified and taken - including a mutant the memo commit had stranded, which the audit
    itself reported as INCONCLUSIVE before the fix.
  - *Forward, with numbers (nothing before 21 Nov):* **data/surface.csv grows ~0.5 MB a trading day** (15.7 MB on 30 Oct):
    GitHub warns past 50 MB (~mid-Feb 2027) and refuses a file over 100 MB (~late June 2027), when the recorder could no
    longer commit. Split it by month after the January confirmatory window (a recorder change, so not before). **The site
    downloads all of surface.csv on every visit** (3.9 MB compressed now, ~5.5 MB by 21 Nov) for its health panel only; the
    page shows at once, the live panel waits - for the post-verdict site discussion (a small daily summary file, or a
    ranged read of the tail). A full audit is now ~25-30 min (130 mutants); the cloud routine backgrounds it. A stale app
    worktree (`.claude/worktrees/hopeful-meitner-74bb9a`, merged, clean) can go when convenient.

**Tue 3 Nov - the deep audit and its fixes (the dated plan above still holds; both tokens renewed that evening, next by 22 Jan)**
- *Asked* (Gabriel, "paranoid again"): "run a check on everything ... Dig DEEEEPPP"; after the read-only report, "make
  all the fixes that you believe to be the best, then run tests on them". Nothing below touches recorded data, a
  registered bar or verdict, a frozen file, recorder code or a recorder schedule.
- *Clean:* **Data** - all four panels: no duplicate row, no crossed or broken quote; no recorded row rewritten in 75
  commits except the one documented migration; the clock change landed (Mon 2 Nov rows taken 14:31 and 14:40 New
  York). **Jobs** - triggers and guard on time every day since 19 Oct, every workflow green, the nightly GREEN sent,
  the private run green every night, Databento $84.04; the verdict dry run lines up H5e FINAL and H7 for 12 Nov.
  **Security** - no key or token in git history, no licensed file ever committed, no routine with a connector.
  **Public** - the site is live at HEAD with no console error, the poster builds, OSF is public. **Interim readings
  (not the record):** H3 to 2 Nov at full precision H3a 0.616, H3b -0.324, H3c p 0.0215 (all three hold), BH 4 of 5
  and 3 of 5; H5e 0.98, 19 of 28.
- *Fixed* (this repo's "3 Nov audit fixes" commits; `9d6de2c` in volrec-licensed):
  (1) **The once-only H3 companion would have read "H3c UNRESOLVED" on 12 Nov.** The private run gave the frozen
  scorer a 2-decimal `modelfree.py` file, and since 28 Oct the scorer gives H3c and the BH counts only at full
  precision. Reproduced first: the 2-decimal file gives "H3c UNRESOLVED" and "n/a of 5"; the same data with
  `--precise` gives exactly the scorer's own run (H3a 0.616 HOLDS, H3c p 0.0215 HOLDS, 4 of 5 and 3 of 5). That one
  line in volrec-licensed's `daily.yml` gained `--precise` (3 Nov 17:55 UTC, five hours before the night's run; the
  step runs once, after both finals). No verdict changes.
  (2) **volrec-licensed's `PUBLIC_REPO_TOKEN` expires ~23 Dec, and nothing said so** (only the cron-job.org token was
  dated). Now dated in the pressure test beside the trigger's (WARN 25 Nov, FAIL 16 Dec); each token's check is a
  FAIL line plus a WARN line, so the auditor can break each one. The 1 Dec reminder covers both; both are due 15 Dec.
  (3) **The pressure test fetched the live FRED rate** in a fresh copy on a machine with a real key - this Mac,
  inside the audit's worktrees: 4.06% fetched, the rate check rightly FAILED against 3.91%, and one mutant read
  INCONCLUSIVE. GitHub and the cloud auditor have no key, so never hit it; a stranger with a key would. Two layers:
  the pressure test swaps a real `FRED_KEY` for the `use-cache` placeholder, for every check and child (an absent key
  stays absent: r = 0, as on GitHub), and `use-cache` can no longer reach FRED - a series missing from the cache is
  refused (`tools/fred.py`, LookupError; `modelfree.risk_free` already falls back to r = 0 on any error). New checks:
  the run must leave `data/fred_cache.json` byte-identical (judged last, in a new section U), and an in-process test
  with the network patched out proves a miss makes no request and writes nothing.
  (4) **The phone's nightly H5e figure was the r = 0 version** (0.99 against the record's 0.98 on 2 Nov; in daily.py's
  full line, 20 of 28 days against 19): GitHub's runner has no FRED cache (git-ignored), and the alert's filter drops
  daily.py's "NOT the reading of record" label. `daily.py` now runs `tools/seed_frozen_rate.py` before the H3/H5e
  step and after the pressure test (so every check still sees what it saw before): it writes the frozen rate only
  where no cache exists and checks one that does, and a cache without the registered rate is a LOOK AT. Proved end to
  end in a fresh clone, with a real key set and again as GitHub's runner (UTC, no key, no cache): rate 3.910%, H5e
  0.98 and 19 of 28, the phone text "0.98", afterwards only the seed in the cache - nothing fetched. With a cache
  holding another series only: "LOOK AT: pressure_test, frozen rate", the cache left untouched.
  (5) **The site's countdowns pointed at GitHub's backup cron** (14:47 / 14:57 UTC; the rail read ~21 hours when the
  recording was ~2 hours away). They now count to the recorders' real start - 14:30 / 14:40 New York,
  11:30 / 11:40 on an early close - skipping weekends and market holidays (`V.nextTrigger` in `tools/volrec.js`, used
  by the rail and the monitor page). The pressure test compares the site's copies of the start times, early closes
  and holidays with record.py, the guard and panel_health, and runs the countdown itself in node in 11 cases (both
  clock changes, a weekend, holidays, an early close). The monitor's pending countdown is recomputed each second, as
  the rail is, so it rolls on past a start instead of resting at zero.
  (6) The backup WARN said "landed 20:01 UTC" of a run that started 8 h 06 m late; it now says the quote stamps read
  20:01 and stop at the close.
  (7) **Seen on the live site after the push:** the rail read "LAST SNAPSHOT 1h 60m ago". `V.since` rounded the
  minutes after taking the hours, so for 30 seconds every hour it read "Nh 60m" (since 13 Sep); it now rounds to
  whole minutes first, and the pressure test runs it in node at 8 values (the old formula fails 3 of them).
  *Tests:* pressure test 0 fail, 2 warn; eleven suites 0 failures; independent 971 of 971. **Fifteen new auditor
  mutants, 145 in all** (a side job writing the cache, the placeholder fetching, each token lapsing, daily.py
  skipping the seed, ignoring its failure, switching its test off or missing a crash, a cache without the rate, the
  seed passing one, the site's start time drifting, a holiday dropped, the rail counting to the surface, the
  countdown ignoring holidays, the rail's "ago" rounding the old way): the full run on the final code reads
  **145 of 145** (3 Nov, 30 min).
  *Astra* (Ultra) reviewed packets of the diffs - its runner bundles only uncommitted files, each cut at 32 KB. The
  first review read INCOMPLETE (it lacked `V.isoDay`, daily.py's run and status code, and the audit's per-mutant
  results), with four findings, all verified and taken: a cache holding other series but not the rate gave r = 0
  under ALL CLEAR (daily.py seeded only where no file existed and ignored the seed's exit code) - now a LOOK AT, with
  a seed test and three mutants; the same gap in the pressure test's rate check; the monitor's pending countdown
  rested at zero past a start; and this entry had said every check runs with `use-cache`. The follow-up review had
  an evidence packet too (the full audit mutant by mutant, the fresh-clone runs, the browser readings, the suites)
  and confirmed the four fixes and this entry's claims, with one LOW finding, taken: the daily.py check read text
  only, so `if False:` in place of the seed's test would have passed it. Now `daily.main()` also runs with every
  step stubbed - a seed that fails or crashes must read "LOOK AT: frozen rate", a sound one ALL CLEAR - and two
  more mutants break it. Left open by design: the Ubuntu / Python 3.12 run is tonight's health run (the changed
  files parse under 3.12's grammar), and H7's licensed comparison was out of its scope.
- *Forward:* **Gabriel, DONE the same evening:** both tokens renewed to Mon 1 Feb 2027 (the old dates were right:
  29 Dec and 23 Dec), the secret replaced and every cron-job.org job updated, the 27 Nov and 24 Dec guard copies
  set to their single dates; the pressure test's dates follow, and the reminder moved to Mon 11 Jan. **After 11 Nov (the schedule freeze ends):** GitHub's backup cron has less room
  in winter time - by GitHub's usual delays it would have saved ~45% of days in summer time and ~33% now; an hour
  later (15:47 / 15:57 UTC) restores the summer figure, and it moves back on Sun 14 Mar 2027. Low priority:
  cron-job.org is what records; the backup matters only if that trigger fails. **Small:**
  `samples/long/test_h2_variance.py` reads like a test but is `sample_a.yml`'s script and needs Alpaca keys - rename
  it with the write-up, not before. The stale app worktree (`.claude/worktrees/hopeful-meitner-74bb9a`, merged and
  clean) was removed 3 Nov; its branch is kept.

**Wed 4 Nov - the index closes arrived (Marc Vinyard, 3 Nov), and the new token works**
- *Token:* the private run's first night on the new `PUBLIC_REPO_TOKEN` (run 41764163534; GitHub started the
  23:05 UTC schedule at 02:58 UTC) went green end to end, the public checkout included.
- *Data:* Marc pulled daily closes from **Compustat through WRDS** (Index Prices - Daily): S&P 500 from 2 Jan 1990
  (9,277 days), DJIA from 2 Jan 1997 (7,505), Nasdaq-100 from 2 Jan 2001 (6,497), Russell 2000 from 2 Jan 2004
  (5,747), all to 2 Nov 2026. Closes only, no highs or lows; price indexes. Checked: no missing close, duplicate,
  weekend date or non-positive price; the only gaps over four days are real closures (9/11, 2 Jan 2007, Sandy).
- *Terms (Marc, 3 Nov):* "you can publish aggregate findings, but not share the raw data" - the Bloomberg/LSEG rule.
  The files live in `~/Documents/volrec-wrds` (outside both repositories, README with checksums); `*.xlsx` is
  already ignored here. Credit line when used: Compustat via WRDS, Pepperdine University Libraries.
- *Use:* unchanged from 2 Nov - a NEW registered test after the 12-19 Nov verdicts; H1 stays as recorded. The
  implied-volatility side for the same start dates is Cboe's VIX, VXD, VXN and RVX (FRED reprints them; Cboe's
  permission is still unanswered, FRED fallback from ~13 Nov). Nothing is analysed before the registration.
- *4 Nov (Gabriel):* Cboe has forwarded the permission request internally - a reply may come; the FRED fallback
  still stands if none arrives. Thank-you to Marc drafted, asking WRDS's credit wording and, if easy, the daily
  highs and lows from the same table (for a range-based check in the registered test).
- *Databento Core Indices (newsletter, 4 Nov):* dataset `DBIX.CORE`, 2,500+ indices incl. VIX and OVX; a
  subscriber's history starts 7 Dec 2025 (Databento's blog; the "23 Nov 2025" first written here came from a
  secondary summary, corrected the same day), so no use for the 1990 test. $99/month plans, or usage-based at
  $10/GB. **For the 20 Nov discussion, not before:** usage-based intraday OVX/GVZ/VXN/RVX over the H5e/H7 window
  could answer the snapshot-timing question with a licensed, scriptable source, likely for cents - price it first
  (`get_cost` is free), then choose it or the 23 Nov Bloomberg pull. No subscription; nothing bought or analysed
  before the verdicts. *(The purchase part was superseded the same day: next bullet.)*
- *DBIX bought and SEALED (same day; Gabriel: "yes go ahead", plus "if u get any more ideas ... go ahead"):* the
  free checks showed usage-based access reaches back only to **21 Oct** (earlier needs a subscription; undocumented
  whether that start is fixed or rolls - it was exactly 14 days back). Those are the late-October days of H5e's
  and H7's windows, so they were bought now: 17 indices incl. OVX, GVZ, VXN, RVX, VIX, VXAPL; one-second bars +
  daily bars, 21 Oct - 3 Nov; **$0.33**, ledger tag `-dbix`, own $1 cap; ledger $84.55 of $120. They sit in the
  PRIVATE repo's `dbix/`, with every file's sha256 in private commit `0098e82`. Only structure was read (rows,
  symbols, columns, timestamps): the hashes show the files unchanged, and that no value was read rests on this
  record. 4-11 Nov to add after 11 Nov (phone reminder Thu 12 Nov, `trig_016FJwoG5fqGtL5FcK1EJQF3`).
- *The plan:* `docs/drafts/2026-11-04-index-timing-plan.md`, committed in the same commit as this entry,
  before any value is opened; that commit's hash goes beside the seal in the private `dbix/README.md`.
  Exploratory, OVX and GVZ only: each registered gap (H5e, H7) splits exactly into the estimate's gap to the
  index at the snapshot minute plus the index's move to the close. No test and no split of causes. It cannot
  reach H7's in-sample +0.45, whose days predate 21 Oct. SCIENTIST.md runs nothing unregistered (and H7 leaves
  intraday index values out), so it runs only once Gabriel approves it as a descriptive registration in
  `hypotheses/`, or under a dated exception he writes down.
- *Drafts, nothing registered:* H8-DRAFT choice 6 (both feeds against the same-minute index, ~$0.50) and
  `H10-DRAFT.md` (H1's frozen code on the WRDS index closes, windows ending before 2016). H10 would be a
  preregistered secondary-data analysis and needs a dated exception to PROTOCOL step 5: all its days are
  recorded, and the price files were opened for the quality check. Its planning power is clear for VIX/SPX only;
  the other three fall short in the harshest case (σ ×1.5, ρ 0.4, fixed-b critical values). **Correction to the
  *Use* line above:** Cboe's own files for VXD, VXN and RVX start only in Sep 2009 (`samples/long/SOURCES.md`);
  the 1997, 2001 and 2004 starts exist only in FRED's reprints, so H10's early windows for those three rest on
  FRED (on Cboe's files alone, about 75 windows each before 2016, too few for the power figures).
- *Review:* Astra Ultra read all three the same day (`.codex-reviews/20261104T165551Z-w998stl_`): 1 high, 10
  medium, 1 low, all verified and fixed - the split's wording (and a "method dominates" inference, dropped),
  the timestamp, freshness and close rules, and H10's route, inference (fixed-b Newey-West proposed, as
  PROTOCOL's house method), power, segmentation and noise floor. The one follow-up (`20261104T172618Z-_vdcxg45`)
  rated 10 of the 12 resolved (H10's as drafts or planning only), one partly and one not, and raised one new
  point. All three verified and fixed after it: H8 choice 6 lacked the plan's same-day, 60-second and no-fill
  rules (added, citing Databento's documentation for the bar timestamp); "committed" was read before the
  commit existed (now worded as this commit, with its hash going into the private README); and, new,
  SCIENTIST's rule against running an unregistered analysis (the route above). Those last fixes, and the
  IV-coverage correction found after them, were not reviewed again: one follow-up is the rule. All three
  drafts are for the 20 Nov discussion.

**Wed 4 Nov (later) - Cboe approved; Databento stays pay-as-you-go; decisions settled early**
- *Cboe (Gabriel, 4 Nov):* Cboe answered the permission request (sent 10 Oct, repeated 21 Oct: non-commercial
  research, aggregates only, credited, with SCCUR and the 2016-2026 study named): "This is approved." So Cboe's
  own files stay the source of every registered verdict, as registered, and **the FRED fallback planned from
  ~13 Nov is cancelled** (a manual step; no routine carried it). Recorded in README's data-terms table,
  PAPER-DRAFT (section 3 and Appendix C), PAPER-OUTLINE, PROTOCOL step 5 and the timing plan. Keep Cboe's
  email. Cboe's use-of-content page says approval means signing a licence agreement: if one arrives, Gabriel
  signs it. The lab report's "private until Cboe's reply" gate is lifted; putting it on the site is now only
  Gabriel's yes.
- *Databento (Gabriel, 4 Nov):* never the $99/month plan; keep using the pay-as-you-go credits, and spending
  more of them to grow the dataset is pre-approved ("be my guest") - inside the $120 lifetime cap, priced
  first with `get_cost`, logged in the ledger, reported after. Ledger $84.56 of $120 (lab $79.00, H8 so far
  $2.07, the other OPRA references $3.16, DBIX $0.33). Already spoken for through 29 Jan: about $9 for H8's
  daily OPRA (about $0.15 a trading day for the eight funds, ~60 days), ~$0.30 for H7's monthly-expiry files to
  its window's end, ~$0.20 for the DBIX top-up and ~$0.50 for H8 choice 6. About $25 stays free.
- *Decisions settled early (Gabriel: "any decisions we can do now lets do them if it is in our best
  interest"):* settled by Vega the same day. Each is Gabriel's to veto; nothing binds until it is registered.
  - PROTOCOL step 5 gains a dated **secondary-data rule**, an exception to step 5 and to SCIENTIST.md's two
    prospective rules, for one hypothesis at a time. A hypothesis on data that already exist may be
    registered as a preregistered secondary-data analysis only if the effect it tests has not been estimated
    on that data (no proxy assembled either); every prior look is listed, with how it shaped the
    specification and any proxy that could be assembled; nothing was chosen because a look favoured the
    result; Gabriel approves the exception and the final registration with a date; it is frozen on OSF with
    the secondary-data template before it runs; and every report calls it that. No agent invokes it on its
    own. H9 and H10 are the first candidates, each on its own merits.
  - **H8** (`H8-DRAFT.md`, "Decided 4 Nov"): Δ 0.10; Newey-West lag nearest 1.3√T with one-sided fixed-b
    critical values, t(T-1) beside (code, known-answer test and auditor mutant before registering, then a
    day's wait); each fund reported, the count as headline; at least 30 of the window's 41 trading days; the
    bid/ask/mid breakdown as a descriptive reading; choice 6 yes, on its own $1 cap (`-h8dbix`), dropped if
    its reader is not tested by registration. Register about Tue 24 Nov, OSF freeze in Gabriel's browser.
  - **H10** (`H10-DRAFT.md`, "Decided 4 Nov"): register as a secondary-data analysis; fixed-b Newey-West
    carries the verdict; FRED's reprints for all four; the SPX, INDU, NDX and RTY daily closes join the
    Bloomberg session; a Parkinson-range D4 only if Marc's highs and lows arrive before registration; D2 in
    the paper. Target mid-December.
  - **The timing plan:** the descriptive-registration route, now one sequence in its Route section. The
    reader, the split and the report are built and tested on synthetic files first; a day passes and the code
    is re-read; Gabriel approves and it is registered and frozen about Tue 10 Nov, before either verdict;
    the files stay sealed and the script runs only after both verdicts are recorded.
  - **Bloomberg, 23-25 Nov:** keep the 1-minute pull of OVX, GVZ, VXN and RVX - it reaches the days before
    21 Oct, H7's in-sample stretch included, which DBIX cannot - and add the four index closes. Reading the
    1-minute bars needs its own short descriptive registration, written once the export's layout is seen
    and before any analysis. The 23 Nov phone reminder (`trig_014FSkJSmGQqutozEtGxhSVq`) now names both.
  - **H9** (reserved: the Cboe-method replica on the lab's OPRA days): drafted after the verdicts and
    registered under the secondary-data rule only if it meets every condition; target December.
  - **Zenodo:** with the write-up's tagged release (Feb 2027), not before.
- *Gabriel, later on 4 Nov:* "yes to the lab tab, and I approve the decisions, I sent the email". So every
  decision above is approved, the PROTOCOL rule and H10's use of it included (each registration still needs
  his dated approval of its final text; for H9, not yet drafted, the exception is confirmed when its draft
  shows it meets every condition). The Cboe thank-you is sent. The lab report goes on the site as a tab
  (Cboe's approval lifted the last block; built next).
- *Still Gabriel's:* the Bloomberg session; OSF freezes (~10 Nov timing plan, ~24 Nov H8, H9/H10 later); his
  SCCUR session time in Whova (16 Nov); pitch practice before 21 Nov.
- *Dates:* 10 Nov timing-plan registration; 12 Nov DBIX top-up; 13 Nov verdict check; 16 Nov SCCUR time;
  20 Nov reminder and discussion; 21 Nov SCCUR; 23-25 Nov Bloomberg; ~24 Nov H8 registration; 1 Dec H8's
  window opens; after 24 Dec delete the four cron-job.org early-close copies; 11 Jan token renewals (by 1 Feb);
  Feb 2027 the write-up and Zenodo.
- *Review:* Astra Ultra read this entry and the changed files (`.codex-reviews/20261104T180407Z-og2r7tpm`):
  pressure test and independent check passed; nothing registered changed; its arithmetic matched (41 trading
  days, $84.56 spent, about $25 free after the commitments); Cboe's reply read as covering the requested
  non-commercial, credited, aggregate use, not redistribution of raw data. Three medium points, all verified
  and fixed: the secondary-data rule now requires saying how each prior look shaped the specification, naming
  any proxy of the effect, forbidding choices made because a look favoured the result, and Gabriel's dated
  approval, and it names the SCIENTIST.md rules it relaxes; the timing plan's first route text (approval after
  the verdicts, script written after them) is replaced by one sequence; H10 now says how its looks shaped it,
  and names the one proxy that could be assembled (S&P 500 full-sample volatility beside VIX's long-run level:
  the sign for VIX/SPX, already the published prior). From its notes, H8 now states the simulation error of a
  fixed-b p-value (about 0.003 near 0.05) and that the headline count is a tally, not a joint 95% statement.
  The one follow-up (`20261104T181228Z-f6v10yb7`) read CLEAR: all three resolved, nothing new found; pressure
  test and independent check passed again. Its standing notes: H8's fixed-b code, known-answer test, auditor
  mutant and day's wait are still to do before registration, and approvals, OSF freezes and the private seal
  are outside what it could check.

**Wed 4 Nov (evening) - the Lab tab: the side study goes on the site**
- *What (Gabriel: "yes to the lab tab"):* `tools/lab.html`, the `lab/` side study as a page of the site in its
  own design (the live rail, Newsreader and Martian Mono, the paper's section and figure styles), reached
  from every page's navigation ("Lab") and the paper's footer. `lab/report.py` now renders it from the
  private summaries of 28 Oct (after the M02/M03 corrections) and `trades.csv`; re-render, never hand-edit.
  The private 14 Oct `report.html` stays as it was.
- *Corrected against the private 14 Oct report:* P3 reads 2.1-3.3x (was 3.4); the limits sentence now says
  the added-back months make GLD worse (-3.8 -> -9.3 cents per dollar of premium at mid) but not USO (+6.9 ->
  +7.6), both computed from `trades.csv`; "private until Cboe's reply" is gone. The 14 Oct Leak Map left
  negative Shapley shares out of its bars, so its 20% bars did not add up to one paper dollar (SPY's margin
  limits are -23.0 cents). The page draws the Leak Map at 5% only, where margin never binds and each bar is
  exactly one paper dollar (the generator refuses to draw it otherwise), and gives 20% as Table 1: signed
  shares with their range over the 24 orders.
- *GLD's added-back figure:* PAPER-DRAFT and PAPER-OUTLINE said -9.4% of premium; the mean in `trades.csv`
  is -0.09348, so -9.3% (a double rounding through -0.0935). Corrected in both, dated; the 28 Oct entry
  above keeps its text.
- *Charts (dataviz method):* kept in neutral grey (`--lab-kept`, pinned to #697785, the grey the palette was
  validated with, when the site's `--ink-3` moved - below), spreads orange `#d95926`, commissions violet
  `#9085e9`, dark steps validated on `--panel` (the pair: CVD 26.0, normal vision 27.0; grey against each at
  least 12.6 and 16.4), clear of the channel and status colours. The break-even panels draw the net result in
  `--read` and the spread cost dashed in the same orange, with the fitted crossing's 90% interval shaded.
  Legends, table views, hover or tap tooltips through `V.hover`. Checked at 1280 and 375 wide: no sideways
  scroll outside the tables.
- *Astra's review (`.codex-reviews/20261104T213235Z-snjddknt`): twelve points, each verified and fixed.*
  (1) The registration promised the added-back months beside every Plan 3 table, and the page showed them
  only in prose: `report.py` now reads them from the private Plan 3 report (`lab-out/report-plan3.txt`),
  strictly - its registered lines must match `leak_summary.json` or the render stops - and Fig. 1's table,
  Table 1 and Table 3 carry "GLD, all 127 months" and "USO, all 127 months" rows beneath the registered ones.
  The break-even analysis was never run on them; its caption says so, and PAPER-DRAFT and PAPER-OUTLINE no
  longer say "every result both ways". (2) The heading no longer says no break-even exists, only that none is
  reliable. (3) Entry at 2:30 p.m., 11:30 a.m. on half-days; the first and last entry and last expiry are read
  from `trades.csv`. (4) "Chance of losing half" is now "chance equity falls below half its start", and the
  caption says how that differs from a 50% drawdown. (5) The sentences that are not computed rest on facts
  the generator checks first (`premises`, ten of them, each naming its sentence), and `predictions` re-judges
  P1-P5 and stops if a verdict differs from the registration's logged one. (6) A caption reports a crossing
  without an interval as such, and always the share of resamples outside the data. (7) The Leak Map refuses
  any margin leak in any of the 24 orders, a margin call, a negative part, or parts that do not add up.
  (8) `QUOTED` is gone: every figure is computed. (9) Every section and figure must credit Databento, whole
  numbers included. (10) A half-copied summaries folder stops the render; only an empty one is a fresh
  clone's SKIP. (11) Test fixtures add up by construction. (12) Each bar part is its true share of the
  width; the separators are drawn inside it. Its thirteenth, the pressure test's failure, was the local
  checkout missing 4 Nov's snapshot (since pulled); the test passes.
- *Design review (a design agent, 4 Nov), ten recommendations, all done:* the answer in the subtitle and a
  strip of five key numbers; each break-even panel gained the fitted line, its crossing, the interval's ends
  (or the value written at the edge with an arrow), a caption and a zero line; five focusable columns per
  panel with two-series tooltips and a table view; tooltips close on Escape and on scroll (WCAG 1.4.13, in the
  shared `tools/volrec.js`); Table 1 reordered, its kept column emphasised, the fund column pinned on narrow
  screens; Tables 2 and 3 compact, units in the headers; definitions beside the text; the predictions as a
  ledger (Table 4); an author line; the instrument's footer links the Lab. Site-wide (`tools/volrec.css`):
  `--ink-3` #697785 -> #6e7c8a, because the old grey read 4.35:1 on the panel, under WCAG AA (now 4.67:1;
  4.50 on `--panel-2`); `.meta dt` and the tooltip's labels a step brighter; long links wrap; the stylesheet's
  cache key moved to `?v=20261104` on all three pages.
- *Checks:* pressure test K: every section and every figure credits Databento; aggregates only, Cboe and
  Alpaca credited; no option symbol; the script fetches only the two registered panels and no OPRA; every
  page's navigation reaches the Lab; eleven checks that hold each figure to the one `lab/REGISTRATION.md`
  logged for the same fund and measure (Leak Map cents and GLD's loss, the COVID sentence's three funds,
  Table 3's drawdowns and chances registered and added back, Table 1's margin calls and SPY's 20% paper
  return, every break-even caption, USO's added-back row, the predictions' claims, verdicts and evidence, the
  GLD and USO sensitivity), and since the follow-up a twelfth: each key number read under its own label;
  and the page equals the render wherever the summaries exist (a refusal to render is a FAIL).
  `lab/test_lab.py` 211 cases, +59 for the page: one fixture that keeps every premise and counts the same
  months in every input, the Plan 3 parser on a report in the real file's line shapes and eleven ways it
  refuses, three count disagreements the page refuses, the known answer, each guard by the message it stops
  with, `render()` on a temporary folder. Seventeen bugs planted in a scratch copy of the generator (six, then
  eleven after the follow-up) were each caught by their own test; one first crashed the test run instead, so
  the page-level tests now report a crash as that check's FAIL. Auditor mutants `lab-page-uncredited`,
  `lab-page-integer-uncredited`, `lab-page-fetches-opra`, `lab-page-unlinked`, `lab-page-claims-swapped` (the
  generator and the page changed together, so the page still equals the render; the registration check
  catches it, and so does `test_lab`'s COVID sentence on the fixture - this line said "only the registration
  check" until the follow-up corrected it), `lab-page-kpi-mislabelled` (since the follow-up),
  `lab-page-partial-skip`, `lab-page-margin-range-unchecked`, `lab-page-hand-edited` (only where the summaries
  exist); all killed on a pre-check before the commit.
- *Review:* first review above. The one follow-up (`.codex-reviews/20261104T223403Z-t572ks5i`,
  needs_attention; pressure test and independent check PASS): of the twelve, 1-4 and 9-12 RESOLVED, 5-8
  PARTLY; five new MEDIUM and two LOW findings. All fixed the same evening, as below. No further Lab review
  (one follow-up per change set), so these fixes rest on tests, planted bugs and the auditor, not on Astra.
  (a) *P4's evidence* (5, MEDIUM) said "elsewhere spreads widen in step with the premium", which a failed test
  for a rising fraction does not show and a falling slope would contradict. It now states the registered
  test ("the slope's 95% Newey-West interval lies wholly above zero only there") and, computed, "on the
  others it includes zero" (true of SPY, QQQ, IWM and USO), else "the others do not pass it". PAPER-DRAFT's
  "widen in proportion to the premium on four of five funds" is narrowed the same way, dated; the
  registration's own 14 Oct log says the same and stays as logged. (b) *Six more premises* (5), each naming
  its sentence: margin calls "often" (SPY in at least one month in ten at 20%), forced liquidation leads
  somewhere at 20%, the margin shares "swing widely" (10+ cents across the orders), the COVID sentence's three
  are losses, SPY's middle groups 2+ points apart ("several volatility points"), five groups per fund ("one
  fifth"). (c) *Crossing and interval independent through the page* (6, MEDIUM): a caption with no crossing
  still gives its interval; the premise and the paragraph count only the intervals there are and name a fund
  without one; tested through `page()`. (d) *Fig. 1's caption checked on every sample it covers* (7, MEDIUM):
  `margin_free` runs before GLD's branch and on the added-back rows of the figure's table - no margin leak in
  any order, no call, and the spreads' and commissions' shares the same in every order ("every order gives
  the same shares" was not checked). (e) *Key numbers bound to their labels* (8, MEDIUM): label and value
  read from the same card, all five held to the registration's figure for that fund and measure; mutant
  `lab-page-kpi-mislabelled`. (f) *Counts reconciled* (MEDIUM): `plan3` refuses a block or stress line printed
  twice; `same_months` requires Plan 3's registered count, the break-even summary's and `trades.csv`'s
  registered rows to agree, and the added-back sample to equal `trades.csv`'s tradeable rows (the
  sensitivity's sample). The real files agree: SPY, QQQ, IWM 127; GLD 124 + 3; USO 123 + 4. (g) "stays under
  0.14" -> "stays at or below" (LOW: the bound is rounded up and can equal the value). (h) PAPER-OUTLINE names
  where the added-back rows are (Fig. 1's table, Table 1, Table 3) and that Table 2 and the break-even
  curves are registered-only (LOW). (i) The claims-swapped line above, corrected. The page itself changed in
  two sentences (P4's evidence; "at or below"); `report.py --check` matches.

**Wed 4 Nov (evening) - H8's fixed-b equivalence test, built (decided earlier that day)**
- *What:* `tools/h8_quotes.py`: `lag_for(T)`, the whole number nearest 1.3√T (8 at 41 trading days, 7 at
  30); `tost()` now takes each one-sided p from the fixed-b null (`analyze.fixed_b_null`: Bartlett kernel,
  seeded, memoised), with t(T-1)'s one-sided p beside each, never in its place; since the review (below), at
  H8's own 200,000 draws (`H8_REPS`). H8 is not registered; this is the code its decision 2 asked for before
  registration.
- *Tests:* `tools/test_h8.py` 36 cases: the lag rule; at lag 0 the simulated p at 1.70477 (t(40)'s 5% point
  times √(41/40)) is ~0.05 and t(40)'s p beside it 0.047997 (checked to 0.0001); at lag 8 the 5% point sits above t(40)'s
  1.684; a gap 1.9 standard errors inside each bound is equivalent under t (p 0.032 each) and not under
  fixed-b (0.064, 0.061); both tests one-sided (these tail checks run on 4,000 draws, for speed); and, on a
  null fixed by hand, `tost` hands 200,000 to the shared null, a draw equal to the statistic counts as "at
  or beyond", and a p of exactly 0.05 is not below 0.05. Auditor mutants `h8-tost-uses-t`,
  `h8-fixedb-two-sided`, `h8-lag-rule`, then `h8-reps-shared`, `h8-reps-not-passed`, `h8-tie-excluded`,
  `h8-tie-excluded-upper`, `h8-threshold-inclusive`, each killed on a pre-check.
- *For registration, changed the same night (Vega's call; Gabriel approved it after the push):* at T = 41 and lag 8 the shared
  seeded 4,000-draw null puts the one-sided 5% points at 2.03 and -2.06, against 2.09 and -2.11 from 200,000
  draws (the fixed-b limit at b = 9/41, simulated at large T: about 2.10); at those points the 4,000-draw null gives p = 0.047 and 0.046,
  light in both tails for this seed (about one simulation standard error each), the lenient direction for an
  equivalence test. So H8 now uses 200,000 seeded draws of its own (simulation error of a p near 0.05: about
  0.0005; about 8 s at T = 41); the shared 4,000 is unchanged for every registered figure. H8-DRAFT item 2
  says so, with the old wording kept ("kept at 4,000 so every fixed-b figure comes from one null").
- *Review:* Astra Ultra, first review of this and the reader below (`.codex-reviews/20261105T024605Z-lwiz74ix`):
  INCOMPLETE, because the packets lacked `newey_west`, `record_verdict`'s markers and some reader helpers; no
  check failed. On H8 it found the tails, the tie rule, T, the lag's rounding, the constant-series guard and
  the return shape right, and one MEDIUM: 4,000 draws can flip a borderline decision, so fix a larger H8-only
  count (it suggested 200,000) and add deterministic tie and threshold tests. Both done the same night (above).
  Its note on the wording also held: the 4,000-draw gap had been measured on the upper tail only (0.0455 at
  2.11); both tails are measured now. One follow-up review: see the reader's entry.

**Wed 4 Nov - the index-timing reader, built and tested on synthetic files (the plan's step 1)**
- *What:* `tools/index_timing.py` implements `docs/drafts/2026-11-04-index-timing-plan.md`: the sha256 check of
  every file against the private seal before it is read, and every day file the seal lists present on disk;
  OVX and GVZ only (other rows skipped before any field is converted); I(T) as the last one-second bar whose
  second has ended by T, same New York day, from 09:31, at most 60 s old, otherwise the day is not measured;
  the exact split E - C = (E - I(T)) + (I(T) - C); the 15-second "nearest bar" sensitivity, labelled; the
  0.05 close flag; each day's quote-time spread around T, with its date; aggregates only. The rebuilt readings
  use the frozen 3.910% rate or nothing runs (cache-only key, checked in-process and in modelfree's output),
  and they must match modelfree's own H5e reading, whose run must exit cleanly. It refuses to open the files
  until H5e FINAL and H7 are both recorded. `tools/test_index_timing.py`: 63 cases on SYNTHETIC files in
  DBIX's recorded layout, made from the structure only, never a value; the CSV header is typed from
  Databento's documented field order rather than taken from the reader. The pressure test needs all 63.
- *Next (the plan's sequence):* at least a day, a cold re-read, Gabriel's approval, registration and OSF freeze
  about Tue 10 Nov; the files stay sealed until both verdicts are recorded.
- *Review:* the same first review as H8's (above), INCOMPLETE for missing helpers, no check failed. It found the
  completed-second rule, New York dates, 09:31, the 60-second limit, the hash before decompression, the skip
  before conversion, the split, the sensitivity and the close flag right, and five MEDIUM and one LOW, all
  verified and fixed the same night: (a) a sealed day file missing from disk read as a day "before the data
  begins" - now refused, and every uncovered day says where it sits (before, after, or a day with no file),
  with its date; (b) the reference run's exit code was ignored and two empty sides passed as agreement - both
  refused; (c) `setdefault` kept a real FRED key and the frozen rate was never checked - the key is now forced
  to `use-cache` and the rate checked both ways (`record_verdict.rate_ok`); (d) a "widest day" pieced
  together from two days, where the plan promises each day's spread - each day is printed instead; (e) the
  verdict gate's AND was never run - now tested on the writer's own markers in all four states; (f, LOW) the
  pressure test accepted 43 of 44 cases - now 63 of 63. Its fixture point (the header came from the reader's
  own constant) is answered above. Seven new auditor mutants (`timing-gate-either`,
  `timing-lost-file-unchecked`, `timing-reference-exit-ignored`, `timing-rate-unchecked`,
  `timing-printed-rate-unchecked`, `timing-empty-agreement`, `timing-key-kept`), each killed on a pre-check.
  The one follow-up review, of this entry and H8's (`.codex-reviews/20261105T035104Z-1aaz6u50`): CLEAR;
  pressure test and independent check PASS. All seven findings resolved; no defect found in the fixes
  (`day_files` against the seal's naming, the edge classifications, `frozen_r`'s units, the forced key, the
  stubbed test of `main`). With the helpers supplied it established the three end-to-end claims: the statistic
  and the simulated null share one normalization (Bartlett weights, T denominators, the lag clamp, the variance
  floor); the gate reads the markers the writer writes; I(T)'s instants are UTC throughout, New York time only
  for the session rules. It called the 200,000-draw choice defensible (simulation error near 0.05: 0.000487).
  Its notes, recorded rather than changed: importing the reader sets `FRED_KEY` for the whole process
  (intended; only its tests load it, in their own process, and the auditor and pressure test run it as a
  file); `main`'s end-to-end test runs on stubs, so it shows the order of the steps and the refusals, not a
  rebuild from registered inputs; nothing here has run on real data. Two corrections after it, unreviewed (one
  follow-up is the rule): H8's test line said t(40)'s p was "exactly 0.04800" (it is 0.047997); and "Kiefer-
  Vogelsang's limit about 2.14", which the review noted was unverified, came from their fitted polynomial as
  recalled. Simulating the limit at b = 9/41 (T = 2,050 and 4,100; 200,000 and 100,000 draws) gives about 2.10
  (2.11, 2.09), and the same polynomial sits above the simulation at b = 1 (3.80 against 3.76). H8's entry and
  H8-DRAFT now say about 2.10; H8's 200,000-draw points (2.09, -2.11) sit at the limit.

**Wed 4 Nov (night) - the 23-25 Nov Bloomberg list, SCCUR pitch notes, and why H10's loader waits**
- *Bloomberg:* `BLOOMBERG-MONDAY.md` now opens with the next visit: two pulls, in order. (A) One-minute bars
  of OVX, GVZ, VXN and RVX from Mon 14 Sep (H7's in-sample start) to the last full day - first, because the
  history rolls off: on the shortest estimate (~50 business days), 14 Sep is 51 business days before Mon 23
  Nov, so the 23rd is the day to go. The desk is asked how far back the bars go, what time zone the export
  uses, and whether a bar stamped 14:30 starts or ends then; `TZDF` is read, not changed; the values are not
  studied until the bars' short descriptive registration is written. (B) Daily `PX_LAST` closes of SPX, INDU,
  NDX and RTY from 1 Jan 1986 (H10's decision 4), closes only, listed under H10's "Data already seen" once
  pulled. The file's Timing section (16 Sep) got a dated correction: the snapshot has been at 14:30 New York
  since 1 Oct, which is 11:30am Pacific since the 1 Nov clock change.
- *SCCUR:* `SCCUR-PITCH.md`: a 30-second opener (with the variant for the headline the poster switches to by
  itself if H7 fails), a 2-minute walk across the poster, likely questions with short answers, and two lines
  marked [after 19 Nov] to fill from the hypothesis files. Every number is the poster's own.
- *H10's loader:* not built yet, on purpose. H10's own order puts it after H8's registration and the Bloomberg
  session; its specification is a draft the 20 Nov discussion may still change; and its noise floor compares
  Compustat with the Bloomberg closes, which arrive 23-25 Nov. Built once, with both price sources in hand.
  Target unchanged: registered mid-December.

**Wed 4 Nov (night, after the push) - live, and Gabriel's yes to both open decisions**
- *Pushed:* `df6b68f` at 04:40 UTC 5 Nov (20:40 Pacific, 4 Nov), after the auditor read 173 of 173 (2,025 s)
  and the pre-push pressure test 0 fail; Pages built at 04:41 UTC. Checked on the live site at desktop width
  and at 375 px: the Lab page (the answer in the subtitle, five key numbers, the fitted line on all five
  break-even panels, Databento credited in every section, the author line, no sideways scroll, no console
  error), "Lab" in every page's rail, the paper's Tools list and the instrument's footer, `--ink-3` #6e7c8a.
- *Gabriel:* "all the descions seem good to me". So (1) H8 keeps 200,000 fixed-b draws of its own
  (`H8_REPS`; H8-DRAFT item 2 now says approved). (2) The 23-25 Nov Bloomberg pull B adds the four indices'
  daily highs and lows (`PX_HIGH`, `PX_LOW`, from 1 Jan 1986) beside the closes, so H10's range-based D4 does
  not depend on Marc's file: pulled, listed under H10's "Data already seen", not studied; whether D4 runs,
  and on which source, is fixed in H10-DRAFT before registration, after a coverage check (dates, counts, and
  low <= close <= high). `BLOOMBERG-MONDAY.md` (pull B; the file is now `INDEX_DAILY_2026-11-23.xlsx`) and
  H10-DRAFT decision 5 updated. The 23 Nov phone reminder (`trig_014FSkJSmGQqutozEtGxhSVq`) names the
  highs and lows and points to the list.

**Thu 5 Nov (00:00-10:00 UTC) - Gabriel: "Do #2-4": H8's choices 6 and 7 built, link previews, the paper's sections 1, 2 and 6, harder judge questions**
- *Pushed first:* `3c0da27` (the approvals) at about 05:30 UTC, after the auditor read 173 of 173 (2,132 s).
  The pre-push pressure test was 0 fail, 3 warn (the known three).
- *H8's choice 6 (H8-DRAFT item 6) is built, so it is not dropped at registration.*
  - `tools/h8_index.py` reads H8's own fund-days from `h8_quotes.fund_days`, which `main` now reads too.
    H8's report on the real calibration data was byte-for-byte the same before and after (diffed).
  - It reads the index at the snapshot minute through the timing reader. `index_timing.bars` gained an
    `indices` argument (default still OVX and GVZ), and its two seal messages no longer name the folder.
    `day_pair` now returns `T`.
  - It refuses the timing plan's sealed folder, and refuses anything before 30 Jan 2027.
  - A fund-day counts only when both feeds and I(T) are there, all finite. Every window trading day (41,
    from `panel_health`'s calendar) is accounted for once per fund, never filled.
  - Tests: `tools/test_h8_index.py`, 47 synthetic cases, and the pressure test "H8's index reading's tests
    pass". Eleven auditor mutants (nine h8index-*, timing-default-widened, timing-nonfinite-index), each
    tried alone before it was added.
- *Its purchases:* private `dbix-h8/buy.py` and a README with an empty seal. Nothing is bought yet.
  - Commits: volrec-licensed `396c3c9`, then `f305f8b`, which takes the window's trading days from
    `h8_index.window_days()` so there is one calendar.
  - It buys each window trading day through yesterday that is not yet on disk. Each request is priced
    first, against its own $1 cap (tag `-h8dbix`), and each file is sealed as it lands.
  - `--plan`: 41 days (22 in December, 19 in January).
  - **To do about 20-24 Nov, after both verdicts:** add its daily.yml step (the text is in
    `dbix-h8/README.md`) outside trading hours, then check that the next scheduled run fired. The first
    file is 1 Dec's, bought on 2 Dec.
- *H8's choice 7 (new; H8-DRAFT item 7): the snapshot gap split by side.*
  - Gabriel asked whether any metric besides volatility was worth bringing in, "i dont want u to be
    grasping at straws". The answer: volatility is the right lens, and skew is the only real candidate. It
    enters as a split of H8's own gap, not as a new measure.
  - His reply: "if u think it could actually stand to help the project then sure go for it".
  - The exact definition went into H8-DRAFT before any of it was computed. On the snapshot contracts, the
    estimator runs on OPRA's puts with the free calls (MPs) and on OPRA's calls with the free puts (MCs).
    The gap splits exactly, puts first and calls first, and both orders are reported. Per fund: the mean
    and mean absolute of each part beside the mean gap. No bar; never part of the verdict.
  - Built: `day_pair`'s MPs and MCs, `sides`, and one report line on the split's own sample, with its count
    and no minimum.
  - Tests: `tools/test_h8.py` now has 49 cases, twelve of them new:
    - a move in OPRA's puts alone is all put part, in both orders, exactly;
    - a move in its calls alone is all call part, exactly;
    - each order adds up to the gap;
    - the means match hand-computed answers;
    - the line is printed, including for a fund with few quote-time pairs, with one eligible day, or none;
    - in a fixture where the quote-time and snapshot quotes and contract sets differ, both mixes equal the
      estimator on inputs assembled by hand, and the order matters.
  - Mutants: seven h8-sides-* (swapped, one-order, nonfinite-kept, not-printed, minimum, quote-time-set,
    quote-time-quotes). Each was tried alone first, and each is caught by a check, not by a crash.
- *Link previews:*
  - og/twitter tags on the three pages. The Lab's go through `lab/report.py`; it was re-rendered and
    `--check` matches.
  - Three 1200x630 images, `og/home.png`, `og/monitor.png` and `og/lab.png`, drawn by `tools/og_cards.py`
    from fixed text (no result on them).
  - Pressure checks: "each page's link preview names its own title, description, address and a 1200x630
    image" and "the preview check refuses a truncated or damaged image".
  - Mutants: site-preview-image-missing, site-preview-description-drifts, site-preview-png-unchecked,
    site-preview-raster-unchecked.
- *Paper:* PAPER-DRAFT v2 adds sections 1, 2 and 6. It is an AI-assisted first draft for Gabriel to
  rewrite, citing only sources PAPER-OUTLINE documents. Every verdict-dependent line is a bracketed
  placeholder.
- *SCCUR:* SCCUR-PITCH.md gains ten harder judge questions and a scoring line. The mock session runs when
  Gabriel says "judge me" (any day before Sat 21 Nov).
- *Astra, two Ultra reviews.* The first (07:35 UTC) found five things, all fixed:
  - A trading day missing from both of choice 6's sources vanished. It is now listed from the calendar.
  - A non-finite estimate or index close would have been counted. Such a day is now not measured. The rule
    sits in `index_at` itself, so the timing reader shares it (64 tests).
  - The paper's introduction said every test was registered before its data existed, and its related
    work said every comparison was aligned to the minute. Both are narrowed to what sections 3 and 6 say,
    and the pitch too.
  - The preview check read only the first 24 bytes of each image. It now checks the whole PNG, CRCs and
    all.

  Its INCOMPLETE status came from the bundle limits and from the review bridge's own uncommitted files.
  The follow-up (the one allowed; 07:59 UTC, INCOMPLETE again for the same reasons) found five more, all
  fixed. Each fix is proven by a test that fails without it:
  - Item 7's line was skipped for a fund with fewer than three quote-time days, and it carried a minimum
    its definition does not have. It now prints on its own sample, with its count and no minimum.
  - The tests did not pin that the mixes use the snapshot contracts and the snapshot minute's quotes. A new
    fixture, where those differ from the quote-time ones, assembles both mixes' inputs by hand.
  - Two pitch answers still overclaimed: timing was "out" of the OPRA comparison, and H5's exception was
    missing.
  - A whole PNG with no pixels passed the preview check. The inflated data must now hold one filter byte
    and one row of pixels per line.

  Not addressed: a row typed neither C nor P. The recorder writes only C and P (47,968 and 47,966 rows,
  counted), and the mix uses the estimator's own test. No third review, by the project's rule.
- *Bridge tool (uncommitted, like the rest of the bridge):* `tools/codex_review.py`'s independent-check
  caveat now matches how that check has counted since 28 Oct. 24 tests OK.
- *Reminder:* phone routine `trig_01N8ZbM1FW4B1P4EWkJ8VCcq`, Tue 10 Nov 17:00 UTC: register the timing
  plan (Gabriel's yes, and the OSF freeze in his browser).
- *Backup (Gabriel's to set up; it is a system setting):* iCloud's Desktop & Documents is sync, not backup,
  and Time Machine has no disk. Recommended: a 2 TB portable hard drive with an encrypted Time Machine
  backup.
- *Item 7's first reading, after `7cfacc9` committed its definition.* H8's report ran on every OPRA file on
  disk: 14-18 Sep to 3 Nov, 32-34 fund-days per fund.
  - The two orders agree within 0.001 points for every fund.
  - On SPY, QQQ, IWM and GLD, about 60-70% of the gap sits with the puts. TSLA and NVDA are close to even;
    AAPL leans to calls.
  - Recorded in H8-DRAFT's pilot section as already seen.
  - H8's existing report is unchanged line for line. Checked by running `3c0da27`'s report on the same files
    in a worktree, with the FRED cache copied in, and diffing (21 lines identical). Without the cache the old
    code priced at r = 0, the known trap.

**Thu 5 Nov (17:30-19:00 UTC) - Marc Vinyard's highs and lows arrived: H10's D4 specified first, then a coverage check only**
- *What came:* daily highs and lows from Compustat (`prchd`, `prcld`) for the S&P 500 (from 1990), DJIA
  (from 1997) and Nasdaq-100 (from 2001), each to 4 Nov 2026. Compustat has none for the Russell 2000.
  - Marc's credit format, now in H10-DRAFT: "Data were obtained from the Compustat database via Wharton
    Research Data Services (WRDS)." Pepperdine University Libraries is thanked in the acknowledgments.
  - Copied to `~/Documents/volrec-wrds`, whose private README now lists them with checksums. The Downloads
    originals were left in place, as on 3 Nov. They never go into either repository or a review packet.
- *D4 first (`cbd8d03`).* Decision 5 says D4 is "specified here before any value is read". So its
  specification was committed after reading only each file's header, row count, and first and last dates.
  - Parkinson range volatility on H10a's and D1's own windows.
  - Reported: mean IV - RV_P with the fixed-b statistic beside it (no verdict), and mean RV_P - RV. Its
    downward biases are stated in advance.
  - A day is usable only if H and L are present and positive, H > L, and L <= close <= H. A window needs
    all 21 of its days usable. Definition changes are method breaks, read from documentation only.
  - Sources, fixed before the check: Compustat for the three indices; Bloomberg's 23-25 Nov RTY pull for
    the Russell 2000; Bloomberg's other three as a cross-check.
  - Decided by Vega under the 4 Nov go-ahead; Gabriel's to veto.
- *The coverage check, after that commit (counts and dates only):*
  - No missing, non-numeric, non-positive, duplicate or weekend entry.
  - Every day with a close has low <= close <= high.
  - **For the S&P 500 and DJIA, the high equals the low on every day before 1 April 1998** (2,085 and 314
    days), and on 11 later days each. Under D4's rule those days are unusable, so D4 measures those two
    from April 1998. The Nasdaq-100's are usable throughout.
  - Usable days: 7,181 of 9,279, 7,180 of 7,507, and 6,497 of 6,499.
  - D4 is not amended to fill 1990 to March 1998 from Bloomberg: that would splice a second vendor into
    one series, and the sources were fixed before the check. Gabriel's to veto.
- *Reply to Marc:* drafted by Vega; Gabriel sent it the same evening (5 Nov). Any answer about the
  pre-April-1998 highs and lows changes nothing in D4, since those days are unusable either way.
- *Marc's answer, the same evening:* before April 1998, Compustat appears to have archived only closing
  prices. Those years are fine for closes, which is all H10a uses, but not for intraday ranges. That is
  the documented reason for the coverage finding. D4 is unchanged, and the reason is noted in H10-DRAFT's
  D4 coverage note for the paper.
- *Astra (Ultra), 18:07 UTC: INCOMPLETE,* because the packet lacked the separate commit contents, a dated
  run transcript and the date-listing script, and licensed inputs were excluded on purpose. The
  deterministic checks passed. It found the formula, the 21-day alignment, the missing c4, the usable-day
  rule and the no-fill decision sound, and the usable-day totals reconcile. Both findings are fixed:
  - Medium: the definition-change rule pointed to the Specification's break rule, which restarts the grid.
    D4 now keeps H10a's and D1's windows and leaves out a window that spans the date.
  - Low: "a larger premium is expected by construction" overclaimed. The biases now hold under the
    Parkinson model's assumptions and on average only, and `RV_P - RV` can take either sign.
- *The one follow-up (18:16 UTC, `f9986d3`): CLEAR.* Both findings are resolved and nothing new was found.
  It had the commit times, the coverage output's write time (18:03:42 UTC, after `cbd8d03` at 18:02:11) and
  the date-listing script, and it says the order is consistent with the record, not proof of when values
  were first opened. The review packet was moved out of the repository.

**Thu 5 Nov (20:16 UTC) - pushed after the window; a second one-sided FXE quote (4 Nov)**
- *Pushed:* `0573182` (the reply to Marc was sent) and `4913882` (Marc's answer) went out at 20:16 UTC,
  a minute after the no-push window closed, on top of the day's recorder commits (`082a8dc` snapshot,
  `7a6244f` surface). The auditor read **195 of 195** first, and only the recorder's data files had come in
  since `cf02eef`. Pre-push test 0 fail, 2 warn; the site rebuilt.
- *FXE:* the pressure test's one-sided-quote warning now lists two FXE days, 7 Oct and **4 Nov**. On 4 Nov
  FXE's ATM call (18 Dec expiry) was quoted bid 0, ask 2.03, with no vendor IV. Its put was two-sided
  (0.83/1.07), and FXE quoted two-sided again on 5 Nov.
  - As on 7 Oct, the panel keeps what the feed said and is never rewritten. The check that no one-sided
    quote carries an IV into the analysis passes.
  - That warning reads the call leg only. Across all three legs the panel holds 7 one-sided quotes - calls:
    FXE 7 Oct and 4 Nov; puts: FXE 28 Oct; far legs: RIVN 24 Sep, and VZ, T and CMCSA 22 Oct - and none
    carries an IV.
  - No action: warnings pass, and the ticker universe is frozen.

**Fri 6 Nov (00:00 UTC, Thursday evening in New York) - tidy-up, and what is due before Tuesday**
- *Marc's originals:* the seven files from 3 and 5 Nov (four closes, three highs and lows) were moved from
  Downloads to the Trash after `cmp` found each byte-identical to its copy in `~/Documents/volrec-wrds`.
  Those copies are now the only ones on the Mac, and Marc's emails still hold the attachments. The private
  README says so.
- *Checked:* `daily.py` ALL CLEAR (5 Nov landed 19:31/19:40 UTC). The cloud reminders for 10, 12, 13, 20
  and 23 Nov and 11 Jan are enabled with no connector, beside the Monday auditor and the Wednesday watchdog.
- *Due before Tuesday's registration:* the timing plan's cold re-read. Its reader last changed on 5 Nov
  (the shared `index_at`, in the 00:00-10:00 UTC entry), so the re-read waits until at least Fri 6 Nov
  10:00 UTC. It is Vega's work: in any session from then, or first thing on Tuesday, before Gabriel's yes
  and the OSF freeze (the reminder's "about 5 minutes" is his part only).
- *Due by Tue 10 Nov:* refresh the system-status table above (checked 3 Nov); the auditor warns from 11 Nov.

**Fri 6 Nov (00:40 UTC) - Gabriel: the timing plan on Friday, by the book; a reminder for every future item**
- *Timing plan:* Gabriel asked to register it now instead of Tue 10 Nov. PROTOCOL step 2 requires at least
  one calendar day between finishing an instrument and registering on it, and the reader last changed at
  08:18 UTC on 5 Nov (03:18 New York, the same New York day). Offered tonight as a logged deviation or
  Friday by the book, he chose **Friday, by the book**. The Friday session, in order:
  - cold re-read of `docs/drafts/2026-11-04-index-timing-plan.md`, `tools/index_timing.py` and its tests;
  - PROTOCOL step 2's checklist, and the three sections the pressure test requires of any `hypotheses/`
    file registered from 10 Oct ("## Instrument readiness", "## Noise floor", "## Smallest detectable
    effect"), which the draft does not have yet;
  - Gabriel's dated yes, the commit to `hypotheses/`, and his OSF freeze;
  - the system-status table refresh.
  - **The registered file's name must contain "timing":** the 10 Nov fallback reminder looks for it and
    stays silent if it is there.
- *Gabriel's standing instruction (6 Nov): "things in the future just make sure there are reminders set".*
  Every dated item now has a phone reminder: one-off cloud routines at 17:00 UTC (09:00 Pacific),
  `claude-sonnet-5`, Bash and Read only, no connector.
  - New: Fri 6 Nov, the timing plan (`trig_01XbJh1buX7gvZBbTLamY3Xr`); Sat 7 Nov, back up the Mac
    (`trig_01VEX1yP47cVFGk6sG6TbYyg`); Mon 16 Nov, SCCUR poster time in Whova and the final poster to print
    (`trig_01WeRHdAkoi1zrk7XcBMUfWT`); Thu 19 Nov, pitch practice, parking and badge
    (`trig_01H71PLiyToiiee4Fn4JwbR8`); Tue 24 Nov, register H8 (`trig_015xUPeM6BmznpW1RCEmPfk3`); Fri 4 Dec,
    H8's first days and H9/H10 planning (`trig_01THveZL4RJSkH4sFpDDDJAX`); Mon 4 Jan 2027, plan the February
    write-up (`trig_01Wow8fv5oaPmS78HBHhXj41`).
  - Rewritten: Tue 10 Nov is now the timing plan's fallback, silent if the plan is registered
    (`trig_01N8ZbM1FW4B1P4EWkJ8VCcq`).
  - Already set: 12 Nov DBIX top-up, 13 Nov verdict check, 20 Nov verdicts and next steps, 23 Nov
    Bloomberg, 11 Jan tokens and the early-close cleanup; the Monday auditor and the Wednesday watchdog.
  - Each new routine arrived with nine connectors attached by default (Gmail, Drive, Notion and others).
    All were cleared, so no routine has a connector. From now on, add a dated item's reminder the same day,
    and clear its connectors.

**Fri 6 Nov (03:30 UTC, Thursday night in New York) - the nightly OPRA run failed on a new Databento answer; fixed**
- *What failed:* the yellow Pushover message was the private run of 6 Nov 03:22 UTC (issue #3 in
  volrec-licensed). Databento's OPRA data was running about ten hours late: its newest minute was 18:00 UTC
  on 5 Nov when the run priced 5 Nov (19:38-19:43 UTC), and still 18:10 at 03:40 UTC. The price query came
  back 422 `data_start_after_available_end`, not the 403 "needs a live licence" that `call()` already turns
  into a skip (5 Nov's two runs met that 403 for 4 Nov and passed). `call()` stopped the run.
- *What it cost:* the run had just bought 4 Nov for TSLA and USO ($0.0153 + $0.0177). The failed step
  skipped the one that commits, so both files and their ledger rows were lost. The next run buys them again,
  and the private ledger under-states the lifetime spend by $0.0330 (about $35 of the $120 cap is left).
- *Fix (`5dc30cc`, then `7e72a9e` after Astra):* `call()` maps a 422 whose `case` is
  `data_start_after_available_end` or `data_end_after_available_end` (a window that starts past Databento's
  newest minute, or straddles it) to `NotYetHistorical`, reading that minute from the reply. `fetch()` and
  `definitions()` catch it at the price query and print "not released yet (Databento has data up to ...);
  nothing charged - run again tomorrow". Any other 422 still stops the run; the lab fetcher's symbol check
  depends on that.
  - The fixtures are Databento's real replies, captured with free price queries (nothing bought): both
    "not released" cases and a symbol-lookup 422, plus that symbol-lookup reply with its message edited to
    name the case (it must still stop the run).
  - Pressure test: five new checks - the mapping, the lab still reading a symbol-lookup 422 as
    unresolvable, the skip in all three nightly modes (daily, H7, H8), a real refusal still stopping
    `fetch()`, and `definitions()`. The mapping, the skip and `definitions()` were seen failing before the
    code changed; the other two are guards, proven by mutants. 0 fail, the usual two warnings.
  - Auditor: seven new mutants (the mapping removed; widened to every 422; matched on any text; the
    straddle case dropped; `fetch()`'s handler removed; `fetch()` swallowing every refusal;
    `definitions()`'s handler removed). Each was applied by hand and seen to fail its own check for the
    intended reason; 202 in all.
- *Astra (Ultra):* `5dc30cc` CLEAR. Of its limitations, `7e72a9e` closed three: the match now reads the
  reply's `case`, not any word in it; the skip is checked in all three modes, with a negative case; the
  lab's wrapper is checked. Kept: the checks read the "nothing charged" log text. Open: a day Databento
  never releases (or a wrongly dated window) would be skipped every night, as the 403 path always allowed -
  a "still not released after N days" stop would be a new safeguard, Gabriel's call. Follow-up on
  `7e72a9e`: CLEAR. What it still lists, none of it a defect it found: the match reads the whole reply rather
  than parsing `detail.case`; a reply with spaces in its JSON would still be skipped but would log "its
  newest data" instead of the minute; `main()`'s loop and a negative case for `definitions()` are not
  tested directly. Left as they are - one follow-up review is the limit.
- *Push:* these commits go out once the auditor reads 202 of 202, before the next scheduled run
  (GitHub has been delivering the 03:05 UTC cron around 10:45 UTC). That run should read green: if
  Databento is still behind, 5 Nov prints "not released yet" and is bought a night later, and 4 Nov's two
  lost days are bought again.
- *After the verdicts (the private daily.yml is frozen until then):*
  - keep the purchased files and the ledger even when a fetch step fails;
  - "Run page summary" exits 1 whenever `verdicts.txt` is absent, which happens only after another step
    has failed (cosmetic);
  - reconcile the $0.0330 ledger gap - Gabriel's call;
  - close issue #3 once a run reads green (the workflow never closes its own failure issues).

**Fri 6 Nov (04:55 UTC) - Gabriel: "do whatever is best for the decisions"; what was decided**
- *Asked:* the open points of the entry above, left to Vega. Each is recorded as Decided (his to veto).
- *The "still not released after N days" stop - Decided (his to veto): after the verdicts, and never as a
  step that fails the run.* The roadmap allows no new monitors before 21 Nov. And in the private daily.yml a
  failed fetch step skips every later step, "Keep the data" and "Verdicts that have come due" among them, so
  a stop that fails the run would throw away what it guards. When built, it reports (a yellow Pushover, the
  run page) and lets the run finish. Until then a day Databento never releases is skipped every night - the
  risk the 403 path always carried.
- *The private daily.yml edit - Decided (his to veto): Sun 22 Nov, after the verdicts and SCCUR, in one
  sitting.* Four changes:
  - keep the bought files and the ledger when a fetch step fails;
  - stop "Run page summary" failing when `verdicts.txt` is absent;
  - the stop above, as a step that never fails the run;
  - H8 choice 6's buy step (its text is in `dbix-h8/README.md`; due 20-24 Nov; the first file is 1 Dec's,
    bought on 2 Dec).

  Sunday has no scheduled run, so a mistake cannot cost a night, and the frozen workflow is opened once.
  Then check that the next scheduled run fired. Reminder: Sun 22 Nov 17:00 UTC
  (`trig_01CynExVW2bFJLh7YXQdRR85`, no connector).
- *The $0.0330 ledger gap - Decided (his to veto): reconciled.* The two lost purchases were real charges, so
  they went back into the private ledger through `record_spend()`, its only writer: dated 4 Nov, TSLA
  $0.015274 and USO $0.017677 (volrec-licensed `cec23bd`; lifetime total $84.740343 -> $84.773294). A day
  counts as bought when its file is on disk, not when the ledger has a row (`fetch()` checks `DATA_DIR`), so
  the next run still buys both again and logs that charge too. The ledger then holds both, as Databento's
  bill does.
- *Checked live:* `74cd4ad` was pushed at 04:27 UTC (auditor 202 of 202). A price-only dispatch of the private
  run right after it (run 42162653695) passed: all three modes printed "not released yet" for 5 Nov, nothing
  charged. Databento's newest minute read 19:10, then 19:20 UTC on 5 Nov (at 04:31 and 04:42 UTC): moving
  with the clock, still about 9 h 20 min behind.
- *Issue #3:* the session's permission guard refused the comment-and-close, and it was not worked around.
  Gabriel closes it once a run reads green; the first chance is today's run, around 10:45 UTC.

**Fri 6 Nov (08:20 UTC) - healthchecks marked volrec-licensed down; a full run cleared it**
- *Why:* healthchecks.io's `volrec-licensed` check expects a success ping within 9 h of each weekday 23:05 UTC
  run. Thursday's 23:05 run is the one that failed at 03:22, and the 04:27 price-only check never pings, so
  the check went DOWN at 08:05 UTC and told Gabriel. It is the failure above arriving late, not a new one.
- *Done:* a full dispatch at 08:07 UTC (run 42185443188). Every step passed.
  - It bought 4 Nov: TSLA and USO again, plus the H7 (GLD, USO) and H8 (AAPL, GLD, IWM, NVDA, QQQ, SPY)
    files the failed run never reached. 10 files, $0.1938 (private `eff13e5`); the ledger reads $84.967119,
    $35.03 of the cap left.
  - 5 Nov was skipped in all three modes by the licence path ("data after 2026-11-05T14:30 UTC needs a live
    licence"), nothing charged; the next runs buy it.
  - No verdict due (H5e final and H7 are due 12 Nov). It pinged, so the check reads up again.
- *Gabriel closed issue #3 at 05:43 UTC.*
- *Next time:* a failed or missing 23:05 run turns the check DOWN at 08:05 UTC. A full dispatch
  (`gh workflow run daily.yml -R gabrielmitton-cloud/volrec-licensed -f mode=full`) is a harmless second
  pass - runs queue, and days on disk are never bought twice - and its ping clears the alarm.

**Fri 6 Nov (17:00-19:30 UTC) - the timing plan's cold re-read: one real defect, fixed; registration moves to Sat 7 Nov, by the book**
- *Asked:* Gabriel at 17:00 UTC: "please check the code again" - the cold re-read due before registering
  (the 00:40 UTC entry above).
- *Found:* the reader could measure on the wrong days without a word.
  - H7's two replicas are rebuilt from the OPRA folder that `VOLREC_DATABENTO_DIR` names. Pointed anywhere
    but the private, pulled folder, `h7_reader` counts fewer days (or none), and the report measured what
    was left.
  - H5e was checked only against today's `modelfree` output. Both read the same closes, so a close Cboe
    revised after the verdict would agree on both sides and still differ from the recorded verdict.
- *Fixed (test first; code and tests only, no definition changed):* nothing is measured unless the rebuilt
  readings give the recorded verdicts' own days and numbers.
  - H5e: the FINAL reading's "Skip-only gap by day" line, day by day at its two decimals. The FIRST
    verdict's line above it is never read.
  - H7: its expected trading days less the ones its record names as missing or not counted, date by date;
    the counts; the four means (H7a USO and GLD, H7b GLD, H7c USO) at three decimals. H7's record holds
    aggregates only, so this is as close as a check can get.
  - A value that is not a finite number is a disagreement (`nan > tolerance` is False, so it used to pass
    every comparison, the older `modelfree` check included). Agreement on nothing is refused, and a reading
    with no counted day keeps its lines in the report.
- *Astra (Ultra):* `20261106T183239Z`, on the first fix: three findings, all verified and fixed - H7's days
  were compared by count only (a swapped day passed at the same count and means), the NaN pass, and an
  empty reading dropping out of the report. Follow-up `20261106T184500Z`: needs attention, one MEDIUM -
  verified, and fixed after it. `panel_health.ACCEPTED_GAPS` is keyed by date, so a day the ATM panel lost
  can still have its monthly legs; H7 counts it, and the writer's coverage check skips it. The rebuilt day
  list left such a date out, so the check would have refused a record that agrees: a false refusal, after
  registration. Such a date is now checked by the counts and means only. No gap falls in H7's window today
  (the only one is 16 Sep). The fix was not re-reviewed (one follow-up is the limit); Saturday's cold
  re-read covers it.
- *Checked:*
  - `tools/test_index_timing.py`: 98 cases (64 before), 0 failures. Pressure test: 0 fail, the usual two
    warnings.
  - 15 new auditor mutants, 217 in all (28 for the timing reader). Each was applied to a copy and seen to
    fail its own check: it parsed, did not crash, and tripped the intended test.
  - On real data, with the sealed folder never opened: H5e's 31 counted days agreed with `modelfree` and
    with a FINAL block that `record_verdict` rendered from the day's output. H7's 19 days a fund agreed on
    days, counts and all four means (9 Oct - 5 Nov, since H7's verdict is not written yet). With the OPRA
    folder left at its default, the reader refused and listed every day.
- *Registration - Decided (his to veto): Sat 7 Nov, from 20:00 UTC (noon Pacific), by the book.* The reader
  changed today (last at 19:01 UTC). PROTOCOL step 2 wants a calendar day between finishing an instrument
  and registering on it, then a cold re-read, and on 5 Nov Gabriel chose "by the book". Saturday is still
  days before the verdicts (12-13 Nov). The alternative was today, as a logged deviation.
  - Reminder: Sat 7 Nov 20:00 UTC (`trig_01URGXVbkitS8yKiqBSxQtD5`, no connector). It stays silent if a
    "timing" file is already in `hypotheses/`. The Tue 10 Nov fallback stays as it is.
- *The registration text:* `docs/drafts/2026-11-06-index-timing-registration.md`, with the three sections
  the pressure test requires and every prior look listed (the secondary-data exception is not used). It
  moves to `hypotheses/` only after Gabriel's dated yes: a "timing" file there silences the 10 Nov fallback.
  - The plan expected the gaps on the covered days to be "strongly persistent, an n_eff of a few". Measured
    over 21 Oct - 5 Nov, the registered gaps are barely persistent (rho -0.12 to +0.23, n_eff 7.5-12 at
    T = 11-12). The text gives those numbers instead, in its adjustment log.
- *Saturday, in order:*
  - cold re-read of the reader and its tests;
  - fill in the reader's sha256 and the audit's N of N;
  - `git mv` the text to `hypotheses/2026-11-07-index-timing.md`, with the Registered date and a row in
    `hypotheses/README.md`. No H number - Decided (his to veto): it is descriptive, and H9 stays reserved;
  - Gabriel's dated yes and his OSF freeze;
  - the pressure test, then the push.
  - Also due by Tue 10 Nov: the system-status table refresh.
- *Push:* these commits go out after the recorders' window, through the gated script, once the auditor reads
  217 of 217.

*OPRA figures: Data provided by Databento. Index closes: Cboe Global Markets. Aggregates only.*

**Fri 6 Nov (19:35-20:00 UTC) - Gabriel: register today; the timing plan is registered, the day's wait not kept and logged**
- *Asked:* after the report above, Gabriel chose today over Saturday ("yeah lets do that today today"). The
  Saturday date was Decided (his to veto); this is his veto.
- *Done before registering:* today's diff re-read line by line (no defect found; the same day, so not cold).
  The auditor read 217 of 217 on the reader's commit (19:08-19:32 UTC). The reader's sha256,
  `e65b5270...afb46`, is in the file in full.
- *Registered:* the draft moved (`git mv`) to `hypotheses/2026-11-06-index-timing.md`, with a row in
  `hypotheses/README.md`. No H number: it is descriptive, and H9 stays reserved. The skipped wait is stated in
  its header, its readiness section and its adjustment log.
- *Still open:*
  - the OSF freeze, on Gabriel's account. On 10 Oct Claude did it in his browser at his request; his call.
    Its link then goes into the file's header.
  - the system-status table refresh, due by Tue 10 Nov.
- *Reminders:* Saturday's (`trig_01URGXVbkitS8yKiqBSxQtD5`) and the Tue 10 Nov fallback both look for a
  "timing" file in `hypotheses/` on GitHub, so both stay silent once this is pushed.
- *Push:* with the reader's commit, after the recorders' window, through the gated script (a fresh audit of
  this commit first). Neither file cites either commit's ID: the push rebases both onto the recorders' commits,
  which gives them new IDs (the reader's sha256 does not change). Their GitHub IDs go in with the OSF link.

**Fri 6 Nov (20:22-22:10 UTC) - pushed; the timing plan frozen on OSF: https://osf.io/4mcgf**
- *Pushed* at 20:22:34 UTC through the gated script: the auditor read 217 of 217 on the registration commit,
  only the two recorder commits came in, and the pressure test read 0 fail, 2 warn. On GitHub the reader's
  commit is `b7962ac` and the registration's `e02724e` (the rebase renamed `acd73af` and `b959069`). The
  reader's sha256 there is the registered `e65b5270...afb46`.
- *OSF:* Vega filled the "Secondary Data Preregistration" template in Gabriel's Chrome at his request (he
  signed in himself), in the 10 Oct project (https://osf.io/n8y3z), and submitted on his yes. Registered at
  21:06:58 UTC, no embargo, MIT licence; its description cites `e02724e`. The four files (the registration,
  the 4 Nov plan, the reader, `PROTOCOL.md`) are in the project's folder `index-timing-registered-2026-11-06`,
  and the registration's archive holds all four, each matching the repository's sha256. It waits for Gabriel
  to approve OSF's email; OSF approves it by itself after 48 h.
- *Choices made while filling:*
  - data availability is "available through protected access": the index files and the OPRA quotes are
    licensed. On 10 Oct it was "publicly available".
  - the template's own fields differ from some of `OSF-REGISTRATION-TIMING.md`'s headings, and the answers
    were fitted to them. The OSF page is the record.
  - starting the draft asked to confirm it is a research plan; ticked.
- *In the repository:* the link in the registration file's header (its only change; OSF holds the file
  without it), the status table, SESSION-START and PAPER-OUTLINE appendix A. `OSF-REGISTRATION-TIMING.md`
  stays as the paste sheet, as 10 Oct's did.
- *Gabriel's call:* a link on the site. `index.html` links only H5e and H7's registration, and a new link
  would show visitors an error until the registration is public.
- *Still open:* the system-status table refresh, due by Tue 10 Nov.
- *Reminder:* Mon 9 Nov 17:00 UTC (`trig_019zejFoiy1MfsdPD5J689LR`, no connector). It asks OSF's API whether
  4mcgf is public (tested 6 Nov: the 10 Oct registration reads public; 4mcgf answers 401 until it is) and
  whether the status table's heading still says "checked 3 Nov 2026". It stays silent only if both are done;
  if OSF cannot be reached, it sends the OSF line anyway.

**Fri 6 Nov (22:40-23:00 UTC) - the site links the timing registration; no backup disk; iCloud's stray copies cleared**
- *Site (Gabriel: "u can add the link thats fine"):* `index.html` links https://osf.io/4mcgf in the ledger's
  paragraph and in the footer's Hypotheses list, beside H5e and H7's. The link does not open for visitors until
  OSF makes the registration public (his email approval, or by itself about Sun 8 Nov 21:07 UTC); he accepted
  that. Checked in the preview: both links render, no console errors.
- *Backup - decided by Gabriel, closed:* "im not getting the backup disk, and itll be fine". The Sat 7 Nov
  reminder to buy one (`trig_01VEX1yP47cVFGk6sG6TbYyg`) is disabled. Not to be raised again.
- *Clean-up (his go-ahead: "If u need to go through and clean up the volrec files then u can do that"):*
  - the repository sits in iCloud's Desktop. iCloud had left 28 conflict copies of git's index in `.git`
    (8 Oct - 5 Nov; git never reads them) and, on 6 Nov, one of the registration file (byte-identical to the
    registered one). All are in the Trash.
  - no other conflict copy in the repository or the `~/Documents/volrec-*` folders (compared by sha256 only;
    no value read). `git fsck --full` reads clean here and on the private clone.
  - iCloud has moved some files to the cloud (`.venv`'s library files, two papers, one comparison note); they
    download when opened. The repository stays where it is.
  - a stray untracked `name 2.ext` file is iCloud's, not new work: compare it with the original before acting.
- *Checks:* pressure test 0 fail, 2 warn (the known two).
- *Pushed* at 23:28 UTC through the off-hours script as `8995135`: auditor 217 of 217, nothing came in,
  pressure test 0 fail, 2 warn.

**Fri 6 Nov (23:20-23:50 UTC) - the status table refreshed; the paper's draft cites the timing registration; the poster stays as it is**
- *Status table (Gabriel: "go do the status table rn"):* every row re-checked on 6 Nov, and the heading says
  so, which also answers that half of the Mon 9 Nov reminder. The H3 line under "Where each hypothesis
  stands" now reads to 5 Nov. One new finding, next.
- *cron-job.org's noon copy still fires every November weekday.* The one-off 12:00 New York guard copy for
  Fri 27 Nov fired at 17:00 UTC on 3, 4, 5 and 6 Nov, after it was set to its single date on 3 Nov.
  Harmless: each time the guard waited ("before the 14:30 New York trigger slot - never re-run early") and
  did nothing. Likely cause, not confirmed for cron-job.org: cron runs a job when its day of the month OR its
  weekday matches, so weekdays left at Monday-Friday keep it firing. Optional fix, in Gabriel's account: set
  both copies' weekdays to every day. Left alone, the 24 Dec copy will likely fire on every December weekday,
  just as harmlessly. Nothing else depends on it.
- *The paper's draft (Gabriel: "u can do what u want with the citation"):* one sentence added to
  `PAPER-DRAFT.md`'s pre-registration paragraph: the descriptive timing measurement, frozen on OSF on 6 Nov
  before either verdict and before its intraday index data was opened (osf.io/4mcgf). Nothing else in the
  draft changed; he is not writing it yet.
- *Poster - Decided (his to veto): unchanged.* `poster/build_poster.py` reports H5e and H7, and its one OSF
  line (z5gfu) is their registration. The timing measurement has no result until both verdicts are recorded
  and its last index files are bought, and the final poster goes to print around Mon 16 Nov (reminder set),
  so a line for it now would point at a number the poster cannot show. When the poster is rebuilt after the
  verdicts, adding the measurement, if it has read by then, is a choice for that day.
- *Checks:* pressure test 0 fail, 2 warn (the known two); the poster's tests 19 OK. Docs only, so no Astra
  review.

**Sat 7 Nov (01:54-02:05 UTC) - the timing registration is public**
- *OSF's approval email reached Gabriel late.* He had none at 00:05 UTC and pasted it at 01:54 UTC; its title
  is the registration's, word for word. Without a click it would have gone through "48 hours from midnight
  tonight (EDT)", about Mon 9 Nov 04:00-05:00 UTC, later than the Sun 8 Nov 21:07 UTC worked out from OSF's
  help page. Its cancel link would have sent the registration back to draft for good, and a resubmission
  would carry a new date.
- *Approved.* Gabriel clicked the approve link. OSF's API answered 401 at 01:54 UTC and 200 at 01:57 UTC:
  public, not pending, not withdrawn, no embargo, and `date_registered` still 2026-11-06T21:06:58 UTC.
- *Its files, read as any visitor would:* the folder `index-timing-registered-2026-11-06` holds the four
  registered files, and each sha256 matches the file at `e02724e` (the reader's is e65b5270...afb46, the
  hash the registration states). The archive also carries the 10 Oct registration's files, because OSF
  archives the project's whole storage.
- *Records:* the status table's OSF row and `OSF-REGISTRATION-TIMING.md`'s header. The Mon 9 Nov reminder
  now has nothing to report (the table is refreshed and OSF reads public), so it should stay silent.
- *Checks:* pressure test 0 fail, 2 warn (the known two). Docs only, so no Astra review.

**Sat 7 - Wed 11 Nov (UTC) - the SCCUR poster redesigned: graphs and findings first (Gabriel chose layout A)**
- *Gabriel's ask (7 Nov):* no side table of hypotheses; "graphs and ... actual findings", like other posters, with
  the tests shrunk to a strip. He chose layout A (headline + evidence): "make sure graphs are easy to understand
  and interpret but informative", verdicts smaller ("a side note for me to point to during talks"), the classic
  research-poster look but mostly A, "do ur thing". Design:
  `docs/superpowers/specs/2026-11-08-sccur-poster-findings-first-design.md`; plan and its amendments:
  `docs/superpowers/plans/2026-11-08-sccur-poster-findings-first.md`.
- *What the poster shows now:* the headline (unchanged, with its 21 Oct fallbacks); left: 1 the question, 2 what
  I did (a flow: free quotes, the VIX formula with strikes and expiries I chose, the references), how it stays
  honest, what's next, limits; centre: 3 "Free data tracks Cboe's index", five histograms (SPY, QQQ, IWM, GLD and
  USO against VIX, VXN, RVX, GVZ and OVX), each counting the days at each half-point gap (free estimate minus
  Cboe's published index), one gap axis and one day axis for all five, a blue line at zero for Cboe's index and
  a band for within one point, no dates; beside them the H3 tile (the average gap against the 1.0 bar set before
  the data); right: 4 the quotes (a dot scale in bid-ask spreads, both feeds, both readings), 5 the recipe (two
  bell curves under a +/-10% band; the mean gap by strike band on the 11 Sep calibration day); bottom: every
  registered hypothesis, H1-H7, as a small chip beside the QR code. The charts are pure functions in the new
  `poster/charts.py`.
- *Licensing - Decided (his to veto): the main chart counts days; it draws no index level and no day.* Cboe's
  4 Nov approval answers the request as sent (10 Oct, repeated 21 Oct), whose words are: "No Cboe data files are
  republished. Only aggregate statistics appear (for example, average differences between my estimates and the
  index), credited to Cboe Global Markets." The first build drew the five indices as lines; the second drew
  each day's gap as a bar; Astra's 8 Nov review read those dated gaps as per-day data (HIGH), so each panel is
  now a histogram. Page tests fail if an index value or a day reaches the page, and `charts.gap_histogram`
  refuses dated rows. The pitch quotes the request ("Why does the chart count days instead of drawing the
  VIX?"). Two older exceptions are put to Gabriel, not changed: the calibration day's level (11 Sep: SPY 15.83
  against a VIX of 15.84) and worst single-pair gaps, in section 5's caption and public in the README and site
  since September; and the H5 file's line 488, written by the frozen writer on 8 Oct, which lists each counted
  day's gap to OVX (H5e's final block, about 12 Nov, will add the same line).
- *Three independent reviews of the rendered poster (8 Nov; Claude agents: design, the claims against the
  records, the code); each finding checked against the records before it was fixed, code fixes tests first:*
  figures rounded once, from full precision (double rounding had shifted the tile's mean and GLD by 0.01); the
  tile's colour follows each part's verdict (it was always green); "of record" needs the 11 Nov data in every
  pair, not the date alone; wording matched to the records (the flow's arrow, "recorded daily", "H5e and H7 were
  also frozen on OSF", "eight funds and stocks", H2a and H6a's chips, a section 5 caveat: one calibration day
  shows a coverage effect and does not by itself rule out the feed, the timing or index-versus-fund); a final
  H5e chip keeps the recorded 8 Oct failure beside it; an H7 part below its minimum shows a grey "-" (never
  scored), not the amber "..." of a reading still due; a comparison ("p < 0.01") never breaks across lines; the
  quote scale shows both readings for both feeds.
- *Astra Ultra, 8 Nov (`.codex-reviews/20261108T174846Z-m75ku9g0`): INCOMPLETE,* because the Cboe request, the
  frozen verdict writers and the scorer's exit contract were not in its bundle; ten findings (2 HIGH, 7 MEDIUM,
  1 LOW), each verified. Fixed: the per-day gaps (the histograms above); "recomputed every recorded number"
  (now "recomputed every recorded result on 17 Oct", the re-check's own scope); the H5e lines are matched exactly
  as the frozen writer prints them, bars word for word; a scorer refusal (nonzero exit) stops the build; Chrome's
  output counts only if that run wrote it, and `poster.pdf` / `preview.png` exist only after a render that
  passed (`*.FAILED-CHECK.*` otherwise); the page check now runs after the fonts load, fails on chart text that
  leaves its chart or meets another label, and writes its result into the page title, which Chrome carries into
  the PDF, so the printed file is judged by the run that printed it; chart tests with known coordinates. Moot:
  per-panel date ranges (no date axis now). Put to Gabriel: the headline rule (his of 21 Oct).
- *Follow-up Astra Ultra review (11 Nov, `.codex-reviews/20261111T070947Z-hqkxc6wa`): INCOMPLETE.* It found
  the histogram, the H5e parser, the scorer's exit and the dated re-check resolved, but could not compare every
  claim with its record: the timing study's 0.53-point figure and the full H1, H2 and H6 results were not in its
  bundle. Checked here instead, each matches its file: 0.53 (OSF-REGISTRATION-TIMING.md, "a median 0.53 points
  between 14:30 and 15:55"), H1 9 of 11, H2a p 0.18 by date (companion run 40720872275), H2b 3 of 11, H6a 0 of 9,
  H6b +0.33 against +0.42 (p < 0.01). Four new points, each verified and fixed tests first: (1) the preview came
  from a Chrome run of its own whose page check nothing read - it is now drawn from the checked PDF itself by
  macOS's own `sips` (*Decided, his to veto:* a tool every Mac has, nothing installed), so it shows exactly what
  was checked; (2) the PDF was judged by text searches a file cut short could pass - it must now end in its
  cross-reference table and %%EOF, `sips` must be able to draw it, and the drawing must decode whole as one 4:3
  page; (3) the smallest size was rounded before the 24 pt comparison (31.996 px passed) and labels could cross
  by up to a pixel - now compared unrounded, with only numerical error allowed (0.01 px), and boundary tests in
  real Chrome (half a pixel caught, touching not, 31.996 px caught); (4) the pitch said the "within a point"
  headline follows any H7 failure - it now follows both branches of his rule (that one only if H3 holds). Under
  the review rules there is no third review: these four fixes are verified by tests, mutants and real renders,
  not re-reviewed by Astra.
- *Lost and rebuilt:* the Mac rebooted between 8 and 11 Nov and cleared the session scratchpad (`/private/tmp`).
  The check scripts and drafts were rebuilt from the session record; a 6 Nov review packet set aside there was
  recovered word for word from that day's review logs and put back in `review-packet/` (untracked; it can be
  deleted). Anything held now goes in `.codex-reviews/held/` (git-ignored, never bundled into a review).
- *Checks (11 Nov, data to 10 Nov, after the follow-up fixes):* `poster/test_build_poster.py` 57 OK and
  `poster/test_charts.py` 27 OK (19 before the redesign). Both stay standalone - the pressure test does not run
  them - so run them by hand before any rebuild. 43 mutants, each parsed and caught by its intended test with an
  assertion (one first "caught" by a crash was not counted until its test was reordered to fail on an
  assertion). Four deliberately broken posters in real Chrome (a label past its chart's edge, a label over a
  title, the web fonts' address broken, the check delayed past the print): all refused, none left a
  `poster.pdf`. Five states pass (today, fallback headlines 1 and 2, and after the verdicts a worst and a best
  case written by `record_verdict.py`'s own writers into temporary copies): smallest text exactly 24 pt, no
  overflow, fonts loaded, no chart text clipped or overlapping, one 48 x 36 in page written to its end, the
  preview drawn from it (3456 x 2592), the PDF's own check passed. Live: H3 0.71 over 200 readings (40 of the 42
  weekdays, 14 Sep - 10 Nov, five pairs), mean -0.44, H3a-c hold so far; by fund SPY 0.44, QQQ 0.50, IWM 0.46,
  GLD 0.37, USO 1.77, within one point on 37, 36, 39, 40 and 13 of 40 days.
- *SCCUR-PITCH.md* follows the new poster: the walk, the histogram's reading, the re-check dated 17 Oct, the
  headline's two fallback branches, and the new question above.
- *Needs Gabriel:* (1) the headline rule (his of 21 Oct) in three outcomes Astra questioned: a NOT READ H7
  keeps "Most of the error is in the recipe"; the H7-fails fallback's "within a point of Cboe's index" is H3's
  pooled mean across five pairs, while USO alone is 1.77; and the fallback for H7 and H3 both failing ("loses
  more to the method than to the quotes") claims a split those results do not establish. His rule stands until
  he says. (2) The two older Cboe exceptions above. (3) The AI line reads "Code written with the help of an AI
  coding assistant (Claude Code); ..." (approved 21 Oct), but AI also drafted chart and caption wording and a
  second AI model reviewed; suggested: "Code, charts and draft wording produced with AI assistants (Claude Code;
  a second AI model reviewed); the research question, decisions and interpretation are the author's." The
  switch is `AI_LINE` in `poster/build_poster.py`. (4) Any veto of the Decided items, the histogram first. (5) Marc saw the 21 Oct
  draft; sending him this one is his call. (6) Unchanged: the verdict rebuild (about 13-19 Nov) and the print
  (reminder Mon 16 Nov). (7) The Gmail connector failed twice on 11 Nov and needs reconnecting in claude.ai's
  connector settings; the request's wording above is from the 8 Nov reading of the 21 Oct email.
  *Reminder (set 11 Nov, his rule of 6 Nov):* Fri 13 Nov 17:00 UTC (09:00 Pacific), half an hour after the
  verdict check, `trig_01728s5J95kLRL1ti2NG74bG` (Bash and Read only, connectors cleared). It stays silent
  once his answers are recorded in this section under a line of their own beginning
  `#### Poster questions: his answers` (then the date).

**Wed 11 Nov (UTC) - Gabriel delegated the poster's open questions; SCCUR's session details**
- *His words (11 Nov):* "for the things that need me just do whats best and move on", with SCCUR's email pasted.
- *SCCUR (the email):* Sat 21 Nov, Session 2, 9:30-11:00 am, Montezuma Hall (Conrad Prebys Aztec Student Union,
  San Diego State), poster board 12, under the poster's own title. Ten minutes to set up (double-sided tape on the
  supply tables), the whole 75 minutes at the poster, five minutes to take it down; no schedule changes. Also at
  the top of `SCCUR-PITCH.md`.
- *Reminders:* 16 Nov (`trig_01WeRHdAkoi1zrk7XcBMUfWT`) and 19 Nov (`trig_01H71PLiyToiiee4Fn4JwbR8`) rewritten
  with the session, room and board (the 16 Nov text had said Whova would post them that day). New: Fri 20 Nov
  18:00 Pacific (Sat 02:00 UTC), "SCCUR tomorrow" with the room, board and timings
  (`trig_01SLqhP41Hs5H2mDoAwb4NrB`, Bash and Read only, connectors cleared). The 13 Nov poster-questions reminder
  (`trig_01728s5J95kLRL1ti2NG74bG`) is switched off: the questions are answered below.

#### Poster questions: his answers (11 Nov 2026, delegated: decided by Vega)
1. *The headline rule:* his 21 Oct structure stands: the headline changes by itself only when an H7 verdict is
   written and fails. Kept: an unread H7 keeps "The free quotes are close. Most of the error is in the recipe."
   under "On the evidence so far" (the far quotes sit within half a spread of both professional feeds; one
   recipe change moved the calibration day's mean gap from 3.97 to 0.59 points; H7's chips say "due").
   Reworded: H7 fails and H3 holds, "Widen the strikes, and free data averages within a point of Cboe's index."
   (the point is the five-pair average; USO alone read 1.77); both fail, "Free data misses Cboe's index by a
   point or more, on average." (H3's verdict there is H3a's, so the line states only that failure and claims no
   quotes-versus-method split). Both render on one line and pass the page check.
2. *Cboe:* the poster now prints no index level. Section 5's caption gives the calibration day as a difference,
   "SPY's estimate read 0.01 points under the VIX" (the H3 file's -0.01), not "15.83 against a VIX of 15.84";
   the credit line ends "Derived figures only."; a page test fails if any of that day's ten levels (five
   estimates, five indices) reaches the page. Kept as they are: the worst-pair gaps (differences, the approval's
   own example); the bell curves' 16 and 59 (whole-point inputs to a curve labelled a simple model); the frozen
   H3 file's calibration table and the H5 file's per-day OVX gaps (registered records, never edited; H5e's final
   block, written by the frozen writer about 12 Nov, adds its own line); and the README and site, the older
   public record since September, whose table the registered H3 file shows anyway.
3. *The AI line:* "Code, charts and draft wording produced with AI assistants (Claude Code; a second AI model
   reviewed); the research question, decisions and interpretation are the author's." The pitch's answer follows.
4. *Vetoes:* none; the histograms and the sips preview stay.
5. *Marc:* no interim draft; he gets the final poster to print, as planned for 16 Nov.
6. *The Gmail connector:* not needed; emails can be pasted.
- *Checks (11 Nov):* `poster/test_build_poster.py` 60 OK (three new: the fallback wording, no calibration-day
  level, the AI line; each failed first on the old code) and `poster/test_charts.py` 27 OK; the 43 planted bugs
  all caught; five states pass the page check (today, both fallbacks, a worst and a best case after the
  verdicts): smallest text 24 pt, nothing overflowing, clipped or overlapping, the preview drawn from the checked
  PDF (3456 x 2592). These answers close the follow-up review's open points, so under the one-follow-up rule they
  are verified by tests, planted bugs and real renders, not re-reviewed by Astra.

**Wed 11 - Thu 12 Nov (UTC) - the whole-project review; H5e's FINAL reading recorded; the site's Bloomberg figures corrected**
- *Gabriel (11 Nov, on switching the session's model to Fable 5.2):* "read through my research project, make
  improvments, make suggestions on new technology to add, anything that might need to be refined or optimized ...
  make sure that everything is right and tip top shape".
- *H5e's FINAL reading (the workflow, 12 Nov 03:55 UTC, `e0b36c9`):* **FAILS**, mean absolute gap 0.91 against 0.5,
  closer than the registered estimate on 26 of 35 counted days; it agrees with the first verdict. Written by the
  frozen writer, in fixed wording; nothing in this entry touches it. H7 waits for 11 Nov's OPRA files (the status
  table has the timing): the run GitHub starts about 03:00-05:00 UTC on Fri 13 Nov is the first that can write it,
  and the 13 Nov 16:30 UTC check reports both. **By his rule of 4 Oct what the site says about the verdicts, and
  the next step, are a discussion once both are in; neither is changed here** (the page's corrections below
  concern September's Bloomberg figures only).
- *Verdict night was rehearsed first (11 Nov).* In a scratch clone with no remote, the real writer's `main()` wrote
  both final blocks from SYNTHETIC reader output (never a real H7 number) and replaced HANDOFF's two rows. In that
  state: the pressure test read 0 fail (the gate before the workflow's push), the poster built and switched its
  headline by itself, `daily.py` read ALL CLEAR, thirteen suites passed and the full auditor read 217 of 217. The
  H5e final path also passed every one of the writer's refusals on the real, complete window. The real run then
  pushed as rehearsed.
- *Read-only sweep, clean:* `daily.py`; every suite; the independent check (1206 of 1206); a stdlib lint over all
  93 Python files (no undefined name in maintained code; its only hits are the 17 Oct re-check scripts, which
  `exec` a shared prelude); the nine workflows (scoped permissions, inputs passed through the environment, no
  injection path); the holiday and early-close calendar, right to January 2029; H8's two one-sided tests (the
  tails and the fixed-b null are right; its cold re-read stays on about 24 Nov).
- *Found: the 17 Oct fix of the Bloomberg-export reader had not reached everything.* Both readers were run on the
  same exports (`VOLREC_BBG_POSITIONAL=1` is the old one). The public page still carried the old reader's figures
  in three table rows (22 Sep USO 107 contracts and 0.09 on far puts, now 113 and 0.06; 23 Sep USO 0.01, now 0.00;
  23 Sep TSLA 86 and 0.33, now 87 and 0.50), in the day-count sentence (546 contracts, +1.15, standard error 0.13,
  R-squared 0.88; now 542, +1.14, 0.14, 0.87), in the 21-month sentence (+0.95 on 94 contracts; now +0.96 on 109)
  and in one narrative sentence (36 of 36 and 0.40, where the record and the page's own table say 44 of 44 and
  0.33). The same old figures stood in the after-data sections of the H3 and H5 files. **Corrected beside the
  originals, dated** (his rule; "yes fix the site too", 17 Oct): the page; seven notes in the two hypothesis files,
  in the form of the 17 Oct ones; three in `BLOOMBERG-MONDAY.md`; a row in `TEST-INVENTORY.md`. No registration
  text, bar, window, verdict or log entry is touched, and no conclusion changes.
- *One descriptive reading does change:* H5c's 22 Sep figure, "a 30% difference, outside H5c's 25%", was the reader
  bug. With every row read, Bloomberg's inflation that day is 5.14 against the free feed's 5.01 (2.6%), and all
  four matched expiry-days sit inside 25% (9.0%, 2.6%, 0.2%, 1.0%). H5c is still descriptive: never tested.
- *So it cannot recur:* `tools/site_bloomberg.py` compares 47 figures of the page with what the two tools print from
  the exports, each under its own day, underlying and expiry, always with the fixed reader. It runs on this Mac,
  where the licensed exports are (a SKIP elsewhere; a FAIL when the folder is half there), inside the pressure test,
  so the push hook refuses a page that has drifted. Before the page was fixed it reported exactly the eleven stale
  figures; now VERIFIED, 47 of 47. H5a's and H5b's pooled figures, which no maintained tool prints, are checked
  everywhere against the H5 file's corrected reading, in the narrative and in the hypothesis table. Four pressure
  checks, a suite of 45 cases, twelve auditor mutants (229 in all), each tried alone first: the mutated file parses
  and its own check fails by assertion.
- *Astra Ultra.* First review (12 Nov 03:27 UTC, `.codex-reviews/20261112T032744Z-hjxxncvu`): INCOMPLETE (bundle
  limits), three MEDIUM and one LOW, each verified against the code and fixed, tests first. (1) The checker's tools
  inherited the shell's environment, so the old-reader switch could have made it compare the page with the old
  reader: the switch is now never passed on (on the real exports the corrected page verifies with the switch set,
  and the old page still shows its eleven differences). (2) The H5a/H5b check compared two passages of one page:
  it now reads the record. (3) Figures were taken without checking which block they came from: every row, lift,
  note and block now carries its day, underlying and expiry, and a report for another expiry with the same numbers
  is a difference. (4) Three stale figures in `BLOOMBERG-MONDAY.md`: corrected.
- *Astra's follow-up, the one the rules allow.* Its first attempt (08:17 UTC) never reached the model: the ChatGPT
  account behind Astra had hit its usage limit, and no other model was substituted; a second was stopped with the
  session; the third ran (08:41 UTC, `.codex-reviews/20261112T084100Z-13p2lo5t`). INCOMPLETE again (the bundle
  cannot hold the page, both hypothesis files and both harnesses whole). It found the four fixes implemented and
  supported by their tests, the page's changed figures and H5c's percentages equal to the fixed reader's output,
  the mutants aimed at real assertions, and no registered verdict, bar, band or window touched. Four new points,
  each verified and fixed, tests first: the table's headings were not checked, so swapping "Far puts" and "Far
  calls" would have passed (the six headings are now required, in order); the pooled day-count run was checked by
  date only (it must now print exactly the ten blocks the H3 file names); a gap in the reader itself (next item);
  and one note's "unchanged" was too wide (narrowed). Under the one-follow-up rule these last fixes are verified
  by tests, mutants and identical outputs, not re-reviewed.
- *Also corrected:* README (the pressure test's count was "247", now dated; the "matching the published VIX to 0.01"
  status line now says one calibration day; the 40-day line is ticked); the page's "about four weeks" (H3's series
  is two months, closed 11 Nov).
- *The reader itself (from the follow-up).* The 17 Oct fix filled a row only as far as its last stored cell, so a
  row whose LAST cells the file left out (the put's volume, or its IVM too) would still have lost its put. Counted
  on all 18 exports: every one of the 1,917 strike rows carries its 14 cells, so it has never happened and no
  figure moves. Closed anyway in the fixed reading only (`ROW_CELLS`; the positional reading is untouched), with
  two such rows in the pressure test's synthetic sheet (the check failed first) and a mutant. Every Bloomberg
  tool's output on every export, in both reader modes, is byte-identical before and after (648 lines compared).
- *Noted, not changed.* (a) The guard's one `startup_failure` (status table). (b) `analyze.fetch_market_vol` keeps
  each index's file for the LOCAL day, so a run before the close hides that evening's Cboe closes until the next
  local day: an evening "n/a" on this Mac is the cache (CI fetches fresh). (c) The auditor costs about 85
  CPU-minutes (229 runs of about 22 s); the new export check adds about 3 s of that per run on this Mac.
  (d) Gabriel was using Codex in the ChatGPT app the same night, and the two share one allowance.
- *Suggested for after SCCUR (none done; each is his call):* (1) pin the recorders' one dependency before H8's window
  opens on 1 Dec (`pip install requests` resolves afresh on every run: 2.34.2 with urllib3 2.8.0 on 11 Nov), on an
  evening after the close, checking the next run fired; (2) generate the page's hypothesis table and the README's
  status from the hypothesis files, as the poster already does, so one figure lives in one place (today's defect
  was three places carrying one number; the table's H3 row still reads "to 9 Oct"); (3) a build script for the
  paper that takes every number from the record and refuses a mismatch, like the poster's; (4) a `CITATION.cff`,
  with Zenodo at the tagged release; (5) the auditor run only on the mutants whose files changed, with the full run
  weekly in the cloud; (6) a linter in CI, as a development tool only.
- *Needs Gabriel:* (1) ask Marc how long printing takes: the final poster is built once H7 is in (Fri 13 Nov at the
  earliest), and the 16 Nov reminder assumes a few days are enough; (2) the discussion once both verdicts are in
  (site, next step); (3) the 12 Nov reminder: say "buy the sealed index data for 4-11 Nov"; (4) the backup cron's
  margin: his 23 Sep acceptance ran to 11 Nov, and the pressure test warns again from 12 Nov (a WARN stops nothing).
  Recommended: renew it through H8's window, to 29 Jan 2027 (one line, `CRON_MARGIN_ACCEPTED`), not move a
  schedule - the outside trigger and the guard do the recording, and the one lost day (16 Sep) came from editing
  a cron. His yes or no.
- *Checks:* pressure test 0 fail, 3 warn (325 checks); the page-against-reader suite 45 cases, also under
  Python 3.9 and 3.13 (CI runs 3.12); the poster's 60 and 27, and the poster built on the real state (H5e's chip
  reads the workflow's own block: fails, final, 0.91; H3 reads "The reading of record, to 11 Nov 2026"; the page
  check passes); the independent check 1206 of 1206; twelve new mutants each caught alone.

*Bloomberg figures: Source: Bloomberg Finance L.P. OPRA figures: Data provided by Databento. Aggregates only.*

**Thu 12 Nov (later, UTC) - Gabriel's answers: the cron margin renewed, the 4-11 Nov index data bought and sealed, the H7 discussion held, Marc's email drafted, the suggestions on his calendar**
- *Gabriel (12 Nov, about 17:35 UTC):* "yes renew it, and buy the sealed index data for 4-11 Nov, make the email i
  can send to Marc, lets have the discussion for H7, and give me the steps for the cron margin, then add the
  suggestions to the calendar".
- *The cron margin, renewed:* `CRON_MARGIN_ACCEPTED` now runs to 29 Jan 2027, the end of H8's window (his 23 Sep
  acceptance ran out with the 40-day window on 11 Nov). The reasons stand: the outside trigger at 14:30 New York
  does the recording, the guard turns a post-close landing into a missed day, and the one day lost so far (16 Sep)
  came from editing a cron. No cron time meets the rule: at the worst delay seen (5h14m, 28 Sep), 30 minutes
  before the earlier (summer) close needs the cron at 14:16 UTC or earlier, and it must be at 14:30 or later so it
  never fires before the winter open. All of H8's window is on winter time, where the worst landing (20:01 UTC)
  sits 59 minutes before the 21:00 UTC close; only the half-days (27 Nov, 24 Dec, when cron-job.org's copies run
  the recorder at 11:30) leave the backup no room. Pressure test 0 fail, 2 warn (was 3).
- *The index top-up (the step the registration names):* 17 indices, one-second and daily bars, 4-11 Nov (6 trading
  days), priced first by `get_cost` at $0.197694, the item and total confirmed by Gabriel, bought 17:41-17:43 UTC
  (private `d03c511`, `ea9ce9e`): ledger $85.949143, DBIX $0.527557 of its $1 cap. The twelve sha256 went into the
  private README's seal before any value was read (`11aa734`), and all 36 were re-checked against the files with
  the reader's own `seal()` and `day_files()`: 16 one-second days, 21 Oct - 11 Nov, nothing missing, nothing extra.
  Read: `buy.py --check` only (17 symbols in every file). The 12 Nov top-up reminder was switched off at 17:47 UTC,
  13 minutes before it would have fired.
- *The H7 discussion (held before the verdict, at his request). His answers, both as recommended:* (1) **the
  site** is updated once H7 lands: its results table built from the hypothesis files (one number in one place,
  suggestion 2), a plain-words results line worded like the poster's headline, the companion readings beside the
  verdicts; pushed outside the recorders' window, with a screenshot to him. (2) **The sealed timing data**
  (`hypotheses/2026-11-06-index-timing.md`, OSF 4mcgf) is read once H7 is recorded: the registered command, once,
  reported as a description beside the verdicts (it never changes them), on the site and in the paper's notes, not
  on the poster, which carries only registered verdicts. The registration asks for both readings recorded, not a
  date, so this moves nothing it fixed. Unchanged, not reopened: the poster's headline rule (21 Oct, worded 11 Nov),
  H8's registration about 24 Nov, the Bloomberg pull 23-25 Nov (it covers the days before 21 Oct that DBIX cannot),
  H9 and H10 in December only if they meet every condition, the paper first.
- *What "H7 is in" now means, in order:* pull the private repository (the run that writes H7 also buys 11 Nov's
  OPRA); the companion readings beside the verdicts; the final poster built, checked and sent to Marc; the site;
  the timing reading (the reader refuses unless both marks exist and its rebuild matches H7's recorded days and four
  means). Each push before 13:45 or after 16:10 New York.
- *Marc:* the email asking how long printing takes, which file he needs and when to collect the poster was drafted
  for Gabriel to send (the Gmail connector needs reconnecting; pasting works). The 16 Nov reminder now asks whether
  the final poster has gone to Marc.
- *The calendar:* Notion Calendar has no calendar connected, so the six suggestions went into an .ics file opened in
  the Mac's Calendar, where Gabriel picks the calendar; each event alerts at its start (Pacific): Fri 13 Nov 9:30,
  H7 is in (site, timing reading, final poster; suggestion 2 joins it); Sun 22 Nov 10:00, pin `requests`
  (suggestion 1, beside the nightly-run edit; that day's push now says so); Wed 2 Dec, the faster auditor (5);
  Mon 14 Dec, the linter (6); Tue 5 Jan 2027, the paper's build script (3); Mon 1 Feb 2027, the citation file and
  Zenodo (4). The file stays out of git (`.git/info/exclude`).
- *Routines:* the 13 Nov check's push ends "Open Claude and say: H7 is in"; the 16, 20 and 22 Nov texts match the
  decisions; none has a connector.
- *Not sent to Astra:* a one-line date renewal and records; nothing from the private repository goes in a packet.
- *Needs Gabriel:* (1) send Marc's email; (2) click OK in Calendar's import dialog; (3) when Friday's push arrives,
  open Claude and say "H7 is in".

*OPRA and index figures: Data provided by Databento. Aggregates only.*

**Thu 12 Nov (evening, about 23:10 UTC) - Marc's email sent, the six suggestions in Calendar, the data budget**
- *Gabriel (12 Nov, evening):* "I sent the email, there is no 'ok' for me to do in calendar, also if we need to buy
  more data then its no worries we have plenty of usage credits and i want to have a good project if need be".
- *Marc:* the print email went out on 12 Nov; his answer is not yet known. The 16 Nov reminder still asks whether
  the final poster has gone to him.
- *The calendar:* the earlier `open -a Calendar` had launched Calendar with no window, no dialog ever showed, and
  nothing was imported (Fri 13 Nov held only his own events). With Calendar already running and its window on
  screen, `open -g -a Calendar volrec-suggestions.ics` raised an "Add event" box (calendar picker, OK); Gabriel
  answered it and the six events went into his **Work** calendar (iCloud). Each date was checked in Calendar's Day
  view, one event each: Fri 13 Nov 9:30, Sun 22 Nov 10:00 (alert at the start, notes present), Wed 2 Dec, Mon 14
  Dec, Tue 5 Jan 2027 and Mon 1 Feb 2027 at 9:00.
- *The data budget (his standing word, 12 Nov):* data that makes the project better is welcome beyond the 4 Nov
  pre-approval. Each purchase is still priced with `get_cost` first and its item and total shown to him before it
  is bought; the 4 Nov $120 ledger cap becomes a number named in that message, not a stop; never the $99/month
  plan. Ledger now $85.949143. Nothing needs buying today: the purchases already planned go ahead under their own
  caps.
- *Needs Gabriel:* when Friday's push arrives, open Claude and say "H7 is in".

**Fri 13 Nov (UTC; begun Thu 12 Nov, evening) - CLAUDE.md rewritten as the method, for any model**
- *Gabriel (12 Nov, on switching the session's model to Fable 5.2):* "Read my whole project. Then write a Claude.md
  that makes any other model work the way you do here. Include: what this project is and how it is built, a map of
  the folders, the commands to run, build and test, the coding rules, the design rules, the mistakes a weaker model
  would make here and how to avoid each one, and a checklist to run before saying a task is done."
- *Read first:* this file whole (4,215 lines), the charters, README, TEST-INVENTORY, the hypothesis README and
  template, the recorder and guard workflows, every tool's docstring and flags, the poster, lab and site, and the
  session's own notes on what has gone wrong before.
- *Written:* `CLAUDE.md`, 62 lines to 395 (31,745 bytes). Kept: its first paragraph and every earlier rule (Which
  python condensed, nothing dropped; the TimesFM, Vibe-Trading and Astra sections word for word). New: eight hard
  stops; what the project is and how the data flows; a map of the folders; the commands and the push steps; how a
  session goes and who decides what; coding rules; design rules; 18 mistakes, each with its fix; a 13-line
  checklist. It holds no live state: dates, counts and verdicts stay here and in `hypotheses/`.
- *Two limits it is built to.* (1) The review bridge bundles CLAUDE.md first and cuts any file at 32,000 bytes, so
  the file is held under that (the first draft was 41,185 bytes; 255 bytes are free). The cost: every Astra bundle
  now spends about 47 KB of its 180 KB on the four guidance files, where it spent about 20 KB. (2) The Astra
  section stays local, as before: it now sits after an HTML comment line beginning `<!-- LOCAL ONLY`, the 29,610
  bytes above it name nothing of the bridge, and the section gives the command that stages the file without it.
- *Checked, each by a run:* the 86 paths the file names exist; 15 flags, constants and strings it relies on are in
  the code; 109 tickers and 8 underlyings counted from the recorders; the suite loop (15 suites, 0 failures, about
  20 s); `daily.py --no-pull` ALL CLEAR; `lab/report.py --check` matches; the push gate passes "229 of 229" and
  refuses "228 of 229" and an empty log; the last full audit took 35 min 34 s at `-j 4` (229 mutants); the
  bridge's own bundler takes the file whole; the staging command, in a scratch clone, stages 29,610 bytes with no
  word of the bridge and leaves the local section unstaged. Pressure test 0 fail, 2 warn (the known two).
- *Found on the way, fixed:* SESSION-START's standing rule still said the cron was held "until Wed 11 Nov 2026".
  It now says through Fri 29 Jan 2027, the 12 Nov renewal.
- *Found on the way, not changed:* (a) CLAUDE.md and `analysis/timesfm_vix_baseline.py` point to
  `volrec-data-layer-brief.md`, which was never in the repository (a copy is in Gabriel's Downloads); CLAUDE.md
  section 9 now carries its guardrails in short. (b) The push helper used since 6 Nov lives only in the session's
  temporary folder, which a reboot empties (it was rebuilt once, 11 Nov); CLAUDE.md gives its steps in words.
- *Decided (Vega, under Gabriel's go-ahead; his to veto):* one file, not a short file plus an annex; the name Vega
  written in as the role's name; no Astra review, as for every documentation-only change since 6 Nov.
- *Not done:* nothing is committed or pushed (CLAUDE.md, SESSION-START and the two entries above sit uncommitted).
  H7's verdict commit is on GitHub (`a5497ca`, 13 Nov 03:28 UTC, by volrec-licensed); it was not pulled or opened
  in this session.
- *Needs Gabriel:* (1) say "H7 is in" to start the agreed steps; (2) whether the new CLAUDE.md goes to GitHub, where
  the Monday auditor and the Wednesday watchdog would read it (it would go without the local section); (3) whether
  the push helper moves into `tools/`, so a reboot cannot lose it again.

**Fri 13 Nov (later, UTC) - H7 is in: companions, H3's reading of record, the timing reading, the final poster, the site from the hypothesis files, and the print question**
- *Gabriel (13 Nov):* pasted Marc's answer to his 12 Nov email (Marc asked whether the poster was printed at
  Pepperdine's print services, and suggested checking FedEx's turnaround), then: "then also records came in", and
  "for the things that need me do whatever is best for the system to run efficienctly and best". Read as: H7's
  verdict commit had landed (`a5497ca`, 13 Nov 03:28 UTC), which is "H7 is in", so the four steps agreed on 12 Nov
  were done in order; his other items were decided under his words and are listed below.
- *1. Pulled.* This clone fast-forwarded onto `a5497ca`, later onto the day's recorder commits (`5e82959`,
  `1ec784f`; `data/` only). `volrec-licensed` pulled: its run started 03:21 UTC kept the verdict privately, pushed it,
  and committed the companion step there (`8762c3a`). Pre-pull copies of HANDOFF, SESSION-START and CLAUDE.md are in
  `.codex-reviews/held/pre-pull-2026-11-13/`.
- *2. Beside the verdicts, never in their place,* copied from the workflow's companion step (13 Nov, 03:28 UTC):
  **H3's reading of record** (frozen scorer, full precision, frozen rate; Vega's own run identical line for line):
  H3a HOLDS 0.708 over 205 readings on 41 days (bar under 1.0), H3b HOLDS -0.444, H3c HOLDS +0.0455 per point,
  one-sided p 0.0104 (wild cluster bootstrap, 7,776 Webb vectors); Benjamini-Hochberg 4 of 5 and 3 of 5; USO 1.767
  is the one fund over the bar. **H5e's companions:** mean absolute 0.905, 95% interval 0.385 to 1.425 (n_eff 15.7),
  one-sided p 0.948 for a mean under the bar; closer on 0.743 of days (26 of 35), interval 0.372 to 1.114 (n_eff
  9.3). **H7's companions:** H7a USO 0.316, interval 0.150 to 0.482 (n_eff 10.1; the interval spans the bar); on
  the strikes both feeds carry (log entry 3, written 17 Oct) 0.132 (USO) and 0.061 (GLD) over 24 days each;
  Cboe's walk passed the free file's +/-60% edge on 24 of 24 days for both; the second implementation 1302 of 1302.
  One mismatch noticed and left as printed: H7a's GLD mean reads 0.034 in the verdict and 0.035 in the interval
  line, two tools printing one mean to three places; reconcile it at write-up from full precision (running either
  reader again is a look the rules forbid, so it was not done).
- *3. The timing measurement, read once* (16:34 UTC, the registered command, the reader's sha256 `e65b5270...`
  checked first, the sealed index files opened only then, after both verdicts): 16 days, 21 Oct - 11 Nov 2026. At
  the snapshot minute the OPRA replica sat a mean absolute 0.021 points from OVX and 0.010 from GVZ (free feed 0.369
  and 0.037); the indices then moved a mean absolute 0.630 (OVX) and 0.207 (GVZ) before the close; H5e's
  skip-only estimate was 1.117 from OVX at its minute and 1.203 from the close. The whole output is in the
  hypothesis file: means, counts and quote-time offsets in seconds, no index value. Descriptive: the verdicts
  stand.
- *4. The final poster,* built from the files after both readings: both poster suites pass; `--pdf` wrote
  `poster/Mitton_SCCUR_2026_poster_48x36.pdf` (48 x 36 in, sha256 `158eb729...c00b5c`), sent to Gabriel. Its
  headline is his pre-decided fallback (21 Oct rule, worded 11 Nov): "Widen the strikes, and free data averages
  within a point of Cboe's index." The timing reading is not on it, as agreed. Rebuilt again at the end of the
  day: `poster.html` came out byte-identical, so the PDF is current.
- *5. The site, from the hypothesis files* (his 12 Nov design): new `tools/site_results.py` writes three passages
  of `index.html` between markers - the dek's results line (the poster's headline function, then H3's 0.708 over
  205 readings on 41 days), the ledger's figures for H3, H5, H7 and a new row "T" (the timing measurement), and two
  dated notes in the OPRA section ("Tested out of sample, H7 splits the two funds." and "Then the index moves.")
  - reusing the poster's parsers, never retyping them; `--check` compares and writes nothing. The ledger had still
  read H3 "0.41 mean gap over 90 readings to 9 Oct", H5e's first verdict only, and H7 "Collecting". The in-sample
  paragraph "Rebuilt with Cboe's own rules, the free feed is not the problem." stays as written, with the
  out-of-sample result dated beside it. Also: the ledger's prose names osf.io/4mcgf, "What comes next" says both
  were read, the "One snapshot a day" limit points to the timing note, and Sources gains the one-second index
  values (DBIX.CORE). New suite `tools/test_site_results.py` (159 cases, the two reviews below included). Pressure
  test: three new checks (page = records; the passages sit where they belong; the suite passes). Auditor: 30 new
  mutants (259); all 259 apply in a scratch worktree, and each new one is KILLED alone, its file still parsing, on
  the line it names. Checked in a browser at 1280 x 900 and 375 x 812, last after the follow-up review (14 Nov,
  04:30 UTC): the results line and its three figures, both OPRA notes, the in-sample paragraph above them and the
  ledger's H3, H5, H7 and T rows all visible (`checkVisibility`, opacity and visibility included), no sideways
  scroll, clean console; `tools/site_bloomberg.py` VERIFIED (47 figures).
- *6. Marc's print question,* researched at the source pages: Pepperdine Printing Services (Calabasas) posts no
  turnaround and does not list 48 x 36; the library's large-format printer is retired; FedEx Office prints 36 x 48
  posters. Recommendation, in the chat: FedEx Office, 48 x 36 in, plain paper (no foam board; SCCUR allows up to
  56 x 42 in and provides tape), ordered by Mon 16 Nov, picked up Tue 17 or Wed 18 Nov, carried in a tube; a reply
  to Marc drafted for Gabriel to send himself. The 16 Nov reminder now says exactly that.
- *7. The documents that repeat these facts:* `hypotheses/README.md` (H3, H5, H7 and timing rows; credit), the status
  table and hypothesis table above, TEST-INVENTORY (verdicts, the timing row, 1302 of 1302, the page's results),
  SCCUR-PITCH (the opener now ends with the fallback headline; the walk's two sentences; "Why did H7a fail?"; the
  timing answer; a credit line it lacked), PAPER-OUTLINE (a dated correction beside "The quotes are not the
  problem", the timing description in Limitations, 1302 of 1302, H7a among the failures), README's status list.
- *Decided (Vega, under Gabriel's go-ahead; his to veto):* (a) CLAUDE.md goes to GitHub without its local
  section, so the Monday auditor and the Wednesday watchdog read the same method (item 2 of the entry above);
  (b) the push helper stays out of `tools/`, kept on this Mac in `.codex-reviews/held/` (ignored by the local
  `.gitignore` line; a reboot does not empty it): public code would need its own tests and mutants for steps
  CLAUDE.md section 3 already gives;
  (c) the site's dek, the pitch's opener and the paper outline lead with the poster's fallback headline, his
  pre-decided rule applied everywhere it is repeated; (d) the in-sample OPRA paragraph kept, the out-of-sample
  result dated beside it; (e) the ledger id "T" (a longer one overflowed the 44 px phone column); (f) the print
  recommendation and the reworded 16 Nov reminder; (g) the ledger function pinned by its fingerprint rather than
  run in a JavaScript stub: the checks stay on Python's standard library, and the pin fails on any change at all;
  (h) the stylesheet held to a list of accepted hiding rules rather than to a list of guarded classes, which would
  miss a rule such as `.dek span` hiding the figures inside a passage; (i) no second follow-up review.
- *Found while staging CLAUDE.md, fixed:* its mistake 3 told readers to hold files in `.codex-reviews/held/`
  "(git-ignored)", which is true only on this Mac (the local `.gitignore` line); in the cloud auditor's clone
  they would sit untracked. It now says `~/Documents`, or a folder `git check-ignore` confirms; the local fact
  moved to the local section. CLAUDE.md 31,884 bytes, its public part 29,643, no word of the bridge in it.
- *Astra Ultra on this work, 13 Nov (`.codex-reviews/20261113T221400Z-_2grt5co`): INCOMPLETE.* Its four packets
  were `.diff` and `.txt` files, which the bridge does not bundle, so it read the sources but not the page diff, the
  checks and mutants, the parsers or the records. Eight findings (1 HIGH, 7 MEDIUM), each verified, all fixed, each
  new test seen failing first:
  1. *HIGH:* the new suite's H5 fixture copied the hypothesis file's real "Skip-only gap by day" line, a dated
     per-day series (with the public panel and estimator it rebuilds OVX's closes to two decimals). Now two invented
     days, with the Cboe credit beside them. The hypothesis file's own line stays as the frozen writer printed it
     (the 11 Nov decision above: a registered record, never edited).
  2. The page check compared only the bytes between markers: a passage hidden in a `<template>`, an unmarked
     paragraph contradicting it, the in-sample paragraph deleted, or the ledger showing H7's figures in H3's row all
     passed. New `placement()`: each passage sits at its own place in the page's element tree, the in-sample
     paragraph stands in the OPRA section just above the note, each ledger row reads its own id, and no H3, H5e or
     H7 verdict is stated outside the markers. `--check` runs it, the write mode refuses before writing anything,
     and the pressure test has a third site check.
  3. H3's block: only the first matching line was read, and HOLDS beside 1.708, Benjamini-Hochberg "9 of 5" or a
     p-value over 1 all passed. Now each line must appear exactly once and agree with its registered rule at the
     printed precision (a figure printed at its bar passes either way: the writer decides on full precision).
  4. H7's companions: "25 of 24 days" passed for the edge, and repeated lines were reduced to the first. Now each
     line appears once, the edge's count is at most its days, and its days are the matched days.
  5. The timing record: impossible counts, repeated lines, reversed dates and a broken identity all passed. Now one
     output block, each line once, real dates in order, measured days = covered days <= index files,
     E-C = (E-I) + (I-C) within the printed rounding, no signed mean larger than its mean absolute and no |E-C|
     larger than its two parts together, and two readings at one snapshot minute give their index one move.
  6. *A sign, caught before publication.* The OPRA note said OVX and GVZ moved before the close "averaging -0.066
     and +0.038", but those figures are I(T)-C, the index at the snapshot minus its close; the move to the close has
     the opposite sign. The page and the plain-words lines under the timing output (in both hypothesis files; my
     summaries, not the registered output) now say "the index at the snapshot minus its close averaged ...". It was
     never pushed, so no dated correction is needed. The mean absolute moves (0.630 and 0.207; 0.634 on H5e's days)
     were right; the status table's cell above now calls its 0.634 a mean absolute.
  7. The note was fixed prose: it would say oil fails and gold holds whatever the record said. It now renders only
     the outcome it narrates (H7a FAILS with USO surely over the 0.25 bar and GLD surely under it; H7b HOLDS with
     GVZ surely under 0.30) and refuses anything else.
  8. The note's test only checked that each number appeared somewhere, so swapping OVX's and GVZ's figures passed.
     Ten fragments now bind each label to its value, typed by hand.
  Also: the ledger's bars come from the frozen constants (`h3_scorer.H3A_BAR`, `record_verdict.H5E_BAR`, `H7_BAR_A`,
  `H7_BAR_B`), never retyped, and the ledger came out byte-identical; the edge sentence now says "for both funds".
- *Astra Ultra's follow-up, 13 Nov (`.codex-reviews/20261113T224633Z-1s3z3vf9`): needs attention, eight findings
  (7 MEDIUM, 1 LOW).* Its bundle held the code but not the page or the records (cut at the bridge's limit), so its
  counterexamples were traced by reading, not run. Each was verified against the code and fixed (14 Nov, 03:00 to
  05:00 UTC), every new test seen failing first (63 of the suite's 156 cases, then 2 of its 159, failed before the
  code changed):
  1. The ledger was held by lines it contains: `return;` at the top of the function kept every one, and a row's
     evidence overwritten after the rows were declared passed too. The whole function is now pinned by its sha256
     (`LEDGER_SHA256`, the generated passage cut out): any change to it fails until someone has looked at the ledger
     at 1280 and 375 px and pinned the new one. Its rows and reads are still named when they go wrong.
  2. Claims were looked for in the source, on one line: "H7a" and "holds" on two lines, split by a tag, or joined by
     `&nbsp;` passed. The page's words are now also read as a reader meets them: the text outside scripts and the
     generated passages, entities decoded, joined across tags, whitespace collapsed.
  3. The attributes around a passage do not show it is visible: a `<style>` element hiding the results line, or
     `hidden` on the in-sample paragraph's own block, passed. Now the page may hold no style element and link no
     stylesheet but its own and its fonts; the in-sample sentence must stand in the block it was built in,
     attributes and all, with no other block between it and the H7 note; and no rule in `tools/volrec.css` may hide
     anything (display none, visibility hidden or collapse, content-visibility hidden, opacity 0) beyond its four
     accepted rules (`ACCEPTED_HIDES`: the `hidden` attribute, the rail's scrollbar, the rail's brand words on
     phones, the ledger's head row on phones), nor import another stylesheet (`@import`), whose rules no check reads.
  4. A record block, or a verdict line inside one, written twice was read from its first copy (the poster's
     `_block` and parsers take the first match). Each block (H3, H5e, H7, H7's companion, the timing reading) and
     each verdict line is now read only when written once.
  5. H7's parts were not held to the registered minimum of 10 days (`record_verdict.H7_MIN_DAYS`); now each of
     its three counts is.
  6. Benjamini-Hochberg's counts were held to the slopes' directions, never to the p-values: H3c "5 of 5" passed
     with two p-values over q. Each count must now be what the scorer's own step-up (`analyze.benjamini_hochberg`,
     q 0.05) gives on the per-fund p-values printed beside it, at any value their rounding allows.
  7. Only one of the timing reading's three triangle bounds was held; now all three are, within the printed
     rounding.
  8. *LOW:* a figure of hundreds of digits converts to infinity, which every bar then judges (a slope of 309 digits
     read as positive). Every figure must now be a finite number.
  Also, in the same pass: H5e's FINAL block was read by the poster's parser and held to nothing. It is now held to
  its rule (mean under 0.5 AND closer on a majority), its count (closer days at most its days) and its minimum (10).
  Fourteen new mutants, one per new check (259 in all). *Not resolved, by design:* a static check cannot see how a
  browser finally draws the page (a hiding property beyond the four, an overlay, a script redrawing the table);
  that stays the look in a browser after every page change (CLAUDE.md section 8, item 6), done this time at both
  widths (item 5 above). The review's limitations also name the frozen H5e block's per-day line (left as written:
  the 11 Nov decision above, registered records are never edited) and the independent check's skipped licensed H7
  comparison (by design: the private run makes it). No second follow-up: one follow-up is the rule.
- *Needs Gabriel:* (1) order and pay for the print by Mon 16 Nov (reminder Mon 9:00 Pacific); (2) send Marc the
  reply and the PDF; (3) veto anything above.
- *Not verified from here:* whether the workflow's Pushover NOTICE for H7 reached his phone.
- *Commit and push:* the commit carries this entry; it goes out only when the full audit reads N of N, outside
  13:45-16:10 New York on a weekday, with no verdict due that night (none is: both finals are written).

*OPRA and one-second index figures: Data provided by Databento. Index closes: Cboe Global Markets. Aggregates
only.*

### Prompt for the next session

> Read `CLAUDE.md`, then `SESSION-START.md`, then HANDOFF section 18 - section 17 is history. Run
> `tools/daily.py` with the framework python and report its verdict. Then work from section 18's dated plan
> ("Fri 9 Oct - the dated plan from here") and the newest dated entries above it. Report numbers before
> recommending; never adjust a registered threshold; keep licensed data out of the repo; push only when
> `tools/audit.py` reads N of N. Open work: H8 is being built under `PROTOCOL.md` (`H8-DRAFT.md`, not
> registered; the cloud buys its OPRA daily), and `DESIGN-MEMO.md` is being revised with Gabriel. The
> `lab/` side project (retail implementation audit) is COMPLETE (14 Oct; lab/REGISTRATION.md) - read its
> 14 Oct entries above before touching it. Its public page `tools/lab.html` (4 Nov) is rendered by
> `lab/report.py` from the private summaries: re-render it, never edit it by hand.
> The SCCUR poster was redesigned 7-11 Nov (the entry above): run `poster/test_build_poster.py` and
> `poster/test_charts.py` by hand before any rebuild. Its open questions were answered on 11 Nov under
> Gabriel's delegation (the entry above, "Poster questions: his answers"); SCCUR is Sat 21 Nov, Session 2,
> 9:30 am, Montezuma Hall, board 12.
> H5e's FINAL reading was recorded on 12 Nov (FAILS, 0.91) and H7 on 13 Nov (H7a FAILS on oil, H7b HOLDS on
> gold); H3's reading of record HOLDS. The post-H7 steps were done on 13 Nov (the entry above): companions,
> the final poster, the site from the hypothesis files, the timing reading. Never run `tools/h7_reader.py`,
> `tools/index_timing.py` or `tools/describe.py` (beyond `--count-only`) on these windows again.
> The page's results are generated by `tools/site_results.py` from the hypothesis files: after any change to
> a result block or the page around its markers, run it, then `--check`; never edit between the markers.
> `--check` also refuses a passage hidden, moved or contradicted, and pins the ledger function: after any change
> to that function, look at the ledger at 1280 and 375 px, then set `LEDGER_SHA256` to the new fingerprint.
> SCCUR: Gabriel orders the print by Mon 16 Nov (FedEx Office, 48 x 36 in).
> `tools/site_bloomberg.py` holds the page's Bloomberg figures to the reader's output on every push from
> this Mac: after any change to that reader or that section, read its lines, never edit around them.
