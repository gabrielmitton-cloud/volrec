# H5 — What free option data costs you sits in the WINGS, and it is the estimator's zero-bid handling rather than the quotes

**Registered:** 2026-09-19, after ONE day of wing data (18 Sep, USO, one expiry) and
before the series that tests it. What was already seen on that day is stated in full
below, so nothing here can be mistaken for a prediction made blind.
**Status:** registered.
**Sample:** `data/surface_wide.csv` from 18 Sep 2026 onward, and the matched Bloomberg
OMON wing exports in `~/Documents/volrec-bloomberg`. Never `data/iv_history.csv`.

## Why this hypothesis exists

H3 asks how well a free feed reproduces Cboe's published index. The answer so far is
"well, inside +/-30%". The interesting question the wide band opened is the one H3
cannot ask: **out in the wings, where a free indicative feed should be at its worst,
is the loss in the quotes or in the method?**

Those are different findings with different consequences. If the quotes are bad, no
estimator can fix it and free data has a hard ceiling. If the quotes are fine and the
standard treatment of a missing bid is what does the damage, then the ceiling is a
methods problem, it is fixable, and anyone building a variance estimate from retail
data is making the same mistake at a size nobody has published.

It is also the part of this project nobody with a budget measures, because a funded
desk buys OPRA and never looks at what the free feed does at 0.4x spot.

## What was already seen, 18 September 2026 — one day, USO, the 16 Oct expiry

Stated before the predictions so the reader can discount them accordingly.

- Wing mids against Bloomberg's: **0.07** of a bid-ask spread on the far puts (n=18),
  **0.40** on the far calls (n=9), against 0.25 inside the registered band (n=97).
- **13 of 18** far puts had no bid on either feed; one had a bid on the free feed only.
- Adding the wing strikes to the 16 Oct estimate lifted it by **+5.28** points on the
  free feed and **+4.91** on Bloomberg's own prices. Under Cboe's zero-bid rule the
  same lifts are **+0.94** and **+0.85**.
- On the same day TSLA, NVDA and AAPL had 0 to 1 zero-bid wing rows and their two
  columns were identical to 0.00-0.02 points. USO had 21.
- Inside +/-30%, the zero-bid rule moves every benchmarked H3 gap by <= 0.03 points.

*Bloomberg figures: Source: Bloomberg Finance L.P.*

## The hypothesis

**H5a — the quotes are fine.** Pooled over every matched wing contract across days,
the free feed's mid sits within **half a bid-ask spread** of Bloomberg's - the same
gate `bloomberg_compare.py` already applies inside the band. Wings are contracts
beyond +/-30% of spot, out of the money, quoted on both sides.

**H5b — the emptiness is real, not a free-feed artifact.** Where the free feed shows
no bid, Bloomberg shows no bid too, on **at least 80%** of matched wing contracts. A
free feed that invented or dropped bids would fail this. The 80% is set from one day's
17 of 18 concordance, and is deliberately well below it.

**H5c — the damage is the estimator's, and it shows on both vendors.** Define
*inflation* as the as-registered lift minus the Cboe zero-bid-rule lift, which
`modelfree.py --wide` prints as two columns. Prediction: inflation is **positive**,
appears on **Bloomberg's own prices too**, and the two agree within **25%** of the
free-feed value. If the inflation were a free-feed artifact, Bloomberg's prices would
not reproduce it.

**H5d — it scales with how empty the wings are, and this is the part that is mine.**
Across underlying-days, inflation rises with the **count of zero-bid wing contracts**:
a positive, significant slope regressing inflation on that count, and **under 0.05
points** on any underlying-day whose wings carry no zero bid at all. So the cost of
free data in the wings is not a property of the feed but of the contract's emptiness,
and it is predictable from a number the recorder already writes down.

## Specification — frozen here

- **Wing contract:** recorded in `data/surface_wide.csv`, i.e. beyond the registered
  +/-30% band, out of the money relative to the day's spot, with a quote on both feeds
  for anything comparing to Bloomberg.
- **Inflation:** `modelfree.py --wide`'s `as reg` column minus its `zero-bid` column,
  per underlying-day, in volatility points. Both come from the same rows and the same
  legs, so the difference isolates the zero-bid treatment.
- **Zero bid:** `bid` missing or equal to zero, on the feed in question.
- **The estimator is H3's**, unchanged, including its pair of expiries
  (`modelfree.pick_pair`). H5 changes nothing registered in H3 or H4.
- **Inference:** any pooled test demeans by date and clusters standard errors on date,
  per HANDOFF 14.3. Contract-level pooled t-statistics are descriptive only, as
  `analyze.py --simulate-surface` established.
- **Multiple testing:** if a result is ever reported as a count ("significant on k of
  n underlyings"), it carries Benjamini-Hochberg control at q=0.05
  (`analyze.benjamini_hochberg`), on date-clustered p-values.
- **Minimum evidence:** H5a and H5b need **at least three matched Bloomberg wing days**
  before any verdict; H5c and H5d need **at least 10 underlying-days** with wide rows.
  A verdict on less than that is not reported as a test.

## What would falsify each

- **H5a** fails if the pooled wing mid gap exceeds half a spread. That would mean the
  free feed's wing quotes are genuinely worse, and the ceiling is the data.
- **H5b** fails below 80% concordance.
- **H5c** fails if Bloomberg's prices do not reproduce the inflation, or if the two
  differ by more than 25%. That would make it a feed artifact, not an estimator one.
- **H5d** fails if the slope is flat or negative, or if names with no zero-bid wing
  contracts show inflation above 0.05 points.

## Honest position relative to the literature — CHECK BEFORE CLAIMING NOVELTY

The day-count episode is the precedent: a result that felt new turned out to be
textbook, and the correction cost more than the finding was worth. So, stated in
advance:

- **Cboe's own VIX methodology already excludes zero-bid options and stops after two
  consecutive zero bids.** The rule is published. This project is not discovering it.
- **Implementation error in model-free implied volatility is a studied subject** -
  Jiang & Tian on truncation and discretization error is the obvious prior art, and
  there is a microstructure literature on noise in deep out-of-the-money options.
  **None of this has been read yet.** Before any of H5 is written up as new, that
  literature gets checked the way the day count was.
- What is plausibly unpublished is the **measurement on free retail-grade data with a
  vendor cross-check on the same contracts at the same minute**: the size of the
  inflation, that it is the estimator rather than the feed, and that it is predictable
  from the zero-bid count. That is the claim to defend, and it is a measurement, not a
  discovery.

## Explicitly NOT in this hypothesis

- No claim that the free feed equals OPRA anywhere, wings included.
- No change to H3's registered estimate, its band, or its bar. H5 explains part of
  what H3's `--wide` sensitivity shows; it does not re-cut it.
- No trading claim. The wings are being measured as an instrument, not traded.
- No recorder change. H5 runs on what is already recorded.

## What it needs that does not exist yet

1. More wide days. They accumulate on their own to 11 Nov.
2. **Matched Bloomberg wing pulls on at least two more days** - the binding
   constraint, and the reason ask 1b stays at the top of `BLOOMBERG-MONDAY.md`.
   Both of the recorder's expiries, pulled within 30 minutes of the snapshot.

## Adjustment log

- *(none yet)*

## Result

Not yet tested.
