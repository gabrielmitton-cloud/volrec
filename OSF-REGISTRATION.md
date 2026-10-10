# OSF registration: what to paste (prepared 10 Oct 2026)

**DONE 10 Oct 2026: registered and live at https://osf.io/z5gfu** (17:43 UTC; Secondary Data
Preregistration; public, MIT). Claude filled it in Gabriel's browser at his request; a few answers were
tightened while filling (e.g. H5e's expected sample is about 35 trading days). The OSF page, not this
file, is the record of what was submitted.

**What this freezes:** the two hypotheses still open, H5e (final reading over 23 Sep - 11 Nov) and
H7 (9 Oct - 11 Nov), exactly as the repository already records them, with an independent timestamp.
Both were registered first in git (H5e: commit `ac237a6`, 23 Sep 2026; H7: commit `1d1bef7`,
8 Oct 2026). Git dates are set on the committer's own machine; OSF's are not. The registration
says plainly that it is made after data collection began and after H5e's first verdict.

**Steps (Gabriel, on osf.io):**
1. *Create new project*: title below; storage location United States; leave it public.
2. In the project, *Files*: upload the two hypothesis files from `hypotheses/`
   (`2026-09-19-h5-wing-quote-quality.md`, `2026-10-08-h7-free-feed-cboe-replica.md`),
   `PROTOCOL.md`, and `LICENSE`. No data files.
3. *Registrations* -> *New registration* -> template **"Preregistration Template for Secondary
   Data Analysis"** (if the menu names it slightly differently, pick the secondary-data one).
4. Paste each answer below into the field with the matching heading. Where a field is not listed,
   write "Not applicable".
5. Attach the uploaded files where the form offers it; choose **no embargo** (the repository is
   already public); submit. A registration cannot be edited afterwards - that is the point.
6. Send me the registration's DOI or link; it goes into HANDOFF, the hypothesis files and the paper.

---

## Title
Free versus authoritative options data: does a retail-grade feed reproduce Cboe's ETF volatility
indices? (Registered hypotheses H5e and H7)

## Description
A non-commercial undergraduate study (Pepperdine University) measuring how much precision free,
retail-grade options data (Alpaca's indicative feed) loses against authoritative references: Cboe's
published volatility indices and consolidated OPRA quotes. This registration freezes, with an
independent timestamp, two hypotheses first committed to the public repository
https://github.com/gabrielmitton-cloud/volrec (H5e on 23 Sep 2026, commit ac237a6; H7 on 8 Oct 2026,
commit 1d1bef7). It is made on 10-11 Oct 2026, after data collection began. The repository state at
registration is commit `8d3a555ec6890dd3a8c0208e4d26d55fca814c2d`.

## Research questions
1. With every out-of-the-money zero-bid quote skipped, does a 30-day model-free volatility estimate
   built from the free feed track Cboe's OVX index? (H5e)
2. Run through Cboe's own methodology (monthly expiries, full strike walk, minute clock), does the free
   feed reproduce the same calculation done on consolidated OPRA quotes at the same minute, and does
   it reproduce Cboe's GVZ index? (H7)

## Hypotheses
**H5e.** From 23 Sep 2026 through 11 Nov 2026, USO's 30-day model-free estimate built from the free
feed's +/-30% strike surface plus its wider band, with every out-of-the-money zero-bid quote skipped and
no stop rule, has a mean absolute gap to OVX's close under 0.5 volatility points, AND is closer to OVX
than the project's registered estimator on a majority of counted days. Falsified if either part fails.

**H7a.** From 9 Oct 2026 through 11 Nov 2026, for USO and for GLD, the Cboe-method replica computed
on the free feed and the same replica computed on OPRA consolidated quotes at the same minute differ by
a mean absolute 0.25 volatility points or less. Falsified if either symbol exceeds 0.25.

**H7b.** Over the same window, the free-feed replica for GLD lies within a mean absolute 0.30 points
of GVZ's close. Falsified above 0.30.

**H7c.** USO against OVX: descriptive only, no prediction.

Direction and rationale for each are in the attached hypothesis files ("Why this hypothesis exists").

## Data: datasets used
1. The project's own daily recordings of Alpaca's free indicative options feed (`data/surface.csv`,
   `data/surface_wide.csv`, `data/surface_monthly.csv`), recorded once each trading day since September 2026 (at about 14:30
   New York since 1 Oct 2026; earlier runs landed later in the day).
2. Cboe's published daily closes of OVX and GVZ.
3. OPRA consolidated best bid and offer at one-minute resolution (Databento, OPRA.PILLAR cbbo-1m).

## Data: public availability
(1) Public in the repository, published with Alpaca's agreement for personal, non-commercial research
use. (2) Public on Cboe's website. (3) Licensed; not redistributable. Only aggregates are published,
credited "Data provided by Databento".

## Data: access
https://github.com/gabrielmitton-cloud/volrec ; Cboe index history files ; Databento (licensed).

## Data: date of download / collection
The free feed is recorded daily by the project's scheduled workflows; each row carries its timestamp.
Cboe closes are read at analysis time. OPRA is bought one day at a time, about two days after each
trading day.

## Data collection procedures
Described in the repository README ("Method", "Data notes and limitations") and in each hypothesis file.

## Codebook
Column definitions are in the README and in `record.py` and `surface.py`.

## Variables: manipulated
Not applicable (observational).

## Variables: measured
Daily 30-day model-free implied volatility estimates (free feed and OPRA, computed by the registered
code: `modelfree.model_free_30d` for H5e; `tools/ovx_replicate.cboe_sigma2` and `blend30` for H7),
and the published OVX and GVZ closes.

## Knowledge of data: prior publication / dissemination
H5e's first verdict, at its 10-day minimum, was recorded on 8 Oct 2026: FAILS (mean gap 0.90; closer
on 2 of 10 days). It is published on the project website. The final reading over the whole window is
the one written up. H7 has no reading yet.

## Knowledge of data: prior knowledge of the data
H5e was motivated by three days (18, 21 and 22 Sep 2026) observed before it was written; those days
are excluded, and it is judged only from 23 Sep on. Its first ten counted days (23 Sep - 7 Oct) have
been seen. H7's bars were set knowing in-sample OPRA-replica results from 14 Sep - 7 Oct (stated in
its file, "What is ALREADY known"). H7's window began 9 Oct; its readings have not been computed.
Every change since registration is in each file's adjustment log, marked before or after output; none
changes a bar, window, minimum or estimator.

## Analysis: statistical models
Fixed-rule comparisons, not fitted models. H5e: the mean absolute gap of the daily estimate to OVX,
and a count of days closer than the registered estimator. H7a: the mean absolute free-minus-OPRA
difference per symbol. H7b: the mean absolute gap to GVZ. Computed by `modelfree.py --wide --through
2026-11-11` (H5e) and `tools/h7_reader.py` (H7). Verdicts are written in fixed wording by
`tools/record_verdict.py`.

## Analysis: effect size
The bars above are the effect sizes: 0.5 volatility points (H5e), 0.25 (H7a) and 0.30 (H7b).

## Analysis: statistical power
Not computed at registration. These are threshold tests on a short window; the write-up reports the
number of days, the day-to-day autocorrelation and the effective number of independent observations
beside each verdict (PROTOCOL.md, step 4).

## Analysis: inference criteria
Pass or fail against the fixed bars above; no significance test decides the verdict.

## Analysis: data exclusion
Days recorded after the 16:00 New York close are dropped (rule of 23 Sep 2026; one day so far,
28 Sep). H7 counts only days with both readings and an index close. Minimum 10 counted days for each.

## Analysis: missing data
The verdict writer waits while any window day lacks its index close (and, for H7, its OPRA file), and
from 19 Nov 2026 writes regardless, naming every day still missing.

## Analysis: reliability and robustness
H5e's final is cross-checked against the reader's own full-precision tally. Every instrument is checked
against known answers (`tools/calibrate.py`), and every safeguard is broken on purpose to prove it
fails (`tools/audit.py`). Registered numbers reproduce from a fresh clone (README).

## Analysis: exploratory analyses
The step-by-step decomposition of the gap (`tools/ovx_replicate.py`) and any timing analysis with
intraday index data are exploratory and labelled as such.

## Statement of integrity
The answers are accurate to the best of my knowledge. The data were partly observed before this
registration, as disclosed above. Failures will be reported as failures.
