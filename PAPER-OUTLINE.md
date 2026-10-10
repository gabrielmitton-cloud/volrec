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
- The gap: "to our knowledge, no study benchmarks a free retail options feed against OPRA or
  Cboe's indices." Backed by the dated search log in the appendix (searches of 9 Oct 2026).
  Free-vs-authoritative comparisons exist only for equities (Clayton & Schmidt 2017, Yahoo vs
  Nasdaq), and vendor pages assert data quality "is the same across providers" untested.

**3. Data (1.5 pages).**
- The free feed: Alpaca's indicative options data, recorded daily from Sep 2026. Quote Alpaca's
  own definition verbatim ("a free derivative of the original OPRA feed... not actual OPRA
  quotes"). A staff forum post says it is "randomized a bit" and another that it is sampled at
  most once a second: unofficial, labelled as reported.
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
- 5.2 *Strike coverage.* The ±10% band reads oil 12 points light; ±30% brings the mean gap to 0.59.
  Truncation scales with volatility: Jiang & Tian's mechanism, measured (H3).
- 5.3 *Empty bids in the wings.* What zero-bid quotes do to the estimate, and H5e's test.
  [H5e FINAL reading goes here, as recorded.]
- 5.4 *Cboe's own rules.* The step-by-step rebuild: data, quote rules, coverage, expiry, and what
  is left over (USO 0.29, GLD 0.10 from the close). [H7's reading goes here, as recorded.]
- 5.5 *A reconciliation, not a finding.* Implied volatilities differ by a day-count convention
  (252 vs 365 days), which is textbook.

**6. Limitations (1 page).** One free feed; about two months; eight underlyings; a snapshot about 80
minutes before the index's close; American options treated with European formulas; the bars set
before the protocol (PROTOCOL.md) existed (H5e's sat near its noise floor); few independent
observations (n_eff reported for every series); the step order of the decomposition (the
orderings the data allows, and their range); Cboe's methodology breaks inside the ten-year
validation sample (PROTOCOL.md lists them). These belong in the
paper's main text, not a footnote.

**7. Conclusion (0.5 page).** What a researcher with no budget can trust, and what to fix first.

**Appendix.**
- A. The pre-registration record: every hypothesis, its bar, its verdict and its adjustment log,
  failures included (H5e, H6a, TimesFM).
- B. Side studies: H2 (variance vs volatility), H4 (hedged gains), H6 (implied volatility against a
  trailing range).
- C. Reproducing every number: the scripts and commands, and a Data Availability statement per
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
