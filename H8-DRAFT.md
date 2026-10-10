# H8 — DRAFT registration (NOT registered; drafted 10 Oct 2026, to decide with Gabriel after the 12–19 Nov verdicts)

Nothing here binds until it is copied into `hypotheses/` with a date, committed, and frozen on OSF.
The window it would test, 1 Dec 2026 – 29 Jan 2027, does not exist yet. Everything below the
"calibration" line was measured on 17 Sep – 8 Oct 2026, which is pilot data (PROTOCOL.md step 5).

## The question (PROTOCOL step 1)
The paper asks whether free options data loses precision through its quotes or through the choices
made turning quotes into a volatility number. H8 isolates the quotes: does the free feed's own
quote data, put through the registered estimator, give the same 30-day volatility as the consolidated
market's (OPRA) quotes at the same moment, for all eight funds the project records?

## Hypothesis (proposed wording)
**H8.** From 1 Dec 2026 through 29 Jan 2027, for each of SPY, QQQ, IWM, GLD, USO, TSLA, NVDA and AAPL,
the mean daily difference between the free feed's 30-day model-free estimate and the same estimate
from OPRA quotes - same contracts, both feeds at the snapshot minute (`h8_quotes.py`, S0s - S1s) - lies
within **±Δ** volatility points, shown by two one-sided tests at 5%. Reported per fund; the headline
is how many of the eight show equivalence.

**Δ - to decide with Gabriel. Proposed: 0.10 points**, for these reasons, set from outside the gaps:
- It is about one at-the-money half-spread in the tightest market here (SPY, median 0.07 points,
  below), so a difference inside it is smaller than the cost of trading the option once.
- It is at least twice the largest noise floor measured (USO, 0.051; the others 0.004–0.016).
- The alternative, ±0.25, would pass trivially on the pilot (every fund's mean |gap| is under 0.10)
  and so would test little. **Stated plainly:** the pilot shows a small positive lean (free reads
  high on 7 of 8 funds, +0.01 to +0.09), so at ±0.10 some funds, IWM above all, may genuinely
  fail. That is what makes it a test.

## Instrument readiness [required]
- `tools/h8_quotes.py` (built 10 Oct; re-read cold the same day, which added the snapshot-minute
  reading). Estimator unchanged: `modelfree.model_free_30d`, the ±30% band.
- Known-answer tests: `tools/test_h8.py`, 26 cases. Identical quotes give a gap of exactly 0; a
  uniform 2-cent OPRA premium reads with the right sign; stale quotes are handled both ways;
  n_eff, the smallest detectable effect and the two one-sided tests are checked against hand-computed
  values; the purchase trim keeps exactly what is read.
- Real-format fixtures: Databento's own header and padded OSI symbols, a BLANK for no bid.
- Every report path has run on the real calibration data (all eight funds, 14–16 days each).
- Auditor mutants: h8-blank-bid-dropped, h8-tost-one-sided, h8-neff-ignores-rho, h8-cap-ignored,
  h8-trim-drops-header (all killed, auditor 68/68 on 10 Oct).
- Data: the cloud buys all eight funds daily from 9 Oct 2026 (`opra_reference.py --h8`, own $15 cap).
- **Open, decide at registration:** the Newey-West lag (Lazarus et al. 2018: about 1.3·√T, so ~8 at
  T≈40) and fixed-b critical values (`analyze.fixed_b_pvalue`) in place of t(T−1).

## Noise floor [required]
OPRA against itself one minute later, same contracts, registered estimator (mean |S1n − S1b|),
calibration 17 Sep – 8 Oct: SPY 0.010, QQQ 0.009, IWM 0.007, GLD 0.004, USO 0.051, TSLA 0.015,
NVDA 0.014, AAPL 0.016 points. At Δ = 0.10 the bar is 2× the largest floor and 6–25× the rest.
Practical yardstick, the free feed's median at-the-money (±2%, 20–45 days) half-spread in volatility
points (half-spread / vega): SPY 0.07, QQQ 0.09, IWM 0.13, NVDA 0.28, GLD 0.30, TSLA 0.37, AAPL 0.41,
USO 1.42.

## Smallest detectable effect [required]
Calibration (S0m − S1, 14–16 days): day-to-day sd 0.011–0.052, ρ between −0.34 and +0.23, n_eff 9–16;
the smallest effect found 80% of the time is 0.008–0.039 points. The test window has about 40
trading days, so n_eff should be roughly 25–40 and the detectable effect smaller still: well under
Δ = 0.10. The sample is long enough for this question.

## Calibration readings (pilot, NOT a test; in-sample; for the bar's context only)
Mean free − OPRA at the snapshot minute / mean |gap|, points: SPY +0.055 / 0.055; QQQ +0.038 /
0.038; IWM +0.092 / 0.092; GLD +0.015 / 0.024; USO −0.016 / 0.047; TSLA +0.045 / 0.056;
NVDA +0.078 / 0.078; AAPL +0.013 / 0.021. 97–100% of band contracts matched.
*Data provided by Databento (OPRA consolidated NBBO). Aggregates only.*

## Still to decide with Gabriel (after 19 Nov)
1. Δ (proposed 0.10).
2. The lag and the critical values.
3. Whether the headline is "all eight" or "how many of eight" (proposed: report each, headline the count).
4. The minimum days per fund (proposed 30 of about 40).
