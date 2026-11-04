# The index-timing measurement - analysis plan, written BEFORE the data is opened

**Status: EXPLORATORY plan, not registered.** Written 4 Nov 2026 by Vega, at Gabriel's go-ahead. It enters
this repository in the same commit as HANDOFF's 4 Nov DBIX entry, before any value in the data below is
opened, and that commit's hash is written beside the seal in the private `dbix/README.md`, so each record can
be checked against the other. Nothing here changes a registered bar, window, estimator, verdict or file.
Revised the same day after Astra's review and its one follow-up (wording of the split, timestamp and
freshness rules, the close check, the route below).

**Route (SCIENTIST.md: an analysis runs only once it is registered).** H7's registration does not cover
this: it lists intraday index values among what it leaves out. So this file is the draft of a descriptive
registration, written before any value is read (the structural reads are listed under "The data"). It runs
only after H5e FINAL and H7 are recorded (12-19 Nov), and only once Gabriel has approved it at the
post-verdict discussion and it is committed to `hypotheses/` as a descriptive registration (no bar, no
verdict), or under a dated exception he writes down. Its results are reported beside the registered
numbers, never in place of them.

## The question
H5e compares USO's estimate, built from quotes taken at about 14:30 New York, with OVX's daily close.
H7 compares Cboe's own method, run on the same quotes, with the OVX and GVZ closes. Both gaps mix the
estimate's own error with the index moving between the snapshot and the close, and nothing so far has
separated the two. The size of the move is known only indirectly: on 25 stress-month days per fund (lab/
OPRA, 2016-2026; PAPER-OUTLINE limitations, lab/REGISTRATION.md) the registered *estimator* moved a
median 0.53 points between 14:30 and 15:55 (GLD 0.14, USO 0.74; stress months, so read as an upper range,
lab/main_links.py) - the estimate measured twice, never the index. H7 names timing as the lead suspect for USO's in-sample +0.45 (a signed mean, 14 Sep - 7 Oct).
**Those days are not covered below, so this plan cannot decompose that +0.45**; it measures the same
quantities on the days it does cover.

## The data (sealed)
Databento Core Indices (`DBIX.CORE`), one-second bars, bought 4 Nov 2026 and kept in the private
repository (`volrec-licensed/dbix/`). **Seal:** the private repository's commit `0098e82` holds every
file's sha256. The hashes show the files are unchanged since; that no value has been read rests on this
record - the only reads were structural (rows and symbols per file, columns, timestamps).
Covered: **21 Oct - 3 Nov 2026** (10 trading days); 4-11 Nov to be added after 11 Nov (the 12 Nov
reminder). Pay-per-use access started at 21 Oct, so earlier days of either window cannot be measured
(a subscription would be needed). On 3 Nov, OVX and GVZ printed every 15 s from 09:31 to 16:02 New York.
**This analysis reads OVX and GVZ only.** The other fifteen indices in the same files (VIX, VXN, RVX,
VXD, VXAPL and ten more) stay outside it; any use of them is agreed and written down before their values
are read. *Data provided by Databento. Aggregates only.*
Already public before this plan: daily.py's H5e table through 2 Nov, and H7's in-sample figures.

## Definitions, fixed now
- **Snapshot minute `T`:** `opra_reference.snapshot_minute` of the rows the registered reading used: the
  median quote time (the upper median for an even count), floored to the minute. The OPRA reference was
  matched to this minute contract by contract, within up to 120 s (`ovx_replicate.chain_at`), and the
  recorder's own quote times spread around it. **The comparison is aligned to the designated minute, not
  to each quote's instant**; each day's spread of quote times around `T` is reported beside it.
- **Index at the snapshot `I(T)`:** Databento stamps a one-second bar with the *start* of its second
  (inclusive), and prints a bar only for a second with a published value (its OHLCV documentation, read
  4 Nov 2026). So `I(T)` is the close of the
  last bar whose second has ended by `T`: `ts_event + 1 s <= T`. It must be from the same trading day,
  at or after 09:31 New York, and at most 60 s old; otherwise the day is listed as not measured, never
  filled. **Sensitivity**, labelled as able to use a value printed after `T`: the bar nearest `T`
  within 15 s either side.
- **Close `C`:** Cboe's published daily close as the registered readings use it, unchanged: the CLOSE
  column of Cboe's `OVX_History.csv` / `GVZ_History.csv` (FRED's copy if Cboe refuses the file).
- **Consistency check:** `|last DBIX value of the day - C| > 0.05` flags the day, in either direction;
  flagged days are kept and listed, never dropped. DBIX's last print came at 16:02 on 3 Nov; whether it
  is Cboe's official close is settled from the two sources' documentation before any disagreement is
  read as a data error.
- **Split, an exact identity:** `E - C = (E - I(T)) + (I(T) - C)`: the registered gap equals the
  *contemporaneous residual* (the estimate minus the index at the same minute) plus the index's move
  after the snapshot. The residual is not "method" alone: it holds the estimator's method, quote quality,
  quote-to-minute alignment and reconstruction differences together. The identity has no step order, but
  it does not assign causes to absolute errors: a residual of +1 and a move of -1.5 give a registered gap
  of -0.5, smaller than either part.

## What is computed (aggregates only, on identical days)
1. **H5e (USO vs OVX).** On every H5e-counted day the data covers, for the registered skip-only estimate
   (and the registered estimate beside it): the signed means of `E - C`, `E - I(T)` and `I(T) - C`, which
   add up exactly; separately, the mean absolute value of each; and the correlation between the residual
   and the move (whether they offset).
2. **H7 (USO vs OVX, GLD vs GVZ).** On every H7-counted day the data covers, the same for the OPRA replica
   and for the free-feed replica.
3. **Context, descriptive only:** the quote-time spread around `T`; and how persistent the daily values
   are (T, rho, n_eff = T(1 - rho)/(1 + rho), PROTOCOL step 4).

## Stated in advance, so the reading cannot be bent
- **No test, no bar, no verdict.** About 16 days, strongly persistent, gives an n_eff of a few. This
  measures; it cannot confirm anything.
- **The covered days are not a random sample.** They are the window's last stretch, when OVX rose (to
  62.69 on 2 Nov in daily.py's table) and H5e's gaps were at their widest (wide-skip -4.23 on 28 Oct).
  Results describe those days only.
- **What it can say:** how far, and in which direction, OVX and GVZ moved after the snapshot on these
  days, and the size of the estimates' gap to the index at the same minute beside their registered gap.
  **What it cannot say:** what caused H7's in-sample +0.45 (not covered), or how absolute error divides
  between causes.

## Afterwards
The script that computes this is written after the verdicts, checks each file's sha256 against the
private README before reading it, and prints aggregates only. Its output goes to HANDOFF and, if Gabriel
agrees, to the write-up's limitations section, credited "Data provided by Databento".
