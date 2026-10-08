# Pre-registered hypotheses

One file per hypothesis, named `YYYY-MM-DD-hN-slug.md`, **written and committed
before the join that tests it is ever run**. The commit date is the evidence
that it was pre-registered; that is the whole point of this directory.

## The rules these files exist to enforce

1. **Write the hypothesis before running the join.** Date it. Commit it.
2. **Log every post-hoc adjustment** to a threshold, window, or category set in
   the same file, with a timestamp. That is the p-hacking engine starting up and
   it is much easier to start now that an annotation layer exists.
3. **Three or more adjustments to one hypothesis = abandon it**, and report the
   abandonment in the write-up. An abandoned hypothesis honestly reported is
   worth more than a surviving one that was quietly reshaped.
4. **Nothing moves from `/annotations/` to `/features/` without a hypothesis
   here, dated before the join.** See `annotations/README.md`.
5. **Any pooled test across tickers demeans the cross-section by date and
   clusters standard errors on date.** Undemeaned pooling rejected a *true null*
   63.8-93.0% of the time in this project's own simulation (`analyze.py
   --simulate`). This is not a stylistic preference.

## Status

| id | hypothesis | registered | tested | outcome |
|---|---|---|---|---|
| H1 | VRP is positive on Cboe vol indices, 2016-2026 | 2026-09-06 | 2026-09-07 | H1a holds (9/11, p<0.05); H1b holds but mixed, read the caveat; H1c holds |
| H4 | Hedged gains negative, vary by moneyness, relate to volume | 2026-09-13 | not yet | registered before surface.csv had any rows; **strike 2 of 3** on 8 Oct (calendar carry, BK dividends; strike 1 on 23 Sep: runs break on a missed trading day) |
| H3 | Free-data model-free variance reproduces the Cboe index | 2026-09-12 | series running | H3a mean abs gap 0.40 over 80 readings (8 Oct; was 0.53 over 30 on 23 Sep); first wide reading OUTSIDE its bracket - contamination, as the registered grid anticipated |
| H5 | The cost of free data is in the wings, and it is the estimator's zero-bid handling, not the quotes | 2026-09-19 | H5a holds weakly, H5b holds (23 Sep) | H5a and H5b at their three-day minimum: 0.40 of a spread pooled (0.67 where both feeds bid), 36 of 36 missing bids shared; registered after one wing day, which the file states in full; H5e (23 Sep, judged from 23 Sep) and H5f (23 Sep, before any OPRA data) added; H5e's estimator is ABG (2015)'s RX*; **H5e first verdict FAILS (8 Oct): 0.90 vs 0.5, 2 of 10** |
| H2 | Variance rather than volatility formulation, per Carr & Wu (2009) | 2026-09-09 | 2026-09-09 | H2a holds but raw variance is weakest (t=2.1) and log variance strongest (t=16.3); H2b NOT supported; registered, still unadopted |
| H6 | Implied vol forecasts next-day range better than a technical-levels rule (ATR 14) | 2026-10-08 | not yet | long Cboe-index sample primary (CLAUDE.md: no forecaster evaluation on the live panel alone); live panel descriptive; join built after registration |
| H7 | The free feed through Cboe's own rules reproduces OVX/GVZ | 2026-10-08 | window 9 Oct - 11 Nov | registered before the first monthly-leg row, as an exception to the 11 Nov rule (Gabriel); ~$1 of OPRA approved |

*Bloomberg figures: Source: Bloomberg Finance L.P. OPRA figures: Data provided by Databento. Aggregates only.*
