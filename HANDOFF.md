# HANDOFF

Context for anyone (or any assistant session) picking this project up cold.
Read this before proposing changes. It records not just the current state but
the reasoning behind decisions already made, so they don't get re-argued.

Last updated: 5 September 2026.

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
| GitHub Actions | Live. Weekdays 15:30 UTC (8:30am Pacific). First scheduled run: Tue 8 Sep. Mon 7 Sep is Labor Day and is skipped. |
| Data | Collecting since 2026-09-04. First run: 52/52 rows, all IV populated. |
| `tools/gamma-lab*.html` | Complete. Educational, not part of the pipeline. |
| Analysis | Not started. Blocked on data volume until late October. |

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
  inactivity.** Daily commits from the recorder should prevent this, but it
  fails *silently*. `freshness.yml` runs daily and fails loudly (which emails
  you) if the newest row is more than 5 days old - that is the tripwire.
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
  deliberate limitation.

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

## 10. The schema upgrade - APPLIED 5 Sep 2026

`FIELDS` now declares 24 columns. The data file still has 17 and **migrates
itself on the next run** - `migrate_header()` runs inside `append()` before any
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
requirements.txt              one dependency: requests
.github/workflows/record.yml  the schedule
.github/workflows/freshness.yml  daily staleness alarm
data/iv_history.csv           the dataset — the only irreplaceable artifact
tools/gamma-lab.html          delta-hedging simulator v1
tools/gamma-lab-v2.html       v2 — adds costs, stochastic IV, jumps, freq sweep
tools/monitor.html            collection monitor — reads the live CSV from GitHub
```

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
