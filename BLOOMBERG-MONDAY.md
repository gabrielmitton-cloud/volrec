# Bloomberg session checklist

**The terminal is a validation instrument, not a data source.** It holds only
~90 days of historical equity option data, so there is no long history to
collect. What it can do, and nothing else can, is tell you how good your free
data is. See HANDOFF section 15.1.

**18 September: fourth pull (USO, 16 Oct, wide) — see ask 1b and ask 3.**

**23 September: the sixth pull answered asks 1, 1b and 3.** USO and TSLA on BOTH of the
recorder's expiries (23 Oct and 30 Oct) 0-4 minutes from the snapshot - H5a-b's third
matched day, and both pass; TSLA 16 Jun 2028 with 134 strikes (ask 1); and the day
count stated in writing by the help desk (ask 3). Results: H3 "The day count, stated by
Bloomberg and tested at 21 months" and H5 "The third matched wing day". **What worked:**
OMON shows monthly expiries only until **weekly** is switched on (the recorder's pair
are weeklies for the rest of October); the help desk is reached with **HELP pressed
twice** - typing a question into the command line runs it as a function (it opened
`IN`, the index browser).

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

**DONE 23 Sep: TSLA 16-Jun-28, 134 strikes. The gap did NOT vanish:** +0.95 points on
the 252 clock and +0.94 on 365, so the clocks converge as predicted but about one
point remains that is not the day count (early exercise +0.90). The day count is the
whole story at 21-45 days, not at 21 months. H3 has it. Follow-up is ask 3's second
question, below.

*Bloomberg figures: Source: Bloomberg Finance L.P.*

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

### 1b. USO out to ±60% on both of the recorder's expiries — NEW 18 September

**DONE 23 Sep, both expiries, USO and TSLA. H5a and H5b have their three days** and
both hold (H5a weakly - see H5's Result). More matched days are still useful but no
longer binding.

**22 Sep: USO and TSLA pulled, 16 Oct only again.** USO matched cleanly (0.39 of a
spread; wings 0.09 and 0.00). TSLA FAILED the price gate at 0.87 because it moved
0.14% in the 24 minutes between snapshots. **Before the next session run
`python3 tools/bloomberg_prep.py --date YYYY-MM-DD`**: it names both expiries, the
strike range and the landing window. Pull BOTH expiries, and pull TSLA first,
within 10 minutes of the snapshot.

**Half done 18 Sep.** 16 Oct pulled 18:25 UTC, 30 minutes after the recorder, 144
strikes reaching 0.03x-2.04x spot: the wings match to 0.07 (puts) and 0.40 (calls)
of a spread, and it exposed the zero-bid contamination in H3's wide lift (H3, "The
first wide day"). **Still wanted: the SECOND expiry** (23 Oct on 18 Sep; see the
dates below), and a second day. Note the export came out Ticker-first rather than
Strike-first; the tools now read both, so nothing needs changing at the terminal.

**Why.** From 18 September the recorder also writes USO's wings out to ±60% of spot
(`data/surface_wide.csv`), and H3 predicts that adding them lifts USO's model-free
estimate by 1.4 to 3.2 points. The wings are exactly where a free indicative feed is
weakest: thin quotes, zero bids, stale prints. Nothing has ever checked the free
feed's far-wing prices against a second vendor. A matched wide USO export does two
things no other pull can: it measures **feed quality in the tails**, and it lets the
lift be computed **from Bloomberg's own prices** on the same day, independently of
the free feed.

- **Pull on a day the recorder has run** (ask 0). The wide file lands with the
  surface run, around 18:30 UTC.
- `USO US Equity` `OMON` `<GO>`, Table view.
- **Set `Exp` FIRST, then `Strikes`** - they are separate amber fields, and the
  library's answer of 17 Sep was to set the expiry before the strike count.
- **The two expiries the recorder uses:** the last Friday at or under 30 days out, and
  the Friday after it. Mon 21 and Tue 22 Sep: **16 Oct and 23 Oct**. Wed 23 Sep to
  Tue 29 Sep: **23 Oct and 30 Oct**. Export both.
- **Strikes: 200, or the field's maximum.** USO was near $156 on 17 Sep, so ±60% is
  about **$62 to $250**. The 16 Sep pull at 80 strikes reached only -26%. Before
  exporting, **check the lowest strike shown is at or below ~$65 and the highest at
  or above ~$245**; if the field caps short of that, write down the range reached.
- Export, save as `USO_OMON_YYYY-MM-DD.xlsx` in `~/Documents/volrec-bloomberg/`,
  record `IFwd` and `R` for **both** expiry blocks and the pull time to the minute,
  in UTC.

`tools/bloomberg_compare.py` matches the wings automatically (built 18 Sep against the
first real export). Aggregates only in anything published, with
"Source: Bloomberg Finance L.P.".

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

*Bloomberg figures: Source: Bloomberg Finance L.P.*

### 3. Find out whether Bloomberg STATES its day count anywhere

**ANSWERED 23 Sep, in writing:** OMON's IVM is ACT/252 business time, weekends and
exchange holidays excluded, intraday precision, not configurable; OVME and OVDV's BVOL
surfaces use calendar ACT/365. Documented at `LPHP OMON:0:1 4373105` ("Migration to
Business Day Convention", June 2023) and `HELP OMON`. **The one open follow-up**, same
route (HELP pressed twice, paste into the chat box, never the command line), final
wording 23 Sep, to be sent Thu 24 Sep:

> "For TSLA US 06/16/28 options in OMON, how is the IVM column solved? (1) Which forward does it use: the IFwd shown in the expiry header, or one built from a rate curve with a borrow or dividend assumption? (2) Which rate: the single R in the header, or a term curve? (3) Is the pricing model American or European for these equity options? (4) Does the ACT/252 business-day count to expiry exclude the 2027 and 2028 exchange holidays? Context: re-solving OMON's own mid prices on ACT/252 with the header IFwd and R reproduces IVM on the October 2026 expiries to within about 0.2 vol points, but leaves about 1 vol point on 16-Jun-28."

That is what the 21-month residual turns on. Send back the reply verbatim.

**ANSWERED 24 Sep by email (recorded in H3):** the forward is IFwd and the rate is the
expiry's own R - both what `model_gap.py` uses, so neither is the residual. American
options use a finite-difference model; holidays in 2027-28 are unconfirmed. **The next
and last ask on this: one `GIV` screen.** At the terminal:

1. Type `TSLA US 06/16/28 C380 Equity` then `GIV` and press GO (Enter).
2. `Actions` -> `View Calc Inputs`.
3. Photograph or write down EVERYTHING on that inputs screen, above all: the **time to
   expiry** (with its units: days, business days or years), the rate, any dividend,
   borrow or carry figure, the forward, the underlying price, the exercise style and
   model, and the implied volatility. Note the time you looked.
4. Repeat for `TSLA US 06/16/28 P300 Equity`.
5. Optional, in OMON: `Settings` -> `Edit Columns`, add `XTyp`, and note what it shows
   for the 16-Jun-28 block.

No timing constraint: this never touches the free feed.

**18 Sep: asked, not answered.** The reply described the `GV` template (60-day
classical historical volatility against 3-month at-the-money implied volatility)
and said nothing about how OMON's IVM annualises time. Still open. Ask again naming
the field, and ask for a documentation link: *"In OMON, the IVM column: when you
convert days to expiry into a year fraction, do you divide trading days by 252 or
calendar days by 365? Please point me to the documentation."* Meanwhile the prices
say 252 on a third day (divisor 252.0, 18 Sep).

*Bloomberg figures: Source: Bloomberg Finance L.P.*

**Now the single most important ask on this list, and it is not close.** A research
pass on 16 Sep established that Bloomberg does **not** publish IVM's day-count basis
anywhere public, and found one observable pointing the other way: an OVME ticket
displaying a *calendar-day* "Time to Expiry" counter. A displayed tenor is not an
annualisation basis, but until a written reply exists, **252 is an inference from
prices and must not be asserted as Bloomberg's convention.**

A dated, written Help Desk reply is the primary source the whole section is missing.

- **`HELP HELP` is the one that matters** - it routes a written question to the
  Bloomberg desk. Ask literally: *"What day-count and annualisation basis does the
  IVM column in OMON use for implied volatility - calendar/365 or trading/252?"*
  Save the reply with its date; that is the citable source.
- `FLDS` on a contract, search `IVOL_MID`, and open the field's description
- `OVME` exposes model settings - look for a day count, calendar, or 252/365 basis
  selector. SEC-filed warrant contracts that price off OVME specify their own
  annualisation factor (some 360, some 365), which suggests OVME exposes it as a
  parameter. If there is a toggle, note its default.
- `DES` on a contract, looking for a model or day-count line

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
