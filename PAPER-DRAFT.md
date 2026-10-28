# The February 2027 paper: draft prose (v1, 14 Oct 2026)

*What Does Free Options Data Cost? Measuring a Retail-Grade Feed Against Cboe's Volatility Indices*

**Status.** Draft of the sections that do not depend on the 12-19 Nov verdicts: 3 (Data), 4
(Validating the method) and 5b (the retail implementation audit). Written before H5e's final and H7's
readings exist, like the outline (PAPER-OUTLINE.md), which fixes the question and structure. Every
number below is copied from the project's dated records (README, hypothesis files, lab/REGISTRATION.md)
and must be re-checked against them before submission. Sections 1, 2, 5.1-5.3, 6 and 7 are not drafted.

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
use. Cboe's closes are read from Cboe's public files and not republished. OPRA and Bloomberg data are
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
  of several, and widen in proportion to the premium on four of five funds.
- *Free data misjudges the cost.* Pricing costs from the free feed's wider quotes overstates the spread
  leak by 1-3 cents per dollar on the equity funds (twice the true figure on SPY).

**Two lessons for the main paper.** First, the strike strip that a model-free estimator integrates costs
2.1-3.4 times what an at-the-money estimate suggests to trade, so cost and precision both live in the
wings. Second, data filters can flatter results: months excluded for mechanical data reasons clustered
in crashes, and adding the tradeable ones back turned USO's result from +6.9% to -2.9% of premium.
Every result in the side study is therefore reported both ways.

*Data provided by Databento (OPRA consolidated NBBO). Cboe index levels: Cboe Global Markets. Aggregates
only. Nothing here is investment advice.*

---

## Appendix C (draft, 16 Oct 2026): data availability, per source

*Following the Social Science Data Editors' template. Re-check every line against each provider's terms
before submission.*

- **Free feed (Alpaca Markets).** The daily snapshots are in the public repository (`data/`), with Alpaca's
  written agreement (10 Oct 2026) for personal, non-commercial use. Anyone may re-record the same feed with a
  free Alpaca account; the recorders are in the repository.
- **Cboe index closes.** Read at run time from Cboe's public files; not redistributed. Permission for this use
  was requested from Cboe on 10 Oct 2026. If Cboe does not grant it, the same series are available from FRED,
  which republishes them with Cboe's permission (VIXCLS, VXNCLS, RVXCLS, GVZCLS, OVXCLS, VXVCLS), and the
  results would be re-sourced there, as a logged change.
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

