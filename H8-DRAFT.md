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
- Known-answer tests: `tools/test_h8.py`, 49 cases (26 until 4 Nov; 32 that evening; 36 after Astra's review the same night; 37 on 5 Nov, when `day_pair` began carrying the snapshot minute it priced at, for choice 6; 43 the same day with choice 7's split by side, and 49 after Astra's follow-up review of it). Identical quotes give a gap of
  exactly 0; a uniform 2-cent OPRA premium reads with the right sign; stale quotes are handled both ways;
  n_eff, the smallest detectable effect and the two one-sided tests are checked against hand-computed
  values; the purchase trim keeps exactly what is read. Since 4 Nov: the lag rule (8 at 41 days, 8 at 36,
  7 at 30); at lag 0 the fixed-b p at 1.70477 is the exact 0.05 within simulation error (Newey-West at lag 0
  is √(T/(T−1)) times Student's t); a gap 1.9 standard errors inside each bound passes under t(40) and fails
  under fixed-b at lag 8; each one-sided test reads its own tail. Since Astra's review: `tost` hands H8's own
  200,000 draws to the shared null (item 2), and on a null fixed by hand a draw equal to the statistic counts
  as "at or beyond" while a p of exactly 0.05 is not below 0.05.
- Real-format fixtures: Databento's own header and padded OSI symbols, a BLANK for no bid.
- Every report path has run on the real calibration data (all eight funds, 14–16 days each).
- Auditor mutants: h8-blank-bid-dropped, h8-tost-one-sided, h8-neff-ignores-rho, h8-cap-ignored,
  h8-trim-drops-header (all killed, auditor 68/68 on 10 Oct); since 4 Nov also h8-tost-uses-t,
  h8-fixedb-two-sided and h8-lag-rule, and after Astra's review h8-reps-shared, h8-reps-not-passed,
  h8-tie-excluded, h8-tie-excluded-upper and h8-threshold-inclusive (each killed when checked alone before
  it was added).
- Data: the cloud buys all eight funds daily from 9 Oct 2026 (`opra_reference.py --h8`, own $15 cap).
- **Choice 6's reader, built 5 Nov 2026 (item 6 below; descriptive, never part of the verdict):**
  `tools/h8_index.py`. It reads H8's own fund-days (`h8_quotes.fund_days`, which `main` now reads too; H8's
  report on the real calibration data was byte-for-byte the same before and after that change) and the index
  at the snapshot minute through the timing plan's reader (`index_timing`: seal, file inventory, bar parser,
  `index_at`; its bar parser now takes the six indices for H8's folder only, its own default still OVX and GVZ).
  A fund-day counts only when both feeds' estimates and I(T) are there and finite; every window trading day
  (`panel_health`'s calendar, the project's one copy: 41 days) is accounted for once per fund, never filled.
  It refuses the timing plan's sealed folder, and refuses to read anything until the window has closed
  (30 Jan 2027). Tests: `tools/test_h8_index.py`, 47 cases on SYNTHETIC files in DBIX's recorded layout;
  pressure test "H8's index reading's tests pass"; auditor mutants h8index-opens-before-window,
  h8index-reads-timing-folder, h8index-one-feed-day, h8index-window-ignored, h8index-day-dropped,
  h8index-reads-near, h8index-reseals, h8index-nonfinite-estimate, h8index-calendar-ignored,
  timing-default-widened and timing-nonfinite-index (each made the tests fail when tried alone before it was
  added). Astra's review the same morning found two gaps, both fixed: a trading day missing from both sources
  vanished (now listed from the calendar), and a close that is not a finite number would have been counted
  (now not measured, in `index_at` itself, so the timing reader has the same rule; its tests: 64). Purchases: the private `dbix-h8/buy.py` (committed 5 Nov, nothing bought) buys each
  window trading day through yesterday not yet on disk, priced first, own $1 cap (tag `-h8dbix`), and seals
  each file as it lands (`h8_index.sealed_readme`, read back by the timing reader's `seal`). It runs from a
  daily.yml step to be added about 20-24 Nov, after the verdicts (daily.yml is not edited before them): every
  scheduled weekday, so well inside the 10-day rule. Never run on real index data yet: there is none until
  1 Dec.
- **Was open, decided 4 Nov and built the same evening:** the Newey-West lag (`h8_quotes.lag_for`, the
  whole number nearest 1.3·√T) and fixed-b one-sided p-values (`h8_quotes.tost` reads
  `analyze.fixed_b_null`; t(T−1)'s p-values come back beside, never in place). Item 2 at the end.

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

**By side (item 7's first reading; pilot, 5 Nov 2026, already seen).** Computed for the first time after
the commit that carries item 7's definition (`7cfacc9`), on every OPRA file then on disk: 14-18 Sep to
3 Nov 2026, 32-34 fund-days per fund. Mean put part / call part of the snapshot gap, in points, puts
swapped first (calls first gives the same to within 0.001 for every fund, so the interaction is negligible
here), with the gap:

| Fund | put part | call part | gap | days |
|---|---|---|---|---|
| SPY | +0.030 | +0.019 | +0.049 | 33 |
| QQQ | +0.027 | +0.016 | +0.043 | 33 |
| IWM | +0.048 | +0.030 | +0.078 | 33 |
| GLD | +0.014 | +0.007 | +0.020 | 34 |
| USO | -0.014 | +0.001 | -0.013 | 32 |
| TSLA | +0.019 | +0.018 | +0.037 | 32 |
| NVDA | +0.031 | +0.027 | +0.058 | 33 |
| AAPL | +0.002 | +0.007 | +0.010 | 33 |

Read plainly: on SPY, QQQ, IWM and GLD, about 60-70% of the gap sits with the puts; on TSLA and NVDA it is
close to even; on AAPL more of it sits with the calls. In-sample pilot data, already seen, so it is not
evidence for the window. The registration names item 7 as computed on these days.
*Data provided by Databento (OPRA consolidated NBBO). Aggregates only.*

## Decided 4 Nov 2026 (was: still to decide with Gabriel after 19 Nov)
Settled early by Vega, under Gabriel's go-ahead that day to settle now whatever can be settled now and is in
the project's interest, and **approved by Gabriel the same day** ("I approve the decisions"). Nothing binds
until registration. Target:
registered about Tue 24 Nov, with an OSF freeze in Gabriel's browser, a week before the window opens.
1. **Δ = 0.10**, for the reasons above, the 12 Oct correction included.
2. **Lag: the whole number nearest 1.3√T**, T = the fund's measured days (8 at T = 41), fixed now as a rule
   because T is not yet known. **Critical values: fixed-b, one-sided for each of the two tests**, from
   `analyze.fixed_b_null` at that T and lag (the share of null draws at or beyond the statistic, in the
   direction tested); t(T−1)'s p-values printed beside, never in place. The simulated null (iid
   Gaussian, seeded; 200,000 draws for H8, see below) is an approximation at T of 30-41, and at 200,000
   draws a p-value near 0.05 carries a simulation standard error of about 0.0005. Before registering, `h8_quotes.tost` gains this with a known-answer test and
   an auditor mutant, then at least a day passes (PROTOCOL step 2). *Built 4 Nov (evening): see Instrument
   readiness. Measured that night at T = 41, lag 8: the shared seeded 4,000-draw null puts the one-sided 5%
   points at 2.03 (upper) and -2.06 (lower); 200,000 draws put them at 2.09 and -2.11 (the fixed-b limit at
   b = 9/41, simulated at T = 2,050 and 4,100: about 2.10). At the 200,000-draw points the 4,000-draw null gives p = 0.047 and 0.046:
   this seed's draws run light in both tails here, about one simulation standard error each (sampling error,
   not a bias of the method), and light tails are the lenient direction for an equivalence test.
   **Changed the same night, as Astra's review recommended:** H8 uses 200,000 seeded draws of its own
   (`h8_quotes.H8_REPS`, the same seed; about 8 seconds at T = 41); the shared default of 4,000 is
   unchanged for every registered figure. More draws make the simulation precise; they do not make the
   iid-Gaussian fixed-b approximation exact at T of 30-41. Vega's call, approved by Gabriel the same
   night ("all the descions seem good to me"). (Until this change the note read: "Kept at 4,000 so every fixed-b number in the project
   comes from the same seeded null", and gave the gap as 0.0455 at 2.11, a point measured on the upper tail
   only.)*
3. **Each fund reported; the headline is the count** of the eight that show equivalence: a tally of eight
   separate tests, not a joint 95% statement about all of them.
4. **At least 30 measured days** of the window's 41 trading days (22 in December, 19 in January). A fund
   with fewer is reported as not measured and is not counted among those showing equivalence.
5. **Yes:** the bid / ask / mid breakdown is a secondary, descriptive reading of the window.
6. **Yes**, on its own $1 cap (ledger tag `-h8dbix`, inside the $120 lifetime cap): bought at least every 10
   calendar days through the window, because usage-based access reaches back only about 14 days. It reads
   the files with the timing plan's reader once that reader is built and tested; if it is not ready by
   registration, choice 6 is dropped rather than registered on an untested path. *Built and tested 5 Nov
   (Instrument readiness above): `tools/h8_index.py` through the timing plan's reader, 47 synthetic cases,
   eleven auditor mutants; the purchases' daily.yml step is still to add, about 20-24 Nov.*
7. **Yes - added 5 Nov 2026 (Vega's proposal; Gabriel: "if u think it could actually stand to help the
   project then sure go for it"): the snapshot gap split by side,** a third secondary, descriptive reading,
   and the way skew enters this study without a new measure or a new reference. On each fund-day, on the
   contracts H8's snapshot reading already uses (`day_pair`'s S0s and S1s: the same contracts in both feeds,
   OPRA within 120 s of the snapshot minute), the registered estimator (`modelfree.model_free_30d`, unchanged)
   runs twice more on mixed quotes: OPRA's puts with the free feed's calls (M_P), and OPRA's calls with the
   free feed's puts (M_C). The gap S0s - S1s then splits exactly, two ways: puts swapped first, put part
   S0s - M_P and call part M_P - S1s; calls swapped first, call part S0s - M_C and put part M_C - S1s. Both
   orders are reported, and the distance between them is the interaction (the forward and the strike K0 use
   both sides), never assigned to either side. Per fund: the mean and the mean absolute of each part in each
   order, beside the mean gap, over the fund-days on which all four estimates exist and are finite. No bar,
   no test, never part of the H8 verdict. **Why:** Hentschel (2003) predicts that small price errors matter
   most away from the money; a level test can hide wing errors that offset, and this says whether the free
   feed's gap sits with the puts (the crash-protection side), the calls, or both. Defined here before any of
   it was computed on any data; built and tested before registration, or dropped, like choice 6. *Built and
   tested 5 Nov, after this definition was written: `day_pair`'s MPs and MCs and `sides` in
   `tools/h8_quotes.py`, and one line in its report on the split's own sample, with its count and no minimum
   (so a fund with few quote-time pairs still shows it). Twelve known-answer cases in `tools/test_h8.py`: a
   move in OPRA's puts alone is all put part in both orders and a move in its calls alone all call part,
   exactly; each order adds up to the gap; hand-computed means; the printed line, also for a fund with no
   quote-time pair, one eligible day or none; and a fixture whose quote-time and snapshot quotes, and sets,
   differ, where both mixes must equal the estimator on inputs assembled by hand and the order must matter.
   Auditor mutants h8-sides-swapped, -one-order, -nonfinite-kept, -not-printed, -minimum, -quote-time-set and
   -quote-time-quotes, each tried alone first. Not computed on any real data before the commit that carries
   this definition.*

*The six questions as drafted, kept for their reasons (and, for 6, its specification):*
1. Δ (proposed 0.10; its trading-cost reason was corrected on 12 Oct and now holds only for the
   less liquid funds, while the noise-floor reason stands).
2. The lag and the critical values.
3. Whether the headline is "all eight" or "how many of eight" (proposed: report each, headline the count).
4. The minimum days per fund (proposed 30 of about 40).
5. Whether to name the bid / ask / mid breakdown above as a secondary, descriptive reading of the
   window (proposed: yes; it explains the lean without changing the test).
6. **Proposed 4 Nov 2026 (Vega; to decide with Gabriel):** a second secondary, descriptive reading - both
   feeds' estimates against the **official index at the same minute**, from Databento Core Indices
   (`DBIX.CORE`, one-second bars; usage-based, about $0.01 a trading day for these six indices, so about
   $0.50 over the window, from H8's budget or its own, Gabriel's call). Pairs: USO/OVX, GLD/GVZ and
   AAPL/VXAPL (the index is built on the same fund's or stock's options); SPY/VIX, QQQ/VXN and IWM/RVX
   (built on SPX, NDX and RUT options, so the index-versus-fund difference is part of any gap). TSLA and
   NVDA have no Cboe index. The index value is the close of the last one-second bar whose second has
   ended by the snapshot minute (`opra_reference.snapshot_minute`; Databento's OHLCV documentation, read
   4 Nov, stamps a bar with the inclusive start of its second), so never one printed after it. It must be
   from the same trading day and at most 60 s old; otherwise that fund-day is not measured, never filled,
   and the count of such days is reported. Quotes are matched to that minute within up to 120 s, so the
   alignment is to the minute, not to each quote's instant. Per fund: mean and mean absolute (estimate
   minus index), free and OPRA side by side; no bar, no test, never part of the H8 verdict.
   **Why:** it takes out the snapshot-to-close move that clouds every index comparison so far (H3, H5e,
   H7), and says how far each feed's estimate sits from Cboe's own number at the snapshot minute. **Caveat:** this
   project's estimator (weekly expiries, a +/-30% band, whole-day time) is not Cboe's, so a gap here mixes
   method with data; H8's primary free-versus-OPRA test stays the only clean data comparison. Data
   checked 4 Nov: the six indices are offered (21 Oct onward on usage-based access; earlier history needs a
   subscription), each published every 15 s. *Data provided by Databento. Aggregates only.*
