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

## 18. Current state — 23 September 2026, the reading every session starts from

**Section 17 is now history:** dated notes from 16-23 Sep, with the reasoning behind
every decision. This section is the only one guaranteed current. Read it, run
`tools/daily.py`, and open section 17 only when a task needs the why.

### System status, checked 10 Oct 2026 ~19:30 UTC (rows below "public site" last checked 23 Sep)

| check | result |
|---|---|
| diagnostic, 10 Oct (after the weekend's changes) | `daily.py` **ALL CLEAR**; pressure test **247 checks, 0 fail, 3 warn** (the same three known warnings); auditor **68 of 68**; calibrate **9 of 9**; unit tests hedged 30, H6 27, H7 17, H8 26 - all pass; every registered reader (modelfree, `--wide`, hedged, h7_reader, record_verdict dry run, ovx_replicate, calibrate) **byte-identical** to the code before the weekend (24b9a2a), same data; a fresh public clone reproduces them too |
| Databento, 10 Oct | lifetime **$2.27** of the $100 cap (H8 calibration $1.39; the cloud's first H8 day $0.17); H7 under its own $1.10 cap, H8 under its own $15 |
| OSF | H5e and H7 registered and live, https://osf.io/z5gfu (10 Oct 17:43 UTC) |
| `tools/pressure_test.py` | **0 fail, 3 warn** (9 Oct, after the full audit) - all known and true: FXE's one-sided 7 Oct quote (no IV carried), the snapshot time spread over 10 days (88 min, from before the outside trigger), and the GitHub-cron backup can land after the close (the guard refuses it; the trigger prevents it). Auditor **53 of 53** |
| `tools/calibrate.py` | **9 of 9** instruments calibrated against a known answer (the OPRA comparison added 23 Sep) |
| `tools/test_hedged.py` | 21 hand-computed cases pass |
| static scan | no undefined name in 18 files; dead imports removed |
| `tools/daily.py` | ALL CLEAR |
| workflows | record, surface, freshness, health all **active**; last runs green |
| `health.yml` | first manual run green in 32 s; **first scheduled run tonight, 23:37 UTC** |
| watchdog routine | **updated 23 Sep; first run 23 Sep 16:13 UTC healthy**, 54 s, no notification (Wednesdays 09:13 Pacific). Its sandbox blocks `cdn.cboe.com` and FRED, so its `daily.py` always ends LOOK AT: modelfree - expected, and the prompt says so. It runs on Gabriel's usage |
| iMessage alerts | test message delivered; launchd job **installed**, weekdays 13:30 Pacific, from the clean clone `~/.volrec-ops` |
| pre-push hook | installed (`core.hooksPath tools/hooks`); every push to main runs the pressure test |
| Databento | key saved outside the repo; **$0.0865 over 12 requests** of the $100 cap; days on disk are never bought twice (fixed 23 Sep) |
| holiday list | `panel_health.US_MARKET_HOLIDAYS` had 2027's Good Friday a week late (2 Apr; it is 26 Mar) - **fixed 23 Sep**; the pressure test now checks every Good Friday against a computed Easter |
| public site | live at gabrielmitton-cloud.github.io/volrec with the Bloomberg aggregates section, **the OPRA aggregates section (added 23 Sep)** and an up-to-date hypothesis table |

### What runs unattended (UTC)

| what | when | on failure |
|---|---|---|
| `record.yml`, `surface.yml` | weekdays **14:30 / 14:40 New York** via cron-job.org `workflow_dispatch` (11:30 / 11:40 on NYSE's early closes); GitHub's 14:47 / 14:57 UTC cron is the backup and stands aside if it starts before the trigger's slot + 15 min | `freshness` fails and GitHub emails; `panel_health` warns when a landing is off the trigger's slot |
| `freshness.yml` | 20:00 and 23:00 daily | GitHub emails |
| `health.yml` | weekdays 23:37 | GitHub emails (the whole daily check) |
| launchd `com.volrec.daily` | weekdays 13:30 Pacific | the iMessage leads with LOOK AT |
| watchdog routine | Wednesdays 16:13 | a push notification, only when something is wrong |
| **auditor routine** (built 30 Sep) | Mondays 16:30 UTC | a push notification when a safeguard does not fail when broken, `volrec-licensed` is public, or HANDOFF contradicts the live state |
| **healthchecks.io** (outside GitHub, set up 25 Sep) | checks `volrec-recorders` (freshness, daily 20:00 UTC, 8 h grace), `volrec-health` (weekdays 23:37, 6 h), `volrec-licensed` (weekdays 23:05, 9 h) | an email when a ping is MISSING - the job never ran. Pinged on success only; ping URLs are GitHub secrets HC_*; a ping can never fail a job |
| **`volrec-licensed` daily.yml** (private repo, built 24 Sep) | weekdays 23:05 UTC | an issue in `volrec-licensed` (email + GitHub app): OPRA fetch, compare, and the H5f / H5e verdicts on their dates in fixed wording (`tools/record_verdict.py`). Pushes to THIS repo only on verdict days, never 13-21 UTC |

### Where each hypothesis stands

| | status | the numbers |
|---|---|---|
| H1 | tested, holds | 9 of 11 Cboe pairs survive FDR control |
| H2 | tested, not adopted | log variance strongest (t=16.26) |
| H3 | series running | H3a mean abs gap **0.53** over 30 readings (bar 1.0). First registered wide reading **OUTSIDE** 1.4-3.2 (+9.41; +10.71 with 23 Sep): quote contamination, as the grid anticipated. **IWM reads positive on all six days**, against H3b's sign - watch. **Day count: Bloomberg stated ACT/252 in writing (23 Sep); at 21 months ~1 point remains, not the forward or rate, unidentified and closed (24 Sep).** H3c's mechanism is Jiang & Tian (2007)'s, credited |
| H4 | descriptive, **strike 2 of 3** (8 Oct) | strike 2: calendar-day carry + Bakshi-Kapadia dividend-adjusted price (strike 1, 23 Sep: runs break on a missed trading day). Data to 7 Oct: date level -5.23bp (t -2.50) vs -5.22bp under strike 1; no conclusion moved. One strike left |
| H5a | **tested 23 Sep, holds weakly** | pooled median 0.40 of a spread over 169 wing contracts on 3 days (bar 0.5); **0.67 on the 132 both feeds bid** - the two readings of "quoted" are logged, nothing adjusted |
| H5b | **tested 23 Sep, holds** | 36 of 36 free-feed missing bids are missing on Bloomberg (bar 80%) |
| H5c | descriptive | Bloomberg reproduces USO's inflation within 0.5% and 10.4% on 23 Sep (6.5% and 30% before); needs 10 underlying-days |
| H5d | descriptive | 12 underlying-days on 3 dates; the date-clustered test needs more dates |
| H5e | **first verdict: FAILS** (8 Oct) | mean abs gap 0.90 (bar under 0.5); closer on 2 of 10 days; final reading 11 Nov |
| H5f | **read 25 Sep at 5 days: a, b, c hold** (a ON the bar) | H5f-a **0.500** of OPRA's spread (bar 0.5); H5f-b **64 of 64** no-bid (bar 80%); H5f-c inflation gap **0.6%** per day, 0.4% on medians (bar 25%); stale quotes excluded by the rule |
| H6 | **tested 9 Oct: H6a FAILS, H6b HOLDS** | ATR(14) beats implied vol on the next day's range in 9 of 9 pairs (IV overshoots the level 1.6-2.3x: close-to-close risk plus the premium); IV's disadvantage shrinks after spikes (Welch t -7.95; with Newey-West errors t -3.80 at lag 21, -3.12 at lag 63 - still holds); exploratory: with the level removed IV's timing error is smaller in 8 of 9 |
| H7 | **registered 8 Oct (exception to the 11 Nov rule, Gabriel); collecting from 9 Oct** | free feed through Cboe's rules vs OVX/GVZ on the monthly legs (first rows 9 Oct, 1,066 contracts); read once over 9 Oct - 11 Nov, min 10 days, written when the window's data is complete (by 19 Nov at the latest); reader corrected before any data (blank OPRA bid = zero bid, H7 log 1); GLD OPRA in the cloud fetch (~$1 approved) |

*Bloomberg figures: Source: Bloomberg Finance L.P. OPRA figures: Data provided by Databento. Aggregates only.*

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
  says about five business days); if nothing by **Mon 19 Oct**, one polite follow-up. **MIT licence
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
- **Wed 11 Nov:** the 40-day window closes, and with it H5e's and H7's. The live panel's premium analysis
  (`analyze.py`) needs Alpaca keys, so it will run through a manual read-only workflow like `sample_a.yml`;
  register what it will read before running it.
- **Thu 12 - Thu 19 Nov:** the cloud writes H5e FINAL and H7 once each window's data is complete (11 Nov's
  OPRA arrives about 13 Nov) and by 19 Nov regardless. **Fri 13 Nov 16:30 UTC:** the phone alert
  (`trig_01MG53JubGrUPhph4bd9yimY`); "NOT recorded yet" then means waiting for data, not a failure.
- **After the verdicts:** the site and any next step are a discussion with Gabriel first (his 4 Oct rule).
- **December:** add the December ex-dates for SPY, QQQ, IWM, NVDA and AAPL to `data/dividends.csv` when
  declared (a WARN fires from about 27 Dec). **By Tue 22 Dec:** renew the cron-job.org GitHub token
  `volrec-trigger` (expires 29 Dec), paste it into every job, then update `TRIGGER_TOKEN_EXPIRES` in
  `pressure_test.py` (WARN from 1 Dec, FAIL - an email - from 22 Dec).
- **February 2027:** the write-up, TimesFM's FAIL included.

### Prompt for the next session

> Read `CLAUDE.md`, then `SESSION-START.md`, then HANDOFF section 18 - section 17 is history. Run
> `tools/daily.py` with the framework python and report its verdict. Then work from section 18's dated plan
> ("Fri 9 Oct - the dated plan from here") and the newest dated entries above it. Report numbers before
> recommending; never adjust a registered threshold; keep licensed data out of the repo; push only when
> `tools/audit.py` reads N of N. Open work: H8 is being built under `PROTOCOL.md` (`H8-DRAFT.md`, not
> registered; the cloud buys its OPRA daily), and `DESIGN-MEMO.md` is being revised with Gabriel.
