# Research summary for Professor Scott Baier (21 Oct 2026)

**From:** Gabriel Mitton, Pepperdine University (first-year)  
**Project:** volrec - github.com/gabrielmitton-cloud/volrec (site: gabrielmitton-cloud.github.io/volrec)  
**Mentor:** Marc Vinyard, Pepperdine University Libraries  
**What I am asking for:** your judgement as an economist on the three questions at the end (about 10
minutes to read), and, when the paper draft is ready in February, a read of it.

## The question
Students and small investors who price options mostly use free data, because professional feeds cost
thousands of dollars a year. Nobody has measured how much accuracy that costs. **How much precision does
free options data lose against the professional standard, and does the loss come from the free prices
themselves or from how prices are turned into a volatility estimate?**

## How I test it
- **Data.** Every trading day since September, my code records Alpaca's free feed: 109 tickers, and full
  strike surfaces (bid, ask, volume, open interest) for SPY, QQQ, IWM, GLD, USO, TSLA, NVDA and AAPL.
- **References.** Cboe's published volatility indices (VIX, VXN, RVX, GVZ, OVX); consolidated OPRA
  quotes at the same minute (bought from Databento); Bloomberg on four days.
- **Method.** Cboe's model-free variance formula on the free prices, compared with the index and with the
  same formula on OPRA, taken apart step by step (prices, quote filters, strike coverage, expiry choice).
- **Discipline.** Every hypothesis has a pass/fail bar written down, and dated in a public repository,
  before its test is run; the two open tests are also frozen on the Open Science Framework
  (osf.io/z5gfu, 10 Oct). Failures are reported beside successes. Every recorded result has been
  recomputed by a second program that shares no code with the first; it caught one spreadsheet-reading
  bug, which is fixed and changed no verdict.

## What it has found so far
1. **The free prices are close.** Against Bloomberg, the free feed's mid-prices sit a median 0.33 of a
   bid-ask spread away; against OPRA at the same minute, 0.50 of a spread, exactly on the registered bar.
   Where the free feed shows no bid, the market shows none either (64 of 64). A pilot on all eight funds
   reads a few hundredths of a volatility point from OPRA; the confirmatory test runs December-January.
2. **Most of the error is method.** Integrating only strikes within 10% of the price reads oil volatility
   12 points below Cboe's oil index; widening to 30% cuts the average gap across five indices from 3.97
   to 0.59 points (one calibration day). Over the registered series since then the mean gap is 0.45
   points across 125 readings, against a bar of 1.0. This is Jiang and Tian's (2005) truncation
   mechanism, measured on free data.
3. **Cboe's full method on OPRA lands 0.10 points from the gold index and 0.29 from the oil index.** The
   free data's reading on the same footing is due 12-19 November.
4. **Failures, reported:** skipping zero-bid quotes did not bring the free estimate within 0.5 points of
   the oil index (first verdict, 0.90); and implied volatility did not beat a simple trailing average at
   forecasting the next day's price range (the average won 9 of 9).
5. **Validation:** the code recovers the variance risk premium on ten years of Cboe indices (9 of 11
   pairs; 8 under the Benjamini-Yekutieli correction).

## Where an economist's judgement would help most
1. **Is "method, not data" a fair inference?** The attribution depends a little on the order of the
   steps, so I report every order the data allows (Shapley values). Is that enough, or would you frame
   the decomposition differently?
2. **Am I claiming only what two months support?** Daily readings overlap, so beside each verdict I will
   report its effective sample size and an interval, plus a multiple-testing correction across every test
   the project ran (the script is written before the November verdicts and run once after them). What
   would you want to see before believing the result?
3. **Is the reference right?** I treat Cboe's published close as truth, but my snapshot is taken about 80
   minutes before the close (measured drift: a median 0.53 points in stress months). Is measuring the
   index at my snapshot minute the right fix?

The results will be presented at SCCUR (21 November, San Diego State), and I plan to submit the paper to
the Journal of Undergraduate Research in Finance in spring 2027.

*Data credits: OPRA data provided by Databento; Bloomberg figures: Source: Bloomberg Finance L.P.
Aggregates only - no licensed data is redistributed.*
