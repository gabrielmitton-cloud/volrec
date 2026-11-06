# OSF registration of the index-timing measurement: what to paste (prepared 6 Nov 2026)

**DONE 6 Nov 2026: registered at https://osf.io/4mcgf** (21:06:58 UTC; Secondary Data Preregistration; no
embargo, MIT; public once Gabriel approves OSF's email, or by itself after 48 h). Claude filled it in Gabriel's
browser at his request and submitted on his yes. The template's own fields differ from some headings below,
so the answers were fitted to them while filling (for example, data availability: "available through
protected access"). The OSF page, not this file, is the record of what was submitted.

**What this freezes:** the descriptive index-timing measurement, exactly as the repository registered it on
6 Nov 2026 (`hypotheses/2026-11-06-index-timing.md`), with an independent timestamp. It is frozen before
either verdict it reads is recorded and before any value of the index files is opened. It is descriptive: no
test, no bar, no verdict. The registration also states that PROTOCOL step 2's one-day wait was not kept. Git
dates are set on the committer's own machine; OSF's are not.

**Steps (on osf.io, Gabriel's account; the same as 10 Oct):**
1. Open the project the 10 Oct registration came from: https://osf.io/n8y3z
2. *Files*: upload `hypotheses/2026-11-06-index-timing.md`, `docs/drafts/2026-11-04-index-timing-plan.md`,
   `tools/index_timing.py` (the reader; its sha256 is in the registration) and `PROTOCOL.md`. No data files.
3. *Registrations* -> *New registration* -> template **"Secondary Data Preregistration"** (the one used
   on 10 Oct).
4. Paste each answer below into the field with the matching heading. Where a field is not listed, write
   "Not applicable".
5. Attach the uploaded files where the form offers it; choose **no embargo** (the repository is already
   public); submit. A registration cannot be edited afterwards; that is the point.
6. The link goes into the registration file's header, HANDOFF and this file.

---

## Title
Free versus authoritative options data: how much of the registered H5e and H7 gaps is OVX and GVZ moving
after the snapshot? (Descriptive index-timing measurement)

## Description
A non-commercial undergraduate study (Pepperdine University) measuring how much precision free,
retail-grade options data loses against authoritative references. Two registered hypotheses, H5e and H7
(https://osf.io/z5gfu), compare estimates built from quotes taken at about 14:30 New York with Cboe's daily
closes of OVX and GVZ. Their gaps therefore mix the estimate's own error with the index moving between the
snapshot and the close. This registration freezes a DESCRIPTIVE measurement that splits each gap exactly into
those two parts. It uses the days covered by licensed intraday index data (Databento Core Indices, one-second
bars, OVX and GVZ only). There is no test, no bar and no verdict.

It was registered first in the public repository https://github.com/gabrielmitton-cloud/volrec on 6 Nov 2026
(`hypotheses/2026-11-06-index-timing.md`). That was before either verdict it reads was recorded and before
any value of the index files was opened. The repository state at registration is commit
`e02724e1452ad09fd716e4f69109bb7cd80cecac`. The plan it implements was committed on 4 Nov 2026 (commit 28b69f3), also
before any value was opened.

Disclosed deviation: the project's protocol asks for a calendar day between finishing an instrument and
registering on it. The reader was finished and registered on the same day, at the researcher's choice, and
the registration file logs this.

## Research questions
This uses the days the intraday index data covers (21 Oct - 11 Nov 2026) and counts the registered readings
on them. The readings are H5e's skip-only estimate and its registered estimate (USO vs OVX), and H7's OPRA
replica and free-feed replica (USO vs OVX, GLD vs GVZ). For each:
- How large is the estimate's gap to the index at the snapshot minute, and in which direction?
- How large is the index's move from that minute to the close, and in which direction?
- Do the two offset each other?

## Hypotheses
None. This is a descriptive measurement: it makes no prediction, and no result can confirm or falsify
anything. It is registered so that its definitions, days and computations are fixed before the data is read.

## Data: datasets used
1. The registered estimates of H5e and H7, rebuilt by the registered code from two sources:
   - the project's daily recordings of Alpaca's free indicative options feed;
   - OPRA consolidated quotes at one-minute resolution (Databento, OPRA.PILLAR cbbo-1m), for H7's OPRA
     replica.
2. Cboe's published daily closes of OVX and GVZ (`OVX_History.csv`, `GVZ_History.csv`).
3. Databento Core Indices (DBIX.CORE), one-second bars, OVX and GVZ only:
   - 21 Oct - 3 Nov 2026 was bought on 4 Nov 2026;
   - 4 - 11 Nov will be bought after 11 Nov.

## Data: public availability
(1) The free-feed recordings are public in the repository, published with Alpaca's agreement for personal,
non-commercial research use. OPRA is licensed and not redistributable. (2) Public on Cboe's website.
(3) Licensed; not redistributable. Only aggregates are published (dates and counts, never an index value),
credited "Data provided by Databento".

## Data: access
https://github.com/gabrielmitton-cloud/volrec ; Cboe index history files ; Databento (licensed:
OPRA.PILLAR, DBIX.CORE).

## Data: date of download / collection
- Free feed: recorded each trading day by the project's scheduled workflows.
- OPRA: bought one day at a time, about two days after each trading day.
- Index files, 21 Oct - 3 Nov: bought 4 Nov 2026 and sealed by sha256 the same day (structure read only).
- Index files, 4 - 11 Nov: bought after 11 Nov. Their sha256 are added to the same seal before any of them
  is read.
- Cboe closes: read at analysis time.

## Data collection procedures
In the repository: the README, the H5e and H7 hypothesis files, and the registration file's
"Specification".

## Codebook
The index files follow Databento's documented OHLCV schema (one-second bars stamped at the start of their
second). The registration file's "Specification" defines E, T, I(T) and C.

## Variables: manipulated
Not applicable (observational).

## Variables: measured
For each counted day and reading:
- E: the registered estimate.
- T: the snapshot minute, the median quote time of the rows the estimate used, floored to the minute.
- I(T): the index's close in the last one-second bar whose second has ended by T. It must come from T's
  trading day, at or after 09:31 New York, and be at most 60 s old.
- C: Cboe's published close.
The split is the exact identity E - C = (E - I(T)) + (I(T) - C).

## Knowledge of data: prior publication / dissemination
- The registered gaps E - C are public through the project's daily outputs (H5e's table through 2 Nov).
- H5e's first verdict (8 Oct 2026: FAILS) is published.
- Neither H5e's final reading nor H7's reading is recorded yet.
- No value of the intraday index files has been read or published.

## Knowledge of data: prior knowledge of the data
- **The index files:** structure only, read on 4 Nov 2026 (rows and symbols per file, columns, timestamps).
  No value has been read.
- **The registered gaps E - C:** H5e's daily table through 2 Nov, the recorded panels through 5 Nov and
  H7's in-sample figures (14 Sep - 7 Oct). Planning numbers were computed on 6 Nov over 21 Oct - 5 Nov
  (sd 0.25-1.08 points; lag-1 autocorrelation -0.12 to +0.23). These set the scale only.
- **The size of moves after the snapshot**, indirectly and named as proxies:
  - The lab's stress-month OPRA days (2016-2026) found the registered estimator moving a median 0.53 points
    between 14:30 and 15:55. That is the estimate measured twice, not the index.
  - On H5e's first ten days, the OPRA replica sat a mean absolute 0.29 points from OVX's close, a figure
    that contains the move.
- **LSEG:** OVX and GVZ intraday data were refused (an entitlement gap), so none was seen.

None of these chose a window, source, exclusion or estimator. The days are set by Databento's usage-based
start (21 Oct) and the verdict windows' end (11 Nov).

*Data provided by Databento. Index closes: Cboe Global Markets. Aggregates only.* (Credit line added in the
repository after submitting; on OSF the credit is in the data-availability answer.)

## Analysis: statistical models
None fitted. For each reading and index, on identical days, the reader computes:
- the signed means of E - C, E - I(T) and I(T) - C, which add up exactly (the residue is printed);
- the mean absolute value of each;
- the correlation between the residual and the move;
- each part's lag-1 autocorrelation and effective number of observations, n_eff = T(1 - rho)/(1 + rho)
  (a negative rho counts as 0; the floor is 1);
- each day's quote-time spread around T.

A sensitivity uses the bar nearest T within 15 s either side, reported on its own days with its own count.
The computation is done by `tools/index_timing.py` (sha256
e65b52704d0b4a28be455a1dc4657ad5309133005526a194bf0dfc27bf4afb46).

## Analysis: effect size
Not applicable (no test). For scale: with about 16 covered days, a mean part smaller than roughly
0.8-1.1 points (USO vs OVX) or 0.2 points (GLD vs GVZ) would not stand out from day-to-day scatter. That is
2.8 sd / sqrt(n_eff) on the registered gaps.

## Analysis: statistical power
Not applicable (no test). See effect size for scale.

## Analysis: inference criteria
None: no significance test, bar or verdict. The results describe the covered days only. Those days are not
a random sample: they are the windows' last stretch, when OVX rose.

## Analysis: data exclusion
- Only days the index files cover are measured. Every other counted day is listed with its reason.
- A day whose I(T) fails the rules above is listed as not measured; it is never filled.
- A day whose last one-second value is more than 0.05 from C is flagged and listed, but kept.

## Analysis: missing data
Never filled. A missing bar, a bar outside the rules or a close that is not a finite number leaves the day
listed as not measured, with the reason.

## Analysis: reliability and robustness
The reader runs nothing until H5e's final reading and H7's reading are both recorded. It refuses unless:
- every index file matches its sealed sha256;
- the readings rebuild at the frozen risk-free rate;
- the rebuilt readings give the recorded verdicts' own days and numbers.

Testing: 98 known-answer tests on synthetic files. The project's auditor breaks each of the reader's 28
safeguards on purpose, and every break is caught (217 of 217 across the project).

## Analysis: exploratory analyses
None beyond the sensitivity above. Other indices, intraday paths after T and causes of absolute error are
excluded and would need their own registration.

## Statement of integrity
The answers are accurate to the best of my knowledge. Some registered gaps were observed and the index
files' structure was read before this registration, as disclosed above; no value of the index files has been
read. The protocol's one-day wait before registering was not kept, as disclosed.
