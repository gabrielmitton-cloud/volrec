# H7 — The free feed, run through Cboe's own rules, reproduces Cboe's ETF volatility indices

**Registered:** 2026-10-08, before the first monthly-leg row exists (it lands Fri 9 Oct); the
commit date is proof. Approved by Gabriel 8 Oct.
**Status:** registered
**Independently timestamped:** OSF registration https://osf.io/z5gfu (H5e and H7, submitted 10 Oct 2026; secondary-data template; discloses what was seen first).
**Sample:** B (own panel), from 9 Oct 2026

## Why this hypothesis exists

H5e asked whether skipping zero bids brings the free feed's USO estimate to OVX, and FAILED
(0.90 against 0.5, 2 of 10; recorded 8 Oct). The 8 Oct methods audit then showed WHY the
comparison was hard: this project's estimator uses weekly expiries, a +/-30% band and whole-day
time, while Cboe uses third-Friday monthlies, the full chain and minutes (HANDOFF 18, fix 1).
H7 asks the cleaner question H5e could not: **with Cboe's own legs, strikes and rules, is the
free feed good enough to reproduce the index?** The monthly legs needed are recorded from
9 Oct (`data/surface_monthly.csv`, Gabriel 7 Oct).

## What is ALREADY known - stated so the bars below are not chosen to fit it

From the 8 Oct replication on OPRA (consolidated NBBO), 14 Sep - 7 Oct, in-sample:
- On the same contracts inside the +/-30% band, free-feed mids equal OPRA's (mean abs 0.04
  points USO, 0.02 GLD). Untested in the wings Cboe's walk reaches, where H5 found the free
  feed's far quotes stale and one-sided (23 Sep).
- Cboe's rules on OPRA land a median 0.07 (mean 0.15) from GVZ's close; on USO, +0.45 above
  OVX on average, unexplained (timing is the lead suspect; LSEG intraday would test it).

*Data provided by Databento (OPRA consolidated NBBO). Aggregates only.*

## The hypothesis, stated before any monthly-leg reading

**H7a (data).** For USO and GLD, the free-feed Cboe replica and the OPRA Cboe replica at the
same minute differ by a mean absolute 0.25 points or less. Uncertain because the wings are new.
**H7b (GVZ).** The free-feed Cboe replica for GLD lies within a mean absolute 0.30 points of
GVZ's close (twice the OPRA replica's in-sample 0.15, to allow for the wings).
**H7c (OVX).** Descriptive only - no prediction until the +0.45 residual is understood.

*Data provided by Databento (OPRA consolidated NBBO). Aggregates only.*

## Specification — to be frozen at registration

- Estimator: `tools/ovx_replicate.cboe_sigma2` and `blend30` (Cboe Math v5.0 s3), on
  `surface_monthly.csv` rows (free) and Databento OPRA cbbo-1m at the snapshot minute (reference).
- Window: Fri 9 Oct to Wed 11 Nov 2026; minimum 10 days
  with both readings and an index close. After-close days dropped (23 Sep rule).
- Verdict: fixed wording via `tools/record_verdict.py`, as H5e/H5f.

## Decided at registration (Gabriel, 8 Oct 2026)

1. **An explicit exception to the 11 Nov rule** ("no new hypotheses before 11 Nov unless one needs
   no new data"): H7 needs the monthly legs, so it is registered now, before they exist - the
   cleanest order - rather than after 11 Nov. Recorded in HANDOFF 18.
2. **Money approved:** about $1 of the Databento free credit for the OPRA reference (USO is already
   bought daily for H5f; GLD is added, ~$0.02 a day to 11 Nov). Lifetime spend at registration:
   $0.65 of $100.
3. **Reading:** once, over 9 Oct - 11 Nov 2026, minimum 10 days with both readings and an index
   close, written in fixed wording; no interim verdict.

## What would falsify it

H7a: a mean absolute free-vs-OPRA difference above 0.25 for either symbol. H7b: above 0.30.

*Data provided by Databento (OPRA consolidated NBBO). Aggregates only.*

## Explicitly NOT in this hypothesis

Re-scoring H5e or H3 (their verdicts stand as registered), any change to the registered
surface or estimator, USO-vs-OVX claims (H7c is descriptive), intraday index values.

## Result

Not read yet: due 12 Nov 2026 (`tools/record_verdict.py`, from `tools/h7_reader.py`).

## Adjustment log

**1. 9 Oct 2026, ~18:00 UTC - BEFORE any H7 data (the first monthly row lands 18:40 UTC today, its
OPRA file tonight): a reading error in the input, fixed; nothing registered moves.** Databento writes
OPRA's no-bid as a BLANK bid (all 1.25 million records on disk: never a 0.00 bid); the free feed
writes 0. In Cboe's terms both are a zero bid, which counts toward the two-strike stop (Math v5.0
s3(a)(iii)); only a quote with neither side is null. `ovx_replicate.chain_at` read the blank as null,
so on OPRA the walk skipped no-bid strikes instead of stopping at them. For H7 that would have opened
a free-vs-OPRA gap made of nothing but the two feeds' spelling of "no bid" - on a synthetic chain
with one stray far bid, 1.9 points against H7a's 0.25 bar. Fixed in `ovx_replicate.cboe_quote`,
applied to BOTH feeds (`chain_at` and `h7_reader.quotes_from_rows`); `cboe_sigma2`, `blend30`, the
bars, window and minimum are untouched. Tests: `tools/test_h7.py` now writes the OPRA file in
Databento's own blank form; pressure test section R; auditor mutants `ovx-blank-bid-null`,
`h7-blank-bid-null`. **This is a correction before output, not a post-output adjustment.**

**2. 9 Oct 2026, ~20:30 UTC - BEFORE any H7 reading; when it is read, not what.** Databento serves
day D's OPRA about a day later (the cloud has bought each day at ~D+2 02:00 UTC), and the workflow
also runs at 03:05 UTC on 12 Nov - when 11 Nov's file cannot exist yet. Read once, H7 would have
lost its last day for good. The verdict writer now waits while any monthly day in the window lacks
its OPRA file or its index close (`h7_reader` prints what it is waiting on), and from 19 Nov writes
regardless, naming what is missing. Window, bars, minimum and estimator unchanged.

*In-sample context moves (the bars do not):* on the 8 Oct data, read correctly, Cboe's rules on OPRA
land a mean 0.12 (median 0.08) from GVZ's close (was 0.15 / 0.07) over 17 days, and USO's residual
to OVX is +0.01 over 14 days (H5e's window, 10 days: +0.05, mean absolute 0.29, median 0.23) - the
"+0.45 unexplained" quoted above was mostly this reading error. H7b's 0.30 bar was set as twice 0.15;
it stays 0.30. H7c stays descriptive, as registered.

*Data provided by Databento (OPRA consolidated NBBO). Aggregates only.*

*Data provided by Databento (OPRA consolidated NBBO). Aggregates only.*
