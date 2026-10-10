# Design memo for a faculty reader (DRAFT 2, 10 Oct 2026 - to revise with Gabriel)

**From:** Gabriel Mitton, Pepperdine University (first-year)
**Project:** volrec - github.com/gabrielmitton-cloud/volrec (site: gabrielmitton-cloud.github.io/volrec)
**What I am asking for:** 20 minutes of your reading and a short conversation about whether the design
holds up, before the results are written up in February 2027.

## The question
How much precision does free, retail-grade options data lose against the authoritative reference, and
does the loss come from the quotes themselves or from the choices made in turning quotes into a
volatility measure?

## Why it matters
Students and small researchers price options from free indicative quotes because consolidated data
and OptionMetrics are out of reach. Nobody measures what that costs. Cboe publishes model-free
volatility indices (VIX, OVX, GVZ and others) for the same underlyings, so the free feed can be
checked against the authoritative number, day by day.

## Design
- **Data:** I record the free feed (Alpaca) every trading day since September 2026: an at-the-money
  panel for 109 tickers, and a ±30% strike surface for 8 underlyings with volume and open interest.
  References are Cboe's index closes, OPRA consolidated quotes at the same minute (Databento), and
  Bloomberg on four days (aggregates only, per the library's terms).
- **Method:** Cboe's own published variance formula, applied to the free quotes, compared with the
  published index. A step-by-step rebuild separates the parts of the gap: the quotes, Cboe's quote
  rules, strike coverage, expiry choice, and what remains.
- **Discipline:** each hypothesis is written down and committed (dated) before its data exists. Bars
  are fixed in advance. Changes made after seeing results are logged, and three of them abandon the
  hypothesis. Failures are reported. Every instrument is checked against a known answer, and every
  safety check is broken on purpose to prove it fails.

## What it has found so far
- The free feed's prices match the consolidated market's to a small fraction of the bid-ask spread,
  and its empty bids are empty on the market too.
- A ±10% strike band reads oil volatility 12 points light, and ±30% cuts the average gap to 0.6
  points. The bias grows with volatility, which is Jiang & Tian's truncation mechanism, measured
  here on free data.
- Rebuilt with Cboe's own rules on consolidated quotes, the estimate lands 0.10 points from the gold
  index (GVZ) and 0.29 from the oil index (OVX). It is measured about 80 minutes before the index's
  close.
- One registered test failed and is reported as failed: skipping empty-bid quotes did not bring the
  free estimate within 0.5 points of OVX.
- As validation, the method recovers the documented volatility risk premium on ten years of Cboe
  data (9 of 11 pairs).

## Where I would value your judgement
1. Is "estimator choices, not data quality" a fair reading of the decomposition, given the order of
   the steps affects how much each one appears to explain? My plan is to report every ordering
   the data allows and its range (Shapley where possible). Some orderings cannot exist: the free
   feed has no full strike chain, so "free quotes, every strike" cannot be computed.
2. Two months of daily data and eight underlyings: what can and cannot honestly be claimed from it?
3. The snapshot is about 80 minutes before the index's close. Is the remaining 0.29 better presented
   as timing noise, or should it be tested with intraday index data (available through LSEG)?
4. Is this the right shape for an undergraduate empirical paper? The venues I have found are
   SCCUR (November), the Seaver symposium (spring), the Journal of Undergraduate Research in
   Finance (late May) and the IAES undergraduate award (June). Would you be willing to act as
   faculty sponsor, which most of them require?
5. What would you check first if you were refereeing it?
6. Alpaca's terms forbid republishing its data without written consent, and Cboe's index
   disclaimers restrict using index values "to verify or correct other data". I am asking both
   in writing. Is that the right way to handle it for a public replication package?
