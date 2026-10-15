# Design memo for Dr. Levon Goukasian (15 Oct 2026)

**From:** Gabriel Mitton, Pepperdine University (first-year)  
**Project:** volrec - github.com/gabrielmitton-cloud/volrec (site: gabrielmitton-cloud.github.io/volrec)  
**What I am asking for:** whether you would act as faculty mentor, and your judgement on the four
questions at the end (about 15 minutes to read).

## The question
Students and small investors who price options mostly use free data, because professional feeds cost
thousands of dollars a year. Nobody has measured how much accuracy that costs. **How much precision does
free options data lose against the professional standard, and does the loss come from the free prices
themselves or from how prices are turned into a volatility estimate?**

## What I took from our meeting on 11 September
You told me to collect raw option prices and volume, not derived implied volatility, across strikes
around the money, and to prove the method on one name before scaling. I did. Two details changed on
measurement, and both are logged: Bloomberg keeps only about 90 days of option history, so the long
history comes from consolidated OPRA quotes (bought from Databento) instead; and a +/-10% strike band
read oil volatility 12 points low, so the band is +/-30%.

## How I test it
- **Data.** Every trading day since September, my code records Alpaca's free feed: 109 tickers, and full
  strike surfaces (bid, ask, volume, open interest) for SPY, QQQ, IWM, GLD, USO, TSLA, NVDA and AAPL.
- **References.** Cboe's published indices (VIX, VXN, RVX, GVZ, OVX); OPRA consolidated quotes at the
  same minute; Bloomberg on four days.
- **Method.** Cboe's model-free variance formula on the free prices, against the index and against the
  same formula on OPRA, taken apart step by step (prices, quote filters, strike coverage, expiry choice).
- **Discipline.** Every hypothesis has a pass/fail bar fixed before its data exists (two also frozen on
  the Open Science Framework, osf.io/z5gfu). Failures are reported. Each calculation is first checked on
  a case whose answer is known.

## What it has found so far
1. **The free prices are close.** Same contracts, same minute: a few hundredths of a volatility point
   from OPRA on all eight funds, leaning slightly high on seven. A confirmatory test runs Dec-Jan.
2. **Most of the error is method.** Strike truncation explains the oil gap (Jiang and Tian's 2005
   mechanism, measured on free data).
3. **Cboe's full method on OPRA lands 0.10 points from GVZ and 0.29 from OVX.** The free data's
   reading on the same footing is due 12-19 November.
4. **One registered prediction failed,** and is reported: skipping zero-bid quotes did not bring the
   free estimate within 0.5 points of OVX.
5. **Validation:** the code recovers the variance risk premium on ten years of Cboe indices (9 of 11
   pairs; 8 under the Benjamini-Yekutieli correction).
6. **A side study, in dollars:** short one-month ATM straddles on five funds, 2016-2026, priced on OPRA
   under Cboe customer margin with forced liquidation (Santa-Clara and Saretto's 2009 mechanic) and
   Muravyev and Pearson's cost fractions. A retail seller keeps 90-95 cents of each paper dollar on SPY,
   QQQ and IWM; the real risk is single crash months (February 2020 cost 26-35% of capital at a modest
   size), not trading costs.

## Where your judgement would help most
1. **Is the reference right?** I treat Cboe's published close as truth, but my snapshot is at 14:30 New
   York. Marc Vinyard found intraday OVX and GVZ on Bloomberg; is measuring the index at my snapshot
   minute the right fix, or is there a better one?
2. **Is "method, not data" a fair inference?** The attribution depends a little on the order of the
   steps, so I report every order the data allows (Shapley values). Is that enough?
3. **Am I claiming only what two months support?** Daily readings overlap, so I report effective sample
   sizes. What would you want to see before believing the result?
4. **Would you act as faculty mentor?** SCCUR (21 November, abstract under review), the Seaver symposium
   in spring, and the Journal of Undergraduate Research in Finance in May. In practice: a short
   conversation now, a look at the paper draft in February, and a mentor letter if a venue requires one.

*Data credits: OPRA data provided by Databento; Bloomberg figures: Source: Bloomberg Finance L.P.
Aggregates only - no licensed data is redistributed.*
