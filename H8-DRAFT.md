# H8 — DRAFT registration (NOT registered; drafted 10 Oct 2026, to decide with Gabriel after the 12–19 Nov verdicts)

Nothing here binds until it is copied into `hypotheses/` with a date, committed, and frozen on OSF.
The window it would test, 1 Dec 2026 – 29 Jan 2027, does not exist yet. Everything below the
"calibration" line was measured on 17 Sep – 8 Oct 2026, which is pilot data (PROTOCOL.md step 5).

## The question (PROTOCOL step 1)
The paper asks whether free options data loses precision through its quotes or through the choices
made turning quotes into a volatility number. H8 isolates the quotes: does the free feed's own
quote data, put through the registered estimator, give the same 30-day volatility as the consolidated
market's (OPRA) quotes at the same moment, for all eight funds the project records?

Why this is the right question, from the provider's own words (checked at source 12 Oct 2026): Alpaca
documents the feed as "a free derivative of the original OPRA feed" whose "quotes are not actual OPRA
quotes", and an Alpaca staff member says on its forum that it is "based upon real time OPRA data but it's
randomized a bit" (12 Sep 2025) and "can vary from the actual `opra` data" (1 Feb 2026); staff statements,
not contractual terms. So the free feed is a deliberately altered copy of exactly the reference H8 buys,
and H8 measures what the alteration costs once quotes become a volatility number. No published
measurement of that size turned up in the literature searches of 9 and 12 Oct 2026.

## Hypothesis (proposed wording)
**H8.** From 1 Dec 2026 through 29 Jan 2027, for each of SPY, QQQ, IWM, GLD, USO, TSLA, NVDA and AAPL,
the mean daily difference between the free feed's 30-day model-free estimate and the same estimate
from OPRA quotes - same contracts, both feeds at the snapshot minute (`h8_quotes.py`, S0s - S1s) - lies
within **±Δ** volatility points, shown by two one-sided tests at 5%. Reported per fund; the headline
is how many of the eight show equivalence.

**Δ - to decide with Gabriel. Proposed: 0.10 points**, for these reasons, set from outside the gaps:
- **Corrected 12 Oct 2026.** The first draft called 0.10 "about one at-the-money half-spread in the
  tightest market (SPY, 0.07)". That 0.07 was the FREE feed's half-spread. On OPRA, the real market,
  SPY's is 0.034 (below), so 0.10 is about three real SPY half-spreads, about one in IWM (0.102),
  and less than one in GLD, USO, TSLA, NVDA and AAPL. The trading-cost reason therefore supports
  0.10 for the less liquid funds only; for SPY and QQQ it is a looser bar than first stated.
- It is at least twice the largest noise floor measured (USO, 0.051; the others 0.004–0.016). This
  reason is unchanged.
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
Practical yardstick: the median at-the-money (±2%, 20–45 days) half-spread in volatility points
(half-spread / vega, the free feed's vega for both columns so only the quote source differs), at
the snapshot minute, 17 Sep – 9 Oct. **OPRA (the real market) / the free feed:**

| Fund | OPRA | free | free ÷ OPRA | contracts |
|---|---|---|---|---|
| SPY | 0.034 | 0.070 | 2.07 | 916 |
| QQQ | 0.066 | 0.086 | 1.31 | 894 |
| IWM | 0.102 | 0.130 | 1.27 | 586 |
| GLD | 0.315 | 0.309 | 0.98 | 758 |
| USO | 1.331 | 1.366 | 1.03 | 458 |
| TSLA | 0.305 | 0.371 | 1.22 | 254 |
| NVDA | 0.280 | 0.288 | 1.03 | 170 |
| AAPL | 0.420 | 0.416 | 0.99 | 264 |

The yardstick is OPRA's column. Over ten years (lab/ weekly samples, 2016-2026, nearest-30-day ATM;
lab/main_links.py) OPRA's median is SPY 0.028, QQQ 0.051, IWM 0.080, GLD 0.121, USO 0.737 - SPY's
pilot is typical, while GLD's and USO's 2026 spreads run about 2.8x their decade medians. The first draft (10 Oct) quoted the free column on 17 Sep – 8 Oct
(USO then 1.42); it overstated SPY's real half-spread about twofold. *Data provided by Databento
(OPRA consolidated NBBO). Aggregates only.*

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

**Where the lean comes from (pilot, 12 Oct 2026; exploratory, already seen).** At-the-money
(±2%, 20–45 days), each free quote matched to OPRA at the free quote's own time (within 120 s),
median free − OPRA in volatility points (difference / vega), bid / ask / mid:

| Fund | bid | ask | mid | contracts |
|---|---|---|---|---|
| SPY | +0.000 | +0.094 | +0.044 | 916 |
| QQQ | +0.012 | +0.136 | +0.060 | 894 |
| IWM | +0.000 | +0.144 | +0.075 | 586 |
| GLD | +0.046 | +0.049 | +0.023 | 758 |
| USO | −0.121 | +0.109 | −0.029 | 458 |
| TSLA | −0.100 | +0.168 | −0.013 | 254 |
| NVDA | +0.111 | +0.235 | +0.141 | 170 |
| AAPL | +0.049 | +0.037 | +0.014 | 264 |

Read plainly: on SPY, QQQ and IWM the free bid sits on OPRA's bid while the free ask sits higher,
so the free mid, and with it the volatility estimate, reads high. On USO and TSLA the free quote is
wider on both sides, roughly symmetrically, so the mid barely moves. On NVDA both sides sit higher.
Medians at the money only, on about three weeks: a mechanism to name in the registration as a
secondary, descriptive reading, not a result.
*Data provided by Databento (OPRA consolidated NBBO). Aggregates only.*

## Still to decide with Gabriel (after 19 Nov)
1. Δ (proposed 0.10; its trading-cost reason was corrected on 12 Oct and now holds only for the
   less liquid funds, while the noise-floor reason stands).
2. The lag and the critical values.
3. Whether the headline is "all eight" or "how many of eight" (proposed: report each, headline the count).
4. The minimum days per fund (proposed 30 of about 40).
5. Whether to name the bid / ask / mid breakdown above as a secondary, descriptive reading of the
   window (proposed: yes; it explains the lean without changing the test).
