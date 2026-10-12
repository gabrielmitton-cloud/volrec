# The retail implementation audit (`lab/`): design

**Status:** design for Gabriel's sign-off, written 12 Oct 2026. Nothing is built or bought yet.
**Agreed in conversation 11-12 Oct 2026** (brainstorming; HANDOFF section 18, 11-12 Oct entry).
**Exploratory.** It is not a registered hypothesis of the main project, never edits registered code,
data or verdicts, and is labelled exploratory everywhere it appears.

## 1. The question

**How much of the volatility risk premium can a retail investor using free data actually keep?**

The premium itself is settled: options are priced above the volatility that follows (H1 found it on
9 of 11 Cboe pairs, 2016-2026). This study asks what is left once a retail investor really trades it:
- real prices: OPRA consolidated quotes, every month from 2016, crash months included;
- real costs: the half-spread actually quoted, at four levels a trader might pay;
- real constraints: Cboe customer margin and forced liquidation;
- real data: what happens if the investor prices it all from the free feed instead.

Framing for the paper and the resume: **a retail implementation audit.**

## 2. What the literature already settles, and what is new

Read in full from the published versions (Pepperdine library, 12 Oct 2026; PDFs kept off the repo):

- **Santa-Clara & Saretto (2009)**, *Option strategies: Good deals and margin calls*, Journal of
  Financial Markets 12(3), 391-417. S&P 500 options. Two datasets: CME futures options 1985-2001 for
  the strategies, and OptionMetrics SPX closing quotes 1996-2006 for spreads. Writing at the bid
  instead of the mid costs 5%-9% a month on puts and 5.3% on the ATM straddle; a round trip is
  charged because positions close after a month (footnote 7: holding to maturity costs half). The
  margin rule: Cboe customer accounts, naked put M = max(P + aS - OTM amount, P + bK), with a = 15%
  and b = 10% for the S&P 500 and brokers free to charge more. A combination is margined as the larger
  side's requirement plus the other side's premium. Liquidation mechanic: start each month with $1,
  meet calls from cash, liquidate at the close when cash runs out, reopen with margin at most 90% of
  wealth, at target weights of 2.5%, 5%, 10% and 20%. Margins cut OTM strategies hardest, and an
  individual's cost of writing is two to three times an institution's.
- **Muravyev & Pearson (2020)**, *Options Trading Costs Are Lower than You Think*, Review of
  Financial Studies 33(11), 4973-5014. Options on S&P 500 stocks, 2004-2015. Quoted half-spread 8.6%
  of the option price; the conventional effective half-spread is 6.8% (~80% of quoted); traders who
  time their orders pay 2.5% (~30% of quoted). In their straddle backtest, conventional costs take
  ~80% of the IV-minus-HV strategy's return (7.4% a month falls to 1.5%), timed costs ~40%.
- **Corrections to the commissioned research report** (checked against the published texts):
  1. Its "Sharpe ratios as high as 1.69" and "crash frequency two or three times" are not in the
     published Santa-Clara & Saretto; there, 1.69 is a Leland alpha (Table 6), and "two to three
     times" is the margin cost of individuals relative to institutions.
  2. Its Muravyev & Pearson figures ("one-third", "five times smaller") are working-paper numbers.
  The paper quotes only the published figures above.
- **What is new here** (no precedent found in the searches of 9 and 12 Oct 2026):
  1. costs measured on a free retail feed and validated against OPRA, the same contracts at the
     same moment;
  2. the retained premium across equity, gold and oil funds, on the fund options a retail investor
     actually trades, through 2026.

## 3. Data, and what it costs

| Source | Use | Cost | Where it lives |
|---|---|---|---|
| OPRA cbbo-1m (Databento), history from 1 Apr 2013 | entry-day quotes, monthly, 2016-2026; daily marks in stress months | about $0.04-0.09 per entry day for the five funds | `~/Documents/volrec-licensed/opra-lab/`, outside the repo, git-ignored; ledger rows tagged `-lab` |
| Fund closes, Alpaca daily bars, **`adjustment="raw"`** | settlement value at expiry; realised volatility | free | fetched at run time, not committed |
| Cboe index closes (VIX, VXN, RVX, GVZ, OVX, VIX3M) | implied level for the rules; synthetic variance-swap cross-check | free | the existing git-ignored cache (`data/market_vol.json`) |
| The free feed (`data/surface.csv`) and H8's OPRA files | free versus OPRA spreads, same contracts, same moment | already held | as now |

- **Why raw prices for settlement:** listed strikes are never back-adjusted. USO's 1-for-8 reverse
  split on 29 Apr 2020 would otherwise misprice every USO expiry before it. Realised volatility uses
  `analyze.realized_vol` on adjusted closes, as H1 does.
- **Funds:** SPY, QQQ, IWM, GLD, USO. Each has both an index and liquid fund options.
- **Budget:** the lab gets its own cap, **$25** (`LAB_BUDGET_USD`), inside the $100 lifetime cap
  (spent about $2.27 by 10 Oct; H8 expects about $10.5 by 29 Jan). Every request is priced first
  with `metadata.get_cost`, and nothing already on disk is bought twice.
- **Expected spend:**
  - one test day, about $0.04;
  - about 128 entry days, about $7;
  - daily marks for 7 stress months (Aug 2015, Feb 2018, Dec 2018, Mar 2020, Jun 2022, Aug 2024,
    Apr 2025), about 147 days, about $9.

  About $16 in all.
- **Test day first:** 5 Feb 2018 for the five funds. It must show complete chains: every listed
  monthly strike within ±10% of spot quoted, with sane spreads. Only then is the rest bought. If it
  fails, the study falls back to the synthetic variance swap alone and says so.

## 4. The trades (fixed in the registration before any purchase)

- **Calendar:**
  - Entry: the first trading day after each standard monthly expiry, at 14:30 New York (the
    project's snapshot minute).
  - Expiry used: the next standard monthly one, 28-35 days out.
  - Exit: held to expiry, settled at intrinsic value on the fund's raw closing price.
- **Primary trade:** short one ATM straddle (call and put at the strike nearest spot).
- **Secondary trade:** short the 5% OTM strangle. The wings are where the variance strip carries its
  weight and where spreads are widest.
- **Cross-check (free, 2016-2026):** the synthetic 30-day variance swap. P&L = index squared minus
  the realised variance that follows, in variance points, with the convexity and non-tradability
  caveats stated beside it.
- **Rules:** four, fixed in advance and deliberately few.
  - **R0, always sell.** The premium itself; the benchmark.
  - **R1, sell only when the index exceeds the fund's trailing 21-day realised volatility.** The
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

- **Commissions:** two cases, $0 and $0.65 per contract, on a $100,000 account.
- **The fractions are borrowed.** They come from single-stock options, 2004-2015. They are stated
  as assumptions, not as findings about fund options.
- **Strip cost versus ATM cost:**
  - Strip cost: the registered estimator (`modelfree.model_free_30d`) run on bids, minus the same
    run on mids.
  - Quick cost: the ATM half-spread divided by vega.
  - The ratio between them is a result in its own right.
  - Measured on OPRA at the 2026 snapshots (H8's files) and on every entry day.

## 6. Margin and the stress lab

- **Margin, Santa-Clara & Saretto's mechanic exactly:**
  - Capital: $1 at each month's start.
  - Target weights: 2.5%, 5%, 10% and 20% of capital written as premium.
  - Calls: met from cash; when cash runs out, liquidate at the close and reopen at margin ≤ 90%
    of wealth.
  - Customer-account rule:
    - SPY, QQQ, IWM (broad-based index funds): a = 15%, b = 10%.
    - GLD, USO: the equity/ETF rate, a = 20%, b = 10%.
    - The current Cboe Margin Manual is read at build step 1. Where it differs, the manual wins, and
      the values are recorded in the registration before any run.
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
  - outputs: maximum drawdown (median, 95th and 99th percentiles), expected shortfall at 95% and 99%,
    and the probability of losing half the capital.
  - The ruin odds are stated as conditional on this sample's crashes, never as unconditional
    estimates.
- **Crash replays:** each stress month, then the worst month scaled 1.5×. A bootstrap cannot draw a
  month worse than the worst one in history.

## 7. The free-feed leg

On every day H8 holds both feeds (from 17 Sep 2026), same contracts, same moment:
- the free half-spread against the OPRA half-spread;
- the cost an investor would estimate from free data against the true cost.

Alpaca's own documentation calls the free quotes "not actual OPRA quotes". This leg measures whether
a free-data user misjudges the price of the trade.

## 8. The trust engine (`lab/engine.py`)

- **Input:** a free option chain (the recorder's format).
- **Output:**
  - the volatility reading (the registered estimator, imported);
  - an error bar from the measured H8 gap and floor for that fund;
  - trust flags: zero-bid wings, stale quotes (over 120 s), fewer than 10 strikes in the band, or a
    median half-spread above the fund's measured 90th percentile;
  - the cost to trade the ATM straddle and the strip right now.
- **CLI:** reads the latest day of `data/surface.csv`.
- **Reach:** a small module, the reusable piece. No web service; nothing sold (Alpaca consent:
  personal, non-commercial).

## 9. Structure

```
lab/
  REGISTRATION.md    rules, cases, margin values, questions and predictions - committed before
                     any purchase or backtest
  costs.py           half-spreads, strip cost, ATM cost, free vs OPRA
  engine.py          the trust engine
  trades.py          entry calendar, straddle/strangle P&L, rules R0-R3, the variance-swap cross-check
  margin.py          Cboe customer margin, liquidation mechanic
  stress.py          stationary bootstrap, PPW block length, replays, tail statistics
  fetch_lab.py       OPRA purchases for the lab: priced first, own cap, files outside the repo
  report.py          one aggregate report, credit lines included
  test_lab.py        known-answer tests
```

Imports: `modelfree`, `analyze`, `tools/opra_reference` (read-only use). No registered file
changes.

## 10. Questions, and predictions stated in advance

**Questions:**
- **Q1:** per fund and cost case, the fraction of the mid-price return the ATM straddle keeps (R0;
  R1-R3 alongside).
- **Q2:** strip cost over ATM cost.
- **Q3:** free-feed cost over OPRA cost.
- **Q4:** at each target weight, effective weight and liquidation months under Cboe customer margin.
- **Q5:** bootstrap tail statistics.

**Predictions** (directions, set from the literature before seeing any result):
- **P1:** at the retail case (80%), the straddle keeps under half its mid-price return on at least
  3 of the 5 funds.
- **P2:** the strip costs at least twice the ATM estimate.
- **P3:** retention is highest on SPY and lowest on USO.

These are predictions in an exploratory study, reported as made, right or wrong. They are not
registered tests of the main project.

## 11. Proving it works

- **Known-answer tests in `test_lab.py`** (fixtures in Databento's real format, blank bids
  included, as with H8):
  - a zero spread gives zero cost;
  - a flat-volatility, zero-premium world gives a mean P&L of zero;
  - straddle settlement matches hand-worked intrinsic values;
  - the margin rule matches Santa-Clara & Saretto's worked example (ATM 45-day put, S = $100, 20%
    volatility, 5% rate: initial Cboe margin $17.80);
  - the bootstrap preserves the sample mean in expectation;
  - the PPW block length is near 1 on white noise and clearly longer on an AR(1) series with
    rho = 0.5;
  - raw-versus-adjusted prices: a split fixture settles correctly only on raw prices.
- **Auditor mutants** (each must be caught):
  - lab-cap-ignored
  - lab-raw-prices-dropped
  - lab-margin-ignores-otm
  - lab-cost-roundtrip-charged
  - lab-bootstrap-iid
  - lab-writes-registered-file
- **Pressure-test checks:**
  - lab spend within its cap;
  - no lab OPRA file inside the repo;
  - the registered readers still byte-identical;
  - `lab/` imported by no registered reader.
- **Rule:** push only when `tools/audit.py` reads N of N.

## 12. Outputs, and what stays private

- **Outputs:**
  - one aggregate report (`lab/report.py`);
  - a paper section ("What the data gap costs in dollars");
  - resume bullets.
- **Credit lines:** "Data provided by Databento" on every OPRA-derived figure; Cboe's indices cited.
- **Nothing on the public site until Cboe's permission reply** (requested 10 Oct). After that, a site
  page is part of the post-November discussion.
- **Kept off the public repo:** no raw quotes, no Cboe CSVs, no paper PDFs.

## 13. Order of work

1. Read the current Cboe Margin Manual; write `lab/REGISTRATION.md`; commit it.
2. Build `costs.py`, `margin.py` and `test_lab.py` first (pure functions, known answers).
3. Buy and verify the 5 Feb 2018 test day.
4. Build `trades.py` and `fetch_lab.py`; buy the entry days; run.
5. Build `stress.py` and `report.py`; buy the stress-month daily marks; run.
6. Build `engine.py`; add the auditor mutants and pressure checks; draft the paper section and
   resume bullets with Gabriel.
