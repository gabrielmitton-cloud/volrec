# The index-timing measurement: how much of H5e's and H7's gaps is the index moving after the snapshot (descriptive)

**Registered:** 2026-11-06 (Fri), before either verdict is recorded and before any value of the index files is
opened; the commit that adds this file is the proof. Approved by Gabriel in chat the same day, choosing to
register that day rather than on Sat 7 Nov: the reader was finished that day, so PROTOCOL step 2's wait of a
calendar day was not kept (logged under "Instrument readiness" and in the adjustment log).
**Status:** registered - DESCRIPTIVE: no test, no bar, no verdict. Read once, 13 Nov 2026 (see Result).
**Independently timestamped:** OSF registration https://osf.io/4mcgf (submitted 6 Nov 2026, 21:06 UTC; secondary-data
template; discloses what was seen first and the wait not kept).
**Sample:** B (own panel): the H5e- and H7-counted days that the sealed index files cover (21 Oct - 11 Nov 2026).

Written 6 Nov 2026 by Vega from the plan of 4 Nov (`docs/drafts/2026-11-04-index-timing-plan.md`, committed
before any value of the index data was opened). The definitions and computations are the plan's, unchanged;
this text adds the three sections PROTOCOL.md requires, the conventions the reader already implements, and the
corrections listed in the adjustment log. Nothing here changes a registered bar, window, estimator, verdict or
file. Its results are reported beside the registered numbers, never in place of them.

## Why this measurement exists

H5e compares USO's estimate, built from quotes taken at about 14:30 New York, with OVX's daily close. H7
compares Cboe's own method, run on the same quotes, with the OVX and GVZ closes. Both gaps mix the estimate's
own error with the index moving between the snapshot and the close, and nothing so far has separated the two.
The size of that move is known only indirectly (see "Prior looks"). This measurement separates them, on the
days the data covers, and serves the paper's question by saying how much of each registered gap is timing.

## The question, stated before the data is opened

No prediction is made. On every covered counted day, for each registered reading:
1. **H5e (USO vs OVX):** the registered skip-only estimate, and the registered estimate beside it.
2. **H7 (USO vs OVX, GLD vs GVZ):** the OPRA replica and the free-feed replica.

how large, and in which direction, are the estimate's gap to the index at the same minute and the index's move
from that minute to the close; and do the two offset each other?

## Specification - frozen here

**The split, an exact identity:** `E - C = (E - I(T)) + (I(T) - C)`: the registered gap equals the
*contemporaneous residual* (the estimate minus the index at the same minute) plus the index's move after the
snapshot. The residual is not "method" alone: it holds the estimator's method, quote quality, quote-to-minute
alignment and reconstruction differences together. The identity has no order of steps, but it does not assign
causes to absolute errors: a residual of +1 and a move of -1.5 give a registered gap of -0.5, smaller than
either part.

- **E**, the registered estimate, rebuilt by the registered code: H5e's two estimates by `modelfree` on
  `modelfree.h5e_report`'s counted days (USO, 23 Sep - 11 Nov, after-close days dropped, an OVX close and both
  estimates present); H7's two replicas by `tools/h7_reader.py`'s own functions on its counted days (9 Oct -
  11 Nov, both readings and the index close finite).
- **Snapshot minute T:** `opra_reference.snapshot_minute` of the rows that estimate used: the median quote time
  (the upper median for an even count), floored to the minute. The comparison is aligned to this designated
  minute, not to each quote's instant; each day's spread of quote times around T is reported beside it.
- **I(T):** Databento stamps a one-second bar with the inclusive start of its second and prints a bar only for
  a second with a published value. I(T) is the close of the last bar whose second has ended by T
  (`ts_event + 1 s <= T`), from T's New York trading day, at or after 09:31 New York, and at most 60 s old
  **measured from the bar's stamp** (`T - ts_event <= 60 s`). A day failing any of these, or whose last
  eligible close is not a finite number, is listed as not measured, with the reason; it is never filled, and
  no earlier bar stands in.
- **C:** Cboe's published close as the registered readings read it (`analyze.fetch_market_vol`: the CLOSE
  column of Cboe's `OVX_History.csv` / `GVZ_History.csv`; that function falls back to FRED's copy only if Cboe
  refuses the file, and says so in its output).
- **Sensitivity**, labelled as able to use a value printed after T: the close of the bar nearest T within 15 s
  either side, a tie going to the earlier bar. It is reported on **its own days, with its own count**: a day
  can be measured by one rule and not the other.
- **Consistency check:** a day whose last one-second value is more than 0.05 from C, in either direction, is
  flagged and listed, never dropped. Whether DBIX's last print (16:02 on 3 Nov) is Cboe's official close is
  settled from the two sources' documentation before any disagreement is read as a data error.
- **Computed, per reading and index, on identical days:** the signed means of `E - C`, `E - I(T)` and
  `I(T) - C` (they add up exactly; the residue is printed); the mean absolute value of each, separately; the
  correlation between the residual and the move; each part's persistence (T, rho, n_eff); the sensitivity's
  signed means with its count; each day's quote-time spread around T (median, earliest, latest, in seconds)
  and the median of the daily medians; the flagged days. Aggregates only: dates and counts are printed, never
  an index value.
- **Persistence conventions:** rho is the lag-1 autocorrelation (lag-1 autocovariance over variance) over the
  measured days in date order - a day not measured is skipped, not filled, so "lag 1" is the previous measured
  day; `n_eff = T(1 - rho)/(1 + rho)`, a negative rho counted as 0, floored at 1 (`tools/h8_quotes.py`);
  fewer than three days gives n/a.
- **Days:** only days the index files cover are measured. Every other counted day is listed as before the
  data begins, after it ends, or a day without a file.
- **The data:** Databento Core Indices (`DBIX.CORE`), one-second bars, **OVX and GVZ only**; every other
  index's row is skipped before any of its fields is converted, and any use of them is agreed and written
  down before their values are read. Covered now: 21 Oct - 3 Nov 2026 (10 trading days), sealed in private
  commit `0098e82`. 4 - 11 Nov (6 trading days) is bought after 11 Nov and its files' sha256 are added to the
  same seal before any of them is read.
- **What runs, in order, and refuses rather than guesses:** nothing opens until H5e's FINAL reading and H7's
  reading are both recorded in their hypothesis files; every file's sha256 must match the seal, every day file
  the seal lists must be on disk and no unlisted day file may be; the readings are rebuilt at the frozen
  risk-free rate (3.910%) or not at all; `modelfree.py --wide --through 2026-11-11` must exit cleanly and give
  the same H5e days and gaps; the rebuilt skip-only gaps must equal the recorded FINAL reading's gap by day
  (same days, two decimals); and H7's days must be its recorded reading's (H7's expected trading days less the
  days the record names as missing or not counted), with the same counts and the same four means (H7a, H7b,
  H7c, three decimals), so an OPRA folder that is missing or not the private one cannot silently drop H7's
  days. A value that is not a finite number is a disagreement, never a pass. H7's record holds aggregates
  only, so its agreement is on days and those means, not day by day. A date accepted as a gap (a day one
  panel lost, `panel_health.ACCEPTED_GAPS`) is checked by those counts and means, not by its date: H7 can
  still count it, and the writer's own coverage check skips it. Every reading gets its lines in the report,
  even one with no counted day.
- **The reader and the command:** `tools/index_timing.py` as in the commit that adds this file (it last changed
  in the commit before), sha256 `e65b52704d0b4a28be455a1dc4657ad5309133005526a194bf0dfc27bf4afb46`, run as
  `VOLREC_DATABENTO_DIR=~/Documents/volrec-licensed/opra python tools/index_timing.py` (the index folder
  defaults to `~/Documents/volrec-licensed/dbix`). Any later change to it is logged below with its date.

*Data provided by Databento. Index closes: Cboe Global Markets. Aggregates only.*

## Instrument readiness

- **Known-answer tests** (`tools/test_index_timing.py`, 98 cases, all synthetic): the plan's own example of the
  split (+1 and -1.5 give -0.5) and 200 random triples adding up within 1e-12; I(T) at each edge (the bar
  stamped T - 1 s is used, the bar stamped T never; 60 s old used, 61 s not; the previous day, before 09:31,
  either side of the 2 Nov clock change, a non-finite last close); the sensitivity's 15 s and its tie; the
  close check at 0.05 and 0.06; the seal (a changed, unlisted, lost or extra file is refused); the record
  checks against hand-worked numbers (a day missing with every mean unchanged, a day swapped for another at the
  same count and means, a mean 0.003 off, a close revised since the verdict, a value that is not a finite
  number, a later note below the verdict, an accepted-gap day counted by both sides (it must pass) or by one
  (it must not), and a difference inside the printed decimals that must pass).
- **Real-format fixtures:** the index files copy DBIX's recorded layout (Databento CSV, pretty timestamps and
  prices, symbols mapped, rtype 32 for one-second bars; structure read 4 Nov 2026, never a value), with the
  header typed from Databento's documented field order rather than from the reader; a missing value is
  Databento's: no bar for a second without a published value. The records copy the writer's own wording,
  rendered by `tools/record_verdict.py`'s `block_h5e` and `block_h7`, and `modelfree`'s printed H5e table.
- **Every path has run once:** the whole report end to end on synthetic files (measured, not covered, not
  measured, flagged); the gate on the writer's own markers. On 6 Nov the real readings were rebuilt from the
  public panels and the private OPRA folder, without opening the sealed folder, and agreed with `modelfree`
  and with blocks the writer rendered from its readers' output that day (H5e 31 counted days; H7 19 a fund,
  its days, counts and four means, over 9 Oct - 5 Nov because H7's verdict was not yet written). With the OPRA
  folder left at its default, the reader refused, listing the days.
- **Finished:** Fri 6 Nov 2026 (last change 19:01 UTC), when the record checks were added after the first
  cold re-read found that H7's days could drop silently. **Not kept: the wait of a calendar day.** Registered
  the same day at Gabriel's choice; that day's changes were re-read line by line before registering, the same
  day, so not cold. The re-read of 6 Nov that found the defect was cold (the reader had last changed on 5 Nov).
- **Auditor:** 28 mutants break the reader's safeguards one at a time (`timing-*` in `tools/audit.py`): reads
  ahead, stale index, seal unchecked, opens before the verdicts, either verdict, lost file, reference exit,
  both rate checks, FRED key kept, default widened, non-finite index; empty agreement three ways (modelfree,
  the FINAL record, H7's record); the FINAL record unchecked, its gap unchecked, a non-finite gap passing it or
  modelfree's check, the FIRST verdict read instead of the FINAL; H7's record unchecked, its days, count or
  means unchecked, a non-finite mean, a later note read as the verdict's, an accepted-gap day refused; and a
  reading dropped from the report. The audit of the reader's commit (the one before this file's) read 217 of 217
  (6 Nov 2026, 19:08-19:32 UTC).

## Noise floor

There is no bar, so there is no multiple of a floor. What limits how small a part can be read:
- **The index at T:** on 3 Nov, OVX and GVZ printed every 15 s from 09:31 to 16:02 New York (structure only),
  so I(T) is normally under 15 s old; the 60 s rule is an outer limit, and the sensitivity (nearest print
  within 15 s either side) shows how much the rule itself moves the parts.
- **The estimate at T:** on H5e's first 10 days, the OPRA replica of Cboe's method sat a mean absolute 0.29
  points from OVX's close (median 0.23) and 0.10 from GVZ's (HANDOFF, 9 Oct). That figure contains the move
  from snapshot to close, so it bounds this measurement's residual floor from above. Between the two feeds
  on the same contracts, H7's in-sample step was +0.02 (mean absolute 0.04) for USO and -0.01 (0.02) for GLD.
- **The close:** Cboe prints C to two decimals (0.005 either way).
*Data provided by Databento. Index closes: Cboe Global Markets. Aggregates only.*

## Smallest detectable effect

No test, so no effect is claimed detectable; this is for scale (PROTOCOL step 4's planning guide). On the
registered gaps `E - C` alone (public estimates against Cboe's closes; no index value at T), counted days from
21 Oct to 4-5 Nov (T = 11-12), computed 6 Nov 2026:
| reading | T | sd of E - C | rho | n_eff | 2.8 sd / sqrt(n_eff) |
|---|---|---|---|---|---|
| H5e skip-only, USO vs OVX | 12 | 1.08 | +0.23 | 7.5 | 1.11 |
| H5e registered, USO vs OVX | 12 | 0.94 | -0.12 | 12.0 | 0.76 |
| H7 OPRA replica, USO vs OVX | 11 | 0.96 | +0.01 | 10.9 | 0.82 |
| H7 free-feed replica, USO vs OVX | 11 | 0.96 | -0.07 | 11.0 | 0.81 |
| H7 OPRA replica, GLD vs GVZ | 11 | 0.25 | +0.05 | 10.0 | 0.22 |
| H7 free-feed replica, GLD vs GVZ | 11 | 0.25 | +0.00 | 10.9 | 0.21 |

So with about 16 covered days, a mean part smaller than roughly 0.8-1.1 points (USO against OVX) or 0.2 points
(GLD against GVZ) would not stand out from day-to-day scatter; the parts' own spread is not known until the
data is read. These are normal approximations at a few effective observations, never a verdict's arithmetic.
*Data provided by Databento. Index closes: Cboe Global Markets. Aggregates only.*

## Stated in advance, so the reading cannot be bent

- **No test, no bar, no verdict.** This measures; it cannot confirm anything.
- **The covered days are not a random sample.** They are the windows' last stretch, when OVX rose and H5e's
  gaps were at their widest. Results describe those days only.
- **What it can say:** how far, and in which direction, OVX and GVZ moved after the snapshot on these days, and
  the size of the estimates' gap to the index at the same minute beside their registered gap.
  **What it cannot say:** what caused H7's in-sample +0.45 (14 Sep - 7 Oct, not covered), or how absolute error
  divides between causes.
- The output goes to HANDOFF and, if Gabriel agrees, to the write-up's limitations section, credited "Data
  provided by Databento".

## Prior looks (every series and date range already seen)

- **The index files:** structure only, 4 Nov 2026 (rows and symbols per file, columns, timestamps). No value.
- **The registered gaps E - C:** H5e's table in `tools/daily.py` through 2 Nov (public), and the recorded panels
  through 5 Nov; H7's in-sample figures (14 Sep - 7 Oct); and the planning numbers above, computed 6 Nov over
  21 Oct - 5 Nov. They set the scale in "Smallest detectable effect" and nothing else.
- **The size of moves after the snapshot, indirectly:** the lab's 25 stress-month days per fund (OPRA,
  2016-2026; `lab/REGISTRATION.md`) found the registered *estimator* moving a median 0.53 points between 14:30
  and 15:55 (GLD 0.14, USO 0.74) - the estimate measured twice, never the index, and in stress months, so an
  upper range. The replica residual's 0.29 above contains the move too. **Both are proxies for `I(T) - C`'s
  size, named here as such.**
- **LSEG:** VIX one-minute bars from 1 Sep 2026 were saved on 14 Oct; VIX is outside this measurement. OVX and
  GVZ intraday were refused (an entitlement gap), so none was seen.
- **How the looks shaped the specification:** none chose a window, source, exclusion or estimator. The days
  are set by Databento's usage-based start (21 Oct) and the verdict windows' end (11 Nov); the readings are the
  registered ones; the 15 s and 60 s rules come from the structural read and Databento's documentation.
*Data provided by Databento. Aggregates only.*

## What would make the reading unusable

Nothing can falsify a description. The reading is not taken at all if any refusal above fires: a seal
mismatch, a lost or extra file, a rate other than the frozen one, or rebuilt readings that differ from
`modelfree` or from the recorded verdicts. Days flagged by the consistency check are kept and listed.

## Explicitly NOT in this registration

Causes of absolute error; H7's in-sample +0.45 (its days predate the data); intraday paths after T; any index
but OVX and GVZ; any change to H5e's or H7's verdicts, bars or windows; H7's companion reading; the 1-minute
bars from the 23-25 Nov Bloomberg session, which need their own short registration.

## Adjustment log

- **4 Nov 2026 - the plan** (`docs/drafts/2026-11-04-index-timing-plan.md`), before any value was opened.
- **6 Nov 2026, before any value was opened - the reader's record checks.** The first cold re-read found that
  H7's days vanished without a word when `VOLREC_DATABENTO_DIR` was not the private OPRA folder, and that a
  close revised since the verdict would pass. The reader now refuses unless its H5e and H7 days give the
  recorded verdicts' own days and numbers. Astra's review that day added three more: H7's days are compared
  date by date (a swapped day had passed at the same count and means), a value that is not a finite number is
  a disagreement (it had passed every comparison, the older modelfree check included), and a reading with no
  counted day keeps its lines in the report. Its follow-up found one more, a refusal that would have been
  false: H7 can count a date accepted as a gap, which the reconstructed day list leaves out, so such a date
  is now checked by the counts and means only. Code and tests only; no definition changed.
- **6 Nov 2026, before any value was opened - wording.** The plan expected "about 16 days, strongly
  persistent, an n_eff of a few"; the registered gaps on the covered days so far are barely persistent
  (rho -0.12 to +0.23, n_eff 7.5-12 at T = 11-12), so that sentence is replaced by the measured numbers. Also
  written out: the sensitivity's own day set, the age rule measured from the bar's stamp, C's FRED fallback,
  the persistence conventions, the run command, the record checks, and the top-up's seal.
- **6 Nov 2026 - registered the day the reader was finished, a deviation from PROTOCOL step 2.** The step asks
  for at least one calendar day between finishing an instrument and registering on it, then a cold re-read.
  The reader last changed at 19:01 UTC; Vega proposed Sat 7 Nov, and Gabriel chose 6 Nov. Before registering,
  that day's diff was re-read line by line (no defect found) and the auditor read 217 of 217 on the
  reader's commit. No definition, rule or check changed.
*Data provided by Databento. Index closes: Cboe Global Markets. Aggregates only.*

## Result

Filled in after the run, which waits for both verdicts.

**Read once, 13 November 2026, 16:34 UTC** - by Vega, with the registered command (`VOLREC_DATABENTO_DIR=~/Documents/volrec-licensed/opra python tools/index_timing.py`, the framework Python), on the reader whose sha256 is the registered `e65b5270...` (checked before the run), after H5e's FINAL reading (12 Nov) and H7's reading (13 Nov) were both recorded (Gabriel's go-ahead, 12 Nov: read once H7 is recorded). Exit 0: every refusal passed (the seal and its files, the frozen rate, `modelfree`, the recorded days and means). Its output, whole:

```
Index timing - EXPLORATORY, descriptive; no test, no verdict. DBIX days: 2026-10-21 to 2026-11-11 (16 files).

== H5e registered, against OVX: 16 of 16 covered days measured; 19 counted days before the data begins (2026-09-23 to 2026-10-20)
   signed means, points: E - C -2.896 = (E - I(T)) -2.810 + (I(T) - C) -0.087   [adds up to 0.0e+00]
   mean absolute: |E - C| 2.896, |E - I(T)| 2.810, |I(T) - C| 0.634; corr(E - I(T), I(T) - C) -0.057
   persistence (days, rho, n_eff): E - C 16, +0.017, 15.5; E - I(T) 16, +0.389, 7.0; I(T) - C 16, -0.092, 16.0
   sensitivity, the bar nearest T within 15 s (may use a value printed after T), 16 days: E - I -2.821, I - C -0.076
   quote times around T, seconds: each day's median (earliest to latest); the median of the daily medians +30
      2026-10-21 +27 (-774 to +32); 2026-10-22 +30 (-463 to +37); 2026-10-23 +23 (-16 to +31); 2026-10-26 +29 (-366 to +40)
      2026-10-27 +33 (-165 to +35); 2026-10-28 +31 (-595 to +35); 2026-10-29 +28 (-222 to +30); 2026-10-30 +30 (-82 to +32)
      2026-11-02 +32 (+7 to +33); 2026-11-03 +40 (+8 to +45); 2026-11-04 +32 (+20 to +34); 2026-11-05 +48 (+26 to +52)
      2026-11-06 +33 (-33 to +36); 2026-11-09 +23 (-6 to +92); 2026-11-10 +27 (-106 to +34); 2026-11-11 +25 (-117 to +32)
== H5e skip-only, against OVX: 16 of 16 covered days measured; 19 counted days before the data begins (2026-09-23 to 2026-10-20)
   signed means, points: E - C -1.203 = (E - I(T)) -1.116 + (I(T) - C) -0.087   [adds up to 0.0e+00]
   mean absolute: |E - C| 1.203, |E - I(T)| 1.117, |I(T) - C| 0.634; corr(E - I(T), I(T) - C) -0.181
   persistence (days, rho, n_eff): E - C 16, +0.332, 8.0; E - I(T) 16, +0.625, 3.7; I(T) - C 16, -0.092, 16.0
   sensitivity, the bar nearest T within 15 s (may use a value printed after T), 16 days: E - I -1.127, I - C -0.076
   quote times around T, seconds: each day's median (earliest to latest); the median of the daily medians +30
      2026-10-21 +27 (-774 to +58); 2026-10-22 +30 (-463 to +66); 2026-10-23 +24 (-16 to +63); 2026-10-26 +29 (-366 to +68)
      2026-10-27 +33 (-165 to +63); 2026-10-28 +31 (-595 to +63); 2026-10-29 +28 (-9815 to +56); 2026-10-30 +30 (-16416 to +56)
      2026-11-02 +32 (-2386 to +63); 2026-11-03 +40 (-14185 to +71); 2026-11-04 +32 (+20 to +65); 2026-11-05 +48 (+26 to +84)
      2026-11-06 +36 (-33 to +71); 2026-11-09 +23 (-6 to +103); 2026-11-10 +26 (-113 to +62); 2026-11-11 +25 (-117 to +62)
== H7 OPRA replica, against GVZ: 16 of 16 covered days measured; 8 counted days before the data begins (2026-10-09 to 2026-10-20)
   signed means, points: E - C +0.040 = (E - I(T)) +0.002 + (I(T) - C) +0.038   [adds up to 0.0e+00]
   mean absolute: |E - C| 0.198, |E - I(T)| 0.010, |I(T) - C| 0.207; corr(E - I(T), I(T) - C) -0.675
   persistence (days, rho, n_eff): E - C 16, -0.105, 16.0; E - I(T) 16, -0.256, 16.0; I(T) - C 16, -0.130, 16.0
   sensitivity, the bar nearest T within 15 s (may use a value printed after T), 16 days: E - I -0.002, I - C +0.043
   quote times around T, seconds: each day's median (earliest to latest); the median of the daily medians +11
      2026-10-21 +1 (-688 to +8); 2026-10-22 +13 (-814 to +16); 2026-10-23 +9 (-74 to +13); 2026-10-26 +12 (-3229 to +17)
      2026-10-27 +8 (-904 to +13); 2026-10-28 +11 (-7 to +13); 2026-10-29 +59 (-154 to +66); 2026-10-30 +6 (-9081 to +11)
      2026-11-02 +9 (-229 to +12); 2026-11-03 +19 (-31 to +26); 2026-11-04 +10 (-496 to +16); 2026-11-05 +30 (-49 to +35)
      2026-11-06 +15 (-55 to +20); 2026-11-09 +42 (-22 to +123); 2026-11-10 +12 (-2597 to +16); 2026-11-11 +8 (-932 to +11)
== H7 OPRA replica, against OVX: 16 of 16 covered days measured; 8 counted days before the data begins (2026-10-09 to 2026-10-20)
   signed means, points: E - C -0.083 = (E - I(T)) -0.017 + (I(T) - C) -0.066   [adds up to 0.0e+00]
   mean absolute: |E - C| 0.639, |E - I(T)| 0.021, |I(T) - C| 0.630; corr(E - I(T), I(T) - C) -0.060
   persistence (days, rho, n_eff): E - C 16, -0.031, 16.0; E - I(T) 16, -0.182, 16.0; I(T) - C 16, -0.064, 16.0
   sensitivity, the bar nearest T within 15 s (may use a value printed after T), 16 days: E - I -0.016, I - C -0.067
   quote times around T, seconds: each day's median (earliest to latest); the median of the daily medians +14
      2026-10-21 +59 (-234 to +63); 2026-10-22 +51 (-463 to +70); 2026-10-23 +3 (-35 to +8); 2026-10-26 +10 (-426 to +13)
      2026-10-27 +3 (-225 to +9); 2026-10-28 +4 (-655 to +8); 2026-10-29 +50 (-261 to +61); 2026-10-30 +0 (-179 to +6)
      2026-11-02 +4 (-561 to +7); 2026-11-03 +18 (-57 to +21); 2026-11-04 +4 (-48 to +11); 2026-11-05 +27 (-7 to +30)
      2026-11-06 +10 (-16860 to +15); 2026-11-09 +43 (-12889 to +49); 2026-11-10 +51 (-11332 to +71); 2026-11-11 +52 (-2720 to +66)
== H7 free-feed replica, against GVZ: 16 of 16 covered days measured; 8 counted days before the data begins (2026-10-09 to 2026-10-20)
   signed means, points: E - C +0.039 = (E - I(T)) +0.001 + (I(T) - C) +0.038   [adds up to 0.0e+00]
   mean absolute: |E - C| 0.192, |E - I(T)| 0.037, |I(T) - C| 0.207; corr(E - I(T), I(T) - C) -0.483
   persistence (days, rho, n_eff): E - C 16, -0.124, 16.0; E - I(T) 16, +0.131, 12.3; I(T) - C 16, -0.130, 16.0
   sensitivity, the bar nearest T within 15 s (may use a value printed after T), 16 days: E - I -0.004, I - C +0.043
   quote times around T, seconds: each day's median (earliest to latest); the median of the daily medians +11
      2026-10-21 +1 (-688 to +8); 2026-10-22 +13 (-814 to +16); 2026-10-23 +9 (-74 to +13); 2026-10-26 +12 (-3229 to +17)
      2026-10-27 +8 (-904 to +13); 2026-10-28 +11 (-7 to +13); 2026-10-29 +59 (-154 to +66); 2026-10-30 +6 (-9081 to +11)
      2026-11-02 +9 (-229 to +12); 2026-11-03 +19 (-31 to +26); 2026-11-04 +10 (-496 to +16); 2026-11-05 +30 (-49 to +35)
      2026-11-06 +15 (-55 to +20); 2026-11-09 +42 (-22 to +123); 2026-11-10 +12 (-2597 to +16); 2026-11-11 +8 (-932 to +11)
== H7 free-feed replica, against OVX: 16 of 16 covered days measured; 8 counted days before the data begins (2026-10-09 to 2026-10-20)
   signed means, points: E - C -0.435 = (E - I(T)) -0.369 + (I(T) - C) -0.066   [adds up to 0.0e+00]
   mean absolute: |E - C| 0.699, |E - I(T)| 0.369, |I(T) - C| 0.630; corr(E - I(T), I(T) - C) -0.264
   persistence (days, rho, n_eff): E - C 16, -0.094, 16.0; E - I(T) 16, +0.532, 4.9; I(T) - C 16, -0.064, 16.0
   sensitivity, the bar nearest T within 15 s (may use a value printed after T), 16 days: E - I -0.368, I - C -0.067
   quote times around T, seconds: each day's median (earliest to latest); the median of the daily medians +14
      2026-10-21 +59 (-234 to +63); 2026-10-22 +51 (-463 to +70); 2026-10-23 +3 (-35 to +8); 2026-10-26 +10 (-426 to +13)
      2026-10-27 +3 (-225 to +9); 2026-10-28 +4 (-655 to +8); 2026-10-29 +50 (-261 to +61); 2026-10-30 +0 (-179 to +6)
      2026-11-02 +4 (-561 to +7); 2026-11-03 +18 (-57 to +21); 2026-11-04 +4 (-48 to +11); 2026-11-05 +27 (-7 to +30)
      2026-11-06 +10 (-16860 to +15); 2026-11-09 +43 (-12889 to +49); 2026-11-10 +51 (-11332 to +71); 2026-11-11 +52 (-2720 to +66)
close check (|last DBIX value - Cboe close| > 0.05, kept): no day flagged
Data provided by Databento. Index closes: Cboe Global Markets. Aggregates only.
```

In plain words (descriptive; it changes no verdict, and it does not divide absolute error between causes):
- **At the snapshot minute, Cboe's method on OPRA's quotes sits on the index.** The OPRA replica was a mean absolute 0.021 points from OVX and 0.010 from GVZ at the same minute, over the 16 covered days. At the close its gap is larger (0.639 and 0.198), and the index's own move after the snapshot is about as large (0.630 and 0.207 in size); the index at the snapshot minus its close averaged near zero (-0.066 and +0.038).
- **The free feed's replica is close on GLD and off on USO at the same minute:** 0.037 points from GVZ, 0.369 from OVX (signed -0.369, persistent: rho +0.53, n_eff 4.9).
- **H5e's two estimates are off at the same minute, not only at the close:** the skip-only estimate a mean absolute 1.117 points from OVX at the snapshot minute (signed -1.116), the registered estimate 2.810; OVX's move after the snapshot was 0.634 in size, and OVX at the snapshot minus its close averaged -0.087, the same days for both.
- The 15-second sensitivity moves no signed mean by more than 0.011 points; no day's last index value is more than 0.05 from Cboe's close (no day flagged).
- These are the windows' last 16 days, when OVX rose (see "Stated in advance"); they describe those days only.

*Data provided by Databento. Index closes: Cboe Global Markets. Aggregates only.*
