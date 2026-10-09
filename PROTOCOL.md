# The research protocol: what every new hypothesis passes before it is registered

Written 9 Oct 2026, after the full audit. Every fault that audit found came from the same
process gap, not from a gap in technique:

- **An instrument built and trusted the same day.** The OVX replica was written on 8 Oct, and
  H7 was registered on it the same afternoon. Its test fixture wrote OPRA's missing bid as
  "0.0", where Databento's real files leave it blank, so a bug the size of the 0.25 bar
  passed every test.
- **A bar set before the noise floor was measured.** H5e's 0.5 bar was set before anyone
  measured how close even a faithful copy of Cboe's own method gets to OVX at the snapshot
  minute. The answer turned out to be 0.29, more than half the bar.
- **Report code that had never run.** analyze.py's live-panel report crashed on its first call.

So these steps are required, in this order. The pressure test checks that every hypothesis
registered from 10 Oct 2026 carries the three sections marked [required].

## 1. One question, worth its observations
State what the hypothesis answers and how it serves the paper's single question
(PAPER-OUTLINE.md). If it only "seemed interesting", it is not registered.

## 2. The instrument is ready BEFORE registration, not after it [required: "Instrument readiness"]
- **Known-answer test.** The estimator is fed an input whose right answer is known, and gets it.
- **Real-format fixture.** Every test fixture copies a REAL file's layout, including how a missing
  value is written (blank, 0, "." or a sentinel). Open a real file and look first.
- **Every path has run once.** Every report path has run end to end at least once, on
  synthetic or old data.
- **Wait a day.** At least one calendar day passes between finishing the instrument and
  registering on it. Then re-read the code cold.
- **Auditor coverage.** An auditor mutant exists for each new safeguard, and `tools/audit.py`
  reads N of N.

## 3. The noise floor, measured before the bar is chosen [required: "Noise floor"]
Measure how far apart two readings land when nothing is wrong. That means the best possible
version of the measurement against its reference, on data that already exists. The bar must
sit clearly above that floor. Record the floor, how it was measured, and the bar as a
multiple of it. A bar at or below the floor tests the noise, not the hypothesis.

## 4. What the sample can detect [required: "Smallest detectable effect"]
Before registering, estimate the smallest effect the planned sample would find most of the
time: by simulation (`analyze.py --simulate-surface` is the model), or from the noise floor
and the number of independent observations. Say plainly if the sample is too short to
detect the effect the hypothesis cares about. That is a reason to wait or to drop it, not
to loosen the test.

## 5. Written down, then left alone
The bar, window, minimum, estimator and test are fixed in the file and committed before the
data exists (`hypotheses/TEMPLATE.md`). Later changes are logged with a date. Each one is
marked before or after output, and three after-output changes abandon the hypothesis.
Verdicts are written in fixed wording by `tools/record_verdict.py`, never by judgement.

## 6. A second reader
Before a result is published or written up, someone other than its builder reads the code
and the registration. That reader is Claude in a fresh session with the auditor's brief,
and for anything in the paper, the faculty reader (DESIGN-MEMO.md).

## 7. Reproduction
Every published number is printed by a script in this repository, which re-runs and gives
the same number. Recorded results are re-derived before each write-up (as on 9 Oct, when
H1 and H2 were reproduced and the site's tables recomputed).
