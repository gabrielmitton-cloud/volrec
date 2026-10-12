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
