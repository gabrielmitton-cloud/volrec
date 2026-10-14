# lab/ registration - the retail implementation audit (EXPLORATORY)

**Committed 12 Oct 2026, before any lab purchase or backtest.** The commit date is the evidence.
Design: `docs/superpowers/specs/2026-10-12-retail-vrp-audit-design.md` (rev 2). This is not a
registered hypothesis of the main project; it changes no registered file, number or verdict.

## What is fixed here, before any data
- **Funds:** SPY, QQQ, IWM, GLD, USO.
- **Dates:** trades and samples 4 Jan 2016 - 31 Aug 2026. Nothing bought or read after
  31 Aug 2026 (clear of H5e from 23 Sep, H7 from 9 Oct, H8 from 1 Dec 2026). The one earlier
  purchase is August 2015's daily marks, for a crash replay only.
- **Trades:** entry the first trading day after each standard monthly expiry, 14:30 New York;
  the next standard monthly expiry, 28-35 days out; held to expiry, settled at intrinsic on the
  fund's RAW close. Primary: short ATM straddle. Secondary: short 5% OTM strangle. Cross-check:
  synthetic 30-day variance swap on the Cboe indices.
- **Rules:** R0 always sell. R1 sell only when the fund's index exceeds its trailing 21-day
  realised volatility. R2 size inversely to the index level. R3 skip the month for all five funds
  when VIX3M < VIX.
- **Cost cases** (fraction of the quoted half-spread, entry only): mid 0, timed 0.30,
  retail 0.80 (headline), quoted 1.00. Commissions $0 and $0.65 per contract; the Leak Map uses
  $0.65.
- **Margin** (Cboe Margin Manual, 30 Nov 2021, customer margin account): SPY, QQQ, IWM a = 15%,
  b = 10%; GLD, USO a = 20%, b = 10%. Short put M = max(P + aS - OTM, P + bK); short call
  M = max(C + aS - OTM, C + bS); straddle = the greater side's requirement plus the other side's
  proceeds. Broker variant a = 40%, b = 35% (Santa-Clara & Saretto's E-Trade example).
  Liquidation mechanic as Santa-Clara & Saretto (2009): $1 a month, target weights 2.5/5/10/20%,
  calls met from cash, liquidation at the close when cash runs out, reopen at margin <= 90% of
  wealth.
- **Integrity, every day bought** (fails the day if any check fails):
  1. completeness: every strike OPRA lists for that expiry (Databento's definition schema, bought
     with each day) within +/-10% of the implied forward has both a call and a put quoted
     (ask > 0) within 120 s of the minute, and there are at least 3 such strikes. *(Amended
     12 Oct 2026 AFTER the test day; was "at least 10 strikes, every strike present in the file".
     See the log.)*
  2. sane spreads: at least 95% of those quotes have 0 <= bid <= ask and ask - bid <= max(mid,
     $0.10);
  3. put-call parity: within +/-5% of the forward, at least 90% of strikes have
     |(C_mid - P_mid + K) - median| <= (call half-spread + put half-spread) + 0.005 x forward.
- **Budget:** lab cap $90 (was $75; raised 12 Oct to cover OPRA listings), inside the $100 lifetime
  cap; priced first; never bought twice.
- **Leak Map:** R0 ATM straddle, 5% target weight, retail case; leaks in the order spreads,
  margin limits, forced liquidation, commissions; each leak credited its Shapley value over all
  24 orders, with the min and max across orders; cents kept per $1 undefined when the paper mean
  is not positive. The free-data estimate error is a separate bar, 2026 only, never subtracted.
- **Break-Even VIX:** weekly Wednesday 14:30 New York cost samples; premium from the monthly
  trades (headline) and weekly entries (robustness, Newey-West); index quintile bins with a linear
  fit; stationary-bootstrap interval; no extrapolation beyond the highest index level observed.
- **Stress:** stationary bootstrap, 10,000 ten-year paths, Patton-Politis-White block length
  with 1/3/6/12-month sensitivity; replays of Aug 2015, Feb 2018, Dec 2018, Mar 2020, Jun 2022,
  Aug 2024, Apr 2025, and the worst month x 1.5.
- **Deliberately not run:** the Cboe-method replica against GVZ/OVX on historical OPRA.

## Questions
Q1 the Leak Map; Q2 the Break-Even VIX; Q3 strip cost over ATM cost; Q4 effective weight and
liquidations under margin; Q5 bootstrap tails; Q6 the free-data estimate error (pilot seen
12 Oct 2026, measured, not predicted).

## Predictions (made before any lab data is bought)
- P1: at the retail case the straddle keeps under 50 cents per $1 on at least 3 of 5 funds.
- P2: spreads are the largest leak by Shapley share on at least 3 of 5 funds.
- P3: the strip costs at least twice the ATM estimate.
- P4: the retail cost as a fraction of the premium rises with the index level on at least 4 of
  5 funds.
- P5: retention is highest on SPY and lowest on USO.

## Log (dated; marked before or after any lab data)
- 2026-10-12, before any data: registered.
- 2026-10-12, before any data: the +/-10% and +/-5% band edges made inclusive (a 1e-9 allowance);
  float rounding had put strike 110 outside +/-10% of a forward of exactly 100. Caught by the
  known-answer tests; no threshold changed.
- 2026-10-12, AFTER the test day: 5 Feb 2018 bought ($0.0428, 5 files) and checked at 14:30 New
  York on the Feb 16 and Mar 16 expiries. SPY, QQQ, IWM, GLD pass all three checks on both expiries
  (30-83 strikes two-sided in the band, 100% sane, 100% within parity). USO fails ONLY the
  10-strike minimum: at $12.81 (before its 2020 1-for-8 reverse split) with $0.50 strikes, +/-10%
  holds 5 strikes, all two-sided, 100% sane, 100% within parity; the file carries 31 strikes,
  $3-$23. The rule is unchanged pending Gabriel's decision.
- 2026-10-12, AFTER the test day - the completeness rule amended (Gabriel's decision). The
  10-strike minimum measured strike DENSITY, not completeness: it could never pass a low-priced
  fund on a $0.50 grid. Replaced by a stricter, price-independent test - every strike OPRA itself
  lists for the expiry within +/-10% must be quoted on both sides (at least 3). It needs each day's
  listings (~$0.024 for the five funds), so the lab cap rose from $75 to $90. No return, P&L or
  premium had been computed, so the change cannot flatter a result. Re-run on 5 Feb 2018 with the
  listings ($0.0241, 5 files): all five funds pass on both expiries, and every fund's file carries
  every listed strike in the band (SPY 83/83 and 54/54, QQQ 63/63 and 33/33, IWM 58/58 and 30/30,
  GLD 41/41 and 25/25, USO 5/5 and 5/5). Decision: the archive is sound for 2018; Plan 2 proceeds on
  real straddles. Lab spend to date $0.0669.
- 2026-10-14, before any trade is computed - implementation choices for Plan 2:
  - Daily closes from Alpaca `sip` (raw for settlement, adjusted for realised volatility), which
    starts 4 Jan 2016. So the first entry is 19 Jan 2016, and the Aug 2015 replay (Plan 3) needs
    another price source or is dropped, stated then.
  - The last trade must expire by 31 Aug 2026, so the last entry is 20 Jul 2026 (expiry 21 Aug).
  - Rules read the previous trading day's closes (index, VIX, VIX3M, realised volatility); the
    entry at 14:30 precedes that day's close. R1 needs 21 prior returns; before they exist R1 does
    not trade.
  - R2's weight is 20 / index (the index in points; 20 is a fixed reference, not fitted).
  - ATM = the listed strike nearest the implied forward at 14:30; the strangle = the listed strikes
    nearest 0.95 and 1.05 x forward. Only two-sided strikes are eligible.
  - Returns are per dollar of mid premium; P&L = (mid - charged half-spread) - intrinsic at expiry.
  - The risk-free rate is 0 in the strip comparison (it enters mid and bid alike) and in vega;
    no FRED data is used in lab/.
  - A day failing the integrity checks is excluded for that fund and listed in the report.
  - Correction to the registration's "28-35 days out": entering on the trading day AFTER an
    expiry, the hold to the next monthly is 24-32 calendar days (the 28- or 35-day cycle less the
    days to the next session). The calendar rule itself is unchanged.
- 2026-10-14, before any trade is computed - three edge cases closed (from an automated review):
  only strikes with a positive, uncrossed bid on both legs are eligible (an option with no bid
  cannot be sold); a crossed leg yields no trade rather than a crash; a day with no index level
  lets only R0 and R3 trade. R2 stays 20/index uncapped, so it sizes above 1 when the index is
  below 20 - stated, and pinned by a test.
- 2026-10-14, AFTER data - Plan 2's first run (628 fund-months pass every check, 7 excluded).
  Two changes made after seeing the first run, both logged here because they move numbers:
  1. NYSE half-days: 24 Dec 2018 (1 p.m. close) had no quotes at 14:30, which silently dropped
     December 2018 - a crash month - for all five funds. Half-day entries now use 11:30 (the
     recorder's early-close time) and daily marks 12:55 (`tradecal.EARLY_CLOSES`, `slot`).
  2. A sensitivity is now always printed beside the registered numbers: every excluded month that
     can still be traded, added back. It matters: USO's straddle is +0.069 per $1 of premium at mid
     as registered (n=123) but -0.029 with its 4 excluded months added back (n=127; Mar/Apr 2020,
     when USO traded near $2 and only 2 strikes fit the band, Jul 2025, Jan 2026). GLD: -0.038 ->
     -0.093. Exclusions cluster in stress months, so the registered numbers flatter selling volatility
     on those two funds. Both are reported, always.
  Results, short ATM straddle, mean return per $1 of mid premium, registered; retail case (80% of the
  quoted half-spread) and share kept vs mid: SPY +0.064 -> +0.062 (0.97); QQQ +0.063 -> +0.061 (0.97);
  IWM +0.049 -> +0.046 (0.94); GLD -0.038 -> -0.045; USO +0.069 -> +0.049 (0.71). Worst single month
  (mid): SPY -5.25, QQQ -3.23, IWM -6.95, GLD -3.49, USO -5.85 premiums. 5% strangle, retail kept:
  SPY 0.99, QQQ 0.98, IWM 0.94; GLD and USO turn negative at any cost. Rules (retail): R1 helps SPY,
  QQQ, GLD and hurts IWM, USO; R3 helps SPY, QQQ, IWM, GLD.
  **P3 holds on 5 of 5:** strip cost / ATM cost, median: SPY 3.35, QQQ 2.86, IWM 2.71, GLD 2.06,
  USO 2.49. **Early read on P1/P2 (judged in Plan 3, with margin):** for ATM fund straddles held to
  expiry, spreads take only 3-6% of the premium on SPY/QQQ/IWM (29% on USO) - far less than the
  single-stock costs in Muravyev & Pearson. The losses that matter here are crash months, not costs.
- 2026-10-14, before any margin, Leak Map or stress number is computed - Plan 3 choices:
  - One month = one R0 ATM straddle, held to expiry. Capital $1 at entry, r = 0. Premium written at mid
    = target weight w (2.5/5/10/20%), so n = w / mid straddle per share.
  - Frictions (each on or off; 16 combinations): **spreads** - sold at mid minus 80% of the quoted
    half-spread (retail), and every later trade pays the same per-share cost; **margin limits** - at
    entry n is cut so the margin due n x (requirement - proceeds) <= 0.9 of capital; **forced
    liquidation** - each trading day, if cash < n x requirement (Cboe: 100% of market value + a x S -
    OTM, minimum b), the position is bought back at mark (+ cost), then reopened on the same strike
    with n' = min(n, 0.9 x wealth / (requirement - proceeds)); **commissions** - $0.65 per contract per
    leg per trade on a $100,000 account (0.0065 x n per $1 per leg).
  - Daily marks: in the registered stress months, real OPRA quotes at 15:55 New York (12:55 on a
    half-day), mid of the trade's strike and expiry, with the chain's implied forward as S; on every
    other day, Black-76 (r = 0) at that day's raw close with volatility = the fund's own Cboe index
    close / 100. The model marks miss the smile and are stated as an approximation; the stress
    months, where margin calls cluster, use real quotes.
  - Margin rates as registered (SPY/QQQ/IWM 15%/10%; GLD/USO 20%/10%); the broker variant 40%/35%
    reported beside it.
  - Leak Map at w = 5%: paper = all off; kept = all on; each friction's leak is its Shapley value
    over the 24 orders, with min and max across orders; cents kept = mean(kept) / mean(paper),
    undefined when mean(paper) <= 0.
  - Stress: monthly kept returns (all on, w = 5%) per fund; stationary bootstrap, 10,000 paths of
    120 months, block length by Patton-Politis-White (sensitivity 1/3/6/12); max drawdown median /
    95th / 99th percentile, expected shortfall 95% / 99% of a month, probability equity falls below
    $0.50 within ten years. Replays: each stress month's kept return, and the worst month x 1.5.
    Seed 20261014.
  - August 2015 is dropped from the replays: the fund closes begin 4 Jan 2016, so its trade cannot
    be built. (Its OPRA marks were bought before this was seen; ~$0.10.)
  - Every table is printed for the registered months and, beside it, with the tradeable excluded
    months added back (Plan 2's sensitivity).
- 2026-10-14, AFTER data - Plan 3 results (registered months; added-back months beside them in the
  private report). Check passed: paper returns at w = 5% equal 5% x Plan 2's straddle mid returns.
  **Leak Map, w = 5%, cents kept per $1 of paper return:** SPY 95.4, QQQ 94.3, IWM 90.0, USO 58.4
  (paper +0.346%/mo, kept +0.202%/mo; with its excluded months added back USO's paper return is
  -0.145%/mo, so its ratio is undefined); GLD undefined (paper -0.192%/mo). At 5% margin never binds:
  the leaks are spreads (SPY 0.008, QQQ 0.011, IWM 0.015, GLD 0.033, USO 0.100 %/mo) and commissions.
  **At w = 20% margin dominates:** SPY paper +1.277 -> kept +0.966%/mo, forced liquidation the largest
  leak (+0.523, range +0.049..+1.029 across orders); QQQ liquidation +0.305; IWM's liquidation and
  limits leaks are NEGATIVE (being forced out cut losses that kept growing). Called months at 20%:
  SPY 24, QQQ 21, IWM 12, GLD 30, USO 11 of ~125.
  **Stress, w = 5%, 10,000 ten-year paths** (PPW block 1.0 for every fund - no monthly
  autocorrelation): median max drawdown SPY 32.9%, QQQ 27.1%, IWM 40.1%, GLD 48.3%, USO 39.9%;
  P(equity < $0.50 within ten years) SPY 6.5%, QQQ 1.9%, IWM 15.7%, GLD 34.8%, USO 15.4% (conditional
  on 2016-2026's crashes). Worst month: the COVID trade (24 Feb -> 20 Mar 2020): SPY -26.3%,
  QQQ -16.2%, IWM -34.8%, USO -29.4%, GLD -10.6% of capital at w = 5%. Volmageddon (Feb 2018) cost
  SPY only -3.3% - held to expiry, the straddle recovered.
  A reporting error was fixed before logging: crash replays were keyed by ENTRY month, which hid the
  COVID trade (entered in February); they are now keyed by holding period.
  **P1 FAILS:** no fund keeps under 50 cents per $1 (SPY 95, QQQ 94, IWM 90, USO 58; GLD undefined).
  **P2 HOLDS as written** (spreads are the largest leak on 5 of 5 at w = 5%), but only because margin
  never binds at 5%; at 20% forced liquidation is the largest leak on SPY and QQQ. Both stated.
  The finding, plainly: for a retail seller of liquid fund straddles held to expiry, trading costs
  are small; the risk is the crash month and, at larger sizes, being forced out by margin.
- 2026-10-14, before any weekly sample is read - Plan 4 definitions:
  - Weekly sample: each Wednesday 14:30 New York (11:30 on a half-day), per fund, the standard
    monthly expiry with 20-45 days left that is nearest 30 days; ATM = the sellable strike nearest
    the implied forward; the day must pass the registered integrity checks for that expiry.
  - Cost (volatility points) = 0.80 x (call + put quoted half-spreads) / (call + put Black-76 vega,
    r = 0, at each leg's own implied volatility). Cost fraction = 0.80 x (half-spreads) / straddle mid.
  - Premium (volatility points), from Plan 2's monthly trades = straddle P&L at mid per share /
    entry straddle vega. Net = premium - cost (both per trade, in volatility points).
  - x-axis: the fund's own index at the previous trading day's close (VIX, VXN, RVX, GVZ, OVX); VIX
    for all five shown beside it.
  - Break-even: OLS of net on x; the crossing x* = -a / b, reported only if inside the observed
    range of x, else "none in range" with the direction of the sign. 90% interval from 2,000
    stationary-bootstrap resamples of the months (block length by PPW), seed 20261014; resamples
    whose crossing is out of range are counted and reported, not dropped silently. Quintile bins of x
    (mean x, mean net, count) printed for every fund.
  - P4 ("the retail cost as a fraction of the premium rises with the index level on at least 4 of 5
    funds"): premium = the straddle's mid price at entry; "rises" = OLS slope of the weekly cost
    fraction on x positive with its 95% Newey-West interval (lag 4 weeks) above zero.
- 2026-10-14, AFTER data - Plan 4 results (weekly samples complete: 492-504 per fund; one skip,
  USO 29 Apr 2020, its 1-for-8 split day, when OPRA listed nothing under USO.OPT). Lab purchasing is
  complete: 8,073 files, $79.00 of the $90 cap (lifetime ledger $81.45 of $100).
  **Break-Even, monthly net (straddle P&L at mid / vega - retail cost, volatility points) on the
  fund's own index:** SPY crossing VIX 18.9 (90% 12.1..27.6; 167 of 2,000 resamples out of range);
  QQQ VXN 23.8 (14.8..35.8; 225 out); IWM RVX 15.2 (13.9..45.5; 432 out); GLD GVZ 9.7 (interval
  10.6..29.0 excludes it; 555 out); USO OVX 28.6 (23.6..62.8; 479 out). Read plainly: NO RELIABLE
  BREAK-EVEN. Monthly net P&L swings by several volatility points from quintile to quintile (SPY
  +2.15, -1.05, +1.68), the intervals span most of the observed range, and 8-28% of resamples cross
  outside it. Direction: SPY and QQQ net falls as their index rises; IWM and USO net rises.
  **Costs are not what moves it:** the retail cost of the ATM straddle in volatility points roughly
  doubles from calm to stressed quintiles (SPY 0.024 -> 0.054, QQQ 0.037 -> 0.091, IWM 0.051 ->
  0.135, GLD 0.068 -> 0.226, USO 0.42 -> 1.24) but stays a few hundredths of a point on the equity
  funds, against monthly swings of several points. **P4 FAILS (1 of 5):** cost as a fraction of the
  premium rises with the index only on GLD (slope +0.00021, 95% +0.00013..+0.00030); on SPY, QQQ,
  IWM and USO spreads widen in proportion to the premium, so the fraction is flat.
  The finding, plainly: on liquid funds there is no fear level at which trading costs eat the
  premium; what decides the trade is the premium itself, and it is too noisy over ten years to name a
  break-even level with confidence.
- 2026-10-14, AFTER data - Plan 5 and close-out. **P5 ("retention highest on SPY, lowest on USO")
  HOLDS among the funds with a positive paper return** (SPY 95.4 cents per $1 highest; USO 58.4
  lowest; GLD has no paper profit, so no retention to rank - stated, not hidden). The trust engine
  (`lab/engine.py`) reads a free chain with the registered estimator (r = 0), an error bar from H8's
  pilot (mean |free - OPRA| + OPRA's one-minute floor), four flags (zero-bid wings, stale quotes,
  thin chain, spreads above the fund's own 90th percentile) and the retail straddle cost, raw and
  corrected by the measured free/OPRA spread ratio. A factor-of-2 error in its cost was caught by
  cross-checking against Plan 4's OPRA costs and fixed before use (SPY 0.041 vs 0.024-0.054 on OPRA).
  The report (`lab/report.py` -> the private lab-out/report.html) carries both charts.
  **Summary of the whole study:** P1 fails, P2 holds as written, P3 holds (5/5), P4 fails (1/5),
  P5 holds among funds with a paper profit. For a retail seller of liquid fund options held to
  expiry, trading costs are small; the crash month and, at larger sizes, margin decide the result;
  no fear level emerges at which costs eat the premium. Data: 8,073 OPRA files, $79.00.
- 2026-10-14, AUDIT (Gabriel: "have high confidence but don't fully trust everything"). Findings:
  1. **Purchases:** a new verifier (`lab/verify_purchases.py`, in the pressure test and the auditor)
     found 15 files Databento charged for and the tool logged as bought that hold only a header
     (half-day requests timed after the 1 p.m. close, before the 11:30 fix). None is used. Otherwise
     verified: 8,073 files, each with exactly one ledger row and the reverse; no truncated file; no
     ledger row outside the dates; every planned day-time present except the explained USO split day.
  2. **Independent recomputation:** settlement closes match OPRA's implied forward at 15:55 on 30
     expiry days (median 0.098%, worst 0.42% on 20 Mar 2020); the COVID trade rebuilt from the raw CSV
     with the csv module alone reproduces Plan 2's -5.2546 exactly; the Leak Map's leaks sum to paper
     minus kept to 1e-18.
  3. **Spec items found missing, now done:** (i) model vs real marks in the stress months: no bias
     (median error SPY +0.1%, QQQ +0.3%, IWM 0.0%, GLD +3.4%, USO +1.7% of the straddle's value),
     median absolute error 3-7%; (ii) the free-data bar: pricing costs from the free feed overstates the
     spreads leak by +2.7 / +1.0 / +1.7 / +0.9 cents per $1 on SPY / QQQ / IWM / USO (the 2026 pilot
     ratio applied to the decade - stated); (iii) Break-Even robustness: weekly entries (Newey-West)
     and VIX for every fund. They confirm "no reliable break-even": SPY's weekly slope is +0.023 (95%
     -0.199..+0.245) against the monthly -0.46; only GLD's weekly slope is significant (+0.378,
     +0.067..+0.690).
  4. **Checks added:** no registered reader may import lab/ (pressure test + mutant); the purchase
     verifier's two rules each proved by a mutant. Auditor 79 of 79.
  5. **For the main project (exploratory, `lab/main_links.py`):** on stress-month Wednesdays the
     registered estimator moves a median 0.53 volatility points between 14:30 and 15:55 (GLD 0.14,
     USO 0.74; one broken USO day in April 2020 excluded from interpretation) - the snapshot-timing
     effect, measured without LSEG. OPRA's ATM half-spread over 2016-2026: SPY 0.028, QQQ 0.051, IWM
     0.080, GLD 0.121, USO 0.737 volatility points (2026 alone: 0.026, 0.058, 0.093, 0.341, 2.067).
