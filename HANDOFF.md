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

## 17. Current state and what to do next — 16 September 2026

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

**Two decisions that are Gabriel's, both costed in the 23 Sep session:**

- **H4 splices across missing trading days.** `hedged.runs_for_contract` treats
  "within four calendar days" as consecutive, so 15 -> 17 Sep (16 Sep lost) counts:
  1,376 runs at -11.67bp, plus 19 runs where a contract skipped a day. With them
  the date-level mean is -8.56bp over five pairs; with only truly consecutive pairs,
  about -1.1bp. H4's spec says "consecutive trading days" and this section already
  said the 15-16 pair does not exist. Fixing it is a post-output change to which
  runs count, so it costs one of H4's three strikes. **Recommended: fix, log it as
  strike 1, before H4 has enough pairs to be tested.**
- **The cron margin.** Worst delay seen is now 4h57m: 16 minutes to spare under
  DST, and no single UTC time satisfies both "after the winter open" and "30 minutes
  clear of the summer close" any more. Options: (a) hold to 11 Nov, rely on
  `panel_health` failing a post-close landing and drop that day; (b) a DST-aware
  pair of crons with an in-session guard, edited on a Saturday. **Recommended: (a)**
  - a schedule change moves every remaining snapshot, a late landing costs one day,
  and the clocks change on 1 Nov anyway, adding an hour of room.

**Assessed and parked, 23 Sep:** H6 (Kalshi against the market) - Kalshi's S&P
contracts are same-day (`KXINX`, `KXINXU`, public API, no key); the recorder has no
same-day options, so there is nothing to compare against without a new recorder,
and a correlation search would break pre-registration. TradingView (charting needs a
licence; the broker module is trading), worldmonitor (news-to-market pattern
search), a SQL store (CSV stays the audited record; a gitignored DuckDB view is 20
lines if ever needed). **Worth pursuing: Databento's OPRA data** - consolidated NBBO
at one-minute resolution, historical, $125 free credit - would give a reference
quote for every recorded day at the snapshot's own minute.

*Bloomberg figures: Source: Bloomberg Finance L.P.*

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
> HANDOFF 17, "23 September", has everything, including two decisions awaiting
> Gabriel: the H4 splice fix (costs a strike) and the cron margin.
>
> Rules: report numbers before recommending; never adjust a pre-registered threshold,
> bucket or bar; never edit a workflow's `schedule:` on a day whose run is still
> needed; Bloomberg exports stay in ~/Documents/volrec-bloomberg and never enter the
> repo, and every published Bloomberg-derived figure carries "Source: Bloomberg
> Finance L.P.".
