# Bloomberg session checklist

**The terminal is a validation instrument, not a data source.** It holds only
~90 days of historical equity option data, so there is no long history to
collect. What it can do, and nothing else can, is tell you how good your free
data is. See HANDOFF section 15.1.

**Last updated 16 September 2026, evening — after the third pull.** Sessions on
14, 15 and 16 Sep.
Priorities 0 and 1 below are **done** and kept only as the record of what worked.
**The live asks are in "What is still wanted", and they are ranked.**

---

## What is still wanted, in priority order

### 0. BEFORE YOU PULL: check the recorder actually ran today

**New on 16 September, and it cost the whole point of that pull.** The recorders did
not run at all that day - GitHub dropped the scheduled trigger and left no trace - so
the 221-strike SPY export had no free-feed snapshot to be matched against, and SPY's
feed quality is *still* unmeasured.

A Bloomberg export is only half a comparison. Before pulling, confirm today's date
appears in `data/surface.csv` on GitHub, or run `python3 tools/panel_health.py`, which
now FAILS on a missed trading day. If the recorder has not run and the market is still
open, dispatch it by hand first and pull afterwards.

The day-count test (ask 1) is the exception: it never leaves the export, so it works
without the free feed. Everything about *feed quality* needs both sides.

### 1. A LONG-DATED expiry, wide strikes. This is the decisive one.

**Why it is first.** The 1.7-point implied-volatility gap has been identified as a
day count: Bloomberg's IVM is on a 252 business-day clock, the free feed on a 365
calendar-day one. That was estimated from two expiries at 31 and 66 days, and the
divisor came out between 248 and 256 across six blocks (H3, "The day count").

The two clocks **converge as maturity grows** - at two years, business days over
252 and calendar days over 365 are almost the same number. So a long-dated expiry
is where the explanation makes its riskiest prediction: **the gap should nearly
vanish.** If it does not, the day count is not the whole story and H3's section
needs rewriting. This is the one pull that can falsify a finding already recorded.

- `TSLA US Equity` `OMON`, Table view
- **The expiry nearest 18 months to 2 years out**, plus keep the ~30 day one
- **Raise the strike count to at least 50** for the long expiry. The 14 Sep export
  had 14 expiries at only 5 strikes each, which is why this is still open - the
  long maturities were there and unmeasurable.
- Record the `IFwd` and `R` printed in the long expiry's block header

**One reason to treat this as urgent rather than tidy.** The thin 14 Sep export
did reach 858 days, and on its five strikes the gap did *not* vanish - it read
about +4 points, where the day-count explanation predicts near zero. Five strikes
on a two-year contract with wide markets is not evidence and no conclusion was
drawn from it. But it is the one observation pointing away from a finding that is
already written down, and it should be settled rather than left.

### 2. SPY with 200+ strikes — EXPORT DONE 16 Sep, STILL NEEDS A MATCHED DAY

SPY is the underlying H3 cares most about - it is the VIX benchmark, and the
calibration matched Cboe to 0.01 points on it. The 15 Sep export matched only **14
contracts** against the free feed, because 40 strikes a dollar apart spans 2.6% of
spot.

**The 16 Sep pull fixed the export: 221 strikes, 442 quotes, all with IVM.** That
was enough to measure SPY on the day count for the first time (n=133, gap +0.63 on
365 collapsing to +0.06 on 252). **But the recorder did not run that day, so it
still could not be matched contract by contract, and SPY's feed quality remains
unmeasured.**

- Repeat the same 221-strike SPY pull on **any day the recorder has run** - see
  ask 0. Nothing about the export needs changing; it was correct.
- The ~30 day expiry is enough here

### 3. Find out whether Bloomberg STATES its day count anywhere

**Highest value for the least time.** Everything in section 1 is an inference from
prices. If the terminal documents the convention, the inference becomes a fact.

- On an option contract, `DES` then `<GO>`, and look for a model or day-count line
- `OVME` (the option valuation screen) exposes model settings - look for a day
  count, calendar, or "252/365" basis selector
- `HELP HELP` on OMON opens the help page; search it for `IVM` and for `day count`
- The field `IVOL_MID` in `FLDS` may carry a description naming the model

**Write down the exact wording and where you found it**, even if it seems to say
nothing. A screenshot is ideal.

### 4. Whether OMON can add an OPEN INTEREST column

The exports so far carry Strike, Ticker, Bid, Ask, Last, IVM, Volm - **no open
interest.** H4d is the one prediction in this project that is mine rather than
replicated, and it separates volume from open interest. The free feed's OI lags
about two trading days and nothing has checked it.

- In OMON, look for a column chooser or `Settings`/`Edit Columns`
- If OI can be added, include it in every export from now on
- If it cannot, say so and it will be dropped as an ask

### 5. A second and third matched day, any tickers

The whole *feed-quality* cross-check still rests on **one day**, 15 Sep - 16 Sep
produced no match for the reason in ask 0. The day-count finding, which needs only
the export, now has two days and ten expiry blocks. Replication is worth more than any new
ticker. TSLA and USO on any two further days would move H3 from "a cross-check" to
"a small sample", which is a different sentence in a write-up.

### 6. Still unresolved from the first session

- **How far back does "As of" actually go?** Set it to 30 days, then 60, then 120.
  Library guides say 90 calendar days; the whole Bloomberg plan was rewritten on
  that claim and it is still unconfirmed.
- **Is there a visible export limit?** Any warning about daily or monthly caps.
- **Goukasian on publishing derived Bloomberg figures.** Still unanswered, sent
  11 Sep. **This is now blocking**: HANDOFF section 17 action 2 is to put the
  Bloomberg result on the public site, and that cannot proceed on an assumption.
  Worth a short chase.

---

## Timing — this changed on 16 September, read it again

**The recorders moved.** `record.yml` now fires 14:47 UTC and `surface.yml` 14:57,
and GitHub delays them 3-4.5 hours, so **the snapshot now lands roughly
18:00-19:20 UTC**. That is close to where it used to land, but the window is
tighter and no longer drifts toward the close.

- **Pull as close to 18:30 UTC as you can manage.**
- **In local time that is 11:30am Pacific — until Sunday 1 November**, when US
  clocks change and 18:30 UTC becomes 10:30am Pacific. The recorder's cron is in
  UTC and does not move. Work in UTC and convert.
- **Whatever time you pull, write it down to the minute.** An exact time with a
  mismatch is usable; a tight match with an unknown time is not.
- Pass it in: `python3 tools/bloomberg_compare.py --pull-time 18:57`. Without it
  the file's save time is used, which is later and fails the 30-minute gap check.

## The pull protocol, as refined by two sessions

1. `TICKER US Equity` then `OMON` then `<GO>`
2. Switch the display to **Table** (the default is a graph)
3. **Raise the strike count** - the default ~5 per expiry is useless. Counts that
   worked: **TSLA 50** covers ±30%, **USO needs about 80**, **SPY needs 200+**
   because its strikes step a dollar at a time.
4. Export: the green **Export** button, or `Actions > Export to Excel`
5. Save as `TICKER_OMON_YYYY-MM-DD.xlsx`
6. **Record the `IFwd` and `R` printed in each expiry block header** - they look
   like `16-Oct-26 (31d); CSize 100; R 4.26; IFwd 358.17`, and both tools read them
7. Note the pull time

## Where the files go

`~/Documents/volrec-bloomberg/`, **never inside the repository.** Both
`bloomberg_compare.py` and `model_gap.py` refuse a path inside it, and
`pressure_test.py` checks no spreadsheet has appeared there. Derived aggregates may
be published with **"Source: Bloomberg Finance L.P."**; per-contract quotes may not.

## What NOT to do

- **Do not attempt a fifteen-year pull.** The data is not there. Do not burn a
  session rediscovering that.
- **Do not export raw data intending to commit it.** The licence is restrictive and
  this repo is public.
- **Do not filter strikes by hand at the terminal.** Pull the whole chain for the
  expiry and let the tools match it. Filtering by hand wastes time and drops the
  contracts that matter.
- **Do not trade a wide strike count for more tickers.** One wide export beats
  three narrow ones - that is the lesson of the 14 Sep pull, which had fourteen
  expiries and could measure none of them.

## Send me

The Excel file(s), plus:
- the **pull time**, to the minute, with timezone
- the **`IFwd` and `R`** from each expiry block used
- anything found for ask 3 (the stated day count) - exact wording or a screenshot
- whether OMON could add open interest
- whether "As of" reached past 90 days
- anything that did not work

---

## Settled — kept as the record, no action needed

**Priority 0, get one chain into Excel: DONE** (14 Sep, terminal PAY-BLOOM-03).
The protocol above is what worked.

**Priority 1, verify field names: DONE.** Verified in `FLDS` on
`TSLA US 10/16/26 C390 Equity`: `PX_BID`, `PX_ASK`, `PX_VOLUME`, `OPEN_INT` all
exist. On `TSLA US Equity`: `30DAY_IMPVOL_100.0%MNY_DF` and `VOLATILITY_30D` are
equity-level fields, not per-contract. **`LQA_PRICE_VOLATILITY` is a
liquidity-model field, not implied volatility - ignore it.**

**Priority 2, the comparison pull: DONE for TSLA and USO** on 15 Sep, 78 and 40
matched contracts. Prices agree with the free feed to within half a bid-ask spread
and volumes to within 3%. SPY is the gap, which is why it is ask 2 above.
