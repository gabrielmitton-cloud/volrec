# The February 2027 paper: outline

Drafted 9 Oct 2026, **before** the H5e final and H7 readings (due 12-19 Nov), so the results cannot
shape the framing. The question and section structure below are fixed from today. Results slot into
the places marked; a result that fails is reported in the same place as one that holds.

## Working title
*What Does Free Options Data Cost? Measuring a Retail-Grade Feed Against Cboe's Volatility Indices*

## The one question
**How much precision does free, retail-grade options data lose against the authoritative reference,
and where does the loss come from: the quotes themselves, or the choices made in turning quotes
into a volatility measure?**

Every section answers part of that question. Anything that doesn't is in the appendix.

## The answer, as the evidence stands (to be confirmed by the final readings)
The quotes are not the problem. Measured against the consolidated feed at the same minute, the free
feed's prices sit a small fraction of a bid-ask spread away, and its empty bids are empty on the
market too. Almost all of the gap to Cboe's published index comes from estimator choices: how many
strikes are integrated, which expiries are used, and how empty bids are handled. The one
feed-specific defect is stale one-sided quotes on far contracts the market no longer quotes.

## Sections

**1. Introduction (1.5 pages).** The problem: researchers without a data budget use free quotes, and
nobody measures what that costs. The question. The answer in three sentences. The contribution: a
measurement, not a new method. The methods are Cboe's and published work's, and are credited.

**2. Related work (1 page).** Short, against the closest papers (Cochrane's advice).
- Cboe's VIX methodology and its mathematics document: the reference being reproduced.
- Hentschel (2003, JFQA): small price errors become large IV errors, worst away from the money
  and at short maturities. The theory for where the free feed's error should show.
- Duarte, Jones & Wang (2024, JF): noise in option prices biases inference about risk premia.
  Why data quality is economically consequential, not cosmetic.
- Osterrieder, Vetter & Röschli: VIX replicated from Cboe quotes to about 0.02 points, timestamp
  mismatch the main error. The closest design, and the floor with authoritative data.
- Wallmeier (2024): OptionMetrics' 3:59 p.m. snapshot alone manufactures IV variation. Timing
  first, before blaming the feed.
- Jiang & Tian (2005, 2007): truncation and discretization error in model-free volatility. This
  paper's truncation result is their mechanism, measured on free data.
- Andersen, Bondarenko & Gonzalez-Perez (2015; 2025): the zero-bid handling H5e tested, and the
  larger interpolation error of monthly-only indices such as OVX and GVZ.
- Carr & Wu (2009): variance swaps and the variance risk premium, which H1 and H2 follow.
- Bakshi & Kapadia (2003): delta-hedged gains (H4, appendix).
- For section 5b (lab/): Santa-Clara & Saretto (2009, JFM 12(3)) - spreads and margin calls on S&P 500
  option writing; Muravyev & Pearson (2020, RFS 33(11)) - effective vs quoted spreads; Dew-Becker,
  Giglio, Le & Rodriguez (2017, JFE 123(2); read in the NBER w21182 version - confirm figures against
  the published text) - only one-month realised-variance risk is priced (Sharpe about -1.7 for a long
  position), which is why the lab trades one-month claims; dealer variance-swap bid-asks of 1-2% up to
  one year give an institutional benchmark for the retail costs measured (units differ; compare with
  care). Goyal & Saretto (2009, JFE 94(2), 310-326) - READ 14 Oct: single-stock options 1996-2006, sorted
  on 12-month historical minus ATM implied volatility; the long-short decile straddle earns 22.7% a month
  at mid, 3.9% when paying the full quoted spread; costs taken at entry only, held to expiry (the lab's
  convention); effective/quoted 50/75/100% (literature: below 0.5, up to 0.8-1 for large stocks); SPAN
  margin needs about $1.42 per $1 written. Rule R1 is only a cousin of their signal (a time-series 21-day
  gate on five funds, not a 12-month cross-sectional sort) - cite it as "in the spirit of", never as
  their rule. Bondarenko (2014, J. Econometrics 180(1), 81-97) - READ 15 Oct: a model-free variance
  contract on S&P 500 futures options, 1990-2009; the long side earns -26.30% a month (only -2.72 of it
  explained by market beta); selling it has a monthly Sharpe ratio of 0.42, about 5x the market's and
  1.6-1.8x selling ATM puts. The size anchor for H1's recovered premium. He also shows the traded
  contract is DISCRETELY sampled realised variance (daily returns), not integrated variance - the
  lab's variance-swap cross-check uses daily returns, the right target - and that hedging errors are
  very sensitive to rebalancing timing. Bogousslavsky & Muravyev (working paper, SSRN 4682388, 9 Feb 2025) - READ 14 Oct:
  no fund-option effective/quoted ratio, but retail trades lose 0.9% against a 3.7% quoted spread
  (limit orders), so the lab's 80% retail case is likely pessimistic; $0.65 commission confirmed.
- The gap: "to our knowledge, no study benchmarks a free retail options feed against OPRA or
  Cboe's indices." Backed by the dated search log in the appendix (searches of 9 Oct 2026).
  Free-vs-authoritative comparisons exist only for equities (Clayton & Schmidt 2017, Yahoo vs
  Nasdaq), and vendor pages assert data quality "is the same across providers" untested.

**3. Data (1.5 pages).**
- The free feed: Alpaca's indicative options data, recorded daily from Sep 2026. Quote Alpaca's
  own definition verbatim ("a free derivative of the original OPRA feed... not actual OPRA
  quotes", docs page "Historical Option Data", read 12 Oct 2026). Alpaca staff on the community
  forum (Dan_Whitnable_Alpaca; staff statements, not contractual terms, labelled as such), checked
  at source 12 Oct 2026:
  - 12 Sep 2025 (forum t/17795): "based upon real time OPRA data but it's randomized a bit."
  - 1 Feb 2026 (same thread): it "can vary from the actual `opra` data."
  - 4 Jul 2024 (forum t/14595), the balancing line: "isn't exactly 'dummy' or random values... rather
    'close' or 'indicative' of the actual OPRA data."
  - Another post says it is sampled at most once a second (unofficial, labelled as reported).
  This frames the paper: the free feed is a documented, deliberately altered derivative of OPRA,
  and the project measures what that alteration costs once quotes become a volatility number.
  H8 measures it directly (same contracts, same moment, the registered estimator); the pilot
  reads a few hundredths of a point, high on 7 of 8 funds.
- The references: Cboe index closes; OPRA consolidated quotes (Databento); Bloomberg on four days.
- The recorder's design, and its safeguards: after-close guard, missed-day alarms, pre-registration.
- Licensing: aggregates only, with the credit lines.

**4. Validating the method before using it (1.5 pages).**
- Known-answer calibration: model-free variance on a known volatility, the pricer, test size.
- H1: the variance risk premium recovered on ten years of Cboe indices (9 of 11 pairs; 8 under BY).
  It shows the code finds a known result before it is trusted on new data.

**5. Results: where the loss comes from (the core, 4-5 pages).** Opens with ONE table of every
registered test: its bar, its window, its verdict, failures included. Then the magnitudes, each
with an interval.
- 5.1 *The quotes.* Free versus OPRA at the same minute, and versus Bloomberg (H5a, H5b, H5f).
  Prices within a fraction of a spread; empty bids match the market.
  [H8's confirmatory reading goes here, 1 Dec 2026 - 29 Jan 2027, all eight funds; registered after
  the November verdicts under PROTOCOL.md - see H8-DRAFT.md.]
- 5.2 *Strike coverage.* The ±10% band reads oil 12 points light; ±30% brings the mean gap to 0.59.
  Truncation scales with volatility: Jiang & Tian's mechanism, measured (H3).
- 5.3 *Empty bids in the wings.* What zero-bid quotes do to the estimate, and H5e's test.
  [H5e FINAL reading goes here, as recorded.]
- 5.4 *Cboe's own rules.* The step-by-step rebuild: data, quote rules, coverage, expiry, and what
  is left over (USO 0.29, GLD 0.10 from the close). [H7's reading goes here, as recorded.]
- 5.5 *A reconciliation, not a finding.* Implied volatilities differ by a day-count convention
  (252 vs 365 days), which is textbook.

**5b. What the data gap costs a retail investor (exploratory side study, 1-1.5 pages).** From
`lab/` (design: docs/superpowers/specs/2026-10-12-retail-vrp-audit-design.md; rules and predictions
committed before any data: lab/REGISTRATION.md). Short one-month ATM straddles on SPY, QQQ, IWM, GLD,
USO, every month Jan 2016 - Aug 2026, priced on OPRA (Databento), settled on raw closes, under Cboe
customer margin with daily marking (Santa-Clara & Saretto 2009's mechanic) and four cost levels
(Muravyev & Pearson 2020's published fractions). Report, in order:
- The Leak Map: at a modest size a retail seller keeps 95 / 94 / 90 cents per paper dollar on SPY /
  QQQ / IWM and 58 on USO; GLD loses before costs. At a 20% size forced liquidation becomes the
  largest leak (SPY 1.28 -> 0.97 %/month). Every friction credited by Shapley value over all orders,
  range beside it - the same answer as section 5's decomposition.
- The tail: the COVID trade cost 26-35% of the account in one month at the modest size; ten-year
  ruin odds 2-35% (stationary bootstrap, conditional on the sample's crashes).
- The Break-Even VIX: none reliable - costs roughly double in stress but stay hundredths of a point
  on the equity funds, while the premium swings by several points.
- The strip-versus-ATM cost ratio (2.1-3.4x, P3 holds on 5 of 5) - directly relevant to section 5,
  since the registered estimator is a strip.
- Predictions as recorded: P1 fails, P2 holds as written, P3 holds, P4 fails, P5 holds among funds
  with a paper profit. Exclusions cluster in crash months; with them added back USO and GLD turn
  worse - always shown beside the registered numbers.
Framing: an implementation audit, not a strategy. Nothing here is investment advice.

**6. Limitations (1 page).** One free feed; about two months; eight underlyings; a snapshot about 80
minutes before the index's close; American options treated with European formulas; the bars set
before the protocol (PROTOCOL.md) existed (H5e's sat near its noise floor); few independent
observations (n_eff reported for every series); the step order of the decomposition (the
orderings the data allows, and their range); Cboe's methodology breaks inside the ten-year
validation sample (PROTOCOL.md lists them); the snapshot's time of day changed inside H5e's and
H7's windows (GitHub's delayed cron until 30 Sep, the 14:30 New York trigger since), so a
before/after split is reported beside the pooled figure; the snapshot's distance from the close is
measured, not assumed: on 25 stress-month days per fund (lab/ OPRA, 2016-2026) the estimator moved a
median 0.53 volatility points between 14:30 and 15:55 (GLD 0.14) - large beside H7's 0.25-0.30 bars; VIX, VXN and RVX are built from index
options (SPX, NDX, RUT) while the free feed records the funds' options (SPY, QQQ, IWM), so H3's gaps
on those three pairs include the index-versus-fund difference (GVZ and OVX are built from GLD's and
USO's own options, so H5e and H7 are like for like); the free feed's quoted spreads are wider than
OPRA's on the liquid funds (SPY about twice), so any trading-cost yardstick comes from OPRA, never
from the free quotes. These belong in the
paper's main text, not a footnote.

**7. Conclusion (0.5 page).** What a researcher with no budget can trust, and what to fix first.

**Appendix.**
- A. The pre-registration record (OSF: https://osf.io/z5gfu for H5e and H7): every hypothesis, its bar, its verdict and its adjustment log,
  failures included (H5e, H6a, TimesFM).
- B. Side studies: H2 (variance vs volatility), H4 (hedged gains), H6 (implied volatility against a
  trailing range).
- C. Reproducing every number: the scripts and commands (a fresh clone reproduces the registered
  readings byte-for-byte after `tools/seed_frozen_rate.py`, checked 10 Oct 2026), and a Data Availability statement per
  source (Social Science Data Editors' template README): what each licence allows, and that the
  raw licensed data is not in the package.
- D. The literature search log: what was searched, when, and what was found (9 Oct 2026 reports).

## Where it goes (checked 9-10 Oct 2026; confirm each before submitting)
- **SCCUR, 21 Nov 2026 (San Diego State).** Preliminary results allowed; abstract window closed
  9 Oct 11:59 p.m. A poster or talk of the November readings.
- **Seaver Research and Scholarly Achievement Symposium, spring 2027.** On campus.
- **Journal of Undergraduate Research in Finance.** The best fit: welcomes replications, blind
  faculty review, no revisions (accept or reject, with a referee report), $1,000 Bertus Prize.
  The 2026 deadline was 31 May; expect late May 2027.
- **IAES Best Undergraduate Paper Award.** 2026 deadline 16 June; Word files only; needs a mentor
  letter; the paper must not be submitted elsewhere at the same time - so JURF *or* BUPA in a
  given cycle, not both.
- Most venues need a faculty sponsor: ask one this semester (DESIGN-MEMO.md is the ask).

## Length and style
Twelve to fifteen pages plus appendix. Figures: the truncation curve, the gap decomposition, and
the price-agreement table. Every number in the text comes from a script in the repository.
