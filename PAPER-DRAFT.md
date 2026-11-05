# The February 2027 paper: draft prose (v1, 14 Oct 2026; v2, 5 Nov 2026)

*What Does Free Options Data Cost? Measuring a Retail-Grade Feed Against Cboe's Volatility Indices*

**Status.** Draft of the sections that do not depend on the 12-19 Nov verdicts: 3 (Data), 4
(Validating the method) and 5b (the retail implementation audit). Written before H5e's final and H7's
readings exist, like the outline (PAPER-OUTLINE.md), which fixes the question and structure. Every
number below is copied from the project's dated records (README, hypothesis files, lab/REGISTRATION.md)
and must be re-checked against them before submission. Sections 1, 2 and 6 were added 5 Nov 2026 (v2), also
before the verdicts: an AI-assisted first draft (Vega) for Gabriel to rewrite in his own words, citing only
sources PAPER-OUTLINE.md already documents; every statement that depends on a verdict is a bracketed
placeholder, never a guess. Sections 5.1-5.4 and 7 are not drafted.

---

## 1. Introduction

Researchers, students and individual investors without a data budget work from free options quotes: feeds
that brokers and data sites offer at no charge. The alternative - OPRA's consolidated feed, a Bloomberg
terminal, OptionMetrics - is priced for institutions. Nobody has measured what the free route costs. If a
free feed's quotes sit close to the market's, volatility measures built on them can be trusted; if they do
not, every result built on them carries an error its author cannot see.

This paper asks one question: how much precision does free, retail-grade options data lose against the
authoritative reference, and where does the loss come from - the quotes themselves, or the choices made in
turning quotes into a volatility measure? The references are Cboe's published volatility indices (VIX, VXN,
RVX, OVX and GVZ), the consolidated market (OPRA's best bid and offer, bought by the minute from Databento)
and Bloomberg terminal snapshots. The free feed is Alpaca's indicative options data, which Alpaca itself
documents as a derivative of the OPRA feed whose quotes are not actual OPRA quotes.

[THE ANSWER, three sentences, written after the 12-19 Nov readings from the recorded verdicts. As the
evidence stood before them (PAPER-OUTLINE.md, to be confirmed or replaced): the quotes are not the main
problem - at the same minute the free feed's prices sit a small fraction of a bid-ask spread from the
consolidated market, and its empty bids are empty on the market too; most of the gap to Cboe's indices comes
from estimator choices (how many strikes are integrated, which expiries are used, how empty bids are
handled); the one feed-specific defect is stale one-sided quotes on far contracts the market no longer
quotes.]

The contribution is a measurement, not a method. Every estimator here is Cboe's or published work's, credited
where it is used (section 2). What is new is the comparison and the way it was run: each hypothesis was
committed to the public repository, with its pass/fail bar, before its test was run - for the forward-looking
tests also before their data existed, with the exceptions section 3 states - and a test that fails is reported
in the same place as one that holds. The later tests follow a protocol fixed in the repository (PROTOCOL.md);
the earlier ones were registered before it existed (section 6). Section 5's table counts
every test the project ran. The recorders, the analysis code, the registrations and every daily snapshot are
public; licensed data enters the public record only as aggregates.

Section 2 places the study against the closest work. Section 3 describes the free feed, the references and
how each was recorded. Section 4 shows the method recovering known results before it is trusted on new
data. Section 5 reports where the loss comes from: the quotes (5.1), strike coverage (5.2), empty bids in the
wings (5.3) and Cboe's own rules (5.4). Section 5b is an exploratory side study of what the same costs mean
for a retail options seller. Section 6 sets out the limitations, which belong in the main text, and section
7 concludes with what a researcher with no budget can trust, and what to fix first.

## 2. Related work

**The reference being reproduced.** Cboe's VIX methodology and its mathematics document define the
model-free variance computed here, including the strike-selection and zero-bid rules that section 5 tests
one at a time. Andersen, Bondarenko and Gonzalez-Perez (2015) show how the zero-bid truncation rule shapes
the index - the handling H5e tests - and their later work (2025) finds larger interpolation error in
monthly-only indices such as OVX and GVZ, the two indices compared most closely here.

**Why small price errors matter.** Hentschel (2003) shows that small errors in option prices become large
errors in implied volatility, worst away from the money and at short maturities: the theory for where a
free feed's error should show. Duarte, Jones and Wang (2024) show that noise in option prices biases
inference about risk premia, so data quality is an economic question, not a cosmetic one. Jiang and Tian
(2005, 2007) measure the truncation and discretization error of model-free volatility; section 5.2 measures
their mechanism on free data.

**The closest designs.** Osterrieder, Vetter and Röschli [year: confirm] replicate VIX from Cboe's own
quotes to about 0.02 index points, with timestamp mismatch the main remaining error: the floor that
authoritative data reaches, and the reason each OPRA comparison here matches the free quote's contract to
OPRA's record within 120 seconds. Comparisons with closing values carry the snapshot-to-close move instead,
measured in section 6, and the Bloomberg quotes their own capture times (section 3). Wallmeier (2024)
shows that OptionMetrics' 3:59 p.m. snapshot alone manufactures implied-volatility variation, a reason to
rule out timing before blaming a feed; section 6 measures the snapshot's distance from the close rather than
assuming it.

**Free against authoritative data.** Such comparisons exist for equities (Clayton and Schmidt 2017, Yahoo
against Nasdaq), and vendors assert untested that options data quality "is the same across providers". To
our knowledge, no study benchmarks a free retail options feed against OPRA or Cboe's indices; the dated
search log behind that statement (searches of 9 October 2026) is Appendix D.

**Validation and the side study.** Section 4 checks the method against results the literature already
holds: the variance risk premium of Carr and Wu (2009), sized by Bondarenko (2014), and delta-hedged option
gains (Bakshi and Kapadia 2003; appendix). The side study in section 5b builds on Santa-Clara and Saretto
(2009) on the spreads and margin calls that erode option writing, Muravyev and Pearson (2020) on effective
against quoted spreads, Goyal and Saretto (2009) on costs paid at entry, and Dew-Becker, Giglio, Le and
Rodriguez (2017) on why one-month variance claims are the ones priced; Bogousslavsky and Muravyev (working
paper, 2025) report retail execution costs against which section 5b's spread assumptions look pessimistic.

---

## 3. Data

**The free feed.** The study records Alpaca's free options feed, which Alpaca documents as "a free
derivative of the original OPRA feed" whose "quotes are not actual OPRA quotes." An Alpaca staff member
describes it on the company's forum as "based upon real time OPRA data but it's randomized a bit" (12
September 2025). These are staff statements, not contractual terms. The feed is therefore a documented,
deliberately altered copy of the consolidated market, and the question of this paper is what that
alteration costs once quotes are turned into a volatility number.

Three recorders capture it, each once per trading day at 14:30 New York (started by an outside trigger;
before 1 October 2026 GitHub's own scheduler ran later and unevenly, a change the results report
separately):

- an at-the-money panel of 109 tickers, chosen for spread across sectors rather than count, with the
  call nearest 30 days and nearest the money (from 4 September 2026);
- a strike surface for eight underlyings (SPY, QQQ, IWM, GLD, USO, TSLA, NVDA, AAPL): two expiries and
  forty strikes spanning ±30% of spot, with bid, ask, implied volatility, greeks, volume and open
  interest per contract (from 14 September 2026), plus wider strikes for the high-volatility names;
- the two standard monthly expiries Cboe's GLD and USO indices use (from 9 October 2026).

**The references.** Three, in increasing order of authority over the quotes:
- Cboe's published daily closes of VIX, VXN, RVX, GVZ and OVX - the authoritative model-free numbers.
  GVZ and OVX are built from GLD's and USO's own options, so those pairs compare like with like; VIX,
  VXN and RVX are built from index options (SPX, NDX, RUT), so on those pairs a gap also carries the
  small difference between an index and the fund that tracks it.
- Consolidated OPRA quotes (best bid and offer, one-minute resolution, bought from Databento) at the
  recorder's own minute, so the same contracts can be compared at the same moment.
- Bloomberg quotes on four days, from the university library's terminal.

**Safeguards.** A recorder that runs unattended can fail silently, and twice in this project a check
passed when it should not have. The recorder therefore refuses to write after the 16:00 close; separate
workflows raise an alarm on a missed day; a pressure test of more than 240 checks runs before any
change is published; and an auditor breaks every safeguard on purpose, one at a time, and requires its
check to fail. Every hypothesis was committed to the public repository, with its pass/fail bar, before
its test was run. For the forward-looking tests (H3, H5, H7) that was also before their data existed; the
validation (H1) and the H6 side study ran on history that already existed, and H5 was registered after one
day of wing data, which its file states. The two still open (H5e and H7) were also frozen on the Open
Science Framework (osf.io/z5gfu) for an independent timestamp.

**Licensing.** Recorded free-feed data is published with Alpaca's agreement for personal, non-commercial
use. Cboe's closes are read from Cboe's public files, with Cboe's permission (granted 4 November 2026),
and not republished. OPRA and Bloomberg data are
licensed: only aggregates appear here, credited "Data provided by Databento" and "Source: Bloomberg
Finance L.P."

## 4. Validating the method before using it

A measurement of error is only as good as the instrument, so each instrument is first checked against
a case whose answer is known.

**The pricer.** The Black-76 pricer satisfies put-call parity to 1.4e-14 and inverts its own prices to
1.8e-15 across the test contracts.

**The volatility estimator.** Cboe's model-free formula, applied to prices generated from a known
volatility and truncated at ±30% of spot, recovers that volatility to within 0.20 points across true
volatilities from 13% to 51%. The same estimator on real free-feed quotes depends heavily on how many
strikes it integrates. On 11 September 2026, against Cboe's published closes:

| strike band | mean absolute gap to Cboe | worst |
|---|---|---|
| ±10% (20 strikes) | 3.97 points | -12.37 |
| ±20% (30 strikes) | 1.31 | -4.39 |
| ±30% (40 strikes) | 0.59 | -1.84 |

At the widest band the free feed's SPY estimate was 15.83 against a published VIX of 15.84. Most of the
gap was truncation: a fixed ±10% band spans about 2.2 standard deviations on a 16-volatility fund but 0.6
on crude oil near 59, which is why USO read twelve points light. This is Jiang and Tian's (2005)
mechanism, measured on free data. Widening the band shows a coverage effect; it does not by itself rule
out the feed's own error, the snapshot's timing or the index-versus-fund difference, which sections 5.1,
5.4 and 6 measure separately. *(Wording narrowed 28 Oct 2026 after an outside review, M09; it read "the gap
was truncation, not data".)*

**The tests.** In simulated data with no premium by construction, the three designs simulated (the
at-the-money non-overlapping test, the surface's date aggregation and the within-day volume contrast)
reject close to their nominal 5%, under the simulation's assumptions; that is not a proof for every
registered test or every dependence structure. *(Narrowed 28 Oct 2026, outside review M09; it read "every
registered test".)* The simulation also shows why the design needs a second sample: pooling tickers on
the collected panel rejects a true null 63.8% of the time, because most days move together.

**A known result, recovered.** Before any claim about the new data, the same frozen code was run on ten
years of Cboe's own indices against their underlying funds (2016-2026, about 127 non-overlapping
one-month episodes per pair). The volatility risk premium - implied volatility above the realised
volatility that follows, in volatility points (not the variance premium, whose sample mean can differ in
sign; H2 measures that) - is significantly positive on 9 of 11 pairs (VIX/SPY +3.52 points, t = 5.14); 9 survive
Benjamini-Hochberg control and 8 the dependence-robust Benjamini-Yekutieli correction. The method finds
a well-documented result where it should, which is the precondition for trusting what it says about two
months of new data.

## 5b. What the data gap costs a retail investor (an exploratory side study)

The main results measure precision in volatility points. A reader may fairly ask what that means in
dollars. A side study answers the question for the trade most associated with selling volatility: a
short one-month at-the-money straddle on SPY, QQQ, IWM, GLD and USO, entered after each monthly
expiry and held to the next, every month from January 2016 to August 2026. Its rules, cost cases and
five predictions were committed before any data was bought (lab/REGISTRATION.md); it is exploratory and
changes no registered result.

**Design.** Entry prices are consolidated OPRA quotes at 14:30 New York (8,073 files, each checked for
completeness, sensible spreads and put-call parity against OPRA's own listings); settlement uses the
funds' raw closing prices, which an independent check matched to OPRA's implied forward within a median
0.1%. Costs follow Muravyev and Pearson (2020): the investor pays a fraction of the quoted half-spread
(0%, 30%, 80% or 100%; 80% is the headline and, on recent retail evidence, conservative), charged at
entry only because positions are held to expiry, as in Goyal and Saretto (2009). Margin follows
Santa-Clara and Saretto (2009): Cboe's customer rule (15% of the underlying for the index funds, 20% for
GLD and USO, verified against Cboe's 2008 circular for GLD), daily marking, and forced liquidation when
cash cannot meet a call. Each friction's share of the loss is its Shapley value over all 24 orders in
which the frictions can be added - the same answer the main decomposition gives to the same problem.

**Findings.**
- *Costs barely matter on liquid funds.* At a modest size (premium written = 5% of capital) a retail
  seller keeps 95, 94 and 90 cents of each paper dollar on SPY, QQQ and IWM, and 58 on USO; GLD lost
  money before any cost. The prediction that retail would keep under half failed.
- *Size changes the answer.* At 20% of capital, forced liquidation becomes the largest leak (SPY falls
  from 1.28% to 0.97% a month) - though on IWM being forced out cut losses that would have grown.
- *Retail margin is heavy on calm funds.* Goyal and Saretto (2009) find that exchange-style (SPAN)
  margin on single-stock straddles asks an initial $1.21 beyond the premium per dollar written ($1.42
  with later calls). Cboe's customer rule on these funds asks an initial $2.6-5.8 beyond the premium
  (median by fund; GLD highest, USO lowest), because a flat 15-20% of the underlying is large against a low-volatility fund's premium.
  This is an approximation (the premium is estimated from each fund's volatility index), not a lab
  measurement.
- *The risk is one month.* The trade entered 24 February 2020 cost 26% of capital on SPY and 35% on IWM
  at the modest size. Across 10,000 simulated decades the median worst drawdown is 27-48% and the
  chance of losing half the account 2-35%, conditional on the crashes in the sample.
- *No fear level at which costs eat the premium.* Spreads widen in stress - SPY's cost roughly doubles
  from calm to stressed markets - but stay a few hundredths of a volatility point against monthly swings
  of several. As a fraction of the premium, the cost rises significantly with the index only on GLD (P4
  failed, 1 of 5); on the other four the slope's interval includes zero. *(Narrowed 4 Nov 2026 after an
  outside review: it read "and widen in proportion to the premium on four of five funds", which a failed
  test for a rising fraction does not show.)*
- *Free data misjudges the cost.* Pricing costs from the free feed's wider quotes overstates the spread
  leak by 1-3 cents per dollar on the equity funds (twice the true figure on SPY).

**Two lessons for the main paper.** First, the strike strip that a model-free estimator integrates costs
2.1-3.3 times what an at-the-money estimate suggests to trade (measured with the strip held fixed), so
cost and precision both live in the wings. Second, data filters can flatter results: on GLD, adding the
tradeable excluded months back turns the straddle from -3.8% to -9.3% of premium and raises the
bootstrap odds of losing half the account from 35% to 63%. Every Leak Map, margin and stress result in the
side study is therefore reported both ways; the break-even analysis was run on the registered months only,
and says so. *(Corrected 28 Oct 2026 after an outside review: this paragraph cited USO, "+6.9% to
-2.9%", but that swing came entirely from one trade held across USO's 2020 reverse split and settled on the
wrong deliverable; settled correctly, USO's added-back figure is +7.6%. The strip ratio read 2.1-3.4. GLD's
added-back figure read -9.4% until 4 Nov 2026, a double rounding of the mean, -0.09348.)*

*Data provided by Databento (OPRA consolidated NBBO). Cboe index levels: Cboe Global Markets. Aggregates
only. Nothing here is investment advice.*

---

## 6. Limitations

These limitations bound every result above, and they belong in the main text rather than in footnotes.

**Scope.** One free feed (Alpaca's), about two months of registered readings, and eight underlyings on the
strike surface. Another free feed, a calmer or rougher market, or other underlyings could read differently:
the study measures this feed, in this period.

**Timing.** The free snapshot is taken about 80 minutes before the index's close, so every comparison with a
closing value includes the market's move in between. That distance is measured, not assumed: on 25
stress-month days per fund (lab/ OPRA data, 2016-2026) the estimator moved a median 0.53 volatility points
between 14:30 and 15:55 (GLD 0.14), large beside H7's bars of 0.25-0.30. The snapshot's time of day also
changed inside H5e's and H7's windows (GitHub's delayed scheduler until 30 September 2026, an outside 14:30
New York trigger since), so a before/after split is reported beside each pooled figure. [If H8's choice 6 is
registered and read: it compares both feeds with each index at the snapshot minute itself, which removes this
move from that one comparison.]

**Method.** American options are priced with European formulas. The decomposition in section 5.4 depends on
the order of its steps; the orderings the data allows, and their range, are reported. This project's
estimator (weekly expiries, a ±30% band, whole-day time) is not Cboe's, so a gap to Cboe's index mixes
method with data; only the same-contract, same-minute comparison with OPRA (5.1 and H8) isolates the data.

**Like for like.** VIX, VXN and RVX are built from index options (SPX, NDX, RUT) while the free feed records
the funds' options (SPY, QQQ, IWM), so H3's gaps on those three pairs include the index-versus-fund
difference. GVZ and OVX are built from GLD's and USO's own options, so H5e and H7 compare like with like.

**Statistics.** Daily gaps are persistent, so there are fewer independent observations than days; every
series reports its effective sample size, n_eff, beside its length. The bars of the tests registered before
the protocol (PROTOCOL.md) existed were set without a measured noise floor, and H5e's sat near its floor. The
intervals and n_eff printed beside each verdict were added after registration and are descriptive; each
verdict is read only against its registered bar. [Section 5's table: the Holm-adjusted column, as
disclosure.]

**The reference itself.** Cboe's methodology changes inside the ten-year validation sample of section 4
(PROTOCOL.md lists the breaks), so that section validates the method's recovery of a known result, not a
fixed index.

**Costs.** The free feed's quoted spreads are wider than OPRA's on the liquid funds (SPY about twice), so
every trading-cost yardstick in this paper, section 5b's included, comes from OPRA, never from the free
quotes.

[Any limitation a verdict exposes is added here, beside the result it qualifies.]

---

## Appendix C (draft, 16 Oct 2026): data availability, per source

*Following the Social Science Data Editors' template. Re-check every line against each provider's terms
before submission.*

- **Free feed (Alpaca Markets).** The daily snapshots are in the public repository (`data/`), with Alpaca's
  written agreement (10 Oct 2026) for personal, non-commercial use. Anyone may re-record the same feed with a
  free Alpaca account; the recorders are in the repository.
- **Cboe index closes.** Read at run time from Cboe's public files; not redistributed. Permission for this use
  was requested from Cboe on 10 Oct 2026 and granted on 4 Nov 2026 (non-commercial research, aggregate results
  only, credited). Replicators can also take the same series from FRED, which republishes them with Cboe's
  permission (VIXCLS, VXNCLS, RVXCLS, GVZCLS, OVXCLS, VXVCLS).
- **Consolidated OPRA quotes (Databento).** Licensed; not redistributed. Replicators can buy the same files
  (OPRA.PILLAR, cbbo-1m); the repository records every request and its cost. Only aggregates appear here,
  credited "Data provided by Databento".
- **Bloomberg (Pepperdine University's terminal).** Licensed; not redistributed. Derived figures only,
  credited "Source: Bloomberg Finance L.P."
- **FRED (Federal Reserve Bank of St. Louis).** The one-month Treasury rate (DGS1MO), cached; FRED's notice is
  carried in the repository.
- **Code.** MIT licence, covering the code and documentation only, not third-party data. A fresh clone
  reproduces the registered readings byte for byte after `tools/seed_frozen_rate.py` (checked 10 Oct 2026).
- **Human subjects.** None; IRB review not required.

