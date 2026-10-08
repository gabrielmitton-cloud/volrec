# DRAFT H7 — The free feed, run through Cboe's own rules, reproduces Cboe's ETF volatility indices

> **DRAFT, 8 Oct 2026. NOT REGISTERED.** Written by Claude for Gabriel's review; nothing is
> frozen until he approves it and it is committed under `hypotheses/` without the DRAFT prefix.
> No reading of the monthly-leg file has been made: its first rows land Fri 9 Oct.

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

## The hypothesis, stated before any monthly-leg reading

**H7a (data).** For USO and GLD, the free-feed Cboe replica and the OPRA Cboe replica at the
same minute differ by a mean absolute 0.25 points or less. Uncertain because the wings are new.
**H7b (GVZ).** The free-feed Cboe replica for GLD lies within a mean absolute 0.30 points of
GVZ's close (twice the OPRA replica's in-sample 0.15, to allow for the wings).
**H7c (OVX).** Descriptive only - no prediction until the +0.45 residual is understood.

## Specification — to be frozen at registration

- Estimator: `tools/ovx_replicate.cboe_sigma2` and `blend30` (Cboe Math v5.0 s3), on
  `surface_monthly.csv` rows (free) and Databento OPRA cbbo-1m at the snapshot minute (reference).
- Window: from the registration date (or 9 Oct, see below) to Wed 11 Nov 2026; minimum 10 days
  with both readings and an index close. After-close days dropped (23 Sep rule).
- Verdict: fixed wording via `tools/record_verdict.py`, as H5e/H5f.

## Two choices for Gabriel before registering

1. **The 11 Nov rule.** HANDOFF 18: "no new hypotheses before 11 Nov unless one needs no new
   data." H7 needs new data. Either (a) register it NOW, before the first monthly row exists -
   the cleanest order, as an explicit exception you grant; or (b) wait until 11 Nov and count
   only days after registration (verdict around early December).
2. **Money.** The OPRA reference costs about $0.02 per symbol per day (measured 8 Oct), so USO
   and GLD to 11 Nov is about **$0.95** more - past the $1-without-asking cap (lifetime spend is
   $0.65 of the $100 free credit). Approve, or run H7a on GLD only (~$0.48), or drop H7a and
   keep H7b, which needs no paid data.

## What would falsify it

H7a: a mean absolute free-vs-OPRA difference above 0.25 for either symbol. H7b: above 0.30.

## Explicitly NOT in this hypothesis

Re-scoring H5e or H3 (their verdicts stand as registered), any change to the registered
surface or estimator, USO-vs-OVX claims (H7c is descriptive), intraday index values.

## Adjustment log

(empty - nothing registered)

*Data provided by Databento (OPRA consolidated NBBO). Aggregates only.*
