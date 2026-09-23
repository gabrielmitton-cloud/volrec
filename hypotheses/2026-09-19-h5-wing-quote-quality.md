# H5 — What free option data costs you sits in the WINGS, and it is the estimator's zero-bid handling rather than the quotes

**Registered:** 2026-09-19, after ONE day of wing data (18 Sep, USO, one expiry) and
before the series that tests it. What was already seen on that day is stated in full
below, so nothing here can be mistaken for a prediction made blind.
**Status:** registered. **H5a and H5b tested 23 Sep 2026** - H5b holds, H5a holds weakly (see Result).
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

## H5e — registered 23 September 2026, BEFORE that day's run; out of sample from 23 Sep

**Why it exists, stated first because it was motivated by data.** On 18, 21 and 22 Sep
a diagnostic that was NOT pre-registered - USO's wide estimate with every zero-bid
quote skipped and no stop rule - landed on OVX at **+0.23, -0.24 and -0.00**, while
the registered estimator sat at -1.18, -1.09 and -1.00. Three days, chosen after the
fact, prove nothing. So the diagnostic is registered here as a prediction and judged
**only on days that did not exist when it was written**: from Wed 23 Sep 2026, whose
surface run had not fired at the time of this commit (the commit time is the proof).

**H5e.** From 23 Sep 2026 through the end of the window (Wed 11 Nov), USO's 30-day
model-free estimate built from `surface.csv` plus `surface_wide.csv`, with every
out-of-the-money zero-bid quote skipped and no stop rule, tracks the published OVX
with a **mean absolute gap under 0.5 volatility points**, AND sits **closer to OVX than
the registered estimate on a majority of days**.

- **Estimator:** `modelfree.model_free_30d(rows, r, "skip")`, H3's pair of expiries,
  H3's everything else. Only the zero-bid handling differs.
- **Bar:** 0.5 points, half of H3a's 1.0 budget - the same share `calibrate.py`
  allows method error. Set from outside this data, not from the in-sample 0.16.
- **Minimum:** 10 counted days before any verdict. `modelfree.py --wide` prints the
  running tally and marks the three in-sample days as not counted.
- **Falsified** if the mean absolute gap is 0.5 or more, or if skip-only is not
  closer than the registered estimator on a majority of counted days.

**Why this matters if it holds.** It is the constructive half of H5: the wing quotes
are usable, the standard zero-bid treatment is what breaks the estimate, and a
treatment that simply drops one-sided stub quotes lets free data track Cboe's own
index on the name where it was worst. **What it would not show:** that skip-only is
right in general. Cboe's stop rule exists for dense, regular SPX ladders; the
finding would be about sparse ETF ladders with stub quotes on odd strikes.

## The second wide pull, 22 September 2026 — AFTER data

USO and TSLA OMON, **16 Oct only** (the recorder's other expiry, 23 Oct, was not
pulled), 18:46 UTC against the recorder's 18:22 snapshot, a 24-minute gap.

| | matched, band | mids vs spread, band | put wing | call wing | zero bid on both / one only |
|---|---|---|---|---|---|
| USO | 107 | 0.39 | 0.09 (n=12) | 0.00 (n=9) | 7 / 0 |
| TSLA | 98 | **0.87 - FAILS the 0.5 gate** | 1.00 (n=18) | 1.00 (n=15) | 0 / 0 |

- **TSLA's failure is stated as a failure.** The diagnosis: TSLA's parity forward was
  380.80 on the free feed and 380.28 on Bloomberg's prices, a 0.14% move in 24
  minutes, and the signature is a move rather than a bad feed (calls +$0.155 on the
  free feed, puts -$0.03; a bad feed pushes both one way). In the wings TSLA's far puts
  are three cents wide, so a two-cent difference is most of a spread: the half-spread
  metric is coarse for one-tick markets. Neither point re-scores anything. The lesson
  is operational: pull TSLA within ~10 minutes of the snapshot.
- **H5c on this day:** inflation (as registered minus Cboe rule) is 5.01 on the free
  feed and 3.51 on Bloomberg for USO - a 30% difference, outside H5c's 25% (18 Sep was
  6.5%). TSLA's is 0.00 on both, exactly as H5d predicts for wings with no zero bids.
- **The Cboe stop rule cut the registered band on 22 Sep.** USO's 23 Oct leg carried
  one-sided stubs (no bid, $2.92-3.29 ask) at P119, P122 and P124, beside two-sided
  P120 and P124.5. Walking outward, the rule stopped at P122 and dropped every put
  below it, moving USO's +/-30% estimate by **-2.75**. The claim in H3 on 18 Sep that
  the rule moves the band by 0.03 at most held for 14-21 Sep (USO -0.12 on 18 Sep) and
  **fails on 22 Sep**. This is why H5e skips rather than stops.
- **Status:** two matched Bloomberg wing days (18 and 22 Sep), three symbol-days.
  H5a and H5b need three days. H5d's 10 underlying-days now exist (USO, TSLA, NVDA and
  AAPL on 18, 21 and 22 Sep) but sit on three dates, too few for the date-clustered
  test the specification requires; the pattern so far is descriptive only.

*Bloomberg figures: Source: Bloomberg Finance L.P.*

## H5f — registered 23 September 2026, BEFORE any OPRA data was requested

H5a-H5c name Bloomberg, and two matched Bloomberg days in a week is the constraint on
H5. OPRA's consolidated NBBO, bought historically from Databento at one-minute
resolution, can be matched at the recorder's own minute on every recorded day. Letting
OPRA count toward H5a-c after the fact would be an adjustment, so its predictions are
registered here first. At this commit no Databento account exists and no OPRA quote
has been seen; the commit time is the proof.

Reference: `tools/opra_reference.py`, dataset OPRA.PILLAR, schema `cbbo-1m`, each
recorded contract matched to the OPRA record nearest its own quote time within 120
seconds (unmatched contracts are excluded and counted). Every day with wide data from
18 Sep 2026 through Wed 11 Nov 2026, USO and TSLA.

- **H5f-a.** Pooled over every matched wing contract (beyond +/-30%, out of the money,
  an OPRA ask present), the median free-feed mid sits within **half an OPRA bid-ask
  spread** of OPRA's mid.
- **H5f-b.** Where the free feed shows no bid, OPRA shows no bid either, on **at least
  80%** of matched wing contracts.
- **H5f-c.** On underlying-days whose wings carry zero-bid quotes, the inflation (as
  registered minus Cboe rule) computed from OPRA's prices on the recorder's own
  strikes is positive and, at the median across those days, within **25%** of the
  free feed's.

The three thresholds are H5a-c's, copied, not chosen again. **Minimum:** five days with
OPRA data before any verdict. The registered-band comparison (inside +/-30%) is also
printed and is descriptive only: H3's feed-quality question, not a hypothesis here.
**Falsified** exactly as H5a-c are, with OPRA in Bloomberg's place.

## The first OPRA comparison, 23 September 2026 — AFTER data, 2 of H5f's 5 days

Fetched from Databento on 23 Sep for $0.0273 (USO and TSLA, 18 and 21 Sep); 22 Sep is
not yet served historically (anything after 22 Sep 13:30 UTC needed a live licence the
next morning) and is retried later. Each contract matched to OPRA within seconds of its
own quote time (median 5-26 s). Mid gaps are medians, as a fraction of OPRA's spread;
lifts use only contracts both feeds quote, so they differ from `modelfree.py --wide`.

| | band | put wing | call wing | zero bid, both / one only | inflation, free / OPRA |
|---|---|---|---|---|---|
| USO 18 Sep | 0.06 | **0.02** | 0.40 | 13 / 0 | 3.50 / 3.49 |
| USO 21 Sep | 0.12 | **0.03** | 0.50 | 9 / 0 | 15.97 / 16.19 |
| TSLA 18 Sep | 0.47 | 0.83 | 0.50 | 0 / 0 | 0.00 / 0.00 |
| TSLA 21 Sep | 0.50 | 0.50 | 0.75 | 0 / 0 | 0.00 / 0.00 |

- **USO's free quotes sit on the consolidated market** at the same minute, and every
  no-bid quote on the free feed is a no-bid quote on OPRA (22 of 22).
- **The inflation reproduces on OPRA to within 0.3% and 1.4%** - the estimator's, not
  the feed's. Descriptive: H5f needs five days.
- **A correction to the 22 Sep section.** TSLA reads 0.47-0.83 of a spread against
  OPRA *thirteen to twenty-three seconds apart*, so its 0.87 against Bloomberg was not
  only the 24-minute drift, as that section said. TSLA's options are a cent or two
  wide, and a one-tick difference is a whole spread: the half-spread metric is coarse
  for one-tick markets. That is a property of the registered metric, stated, not
  re-scored. H5f-a will read TSLA's wings through the same coarse lens.
- **Unmatched, and why.** USO 18 Sep: 44 (5 free quotes 7-8 minutes stale, 39 symbols
  absent from OPRA's file, 29 of them deep in-the-money calls from the wide pass that
  never enter the integral). USO 21 Sep: 16 (1 stale, 15 absent - **13 of them far
  out-of-the-money puts with no bid, P60-P72**, the stub region itself). Whether OPRA
  omits a contract with no quote on either side, or the listing differs, is not yet
  known; Databento's `definition` schema can settle it for cents. Until then, H5f-b
  is silent on those 13.

*Data provided by Databento (OPRA consolidated NBBO). Aggregates only.*

## The unmatched contracts are listed, and the free feed's quotes on them are stale — 23 Sep, AFTER data

Databento's `definition` schema ($0.018 for two days) lists every OPRA instrument per
day. **Every unmatched contract is a real OPRA listing** - 15 of 15 on 21 Sep, 39 of 39
on 18 Sep - so the free feed does not invent contracts. But the out-of-the-money ones
(13 on 21 Sep, 9 on 18 Sep) had **no consolidated quote at all** in the five-minute
window, and the free feed's quote on each was **stale: median 91 minutes old on 21 Sep
and 130 minutes on 18 Sep, up to five hours**, every one of them one-sided, asks from
$0.02 to $2.16.

This refines H5's claim and must be stated beside any verdict:

- **Where both feeds quote a contract, the free feed matches OPRA** (0.02-0.03 of a
  spread in the put wing).
- **In the far wing the free feed also carries hours-old one-sided quotes on
  contracts nobody is quoting.** Part of the as-registered contamination is therefore
  a feed artifact - stale indicative asks - and not purely the estimator's zero-bid
  treatment of live quotes.
- **H5f's registered rule excludes unmatched contracts, so it cannot see the free
  feed's worst quotes.** An H5f pass would describe the quotes both feeds carry, not
  the whole wing. Stated now, before H5f has its five days; the rule is not changed.
- **H5e is unaffected:** these quotes have no bid, and skip-only drops them.
- The registered surface's staleness check (`panel_health`, 0.1-0.3% of rows over 15
  minutes) covers `surface.csv` only; the wide file's far wing is where staleness
  lives.

*Data provided by Databento (OPRA). Aggregates only.*

## The third matched wing day, 23 September 2026 — AFTER data

USO and TSLA OMON, **both of the recorder's expiries** (23 Oct, 30 days; 30 Oct, 37
days), pulled 18:41-18:45 UTC against the recorder's snapshot at 18:41 UTC (median
quote time 18:41:25-31): **0 to 4 minutes apart**, the closest match yet. Every check
in `bloomberg_compare.py` passes.

| | expiry | matched, band | mids vs spread, band | put wing | call wing | zero bid on both / free only / Bloomberg only |
|---|---|---|---|---|---|---|
| USO | 23 Oct | 133 | 0.31 | 0.01 (n=8) | 0.19 (n=6) | 8 / 0 / 0 |
| USO | 30 Oct | 54 | 0.20 | 0.01 (n=8) | 0.66 (n=6) | 8 / 0 / 0 |
| TSLA | 23 Oct | 86 | 0.28 | 0.33 (n=12) | 0.83 (n=19) | 0 / 0 / 0 |
| TSLA | 30 Oct | 75 | 0.20 | 0.33 (n=13) | 0.67 (n=16) | 0 / 0 / 0 |

- **H5c on this day, descriptive:** USO's inflation (as registered minus Cboe rule) is
  13.51 on the free feed and 13.58 on Bloomberg for 23 Oct (0.5% apart), 12.22 and
  13.49 for 30 Oct (10.4%), both inside H5c's 25%. TSLA's is 0.00 on both feeds and
  both expiries: no zero bids, no inflation, as H5d predicts.
- **USO's parity forwards differ by 0.30-0.90% between the feeds** although the pulls
  were minutes apart. USO's markets are 11-17% of the mid wide, so a forward read off
  mids is noisy (Bloomberg's own two printed forwards, 148.18 and 149.21, differ by
  more than a week's carry). The price gate passes; nothing is re-scored.
- Scratch computation behind the pooled figures below: the same contract rule as
  `bloomberg_compare.wings()` (out of the money, an ask on both feeds, a missing bid
  read as zero), pooled over every matched wing day on disk.

*Bloomberg figures: Source: Bloomberg Finance L.P.*

## Prior art, read 23 September 2026 — H5e's estimator is NOT new

Andersen, Bondarenko & Gonzalez-Perez (2015), "Exploring Return Dynamics via
Corridor Implied Volatility", *Review of Financial Studies* 28(10), 2902-2945
(doi:10.1093/rfs/hhv033), read in full via Pepperdine's access. Two things in it
bear directly on H5, and both must be credited in anything written:

- **The critique of Cboe's cutoff is theirs.** Section 3.1.2 shows that the rule of
  discarding everything past two consecutive zero bids makes the effective strike
  range vary at random, which puts noise and artificial jumps into the
  high-frequency VIX and biases VIX^2 downward against the full model-free measure.
  H5's observation that the stop rule cut USO's band on 22 Sep is an instance of
  their mechanism, not a discovery.
- **H5e's estimator is their RX\*.** They compute the index from every
  out-of-the-money option with a positive bid, abandoning the two-zero-bid cutoff,
  and note that it bounds the official index from above. That is exactly
  `modelfree`'s `"skip"` mode. H5e stays registered as it stands - a prediction
  about free data on USO, not a claim of method - but the method is theirs and is
  cited as theirs.

**What remains this project's:** RX\* applied to a free, indicative, retail-grade
feed; at the daily frequency; on a sparse ETF strike ladder where the cutoff bites
on one-sided stub quotes at odd strikes 15-20% from the money (they study SPX, where
it bites far in the tails); and a same-contract cross-check against Bloomberg. Their
remedy for the underlying problem, a corridor whose barriers follow the options
themselves (their CX index), is the natural next step if H5e holds, and is not
adopted here.

**Still to read:** Jiang & Tian (2005), *RFS* 18, 1305-1342, which they cite as
finding no major VIX biases at the daily frequency - the frequency this project
works at - and the companion working paper named in their footnote 13, "A Corridor
Fix for High-Frequency VIX: Developing Coherent Implied Volatility Measures".

**Read 23 September 2026: Jiang & Tian (2007)**, "Extracting Model-Free Volatility
from Option Prices: An Examination of the VIX Index", *Journal of Derivatives* 14(3),
35-60, via Pepperdine interlibrary loan (a private-study copy, kept outside this
repository). What bears on H5:

- They decompose the error in Cboe's procedure into **truncation** (strikes beyond the
  listed range ignored: biases the estimate down), **discretization** (a coarse strike
  grid and Cboe's integration rule: biases it up), a negligible Taylor-expansion term,
  and maturity interpolation. H3 carries their truncation result; see H3's prior-art
  section of the same date.
- They name Cboe's zero-bid filter and two-consecutive-zero-bid cutoff as a reason the
  truncation interval moves from day to day - the mechanism ABG (2015) formalise and
  H5's 22 Sep stop-rule observation is an instance of. Credited to both.
- **What they do not study** is pricing a no-bid quote at half its ask, as the
  registered estimator does. That pushes the estimate UP by adding stub asks, the
  opposite sign to truncation, and on SPX's dense ladder it would barely register. H5c's
  inflation - its size on a sparse ETF ladder, reproduced on Bloomberg's and OPRA's
  prices - stays this project's measurement, not their result.

## Adjustment log

- **2026-09-23 — an ADDITION, not an adjustment.** H5e added after seeing 18-22 Sep,
  judged only from 23 Sep onward. H5a-H5d, their thresholds and their minimums are
  unchanged.
- **2026-09-23 — NO adjustment; an ambiguity found at the verdict, logged.** H5a's
  sentence says wing contracts are "quoted on both sides"; the frozen specification
  says "with a quote on both feeds". They score differently (0.40 against 0.67, see
  Result). H5a is scored on the specification, which is also how the registration's own
  18 Sep figures were computed (0.07 on 18 far puts, 13 of them without a bid). Both
  readings are printed beside the verdict. Nothing was changed.

## Result

**H5a and H5b reached their registered minimum on 23 Sep 2026:** three matched
Bloomberg wing days (18, 22 and 23 Sep), seven symbol-expiry blocks, 169 wing contracts.

- **H5b HOLDS.** Where the free feed shows no bid, Bloomberg shows none on **36 of 36**
  matched wing contracts (100%; bar 80%). One contract went the other way (a free-feed
  bid, none on Bloomberg, 18 Sep). OPRA agrees independently: 38 of 38 (H5f, descriptive).
- **H5a HOLDS as specified, and weakly.** Pooled over all 169 contracts the median
  free-feed mid sits **0.40** of Bloomberg's spread away (bar 0.5); by date 0.11, 0.71
  and 0.38; 54% of contracts inside half a spread. **But the pass rests on the 37
  contracts with no bid on at least one feed, whose mids agree almost by construction.**
  On the 132 contracts with a bid on both feeds the pooled median is **0.67**, over the
  bar. Most of that is TSLA, whose wing markets are a tick or two wide, so a one-cent
  difference is a whole spread (TSLA 0.33-1.00 by block; USO 0.01-0.66). Read plainly:
  the free feed's far wings carry the same empty bids as the consolidated market, and
  its two-sided wing quotes are within a tick or two, not within half a spread.
- **H5c, H5d:** descriptive until their 10 underlying-days support the date-clustered
  test the specification requires. **H5e:** counting from 23 Sep. **H5f:** 3 of 5 OPRA days.

*Bloomberg figures: Source: Bloomberg Finance L.P.*
