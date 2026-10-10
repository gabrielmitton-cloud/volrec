# Design memo for a faculty reader (DRAFT 3, 10 Oct 2026 - to revise with Gabriel)

**From:** Gabriel Mitton, Pepperdine University (first-year)
**To:** Professor Connie James
**Project:** volrec - github.com/gabrielmitton-cloud/volrec (site: gabrielmitton-cloud.github.io/volrec)
**What I am asking for:** your judgement on whether the design holds up (about 20 minutes to read,
and a short conversation), and whether you would act as faculty sponsor for presenting it.

## The question
Students and small investors who price options mostly use free data, because the professional feeds
cost thousands of dollars a year. Nobody has measured how much accuracy that costs. **How much
precision does free options data lose against the professional standard, and does the loss come from
the free prices themselves or from the way people turn prices into a volatility number?**

## How I test it
- **The data.** Every trading day since September 2026, my code automatically records a free data feed
  (Alpaca's) for 109 stocks and funds, and the full set of option prices for eight of them (SPY, QQQ,
  IWM, GLD, USO, TSLA, NVDA, AAPL).
- **The yardsticks.** Three professional references: the volatility indices Cboe publishes (VIX for the
  S&P 500, OVX for oil, GVZ for gold); the consolidated market feed professionals use (OPRA, bought for
  a few dollars from Databento); and Bloomberg, on four days at the library.
- **The comparison.** I apply Cboe's own published formula to the free prices and compare the result
  with Cboe's index, and with the same formula run on the professional prices. Taking the steps apart
  separates "the prices are wrong" from "the method is set up differently."
- **The discipline.** Every prediction is written down, with its pass/fail line, before the data it is
  tested on exists. Two are also frozen on the Open Science Framework (osf.io/z5gfu) so their dates
  cannot be questioned. Failures are reported as failures, and every calculation is first checked
  against a case whose answer is known.

## What it has found so far
1. **The free prices are close to the professional ones.** On the same options at the same moment, the
   free feed's volatility reading sits a few hundredths of a point from the professional feed's, on
   all eight funds (for scale, oil's volatility index is about 50). It leans slightly high on seven of
   the eight; a test registered for December and January will measure that properly.
2. **Most of the error comes from method choices.** Using only options near the current price reads
   oil's volatility about 12 points too low; widening the range cuts the gap to under 1 point. This is
   a known mathematical effect (Jiang and Tian, 2005), here measured on free data.
3. **Cboe's full method, run on the professional prices, lands close to the published index:** 0.10
   points from gold's index and 0.29 from oil's on average. The free data is being tested on exactly
   the same footing now, with results in November.
4. **One registered prediction has failed, and I report it:** a simple fix for options with no buyer did
   not bring the free estimate within half a point of the oil index.
5. **As a check that the method works at all,** it recovers a well-documented result (investors pay a
   premium for protection against volatility) on ten years of Cboe data, in 9 of 11 cases.

## Where your judgement would help most
1. **What can about two months of data honestly claim?** Daily readings are not independent, so 40
   days are worth fewer observations; I report that adjustment beside every result. Is the scope of
   my claims right?
2. **Is "method, not data" a fair conclusion?** The answer depends a little on the order in which the
   steps are taken apart, so I report every order the data allows. Does that read as convincing?
3. **Where should it go?** I plan SCCUR (November), the Seaver symposium (spring) and the Journal of
   Undergraduate Research in Finance (May). Is that the right path, and would you sponsor it?
4. **What would you check first** if you were reviewing it?

*Data credits: OPRA data provided by Databento; Bloomberg figures: Source: Bloomberg Finance L.P.
Aggregates only - no licensed data is redistributed.*
