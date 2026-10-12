# The retail implementation audit (`lab/`): design

**Status:** design, revision 2, 12 Oct 2026. Gabriel approved the direction ("add whatever you think is
best"), and this revision adds the Leak Map, the Break-Even VIX and a larger budget. Nothing is built or
bought yet.
**Agreed in conversation 11-12 Oct 2026** (brainstorming; HANDOFF section 18, 11-12 Oct entry).
**Exploratory.** It is not a registered hypothesis of the main project, never edits registered code,
data or verdicts, and is labelled exploratory everywhere it appears.

## 1. The question, and the two results it is built to produce

**How much of the volatility risk premium can a retail investor using free data actually keep?**

The premium itself is settled: options are priced above the volatility that follows (H1 found it on
9 of 11 Cboe pairs, 2016-2026). This study follows a dollar of it all the way to a retail account.
- **The Leak Map (section 6).** One number per fund: of every $1 of premium on paper, a retail
  investor keeps __ cents. One picture: the waterfall of where the rest goes, in this order: spreads,
  margin limits, forced liquidation, commissions. A separate bar shows how wrong a free-data user's
  estimate of the remainder would be.
- **The Break-Even VIX (section 7).** Selling volatility pays most when fear is high, which is also
  when spreads blow out. For each fund, this finds the index level above which the extra premium is
  eaten by the extra cost, or reports that no such level exists in the observed range.

Real prices (OPRA consolidated quotes, 2016-2026, crash months included), real costs (four levels of
the quoted half-spread), real constraints (Cboe customer margin and forced liquidation), and real
free data (the free feed against OPRA, same contracts, same moment).
Framing for the paper and the resume: **a retail implementation audit.**

## 2. What the literature already settles, and what is new

Read in full from the published versions (Pepperdine library, 12 Oct 2026; PDFs kept off the repo):

- **Santa-Clara & Saretto (2009)**, *Option strategies: Good deals and margin calls*, Journal of
  Financial Markets 12(3), 391-417.
  - Data: S&P 500 options. CME futures options 1985-2001 for the strategies; OptionMetrics SPX
    closing quotes 1996-2006 for spreads.
  - Spread cost: writing at the bid instead of the mid costs 5%-9% a month on puts and 5.3% on the
    ATM straddle. They charge a round trip because positions close after a month; footnote 7 says
    holding to maturity costs half.
  - Margin rule, Cboe customer accounts: naked put M = max(P + aS - OTM amount, P + bK), with
    a = 15% and b = 10% for the S&P 500, and brokers free to charge more. A combination is margined
    as the larger side's requirement plus the other side's premium.
  - Liquidation mechanic: $1 at each month's start; margin calls met from cash; when cash runs out,
    liquidate at the close and reopen with margin at most 90% of wealth. Target weights 2.5%, 5%,
    10% and 20%.
  - Findings: margins cut OTM strategies hardest, and an individual's cost of writing is two to
    three times an institution's.
- **Muravyev & Pearson (2020)**, *Options Trading Costs Are Lower than You Think*, Review of
  Financial Studies 33(11), 4973-5014.
  - Data: options on S&P 500 stocks, 2004-2015.
  - Quoted half-spread 8.6% of the option price. The conventional effective half-spread is 6.8%
    (about 80% of quoted). Traders who time their orders pay 2.5% (about 30% of quoted).
  - Their straddle backtest: conventional costs take about 80% of the IV-minus-HV strategy's return
    (7.4% a month falls to 1.5%); timed costs take about 40%.
- **Corrections to the commissioned research report** (checked against the published texts):
  1. Its "Sharpe ratios as high as 1.69" and "crash frequency two or three times" are not in the
     published Santa-Clara & Saretto. There, 1.69 is a Leland alpha (Table 6), and "two to three
     times" is the margin cost of individuals relative to institutions.
  2. Its Muravyev & Pearson figures ("one-third", "five times smaller") are working-paper numbers.

  The paper quotes only the published figures above.
- **What is new here** (no precedent found in the searches of 9 and 12 Oct 2026):
  1. every leak in one chain, on the fund options a retail investor actually trades, through 2026;
  2. the break-even index level per fund, measured from real quotes;
  3. costs measured on a free retail feed and validated against OPRA, the same contracts at the
     same moment;
  4. equity, gold and oil funds side by side.

## 3. Data, and what it costs

| Source | Use | Cost | Where it lives |
|---|---|---|---|
| OPRA cbbo-1m (Databento), history from 1 Apr 2013 | monthly entry days; weekly cost samples; daily marks in stress months | about $0.04-0.09 per day for the five funds | `~/Documents/volrec-licensed/opra-lab/`, outside the repo, git-ignored; ledger rows tagged `-lab` |
| Fund closes, Alpaca daily bars, **`adjustment="raw"`** | settlement value at expiry | free | fetched at run time, not committed |
| Fund closes, `adjustment="all"` (as `analyze.py`) | realised volatility (`analyze.realized_vol`, as H1) | free | fetched at run time |
| Cboe index closes (VIX, VXN, RVX, GVZ, OVX, VIX3M) | the rules; the Break-Even axis; the synthetic variance-swap cross-check | free | the existing git-ignored cache (`data/market_vol.json`) |
| The free feed (`data/surface.csv`) and H8's OPRA files | free versus OPRA spreads, same contracts, same moment | already held | as now |

- **Raw prices for settlement:** listed strikes are never back-adjusted. USO's 1-for-8 reverse split
  on 29 Apr 2020 would otherwise misprice every USO expiry before it.
- **Funds:** SPY, QQQ, IWM, GLD, USO. Each has both an index and liquid fund options.
- **Date range:** trades and samples run 4 Jan 2016 to 31 Aug 2026. Nothing is bought or read
  dated after 31 Aug 2026; the one earlier purchase is August 2015's daily marks, for a crash
  replay only. This keeps every lab purchase and reading clear of every registered window: H5e from
  23 Sep, H7 from 9 Oct, H8 from 1 Dec 2026.
- **Budget: own cap $90** (`LAB_BUDGET_USD`; $75 at first, raised 12 Oct to cover OPRA listings at
  about $0.024 a day; Gabriel: it can rise further).
  - Every request is priced first with `metadata.get_cost`, and nothing already on disk is bought
    twice.
  - Expected spend, about $70 in all (listings about $20 of it):
    - one test day, about $0.04;
    - about 128 monthly entry days, about $7;
    - about 555 weekly cost samples (Wednesdays), about $33;
    - daily marks for 7 stress months (Aug 2015 for the replay only, Feb 2018, Dec 2018, Mar 2020,
      Jun 2022, Aug 2024, Apr 2025), about 147 days, about $9.
  - Lifetime: about $2.27 spent by 10 Oct, plus H8's expected $10.5, plus the lab's ~$50 is about
    $63, inside the $100 lifetime cap. If the lifetime cap ever binds, Gabriel is asked before it is
    raised.
- **Integrity first: the test day, 5 Feb 2018, for the five funds.** It must pass all three checks:
  - every strike OPRA lists for the expiry within ±10% of the forward quoted on both sides
    (OPRA's listings bought with each day; amended 12 Oct after the test day, see the registration);
  - spreads positive and below the option's price;
  - put-call parity on the ATM pair within the two half-spreads plus a dividend allowance.

  Only then is the rest bought. If it fails, the study falls back to the synthetic variance swap and
  says so. The same three checks run on every day bought.
- **Deliberately NOT run:** the Cboe-method replica against GVZ and OVX on historical OPRA. That
  comparison belongs to a possible registered main-project test after the November verdicts (section
  13), and looking at it here would make that test a pilot.

## 4. The trades (fixed in the registration before any purchase)

- **Calendar:**
  - Entry: the first trading day after each standard monthly expiry, at 14:30 New York (the
    project's snapshot minute).
  - Expiry used: the next standard monthly one, 28-35 days out.
  - Exit: held to expiry, settled at intrinsic value on the fund's raw closing price.
- **Primary trade:** short one ATM straddle (call and put at the strike nearest spot).
- **Secondary trade:** short the 5% OTM strangle. The wings are where the variance strip carries its
  weight and where spreads are widest.
- **Cross-check (free):** the synthetic 30-day variance swap. P&L = index squared minus the realised
  variance that follows, in variance points, with the convexity and non-tradability caveats stated
  beside it.
- **Rules:** four, fixed in advance and deliberately few.
  - **R0, always sell.** The premium itself; the benchmark, and the trade the Leak Map is drawn on.
  - **R1, sell only when the fund's index exceeds its trailing 21-day realised volatility.** The
    Goyal-Saretto / Muravyev-Pearson filter.
  - **R2, size inversely to the index level.** H6's lesson, used for sizing.
  - **R3, skip months when VIX3M is below VIX (an inverted term structure), for all five funds.**
    H1c's link, used as a market-wide gate.
- **American exercise:** the fund options are American. Early assignment of a deep in-the-money
  short leg settles near intrinsic, so the P&L barely moves. This is stated as a limitation.

## 5. Costs: four cases

Each trade is charged the entry half-spread only, since it is held to expiry (Santa-Clara & Saretto
footnote 7; Muravyev & Pearson's convention).

| Case | Fraction of the quoted half-spread | Source |
|---|---|---|
| Mid | 0 | the frictionless benchmark |
| Timed | 30% | Muravyev & Pearson's execution timers |
| **Retail (headline)** | **80%** | Muravyev & Pearson's conventional effective spread |
| Quoted | 100% | the full quoted half-spread |

- **Commissions:** two cases, $0 and $0.65 per contract, on a $100,000 account. The Leak Map uses
  $0.65.
- **The fractions are borrowed.** They come from single-stock options, 2004-2015, and are stated as
  assumptions, not as findings about fund options.
- **Strip cost versus ATM cost:**
  - Strip cost: the registered estimator (`modelfree.model_free_30d`) run on bids, minus the same
    run on mids.
  - Quick cost: the ATM half-spread divided by vega.
  - The ratio between them is a result in its own right.

## 6. The Leak Map

- **Unit:** percent of capital per month, at the 5% target weight. The 2.5%, 10% and 20% weights
  appear in the appendix.
- **The chain, R0, ATM straddle; each step adds one friction:**

  | Step | What is added |
  |---|---|
  | Paper | mid prices, unlimited capital |
  | − Spreads | the retail cost case (80% of the quoted half-spread) |
  | − Margin limits | Cboe customer margin caps how much can be written (effective weight below target) |
  | − Forced liquidation | margin calls met from cash; liquidation at the close when cash runs out |
  | − Commissions | $0.65 per contract |
  | = Kept | what reaches the account |

- **Cents kept per dollar** = kept mean return ÷ paper mean return, with a bootstrap confidence
  interval. If the paper mean is not positive for a fund, the ratio is undefined: that fund is shown
  in percent of capital and the ratio is reported as "not defined".
- **Order matters, so every order is reported.** Spreads also make liquidations costlier
  (Santa-Clara & Saretto make this point), so each leak's size depends on when it is subtracted.
  - Each leak is credited its Shapley value: the average over all 24 orders of the four frictions.
  - The minimum and maximum across orders are reported beside it.
  - This is the same answer the main paper gives to the same problem in its decomposition.
- **The free-data bar, kept separate.** A free-data user who estimates the cost from the free
  feed's spreads misjudges the remainder by the gap between the free and OPRA costs.
  - It is measured only where both feeds exist (from 17 Sep 2026, on H8's files).
  - It is drawn beside the waterfall, labelled "estimate error, 2026 only", never subtracted as if
    it were cash.
  - Pilot already seen (12 Oct 2026, ATM, 20-45 days, median half-spread in volatility points, free
    / OPRA): SPY 0.070 / 0.034, QQQ 0.086 / 0.066, IWM 0.130 / 0.102, GLD 0.309 / 0.315,
    USO 1.366 / 1.331. So no prediction is made about this bar; it is reported as measured.

## 7. The Break-Even VIX

- **The cost curve:** every Wednesday at 14:30 New York, 2016-2026, the retail-case cost of the ATM
  straddle in volatility points, per fund.
- **The premium curve:** expected mid-price P&L of the R0 straddle as a function of the fund's own
  index level at entry. Measured from the monthly trades (non-overlapping, the headline) and from
  weekly entries (overlapping, Newey-West, as a robustness check).
- **The x-axis is each fund's own index:** VIX (SPY), VXN (QQQ), RVX (IWM), GVZ (GLD), OVX (USO).
  VIX is also shown for all five, as the market's gauge.
- **Estimation:**
  - both curves binned by index quintile, with a linear fit across bins;
  - the break-even is where premium minus cost crosses zero;
  - stationary-bootstrap confidence interval.
- **No extrapolation.** If the curves do not cross inside the observed range, the answer is "no
  break-even below an index of __", with __ the highest level observed.
- **Thin samples:** high-index months are few (2018, 2020, 2022, 2025). Each bin's count is printed
  beside it.

## 8. Margin and the stress lab

- **Margin, Santa-Clara & Saretto's mechanic exactly:**
  - Capital: $1 at each month's start.
  - Target weights: 2.5%, 5%, 10% and 20% of capital written as premium.
  - Calls: met from cash; when cash runs out, liquidate at the close and reopen at margin ≤ 90% of
    wealth.
  - Customer-account rule:
    - SPY, QQQ, IWM (broad-based index funds): a = 15%, b = 10%.
    - GLD, USO: the equity/ETF rate, a = 20%, b = 10%.
    - The current Cboe Margin Manual is read at build step 1. Where it differs, the manual wins,
      and the values are recorded in the registration before any run.
  - Broker variant: a = 40%, b = 35%, the house rate Santa-Clara & Saretto report for E-Trade.
- **Marking positions between entry and expiry:**
  - Stress months: real OPRA daily marks.
  - Other months: Black-Scholes marks at the index's volatility.
  - The stress months show how far the model marks miss, and that gap is reported.
- **Reported results:**
  - all in percent of capital;
  - effective versus target weight;
  - months with forced liquidation;
  - mean, Sharpe ratio, and the worst month.
- **Stationary bootstrap:**
  - 10,000 ten-year paths;
  - Patton-Politis-White automatic block length, with sensitivity at 1, 3, 6 and 12 months;
  - outputs: maximum drawdown (median, 95th and 99th percentiles), expected shortfall at 95% and
    99%, and the probability of losing half the capital.
  - The ruin odds are stated as conditional on this sample's crashes, never as unconditional
    estimates.
- **Crash replays:** each stress month, Aug 2015 included (before the trade sample begins, so a
  replay only), then the worst month scaled 1.5×. A bootstrap cannot draw a month worse than the
  worst one in history.

## 9. The trust engine (`lab/engine.py`)

- **Input:** a free option chain (the recorder's format).
- **Output:**
  - the volatility reading (the registered estimator, imported);
  - an error bar from the measured H8 gap and floor for that fund;
  - trust flags: zero-bid wings, stale quotes (over 120 s), fewer than 10 strikes in the band, or a
    median half-spread above the fund's measured 90th percentile;
  - the estimated cost to trade the ATM straddle and the strip right now.
  - The free feed's spreads run wider than OPRA's on the liquid funds (section 6 pilot), so the cost
    is shown both raw and corrected by the measured free/OPRA ratio, and the correction is labelled.
- **CLI:** reads the latest day of `data/surface.csv`.
- **Reach:** a small module, the reusable piece. No web service; nothing sold (Alpaca consent:
  personal, non-commercial).

## 10. Structure

```
lab/
  REGISTRATION.md    rules, cases, margin values, questions and predictions - committed before
                     any purchase or backtest
  costs.py           half-spreads, strip cost, ATM cost, free vs OPRA
  integrity.py       chain completeness, sane spreads, put-call parity
  trades.py          entry calendar, straddle/strangle P&L, rules R0-R3, the variance-swap cross-check
  margin.py          Cboe customer margin, liquidation mechanic
  leakmap.py         the waterfall and its Shapley attribution over the 24 orders
  breakeven.py       cost and premium curves by index level, the crossing, its interval
  stress.py          stationary bootstrap, PPW block length, replays, tail statistics
  engine.py          the trust engine
  fetch_lab.py       OPRA purchases: priced first, own cap, date range enforced, files outside the repo
  report.py          one aggregate report with the two charts, credit lines included
  test_lab.py        known-answer tests
```

Imports: `modelfree`, `analyze`, `tools/opra_reference` (read-only use). No registered file changes.

## 11. Questions, and predictions stated in advance

**Questions:**
- **Q1, the Leak Map:** cents kept per $1 per fund (R0, retail case, 5% weight), and each leak's
  Shapley share with its range across orders.
- **Q2, the Break-Even VIX:** the crossing index level per fund, or the highest level without one.
- **Q3:** strip cost over ATM cost.
- **Q4:** at each target weight, effective weight and liquidation months under Cboe customer margin.
- **Q5:** bootstrap tail statistics.
- **Q6:** the free-data estimate error (pilot already seen; measured, not predicted).

**Predictions** (directions, set from the literature before any lab data is bought):
- **P1:** at the retail case, the straddle keeps under half its paper return (under 50 cents per $1)
  on at least 3 of the 5 funds.
- **P2:** spreads are the largest leak by Shapley share on at least 3 of the 5 funds.
- **P3:** the strip costs at least twice the ATM estimate.
- **P4:** the retail cost as a fraction of the premium rises with the index level on at least 4 of
  the 5 funds.
- **P5:** retention is highest on SPY and lowest on USO.

These are predictions in an exploratory study, reported as made, right or wrong. They are not
registered tests of the main project.

## 12. Proving it works

- **Known-answer tests in `test_lab.py`** (fixtures in Databento's real format, blank bids included,
  as with H8):
  - a zero spread gives zero cost;
  - a flat-volatility, zero-premium world gives a mean P&L of zero;
  - straddle settlement matches hand-worked intrinsic values;
  - a split fixture settles correctly only on raw prices;
  - the margin rule matches Santa-Clara & Saretto's worked example (ATM 45-day put, S = $100, 20%
    volatility, 5% rate: initial Cboe margin $17.80);
  - Shapley shares sum exactly to the total leak, and a friction that changes nothing gets zero;
  - with one friction only, every order gives the same answer;
  - the break-even of two hand-made lines crossing at a known level is found there, and two
    parallel lines report "no break-even";
  - the bootstrap preserves the sample mean in expectation;
  - the PPW block length is near 1 on white noise and clearly longer on an AR(1) series with
    rho = 0.5;
  - put-call parity passes on a consistent fixture and fails on one with a shifted call.
- **Auditor mutants** (each must be caught):
  - lab-cap-ignored
  - lab-date-range-ignored
  - lab-raw-prices-dropped
  - lab-margin-ignores-otm
  - lab-cost-roundtrip-charged
  - lab-shapley-single-order
  - lab-breakeven-extrapolates
  - lab-bootstrap-iid
  - lab-writes-registered-file
- **Pressure-test checks:**
  - lab spend within its cap;
  - no lab OPRA file inside the repo;
  - no lab purchase dated after 31 Aug 2026;
  - the registered readers still byte-identical;
  - `lab/` imported by no registered reader.
- **Rule:** push only when `tools/audit.py` reads N of N.

## 13. Outputs, what stays private, and what feeds the main project

- **Outputs:**
  - one aggregate report (`lab/report.py`) with two charts, the Leak Map waterfall and the
    Break-Even curve;
  - a paper section ("What the data gap costs in dollars");
  - resume bullets, drafted with Gabriel once the numbers exist.
- **Credit lines:** "Data provided by Databento" on every OPRA-derived figure; Cboe's indices cited.
- **Nothing on the public site until Cboe's permission reply** (requested 10 Oct). After that, a site
  page is part of the post-November discussion.
- **Kept off the public repo:** no raw quotes, no Cboe CSVs, no paper PDFs.
- **Feeds the main project only by discussion with Gabriel after the 12-19 Nov verdicts.** The lab
  buys no day inside a registered window and never computes the Cboe-replica comparison (section 3).

## 14. Order of work

1. Read the current Cboe Margin Manual; write `lab/REGISTRATION.md`; commit it.
2. Build `costs.py`, `integrity.py`, `margin.py` and `test_lab.py` first (pure functions, known
   answers).
3. Buy and verify the 5 Feb 2018 test day.
4. Build `trades.py` and `fetch_lab.py`; buy the monthly entry days; run.
5. Build `leakmap.py`, `stress.py` and `report.py`; buy the stress-month daily marks; run.
6. Buy the weekly cost samples; build `breakeven.py`; run.
7. Build `engine.py`; add the auditor mutants and pressure checks; draft the paper section and
   resume bullets with Gabriel.
